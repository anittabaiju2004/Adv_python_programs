"""Load demo data: 5 categories, 62 questions with explanations, 6 quizzes,
an instructor, 10 students and ~30 days of practice and exam attempts.

Usage:  python seed_demo.py
Logins: admin / admin123 · instructor / teach123 · students anitta, rahul, ... / student123
"""
import random
from datetime import datetime, timedelta

from quiz import utils
from quiz.auth import AuthManager, UserManager
from quiz.categories import CategoryManager
from quiz.database import JSONDatabase
from quiz.engine import QuizManager, QuizSession
from quiz.questions import QuestionManager
from quiz.users import UserService

T, F = "True/False", "MCQ"
# category -> [(difficulty, type, question, options, answer, explanation)]
BANK = {
    "Python Programming": [
        ("Easy", F, "What is the output of print(type(10 / 2))?", ["<class 'int'>", "<class 'float'>", "<class 'str'>", "Error"], "B",
         "The / operator always performs true division and returns a float: 10 / 2 is 5.0."),
        ("Easy", F, "Which keyword is used to define a function in Python?", ["func", "define", "def", "function"], "C",
         "Functions are defined with the def keyword, e.g. def greet():"),
        ("Easy", F, 'What does len("Python") return?', ["5", "6", "7", "Error"], "B", "'Python' has six characters."),
        ("Easy", F, "Which of these data types is immutable?", ["list", "dict", "set", "tuple"], "D",
         "Tuples cannot be changed after creation; lists, dicts and sets are mutable."),
        ("Easy", T, "Python is a case-sensitive language.", None, "True", "Name, name and NAME are three different identifiers."),
        ("Medium", F, "What is the output of print(2 ** 3 ** 2)?", ["64", "512", "36", "Error"], "B",
         "** is right-associative: 3 ** 2 = 9 is evaluated first, then 2 ** 9 = 512."),
        ("Medium", F, "What does [1, 2, 3][::-1] evaluate to?", ["[1, 2, 3]", "[3, 2, 1]", "[3]", "Error"], "B",
         "A slice with step -1 walks the list backwards, producing a reversed copy."),
        ("Medium", F, "Which list method adds an element to the end of a list?", ["add()", "insert()", "append()", "extend()"], "C",
         "append(x) adds one element at the end; extend() adds all items of an iterable."),
        ("Medium", F, "What is the value of bool([])?", ["True", "False", "None", "Error"], "B",
         "Empty containers are falsy, so bool([]) is False."),
        ("Medium", F, 'What does "a,b".split(",") return?', ["('a', 'b')", "['a', 'b']", "'a b'", "['a,b']"], "B",
         "str.split returns a list of the pieces between separators."),
        ("Hard", F, "def f(x, l=[]): l.append(x); return l — after calling f(1), what does print(f(2)) show?",
         ["[2]", "[1, 2]", "[1]", "Error"], "B",
         "Default arguments are evaluated once, so the same list is shared between calls: it already holds 1."),
        ("Hard", F, "What is printed by print(0.1 + 0.2 == 0.3)?", ["True", "False", "0.3", "Error"], "B",
         "Binary floating point cannot represent 0.1 and 0.2 exactly; the sum is 0.30000000000000004."),
        ("Hard", T, "A Python set can contain a list as one of its elements.", None, "False",
         "Set elements must be hashable; lists are mutable and unhashable (use a tuple instead)."),
    ],
    "Computer Fundamentals": [
        ("Easy", F, "What does CPU stand for?", ["Central Processing Unit", "Computer Personal Unit", "Central Program Utility",
                                                 "Control Processing Unit"], "A", "The CPU executes program instructions."),
        ("Easy", F, "How many bits make one byte?", ["4", "8", "16", "32"], "B", "One byte is 8 bits."),
        ("Easy", F, "Which of these is volatile memory?", ["ROM", "RAM", "Hard disk", "SSD"], "B",
         "RAM loses its contents when power is switched off."),
        ("Easy", F, "Which of these is an input device?", ["Monitor", "Printer", "Keyboard", "Speaker"], "C",
         "A keyboard sends data into the computer; the others are output devices."),
        ("Easy", T, "An operating system manages the computer's hardware resources.", None, "True",
         "The OS allocates CPU time, memory and devices to programs."),
        ("Medium", F, "What is decimal 10 in binary?", ["1000", "1010", "1100", "1110"], "B", "10 = 8 + 2 = 1010 in binary."),
        ("Medium", F, "Which protocol is used to transfer web pages?", ["FTP", "SMTP", "HTTP", "SNMP"], "C",
         "HTTP (HyperText Transfer Protocol) carries web pages; SMTP is for e-mail, FTP for files."),
        ("Medium", F, "Which data structure works on the LIFO principle?", ["Queue", "Stack", "Array", "Linked list"], "B",
         "Last In, First Out — the last item pushed onto a stack is the first popped."),
        ("Medium", F, "Which SQL command retrieves data from a table?", ["GET", "SELECT", "FETCH", "RETRIEVE"], "B",
         "SELECT columns FROM table reads data."),
        ("Medium", F, "What is the default port number for HTTPS?", ["80", "21", "443", "8080"], "C",
         "HTTPS uses port 443; plain HTTP uses port 80."),
        ("Hard", F, "What is the time complexity of binary search on a sorted array of n elements?",
         ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "B", "Each step halves the search range, so about log2(n) steps."),
        ("Hard", F, "Which OSI layer is responsible for routing packets between networks?",
         ["Data link", "Transport", "Network", "Session"], "C", "Layer 3, the network layer (e.g. IP), handles routing."),
        ("Hard", F, "What is hexadecimal FF in decimal?", ["155", "255", "256", "1515"], "B", "FF = 15 × 16 + 15 = 255."),
    ],
    "Mathematics & Aptitude": [
        ("Easy", F, "What is 15% of 200?", ["15", "20", "30", "35"], "C", "15/100 × 200 = 30."),
        ("Easy", F, "Find the next number: 2, 4, 8, 16, ?", ["18", "24", "32", "64"], "C", "Each term doubles: 16 × 2 = 32."),
        ("Easy", F, "What is the area of a rectangle 8 m long and 5 m wide?", ["13 m²", "26 m²", "40 m²", "45 m²"], "C",
         "Area = length × breadth = 8 × 5 = 40 m²."),
        ("Easy", T, "91 is a prime number.", None, "False", "91 = 7 × 13, so it is not prime."),
        ("Medium", F, "A 120 m long train runs at 54 km/h. How long does it take to cross a pole?",
         ["6 s", "8 s", "10 s", "12 s"], "B", "54 km/h = 15 m/s; time = 120 ÷ 15 = 8 seconds."),
        ("Medium", F, "What is the average of the first 10 natural numbers?", ["5", "5.5", "6", "10"], "B",
         "Sum = 55, so the average is 55 ÷ 10 = 5.5."),
        ("Medium", F, "5 workers finish a job in 12 days. How many days will 6 workers take?", ["8", "9", "10", "14"], "C",
         "Total work = 5 × 12 = 60 worker-days; 60 ÷ 6 = 10 days."),
        ("Medium", F, "What is the simple interest on ₹5,000 at 8% per annum for 3 years?", ["₹1,000", "₹1,200", "₹1,500", "₹1,800"], "B",
         "SI = P × R × T / 100 = 5000 × 8 × 3 / 100 = ₹1,200."),
        ("Medium", F, "What is the LCM of 12 and 18?", ["6", "24", "36", "72"], "C", "12 = 2²·3 and 18 = 2·3²; LCM = 2²·3² = 36."),
        ("Hard", F, "Two dice are thrown. What is the probability that the sum is 7?", ["1/12", "1/6", "1/9", "7/36"], "B",
         "Six of the 36 outcomes sum to 7: 6/36 = 1/6."),
        ("Hard", F, "Compound interest on ₹10,000 at 10% p.a. for 2 years, compounded annually, is:",
         ["₹2,000", "₹2,100", "₹2,200", "₹1,900"], "B", "Amount = 10,000 × 1.1² = 12,100, so CI = ₹2,100."),
        ("Hard", F, "A sum of money doubles itself in 5 years at simple interest. What is the rate of interest?",
         ["10%", "15%", "20%", "25%"], "C", "Interest equals the principal in 5 years: R = 100 / 5 = 20% per year."),
    ],
    "General Science": [
        ("Easy", F, "What is the chemical formula of water?", ["H2O", "CO2", "O2", "H2O2"], "A",
         "Two hydrogen atoms bonded to one oxygen atom."),
        ("Easy", F, "Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], "B",
         "Iron oxide on its surface gives Mars its red colour."),
        ("Easy", F, "Which gas do plants absorb from the air for photosynthesis?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], "C",
         "Plants use carbon dioxide and water, with sunlight, to make glucose and release oxygen."),
        ("Easy", T, "Sound travels faster than light.", None, "False",
         "Light travels at about 300,000 km/s; sound in air at only about 343 m/s."),
        ("Medium", F, "What is the SI unit of force?", ["Joule", "Watt", "Newton", "Pascal"], "C", "1 newton = 1 kg·m/s²."),
        ("Medium", F, "Which organelle is called the powerhouse of the cell?", ["Nucleus", "Ribosome", "Mitochondria", "Golgi body"], "C",
         "Mitochondria produce most of the cell's energy (ATP)."),
        ("Medium", F, "What is the hardest naturally occurring substance?", ["Iron", "Quartz", "Diamond", "Granite"], "C",
         "Diamond, a form of carbon, is the hardest natural material."),
        ("Medium", F, "What is the approximate speed of light in vacuum?", ["3 × 10⁵ m/s", "3 × 10⁸ m/s", "3 × 10⁶ km/s", "343 m/s"], "B",
         "About 299,792 km/s, usually rounded to 3 × 10⁸ m/s."),
        ("Medium", F, "Which vitamin does the skin produce when exposed to sunlight?", ["Vitamin A", "Vitamin C", "Vitamin D", "Vitamin K"], "C",
         "UV-B light helps the skin make vitamin D."),
        ("Hard", F, "What is the pH of pure water at 25 °C?", ["0", "5", "7", "14"], "C", "Pure water is neutral, pH 7."),
        ("Hard", F, "Which element has atomic number 6?", ["Oxygen", "Nitrogen", "Carbon", "Boron"], "C",
         "Carbon has 6 protons in its nucleus."),
        ("Hard", F, "What is the approximate acceleration due to gravity at the Earth's surface?",
         ["6.7 m/s²", "8.9 m/s²", "9.8 m/s²", "11.2 m/s²"], "C", "g ≈ 9.8 m/s² (11.2 km/s is the escape velocity)."),
    ],
    "India GK": [
        ("Easy", F, "What is the capital of Kerala?", ["Kochi", "Kozhikode", "Thiruvananthapuram", "Thrissur"], "C",
         "Thiruvananthapuram is the capital; Kochi is the largest urban area."),
        ("Easy", F, "What is the national animal of India?", ["Lion", "Tiger", "Elephant", "Peacock"], "B",
         "The Bengal tiger; the peacock is the national bird."),
        ("Easy", F, "Who wrote India's national anthem 'Jana Gana Mana'?", ["Bankim Chandra Chatterjee", "Rabindranath Tagore",
                                                                            "Sarojini Naidu", "Muhammad Iqbal"], "B",
         "Rabindranath Tagore; 'Vande Mataram' (national song) was written by Bankim Chandra Chatterjee."),
        ("Easy", T, "The Constitution of India came into effect on 26 January 1950.", None, "True",
         "That day is celebrated every year as Republic Day."),
        ("Medium", F, "Which is the longest river in India?", ["Godavari", "Yamuna", "Ganga", "Narmada"], "C",
         "The Ganga flows about 2,500 km within India."),
        ("Medium", F, "In which year did India gain independence?", ["1945", "1947", "1950", "1942"], "B", "15 August 1947."),
        ("Medium", F, "Who was the first Prime Minister of India?", ["Sardar Patel", "Jawaharlal Nehru", "Rajendra Prasad",
                                                                     "Lal Bahadur Shastri"], "B",
         "Jawaharlal Nehru (1947-1964); Dr Rajendra Prasad was the first President."),
        ("Medium", F, "Who is known as the 'Missile Man of India'?", ["Homi Bhabha", "Vikram Sarabhai", "A. P. J. Abdul Kalam",
                                                                       "C. V. Raman"], "C",
         "Dr A. P. J. Abdul Kalam led India's missile programme and later became President."),
        ("Medium", F, "Which is the smallest state of India by area?", ["Sikkim", "Tripura", "Goa", "Manipur"], "C",
         "Goa, at about 3,700 km²."),
        ("Hard", F, "In which year was the Battle of Plassey fought?", ["1757", "1764", "1857", "1707"], "A",
         "1757 — Robert Clive's victory over Siraj-ud-Daulah began British dominance in Bengal."),
        ("Hard", F, "Which Indian state has the longest coastline?", ["Tamil Nadu", "Andhra Pradesh", "Gujarat", "Kerala"], "C",
         "Gujarat's coastline is about 1,600 km long."),
        ("Hard", F, "The Chipko movement is associated with which cause?", ["Water conservation", "Forest conservation",
                                                                           "Women's suffrage", "Land reform"], "B",
         "Villagers hugged trees to stop them being cut — a landmark forest conservation movement."),
    ],
}
DESCRIPTIONS = {"Python Programming": "Python syntax, data types and gotchas",
                "Computer Fundamentals": "Hardware, networking, data structures, databases",
                "Mathematics & Aptitude": "Arithmetic, percentages, time & work, probability",
                "General Science": "Physics, chemistry and biology basics", "India GK": "Indian geography, history and civics"}
