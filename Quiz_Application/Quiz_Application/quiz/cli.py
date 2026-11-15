"""Menu-driven interface: student portal and staff portal (admin / instructor)."""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

from . import utils
from .admin import AdminPanel
from .analysis import PerformanceAnalyzer
from .auth import AuthManager, can
from .backup import BackupManager
from .categories import CategoryManager
from .database import JSONDatabase
from .engine import MIXED, QuizManager, QuizSession, bookmark_practice
from .leaderboard import PERIODS, Leaderboard
from .questions import QuestionManager
from .reports import ReportGenerator
from .results import ResultManager
from .users import UserService
from .utils import (APP_NAME, DIFFICULTIES, QUESTION_TYPES, ROLES, QuizError, QuizRuleError, fmt_duration)

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


def wrap(text: str, width: int = W - 6, indent: str = "  ") -> str:
    import textwrap
    return "\n".join(textwrap.wrap(text, width, initial_indent=indent, subsequent_indent=indent)) or indent


def print_result_summary(r: dict) -> None:
    header(f"RESULT — {r['quiz_title']} ({r['mode']})")
    if r["time_up"]:
        print("  ⏰ Time was up — the quiz was submitted automatically.")
    print(f"  Score      : {r['score']:g} / {r['max_score']}   ({r['percent']:.1f}%)")
    print(f"  Grade      : {r['grade']} — {r['remark']}   ·   {'PASSED ✔' if r['passed'] else 'NOT PASSED'}"
          f" (pass mark {r['pass_percent']:g}%)")
    print(f"  Correct {r['correct']} · Wrong {r['wrong']} · Skipped {r['skipped']}"
          + (f" · negative marks -{r['negative_marks']:g}" if r["negative_marks"] else ""))
    print(f"  Time taken : {fmt_duration(r['duration_sec'])}")
    if r["certificate_code"]:
        print(f"  🎓 Certificate earned! ID {r['result_id']}, code {r['certificate_code']}")


def print_review(r: dict) -> None:
    for i, a in enumerate(r["answers"], 1):
        mark = {"CORRECT": "✔", "WRONG": "✖", "SKIPPED": "–"}[a["status"]]
        print(f"\n  {mark} Q{i}. [{a['difficulty']}] {a['text']}")
        yours = a["options"][a["chosen"]] if a["chosen"] is not None else "(skipped)"
        print(f"      Your answer   : {yours}")
        if a["status"] != "CORRECT":
            print(f"      Correct answer: {a['options'][a['answer']]}")
        if a["explanation"]:
            print(wrap("Why: " + a["explanation"], indent="      "))


def print_board(rows: list[dict], per_quiz: bool) -> None:
    if not rows:
        print("  No exam attempts yet.")
        return
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for r in rows:
        tag = medals.get(r["rank"], "  ")
        if per_quiz:
            print(f"  {tag} {r['rank']:>3}. {r['name'][:24]:<25}{r['percent']:>6.1f}%  {r['grade']:<3}"
                  f"{fmt_duration(r['duration_sec']):>9}  {r['date']}")
        else:
            print(f"  {tag} {r['rank']:>3}. {r['name'][:24]:<25}avg {r['average']:>6.1f}%  over {r['quizzes']} quiz(zes)")


