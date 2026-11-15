"""Quiz Engine: quiz definitions, random question selection with difficulty
balancing, timed sessions, practice vs exam modes, negative marking and scoring."""
from __future__ import annotations

import random
import time
from collections import Counter

from .auth import log_activity
from .categories import CategoryManager
from .database import JSONDatabase
from .questions import QuestionManager
from .results import ResultManager
from .utils import (DEFAULT_PASS_PERCENT, DIFFICULTIES, MODES, QuizError, NotFoundError, QuizRuleError, ValidationError,
                    grade_for, now_str, validate_choice, validate_float, validate_int, validate_text)

MIXED = "Mixed"
MIX_RATIO = {"Easy": 0.4, "Medium": 0.4, "Hard": 0.2}       # target share when difficulty is Mixed


# ================================================================ definitions
class QuizManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.questions = QuestionManager(db, actor)
        self.categories = CategoryManager(db, actor)

    def _next_id(self) -> str:
        nums = [int(q["quiz_id"][2:]) for q in self.db.all("quizzes")]
        return f"QZ{(max(nums) + 1) if nums else 1:03d}"

    def _clean(self, data: dict) -> dict:
        out = {}
        if "title" in data:
            out["title"] = validate_text(data["title"], "Title", 80, required=True)
        if "description" in data:
            out["description"] = validate_text(data["description"], "Description", 200)
        if "category" in data:
            out["category"] = MIXED if str(data["category"] or "").strip().lower() in ("", "mixed", "all") \
                else self.categories.get(data["category"])["name"]
        if "difficulty" in data:
            out["difficulty"] = validate_choice(data["difficulty"] or MIXED, DIFFICULTIES + [MIXED], "difficulty")
        if "num_questions" in data:
            out["num_questions"] = validate_int(data["num_questions"], "Number of questions", 1, 100)
        if "time_limit_min" in data:
            out["time_limit_min"] = validate_int(data["time_limit_min"] or 0, "Time limit (minutes)", 0, 180)
        if "negative_marking" in data:
            out["negative_marking"] = validate_float(data["negative_marking"] or 0, "Negative marking", 0, 1)
        if "pass_percent" in data:
            out["pass_percent"] = validate_float(data["pass_percent"] or DEFAULT_PASS_PERCENT, "Pass mark %", 1, 100)
        if "max_attempts" in data:
            out["max_attempts"] = validate_int(data["max_attempts"] or 0, "Maximum attempts", 0, 20)
        if "shuffle_options" in data:
            out["shuffle_options"] = bool(data["shuffle_options"])
        return out

    def create(self, title: str, category: str = MIXED, difficulty: str = MIXED, num_questions=10, time_limit_min=10,
               negative_marking=0.0, pass_percent=DEFAULT_PASS_PERCENT, max_attempts=3, description: str = "",
               shuffle_options: bool = True, publish: bool = False) -> dict:
        clean = self._clean({"title": title, "category": category, "difficulty": difficulty,
                             "num_questions": num_questions, "time_limit_min": time_limit_min,
                             "negative_marking": negative_marking, "pass_percent": pass_percent,
                             "max_attempts": max_attempts, "description": description,
                             "shuffle_options": shuffle_options})
        if any(q["title"].lower() == clean["title"].lower() for q in self.db.all("quizzes")):
            raise ValidationError(f"A quiz titled '{clean['title']}' already exists.")
        quiz = {"quiz_id": self._next_id(), **clean, "published": False, "created_by": self.actor,
                "created_at": now_str()}
        self.db.insert("quizzes", quiz)
        log_activity(self.db, self.actor, "QUIZ_CREATED", f"{quiz['quiz_id']} {quiz['title']}")
        return self.publish(quiz["quiz_id"]) if publish else quiz

    def get(self, quiz_id: str) -> dict:
        q = self.db.find_one("quizzes", quiz_id=str(quiz_id or "").strip().upper())
        if not q:
            raise NotFoundError(f"Quiz '{quiz_id}' not found.")
        return q

    def list(self, published_only: bool = False) -> list[dict]:
        qs = self.db.all("quizzes")
        if published_only:
            qs = [q for q in qs if q["published"]]
        return sorted(qs, key=lambda q: q["quiz_id"])

    def pool(self, quiz: dict) -> list[dict]:
        cat = None if quiz["category"] == MIXED else quiz["category"]
        diff = None if quiz["difficulty"] == MIXED else quiz["difficulty"]
        return self.questions.list(cat, diff)

    def update(self, quiz_id: str, **changes) -> dict:
        q = self.get(quiz_id)
        clean = self._clean({k: v for k, v in changes.items() if v is not None})
        if not clean:
            raise ValidationError("Nothing to update.")
        merged = {**q, **clean}
        if merged["published"] and len(self.pool(merged)) < merged["num_questions"]:
            raise QuizRuleError("Not enough active questions for this setting; unpublish first or add questions.")
        log_activity(self.db, self.actor, "QUIZ_UPDATED", q["quiz_id"])
        return self.db.update("quizzes", "quiz_id", q["quiz_id"], clean)

    def publish(self, quiz_id: str) -> dict:
        q = self.get(quiz_id)
        available = len(self.pool(q))
        if available < q["num_questions"]:
            raise QuizRuleError(f"Only {available} matching active question(s); the quiz needs {q['num_questions']}.")
        log_activity(self.db, self.actor, "QUIZ_PUBLISHED", q["quiz_id"])
        return self.db.update("quizzes", "quiz_id", q["quiz_id"], {"published": True})

    def unpublish(self, quiz_id: str) -> dict:
        q = self.get(quiz_id)
        return self.db.update("quizzes", "quiz_id", q["quiz_id"], {"published": False})

    def delete(self, quiz_id: str) -> None:
        q = self.get(quiz_id)
        if self.db.find("results", quiz_id=q["quiz_id"]):
            raise QuizError("This quiz has results; unpublish it instead of deleting.")
        self.db.delete("quizzes", "quiz_id", q["quiz_id"])
        log_activity(self.db, self.actor, "QUIZ_DELETED", q["quiz_id"])

    @staticmethod
    def practice_quiz(category: str | None, difficulty: str | None, n: int) -> dict:
        """An ad-hoc practice quiz definition (not stored)."""
        return {"quiz_id": "PRACTICE", "title": f"Practice: {category or 'All categories'}"
                + (f" ({difficulty})" if difficulty else ""), "category": category or MIXED,
                "difficulty": difficulty or MIXED, "num_questions": n, "time_limit_min": 0, "negative_marking": 0.0,
                "pass_percent": DEFAULT_PASS_PERCENT, "max_attempts": 0, "shuffle_options": True, "published": True}


