"""Menu-driven interface: staff portal (admin / librarian / assistant) and member portal."""
from __future__ import annotations

import getpass
import sys
from datetime import date, timedelta

from . import utils
from .admin import AdminPanel
from .auth import AuthManager, UserManager, can
from .backup import BackupManager
from .books import BookManager
from .circulation import CirculationManager
from .database import JSONDatabase
from .fines import FineManager
from .librarian import LibrarianDesk
from .members import MemberManager
from .qr import save_qr_png
from .reports import ReportGenerator
from .reservations import ReservationManager
from .utils import (CATEGORIES, LANGUAGES, LIBRARY_NAME, MEMBER_TYPES, PAYMENT_MODES, STAFF_ROLES, LibraryError,
                    money)

W = 84


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


def choose(prompt: str, options: list, allow_blank: bool = False) -> str:
    options = [str(o) for o in options]
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


def period() -> tuple[str, str]:
    return ask("From YYYY-MM-DD", (date.today() - timedelta(days=30)).isoformat()), \
        ask("To YYYY-MM-DD", date.today().isoformat())


def print_books(rows: list[dict]) -> None:
    if not rows:
        print("  No books found.")
        return
    print(f"  {'ID':<7}{'Title':<38}{'Author(s)':<22}{'Shelf':<8}{'Avail':>5}")
    line()
    for b in rows:
        ref = " (ref)" if b["reference_only"] else ""
        print(f"  {b['book_id']:<7}{(b['title'] + ref)[:37]:<38}{b['authors'][:21]:<22}{b['shelf']:<8}{b.get('available', ''):>5}")
    line()
    print(f"  {len(rows)} title(s)")


def print_loans(loans: list[dict], show_member: bool = False) -> None:
    if not loans:
        print("  No loans.")
        return
    today = date.today().isoformat()
    for l in loans:
        flag = "  OVERDUE" if l["status"] == "ISSUED" and l["due_on"] < today else ""
        who = f"{l['member_id']} {l['member_name'][:16]:<17}" if show_member else ""
        print(f"  {l['loan_id']:<8}{l['accession']:<10}{who}{l['title'][:30]:<31}due {l['due_on']}  "
              f"{l['status']}{flag}" + (f"  ren {l['renewals']}" if l["renewals"] else ""))


