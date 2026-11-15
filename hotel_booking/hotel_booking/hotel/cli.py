"""Menu-driven interface with role-based menus (admin, manager, receptionist, housekeeping)."""
from __future__ import annotations

import getpass
import sys
from datetime import date, timedelta

from . import utils
from .admin import AdminPanel
from .auth import AuthManager, can, require
from .backup import BackupManager
from .billing import BillingManager
from .bookings import BookingManager
from .customers import CustomerManager
from .database import JSONDatabase
from .reports import ReportGenerator
from .rooms import STATUSES, RoomManager
from .staff import SHIFTS, StaffManager
from .utils import (BOOKING_SOURCES, HOTEL_NAME, ID_PROOFS, PAYMENT_MODES, ROLES, ROOM_CATEGORIES,
                    SERVICE_TYPES, HotelError, money)

W = 80


# ======================================================================= ui
def line(ch: str = "-") -> None:
    print(ch * W)


def header(title: str) -> None:
    print()
    line("=")
    print(f"{title:^{W}}")
    line("=")


def ask(prompt: str, default: str | None = None) -> str:
    v = input(f"  {prompt}{f' [{default}]' if default else ''}: ").strip()
    return v if v else (default or "")


def confirm(prompt: str) -> bool:
    return ask(f"{prompt} (y/n)").lower() in ("y", "yes")


def pause() -> None:
    input("\n  Press Enter to continue...")


def menu(title: str, options: list[str], back: str = "Back") -> str:
    header(title)
    for i, o in enumerate(options, 1):
        print(f"  {i:>2}. {o}")
    print(f"   0. {back}")
    return ask("Choose an option")


def choose(prompt: str, options: list[str], allow_blank: bool = False) -> str:
    for i, o in enumerate(options, 1):
        print(f"     {i}. {o}")
    while True:
        v = ask(prompt)
        if allow_blank and not v:
            return ""
        if v.isdigit() and 1 <= int(v) <= len(options):
            return options[int(v) - 1]
        for o in options:
            if o.lower() == v.lower():
                return o
        print("  Invalid choice.")


def print_bookings(bs: list[dict]) -> None:
    if not bs:
        print("  No bookings.")
        return
    print(f"  {'Booking':<9}{'Guest':<20}{'Room':<6}{'Category':<11}{'Check-in':<12}{'Check-out':<12}{'N':>3}  Status")
    line()
    for b in bs:
        print(f"  {b['booking_id']:<9}{b['guest_name'][:19]:<20}{b['room_no']:<6}{b['category']:<11}"
              f"{b['check_in']:<12}{b['check_out']:<12}{b['nights']:>3}  {b['status']}")


