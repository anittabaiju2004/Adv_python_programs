"""Unit tests — run with:  python -m pytest -q"""
import json
import random
from collections import Counter

import pytest

from quiz.admin import AdminPanel
from quiz.analysis import PerformanceAnalyzer
from quiz.auth import AuthManager, UserManager, can, require
from quiz.backup import BackupManager
from quiz.categories import CategoryManager
from quiz.database import JSONDatabase
from quiz.engine import QuizManager, QuizSession, bookmark_practice, select_questions
from quiz.leaderboard import Leaderboard
from quiz.questions import QuestionManager
from quiz.reports import ReportGenerator
from quiz.results import ResultManager
from quiz.users import UserService
from quiz.utils import (AuthenticationError, BackupError, DatabaseError, NotFoundError, PermissionDenied, QuizError,
                        QuizRuleError, ValidationError, grade_for)


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def db(tmp_path):
    d = JSONDatabase(tmp_path / "data")
    AuthManager(d)
    return d


@pytest.fixture
def bank(db):
    """Python: 4 easy, 4 medium, 2 hard (marks 1/2/3). GK: 3 easy."""
    CategoryManager(db).add("Python")
    CategoryManager(db).add("GK")
    qm = QuestionManager(db, "teacher")
    for i in range(4):
        qm.add("Python", "Easy", f"Easy question {i}?", [f"right{i}", f"w{i}a", f"w{i}b", f"w{i}c"], "A", f"Because {i}")
        qm.add("Python", "Medium", f"Medium question {i}?", [f"m{i}x", f"mright{i}", f"m{i}y", f"m{i}z"], "B")
    for i in range(2):
        qm.add("Python", "Hard", f"Hard question {i}?", [f"h{i}a", f"h{i}b", f"hright{i}"], "C")
    for i in range(3):
        qm.add("GK", "Easy", f"GK fact {i} is true.", qtype="True/False", answer="True")
    return qm


@pytest.fixture
def student(db):
    return UserService(db).register_student("anitta", "Anitta Joseph", "pass1234", "pass1234", "anitta@x.com")


@pytest.fixture
def exam(db, bank):
    return QuizManager(db, "teacher").create("Python Basics", "Python", "Mixed", 5, time_limit_min=2,
                                             negative_marking=0.25, pass_percent=50, max_attempts=2, publish=True)


def answer_all(s: QuizSession, correct: bool = True, skip: set = frozenset()):
    for i in range(len(s)):
        if i in skip:
            continue
        it = s.items[i]
        target = it["q"]["answer"] if correct else next(k for k in range(len(it["q"]["options"])) if k != it["q"]["answer"])
        s.answer(i, it["order"].index(target))


# ================================================================ basics
def test_grading_scale():
    assert grade_for(95) == ("A+", "Outstanding") and grade_for(80)[0] == "A" and grade_for(49.99)[0] == "F"


def test_users_and_roles(db, student):
    auth = AuthManager(db)
    u = auth.login("anitta", "pass1234")
    assert u["role"] == "student" and can(u, "take") and not can(u, "questions")
    with pytest.raises(PermissionDenied):
        require(u, "reports")
    with pytest.raises(ValidationError):
        UserService(db).register_student("anitta", "X Y", "pass1234", "pass1234")
    with pytest.raises(ValidationError):
        UserService(db).register_student("bob", "Bob", "short", "short")
    with pytest.raises(ValidationError, match="email"):
        UserService(db).register_student("bob", "Bob", "pass1234", "pass1234", "ANITTA@x.com")
    _, temp = UserManager(db, "admin").add("teacher", "Meera Pillai", "instructor")
    t = auth.login("teacher", temp)
    assert t["must_change_password"] and can(t, "questions") and not can(t, "admin")


# ============================================================= questions
def test_question_validation_and_csv(db, bank, tmp_path):
    with pytest.raises(ValidationError, match="different"):
        bank.add("Python", "Easy", "Dup options?", ["a", "A", "b"], "A")
    with pytest.raises(ValidationError, match="needs"):
        bank.add("Python", "Easy", "One option?", ["only"], "A")
    with pytest.raises(ValidationError, match="Answer"):
        bank.add("Python", "Easy", "Bad key?", ["a", "b"], "D")
    with pytest.raises(ValidationError, match="already exists"):
        bank.add("Python", "Hard", "easy question 0?", ["x", "y"], "A")
    q = bank.add("Python", "Easy", "Answer by text?", ["red", "green"], "green")
    assert q["answer"] == 1 and q["marks"] == 1
    tf = bank.get("Q0011")
    assert tf["options"] == ["True", "False"] and tf["answer"] == 0
    path = bank.export_csv(tmp_path / "q.csv")
    db2 = JSONDatabase(tmp_path / "other")
    r = QuestionManager(db2).import_csv(path)
    assert r["added"] == 14 and not r["skipped"] and set(CategoryManager(db2).names()) == {"GK", "Python"}