# ================================================================ selection
def select_questions(pool: list[dict], n: int, difficulty: str, seen: Counter, rng: random.Random) -> list[dict]:
    """Pick n questions at random. Questions the student has seen least are preferred, and
    a Mixed quiz is balanced across difficulty levels (40 % easy, 40 % medium, 20 % hard)."""
    if len(pool) < n:
        raise QuizRuleError(f"Only {len(pool)} question(s) available; {n} needed.")

    def freshest(qs: list[dict], k: int) -> list[dict]:
        shuffled = qs[:]
        rng.shuffle(shuffled)
        return sorted(shuffled, key=lambda q: seen[q["question_id"]])[:k]   # stable: random within equal counts

    if difficulty != MIXED:
        chosen = freshest(pool, n)
    else:
        by_diff = {d: [q for q in pool if q["difficulty"] == d] for d in DIFFICULTIES}
        targets = {d: int(round(n * MIX_RATIO[d])) for d in DIFFICULTIES}
        targets["Medium"] += n - sum(targets.values())
        chosen = []
        for d in DIFFICULTIES:
            chosen += freshest(by_diff[d], min(targets[d], len(by_diff[d])))
        if len(chosen) < n:                                  # fill any shortfall from what is left
            ids = {q["question_id"] for q in chosen}
            chosen += freshest([q for q in pool if q["question_id"] not in ids], n - len(chosen))
    rng.shuffle(chosen)
    return chosen