def print_bill(bill: dict) -> None:
    print(f"  {'Room charges':<34}{money(bill['room_taxable']):>16}")
    print(f"  {'Extra services':<34}{money(bill['extras_taxable']):>16}")
    for rate, v in bill["gst_by_rate"].items():
        print(f"  {'GST @ ' + rate + '% (CGST+SGST) on ' + format(v['taxable'], ',.2f'):<34}{money(v['gst']):>16}")
    print(f"  {'Round off':<34}{bill['round_off']:>+16,.2f}")
    line()
    print(f"  {'GRAND TOTAL':<34}{money(bill['grand_total']):>16}")
    print(f"  {'Paid':<34}{money(bill['paid']):>16}")
    print(f"  {'BALANCE':<34}{money(bill['balance']):>16}")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = report_dir or utils.REPORT_DIR
        self.user: dict | None = None

    # managers bound to the logged-in user (for the activity log)
    @property
    def actor(self) -> str:
        return self.user["username"] if self.user else "system"

    def rooms(self):
        return RoomManager(self.db, self.actor)

    def customers(self):
        return CustomerManager(self.db, self.actor)

    def bookings(self):
        return BookingManager(self.db, self.actor)

    def billing(self):
        return BillingManager(self.db, self.actor)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(HOTEL_NAME.upper(), ["Staff login", "Room tariff card"], "Exit")
            try:
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.tariff_card()
                    pause()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except HotelError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def login(self) -> None:
        header("STAFF LOGIN")
        self.user = self.auth.login(ask("Username"), getpass.getpass("  Password: "))
        if self.user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one.")
            while True:
                try:
                    self.change_password()
                    break
                except HotelError as exc:
                    print(f"  ✖ {exc}")
        print(f"\n  Welcome, {self.user['name']} ({self.user['role']}).")
        self.dashboard()
        self.main_menu()

    def main_menu(self) -> None:
        items = [("Dashboard", self.dashboard, None, False),
                 ("Front desk (bookings, check-in/out, billing)", self.front_desk, "bookings", True),
                 ("Rooms & housekeeping", self.room_menu, "rooms", True),
                 ("Customers", self.customer_menu, "customers", True),
                 ("Reports", self.report_menu, "reports", True),
                 ("Staff management", self.staff_menu, "staff", True),
                 ("Admin panel (activity log, backup)", self.admin_menu, "admin", True),
                 ("Change password", self.change_password, None, False)]
        items = [i for i in items if i[2] is None or can(self.user, i[2])]
        while self.user:
            choice = menu(f"{HOTEL_NAME} — {self.user['name']} ({self.user['role']})", [i[0] for i in items], "Logout")
            if choice == "0":
                print("  Logged out.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(items)):
                continue
            _, handler, _, submenu = items[int(choice) - 1]
            try:
                handler()
            except HotelError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            if not submenu:
                pause()

    def submenu(self, title: str, options: list[tuple]) -> None:
        """options: (label, handler[, permission])"""
        options = [o for o in options if len(o) < 3 or can(self.user, o[2])]
        while self.user:
            choice = menu(title, [o[0] for o in options])
            if choice == "0":
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                continue
            try:
                options[int(choice) - 1][1]()
            except HotelError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.actor, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    def tariff_card(self) -> None:
        header("ROOM TARIFF CARD")
        print(f"  {'Category':<11}{'Per night':>11}{'Weekend':>11}{'Guests':>8}  Amenities")
        line()
        for c, v in ROOM_CATEGORIES.items():
            wk = v["rate"] * (1 + utils.WEEKEND_SURCHARGE / 100)
            print(f"  {c:<11}{money(v['rate']):>11}{money(wk):>11}{v['capacity']:>8}  {v['amenities']}")
        print(f"\n  Weekend (Fri & Sat nights) +{utils.WEEKEND_SURCHARGE:g}% · Extra bed {money(utils.EXTRA_BED_RATE)}/night")
        print(f"  GST: {utils.GST_ROOM_LOW:g}% on tariff up to {money(utils.GST_ROOM_THRESHOLD)}/night, "
              f"{utils.GST_ROOM_HIGH:g}% above · Check-in {utils.CHECK_IN_TIME}, check-out {utils.CHECK_OUT_TIME}")
        print(f"  Free cancellation up to {utils.FREE_CANCELLATION_HOURS} hours before check-in; "
              "later cancellations are charged one night.")

    def dashboard(self) -> None:
        d = AdminPanel(self.db).dashboard()
        header(f"DASHBOARD — {d['date']}")
        status = ", ".join(f"{k.title()} {v}" for k, v in sorted(d["status"].items()))
        print(f"  Rooms: {d['rooms']}  ({status})")
        print(f"  Tonight: {d['sold_tonight']} sold — {d['occupancy_tonight']}% occupancy · "
              f"In-house: {d['in_house']} rooms / {d['guests_in_house']} guests")
        print(f"  Arrivals today: {len(d['arrivals'])} · Departures today: {len(d['departures'])} · "
              f"Arrivals next 7 days: {d['upcoming_7_days']}")
        if can(self.user, "billing"):
            print(f"  Collected today: {money(d['collected_today'])}")
        for b in d["arrivals"]:
            print(f"   → arriving  {b['booking_id']} {b['guest_name']:<20} room {b['room_no']}")
        for b in d["departures"]:
            print(f"   ← departing {b['booking_id']} {b['guest_name']:<20} room {b['room_no']}")
        if d["overdue_departures"]:
            print(f"  ⚠ {len(d['overdue_departures'])} guest(s) past their check-out date.")
        if d["pending_no_shows"]:
            print(f"  ⚠ {len(d['pending_no_shows'])} confirmed booking(s) did not arrive (mark as no-show).")

    # ---------------------------------------------------------- front desk
    def front_desk(self) -> None:
        self.submenu("FRONT DESK", [
            ("New booking", self.new_booking), ("Find / view booking", self.view_booking),
            ("Check-in", self.check_in), ("Add service charge (room service, laundry, spa)", self.add_charge),
            ("Collect payment / advance", self.collect_payment), ("Check-out & invoice", self.check_out),
            ("Cancel booking", self.cancel_booking), ("Extend stay", self.extend_stay),
            ("Change room", self.change_room), ("Print pro-forma bill / invoice (PDF)", self.print_bill),
            ("Arrivals, departures & in-house lists", self.lists),
            ("Mark no-shows", self.no_shows, "noshow")])

    def pick_booking(self, statuses: tuple | None = None):
        q = ask("Booking ID, guest name/phone or room no.")
        bm = self.bookings()
        try:
            b = bm.get(q)
            matches = [b]
        except HotelError:
            matches = bm.search(q)
        if statuses:
            matches = [b for b in matches if b["status"] in statuses]
        if not matches:
            raise HotelError("No matching booking" + (f" ({'/'.join(statuses)})" if statuses else "") + ".")
        if len(matches) == 1:
            return matches[0]
        print_bookings(matches)
        bid = ask("Booking ID").upper()
        return next((b for b in matches if b["booking_id"] == bid), None) or bm.get(bid)

    def pick_customer(self, create: bool = True) -> dict:
        cm = self.customers()
        q = ask("Guest phone, name or customer ID" + (" (blank = new guest)" if create else ""))
        if not q and create:
            return self.new_customer()
        found = cm.find_by_phone(q)
        matches = [found] if found else cm.search(q)
        if not matches:
            if create and confirm("Guest not found. Register a new guest?"):
                return self.new_customer(phone=q if any(ch.isdigit() for ch in q) else "")
            raise HotelError("Guest not found.")
        if len(matches) == 1:
            c = matches[0]
            print(f"  Guest: {c['customer_id']} {c['name']} ({c['phone']})")
            return c
        for i, c in enumerate(matches, 1):
            print(f"  {i:>2}. {c['customer_id']} {c['name']:<22} {c['phone']}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= len(matches)):
            raise HotelError("Invalid selection.")
        return matches[int(n) - 1]

    def new_customer(self, phone: str = "") -> dict:
        header("REGISTER GUEST")
        name = ask("Full name")
        phone = ask("Phone", phone or None)
        email = ask("Email (optional)")
        id_type = choose("ID proof (blank = record at check-in)", list(ID_PROOFS), allow_blank=True)
        id_no = ask(f"{id_type} number") if id_type else ""
        c = self.customers().add(name, phone, email, id_type, id_no, ask("Address"),
                                 ask("Nationality", "Indian"), ask("Company GSTIN (optional)"))
        print(f"  ✔ Guest registered: {c['customer_id']}")
        return c

    def new_booking(self) -> None:
        header("NEW BOOKING")
        ci = ask("Check-in date YYYY-MM-DD", date.today().isoformat())
        nights = ask("Nights", "1")
        co = (utils.parse_date(ci) + timedelta(days=int(nights) if nights.isdigit() else 1)).isoformat()
        guests = int(ask("Number of guests", "2") or 2)
        cat = choose("Category (blank = any)", list(ROOM_CATEGORIES), allow_blank=True) or None
        free = self.rooms().available(ci, co, cat, guests)
        if not free:
            raise HotelError("No rooms available for those dates.")
        print(f"\n  Available {ci} → {co}:")
        for r in free:
            print(f"   Room {r['room_no']:<6}{r['category']:<11}{money(RoomManager.tariff(r)):>12}/night  "
                  f"up to {RoomManager.capacity(r)} guests")
        room_no = ask("Room number", free[0]["room_no"])
        cust = self.pick_customer()
        children = int(ask("Of these, children", "0") or 0)
        cap = RoomManager.capacity(self.rooms().get(room_no))
        extra_bed = guests > cap or (guests == cap and confirm("Add an extra bed?"))
        discount = ask("Discount %", "0") if can(self.user, "discount") else "0"
        source = choose("Booking source", BOOKING_SOURCES)
        b = self.bookings().create(cust["customer_id"], room_no, ci, co, guests - children, children, extra_bed,
                                   float(discount or 0), source, ask("Special requests (optional)"))
        est = self.bookings().estimate(b)
        print(f"\n  ✔ Booking {b['booking_id']} confirmed: room {b['room_no']}, {b['nights']} night(s).")
        for n in b["nights_detail"]:
            print(f"     {n['date']}{' (weekend)' if n['weekend'] else '':<11} {money(n['tariff']):>12} + GST {n['gst_rate']:g}%")
        print(f"     Estimated total (incl. GST): {money(est['grand_total'])}")
        if confirm("Collect an advance now?"):
            self._collect(b["booking_id"])

    def view_booking(self) -> None:
        b = self.pick_booking()
        header(f"BOOKING {b['booking_id']} — {b['status']}")
        c = self.customers().get(b["customer_id"])
        print(f"  Guest      : {c['name']} ({c['customer_id']}) · {c['phone']} · ID: {c['id_type'] or 'not recorded'}")
        print(f"  Room       : {b['room_no']} ({b['category']})  ·  {b['adults']} adult(s), {b['children']} child(ren)"
              + ("  + extra bed" if b["extra_bed"] else ""))
        print(f"  Stay       : {b['check_in']} → {b['check_out']} ({b['nights']} night(s))  ·  source {b['source']}")
        if b["discount_pct"]:
            print(f"  Discount   : {b['discount_pct']:g}%")
        if b["requests"]:
            print(f"  Requests   : {b['requests']}")
        if b["charges"]:
            print("  Charges    :")
            for ch in b["charges"]:
                print(f"     {ch['id']} {ch['date']} {ch['service']:<16}{ch['description'][:24]:<25}"
                      f"{money(ch['amount']):>10} + {ch['gst_rate']:g}%")
        if b["status"] in ("CANCELLED", "NO_SHOW"):
            print(f"  Cancelled  : {b['cancelled_at']} — {b['cancel_reason']} (retained {money(b['cancellation_fee'])})")
        if b.get("invoice_no"):
            print(f"  Invoice    : {b['invoice_no']} dated {b['invoice_date']}")
        print()
        print_bill(b["invoice"] if b.get("invoice") else self.bookings().estimate(b))
        pays = self.billing().payments(b["booking_id"])
        if pays:
            print("\n  Payments:")
            for p in pays:
                print(f"     {p['at'][:16].replace('T', ' ')}  {p['kind']:<8}{p['mode']:<12}{money(p['amount']):>12}  {p['reference']}")

    def check_in(self) -> None:
        b = self.pick_booking(("CONFIRMED",))
        c = self.customers().get(b["customer_id"])
        if not c["id_number"]:
            print("  ID proof is required at check-in.")
            id_type = choose("ID proof", list(ID_PROOFS))
            self.customers().update(c["customer_id"], id_type=id_type, id_number=ask(f"{id_type} number"))
        room = self.rooms().get(b["room_no"])
        if room["status"] != "AVAILABLE":
            print(f"  Room {room['room_no']} is {room['status']}.")
            if room["status"] == "CLEANING" and confirm("Has housekeeping finished? Mark it available"):
                self.rooms().set_status(room["room_no"], "AVAILABLE")
            elif confirm("Move the guest to another room?"):
                self.change_room(b)
        b = self.bookings().check_in(b["booking_id"])
        print(f"  ✔ {b['guest_name']} checked in to room {b['room_no']}. Check-out on {b['check_out']} by "
              f"{utils.CHECK_OUT_TIME}.")

    def add_charge(self) -> None:
        b = self.pick_booking(("CHECKED_IN",))
        service = choose("Service", list(SERVICE_TYPES))
        ch = self.bookings().add_charge(b["booking_id"], service, ask("Description"), ask("Amount (before GST)"))
        print(f"  ✔ {ch['service']} {money(ch['amount'])} + GST {ch['gst_rate']:g}% ({money(ch['gst'])}) added to "
              f"room {b['room_no']}.")

    def _collect(self, booking_id: str, amount: str | None = None) -> None:
        bal = self.billing().bill(booking_id)["balance"]
        amt = ask("Amount", amount or f"{max(bal, 0):.2f}")
        mode = choose("Payment mode", PAYMENT_MODES)
        ref = ask("Transaction reference") if mode != "Cash" else ""
        p = self.billing().record_payment(booking_id, amt, mode, ref)
        print(f"  ✔ Received {money(p['amount'])} by {mode} (receipt {p['payment_id']}).")

    def collect_payment(self) -> None:
        b = self.pick_booking(("CONFIRMED", "CHECKED_IN"))
        print_bill(self.billing().bill(b["booking_id"]))
        self._collect(b["booking_id"])

    def check_out(self) -> None:
        b = self.pick_booking(("CHECKED_IN",))
        prev = self.bookings().checkout_preview(b["booking_id"])
        header(f"CHECK-OUT — {b['booking_id']} room {b['room_no']}")
        if prev["early"]:
            print(f"  ⚠ Early departure: billing {prev['booking']['nights']} of {b['nights']} night(s).")
        print_bill(prev["bill"])
        if prev["bill"]["balance"] > 0:
            print()
            self._collect(b["booking_id"], f"{prev['bill']['balance']:.2f}")
        refund_mode = "Cash"
        if self.bookings().checkout_preview(b["booking_id"])["bill"]["balance"] < 0:
            refund_mode = choose("Refund excess advance by", PAYMENT_MODES)
        out = self.bookings().check_out(b["booking_id"], refund_mode=refund_mode)
        print(f"\n  ✔ Checked out. Invoice {out['invoice_no']} — total {money(out['invoice']['grand_total'])}.")
        print(f"    Room {out['room_no']} sent to housekeeping.")
        if confirm("Save the invoice as PDF?"):
            print(f"  ✔ Saved: {self.billing().invoice_pdf(out['booking_id'], self.report_dir / 'invoices')}")

    def cancel_booking(self) -> None:
        b = self.pick_booking(("CONFIRMED",))
        q = self.bookings().cancellation_quote(b["booking_id"])
        print(f"  {q['hours_before']:g} hours before check-in. Cancellation fee {money(q['fee'])}; "
              f"paid {money(q['paid'])}; refund {money(q['refund'])}.")
        if q["due"]:
            print(f"  (Fee not covered by advance: {money(q['due'])} — collect separately if applicable.)")
        if confirm(f"Cancel booking {b['booking_id']}?"):
            mode = choose("Refund mode", PAYMENT_MODES) if q["refund"] else "Cash"
            self.bookings().cancel(b["booking_id"], ask("Reason", "Guest request"), mode)
            print("  ✔ Booking cancelled.")

    def extend_stay(self) -> None:
        b = self.pick_booking(("CONFIRMED", "CHECKED_IN"))
        new = ask("New check-out date YYYY-MM-DD",
                  (utils.parse_date(b["check_out"]) + timedelta(days=1)).isoformat())
        b = self.bookings().extend(b["booking_id"], new)
        print(f"  ✔ Extended to {b['check_out']} ({b['nights']} nights). New estimate "
              f"{money(self.bookings().estimate(b)['grand_total'])}.")

    def change_room(self, b: dict | None = None) -> None:
        b = b or self.pick_booking(("CONFIRMED", "CHECKED_IN"))
        start = max(b["check_in"], date.today().isoformat())
        free = [r for r in self.rooms().available(start, b["check_out"], guests=b["adults"] + b["children"],
                                                   allow_past=True) if r["room_no"] != b["room_no"]]
        for r in free:
            print(f"   Room {r['room_no']:<6}{r['category']:<11}{money(RoomManager.tariff(r)):>12}/night  {r['status']}")
        if not free:
            raise HotelError("No other room is free for the remaining nights.")
        new = ask("New room", free[0]["room_no"])
        reprice = confirm("Charge the new room's tariff for remaining nights? (n = keep current rate)")
        b = self.bookings().change_room(b["booking_id"], new, reprice)
        print(f"  ✔ Moved to room {b['room_no']}.")

    def print_bill(self) -> None:
        b = self.pick_booking(("CHECKED_IN", "CHECKED_OUT", "CONFIRMED"))
        folder = self.report_dir / "invoices"
        if b.get("invoice_no"):
            print(f"  ✔ Saved: {self.billing().invoice_pdf(b['booking_id'], folder)}")
        else:
            print(f"  ✔ Pro-forma bill saved: {self.billing().invoice_pdf(b['booking_id'], folder, proforma=True)}")

    def lists(self) -> None:
        bm = self.bookings()
        d = ask("Date YYYY-MM-DD", date.today().isoformat())
        header(f"ARRIVALS — {d}")
        print_bookings(bm.arrivals(d))
        header(f"DEPARTURES — {d}")
        print_bookings(bm.departures(d))
        header("IN-HOUSE GUESTS")
        print_bookings(bm.in_house())

    def no_shows(self) -> None:
        pending = [b for b in self.bookings().list("CONFIRMED") if b["check_in"] < date.today().isoformat()]
        print_bookings(pending)
        if pending and confirm(f"Mark these {len(pending)} booking(s) as no-show (first night retained)?"):
            print(f"  ✔ {len(self.bookings().mark_no_shows())} booking(s) marked as no-show.")

    # --------------------------------------------------------------- rooms
    def room_menu(self) -> None:
        self.submenu("ROOMS & HOUSEKEEPING", [
            ("Room status board", self.room_board), ("Check availability", self.availability),
            ("Update room status (housekeeping)", self.housekeeping, "housekeeping"),
            ("Tariff card", self.tariff_card),
            ("Add room", self.add_room, "rooms.manage"), ("Edit room (category / tariff)", self.edit_room, "rooms.manage"),
            ("Delete room", self.delete_room, "rooms.manage")])

    def room_board(self) -> None:
        header("ROOM STATUS BOARD")
        in_house = {b["room_no"]: b for b in BookingManager(self.db).in_house()}
        floor = None
        for r in self.rooms().list():
            if r["floor"] != floor:
                floor = r["floor"]
                print(f"\n  Floor {floor}")
            guest = f"  {in_house[r['room_no']]['guest_name']} until {in_house[r['room_no']]['check_out']}" \
                if r["room_no"] in in_house else ""
            print(f"   {r['room_no']:<6}{r['category']:<11}{money(RoomManager.tariff(r)):>11}  {r['status']:<12}{guest}")
        print("\n  " + ", ".join(f"{k} {v}" for k, v in self.rooms().summary()["by_status"].items()))

    def availability(self) -> None:
        ci = ask("Check-in YYYY-MM-DD", date.today().isoformat())
        co = ask("Check-out YYYY-MM-DD", (utils.parse_date(ci) + timedelta(days=1)).isoformat())
        free = self.rooms().available(ci, co, guests=int(ask("Guests", "1") or 1))
        header(f"AVAILABLE {ci} → {co}: {len(free)} room(s)")
        for r in free:
            print(f"   {r['room_no']:<6}{r['category']:<11}{money(RoomManager.tariff(r)):>11}/night  "
                  f"{RoomManager.capacity(r)} guests  {ROOM_CATEGORIES[r['category']]['amenities']}")

    def housekeeping(self) -> None:
        dirty = self.rooms().list(status="CLEANING")
        if dirty:
            print("  Rooms waiting for cleaning: " + ", ".join(r["room_no"] for r in dirty))
        room = ask("Room number", dirty[0]["room_no"] if dirty else None)
        options = [s for s in STATUSES if s != "OCCUPIED"]
        if not can(self.user, "rooms.manage"):
            options = ["AVAILABLE", "CLEANING"]
        r = self.rooms().set_status(room, choose("New status", options))
        print(f"  ✔ Room {r['room_no']} is now {r['status']}.")

    def add_room(self) -> None:
        r = self.rooms().add(ask("Room number"), choose("Category", list(ROOM_CATEGORIES)), None,
                             ask("Custom tariff (blank = category rate)") or None, ask("Notes (optional)"))
        print(f"  ✔ Room {r['room_no']} added on floor {r['floor']}.")

    def edit_room(self) -> None:
        r = self.rooms().get(ask("Room number"))
        cat = choose(f"Category (blank = keep {r['category']})", list(ROOM_CATEGORIES), allow_blank=True) or None
        rate = ask("Custom tariff (blank = keep, 'x' = use category rate)")
        self.rooms().update(r["room_no"], cat, "" if rate.lower() == "x" else (rate or None), ask("Notes", r["notes"] or None))
        print("  ✔ Room updated.")

    def delete_room(self) -> None:
        room = ask("Room number")
        if confirm(f"Delete room {room}?"):
            self.rooms().delete(room)
            print("  ✔ Deleted.")

    # ----------------------------------------------------------- customers
    def customer_menu(self) -> None:
        def view():
            h = self.customers().history(self.pick_customer(create=False)["customer_id"])
            c = h["customer"]
            header(f"{c['customer_id']} — {c['name']}")
            for k in ("phone", "email", "id_type", "id_number", "address", "nationality", "gstin"):
                print(f"  {k.replace('_', ' ').title():<12}: {c[k] or '-'}")
            print(f"\n  Stays {h['stays']} · nights {h['nights']} · spent {money(h['total_spent'])} · "
                  f"cancellations {h['cancellations']}")
            print_bookings(h["bookings"])

        def update():
            c = self.pick_customer(create=False)
            print("  Leave blank to keep the current value.")
            changes = {k: ask(k.title(), c[k] or None) for k in ("name", "phone", "email", "address")}
            changes = {k: v for k, v in changes.items() if v != c[k]}
            if confirm("Update ID proof?"):
                changes["id_type"] = choose("ID proof", list(ID_PROOFS))
                changes["id_number"] = ask("Number")
            self.customers().update(c["customer_id"], **changes)
            print("  ✔ Updated.")

        def listing():
            for c in self.customers().list():
                print(f"  {c['customer_id']:<7}{c['name'][:24]:<25}{c['phone']:<15}{c['email'][:26]:<27}{c['id_type']}")

        def delete():
            c = self.pick_customer(create=False)
            if confirm(f"Delete {c['customer_id']} {c['name']}?"):
                self.customers().delete(c["customer_id"])
                print("  ✔ Deleted.")
        self.submenu("CUSTOMERS", [("Register guest", self.new_customer), ("Search / view guest & history", view),
                                   ("List all guests", listing), ("Update guest", update), ("Delete guest", delete)])

    # ------------------------------------------------------------- reports
    def report_menu(self) -> None:
        rg = ReportGenerator(self.db, self.report_dir)

        def period():
            first = date.today().replace(day=1)
            return ask("From YYYY-MM-DD", first.isoformat()), ask("To YYYY-MM-DD", date.today().isoformat())

        def revenue():
            r = rg.revenue(*period())
            header(f"REVENUE {r['start']} → {r['end']}")
            print(f"  Room revenue          {money(r['room_revenue']):>16}   ({r['room_nights']} room nights, ADR {money(r['adr'])})")
            for k, v in r["extras"].items():
                print(f"    {k:<20}{money(v):>16}")
            print(f"  Cancellation fees     {money(r['cancellation_fees']):>16}")
            print(f"  NET REVENUE           {money(r['net_revenue']):>16}   (excl. GST)")
            print(f"  GST collected         {money(r['gst_collected']):>16}")
            print(f"  Invoices issued       {r['invoices']:>16}")
            print("\n  By room category:")
            for c, v in r["by_category"].items():
                print(f"    {c:<12}{v['nights']:>4} nights {money(v['revenue']):>16}")
            print("\n  Payments received (net of refunds):")
            for m, v in r["payments_by_mode"].items():
                print(f"    {m:<14}{money(v):>16}")

        def occupancy():
            o = rg.occupancy(*period())
            header(f"OCCUPANCY {o['start']} → {o['end']} — average {o['average_occupancy']}%")
            print(f"  ADR {money(o['adr'])} · RevPAR {money(o['revpar'])} · "
                  f"peak {o['peak']['date']} ({o['peak']['occupancy']}%)")
            for c, v in o["by_category"].items():
                print(f"    {c:<12}{v['rooms']:>3} rooms {v['sold']:>5} nights sold {v['occupancy']:>7}%")
            print()
            for d in o["days"][-31:]:
                print(f"  {d['date']}  {d['sold']:>3}/{d['available']:<3} {d['occupancy']:>6}%  {'█' * round(d['occupancy'] / 4)}")

        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731
        self.submenu("REPORTS", [
            ("Revenue report", revenue), ("Occupancy report", occupancy),
            ("Performance report (PDF)", lambda: saved(rg.performance_pdf(*period()))),
            ("Bookings (CSV)", lambda: saved(rg.bookings_csv(*period()))),
            ("Customers (CSV)", lambda: saved(rg.customers_csv())),
            ("Daily revenue (CSV)", lambda: saved(rg.revenue_csv(*period()))),
            ("Daily occupancy (CSV)", lambda: saved(rg.occupancy_csv(*period())))])

    # --------------------------------------------------------------- staff
    def staff_menu(self) -> None:
        require(self.user, "staff")
        sm = StaffManager(self.db, self.actor)

        def listing():
            print(f"  {'Username':<13}{'Name':<20}{'Role':<14}{'Shift':<17}{'Salary':>11}  Status")
            line()
            for s in sm.list():
                state = "active" if s["active"] else "inactive"
                if s["failed_attempts"] >= 5:
                    state = "LOCKED"
                print(f"  {s['username']:<13}{s['name'][:19]:<20}{s['role']:<14}{s['shift']:<17}"
                      f"{money(s['salary']):>11}  {state}")
            print(f"\n  Monthly staff salary bill: {money(sm.payroll_total())}")

        def add():
            s, temp = sm.add(ask("Username"), ask("Full name"), choose("Role", ROLES), ask("Phone"), ask("Email"),
                             choose("Shift", SHIFTS), ask("Monthly salary", "0"))
            print(f"  ✔ {s['name']} added. Login {s['username']} / temporary password {temp}")

        def update():
            s = sm.get(ask("Username"))
            changes = {"name": ask("Name", s["name"]), "phone": ask("Phone", s["phone"]),
                       "salary": ask("Salary", f"{s['salary']:.0f}")}
            if confirm("Change role?"):
                changes["role"] = choose("Role", ROLES)
            if confirm("Change shift?"):
                changes["shift"] = choose("Shift", SHIFTS)
            sm.update(s["username"], **changes)
            print("  ✔ Updated.")

        def toggle():
            s = sm.get(ask("Username"))
            sm.set_active(s["username"], not s["active"])
            print(f"  ✔ {s['username']} is now {'inactive' if s['active'] else 'active'}.")

        def reset():
            name = ask("Username")
            print(f"  ✔ Temporary password for {name}: {self.auth.reset_password(name, self.actor)} (account unlocked)")
        self.submenu("STAFF MANAGEMENT", [("List staff", listing), ("Add staff", add), ("Update staff", update),
                                          ("Activate / deactivate", toggle), ("Reset password / unlock", reset)])

    # --------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        require(self.user, "admin")
        panel = AdminPanel(self.db)

        def log():
            who = ask("Filter by user (blank = all)") or None
            for a in panel.activity(40, who):
                print(f"  {a['at'].replace('T', ' ')}  {a['user']:<12}{a['action']:<20}{a['details']}")

        def restore():
            backups = self.backup.list_backups()
            for i, b in enumerate(backups, 1):
                print(f"  {i:>2}. {b.name}")
            n = ask("Backup number to restore")
            if n.isdigit() and 1 <= int(n) <= len(backups) and confirm("Replace ALL current data?"):
                safety = self.backup.restore(backups[int(n) - 1])
                print(f"  ✔ Restored. Previous data saved as {safety.name}. Please log in again.")
                self.user = None
        self.submenu("ADMIN PANEL", [
            ("Activity log", log),
            ("System statistics", lambda: [print(f"  {k:<12}{v:>6} record(s)") for k, v in panel.system_stats().items()]),
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}" for b in self.backup.list_backups()) or "  None.")),
            ("Restore backup", restore)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except HotelError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
