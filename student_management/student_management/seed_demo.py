"""Load realistic demo data:  python seed_demo.py  (add --force to wipe existing data first).

Creates 2 classes, 2 teachers, 30 students, about two months of attendance and marks for
Internal Test 1 (published) and Internal Test 2 (BCA published, BSc partly entered).
"""
from __future__ import annotations

import random
import shutil
import sys
from datetime import date, timedelta

from sms import utils
from sms.attendance import AttendanceManager
from sms.auth import AuthManager, UserManager
from sms.database import JSONDatabase
from sms.marks import MarksManager
from sms.students import ClassManager, StudentManager
from sms.utils import SUBJECTS, hash_password

STAFF_PASSWORD = "teach123"
STUDENT_PASSWORD = "stud123"

BCA = [  # name, gender, ability (typical %), attendance tendency
    ("Aswin Raj", "Male", 88, .96), ("Anjali Nair", "Female", 93, .98), ("Devika S", "Female", 79, .93),
    ("Mohammed Fasil", "Male", 66, .88), ("Gokul Krishnan", "Male", 52, .82), ("Sreelakshmi R", "Female", 85, .95),
    ("Arjun Menon", "Male", 45, .62), ("Fathima Rinsha", "Female", 74, .91), ("Nikhil Thomas", "Male", 61, .86),
    ("Gayathri Devi", "Female", 90, .97), ("Rahul P", "Male", 38, .70), ("Meera Joseph", "Female", 70, .90),
    ("Abhinav Suresh", "Male", 57, .84), ("Neha Varghese", "Female", 82, .94), ("Vishnu Prasad", "Male", 64, .89),
    ("Aiswarya Mohan", "Female", 77, .92),
]
BSC = [
    ("Adarsh V", "Male", 71, .90), ("Krishnapriya K", "Female", 89, .97), ("Sidharth Anil", "Male", 55, .85),
    ("Nandana Pillai", "Female", 81, .94), ("Muhammed Shahal", "Male", 48, .68), ("Athira Babu", "Female", 76, .92),
    ("Jithin George", "Male", 63, .88), ("Parvathy Unni", "Female", 92, .98), ("Akhil Dev", "Male", 42, .80),
    ("Diya Sebastian", "Female", 68, .91), ("Hari Shankar", "Male", 59, .87), ("Riya Fathima", "Female", 85, .95),
    ("Sanjay Kumar", "Male", 74, .90), ("Ameya Rajesh", "Female", 66, .89),
]
GUARDIANS = ["Rajan", "Suresh", "Mohanan", "Abdul Kareem", "Thomas", "Joseph", "Krishnan", "Varghese", "Anil Kumar",
             "Babu", "Sebastian", "Unnikrishnan", "Shaji", "George"]
PLACES = ["Kazhakkoottam", "Pattom", "Kowdiar", "Sreekaryam", "Ulloor", "Vazhuthacaud", "Peroorkada", "Nemom",
          "Kesavadasapuram", "Technopark Phase 3", "Attingal", "Neyyattinkara"]


def mark_for(rng: random.Random, ability: int, bias: int) -> float:
    m = round(min(100, max(8, rng.gauss(ability + bias, 7))) * 2) / 2      # half marks allowed
    return int(m) if m == int(m) else m


