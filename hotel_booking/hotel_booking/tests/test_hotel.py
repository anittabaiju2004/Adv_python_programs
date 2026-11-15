"""Unit tests — run with:  python -m pytest -q"""
import json
from datetime import date, datetime, timedelta

import pytest

from hotel.admin import AdminPanel
from hotel.auth import AuthManager, can, require
from hotel.backup import BackupManager
from hotel.billing import BillingManager, price_nights
from hotel.bookings import BookingManager
from hotel.customers import CustomerManager
from hotel.database import JSONDatabase
from hotel.reports import ReportGenerator
from hotel.rooms import RoomManager
from hotel.staff import StaffManager
from hotel.utils import (AuthenticationError, AvailabilityError, BackupError, DatabaseError, HotelError,
                         NotFoundError, PermissionDenied, ValidationError, financial_year, room_gst_rate,
                         rupees_in_words, validate_id_proof, validate_phone)

TODAY = date.today()


def next_weekday(wd, after=TODAY + timedelta(days=3)):
    d = after
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


MON = next_weekday(0)          # a Monday at least 3 days ahead


@pytest.fixture
def db(tmp_path):
    d = JSONDatabase(tmp_path / "data")
    AuthManager(d)
    rm = RoomManager(d)
    for no, cat in [("101", "Standard"), ("102", "Standard"), ("201", "Deluxe"), ("301", "Executive"),
                    ("401", "Suite")]:
        rm.add(no, cat)
    return d


@pytest.fixture
def guest(db):
    return CustomerManager(db).add("Anitta Joseph", "9847012345", "anitta@x.com", "Aadhaar", "2345 6789 0123",
                                   "Kochi")


@pytest.fixture
def bm(db):
    return BookingManager(db, "frontdesk")


def book(bm, guest, room="101", ci=MON, nights=2, **kw):
    return bm.create(guest["customer_id"], room, ci, ci + timedelta(days=nights), **kw)


# ================================================================ utilities
def test_gst_slabs_and_helpers():
    assert room_gst_rate(7500) == 5 and room_gst_rate(7500.01) == 18
    assert financial_year(date(2026, 3, 31)) == "2025-26" and financial_year(date(2026, 4, 1)) == "2026-27"
    assert rupees_in_words(10500) == "Ten Thousand Five Hundred Rupees Only"
    assert validate_phone("+44 20 7946 0958") == "+442079460958"
    assert validate_id_proof("passport", "k1234567") == ("Passport", "K1234567")
    with pytest.raises(ValidationError):
        validate_id_proof("Aadhaar", "0123 4567 8901")


def test_pricing_weekend_extra_bed_discount():
    fri = next_weekday(4)
    nights = price_nights(6800, fri - timedelta(days=1), fri + timedelta(days=2))   # Thu, Fri, Sat
    assert [n["weekend"] for n in nights] == [False, True, True]
    assert [n["tariff"] for n in nights] == [6800, 7480, 7480]
    assert all(n["gst_rate"] == 5 for n in nights)                                 # all <= 7,500
    with_bed = price_nights(6800, fri, fri + timedelta(days=1), extra_bed=True)
    assert with_bed[0]["tariff"] == 8280 and with_bed[0]["gst_rate"] == 18         # bed pushes it over 7,500
    disc = price_nights(9500, MON, MON + timedelta(days=1), discount_pct=25)
    assert disc[0]["tariff"] == 7125 and disc[0]["gst_rate"] == 5                  # discount brings it under
    with pytest.raises(ValidationError):
        price_nights(5000, MON, MON + timedelta(days=1), discount_pct=50)


