"""Menu-driven command-line interface."""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

from . import utils
from .admin import AdminManager
from .auth import AuthManager
from .backup import BackupManager
from .contacts import SORT_KEYS, ContactManager
from .database import JSONDatabase
from .models import Contact, User
from .reports import ReportGenerator, export_users_report
from .utils import APP_NAME, ContactBookError, DuplicateError, NotFoundError

W = 74


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


def print_contacts(contacts: list[Contact], numbered: bool = False) -> None:
    if not contacts:
        print("  No contacts found.")
        return
    lead = "  #  " if numbered else "  "
    print(f"{lead}{'ID':<9}{'Name':<24}{'Phone':<17}{'Email':<24}Category")
    line()
    for i, c in enumerate(contacts, 1):
        star = "*" if c.favorite else " "
        lead = f"  {i:<3}" if numbered else "  "
        print(f"{lead}{c.id:<9}{star}{c.full_name[:22]:<23}{c.display_phone:<17}{c.email[:23]:<24}{c.category}")
    line()
    print(f"  {len(contacts)} contact(s)   (* = favourite)")


def print_contact(c: Contact) -> None:
    header(("* " if c.favorite else "") + c.full_name)
    rows = [("ID", c.id), ("Phone", c.display_phone), ("Alternate phone", c.alt_phone), ("Email", c.email),
            ("Company", c.company), ("Job title", c.job_title), ("Address", c.address), ("Birthday", c.birthday),
            ("Category", c.category), ("Favourite", "Yes" if c.favorite else "No"), ("Notes", c.notes),
            ("Created", c.created_at.replace("T", " ")), ("Updated", c.updated_at.replace("T", " "))]
    for label, value in rows:
        print(f"  {label:<16}: {value or '-'}")
    if c.birthday:
        d = utils.days_until_birthday(c.birthday)
        when = "today! 🎂" if d == 0 else f"in {d} day(s)"
        print(f"  {'':<16}  Next birthday {when} (turning {utils.age_on_next_birthday(c.birthday)})")