def main() -> None:
    data_dir = utils.DATA_DIR
    if any(data_dir.glob("*.json")):
        if "--force" not in sys.argv:
            print(f"Data already exists in {data_dir}. Run with --force to replace it.")
            return
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)
    db = JSONDatabase(data_dir)
    AuthManager(db)                                                  # creates admin / admin123

    um = UserManager(db, "admin")
    for username, name in [("anitha", "Anitha Kumari"), ("rajesh", "Rajesh Menon")]:
        um.add(username, name, "teacher", f"94470{rng.randint(10000, 99999)}", f"{username}@ociuz.edu.in")
        h, s = hash_password(STAFF_PASSWORD)
        db.update("users", "username", username, {"password_hash": h, "salt": s, "must_change_password": False})

    cm = ClassManager(db, "admin")
    cm.add("BCA-2024", "BCA 2024-27 Batch", "Bachelor of Computer Applications", "2026-27", 5, "anitha")
    cm.add("BSC-2025", "BSc CS 2025-28 Batch", "BSc Computer Science", "2026-27", 3, "rajesh")

    sm = StudentManager(db, "admin")
    tendency: dict[str, float] = {}
    ability: dict[str, int] = {}
    phone = 9400000000
    for code, people, born, admitted in [("BCA-2024", BCA, 2006, "2024-08-01"), ("BSC-2025", BSC, 2007, "2025-08-01")]:
        for i, (name, gender, abil, att) in enumerate(people):
            phone += rng.randint(1000, 90000)
            dob = date(born, 1, 1) + timedelta(days=rng.randint(0, 364))
            first = name.split()[0].lower()
            s, _ = sm.add(name, gender, dob.isoformat(), str(phone), code, f"{first}.{code[:3].lower()}{i + 1}@gmail.com",
                          f"{GUARDIANS[i % len(GUARDIANS)]} {name.split()[-1] if len(name.split()[-1]) > 2 else ''}".strip(),
                          str(phone + 7), f"TC {rng.randint(10, 60)}/{rng.randint(100, 2400)}, {PLACES[i % len(PLACES)]}, "
                                          f"Thiruvananthapuram", admitted)
            tendency[s["roll_no"]], ability[s["roll_no"]] = att, abil
            h, salt = hash_password(STUDENT_PASSWORD)
            db.update("users", "username", s["roll_no"].lower(),
                      {"password_hash": h, "salt": salt, "must_change_password": False})

    # ---- attendance: every working day from 7 Sep up to yesterday (today left for the demo)
    am = AttendanceManager(db, "anitha")
    start, end = date.today() - timedelta(days=68), date.today() - timedelta(days=1)
    for day in utils.working_days(start, end):
        for code in ("BCA-2024", "BSC-2025"):
            absent, leave = [], []
            for s in sm.list(code):
                r = rng.random()
                if r > tendency[s["roll_no"]]:
                    (leave if rng.random() < .2 else absent).append(s["roll_no"])
            am.mark_class(code, day, absent, leave)

    # ---- marks
    mm = MarksManager(db, "anitha")
    bias = {"Python": 2, "Java": -2, "DBMS": 0}
    for exam, shift in [("Internal Test 1", 0), ("Internal Test 2", 3)]:
        for code in ("BCA-2024", "BSC-2025"):
            for s in sm.list(code):
                roll = s["roll_no"]
                marks = {sub: mark_for(rng, ability[roll] + shift, bias[sub]) for sub in SUBJECTS}
                if exam == "Internal Test 2" and code == "BSC-2025" and roll >= "BSC25010":
                    marks = {"Python": marks["Python"]}                   # DBMS / Java still being entered
                mm.enter(roll, exam, marks)
    mm.enter("BCA24007", "Internal Test 1", {"Java": "AB"})                # absent for one paper
    mm.enter("BSC25005", "Internal Test 1", {"DBMS": "AB"})
    # two students with identical totals so the tie-ranking rule is visible
    mm.enter("BCA24006", "Internal Test 1", {"Python": 88, "Java": 84, "DBMS": 86})
    mm.enter("BCA24014", "Internal Test 1", {"Python": 85, "Java": 87, "DBMS": 86})
    mm.publish("BCA-2024", "Internal Test 1")
    mm.publish("BSC-2025", "Internal Test 1")
    mm.publish("BCA-2024", "Internal Test 2")

    print(f"Demo data created in {data_dir}")
    print(f"  Admin    : admin / admin123")
    print(f"  Teachers : anitha, rajesh / {STAFF_PASSWORD}")
    print(f"  Students : roll number (e.g. BCA24001, BSC25002) / {STUDENT_PASSWORD}")


if __name__ == "__main__":
    main()