# ===================================================================== auth
def test_roles_and_staff(db):
    sm = StaffManager(db, "admin")
    staff, temp = sm.add("ravi", "Ravi Kumar", "receptionist", "9895012345")
    auth = AuthManager(db)
    user = auth.login("ravi", temp)
    assert user["must_change_password"] and can(user, "bookings") and not can(user, "reports")
    with pytest.raises(PermissionDenied):
        require(user, "staff")
    assert can(auth.login("admin", "admin123"), "anything")
    auth.change_password("ravi", temp, "front123", "front123")
    sm.set_active("ravi", False)
    with pytest.raises(AuthenticationError, match="disabled"):
        auth.login("ravi", "front123")
    with pytest.raises(HotelError):
        sm.set_active("admin", False)                       # only admin
    with pytest.raises(ValidationError):
        sm.add("ravi", "X Y", "manager", "9000000001")     # duplicate username


def test_lockout(db):
    auth = AuthManager(db)
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            auth.login("admin", "bad")
    with pytest.raises(AuthenticationError, match="locked"):
        auth.login("admin", "admin123")


# ==================================================================== rooms
def test_rooms_and_availability(db, bm, guest):
    rm = RoomManager(db)
    with pytest.raises(ValidationError):
        rm.add("101", "Standard")
    assert rm.add("1205A", "Deluxe", rate=5000)["floor"] == 12
    book(bm, guest, "101")
    free = [r["room_no"] for r in rm.available(MON, MON + timedelta(days=1), "Standard")]
    assert free == ["102"]
    assert "101" in [r["room_no"] for r in rm.available(MON + timedelta(days=2), MON + timedelta(days=3))]
    rm.set_status("102", "MAINTENANCE")
    assert rm.available(MON, MON + timedelta(days=1), "Standard") == []
    with pytest.raises(HotelError):
        rm.delete("101")                                    # has an upcoming booking
    with pytest.raises(HotelError):
        rm.set_status("102", "OCCUPIED")
    assert [r["room_no"] for r in rm.available(MON, MON + timedelta(days=1), guests=5)] == ["401"]


# ================================================================ customers
def test_customers(db, guest):
    cm = CustomerManager(db)
    assert guest["customer_id"] == "C1001" and guest["id_number"] == "234567890123"
    with pytest.raises(ValidationError, match="already registered"):
        cm.add("Other", "+91 98470 12345")
    assert [c["customer_id"] for c in cm.search("anitta")] == ["C1001"]
    assert [c["customer_id"] for c in cm.search("12345")] == ["C1001"]
    cm.update("c1001", email="new@x.com")
    assert cm.get("C1001")["email"] == "new@x.com"
    c2 = cm.add("Bob Roy", "9000000001")
    cm.delete(c2["customer_id"])


# ================================================================= bookings
def test_booking_rules(db, bm, guest):
    b = book(bm, guest, "101", adults=2)
    assert b["booking_id"] == "BK10001" and b["nights"] == 2 and b["status"] == "CONFIRMED"
    with pytest.raises(AvailabilityError):
        book(bm, guest, "101", ci=MON + timedelta(days=1))
    with pytest.raises(ValidationError, match="holds 2"):
        book(bm, guest, "102", adults=3)
    assert book(bm, guest, "102", adults=3, extra_bed=True)["extra_bed"]
    with pytest.raises(ValidationError):
        bm.create(guest["customer_id"], "201", TODAY - timedelta(days=1), TODAY)       # past
    with pytest.raises(ValidationError):
        book(bm, guest, "201", nights=31)
    assert [x["booking_id"] for x in bm.search("anitta")] == ["BK10001", "BK10002"]


def test_cancellation_policy(db, bm, guest):
    billing = BillingManager(db, "frontdesk")
    early = book(bm, guest, "101")
    billing.record_payment(early["booking_id"], 2000, "UPI", "UPI123")
    r = bm.cancel(early["booking_id"], "Change of plans")
    assert r["fee"] == 0 and r["refund"] == 2000 and billing.paid(early["booking_id"]) == 0
    late = book(bm, guest, "201")
    billing.record_payment(late["booking_id"], 6000, "Cash")
    arrival = datetime.combine(MON, datetime.min.time()).replace(hour=12)
    r = bm.cancel(late["booking_id"], "Flight cancelled", at=arrival - timedelta(hours=20))
    first = late["nights_detail"][0]
    assert r["fee"] == first["tariff"] + first["gst"] == 4725 and r["refund"] == 1275
    assert bm.get(late["booking_id"])["cancellation_fee"] == 4725
    with pytest.raises(HotelError):
        bm.cancel(late["booking_id"], "again")


