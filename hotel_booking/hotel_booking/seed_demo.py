"""Load demo data: 20 rooms, staff, guests and bookings
(~5 weeks: past stays with invoices, guests in-house now, upcoming reservations,
cancellations and a no-show to process).

Usage:  python seed_demo.py
Logins: admin / admin123 · manager / manager1 · reception / front123 · housekeeping / clean123
"""
import random
from datetime import date, datetime, timedelta

from hotel import utils
from hotel.auth import AuthManager
from hotel.billing import BillingManager
from hotel.bookings import BookingManager
from hotel.customers import CustomerManager
from hotel.database import JSONDatabase
from hotel.rooms import RoomManager
from hotel.staff import StaffManager

ROOMS = [("101", "Standard"), ("102", "Standard"), ("103", "Standard"), ("104", "Standard"), ("105", "Standard"),
         ("106", "Standard"), ("201", "Deluxe"), ("202", "Deluxe"), ("203", "Deluxe"), ("204", "Deluxe"),
         ("205", "Deluxe"), ("206", "Deluxe"), ("301", "Executive"), ("302", "Executive"), ("303", "Executive"),
         ("304", "Executive"), ("401", "Suite"), ("402", "Suite"), ("403", "Suite"), ("404", "Suite")]
NAMES = ["Anitta Joseph", "Rahul Menon", "Priya Nair", "Arjun Das", "Fathima Rasheed", "Thomas Kurian",
         "Meera Pillai", "Vishnu Varma", "Sneha George", "Akhil Krishnan", "Divya Mathew", "Nikhil Raj",
         "Lakshmi Iyer", "Sreejith Babu", "Reshma Thomas", "Emily Clark", "Hiroshi Tanaka", "Sara Ahmed",
         "Joseph Mathew", "Aswathy Nair", "Kiran Kumar", "Neha Sharma", "Varun Gupta", "Anjali Menon"]
SERVICES = [("Food & Beverage", "Room service dinner", (600, 2400)), ("Food & Beverage", "Breakfast in room", (350, 900)),
            ("Laundry", "Laundry", (200, 700)), ("Spa & Wellness", "Ayurvedic massage", (2500, 4500)),
            ("Other Services", "Airport transfer", (900, 1500))]


