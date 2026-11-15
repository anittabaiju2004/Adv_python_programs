"""Question Management: MCQ and True/False questions with difficulty levels,
explanations, CSV import/export, bookmarks and per-question analysis."""
from __future__ import annotations

import csv
from pathlib import Path

from .auth import log_activity
from .categories import CategoryManager
from .database import JSONDatabase
from .utils import (DIFFICULTIES, DIFFICULTY_MARKS, MAX_BOOKMARKS, MAX_OPTIONS, MIN_OPTIONS, QUESTION_TYPES, QuizError,
                    NotFoundError, ValidationError, now_str, validate_choice, validate_int, validate_text)

CSV_HEADER = ["Category", "Difficulty", "Type", "Question", "Option A", "Option B", "Option C", "Option D",
              "Option E", "Option F", "Answer", "Explanation", "Marks"]


class QuestionManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.categories = CategoryManager(db, actor)

    def _next_id(self) -> str:
        nums = [int(q["question_id"][1:]) for q in self.db.all("questions")]
        return f"Q{(max(nums) + 1) if nums else 1:04d}"

    @staticmethod
    def _answer_index(answer, options: list[str]) -> int:
        """Accept the answer as a letter (A-F), a 1-based number, or the option text."""
        a = str(answer or "").strip()
        if len(a) == 1 and a.upper() in "ABCDEF" and ord(a.upper()) - 65 < len(options):
            return ord(a.upper()) - 65
        if a.isdigit() and 1 <= int(a) <= len(options):
            return int(a) - 1
        for i, o in enumerate(options):
            if o.lower() == a.lower():
                return i
        raise ValidationError(f"Answer must be one of A-{chr(64 + len(options))}, 1-{len(options)} or an option's text.")

    def _clean(self, data: dict, current: dict | None = None) -> dict:
        cur = current or {}
        qtype = validate_choice(data.get("qtype", cur.get("qtype", "MCQ")), QUESTION_TYPES, "question type")
        out = {"qtype": qtype}
        out["category"] = self.categories.get(data["category"])["name"] if "category" in data else cur["category"]
        out["difficulty"] = validate_choice(data["difficulty"], DIFFICULTIES, "difficulty") if "difficulty" in data \
            else cur["difficulty"]
        out["text"] = validate_text(data["text"], "Question", 500, required=True) if "text" in data else cur["text"]
        if qtype == "True/False":
            options = ["True", "False"]
        else:
            raw = data.get("options", cur.get("options", []))
            options = [validate_text(o, "Option", 200) for o in raw if str(o or "").strip()]
            if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
                raise ValidationError(f"An MCQ needs {MIN_OPTIONS}-{MAX_OPTIONS} options.")
            if len({o.lower() for o in options}) != len(options):
                raise ValidationError("Options must all be different.")
        out["options"] = options
        if "answer" in data:
            out["answer"] = self._answer_index(data["answer"], options)
        elif cur and cur.get("answer", 99) < len(options):
            out["answer"] = cur["answer"]
        else:
            raise ValidationError("Correct answer is required.")
        out["explanation"] = validate_text(data.get("explanation", cur.get("explanation", "")), "Explanation", 400)
        marks = data.get("marks", cur.get("marks"))
        out["marks"] = validate_int(marks, "Marks", 1, 10) if marks not in (None, "") else DIFFICULTY_MARKS[out["difficulty"]]
        dup = next((q for q in self.db.all("questions") if q["category"] == out["category"]
                    and q["text"].lower() == out["text"].lower() and q["question_id"] != cur.get("question_id")), None)
        if dup:
            raise ValidationError(f"The same question already exists as {dup['question_id']}.")
        return out

    # ---------------------------------------------------------------- crud
    def add(self, category: str, difficulty: str, text: str, options: list[str] | None = None, answer="A",
            explanation: str = "", qtype: str = "MCQ", marks=None) -> dict:
        clean = self._clean({"category": category, "difficulty": difficulty, "text": text, "options": options or [],
                             "answer": answer, "explanation": explanation, "qtype": qtype, "marks": marks})
        q = {"question_id": self._next_id(), **clean, "active": True, "created_by": self.actor, "created_at": now_str(),
             "updated_at": now_str()}
        self.db.insert("questions", q)
        log_activity(self.db, self.actor, "QUESTION_ADDED", f"{q['question_id']} {q['category']}/{q['difficulty']}")
        return q

    def get(self, question_id: str) -> dict:
        q = self.db.find_one("questions", question_id=str(question_id or "").strip().upper())
        if not q:
            raise NotFoundError(f"Question '{question_id}' not found.")
        return q

    def update(self, question_id: str, **changes) -> dict:
        q = self.get(question_id)
        changes = {k: v for k, v in changes.items() if v not in (None, "")}
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._clean(changes, q)
        clean["updated_at"] = now_str()
        log_activity(self.db, self.actor, "QUESTION_UPDATED", q["question_id"])
        return self.db.update("questions", "question_id", q["question_id"], clean)

    def set_active(self, question_id: str, active: bool) -> dict:
        q = self.get(question_id)
        log_activity(self.db, self.actor, "QUESTION_ENABLED" if active else "QUESTION_DISABLED", q["question_id"])
        return self.db.update("questions", "question_id", q["question_id"], {"active": active})

    def delete(self, question_id: str) -> None:
        """Questions used in any result are disabled instead (results must stay reviewable)."""
        q = self.get(question_id)
        if any(a["question_id"] == q["question_id"] for r in self.db.all("results") for a in r["answers"]):
            raise QuizError(f"{q['question_id']} appears in quiz results; disable it instead of deleting.")
        self.db.delete_where("bookmarks", question_id=q["question_id"])
        self.db.delete("questions", "question_id", q["question_id"])
        log_activity(self.db, self.actor, "QUESTION_DELETED", q["question_id"])

    def list(self, category: str | None = None, difficulty: str | None = None, include_inactive: bool = False) -> list[dict]:
        qs = self.db.all("questions")
        if not include_inactive:
            qs = [q for q in qs if q["active"]]
        if category:
            cat = self.categories.get(category)["name"]
            qs = [q for q in qs if q["category"] == cat]
        if difficulty:
            d = validate_choice(difficulty, DIFFICULTIES, "difficulty")
            qs = [q for q in qs if q["difficulty"] == d]
        return sorted(qs, key=lambda q: q["question_id"])

    def search(self, keyword: str) -> list[dict]:
        k = str(keyword or "").strip().lower()
        return [q for q in self.list(include_inactive=True)
                if not k or k in q["text"].lower() or k == q["question_id"].lower() or any(k in o.lower() for o in q["options"])]

    # ------------------------------------------------------------ CSV
    def export_csv(self, path: Path | str, category: str | None = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(CSV_HEADER)
            for q in self.list(category, include_inactive=True):
                opts = q["options"] + [""] * (MAX_OPTIONS - len(q["options"]))
                w.writerow([q["category"], q["difficulty"], q["qtype"], q["text"], *opts, chr(65 + q["answer"]),
                            q["explanation"], q["marks"]])
        return path

    def import_csv(self, path: Path | str) -> dict:
        """Import questions from a CSV in the export format. Bad rows are skipped and reported;
        unknown categories are created."""
        path = Path(path)
        if not path.exists():
            raise QuizError(f"File '{path}' not found.")
        added, skipped = 0, []
        try:
            with path.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                missing = {"Category", "Difficulty", "Question", "Answer"} - set(reader.fieldnames or [])
                if missing:
                    raise QuizError(f"CSV is missing column(s): {', '.join(sorted(missing))}.")
                for n, row in enumerate(reader, start=2):
                    try:
                        cat = (row.get("Category") or "").strip()
                        if cat and cat.lower() not in (c.lower() for c in self.categories.names()):
                            self.categories.add(cat)
                        opts = [row.get(f"Option {c}", "") for c in "ABCDEF"]
                        self.add(cat, row.get("Difficulty", ""), row.get("Question", ""), opts, row.get("Answer", ""),
                                 row.get("Explanation", ""), row.get("Type") or "MCQ", row.get("Marks") or None)
                        added += 1
                    except QuizError as exc:
                        skipped.append(f"Row {n}: {exc}")
        except UnicodeDecodeError:
            raise QuizError("The file is not UTF-8 text. Save it as 'CSV UTF-8'.")
        return {"added": added, "skipped": skipped}

    # ------------------------------------------------------------ bookmarks
    def bookmark(self, username: str, question_id: str, note: str = "") -> dict:
        q = self.get(question_id)
        if self.db.find_one("bookmarks", username=username, question_id=q["question_id"]):
            raise QuizError("Question is already bookmarked.")
        if len(self.db.find("bookmarks", username=username)) >= MAX_BOOKMARKS:
            raise QuizError(f"You can keep at most {MAX_BOOKMARKS} bookmarks.")
        b = {"username": username, "question_id": q["question_id"], "note": validate_text(note, "Note", 120),
             "created_at": now_str()}
        self.db.insert("bookmarks", b)
        return b

    def remove_bookmark(self, username: str, question_id: str) -> None:
        if not self.db.delete_where("bookmarks", username=username, question_id=str(question_id).strip().upper()):
            raise NotFoundError("That question is not bookmarked.")

    def bookmarks(self, username: str) -> list[dict]:
        out = []
        for b in self.db.find("bookmarks", username=username):
            try:
                out.append({**b, "question": self.get(b["question_id"])})
            except NotFoundError:
                continue
        return sorted(out, key=lambda b: b["created_at"], reverse=True)

    # ------------------------------------------------------------ analysis
    def item_analysis(self) -> list[dict]:
        """For each question: attempts, % answered correctly, % skipped. Questions most often
        answered wrongly are candidates for review (too hard, ambiguous or wrong key)."""
        stats = {q["question_id"]: {"question": q, "attempts": 0, "correct": 0, "skipped": 0} for q in self.list(include_inactive=True)}
        for r in self.db.all("results"):
            for a in r["answers"]:
                s = stats.get(a["question_id"])
                if s:
                    s["attempts"] += 1
                    s["correct"] += a["status"] == "CORRECT"
                    s["skipped"] += a["status"] == "SKIPPED"
        out = []
        for s in stats.values():
            if s["attempts"]:
                s["correct_pct"] = round(s["correct"] / s["attempts"] * 100, 1)
                s["skipped_pct"] = round(s["skipped"] / s["attempts"] * 100, 1)
                out.append(s)
        return sorted(out, key=lambda s: s["correct_pct"])