def test_full_stay_with_charges_and_invoice(db, bm, guest, tmp_path):
    billing = BillingManager(db, "frontdesk")
    ci = TODAY - timedelta(days=2)
    b = bm.create(guest["customer_id"], "301", ci, ci + timedelta(days=2), adults=2, allow_past=True)
    billing.record_payment(b["booking_id"], 5000, "Card", "TXN998")
    bm.check_in(b["booking_id"], on=datetime.combine(ci, datetime.min.time()).replace(hour=13))
    assert RoomManager(db).get("301")["status"] == "OCCUPIED"
    bm.add_charge(b["booking_id"], "food & beverage", "Dinner", 1200)
    bm.add_charge(b["booking_id"], "Laundry", "Shirts", 300)
    with pytest.raises(HotelError, match="Balance due"):
        bm.check_out(b["booking_id"])
    bill = bm.checkout_preview(b["booking_id"])["bill"]
    room = sum(n["tariff"] for n in b["nights_detail"])
    assert bill["taxable"] == room + 1500
    assert bill["gst"] == round(sum(n["gst"] for n in b["nights_detail"]) + 1200 * .18 + 300 * .18, 2)
    assert bill["cgst"] + bill["sgst"] == bill["gst"] and bill["grand_total"] == round(bill["taxable"] + bill["gst"])
    billing.record_payment(b["booking_id"], bill["balance"], "Cash")
    out = bm.check_out(b["booking_id"])
    assert out["status"] == "CHECKED_OUT" and out["invoice_no"].endswith("/0001")
    assert RoomManager(db).get("301")["status"] == "CLEANING"
    assert billing.invoice_pdf(b["booking_id"], tmp_path).read_bytes()[:4] == b"%PDF"
    hist = CustomerManager(db).history(guest["customer_id"])
    assert hist["stays"] == 1 and hist["total_spent"] == bill["grand_total"]


def test_checkin_rules_early_checkout_and_refund(db, bm, guest):
    billing = BillingManager(db, "frontdesk")
    no_id = CustomerManager(db).add("Bob Roy", "9000000001")
    ci = TODAY - timedelta(days=1)
    b1 = bm.create(no_id["customer_id"], "102", ci, ci + timedelta(days=3), allow_past=True)
    with pytest.raises(HotelError, match="ID proof"):
        bm.check_in(b1["booking_id"])
    b = bm.create(guest["customer_id"], "201", ci, ci + timedelta(days=4), allow_past=True)
    RoomManager(db).set_status("201", "CLEANING")
    with pytest.raises(HotelError, match="CLEANING"):
        bm.check_in(b["booking_id"])
    RoomManager(db).set_status("201", "AVAILABLE")
    bm.check_in(b["booking_id"])
    billing.record_payment(b["booking_id"], 15000, "Cash")
    prev = bm.checkout_preview(b["booking_id"])           # leaving after 1 night of 4
    assert prev["early"] and prev["booking"]["nights"] == 1
    out = bm.check_out(b["booking_id"])
    assert out["nights"] == 1 and out["invoice"]["balance"] == 0
    assert billing.paid(b["booking_id"]) == out["invoice"]["grand_total"]   # excess refunded
    assert RoomManager(db).is_free("201", TODAY + timedelta(days=1), TODAY + timedelta(days=2))