# ====================================================================== app
class App:
    def __init__(self, data_dir=None, backup_dir=None, report_dir=None):
        self.data_dir = data_dir or utils.DATA_DIR
        self.db = JSONDatabase(self.data_dir)                    # loaded automatically at start-up
        self.auth = AuthManager(self.db)
        self.backup = BackupManager(self.data_dir, backup_dir or utils.BACKUP_DIR)
        self.report_dir = Path(report_dir or utils.REPORT_DIR)
        self.user: dict | None = None

    @property
    def actor(self) -> str:
        return self.user["username"] if self.user else "system"

    def qm(self):
        return QuestionManager(self.db, self.actor)

    def quizzes(self):
        return QuizManager(self.db, self.actor)

    def reports(self):
        return ReportGenerator(self.db, self.report_dir)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        while True:
            choice = menu(APP_NAME.upper(), ["Login", "Register as a student", "Verify a certificate"], "Exit")
            try:
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.register()
                    pause()
                elif choice == "3":
                    v = ResultManager(self.db).verify_certificate(ask("Certificate ID"), ask("Verification code"))
                    print(f"\n  ✔ VALID — {v['name']}, '{v['quiz']}', {v['percent']:.1f}% (grade {v['grade']}) on {v['date']}."
                          if v["valid"] else f"\n  ✖ NOT VALID — {v['reason']}")
                    pause()
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    return
            except QuizError as exc:
                print(f"\n  ✖ {exc}")
                pause()

    def register(self) -> None:
        header("STUDENT REGISTRATION")
        u = UserService(self.db).register_student(ask("Choose a username"), ask("Full name"),
                                                  getpass.getpass("  Password (6+ chars, letters and digits): "),
                                                  getpass.getpass("  Confirm password: "), ask("Email (optional)"),
                                                  ask("Mobile (optional)"), ask("College / institution (optional)"))
        print(f"  ✔ Account '{u['username']}' created. You can log in now.")

    def login(self) -> None:
        header("LOGIN")
        self.user = self.auth.login(ask("Username"), getpass.getpass("  Password: "))
        if self.user["must_change_password"]:
            print("\n  You are using a temporary password. Please set a new one.")
            while True:
                try:
                    self.change_password()
                    break
                except QuizError as exc:
                    print(f"  ✖ {exc}")
        print(f"\n  Welcome, {self.user['name']}!")
        if self.user["role"] == "student":
            self.student_portal()
        else:
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
            except QuizError as exc:
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
            except QuizError as exc:
                print(f"\n  ✖ {exc}")
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                continue
            pause()

    def change_password(self) -> None:
        self.auth.change_password(self.actor, getpass.getpass("  Current password: "),
                                  getpass.getpass("  New password: "), getpass.getpass("  Confirm new password: "))
        print("  ✔ Password changed.")

    # ====================================================== quiz runner
    def run_session(self, s: QuizSession) -> dict:
        q = s.quiz
        header(f"{q['title']} — {s.mode.upper()} MODE")
        print(f"  {len(s)} question(s)"
              + (f" · time limit {q['time_limit_min']} min" if s.time_limit else " · untimed")
              + (f" · negative marking -{q['negative_marking']:g} × marks per wrong answer"
                 if s.mode == "Exam" and q["negative_marking"] else "")
              + f" · pass mark {q['pass_percent']:g}%")
        print("  Answer with a letter.  S = skip   * = bookmark question   X = finish & submit")
        if s.mode == "Practice":
            print("  Practice mode: you see the correct answer and explanation after each question.")
        input("\n  Press Enter to start...")

        def ask_question(i: int) -> str | None:
            """Returns 'quit' to stop early, None otherwise."""
            while True:
                if s.time_up():
                    return "quit"
                v = s.view(i)
                rem = s.remaining()
                timer = f"   ⏱ {fmt_duration(rem)} left" if rem is not None else ""
                print(f"\n  Question {v['number']} of {v['of']}  [{v['category']} · {v['difficulty']} · "
                      f"{v['marks']} mark{'s' if v['marks'] > 1 else ''}]{timer}")
                print(wrap(v["text"]))
                for k, opt in enumerate(v["options"]):
                    sel = "  ← your answer" if v["chosen"] == k else ""
                    print(f"     {chr(65 + k)}) {opt}{sel}")
                choice = ask("Your answer").upper()
                if choice == "X":
                    return "quit"
                if choice in ("S", ""):            # skip (or keep the current answer when revisiting)
                    return None
                if choice == "*":
                    try:
                        s.bookmark(i)
                        print("  🔖 Bookmarked.")
                    except QuizError as exc:
                        print(f"  {exc}")
                    continue
                try:
                    fb = s.answer(i, choice)
                except QuizRuleError as exc:
                    print(f"  ⏰ {exc}")
                    return "quit"
                except QuizError as exc:
                    print(f"  ✖ {exc}")
                    continue
                if fb:
                    print("  ✔ Correct!" if fb["correct"] else f"  ✖ Not quite. Correct answer: {fb['correct_letter']}) {fb['correct_text']}")
                    if fb["explanation"]:
                        print(wrap("💡 " + fb["explanation"]))
                return None

        stopped = False
        for i in range(len(s)):
            if ask_question(i) == "quit":
                stopped = True
                break
        while not s.time_up() and s.unanswered() and not stopped:
            if not confirm(f"\n  {len(s.unanswered())} question(s) unanswered. Go back to them?"):
                break
            for i in s.unanswered():
                if ask_question(i) == "quit":
                    stopped = True
                    break
        if s.time_up():
            print("\n  ⏰ Time is up! Submitting your answers...")
        elif s.mode == "Exam" and not confirm(f"\n  Submit the exam now? ({len(s) - len(s.unanswered())}/{len(s)} answered)"):
            print("  Submitting anyway — exams cannot be saved for later.")
        r = s.submit()
        print_result_summary(r)
        if confirm("\n  Review your answers?"):
            print_review(r)
        if confirm("\n  Save the result as PDF?"):
            print(f"  ✔ Saved: {self.reports().result_pdf(r['result_id'])}")
        if r["certificate_code"] and confirm("  Download your certificate (PDF)?"):
            print(f"  ✔ Saved: {self.reports().certificate_pdf(r['result_id'])}")
        return r

    # ===================================================== student portal
    def student_portal(self) -> None:
        self.loop(f"STUDENT PORTAL — {self.user['name']}", [
            ("Take a quiz", self.take_quiz, None, False), ("Quick practice by category", self.quick_practice, None, False),
            ("Practise my bookmarked questions", self.practice_bookmarks, None, False),
            ("My results & answer review", self.my_results, None, False),
            ("My performance analysis", self.my_performance, None, False),
            ("Leaderboard", self.leaderboard, None, False), ("My certificates", self.my_certificates, None, False),
            ("My bookmarks", self.my_bookmarks, None, False), ("My profile", self.my_profile, None, False),
            ("Change password", self.change_password, None, False)])

    def take_quiz(self) -> None:
        qs = self.quizzes().list(published_only=True)
        if not qs:
            print("  No quizzes are available yet.")
            return
        rm = ResultManager(self.db)
        header("AVAILABLE QUIZZES")
        for i, q in enumerate(qs, 1):
            used = rm.attempt_count(self.actor, q["quiz_id"])
            best = rm.best(self.actor, q["quiz_id"])
            left = "unlimited" if not q["max_attempts"] else f"{max(0, q['max_attempts'] - used)} exam attempt(s) left"
            print(f"  {i:>2}. {q['title']:<34}{q['category']:<18}{q['difficulty']:<8}{q['num_questions']:>3} Q  "
                  f"{(str(q['time_limit_min']) + ' min') if q['time_limit_min'] else 'untimed':>8}")
            print(f"      {left}" + (f" · your best {best['percent']:.1f}% ({best['grade']})" if best else ""))
        n = ask("Select quiz number")
        if not (n.isdigit() and 1 <= int(n) <= len(qs)):
            return
        mode = choose("Mode (Practice = feedback, no timer · Exam = timed, graded, leaderboard, certificate)",
                      ["Practice", "Exam"])
        self.run_session(QuizSession(self.db, self.actor, qs[int(n) - 1], mode))

    def quick_practice(self) -> None:
        cat = choose("Category (blank = all)", CategoryManager(self.db).names(), allow_blank=True) or None
        diff = choose("Difficulty (blank = mixed)", DIFFICULTIES, allow_blank=True) or None
        n = ask("Number of questions", "5")
        quiz = QuizManager.practice_quiz(cat, diff, utils.validate_int(n, "Number of questions", 1, 50))
        self.run_session(QuizSession(self.db, self.actor, quiz, "Practice"))

    def practice_bookmarks(self) -> None:
        qs = bookmark_practice(self.db, self.actor)
        quiz = {**QuizManager.practice_quiz(None, None, len(qs)), "title": "Practice: my bookmarked questions"}
        self.run_session(QuizSession(self.db, self.actor, quiz, "Practice", questions=qs))

    def my_results(self) -> None:
        rs = ResultManager(self.db).list(self.actor)
        if not rs:
            print("  No attempts yet.")
            return
        for r in rs[:25]:
            print(f"  {r['result_id']}  {r['submitted_at'][:16].replace('T', ' ')}  {r['quiz_title'][:28]:<29}"
                  f"{r['mode']:<9}{r['percent']:>6.1f}%  {r['grade']:<3}{'✔' if r['passed'] else ' '}")
        rid = ask("Result ID to review (blank = back)")
        if rid:
            r = ResultManager(self.db).get(rid)
            if r["username"] != self.actor:
                raise QuizError("That result belongs to someone else.")
            print_result_summary(r)
            print_review(r)
            if confirm("\n  Save as PDF?"):
                print(f"  ✔ Saved: {self.reports().result_pdf(r['result_id'])}")

    def _print_analysis(self, username: str) -> None:
        a = PerformanceAnalyzer(self.db).student(username)
        if not a["attempts"]:
            print("  No attempts yet.")
            return
        header(f"PERFORMANCE — {username}")
        print(f"  Attempts {a['attempts']} (exam {a['exams']}, practice {a['practice']}) · average {a['average']}% · "
              f"best {a['best']:.1f}% · accuracy {a['accuracy']}%")
        if a["exams"]:
            print(f"  Exams passed {a['passed']}/{a['exams']} ({a['pass_rate']}%) · certificates {a['certificates']}")
        print(f"  Average time per question: {a['avg_sec_per_question']} s")
        if a["improvement"] is not None:
            print(f"  Trend: {a['improvement']:+.1f} points (last 3 attempts vs first 3)")
        print("\n  Accuracy by category:")
        for c, s in sorted(a["by_category"].items(), key=lambda kv: kv[1]["accuracy"]):
            print(f"    {c:<24}{s['accuracy']:>6.1f}%  {'█' * int(s['accuracy'] / 5):<20} ({s['correct']}/{s['total']})")
        print("\n  Accuracy by difficulty:")
        for d, s in a["by_difficulty"].items():
            print(f"    {d:<24}{s['accuracy']:>6.1f}%  ({s['correct']}/{s['total']})")
        if a["weak_areas"]:
            print(f"\n  📌 Focus on: {', '.join(a['weak_areas'])}")
        if a["strengths"]:
            print(f"  ⭐ Strengths: {', '.join(a['strengths'])}")

    def my_performance(self) -> None:
        self._print_analysis(self.actor)
        if PerformanceAnalyzer(self.db).student(self.actor)["attempts"] and confirm("\n  Save a PDF report with charts?"):
            print(f"  ✔ Saved: {self.reports().performance_pdf(self.actor)}")

    def leaderboard(self) -> None:
        lb = Leaderboard(self.db)
        period = choose("Period", list(PERIODS))
        quizzes = self.quizzes().list(published_only=True)
        pick = choose("Leaderboard", ["Overall"] + [f"{q['quiz_id']} {q['title']}" for q in quizzes])
        if pick == "Overall":
            header(f"OVERALL LEADERBOARD ({period})")
            print_board(lb.overall(period), per_quiz=False)
            mine = lb.rank_of(self.actor) if self.user["role"] == "student" else None
        else:
            qid = pick.split()[0]
            header(f"LEADERBOARD — {pick} ({period})")
            print_board(lb.for_quiz(qid, period), per_quiz=True)
            mine = lb.rank_of(self.actor, qid) if self.user["role"] == "student" else None
        if mine:
            print(f"\n  Your rank: {mine['rank']} of {mine['out_of']}")

    def my_certificates(self) -> None:
        certs = ResultManager(self.db).certificates(self.actor)
        if not certs:
            print("  No certificates yet — pass an exam to earn one.")
            return
        for r in certs:
            print(f"  {r['result_id']}  {r['quiz_title'][:34]:<35}{r['percent']:>6.1f}%  {r['grade']:<3}{r['submitted_at'][:10]}"
                  f"  code {r['certificate_code']}")
        rid = ask("Result ID to download (blank = back)")
        if rid:
            r = ResultManager(self.db).get(rid)
            if r["username"] != self.actor:
                raise QuizError("That certificate belongs to someone else.")
            print(f"  ✔ Saved: {self.reports().certificate_pdf(r['result_id'])}")

    def my_bookmarks(self) -> None:
        bs = self.qm().bookmarks(self.actor)
        if not bs:
            print("  No bookmarks. Press * during a quiz to bookmark a question.")
            return
        for b in bs:
            q = b["question"]
            print(f"\n  {q['question_id']} [{q['category']} · {q['difficulty']}] {q['text']}")
            print(f"      Answer: {q['options'][q['answer']]}" + (f" — {q['explanation']}" if q["explanation"] else ""))
        qid = ask("\n  Question ID to remove from bookmarks (blank = keep all)")
        if qid:
            self.qm().remove_bookmark(self.actor, qid)
            print("  ✔ Removed.")

    def my_profile(self) -> None:
        u = UserService(self.db).get(self.actor)
        print(f"  {u['name']} ({u['username']}) · {u.get('email') or '-'} · {u.get('phone') or '-'} · "
              f"{u.get('institution') or '-'} · joined {u['created_at'][:10]}")
        if confirm("Update profile?"):
            UserService(self.db, self.actor).update_profile(self.actor, ask("Name", u["name"]),
                                                            ask("Email", u.get("email") or None),
                                                            ask("Mobile", u.get("phone") or None),
                                                            ask("Institution", u.get("institution") or None))
            print("  ✔ Updated.")

    # ======================================================= staff portal
    def staff_portal(self) -> None:
        self.dashboard()
        self.loop(f"STAFF PORTAL — {self.user['name']} ({self.user['role']})", [
            ("Admin dashboard", self.dashboard, None, False), ("Categories", self.category_menu, "categories", True),
            ("Questions", self.question_menu, "questions", True), ("Quizzes", self.quiz_menu, "quizzes", True),
            ("Results & analysis", self.results_menu, "results", True),
            ("Leaderboard", self.leaderboard, "leaderboard", False), ("Reports", self.report_menu, "reports", True),
            ("Users", self.user_menu, "users", True), ("Admin panel (activity log, backup)", self.admin_menu, "admin", True),
            ("Change password", self.change_password, None, False)])

    def dashboard(self) -> None:
        d = AdminPanel(self.db).dashboard()
        header("ADMIN DASHBOARD")
        print(f"  Students {d['students']} (active today {d['active_today']}) · staff {d['staff']}")
        print(f"  Questions {d['questions']} active ({', '.join(f'{k} {v}' for k, v in d['by_difficulty'].items())})"
              f" · {d['disabled_questions']} disabled")
        print(f"  Quizzes {d['quizzes']} ({d['published']} published)")
        print(f"  Attempts {d['attempts']} (exam {d['exam_attempts']}, practice {d['practice_attempts']}) · today {d['attempts_today']}")
        print(f"  Exam average {d['average']}% · pass rate {d['pass_rate']}% · certificates {d['certificates']}")
        if d["top_students"]:
            print("\n  Top students:")
            print_board(d["top_students"], per_quiz=False)
        if d["recent"]:
            print("\n  Recent attempts:")
            for r in d["recent"]:
                print(f"    {r['submitted_at'][:16].replace('T', ' ')}  {r['username']:<12}{r['quiz_title'][:28]:<29}"
                      f"{r['mode']:<9}{r['percent']:>6.1f}%")

    # --------------------------------------------------------- categories
    def category_menu(self) -> None:
        cm = CategoryManager(self.db, self.actor)

        def listing():
            for c in cm.stats():
                print(f"  {c['name']:<26}{c['questions']:>4} questions (E {c['easy']} · M {c['medium']} · H {c['hard']})"
                      f"  {c['description']}")
        self.submenu("CATEGORIES", [
            ("List categories", listing),
            ("Add category", lambda: print(f"  ✔ Added '{cm.add(ask('Name'), ask('Description'))['name']}'.")),
            ("Edit category", lambda: (lambda c: (cm.update(c, ask("New name", c), ask("Description")),
                                                  print("  ✔ Updated.")))(choose("Category", cm.names()))),
            ("Delete category", lambda: (cm.delete(choose("Category", cm.names())), print("  ✔ Deleted.")))])

    # ---------------------------------------------------------- questions
    def question_menu(self) -> None:
        self.submenu("QUESTIONS", [
            ("List questions", self.list_questions), ("Search questions", lambda: self._print_questions(self.qm().search(ask("Keyword")))),
            ("View a question", self.view_question), ("Add question", self.add_question),
            ("Edit question", self.edit_question),
            ("Enable / disable question", lambda: (lambda q: (self.qm().set_active(q["question_id"], not q["active"]),
                                                              print(f"  ✔ {'Disabled' if q['active'] else 'Enabled'}.")))(self.qm().get(ask("Question ID")))),
            ("Delete question", lambda: (self.qm().delete(ask("Question ID")), print("  ✔ Deleted."))),
            ("Import questions from CSV", self.import_questions),
            ("Export questions to CSV", lambda: print(f"  ✔ Saved: {self.qm().export_csv(self.report_dir / 'questions_export.csv')}")),
            ("Question analysis (hardest first)", self.item_analysis)])

    def _print_questions(self, qs: list[dict]) -> None:
        if not qs:
            print("  No questions.")
            return
        for q in qs:
            print(f"  {q['question_id']}  {q['category'][:16]:<17}{q['difficulty']:<7}{q['qtype']:<11}"
                  f"{q['text'][:40]:<41}{'' if q['active'] else '(disabled)'}")
        print(f"\n  {len(qs)} question(s)")

    def list_questions(self) -> None:
        cat = choose("Category (blank = all)", CategoryManager(self.db).names(), allow_blank=True) or None
        diff = choose("Difficulty (blank = all)", DIFFICULTIES, allow_blank=True) or None
        self._print_questions(self.qm().list(cat, diff, include_inactive=True))

    def view_question(self) -> None:
        q = self.qm().get(ask("Question ID"))
        header(f"{q['question_id']} — {q['category']} · {q['difficulty']} · {q['qtype']} · {q['marks']} mark(s)")
        print(wrap(q["text"]))
        for k, o in enumerate(q["options"]):
            print(f"     {chr(65 + k)}) {o}{'   ✔ correct' if k == q['answer'] else ''}")
        if q["explanation"]:
            print(wrap("Explanation: " + q["explanation"]))
        print(f"\n  Status: {'active' if q['active'] else 'disabled'} · created by {q['created_by']}")

    def add_question(self) -> None:
        header("ADD QUESTION")
        cat = choose("Category", CategoryManager(self.db).names())
        diff = choose("Difficulty", DIFFICULTIES)
        qtype = choose("Type", QUESTION_TYPES)
        text = ask("Question text")
        options = []
        if qtype == "MCQ":
            print("  Enter 2-6 options (blank to finish).")
            while len(options) < utils.MAX_OPTIONS:
                o = ask(f"Option {chr(65 + len(options))}")
                if not o:
                    break
                options.append(o)
        answer = ask("Correct answer (letter)" if qtype == "MCQ" else "Correct answer (True/False)")
        q = self.qm().add(cat, diff, text, options, answer, ask("Explanation (shown after answering)"), qtype,
                          ask(f"Marks (blank = {utils.DIFFICULTY_MARKS[diff]})") or None)
        print(f"  ✔ Added {q['question_id']}.")

    def edit_question(self) -> None:
        q = self.qm().get(ask("Question ID"))
        print("  Leave blank to keep the current value.")
        changes = {"text": ask("Question", q["text"]), "explanation": ask("Explanation", q["explanation"] or None),
                   "marks": ask("Marks", str(q["marks"]))}
        if confirm("Change difficulty / category?"):
            changes["difficulty"] = choose("Difficulty", DIFFICULTIES)
            changes["category"] = choose("Category", CategoryManager(self.db).names())
        if q["qtype"] == "MCQ" and confirm("Change options?"):
            opts = []
            for k in range(utils.MAX_OPTIONS):
                o = ask(f"Option {chr(65 + k)}", q["options"][k] if k < len(q["options"]) else None)
                if not o:
                    break
                opts.append(o)
            changes["options"] = opts
            changes["answer"] = ask("Correct answer (letter)")
        elif confirm("Change correct answer?"):
            changes["answer"] = ask("Correct answer")
        self.qm().update(q["question_id"], **changes)
        print("  ✔ Updated.")

    def import_questions(self) -> None:
        print("  Columns: Category, Difficulty, Type, Question, Option A-F, Answer (letter), Explanation, Marks")
        r = self.qm().import_csv(Path(ask("CSV file path").strip('"')))
        print(f"  ✔ Imported {r['added']} question(s).")
        for s in r["skipped"][:15]:
            print(f"    ✖ {s}")

    def item_analysis(self) -> None:
        rows = self.qm().item_analysis()
        if not rows:
            print("  No attempts yet.")
            return
        print(f"  {'ID':<7}{'Correct':>8}{'Skipped':>9}{'Tries':>7}  Question")
        for s in rows[:25]:
            flag = "  ⚠ review" if s["correct_pct"] < 30 and s["attempts"] >= 5 else ""
            print(f"  {s['question']['question_id']:<7}{s['correct_pct']:>7.1f}%{s['skipped_pct']:>8.1f}%{s['attempts']:>7}  "
                  f"{s['question']['text'][:40]}{flag}")

    # ------------------------------------------------------------ quizzes
    def quiz_menu(self) -> None:
        qzm = self.quizzes()

        def listing():
            for q in qzm.list():
                print(f"  {q['quiz_id']}  {q['title'][:30]:<31}{q['category'][:16]:<17}{q['difficulty']:<8}{q['num_questions']:>3} Q "
                      f"{q['time_limit_min']:>3} min  neg {q['negative_marking']:<5g}pass {q['pass_percent']:g}%  "
                      f"att {q['max_attempts'] or '∞'}  {'PUBLISHED' if q['published'] else 'draft'}  "
                      f"(pool {len(qzm.pool(q))})")

        def create():
            header("CREATE QUIZ")
            q = qzm.create(ask("Title"), choose("Category", [MIXED] + CategoryManager(self.db).names()),
                           choose("Difficulty", [MIXED] + DIFFICULTIES), ask("Number of questions", "10"),
                           ask("Time limit in minutes (0 = untimed)", "10"),
                           ask("Negative marking per wrong answer (0-1 × marks)", "0"), ask("Pass mark %", "50"),
                           ask("Maximum exam attempts (0 = unlimited)", "3"), ask("Description"),
                           confirm("Shuffle answer options?"))
            print(f"  ✔ Created {q['quiz_id']} ({len(qzm.pool(q))} matching questions).")
            if confirm("Publish now?"):
                qzm.publish(q["quiz_id"])
                print("  ✔ Published.")

        def edit():
            q = qzm.get(ask("Quiz ID"))
            print("  Leave blank to keep the current value.")
            qzm.update(q["quiz_id"], title=ask("Title", q["title"]), num_questions=ask("Questions", str(q["num_questions"])),
                       time_limit_min=ask("Time limit (min)", str(q["time_limit_min"])),
                       negative_marking=ask("Negative marking", f"{q['negative_marking']:g}"),
                       pass_percent=ask("Pass mark %", f"{q['pass_percent']:g}"),
                       max_attempts=ask("Max attempts", str(q["max_attempts"])))
            print("  ✔ Updated.")

        def toggle():
            q = qzm.get(ask("Quiz ID"))
            (qzm.unpublish if q["published"] else qzm.publish)(q["quiz_id"])
            print(f"  ✔ {'Unpublished' if q['published'] else 'Published'}.")
        self.submenu("QUIZZES", [("List quizzes", listing), ("Create quiz", create), ("Edit quiz", edit),
                                 ("Publish / unpublish", toggle),
                                 ("Delete quiz (no results only)", lambda: (qzm.delete(ask("Quiz ID")), print("  ✔ Deleted."))),
                                 ("Try a quiz (practice preview)", lambda: self.run_session(
                                     QuizSession(self.db, self.actor, qzm.get(ask("Quiz ID")), "Practice")))])

    # ------------------------------------------------------------ results
    def results_menu(self) -> None:
        rm, an = ResultManager(self.db), PerformanceAnalyzer(self.db)

        def listing():
            qid = ask("Quiz ID (blank = all)") or None
            user = ask("Username (blank = all)") or None
            for r in rm.list(user, qid)[:40]:
                print(f"  {r['result_id']}  {r['submitted_at'][:16].replace('T', ' ')}  {r['username']:<12}"
                      f"{r['quiz_title'][:26]:<27}{r['mode']:<9}{r['percent']:>6.1f}%  {r['grade']}")

        def detail():
            r = rm.get(ask("Result ID"))
            print_result_summary(r)
            print_review(r)

        def quiz_stats():
            q = an.quiz(ask("Quiz ID").upper())
            if not q["attempts"]:
                print("  No exam attempts yet.")
                return
            header(f"QUIZ ANALYSIS — {q['title']}")
            print(f"  Attempts {q['attempts']} by {q['students']} student(s) · average {q['average']}% · "
                  f"high {q['highest']:.1f}% · low {q['lowest']:.1f}% · pass rate {q['pass_rate']}%")
            print(f"  Average time {fmt_duration(q['avg_duration'])} · submitted at time-up {q['time_ups']}")
            print("  Grades: " + "  ".join(f"{g}: {n}" for g, n in q["grade_distribution"].items()))
            if q["hardest"]:
                print("\n  Hardest questions:")
                for h in q["hardest"]:
                    print(f"    {h['correct_pct']:>5.1f}% correct  {h['text'][:60]}")
        self.submenu("RESULTS & ANALYSIS", [
            ("Browse results", listing), ("Result details & answers", detail),
            ("Result PDF", lambda: print(f"  ✔ Saved: {self.reports().result_pdf(ask('Result ID'))}")),
            ("Quiz analysis", quiz_stats), ("Student performance", lambda: self._print_analysis(ask("Username").lower()))])

    # ------------------------------------------------------------ reports
    def report_menu(self) -> None:
        rg = self.reports()
        saved = lambda p: print(f"  ✔ Saved: {p}")  # noqa: E731
        self.submenu("REPORTS", [
            ("Quiz report (PDF with grade chart)", lambda: saved(rg.quiz_pdf(ask("Quiz ID").upper()))),
            ("Student performance report (PDF with charts)", lambda: saved(rg.performance_pdf(ask("Username").lower()))),
            ("Results (CSV)", lambda: saved(rg.results_csv(ask("Quiz ID (blank = all)").upper() or None))),
            ("Leaderboard (CSV)", lambda: saved(rg.leaderboard_csv(ask("Quiz ID (blank = overall)").upper() or None))),
            ("Question analysis (CSV)", lambda: saved(rg.item_analysis_csv())),
            ("Users (CSV)", lambda: saved(rg.users_csv()))])

    # -------------------------------------------------------------- users
    def user_menu(self) -> None:
        us = UserService(self.db, self.actor)

        def listing():
            for u in us.search(ask("Search (blank = all)")):
                state = "LOCKED" if u["failed_attempts"] >= 5 else ("active" if u["active"] else "inactive")
                print(f"  {u['username']:<14}{u['name'][:22]:<23}{u['role']:<11}{state:<9}"
                      f"last login {(u['last_login'] or '-').replace('T', ' ')[:16]}")

        def add_staff():
            u, temp = us.add(ask("Username"), ask("Full name"), choose("Role", [r for r in ROLES if r != "student"]),
                             ask("Phone (optional)"), ask("Email (optional)"))
            print(f"  ✔ {u['username']} created. Temporary password: {temp}")
        self.submenu("USERS", [
            ("List / search users", listing), ("Add staff account", add_staff),
            ("Change role", lambda: (us.set_role(ask("Username"), choose("Role", ROLES)), print("  ✔ Updated."))),
            ("Activate / deactivate", lambda: (lambda u: (us.set_active(u["username"], not u["active"]),
                                                          print("  ✔ Done.")))(us.get(ask("Username")))),
            ("Reset password / unlock", lambda: print(f"  ✔ Temporary password: {self.auth.reset_password(ask('Username'), self.actor)}")),
            ("Delete student (no results only)", lambda: (us.delete_student(ask("Username")), print("  ✔ Deleted.")))])

    # -------------------------------------------------------------- admin
    def admin_menu(self) -> None:
        panel = AdminPanel(self.db)

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
            ("Activity log", lambda: [print(f"  {a['at'].replace('T', ' ')}  {a['user']:<12}{a['action']:<18}{a['details']}")
                                      for a in panel.activity(40, ask("Filter by user (blank = all)") or None)]),
            ("Record counts", lambda: [print(f"  {k:<12}{v:>7}") for k, v in panel.record_counts().items()]),
            ("Create backup", lambda: print(f"  ✔ Backup created: {self.backup.create_backup().name}")),
            ("List backups", lambda: print("\n".join(f"  {b.name}" for b in self.backup.list_backups()) or "  None.")),
            ("Restore backup", restore)])


def main() -> None:
    try:
        App().run()
    except (KeyboardInterrupt, EOFError):
        print("\n  Goodbye!")
    except QuizError as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