FIELD_PROMPTS = [("first_name", "First name *"), ("last_name", "Last name"), ("phone", "Phone *"),
                 ("alt_phone", "Alternate phone"), ("email", "Email"), ("company", "Company"),
                 ("job_title", "Job title"), ("address", "Address"), ("birthday", "Birthday YYYY-MM-DD"),
                 ("notes", "Notes")]


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = report_dir or utils.REPORT_DIR
        self.user: User | None = None

    @property
    def cm(self) -> ContactManager:
        return ContactManager(self.db, self.user.username)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(APP_NAME.upper(), ["Login", "Register"], "Exit")
            try:
                if choice == "1":
                    self.user = self.auth.login(ask("Username"), getpass.getpass("  Password: "))
                    print(f"\n  Welcome, {self.user.full_name or self.user.username}!")
                    self.birthday_reminder()
                    self.session()
                elif choice == "2":
                    header("REGISTER")
                    u = self.auth.register(ask("Username"), getpass.getpass("  Password: "),
                                           getpass.getpass("  Confirm password: "), ask("Full name (optional)"))
                    print(f"  ✔ Account '{u.username}' created. You can log in now.")
                    pause()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def birthday_reminder(self) -> None:
        soon = self.cm.upcoming_birthdays(7)
        if soon:
            print("\n  Upcoming birthdays this week:")
            for b in soon:
                when = "TODAY" if b["in_days"] == 0 else f"in {b['in_days']} day(s)"
                print(f"   • {b['contact'].full_name} — {when} (turning {b['turning']})")

    def session(self) -> None:
        actions = [("View all contacts", self.view_all), ("Add contact", self.add_contact),
                   ("Search contacts", self.search), ("Contact details", self.details),
                   ("Update contact", self.update_contact), ("Delete contact", self.delete_contact),
                   ("Favourites", self.favourites), ("Categories", self.category_menu),
                   ("Upcoming birthdays", self.birthdays), ("Recycle bin", self.recycle_bin),
                   ("Import contacts (CSV)", self.import_csv), ("Export contacts (CSV / PDF / vCard)", self.export_menu),
                   ("Statistics", self.statistics), ("Backup & Restore", self.backup_menu),
                   ("Change password", self.change_password)]
        if self.user.is_admin:
            actions.append(("Admin panel", self.admin_menu))
        submenus = (self.category_menu, self.recycle_bin, self.export_menu, self.backup_menu, self.admin_menu)
        while self.user:
            choice = menu(f"CONTACT BOOK — {self.user.username}", [a[0] for a in actions], "Logout")
            if choice == "0":
                print(f"  Logged out {self.user.username}.")
                self.user = None
                return
            if not (choice.isdigit() and 1 <= int(choice) <= len(actions)):
                continue
            handler = actions[int(choice) - 1][1]
            try:
                handler()
                if handler in submenus:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    # ------------------------------------------------------------ helpers
    def pick_contact(self, prompt: str = "Contact name, phone or ID") -> Contact:
        """Let the user identify a contact by ID or by searching."""
        query = ask(prompt)
        if not query:
            raise ContactBookError("No contact selected.")
        try:
            return self.cm.get(query)
        except NotFoundError:
            pass
        matches = self.cm.search(query)
        if not matches:
            raise NotFoundError(f"No contact matches '{query}'.")
        if len(matches) == 1:
            return matches[0]
        print_contacts(matches, numbered=True)
        n = ask("Select number")
        if not (n.isdigit() and 1 <= int(n) <= len(matches)):
            raise ContactBookError("Invalid selection.")
        return matches[int(n) - 1]

    def _save_with_duplicate_check(self, fn, **data):
        try:
            return fn(**data)
        except DuplicateError as exc:
            print(f"\n  ⚠ {exc}")
            if confirm("Save anyway?"):
                return fn(allow_duplicate=True, **data)
            raise ContactBookError("Not saved.")

    # ------------------------------------------------------------ contacts
    def view_all(self) -> None:
        sort = choose("Sort by", list(SORT_KEYS)) if confirm("Change sort order? (default A-Z)") else "name"
        header("ALL CONTACTS")
        if sort == "name":
            for letter, group in self.cm.by_letter().items():
                print(f"\n  ── {letter} ──")
                for c in group:
                    print(f"   {c.id:<9}{'*' if c.favorite else ' '}{c.full_name[:24]:<25}{c.display_phone:<17}{c.category}")
            print(f"\n  {self.cm.stats()['total']} contact(s)   (* = favourite)")
        else:
            print_contacts(self.cm.list(sort_by=sort))

    def add_contact(self) -> None:
        header("ADD CONTACT")
        print("  Fields marked * are required. Phone accepts 98765 43210, 0471 2345678 or +1 415 555 2671.")
        data = {k: ask(label) for k, label in FIELD_PROMPTS}
        data["category"] = choose("Category", self.cm.categories())
        data["favorite"] = confirm("Mark as favourite?")
        c = self._save_with_duplicate_check(self.cm.add, **data)
        print(f"  ✔ {c.full_name} saved (ID {c.id}).")

    def search(self) -> None:
        header("SEARCH CONTACTS")
        kw = ask("Keyword (name, phone digits, email, company, notes)")
        cat = choose("Category (blank = all)", self.cm.categories(), allow_blank=True) or None
        fav = confirm("Favourites only?")
        print_contacts(self.cm.search(kw, cat, fav))

    def details(self) -> None:
        print_contact(self.pick_contact())

    def update_contact(self) -> None:
        c = self.pick_contact()
        print_contact(c)
        print("\n  Enter new values; leave blank to keep. Type '-' to clear an optional field.")
        changes = {}
        for key, label in FIELD_PROMPTS:
            current = getattr(c, key)
            v = ask(label.rstrip(" *"), current or None)
            if v == "-" and key not in ("first_name", "phone"):
                changes[key] = ""
            elif v != current and v:
                changes[key] = v
        cat = choose(f"Category (blank = keep {c.category})", self.cm.categories(), allow_blank=True)
        if cat and cat != c.category:
            changes["category"] = cat
        if not changes:
            print("  No changes.")
            return
        updated = self._save_with_duplicate_check(lambda **kw: self.cm.update(c.id, **kw), **changes)
        print(f"  ✔ {updated.full_name} updated ({', '.join(changes)}).")

    def delete_contact(self) -> None:
        c = self.pick_contact()
        if confirm(f"Move {c.full_name} ({c.display_phone}) to the recycle bin?"):
            self.cm.delete(c.id)
            print("  ✔ Moved to the recycle bin. You can restore it from there.")

    def favourites(self) -> None:
        header("FAVOURITES")
        print_contacts(self.cm.list(favorites_only=True))
        if confirm("Add or remove a favourite?"):
            c = self.cm.toggle_favorite(self.pick_contact().id)
            print(f"  ✔ {c.full_name} {'added to' if c.favorite else 'removed from'} favourites.")

    def birthdays(self) -> None:
        days = ask("Show birthdays in the next how many days", str(utils.BIRTHDAY_WINDOW_DAYS))
        days = int(days) if days.isdigit() else utils.BIRTHDAY_WINDOW_DAYS
        header(f"BIRTHDAYS IN THE NEXT {days} DAYS")
        soon = self.cm.upcoming_birthdays(days)
        if not soon:
            print("  None.")
        for b in soon:
            c = b["contact"]
            when = "TODAY 🎂" if b["in_days"] == 0 else f"in {b['in_days']:>3} day(s)"
            print(f"  {c.birthday[5:]}  {c.full_name:<26}{when:<16}turning {b['turning']}   {c.display_phone}")

    # ---------------------------------------------------------- categories
    def category_menu(self) -> None:
        while True:
            choice = menu("CATEGORIES", ["List categories", "View contacts in a category", "Add category",
                                         "Rename category", "Delete category", "Change a contact's category"])
            if choice == "0":
                return
            try:
                cm = self.cm
                if choice == "1":
                    counts = cm.stats()["by_category"]
                    for cat in cm.categories():
                        print(f"  {cat:<20}{counts.get(cat, 0):>4} contact(s)")
                elif choice == "2":
                    print_contacts(cm.list(category=choose("Category", cm.categories())))
                elif choice == "3":
                    print(f"  ✔ Category '{cm.add_category(ask('New category name'))}' added.")
                elif choice == "4":
                    old = choose("Category to rename", cm.categories())
                    n = cm.rename_category(old, ask("New name"))
                    print(f"  ✔ Renamed; {n} contact(s) updated.")
                elif choice == "5":
                    cat = choose("Category to delete", cm.categories())
                    if confirm(f"Delete '{cat}'? Its contacts will move to '{utils.FALLBACK_CATEGORY}'"):
                        print(f"  ✔ Deleted; {cm.delete_category(cat)} contact(s) moved.")
                elif choice == "6":
                    c = self.pick_contact()
                    cat = choose(f"New category for {c.full_name}", cm.categories())
                    cm.update(c.id, category=cat, allow_duplicate=True)
                    print("  ✔ Category changed.")
                else:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    # --------------------------------------------------------- recycle bin
    def recycle_bin(self) -> None:
        while True:
            items = self.cm.trash()
            choice = menu(f"RECYCLE BIN ({len(items)})", ["View deleted contacts", "Restore a contact",
                                                         "Delete a contact permanently", "Empty recycle bin"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print_contacts(items)
                elif choice in ("2", "3"):
                    if not items:
                        print("  Recycle bin is empty.")
                    else:
                        print_contacts(items, numbered=True)
                        n = ask("Select number")
                        if n.isdigit() and 1 <= int(n) <= len(items):
                            c = items[int(n) - 1]
                            if choice == "2":
                                self.cm.restore(c.id)
                                print(f"  ✔ {c.full_name} restored.")
                            elif confirm(f"Permanently delete {c.full_name}? This cannot be undone"):
                                self.cm.purge(c.id)
                                print("  ✔ Deleted permanently.")
                elif choice == "4":
                    if items and confirm(f"Permanently delete all {len(items)} contact(s) in the bin?"):
                        print(f"  ✔ {self.cm.empty_trash()} contact(s) deleted permanently.")
                else:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    # ---------------------------------------------------- import / export
    def import_csv(self) -> None:
        header("IMPORT CONTACTS FROM CSV")
        print("  Required columns: First Name, Phone. Optional: Last Name, Alternate Phone, Email, Company,")
        print("  Job Title, Address, Birthday, Category, Favorite, Notes (same format as the CSV export).")
        r = self.cm.import_csv(Path(ask("Path to CSV file").strip('"')))
        print(f"\n  ✔ Imported {r['imported']} contact(s).")
        if r["skipped"]:
            print(f"  ⚠ Skipped {len(r['skipped'])} row(s):")
            for s in r["skipped"][:15]:
                print("    " + s)
            if len(r["skipped"]) > 15:
                print(f"    ... and {len(r['skipped']) - 15} more")

    def export_menu(self) -> None:
        rg = ReportGenerator(self.db, self.user.username, self.report_dir)
        while True:
            choice = menu("EXPORT CONTACTS", ["Export to CSV", "Export to PDF (directory)",
                                              "Export to vCard (.vcf for phones / Gmail / Outlook)"])
            if choice == "0":
                return
            try:
                if choice in ("1", "2", "3"):
                    cat = choose("Category (blank = all)", self.cm.categories(), allow_blank=True) or None
                    fav = confirm("Favourites only?")
                    if choice == "1":
                        path = rg.export_csv(cat, fav)
                    elif choice == "2":
                        group = "category" if confirm("Group by category? (default: A-Z)") else "letter"
                        path = rg.export_pdf(cat, fav, group)
                    else:
                        path = rg.export_vcard(cat, fav)
                    print(f"  ✔ Saved: {path}")
                else:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    def statistics(self) -> None:
        s = self.cm.stats()
        header("STATISTICS")
        print(f"  Total contacts   : {s['total']}")
        print(f"  Favourites       : {s['favorites']}")
        print(f"  With email       : {s['with_email']}")
        print(f"  With birthday    : {s['with_birthday']}")
        print(f"  In recycle bin   : {s['in_trash']}")
        if s["by_category"]:
            print("\n  By category:")
            peak = max(s["by_category"].values())
            for cat, n in s["by_category"].items():
                print(f"    {cat:<16}{n:>4}  {'█' * max(1, round(n / peak * 30))}")
        if s["top_companies"]:
            print("\n  Top companies:")
            for co, n in s["top_companies"]:
                print(f"    {co:<28}{n:>4}")

    # -------------------------------------------------------------- backup
    def backup_menu(self) -> None:
        while True:
            choice = menu("BACKUP & RESTORE", ["Create backup", "List backups", "Restore backup (admin)"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print(f"  ✔ Backup created: {self.backup.create_backup().name}")
                elif choice in ("2", "3"):
                    backups = self.backup.list_backups()
                    if not backups:
                        print("  No backups yet.")
                    for i, b in enumerate(backups, 1):
                        print(f"  {i:>2}. {b.name}  ({b.stat().st_size / 1024:.1f} KB)")
                    if choice == "3" and backups:
                        if not self.user.is_admin:
                            print("  Only an administrator can restore backups (it affects all users).")
                        else:
                            n = ask("Backup number to restore")
                            if n.isdigit() and 1 <= int(n) <= len(backups) and \
                                    confirm("Replace ALL current data with this backup?"):
                                safety = self.backup.restore(backups[int(n) - 1])
                                print(f"  ✔ Restored. Previous data saved as {safety.name}.")
                                print("  Please log in again.")
                                self.user = None
                                pause()
                                return
                else:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.user.username, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    # --------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        am = AdminManager(self.db, self.user)
        while True:
            choice = menu("ADMIN PANEL", ["List users", "System statistics", "Create user",
                                          "Activate / deactivate user", "Change user role",
                                          "Reset user password", "Delete user", "Export users report (CSV)"])
            if choice == "0":
                return
            try:
                if choice == "1":
                    print(f"  {'Username':<16}{'Name':<20}{'Role':<7}{'Active':<8}{'Contacts':>8}  Last login")
                    line()
                    for u in am.list_users():
                        print(f"  {u['username']:<16}{(u['full_name'] or '-')[:19]:<20}{u['role']:<7}"
                              f"{'yes' if u['active'] else 'no':<8}{u['contact_count']:>8}  "
                              f"{(u['last_login'] or '-').replace('T', ' ')}")
                elif choice == "2":
                    s = am.system_stats()
                    for k, v in s.items():
                        if not isinstance(v, (dict, list)):
                            print(f"  {k.replace('_', ' ').capitalize():<28}: {v}")
                    print("\n  Contacts by category:")
                    for cat, n in s["contacts_by_category"].items():
                        print(f"    {cat:<18}{n:>5}")
                    print("\n  Users with most contacts:")
                    for name, n in s["top_users"]:
                        print(f"    {name:<18}{n:>5}")
                elif choice == "3":
                    role = choose("Role", ["user", "admin"])
                    pw = getpass.getpass("  Password: ")
                    u = self.auth.register(ask("Username"), pw, pw, ask("Full name"), role)
                    print(f"  ✔ User '{u.username}' created.")
                elif choice == "4":
                    name = ask("Username")
                    am.set_active(name, confirm("Activate? (n = deactivate)"))
                    print("  ✔ Updated.")
                elif choice == "5":
                    am.set_role(ask("Username"), choose("New role", ["user", "admin"]))
                    print("  ✔ Role updated.")
                elif choice == "6":
                    am.reset_password(ask("Username"), getpass.getpass("  New password: "))
                    print("  ✔ Password reset.")
                elif choice == "7":
                    name = ask("Username")
                    if confirm(f"Delete '{name}' and ALL their contacts permanently?"):
                        self.backup.create_backup("pre_delete_user")
                        print(f"  ✔ User deleted with {am.delete_user(name)} contact(s). (Backup taken first.)")
                elif choice == "8":
                    print(f"  ✔ Saved: {export_users_report(self.db, self.report_dir)}")
                else:
                    continue
            except ContactBookError as exc:
                print(f"\n  ✖ {exc}")
            pause()


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except ContactBookError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