def test_extend_change_room_and_no_show(db, bm, guest):
    b = book(bm, guest, "101", nights=2)
    other = CustomerManager(db).add("Bob Roy", "9000000001", id_type="Passport", id_number="K1234567")
    bm.create(other["customer_id"], "101", MON + timedelta(days=3), MON + timedelta(days=5))
    b = bm.extend(b["booking_id"], MON + timedelta(days=3))
    assert b["nights"] == 3 and len(b["nights_detail"]) == 3
    with pytest.raises(AvailabilityError):
        bm.extend(b["booking_id"], MON + timedelta(days=4))
    b = bm.change_room(b["booking_id"], "102")
    assert b["room_no"] == "102"
    past = bm.create(guest["customer_id"], "401", TODAY - timedelta(days=2), TODAY, allow_past=True)
    BillingManager(db).record_payment(past["booking_id"], 15000, "Cash")
    marked = bm.mark_no_shows()
    assert [m["booking_id"] for m in marked] == [past["booking_id"]]
    first = past["nights_detail"][0]
    assert BillingManager(db).paid(past["booking_id"]) == first["tariff"] + first["gst"]


def test_payment_rules(db, bm, guest):
    billing = BillingManager(db)
    b = book(bm, guest, "101")
    with pytest.raises(ValidationError, match="reference"):
        billing.record_payment(b["booking_id"], 100, "UPI")
    with pytest.raises(ValidationError, match="exceeds"):
        billing.record_payment(b["booking_id"], 99999, "Cash")
    with pytest.raises(ValidationError):
        billing.refund(b["booking_id"], 10, "Cash")
    with pytest.raises(HotelError):
        billing.invoice_pdf(b["booking_id"], "/tmp")         # no invoice before check-out


# ========================================================= reports & admin
def test_reports_and_dashboard(db, bm, guest, tmp_path):
    billing = BillingManager(db)
    ci = TODAY - timedelta(days=3)
    b = bm.create(guest["customer_id"], "201", ci, ci + timedelta(days=2), allow_past=True)
    bm.check_in(b["booking_id"], on=datetime.combine(ci, datetime.min.time()).replace(hour=14))
    billing.record_payment(b["booking_id"], bm.checkout_preview(b["booking_id"])["bill"]["balance"], "Cash")
    bm.check_out(b["booking_id"])
    book(bm, guest, "101", ci=TODAY + timedelta(days=1))
    rg = ReportGenerator(db, tmp_path)
    rev = rg.revenue(TODAY - timedelta(days=7), TODAY)
    room_rev = sum(n["tariff"] for n in b["nights_detail"])          # 4,500/night (+10 % on weekends)
    assert rev["invoices"] == 1 and rev["room_revenue"] == room_rev and rev["adr"] == round(room_rev / 2, 2)
    occ = rg.occupancy(ci, ci + timedelta(days=1))
    assert occ["average_occupancy"] == 20.0 and occ["by_category"]["Deluxe"]["occupancy"] == 100
    assert occ["revpar"] == round(room_rev / 10, 2)                     # 5 rooms x 2 nights
    for p in (rg.bookings_csv(), rg.customers_csv(), rg.revenue_csv(ci, TODAY), rg.occupancy_csv(ci, TODAY),
              rg.performance_pdf(ci, TODAY)):
        assert p.exists() and p.stat().st_size > 50
    assert "234567890123" not in rg.customers_csv().read_text(encoding="utf-8-sig")   # ID masked
    dash = AdminPanel(db).dashboard()
    assert dash["rooms"] == 5 and dash["status"]["CLEANING"] == 1
    assert any(a["action"] == "CHECKED_OUT" for a in AdminPanel(db).activity())


# =========================================================== backup & db
def test_backup_and_persistence(db, guest, tmp_path):
    bk = BackupManager(db.data_dir, tmp_path / "backups")
    archive = bk.create_backup()
    CustomerManager(db).add("Bob Roy", "9000000001")
    bk.restore(archive)
    assert len(CustomerManager(JSONDatabase(db.data_dir)).list()) == 1
    assert json.loads((db.data_dir / "rooms.json").read_text())[0]["room_no"] == "101"
    (db.data_dir / "bookings.json").write_text("{bad")
    with pytest.raises(DatabaseError):
        BookingManager(db).list()
    bad = tmp_path / "backups" / "hotel_backup_bad.zip"
    bad.write_text("x")
    with pytest.raises(BackupError):
        bk.restore(bad)
    with pytest.raises(NotFoundError):
        CustomerManager(db).get("C9999")
