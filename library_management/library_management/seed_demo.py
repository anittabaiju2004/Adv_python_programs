"""Load demo data: staff, ~35 titles, 20 members and 60 days of circulation
(late returns with fines, renewals, a lost and a damaged book, reservation
queues with a hold ready for pickup, current overdue loans).

Usage:  python seed_demo.py
Logins: admin / admin123 · librarian / lib12345 · assistant / asst1234
        members M0001 ... M0020 / member123
ISBNs in the demo data are synthetic (valid check digits, not real books' ISBNs).
"""
import random
from datetime import date, timedelta

from library import utils
from library.auth import AuthManager, UserManager
from library.books import BookManager
from library.circulation import CirculationManager
from library.database import JSONDatabase
from library.fines import FineManager
from library.members import MemberManager
from library.reservations import ReservationManager

BOOKS = [  # title, authors, category, price, copies, publisher, year
    ("Introduction to Algorithms", "Cormen, Leiserson, Rivest, Stein", "Computer Science", 1450, 3, "MIT Press", 2022),
    ("Python Crash Course", "Eric Matthes", "Computer Science", 650, 3, "No Starch Press", 2023),
    ("Clean Code", "Robert C. Martin", "Computer Science", 720, 2, "Pearson", 2008),
    ("Database System Concepts", "Silberschatz, Korth, Sudarshan", "Computer Science", 980, 2, "McGraw Hill", 2019),
    ("Operating System Concepts", "Silberschatz, Galvin, Gagne", "Computer Science", 950, 2, "Wiley", 2018),
    ("Computer Networks", "Andrew S. Tanenbaum", "Computer Science", 890, 2, "Pearson", 2021),
    ("Artificial Intelligence: A Modern Approach", "Stuart Russell, Peter Norvig", "Computer Science", 1250, 1, "Pearson", 2021),
    ("Let Us C", "Yashavant Kanetkar", "Computer Science", 420, 3, "BPB Publications", 2020),
    ("Engineering Mathematics", "B. S. Grewal", "Mathematics", 850, 3, "Khanna Publishers", 2021),
    ("Discrete Mathematics and Its Applications", "Kenneth H. Rosen", "Mathematics", 990, 2, "McGraw Hill", 2019),
    ("Concepts of Physics Vol 1", "H. C. Verma", "Science", 480, 2, "Bharati Bhawan", 2022),
    ("Basic Electrical Engineering", "D. P. Kothari, I. J. Nagrath", "Engineering", 560, 2, "McGraw Hill", 2019),
    ("Strength of Materials", "R. K. Bansal", "Engineering", 640, 1, "Laxmi Publications", 2018),
    ("Principles of Marketing", "Philip Kotler, Gary Armstrong", "Management", 880, 1, "Pearson", 2020),
    ("The Lean Startup", "Eric Ries", "Management", 499, 1, "Crown Business", 2011),
    ("Atomic Habits", "James Clear", "Self-Help", 450, 2, "Penguin Random House", 2018),
    ("Wings of Fire", "A. P. J. Abdul Kalam", "Literature", 350, 2, "Universities Press", 1999),
    ("The God of Small Things", "Arundhati Roy", "Fiction", 399, 2, "Penguin India", 1997),
    ("To Kill a Mockingbird", "Harper Lee", "Fiction", 350, 1, "Harper Perennial", 1960),
    ("1984", "George Orwell", "Fiction", 299, 2, "Penguin Classics", 1949),
    ("The Alchemist", "Paulo Coelho", "Fiction", 299, 2, "HarperCollins", 1988),
    ("Randamoozham", "M. T. Vasudevan Nair", "Malayalam", 380, 2, "Current Books", 1984),
    ("Khasakkinte Itihasam", "O. V. Vijayan", "Malayalam", 320, 1, "DC Books", 1969),
    ("Balyakalasakhi", "Vaikom Muhammad Basheer", "Malayalam", 180, 2, "DC Books", 1944),
    ("Sapiens", "Yuval Noah Harari", "History", 599, 1, "Harper", 2014),
    ("India After Gandhi", "Ramachandra Guha", "History", 799, 1, "Picador", 2007),
    ("A Brief History of Time", "Stephen Hawking", "Science", 399, 1, "Bantam", 1988),
    ("Harry Potter and the Philosopher's Stone", "J. K. Rowling", "Children", 399, 2, "Bloomsbury", 1997),
    ("Panchatantra Stories", "Vishnu Sharma", "Children", 150, 2, "Amar Chitra Katha", 2010),
    ("Oxford Advanced Learner's Dictionary", "A. S. Hornby", "Reference", 950, 1, "Oxford", 2020),
    ("Encyclopaedia of Indian History", "Various", "Reference", 1800, 1, "Penguin", 2015),
]
MEMBERS = [  # name, type, id_number, department
    ("Anitta Joseph", "Student", "CS21001", "B.Tech CSE"), ("Rahul Menon", "Student", "CS21014", "B.Tech CSE"),
    ("Priya Nair", "Student", "EC21007", "B.Tech ECE"), ("Arjun Das", "Student", "ME22003", "B.Tech Mech"),
    ("Fathima Rasheed", "Student", "CS22019", "B.Tech CSE"), ("Akhil Krishnan", "Student", "MBA23005", "MBA"),
    ("Sneha George", "Student", "CS23021", "MCA"), ("Nikhil Raj", "Student", "EE22011", "B.Tech EEE"),
    ("Divya Mathew", "Student", "CE21030", "B.Tech Civil"), ("Reshma Thomas", "Student", "CS23002", "MCA"),
    ("Dr. Thomas Kurian", "Faculty", "FAC101", "Computer Science"), ("Dr. Meera Pillai", "Faculty", "FAC118", "Mathematics"),
    ("Prof. Vishnu Varma", "Faculty", "FAC124", "Electronics"), ("Lakshmi Iyer", "Staff", "STF045", "Accounts"),
    ("Sreejith Babu", "Staff", "STF052", "Lab"), ("Joseph Mathew", "Public", "", ""),
    ("Aswathy Nair", "Public", "", ""), ("Kiran Kumar", "Public", "", ""), ("Neha Sharma", "Student", "CS24008", "MCA"),
    ("Varun Gupta", "Faculty", "FAC131", "Management"),
]