def test_categories(db, bank):
    cm = CategoryManager(db)
    with pytest.raises(QuizError):
        cm.delete("Python")
    cm.update("Python", new_name="Python 3")
    assert len(bank.list("Python 3")) == 10
    stats = {c["name"]: c for c in cm.stats()}
    assert stats["Python 3"]["easy"] == 4 and stats["Python 3"]["hard"] == 2


# ================================================================ engine
def test_select_questions_balanced_and_fresh(bank):
    pool = bank.list("Python")
    rng = random.Random(1)
    chosen = select_questions(pool, 5, "Mixed", Counter(), rng)
    assert Counter(q["difficulty"] for q in chosen) == {"Easy": 2, "Medium": 2, "Hard": 1}
    seen = Counter({q["question_id"]: 1 for q in pool if q["difficulty"] == "Easy" and q["text"].endswith(("0?", "1?"))})
    fresh = select_questions([q for q in pool if q["difficulty"] == "Easy"], 2, "Easy", seen, rng)
    assert all(q["text"] in ("Easy question 2?", "Easy question 3?") for q in fresh)
    with pytest.raises(QuizRuleError):
        select_questions(pool, 50, "Mixed", Counter(), rng)


def test_quiz_publish_rules(db, bank):
    qm = QuizManager(db, "teacher")
    with pytest.raises(QuizRuleError, match="Only 2"):
        qm.create("Hard only", "Python", "Hard", 3, publish=True)
    qz = qm.create("Draft", "Python", "Easy", 3)
    assert not qz["published"]
    with pytest.raises(QuizRuleError, match="not published"):
        QuizSession(db, "anitta", qz, "Exam")


def test_exam_scoring_negative_marking_and_certificate(db, exam, student, tmp_path):
    s = QuizSession(db, "anitta", exam, "Exam", clock=FakeClock(), rng=random.Random(3))
    assert len(s) == 5 and s.view(0)["chosen"] is None
    for i in range(len(s)):                            # first two wrong, rest right
        it = s.items[i]
        target = it["q"]["answer"] if i >= 2 else (it["q"]["answer"] + 1) % len(it["q"]["options"])
        assert s.answer(i, it["order"].index(target)) is None           # no feedback in exam mode
    r = s.submit()
    marks = [it["q"]["marks"] for it in s.items]
    expected = sum(marks[2:]) - 0.25 * (marks[0] + marks[1])
    assert r["score"] == round(expected, 2) and r["max_score"] == sum(marks)
    assert r["negative_marks"] == 0.25 * (marks[0] + marks[1]) and r["wrong"] == 2 and r["correct"] == 3
    assert r["passed"] == (r["percent"] >= 50) and r["grade"] == grade_for(r["percent"])[0]
    s2 = QuizSession(db, "anitta", exam, "Exam", clock=FakeClock())
    answer_all(s2)
    r2 = s2.submit()
    assert r2["percent"] == 100 and r2["grade"] == "A+" and r2["certificate_code"]
    with pytest.raises(QuizRuleError, match="all 2"):
        QuizSession(db, "anitta", exam, "Exam")
    v = ResultManager(db).verify_certificate(r2["result_id"], r2["certificate_code"].lower())
    assert v["valid"] and v["name"] == "Anitta Joseph"
    assert not ResultManager(db).verify_certificate(r2["result_id"], "WRONGCODE")["valid"]
    rg = ReportGenerator(db, tmp_path)
    assert rg.certificate_pdf(r2["result_id"]).read_bytes()[:4] == b"%PDF"
    assert rg.result_pdf(r["result_id"]).read_bytes()[:4] == b"%PDF"


def test_timer(db, exam, student):
    clock = FakeClock()
    s = QuizSession(db, "anitta", exam, "Exam", clock=clock)
    s.answer(0, 0)
    clock.t = 60
    assert s.remaining() == 60 and not s.time_up()
    clock.t = 125
    assert s.time_up()
    with pytest.raises(QuizRuleError, match="Time is up"):
        s.answer(1, 0)
    r = s.submit()
    assert r["time_up"] and r["duration_sec"] == 120 and r["skipped"] == 4


def test_practice_mode_feedback_and_negative_free(db, exam, student):
    s = QuizSession(db, "anitta", exam, "Practice", clock=FakeClock())
    assert s.time_limit == 0
    it = s.items[0]
    wrong = next(k for k in range(len(it["q"]["options"])) if k != it["q"]["answer"])
    fb = s.answer(0, it["order"].index(wrong))
    assert fb["correct"] is False and fb["correct_text"] == it["q"]["options"][it["q"]["answer"]]
    r = s.submit()
    assert r["negative_marks"] == 0 and r["certificate_code"] is None
    for _ in range(3):                                  # practice attempts are unlimited
        QuizSession(db, "anitta", exam, "Practice").submit()
    with pytest.raises(QuizRuleError, match="Practice mode"):
        QuizSession(db, "anitta", QuizManager.practice_quiz("Python", None, 3), "Exam")
    adhoc = QuizSession(db, "anitta", QuizManager.practice_quiz("GK", "Easy", 3), "Practice")
    assert {it["q"]["category"] for it in adhoc.items} == {"GK"}