def print_fines(fines: list[dict]) -> None:
    if not fines:
        print("  No fines.")
        return
    for f in fines:
        print(f"  {f['fine_id']:<8}{f['created_on']:<12}{f['type']:<9}{money(f['amount']):>11}  paid {money(f['paid']):>10}"
              f"  bal {money(FineManager.balance(f)):>10}  {f['status']:<8}{f['note'][:24]}")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)                 # data loaded automatically at start-up
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = report_dir or utils.REPORT_DIR
        self.user: dict | None = None

    @property
    def actor(self) -> str:
        return self.user["username"] if self.user else "system"

    def books(self):
        return BookManager(self.db, self.actor)

    def members(self):
        return MemberManager(self.db, self.actor)

    def circ(self):
        return CirculationManager(self.db, self.actor)

    def res(self):
        return ReservationManager(self.db, self.actor)

    def fines(self):
        return FineManager(self.db, self.actor)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(LIBRARY_NAME.upper(), ["Login (staff or member)", "Search the catalogue"], "Exit")
            try:
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.catalogue_search()
                    pause()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except LibraryError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def login(self) -> None:
        header("LOGIN")
        print("  Staff: your username.  Members: your member ID (e.g. M0001).")
        self.user = self.auth.login(ask("Username / member ID"), getpass.getpass("  Password: "))
        if self.user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one.")
            while True:
                try:
                    self.change_password()
                    break
                except LibraryError as exc:
                    print(f"  ✖ {exc}")
        print(f"\n  Welcome, {self.user['name']}!")
        if self.user["role"] == "member":
            self.member_portal()
        else:
            expired = self.res().expire_holds()
            if expired:
                print(f"  {len(expired)} uncollected hold(s) expired and passed to the next member.")
            self.staff_portal()

    def loop(self, title: str, items: list[tuple]) -> None:
        """items: (label, handler, permission or None, is_submenu)"""
        items = [i for i in items if i[2] is None or can(self.user, i[2])]
        while self.user:
            choice = menu(title, [i[0] for i in items], "Logout")
            if choice == "0":
                print("  Logged out.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(items)):
                continue
            _, handler, _, sub = items[int(choice) - 1]
            try:
                handler()
            except LibraryError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            if not sub:
                pause()

    def submenu(self, title: str, options: list[tuple]) -> None:
        options = [o for o in options if len(o) < 3 or can(self.user, o[2])]
        while self.user:
            choice = menu(title, [o[0] for o in options])
            if choice == "0":
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(options)):
                continue
            try:
                options[int(choice) - 1][1]()
            except LibraryError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.actor, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    def catalogue_search(self) -> None:
        header("CATALOGUE SEARCH")
        kw = ask("Title, author, ISBN, publisher or keyword")
        cat = choose("Category (blank = all)", CATEGORIES, allow_blank=True) or None
        print_books(self.books().search(kw, cat, confirm("Only books on the shelf now?")))

    # ============================================================ pickers
    def pick_member(self) -> dict:
        q = ask("Member ID, name, phone or roll number (or scanned card code)")
        q = q.replace("LIB-MEMBER:", "")
        try:
            return self.members().get(q)
        except LibraryError:
            pass
        matches = self.members().search(q)
        if not matches:
            raise LibraryError(f"No member matches '{q}'.")
        if len(matches) == 1:
            return matches[0]
        for i, m in enumerate(matches[:15], 1):
            print(f"   {i:>2}. {m['member_id']}  {m['name']:<24}{m['type']:<9}{m['phone']}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= min(len(matches), 15)):
            raise LibraryError("Invalid selection.")
        return matches[int(n) - 1]

    def pick_book(self, prompt: str = "Book ID, ISBN, accession or title") -> dict:
        q = ask(prompt)
        try:
            return self.books().get(q)
        except LibraryError:
            pass
        matches = self.books().search(q)
        if not matches:
            raise LibraryError(f"No book matches '{q}'.")
        if len(matches) == 1:
            return matches[0]
        for i, b in enumerate(matches[:15], 1):
            print(f"   {i:>2}. {b['book_id']}  {b['title'][:40]:<41}{b['authors'][:20]:<21}avail {b['available']}")
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= min(len(matches), 15)):
            raise LibraryError("Invalid selection.")
        return matches[int(n) - 1]

    # ======================================================== staff portal
    def staff_portal(self) -> None:
        self.desk()
        self.loop(f"{LIBRARY_NAME} — {self.user['name']} ({self.user['role']})", [
            ("Desk dashboard", self.desk, "desk", False),
            ("Issue & return", self.circulation_menu, "circulation", True),
            ("Reservations", self.reservation_menu, "reservations", True),
            ("Books", self.book_menu, "books", True),
            ("Members", self.member_menu, "members", True),
            ("Fines", self.fine_menu, "fines", True),
            ("Reports", self.report_menu, "reports", True),
            ("Admin panel (statistics, staff, activity log, backup)", self.admin_menu, "admin", True),
            ("Change password", self.change_password, None, False)])

    def desk(self) -> None:
        d = LibrarianDesk(self.db).dashboard()
        header(f"CIRCULATION DESK — {d['date']}")
        print(f"  Issued today {d['issued_today']} · returned today {d['returned_today']} · on loan {d['on_loan']}")
        print(f"  Due today {len(d['due_today'])} · due in next 3 days {len(d['due_next_3_days'])} · "
              f"OVERDUE {len(d['overdue'])}")
        print(f"  Holds ready for pickup {len(d['holds_ready'])} · reservations waiting {d['waiting']}")
        print(f"  Fines collected today {money(d['fines_collected_today'])} · outstanding {money(d['fines_outstanding'])}")
        print(f"  Memberships expiring within 30 days: {len(d['expiring_members'])}")
        if d["overdue"]:
            print("\n  Most overdue:")
            for l in d["overdue"][:5]:
                print(f"   {l['accession']:<10}{l['title'][:30]:<31}{l['member_name'][:18]:<19}"
                      f"{l['days_overdue']:>3} days  {money(l['fine_so_far'])}")
        if d["holds_ready"]:
            print("\n  Holds ready:")
            for r in d["holds_ready"][:5]:
                print(f"   {r['accession']:<10}{r['title'][:30]:<31}for {r['member_id']}  until {r['hold_until']}")

    # ---------------------------------------------------------- circulation
    def circulation_menu(self) -> None:
        self.submenu("ISSUE & RETURN", [
            ("Issue book", self.issue), ("Return book", self.return_book), ("Renew loan", self.renew),
            ("Report lost book", self.lost), ("Reprint issue slip (PDF)", self.slip),
            ("A member's loans", lambda: print_loans(self.circ().loans(self.pick_member()["member_id"]))),
            ("All books on loan", lambda: print_loans(self.circ().loans(status="ISSUED"), show_member=True)),
            ("Overdue books", self.overdue_list)])

    def issue(self) -> None:
        header("ISSUE BOOK")
        m = self.pick_member()
        e = self.members().eligibility(m["member_id"])
        print(f"  {m['name']} ({m['type']}) — {e['loans']}/{e['limit']} books, fines {money(e['fines'])}, "
              f"valid till {m['expires_on']}")
        if not e["can_borrow"]:
            raise LibraryError("Cannot borrow: " + "; ".join(e["reasons"]) + ".")
        while True:
            ref = ask("Accession number, book ID or ISBN (blank = done)")
            if not ref:
                break
            try:
                loan = self.circ().issue(m["member_id"], ref)
                print(f"  ✔ {loan['title']} ({loan['accession']}) issued — due {loan['due_on']}  [{loan['loan_id']}]")
                if confirm("Print issue slip?"):
                    print(f"  ✔ Saved: {self.circ().issue_slip_pdf(loan['loan_id'], self.report_dir / 'slips')}")
            except LibraryError as exc:
                print(f"  ✖ {exc}")

    def return_book(self) -> None:
        header("RETURN BOOK")
        ref = ask("Accession number or loan ID")
        loan = self.circ().get(ref)
        days, fine = self.circ().overdue_fine(loan)
        print(f"  {loan['title']} — borrowed by {loan['member_name']} ({loan['member_id']}), due {loan['due_on']}")
        if days:
            print(f"  ⚠ {days} day(s) late — fine {money(fine)}")
        damaged = confirm("Is the book damaged?")
        fee = ask("Damage fee", "0") if damaged else 0
        r = self.circ().return_book(loan["loan_id"], damaged=damaged, damage_fee=fee,
                                    note=ask("Note (optional)") if damaged else "")
        print(f"  ✔ Returned." + (f" Fine raised: {money(r['fine'])}." if r["fine"] else " No fine."))
        if r["hold_for"]:
            print(f"  ➜ Put this copy on the HOLD shelf for {r['hold_for']['member_id']} "
                  f"(reservation {r['hold_for']['res_id']}, until {r['hold_for']['hold_until']}).")
        if r["fine"] and confirm("Collect the fine now?"):
            self._collect(loan["member_id"])

    def renew(self) -> None:
        loan = self.circ().renew(ask("Accession number or loan ID"))
        print(f"  ✔ Renewed — new due date {loan['due_on']} (renewal {loan['renewals']} of {utils.MAX_RENEWALS}).")

    def lost(self) -> None:
        loan = self.circ().get(ask("Accession number or loan ID"))
        price = self.books().get(loan["book_id"])["price"]
        if confirm(f"Mark '{loan['title']}' as lost by {loan['member_name']}? Charge {money(price + utils.LOST_PROCESSING_FEE)}"):
            l = self.circ().mark_lost(loan["loan_id"])
            print(f"  ✔ Recorded as lost. Fine raised: {money(l['fine'])}.")

    def slip(self) -> None:
        print(f"  ✔ Saved: {self.circ().issue_slip_pdf(ask('Loan ID or accession'), self.report_dir / 'slips')}")

    def overdue_list(self) -> None:
        rows = self.circ().overdue()
        if not rows:
            print("  No overdue books.")
        for l in rows:
            print(f"  {l['accession']:<10}{l['title'][:28]:<29}{l['member_id']} {l['member_name'][:16]:<17}"
                  f"due {l['due_on']}  {l['days_overdue']:>3} days  {money(l['fine_so_far'])}")

    # --------------------------------------------------------- reservations
    def reservation_menu(self) -> None:
        def reserve():
            m = self.pick_member()
            r = self.res().reserve(m["member_id"], self.pick_book()["book_id"])
            msg = f"ready now on copy {r['accession']} (hold until {r['hold_until']})" if r["status"] == "READY" \
                else f"position {self.res().position(r['res_id'])} in the queue"
            print(f"  ✔ Reservation {r['res_id']} for {m['name']} — {msg}.")

        def queue():
            b = self.pick_book()
            q = self.res().queue(b["book_id"])
            ready = self.res().list(status="READY", book_id=b["book_id"])
            print(f"  {b['title']}: {self.books().availability(b['book_id'])}")
            for r in ready:
                print(f"   READY    {r['res_id']}  {r['member_id']}  copy {r['accession']} until {r['hold_until']}")
            for i, r in enumerate(q, 1):
                print(f"   #{i:<7} {r['res_id']}  {r['member_id']}  reserved {r['reserved_on']}")

        def ready():
            for r in self.res().list(status="READY"):
                print(f"  {r['res_id']}  {r['accession']:<10}{r['title'][:32]:<33}{r['member_id']}  until {r['hold_until']}")

        self.submenu("RESERVATIONS", [
            ("Reserve a book for a member", reserve), ("Queue for a title", queue), ("Holds ready for pickup", ready),
            ("Cancel a reservation", lambda: (self.res().cancel(ask("Reservation ID")), print("  ✔ Cancelled."))),
            ("Expire uncollected holds now", lambda: print(f"  ✔ {len(self.res().expire_holds())} hold(s) expired."))])

    # ----------------------------------------------------------------- books
    def book_menu(self) -> None:
        self.submenu("BOOKS", [
            ("Search catalogue", self.catalogue_search), ("Book details & copies", self.book_details),
            ("Add book", self.add_book, "books.manage"), ("Edit book", self.edit_book, "books.manage"),
            ("Add copies", self.add_copies, "books.manage"),
            ("Withdraw a copy", lambda: (self.books().withdraw_copy(ask("Accession"), ask("Reason")),
                                         print("  ✔ Copy withdrawn.")), "books.manage"),
            ("Mark copy damaged / repaired", lambda: (self.books().set_copy_status(
                ask("Accession"), choose("New status", ["DAMAGED", "AVAILABLE"]), ask("Note")), print("  ✔ Updated.")),
             "books.manage"),
            ("Delete book (no history only)", lambda: (self.books().delete(self.pick_book()["book_id"]),
                                                       print("  ✔ Deleted.")), "books.manage")])

    def book_details(self) -> None:
        b = self.pick_book()
        header(f"{b['book_id']} — {b['title']}")
        for label, key in [("Author(s)", "authors"), ("ISBN", "isbn"), ("Publisher", "publisher"), ("Year", "year"),
                           ("Edition", "edition"), ("Category", "category"), ("Language", "language"),
                           ("Shelf", "shelf"), ("Keywords", "keywords")]:
            print(f"  {label:<12}: {b[key] or '-'}")
        print(f"  {'Price':<12}: {money(b['price'])}" + ("   REFERENCE ONLY" if b["reference_only"] else ""))
        a = self.books().availability(b["book_id"])
        print(f"\n  Copies: {a['total']} in collection · {a['available']} available · {a['issued']} issued · "
              f"{a['on_hold']} on hold · {a['damaged']} damaged · {a['lost']} lost")
        loans = {l["accession"]: l for l in self.circ().loans(status="ISSUED")}
        for c in self.books().copies(b["book_id"]):
            extra = f"with {loans[c['accession']]['member_id']} until {loans[c['accession']]['due_on']}" \
                if c["accession"] in loans else (f"held for {c['hold_for']} until {c['hold_until']}" if c["hold_for"] else c["note"])
            print(f"   {c['accession']:<10}{c['status']:<11}{extra}")
        q = self.res().queue(b["book_id"])
        if q:
            print(f"\n  Reservation queue: {len(q)} waiting")

    def add_book(self) -> None:
        header("ADD BOOK")
        isbn = ask("ISBN (10 or 13 digits, optional)")
        b = self.books().add(ask("Title"), ask("Author(s)"), choose("Category", CATEGORIES), ask("Price"),
                             ask("Number of copies", "1"), isbn, ask("Publisher"), ask("Year"), ask("Edition"),
                             choose("Language", LANGUAGES), ask("Shelf / rack"), ask("Keywords"),
                             confirm("Reference only (not for lending)?"))
        print(f"  ✔ Added {b['book_id']} with copies {', '.join(c['accession'] for c in self.books().copies(b['book_id']))}.")

    def edit_book(self) -> None:
        b = self.pick_book()
        print("  Leave blank to keep the current value.")
        changes = {}
        for key, label in [("title", "Title"), ("authors", "Author(s)"), ("isbn", "ISBN"), ("publisher", "Publisher"),
                           ("year", "Year"), ("edition", "Edition"), ("price", "Price"), ("shelf", "Shelf"),
                           ("keywords", "Keywords")]:
            cur = "" if b[key] is None else str(b[key])
            v = ask(label, cur or None)
            if v != cur and v:
                changes[key] = v
        if confirm("Change category?"):
            changes["category"] = choose("Category", CATEGORIES)
        if not changes:
            print("  No changes.")
            return
        self.books().update(b["book_id"], **changes)
        print(f"  ✔ Updated: {', '.join(changes)}.")

    def add_copies(self) -> None:
        b = self.pick_book()
        cs = self.books().add_copies(b["book_id"], ask("How many copies", "1"))
        print(f"  ✔ Added {', '.join(c['accession'] for c in cs)}.")
        held = self.res().allocate(b["book_id"])
        for r in held:
            print(f"  ➜ {r['accession']} held for {r['member_id']} (reservation {r['res_id']}).")

    # ---------------------------------------------------------------- members
    def member_menu(self) -> None:
        self.submenu("MEMBERS", [
            ("Register member", self.register_member, "members.manage"), ("Search members", self.search_members),
            ("Member details", self.member_details), ("Update member", self.update_member, "members.manage"),
            ("Renew membership", lambda: print(f"  ✔ Valid till {self.members().renew(self.pick_member()['member_id'])['expires_on']}."),
             "members.manage"),
            ("Suspend member", lambda: (self.members().suspend(self.pick_member()["member_id"], ask("Reason")),
                                        print("  ✔ Suspended.")), "members.manage"),
            ("Reactivate member", lambda: (self.members().reactivate(self.pick_member()["member_id"]),
                                           print("  ✔ Reactivated.")), "members.manage"),
            ("Close membership", lambda: (self.members().close(self.pick_member()["member_id"]),
                                          print("  ✔ Membership closed.")), "members.manage"),
            ("Print member card (PDF with QR)", self.member_card),
            ("Reset member's portal password", lambda: print(
                f"  ✔ Temporary password: {self.auth.reset_password(self.pick_member()['member_id'], self.actor)}"),
             "members.manage")])

    def register_member(self) -> None:
        header("REGISTER MEMBER")
        print("  Types: " + " · ".join(f"{t} ({r['max_books']} books, {r['loan_days']} days, fee {money(r['fee'])})"
                                       for t, r in MEMBER_TYPES.items()))
        mtype = choose("Member type", list(MEMBER_TYPES))
        m, temp = self.members().add(ask("Full name"), mtype, ask("Mobile number"), ask("Email (optional)"),
                                     ask("Address"), ask("Roll / employee / ID number"), ask("Department / class"))
        print(f"\n  ✔ Registered {m['member_id']} — valid till {m['expires_on']}. Fee collected {money(m['fee_paid'])}.")
        print(f"    Portal login: {m['member_id']}   Temporary password: {temp}")
        if confirm("Print membership card?"):
            print(f"  ✔ Saved: {self.members().card_pdf(m['member_id'], self.report_dir / 'cards')}")

    def search_members(self) -> None:
        for m in self.members().search(ask("Keyword (blank = all)")):
            print(f"  {m['member_id']:<7}{m['name'][:24]:<25}{m['type']:<9}{m['phone']:<12}"
                  f"{MemberManager.effective_status(m):<10}till {m['expires_on']}")

    def member_details(self) -> None:
        m = self.pick_member()
        e = self.members().eligibility(m["member_id"])
        header(f"{m['member_id']} — {m['name']} ({m['type']})")
        print(f"  {m['phone']} · {m['email'] or '-'} · {m['id_number'] or '-'} · {m['department'] or '-'}")
        print(f"  Joined {m['joined_on']} · valid till {m['expires_on']} · status {e['status']}")
        print(f"  Books {e['loans']}/{e['limit']} · overdue {e['overdue']} · fines due {money(e['fines'])} · "
              + ("CAN BORROW" if e["can_borrow"] else "BLOCKED: " + "; ".join(e["reasons"])))
        print("\n  Current loans:")
        print_loans([l for l in self.circ().loans(m["member_id"]) if l["status"] == "ISSUED"])
        rs = [r for r in self.res().list(m["member_id"]) if r["status"] in ("WAITING", "READY")]
        if rs:
            print("\n  Reservations:")
            for r in rs:
                print(f"   {r['res_id']} {r['title'][:36]:<37}{r['status']}"
                      + (f" until {r['hold_until']}" if r["status"] == "READY" else f" #{self.res().position(r['res_id'])}"))
        print("\n  Outstanding fines:")
        print_fines(self.fines().outstanding_fines(m["member_id"]))

    def update_member(self) -> None:
        m = self.pick_member()
        print("  Leave blank to keep the current value.")
        changes = {k: ask(label, m[k] or None) for k, label in
                   [("name", "Name"), ("phone", "Phone"), ("email", "Email"), ("address", "Address"),
                    ("department", "Department")]}
        changes = {k: v for k, v in changes.items() if v != (m[k] or "")}
        if confirm("Change member type?"):
            changes["type"] = choose("Type", list(MEMBER_TYPES))
        if changes:
            self.members().update(m["member_id"], **changes)
            print("  ✔ Updated.")

    def member_card(self) -> None:
        m = self.pick_member()
        print(f"  ✔ Saved: {self.members().card_pdf(m['member_id'], self.report_dir / 'cards')}")
        if confirm("Also save the QR code as a PNG image?"):
            print(f"  ✔ Saved: {save_qr_png('LIB-MEMBER:' + m['member_id'], self.report_dir / 'cards' / (m['member_id'] + '.png'))}")

    # ------------------------------------------------------------------ fines
    def _collect(self, member_id: str) -> None:
        due = self.fines().outstanding(member_id)
        mode = choose("Payment mode", PAYMENT_MODES)
        ref = ask("Transaction reference") if mode != "Cash" else ""
        paid = self.fines().pay_all(member_id, mode, ref)
        print(f"  ✔ Collected {money(paid)} of {money(due)}.")

    def fine_menu(self) -> None:
        def member_fines():
            m = self.pick_member()
            print_fines(self.fines().list(m["member_id"]))
            print(f"\n  Outstanding: {money(self.fines().outstanding(m['member_id']))}")

        def pay_one():
            f = self.fines().get(ask("Fine ID"))
            mode = choose("Payment mode", PAYMENT_MODES)
            f = self.fines().pay(f["fine_id"], ask("Amount", f"{FineManager.balance(f):.2f}"), mode,
                                 ask("Reference") if mode != "Cash" else "")
            print(f"  ✔ Receipt {f['payments'][-1]['receipt']} — status {f['status']}.")

        def waive():
            f = self.fines().waive(ask("Fine ID"), ask("Reason"), ask("Amount (blank = full balance)") or None)
            print(f"  ✔ Waived. Status {f['status']}.")
        self.submenu("FINES", [
            ("A member's fines", member_fines), ("Collect all dues from a member", lambda: self._collect(self.pick_member()["member_id"])),
            ("Pay a single fine", pay_one), ("Waive a fine", waive, "fines.waive"),
            ("All unpaid fines", lambda: print_fines([f for f in self.fines().list() if FineManager.balance(f) > 0]))])

    # ---------------------------------------------------------------- reports
    def report_menu(self) -> None:
        rg = ReportGenerator(self.db, self.report_dir)
        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731

        def available():
            rows = rg.available_books()
            print(f"  {'ID':<7}{'Title':<40}{'Copies':>7}{'Avail':>7}{'Issued':>8}{'Hold':>6}")
            line()
            for x in rows:
                print(f"  {x['book']['book_id']:<7}{x['book']['title'][:39]:<40}{x['total']:>7}{x['available']:>7}"
                      f"{x['issued']:>8}{x['on_hold']:>6}")

        def issued():
            for l in rg.issued_books():
                late = f"{l['days_overdue']} days late {money(l['fine_so_far'])}" if l["days_overdue"] else ""
                print(f"  {l['accession']:<10}{l['title'][:30]:<31}{l['member_id']} {l['member_name'][:14]:<15}"
                      f"due {l['due_on']}  {late}")

        def popular():
            for i, p in enumerate(rg.popular_books(*period()), 1):
                print(f"  {i:>2}. {p['book']['title'][:40]:<41}{p['book']['authors'][:20]:<21}{p['issues']:>4} issues"
                      + (f"  ({p['waiting']} waiting)" if p["waiting"] else ""))

        def summary():
            s = rg.circulation_summary(*period())
            header(f"CIRCULATION {s['start']} → {s['end']}")
            print(f"  Issued {s['issued']} · returned {s['returned']} · renewals {s['renewals']} · "
                  f"late returns {s['returned_late']} · on-time {s['on_time_rate']}% · lost {s['lost']}")
            print(f"  Fines raised {money(s['fines']['raised'])} · collected {money(s['fines']['collected'])} · "
                  f"waived {money(s['fines']['waived'])}")
            print("\n  Issues by category:")
            for c, n in s["by_category"].items():
                print(f"    {c:<20}{n:>5}  {'█' * n}")
            print("\n  Issues by member type:")
            for t, n in s["by_member_type"].items():
                print(f"    {t:<20}{n:>5}")

        def reminders():
            rs = LibrarianDesk(self.db).reminders()
            for r in rs:
                print(f"  [{r['kind']}] {r['member']['phone']}: {r['message']}")
            if rs and confirm("\n  Export reminders to CSV (for SMS / email)?"):
                saved(rg.reminders_csv())

        def exports():
            self.submenu("CSV EXPORTS", [
                ("Catalogue with availability", lambda: saved(rg.catalogue_csv())),
                ("Issued books", lambda: saved(rg.issued_csv())), ("Overdue books", lambda: saved(rg.overdue_csv())),
                ("Members", lambda: saved(rg.members_csv())), ("Fines", lambda: saved(rg.fines_csv())),
                ("Daily circulation", lambda: saved(rg.circulation_csv(*period())))])
        self.submenu("REPORTS", [
            ("Available books", available), ("Issued books", issued), ("Overdue books", self.overdue_list),
            ("Most borrowed books", popular), ("Circulation summary", summary), ("Reminder notices", reminders),
            ("Available & issued books (PDF)", lambda: saved(rg.availability_pdf())),
            ("Overdue books (PDF)", lambda: saved(rg.overdue_pdf())),
            ("Circulation report (PDF)", lambda: saved(rg.circulation_pdf(*period()))),
            ("CSV exports", exports)])

    # ------------------------------------------------------------------ admin
    def admin_menu(self) -> None:
        um, panel = UserManager(self.db, self.actor), AdminPanel(self.db)

        def stats():
            s = panel.statistics()
            header("LIBRARY STATISTICS")
            print(f"  Titles {s['titles']} · copies {s['copies']} · collection value {money(s['collection_value'])}")
            print(f"  Copies by status: " + ", ".join(f"{k.lower()} {v}" for k, v in s["by_status"].items()))
            print(f"  Members {s['members']}: " + ", ".join(f"{k.lower()} {v}" for k, v in s["members_by_status"].items()))
            print(f"  Loans total {s['loans_total']} · on loan {s['loans_active']} · reservations {s['reservations_active']}")
            print(f"  Fines collected {money(s['fines_collected'])} · outstanding {money(s['fines_outstanding'])} · "
                  f"membership fees {money(s['membership_fees'])}")
            print("\n  Titles by category:")
            for c, n in s["by_category"].items():
                print(f"    {c:<20}{n:>4}")

        def staff():
            for u in um.list():
                state = "LOCKED" if u["failed_attempts"] >= 5 else ("active" if u["active"] else "inactive")
                print(f"  {u['username']:<14}{u['name'][:22]:<23}{u['role']:<11}{state:<9}"
                      f"last login {(u['last_login'] or '-').replace('T', ' ')}")

        def add_staff():
            u, temp = um.add(ask("Username"), ask("Full name"), choose("Role", STAFF_ROLES), ask("Phone (optional)"),
                             ask("Email (optional)"))
            print(f"  ✔ {u['username']} created. Temporary password: {temp}")

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
            ("Library statistics", stats), ("Staff accounts", staff), ("Add staff account", add_staff),
            ("Change staff role", lambda: (um.set_role(ask("Username"), choose("Role", STAFF_ROLES)), print("  ✔ Updated."))),
            ("Activate / deactivate staff", lambda: (lambda u: (um.set_active(u["username"], not u["active"]),
                                                                print("  ✔ Done.")))(um.get(ask("Username")))),
            ("Reset staff password / unlock", lambda: print(f"  ✔ Temporary password: {self.auth.reset_password(ask('Username'), self.actor)}")),
            ("Activity log", lambda: [print(f"  {a['at'].replace('T', ' ')}  {a['user']:<12}{a['action']:<22}{a['details']}")
                                      for a in panel.activity(40, ask("Filter by user (blank = all)") or None)]),
            ("Record counts", lambda: [print(f"  {k:<14}{v:>7}") for k, v in panel.record_counts().items()]),
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}" for b in self.backup.list_backups()) or "  None.")),
            ("Restore backup", restore)])

    # ========================================================= member portal
    def member_portal(self) -> None:
        me = self.user["member_id"]

        def my_loans():
            loans = [l for l in self.circ().loans(me) if l["status"] == "ISSUED"]
            print_loans(loans)
            for l in loans:
                days, fine = self.circ().overdue_fine(l)
                if days:
                    print(f"  ⚠ {l['title']}: {days} day(s) overdue, fine so far {money(fine)}")

        def renew():
            loans = [l for l in self.circ().loans(me) if l["status"] == "ISSUED"]
            print_loans(loans)
            if loans:
                l = self.circ().renew(ask("Accession or loan ID to renew"), by_member=me)
                print(f"  ✔ Renewed — new due date {l['due_on']}.")

        def reserve():
            rows = self.books().search(ask("Search title / author"))
            print_books(rows)
            if rows:
                r = self.res().reserve(me, ask("Book ID to reserve"))
                print(f"  ✔ Reserved ({r['res_id']}). " + (f"Ready for pickup until {r['hold_until']}." if r["status"] == "READY"
                                                           else f"You are #{self.res().position(r['res_id'])} in the queue."))

        def my_res():
            rs = self.res().list(me)
            for r in rs:
                extra = f" #{self.res().position(r['res_id'])} in queue" if r["status"] == "WAITING" else \
                    (f" — collect by {r['hold_until']}" if r["status"] == "READY" else "")
                print(f"  {r['res_id']}  {r['title'][:40]:<41}{r['status']}{extra}")
            if any(r["status"] in ("WAITING", "READY") for r in rs) and confirm("Cancel a reservation?"):
                self.res().cancel(ask("Reservation ID"), by_member=me)
                print("  ✔ Cancelled.")

        def profile():
            e = self.members().eligibility(me)
            m = e["member"]
            print(f"  {m['name']} ({m['member_id']}) · {m['type']} · valid till {m['expires_on']} · {e['status']}")
            print(f"  Borrowing: {e['loans']} of {e['limit']} books · fines due {money(e['fines'])}")
            if not e["can_borrow"]:
                print("  ⚠ " + "; ".join(e["reasons"]))
            if confirm("Download your membership card (PDF)?"):
                print(f"  ✔ Saved: {self.members().card_pdf(me, self.report_dir / 'cards')}")

        def history():
            print_loans(self.circ().loans(me))
        self.loop(f"MEMBER PORTAL — {self.user['name']} ({me})", [
            ("Search the catalogue", self.catalogue_search, None, False), ("My books & due dates", my_loans, None, False),
            ("Renew a book", renew, None, False), ("Reserve a book", reserve, None, False),
            ("My reservations", my_res, None, False),
            ("My fines", lambda: print_fines(self.fines().list(me)), None, False),
            ("Borrowing history", history, None, False), ("My profile & membership card", profile, None, False),
            ("Change password", self.change_password, None, False)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except LibraryError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