def synthetic_isbn(rng) -> str:
    core = "978" + "".join(str(rng.randint(0, 9)) for _ in range(9))
    check = (10 - sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core)) % 10) % 10
    return core + str(check)


def main():
    rng = random.Random(23)
    db = JSONDatabase(utils.DATA_DIR)
    if db.all("books"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    um = UserManager(db, "admin")
    for u, name, role, pw in [("librarian", "Sumathi Devi", "librarian", "lib12345"),
                              ("assistant", "Ajay Kumar", "assistant", "asst1234")]:
        _, t = um.add(u, name, role)
        auth.change_password(u, t, pw, pw)

    today = date.today()
    start = today - timedelta(days=60)
    bm = BookManager(db, "librarian")
    books = []
    for i, (title, authors, cat, price, copies, pub, year) in enumerate(BOOKS):
        books.append(bm.add(title, authors, cat, price, copies, synthetic_isbn(rng), pub, year, "",
                            "Malayalam" if cat == "Malayalam" else "English", f"{cat[:2].upper()}-{rng.randint(1, 20):02d}",
                            reference_only=(cat == "Reference")))
    mm = MemberManager(db, "librarian")
    members = []
    for i, (name, mtype, idn, dept) in enumerate(MEMBERS):
        joined = start - timedelta(days=rng.randint(30, 300))
        m, t = mm.add(name, mtype, f"9{rng.randint(100000000, 999999999)}",
                      f"{name.split()[-1].lower()}{i}@example.com", rng.choice(["Kazhakkoottam", "Sreekaryam", "Pattom"]),
                      idn, dept, on=joined)
        auth.change_password(m["member_id"], t, "member123", "member123")
        members.append(m)

    circ, fines, res = CirculationManager(db, "assistant"), FineManager(db, "assistant"), ReservationManager(db, "librarian")
    lendable = [b for b in books if not b["reference_only"]]
    plans = {}          # loan_id -> (return day offset or None, renew?)
    for offset in range(0, 60):
        day = start + timedelta(days=offset)
        if day.weekday() == 6:
            continue
        # returns planned for today
        for loan_id, (ret_day, renew_day) in list(plans.items()):
            loan = circ.get(loan_id)
            if loan["status"] != "ISSUED":
                plans.pop(loan_id)
                continue
            if renew_day and renew_day <= day and loan["renewals"] == 0 and loan["due_on"] >= day.isoformat():
                try:
                    circ.renew(loan_id, on=day)
                except utils.LibraryError:
                    pass
            if ret_day and ret_day <= day:            # Sunday returns happen the next open day
                damaged = rng.random() < 0.02
                circ.return_book(loan_id, on=day, damaged=damaged, damage_fee=200 if damaged else 0,
                                 note="Cover torn" if damaged else "")
                plans.pop(loan_id)
        # new issues
        for _ in range(rng.randint(2, 6)):
            m = rng.choice(members)
            b = rng.choice(lendable)
            try:
                loan = circ.issue(m["member_id"], b["book_id"], on=day)
            except utils.LibraryError:
                continue
            loan_days = utils.MEMBER_TYPES[m["type"]]["loan_days"]
            r = rng.random()
            keep = loan_days - rng.randint(1, 6) if r < 0.65 else loan_days + rng.randint(1, 12)   # ~35% late
            ret = day + timedelta(days=max(1, keep))
            renew = day + timedelta(days=loan_days - 2) if rng.random() < 0.15 else None
            plans[loan["loan_id"]] = (ret if ret < today else None, renew)
    # fines: most paid, one waived
    for f in fines.list():
        if fines.balance(f) > 0 and rng.random() < 0.7:
            mode = rng.choice(["Cash", "UPI"])
            fines.pay(f["fine_id"], fines.balance(f), mode, "" if mode == "Cash" else f"UPI{rng.randint(10**5, 10**6)}")
    unpaid = [f for f in fines.list() if fines.balance(f) > 0]
    if unpaid:
        FineManager(db, "librarian").waive(unpaid[0]["fine_id"], "Medical leave — late return excused")
    # a lost book
    issued = circ.loans(status="ISSUED")
    if issued:
        CirculationManager(db, "librarian").mark_lost(issued[-1]["loan_id"], on=today - timedelta(days=2))
    # reservation queues on popular titles: borrow out all copies, then queue members
    for b in [books[6], books[1]]:                 # AI: A Modern Approach (1 copy), Python Crash Course
        for c in bm.copies(b["book_id"]):
            if c["status"] == "AVAILABLE":
                for m in rng.sample(members, len(members)):
                    try:
                        circ.issue(m["member_id"], c["accession"], on=today - timedelta(days=3))
                        break
                    except utils.LibraryError:
                        continue
        for m in rng.sample(members, len(members)):
            if len(res.queue(b["book_id"])) >= 2:
                break
            try:
                res.reserve(m["member_id"], b["book_id"], on=today - timedelta(days=2))
            except utils.LibraryError:
                continue
    # one copy of Python Crash Course comes back today -> held for the first in the queue
    py_loans = [l for l in circ.loans(status="ISSUED") if l["book_id"] == books[1]["book_id"]]
    if py_loans:
        circ.return_book(py_loans[0]["loan_id"])

    s = {"loans": len(db.all("loans")), "on_loan": len(circ.loans(status="ISSUED")), "overdue": len(circ.overdue()),
         "fines": len(fines.list()), "res": len(db.all("reservations"))}
    print(f"Seeded {len(books)} titles ({len(db.all('copies'))} copies), {len(members)} members, {s['loans']} loans "
          f"({s['on_loan']} on loan, {s['overdue']} overdue), {s['fines']} fines, {s['res']} reservations.")
    print("Logins: admin/admin123 · librarian/lib12345 · assistant/asst1234 · members M0001-M0020 / member123")


if __name__ == "__main__":
    main()