def test_letter_answers_and_bookmarks(db, exam, student, bank):
    s = QuizSession(db, "anitta", exam, "Exam", clock=FakeClock())
    s.answer(0, "a")
    with pytest.raises(ValidationError):
        s.answer(0, "Z")
    s.bookmark(1, "revise this")
    with pytest.raises(QuizError, match="already bookmarked"):
        s.bookmark(1)
    assert len(bank.bookmarks("anitta")) == 1
    qs = bookmark_practice(db, "anitta")
    assert len(qs) == 1
    bank.remove_bookmark("anitta", qs[0]["question_id"])
    with pytest.raises(QuizRuleError):
        bookmark_practice(db, "anitta")


def test_results_snapshot_survives_question_edit(db, exam, student, bank):
    s = QuizSession(db, "anitta", exam, "Exam", clock=FakeClock())
    answer_all(s)
    r = s.submit()
    qid = r["answers"][0]["question_id"]
    old_text = r["answers"][0]["text"]
    bank.update(qid, text="Edited wording?")
    assert ResultManager(db).get(r["result_id"])["answers"][0]["text"] == old_text
    with pytest.raises(QuizError, match="disable it"):
        bank.delete(qid)


# =========================================================== leaderboard
def test_leaderboard_ranking(db, exam):
    us = UserService(db)
    for name in ("asha", "bala", "chitra"):
        us.register_student(name, name.title(), "pass1234", "pass1234")
    for user, correct, secs in (("asha", True, 50), ("bala", True, 30), ("chitra", False, 20)):
        clock = FakeClock()
        s = QuizSession(db, user, exam, "Exam", clock=clock)
        answer_all(s, correct)
        clock.t = secs
        s.submit()
    board = Leaderboard(db).for_quiz(exam["quiz_id"])
    assert [b["username"] for b in board] == ["bala", "asha", "chitra"]          # same score: faster first
    assert [b["rank"] for b in board] == [1, 2, 3]
    assert Leaderboard(db).rank_of("asha", exam["quiz_id"])["out_of"] == 3
    assert Leaderboard(db).overall()[0]["average"] == 100


# ======================================================== analysis/reports
def test_analysis_reports_and_dashboard(db, exam, student, bank, tmp_path):
    for correct in (False, True, True):
        s = QuizSession(db, "anitta", exam, "Practice", clock=FakeClock())
        answer_all(s, correct)
        s.submit()
    s = QuizSession(db, "anitta", exam, "Exam", clock=FakeClock())
    answer_all(s)
    s.submit()
    a = PerformanceAnalyzer(db).student("anitta")
    assert a["attempts"] == 4 and a["exams"] == 1 and a["best"] == 100 and a["improvement"] > 0
    assert set(a["by_difficulty"]) <= {"Easy", "Medium", "Hard"}
    qa = PerformanceAnalyzer(db).quiz(exam["quiz_id"])
    assert qa["attempts"] == 1 and qa["pass_rate"] == 100
    rg = ReportGenerator(db, tmp_path)
    for p in (rg.performance_pdf("anitta"), rg.quiz_pdf(exam["quiz_id"]), rg.results_csv(), rg.leaderboard_csv(),
              rg.leaderboard_csv(exam["quiz_id"]), rg.item_analysis_csv(), rg.users_csv()):
        assert p.exists() and p.stat().st_size > 50
    d = AdminPanel(db).dashboard()
    assert d["attempts"] == 4 and d["exam_attempts"] == 1 and d["certificates"] == 1 and d["students"] == 1


# =========================================================== backup & db
def test_backup_and_persistence(db, bank, tmp_path):
    bk = BackupManager(db.data_dir, tmp_path / "b")
    archive = bk.create_backup()
    bank.add("GK", "Easy", "New question?", ["a", "b"], "A")
    bk.restore(archive)
    assert len(QuestionManager(JSONDatabase(db.data_dir)).list()) == 13
    assert json.loads((db.data_dir / "questions.json").read_text())[0]["question_id"] == "Q0001"
    (db.data_dir / "results.json").write_text("{x")
    with pytest.raises(DatabaseError):
        ResultManager(db).list()
    bad = tmp_path / "b" / "quiz_backup_bad.zip"
    bad.write_text("junk")
    with pytest.raises(BackupError):
        bk.restore(bad)
    with pytest.raises(NotFoundError):
        bank.get("Q9999")
    with pytest.raises(AuthenticationError):
        AuthManager(db).login("admin", "wrong")