# ================================================================== session
class QuizSession:
    """One attempt at a quiz. The clock is injectable for testing."""

    def __init__(self, db: JSONDatabase, username: str, quiz: dict, mode: str = "Exam",
                 questions: list[dict] | None = None, clock=time.monotonic, rng: random.Random | None = None):
        self.db = db
        self.username = username
        self.quiz = quiz
        self.mode = validate_choice(mode, MODES, "mode")
        self.clock = clock
        self.rng = rng or random.Random()
        self.results = ResultManager(db)
        if not quiz.get("published"):
            raise QuizRuleError("This quiz is not published yet.")
        if self.mode == "Exam":
            if quiz["quiz_id"] == "PRACTICE":
                raise QuizRuleError("Ad-hoc practice sets can only be taken in Practice mode.")
            used = self.results.attempt_count(username, quiz["quiz_id"], "Exam")
            if quiz["max_attempts"] and used >= quiz["max_attempts"]:
                raise QuizRuleError(f"You have used all {quiz['max_attempts']} exam attempt(s) for this quiz.")
        if questions is None:
            pool = QuizManager(db).pool(quiz)
            seen = Counter(a["question_id"] for r in self.results.list(username) for a in r["answers"])
            questions = select_questions(pool, quiz["num_questions"], quiz["difficulty"], seen, self.rng)
        if not questions:
            raise QuizRuleError("No questions to ask.")
        self.items = []
        for q in questions:
            order = list(range(len(q["options"])))
            if quiz.get("shuffle_options", True) and q["qtype"] == "MCQ":
                self.rng.shuffle(order)
            self.items.append({"q": q, "order": order, "choice": None, "answered_at": None})
        self.started_at = now_str()
        self._start = clock()
        self.submitted = None
        log_activity(db, username, "QUIZ_STARTED", f"{quiz['quiz_id']} {self.mode}")

    # ---------------------------------------------------------------- timer
    @property
    def time_limit(self) -> int:
        """Seconds; 0 = untimed. Practice mode is always untimed."""
        return 0 if self.mode == "Practice" else self.quiz["time_limit_min"] * 60

    def elapsed(self) -> float:
        return self.clock() - self._start

    def remaining(self) -> float | None:
        return None if not self.time_limit else max(0.0, self.time_limit - self.elapsed())

    def time_up(self) -> bool:
        return bool(self.time_limit) and self.elapsed() >= self.time_limit

    # ------------------------------------------------------------- questions
    def __len__(self) -> int:
        return len(self.items)

    def view(self, i: int) -> dict:
        it = self.items[i]
        q = it["q"]
        return {"number": i + 1, "of": len(self.items), "question_id": q["question_id"], "text": q["text"],
                "options": [q["options"][k] for k in it["order"]], "difficulty": q["difficulty"],
                "category": q["category"], "marks": q["marks"], "qtype": q["qtype"],
                "chosen": None if it["choice"] is None else it["order"].index(it["choice"])}

    def answer(self, i: int, display_choice) -> dict | None:
        """Record an answer (display_choice is 0-based in the shuffled order, or a letter).
        Practice mode returns immediate feedback; exam mode returns None."""
        if self.submitted:
            raise QuizRuleError("This attempt has already been submitted.")
        if self.time_up():
            raise QuizRuleError("Time is up — answers can no longer be changed.")
        it = self.items[i]
        if isinstance(display_choice, str):
            c = display_choice.strip().upper()
            if len(c) != 1 or not "A" <= c <= chr(64 + len(it["order"])):
                raise ValidationError(f"Choose A-{chr(64 + len(it['order']))}.")
            display_choice = ord(c) - 65
        if not 0 <= display_choice < len(it["order"]):
            raise ValidationError("Invalid option.")
        it["choice"] = it["order"][display_choice]
        it["answered_at"] = round(self.elapsed(), 1)
        if self.mode == "Practice":
            q = it["q"]
            return {"correct": it["choice"] == q["answer"], "correct_letter": chr(65 + it["order"].index(q["answer"])),
                    "correct_text": q["options"][q["answer"]], "explanation": q["explanation"]}
        return None

    def clear(self, i: int) -> None:
        if not self.time_up() and not self.submitted:
            self.items[i]["choice"] = None

    def unanswered(self) -> list[int]:
        return [i for i, it in enumerate(self.items) if it["choice"] is None]

    def bookmark(self, i: int, note: str = "") -> dict:
        return QuestionManager(self.db).bookmark(self.username, self.items[i]["q"]["question_id"], note)

    # ---------------------------------------------------------------- submit
    def submit(self) -> dict:
        if self.submitted:
            return self.submitted
        time_up = self.time_up()
        neg = self.quiz["negative_marking"] if self.mode == "Exam" else 0.0
        answers, total, maximum = [], 0.0, 0
        for it in self.items:
            q = it["q"]
            if it["choice"] is None:
                status, marks = "SKIPPED", 0.0
            elif it["choice"] == q["answer"]:
                status, marks = "CORRECT", float(q["marks"])
            else:
                status, marks = "WRONG", -round(neg * q["marks"], 2)
            total += marks
            maximum += q["marks"]
            answers.append({"question_id": q["question_id"], "text": q["text"], "options": q["options"],
                            "answer": q["answer"], "chosen": it["choice"], "status": status, "marks": marks,
                            "max_marks": q["marks"], "difficulty": q["difficulty"], "category": q["category"],
                            "explanation": q["explanation"]})
        score = round(max(0.0, total), 2)
        percent = round(score / maximum * 100, 2) if maximum else 0.0
        grade, remark = grade_for(percent)
        counts = Counter(a["status"] for a in answers)
        duration = min(self.elapsed(), self.time_limit) if self.time_limit else self.elapsed()
        result = {"username": self.username, "quiz_id": self.quiz["quiz_id"], "quiz_title": self.quiz["title"],
                  "category": self.quiz["category"], "mode": self.mode, "started_at": self.started_at,
                  "submitted_at": now_str(), "duration_sec": round(duration, 1), "time_limit_sec": self.time_limit,
                  "time_up": time_up, "answers": answers, "correct": counts["CORRECT"], "wrong": counts["WRONG"],
                  "skipped": counts["SKIPPED"], "score": score, "max_score": maximum, "percent": percent,
                  "negative_marks": round(-sum(a["marks"] for a in answers if a["marks"] < 0), 2),
                  "grade": grade, "remark": remark, "pass_percent": self.quiz["pass_percent"],
                  "passed": percent >= self.quiz["pass_percent"]}
        self.submitted = self.results.save(result)
        log_activity(self.db, self.username, "QUIZ_SUBMITTED",
                     f"{self.quiz['quiz_id']} {self.mode} {percent:.1f}% {grade}" + (" (time up)" if time_up else ""))
        return self.submitted


def bookmark_practice(db: JSONDatabase, username: str, n: int | None = None, rng: random.Random | None = None) -> list[dict]:
    """Questions for a practice round made from the student's bookmarks."""
    qs = [b["question"] for b in QuestionManager(db).bookmarks(username) if b["question"]["active"]]
    if not qs:
        raise QuizRuleError("You have no bookmarked questions yet.")
    rng = rng or random.Random()
    rng.shuffle(qs)
    return qs[:n] if n else qs