STUDENTS = [("anitta", "Anitta Joseph", 0.80), ("rahul", "Rahul Menon", 0.65), ("priya", "Priya Nair", 0.88),
            ("arjun", "Arjun Das", 0.50), ("fathima", "Fathima Rasheed", 0.72), ("akhil", "Akhil Krishnan", 0.58),
            ("sneha", "Sneha George", 0.76), ("nikhil", "Nikhil Raj", 0.45), ("divya", "Divya Mathew", 0.68),
            ("vishnu", "Vishnu Varma", 0.62)]


class SimClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def main():
    rng = random.Random(31)
    db = JSONDatabase(utils.DATA_DIR)
    if db.all("questions"):
        print("Data already present — delete the data/ folder first to re-seed.")
        return
    auth = AuthManager(db)
    _, t = UserManager(db, "admin").add("instructor", "Meera Pillai", "instructor", email="meera@ociuz.in")
    auth.change_password("instructor", t, "teach123", "teach123")
    cm, qm = CategoryManager(db, "instructor"), QuestionManager(db, "instructor")
    for cat, items in BANK.items():
        cm.add(cat, DESCRIPTIONS[cat])
        for diff, qtype, text, options, answer, why in items:
            qm.add(cat, diff, text, options, answer, why, qtype)
    qz = QuizManager(db, "instructor")
    quizzes = [
        qz.create("Python Basics", "Python Programming", "Mixed", 10, 10, 0.25, 50, 3,
                  "Core Python: types, operators, lists and common pitfalls.", publish=True),
        qz.create("Computer Fundamentals Test", "Computer Fundamentals", "Mixed", 10, 8, 0, 50, 2,
                  "Hardware, number systems, networking and data structures.", publish=True),
        qz.create("Aptitude Challenge", "Mathematics & Aptitude", "Mixed", 8, 12, 0.25, 60, 3,
                  "Quantitative aptitude for placement tests.", publish=True),
        qz.create("General Knowledge Mix", "Mixed", "Mixed", 15, 12, 0, 50, 0,
                  "Questions from every category.", publish=True),
        qz.create("Science Quick Test", "General Science", "Easy", 4, 3, 0, 50, 0, "A 3-minute warm-up.", publish=True),
        qz.create("Python Advanced", "Python Programming", "Hard", 5, 10, 0.5, 60, 1,
                  "Draft — needs more hard questions before publishing."),
    ]
    us = UserService(db, "system")
    for username, name, _ in STUDENTS:
        us.register_student(username, name, "student123", "student123", f"{username}@example.com",
                            institution=rng.choice(["Ociuz Academy", "CET Thiruvananthapuram", "TKM College"]))

    # Simulated attempts: each student improves a little over time
    playable = [q for q in quizzes if q["published"]]
    for round_no in range(8):
        for username, _, skill in STUDENTS:
            if rng.random() < 0.3:
                continue
            quiz = rng.choice(playable)
            mode = "Practice" if round_no < 3 or rng.random() < 0.35 else "Exam"
            clock = SimClock()
            try:
                s = QuizSession(db, username, quiz, mode, clock=clock, rng=rng)
            except utils.QuizError:
                continue
            ability = min(0.97, skill + round_no * 0.025)
            for i, it in enumerate(s.items):
                q = it["q"]
                clock.t += rng.uniform(12, 45)
                if s.time_up():
                    break
                if rng.random() < 0.05:
                    continue                                         # skipped
                p = ability + {"Easy": 0.1, "Medium": 0.0, "Hard": -0.18}[q["difficulty"]]
                choice = q["answer"] if rng.random() < p else rng.choice(
                    [k for k in range(len(q["options"])) if k != q["answer"]])
                s.answer(i, it["order"].index(choice))
                if rng.random() < 0.04:
                    try:
                        s.bookmark(i)
                    except utils.QuizError:
                        pass
            s.submit()

    # Spread the attempts over the last 30 days (keeping their order) so trends look real
    with db.editing("results") as results:
        start = datetime.now() - timedelta(days=30)
        step = timedelta(days=30) / max(1, len(results))
        for i, r in enumerate(results):
            t0 = start + step * i + timedelta(minutes=rng.randint(0, 90))
            r["started_at"] = t0.isoformat(timespec="seconds")
            r["submitted_at"] = (t0 + timedelta(seconds=r["duration_sec"])).isoformat(timespec="seconds")

    rs = db.all("results")
    print(f"Seeded {len(db.all('questions'))} questions in {len(BANK)} categories, {len(quizzes)} quizzes, "
          f"{len(STUDENTS)} students, {len(rs)} attempts ({sum(r['mode'] == 'Exam' for r in rs)} exams, "
          f"{sum(1 for r in rs if r['certificate_code'])} certificates).")
    print("Logins: admin/admin123 · instructor/teach123 · students anitta, rahul, priya ... / student123")


if __name__ == "__main__":
    main()
