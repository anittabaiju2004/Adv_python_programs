"""Load a demo user with sample contacts.

Usage:  python seed_demo.py
Login:  demo / demo123      (admin: admin / admin123)
"""
import random
from datetime import date, timedelta

from contactbook import utils
from contactbook.auth import AuthManager
from contactbook.contacts import ContactManager
from contactbook.database import JSONDatabase

FIRST = ["Anitta", "Rahul", "Priya", "Arjun", "Fathima", "Thomas", "Meera", "Vishnu", "Sneha", "Akhil",
         "Divya", "Joseph", "Lakshmi", "Nikhil", "Anjali", "Sreejith", "Neha", "Kiran", "Reshma", "Abdul",
         "Gopika", "Manu", "Aswathy", "Varun", "Nimisha", "Hari", "Ammu", "Jithin", "Sara", "Vivek"]
LAST = ["Joseph", "Menon", "Nair", "Das", "Rasheed", "Kurian", "Pillai", "Varma", "George", "Krishnan",
        "Mathew", "Thomas", "Iyer", "Raj", "Babu"]
COMPANIES = ["Infosys", "TCS", "UST Global", "IBS Software", "Ociuz Infotech", "Federal Bank", "", "", ""]
TITLES = ["Software Engineer", "Manager", "Designer", "Accountant", "Teacher", "Doctor", "Student", ""]
CITIES = ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur"]


def main():
    random.seed(5)
    db = JSONDatabase(utils.DATA_DIR)
    auth = AuthManager(db)
    if auth.get_user("demo"):
        print("Demo user already exists — nothing to do.")
        return
    auth.register("demo", "demo123", "demo123", "Demo User")
    cm = ContactManager(db, "demo")
    cm.add_category("Gym")
    cats = [c for c in cm.categories() if c != "Emergency"]

    used = set()
    for i, first in enumerate(FIRST):
        last = random.choice(LAST)
        phone = f"9{random.randint(100000000, 999999999)}"
        company = random.choice(COMPANIES)
        bday = ""
        if i < 4:                                      # a few birthdays coming up soon
            d = date.today() + timedelta(days=[0, 2, 5, 12][i])
            bday = d.replace(year=d.year - random.randint(22, 45), day=min(d.day, 28)).isoformat()
        elif random.random() < 0.5:
            bday = date(random.randint(1965, 2003), random.randint(1, 12), random.randint(1, 28)).isoformat()
        email = f"{first.lower()}.{last.lower()}@{'gmail.com' if not company else company.lower().replace(' ', '') + '.com'}"
        if email in used:
            email = ""
        used.add(email)
        cm.add(first_name=first, last_name=last, phone=phone, email=email, company=company,
               job_title=random.choice(TITLES) if company else "", address=random.choice(CITIES),
               birthday=bday, category=random.choice(cats), favorite=random.random() < 0.2,
               alt_phone=f"0471{random.randint(2000000, 2999999)}" if random.random() < 0.15 else "")
    cm.add(first_name="Emily", last_name="Clark", phone="+44 20 7946 0958", email="emily@example.co.uk",
           company="Clark & Sons", category="Business", notes="London office; call after 2 pm IST")
    cm.add(first_name="Police", phone="0471 2331843", category="Emergency", favorite=True)
    cm.add(first_name="Ambulance", phone="0471 2306108", category="Emergency", favorite=True)
    for c in cm.search("Babu")[:2]:                    # put a couple in the recycle bin
        cm.delete(c.id)
    s = cm.stats()
    print(f"Seeded {s['total']} contacts ({s['favorites']} favourites, {s['in_trash']} in recycle bin).")
    print("Log in with  demo / demo123   (admin: admin / admin123)")


if __name__ == "__main__":
    main()