def main():
    random.seed(8)
    db = JSONDatabase(utils.DATA_DIR)
    if db.all("rooms"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    sm = StaffManager(db, "admin")
    for user, name, role, phone, shift, salary, pw in [
            ("manager", "Ravi Shankar", "manager", "9895011111", "General (9-18)", 45000, "manager1"),
            ("reception", "Divya Krishnan", "receptionist", "9895022222", "Morning (6-14)", 22000, "front123"),
            ("reception2", "Akash Thomas", "receptionist", "9895033333", "Evening (14-22)", 22000, "front123"),
            ("housekeeping", "Sumathi Devi", "housekeeping", "9895044444", "Morning (6-14)", 16000, "clean123")]:
        _, temp = sm.add(user, name, role, phone, f"{user}@malabarresidency.in", shift, salary)
        auth.change_password(user, temp, pw, pw)

    rm = RoomManager(db, "admin")
    for no, cat in ROOMS:
        rm.add(no, cat)
    rm.set_status("404", "MAINTENANCE")

    cm = CustomerManager(db, "reception")
    custs = []
    for i, name in enumerate(NAMES):
        foreign = name in ("Emily Clark", "Hiroshi Tanaka")
        phone = f"+44 7700 9{i:05d}" if foreign else f"9{random.randint(100000000, 999999999)}"
        idt, idn = ("Passport", f"{random.choice('KLMNPZ')}{random.randint(1000000, 9999999)}") if foreign or i % 5 == 0 \
            else ("Aadhaar", str(random.randint(2 * 10**11, 10**12 - 1)))
        custs.append(cm.add(name, phone, f"{name.split()[0].lower()}{i}@example.com", idt, idn,
                            random.choice(["Kochi", "Thrissur", "Bengaluru", "Chennai", "Mumbai", "London", "Tokyo"]),
                            "British" if name == "Emily Clark" else "Japanese" if name == "Hiroshi Tanaka" else "Indian",
                            "32AABCU9603R1ZM" if i == 6 else ""))

    bm, billing = BookingManager(db, "reception"), BillingManager(db, "reception")
    today = date.today()

    def pay(bid, amount, when, mode=None):
        mode = mode or random.choice(["Cash", "UPI", "Card"])
        p = billing.record_payment(bid, amount, mode, "" if mode == "Cash" else f"REF{random.randint(10**6, 10**7)}")
        db.update("payments", "payment_id", p["payment_id"], {"at": when.isoformat(timespec="seconds")})

    rooms = [r for r, _ in ROOMS if r != "404"]
    stats = {"stays": 0, "in_house": 0, "upcoming": 0, "cancelled": 0}
    # Past and current stays: walk day by day, filling rooms ~55-80 %
    start = today - timedelta(days=35)
    for offset in range(0, 38):
        day = start + timedelta(days=offset)
        for room in random.sample(rooms, k=random.randint(2, 6)):
            nights = random.choice([1, 1, 2, 2, 3, 4])
            co = day + timedelta(days=nights)
            if not rm.is_free(room, day, co) or day > today + timedelta(days=2):
                continue
            cap = RoomManager.capacity(rm.get(room))
            adults = random.randint(1, cap)
            b = bm.create(random.choice(custs)["customer_id"], room, day, co, adults, 0,
                          extra_bed=random.random() < 0.08, discount_pct=random.choice([0, 0, 0, 5, 10]),
                          source=random.choice(utils.BOOKING_SOURCES), allow_past=True)
            booked_at = datetime.combine(day - timedelta(days=random.randint(1, 20)), datetime.min.time()).replace(hour=11)
            if random.random() < 0.5:
                pay(b["booking_id"], round(bm.estimate(b)["grand_total"] * 0.3), booked_at)
            if day > today:                                  # upcoming: leave confirmed
                stats["upcoming"] += 1
                continue
            if random.random() < 0.07 and day < today:       # late cancellation
                bm.cancel(b["booking_id"], "Plans changed", at=datetime.combine(day, datetime.min.time()).replace(hour=9))
                stats["cancelled"] += 1
                continue
            if day == today - timedelta(days=1) and stats.get("noshow") is None:
                stats["noshow"] = b["booking_id"]            # leave one past-arrival unprocessed (no-show)
                continue
            rm.set_status(room, "AVAILABLE")
            bm.check_in(b["booking_id"], on=datetime.combine(day, datetime.min.time()).replace(hour=random.randint(12, 20)))
            for _ in range(random.choice([0, 1, 1, 2, 3])):
                svc, desc, (lo, hi) = random.choice(SERVICES)
                bm.add_charge(b["booking_id"], svc, desc, random.randint(lo, hi))
            if co <= today:
                when = datetime.combine(co, datetime.min.time()).replace(hour=10, minute=random.randint(0, 59))
                bal = bm.checkout_preview(b["booking_id"], co)["bill"]["balance"]
                if bal > 0:
                    pay(b["booking_id"], bal, when)
                bm.check_out(b["booking_id"], on=when)
                if co < today:
                    rm.set_status(room, "AVAILABLE")         # housekeeping done for older stays
                stats["stays"] += 1
            else:
                stats["in_house"] += 1
    # Future reservations over the next 3 weeks
    for _ in range(18):
        ci = today + timedelta(days=random.randint(1, 21))
        co = ci + timedelta(days=random.randint(1, 4))
        free = rm.available(ci, co)
        if free:
            r = random.choice(free)
            b = bm.create(random.choice(custs)["customer_id"], r["room_no"], ci, co, 2 if RoomManager.capacity(r) >= 2 else 1,
                          source=random.choice(utils.BOOKING_SOURCES))
            if random.random() < 0.6:
                pay(b["booking_id"], round(bm.estimate(b)["grand_total"] * 0.3), datetime.now() - timedelta(days=1))
            stats["upcoming"] += 1

    print(f"Seeded {len(ROOMS)} rooms, {len(custs)} guests, {stats['stays']} completed stays, "
          f"{stats['in_house']} guests in-house, {stats['upcoming']} upcoming bookings, "
          f"{stats['cancelled']} cancellations, 1 no-show to process.")
    print("Logins: admin/admin123 · manager/manager1 · reception/front123 · housekeeping/clean123")


if __name__ == "__main__":
    main()
