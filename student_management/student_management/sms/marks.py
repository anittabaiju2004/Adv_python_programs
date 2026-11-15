"""Marks & Grade Management: marks entry for Python, Java and DBMS per exam,
absent entries, completeness checks, and publishing (locking) results."""
from __future__ import annotations

from .auth import log_activity
from .database import JSONDatabase
from .students import ClassManager, StudentManager
from .utils import (ABSENT, EXAMS, SUBJECT_MAX, SUBJECTS, NotFoundError, SMSError, ValidationError, grade_for, now_str,
                    validate_choice)


def parse_mark(value):
    """A mark is 0-100 (half marks allowed) or 'AB' for absent."""
    v = str(value if value is not None else "").strip().upper()
    if v in (ABSENT, "A", "ABSENT"):
        return ABSENT
    try:
        m = float(v)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid mark. Enter 0-{SUBJECT_MAX} or {ABSENT}.")
    if not 0 <= m <= SUBJECT_MAX:
        raise ValidationError(f"Marks must be between 0 and {SUBJECT_MAX}.")
    if m * 2 != int(m * 2):
        raise ValidationError("Marks can only be whole or half numbers.")
    return int(m) if m == int(m) else m


def subject_grade(mark) -> str:
    return "AB" if mark == ABSENT else grade_for(mark)[0]


class MarksManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.students = StudentManager(db, actor)
        self.classes = ClassManager(db, actor)

    # ------------------------------------------------------------- publish
    def is_published(self, class_code: str, exam: str) -> bool:
        return exam in self.classes.get(class_code).get("published_exams", [])

    def publish(self, class_code: str, exam: str) -> dict:
        """Lock the marks of a class for an exam. All active students must have all subjects."""
        cls = self.classes.get(class_code)
        exam = validate_choice(exam, EXAMS, "exam")
        missing = self.missing(cls["code"], exam)
        if missing:
            raise SMSError(f"Marks are incomplete for {len(missing)} student(s), e.g. "
                           f"{missing[0]['roll_no']} ({', '.join(missing[0]['subjects'])}).")
        published = sorted(set(cls.get("published_exams", [])) | {exam})
        log_activity(self.db, self.actor, "RESULT_PUBLISHED", f"{cls['code']} {exam}")
        return self.db.update("classes", "code", cls["code"], {"published_exams": published})

    def unpublish(self, class_code: str, exam: str) -> dict:
        cls = self.classes.get(class_code)
        exam = validate_choice(exam, EXAMS, "exam")
        log_activity(self.db, self.actor, "RESULT_UNPUBLISHED", f"{cls['code']} {exam}")
        return self.db.update("classes", "code", cls["code"],
                              {"published_exams": [e for e in cls.get("published_exams", []) if e != exam]})

    # --------------------------------------------------------------- entry
    def _record(self, roll_no: str, exam: str) -> dict | None:
        return self.db.find_one("marks", id=f"{roll_no}:{exam}")

    def enter(self, roll_no: str, exam: str, marks: dict) -> dict:
        """Enter or update marks, e.g. {"Python": 78, "Java": "AB"}. Subjects not given are kept."""
        s = self.students.get(roll_no)
        if s["status"] != "ACTIVE":
            raise SMSError(f"{s['roll_no']} is {s['status']}.")
        exam = validate_choice(exam, EXAMS, "exam")
        if self.is_published(s["class_code"], exam):
            raise SMSError(f"{exam} results for {s['class_code']} are published and locked. Ask the admin to unpublish.")
        if not marks:
            raise ValidationError("No marks given.")
        clean = {}
        for subj, value in marks.items():
            subj = validate_choice(subj, SUBJECTS, "subject")
            clean[subj] = parse_mark(value)
        rec = self._record(s["roll_no"], exam)
        if rec:
            merged = {**rec["subjects"], **clean}
            log_activity(self.db, self.actor, "MARKS_UPDATED", f"{s['roll_no']} {exam} {clean}")
            return self.db.update("marks", "id", rec["id"], {"subjects": merged, "entered_by": self.actor,
                                                              "updated_at": now_str()})
        rec = {"id": f"{s['roll_no']}:{exam}", "roll_no": s["roll_no"], "class_code": s["class_code"], "exam": exam,
               "subjects": clean, "entered_by": self.actor, "updated_at": now_str()}
        self.db.insert("marks", rec)
        log_activity(self.db, self.actor, "MARKS_ENTERED", f"{s['roll_no']} {exam}")
        return rec

    def enter_subject_for_class(self, class_code: str, exam: str, subject: str, marks_by_roll: dict) -> int:
        """Bulk entry of one subject for many students. Returns the number saved."""
        cls = self.classes.get(class_code)
        rolls = {s["roll_no"] for s in self.students.list(cls["code"])}
        bad = set(r.upper() for r in marks_by_roll) - rolls
        if bad:
            raise ValidationError(f"Not active in {cls['code']}: {', '.join(sorted(bad))}.")
        for r, v in marks_by_roll.items():
            parse_mark(v)                                  # validate everything before saving anything
        for r, v in marks_by_roll.items():
            self.enter(r, exam, {subject: v})
        return len(marks_by_roll)

    def get(self, roll_no: str, exam: str) -> dict:
        rec = self._record(str(roll_no).strip().upper(), validate_choice(exam, EXAMS, "exam"))
        if not rec:
            raise NotFoundError(f"No {exam} marks for {roll_no}.")
        return rec

    def class_marks(self, class_code: str, exam: str) -> list[dict]:
        exam = validate_choice(exam, EXAMS, "exam")
        cls = self.classes.get(class_code)
        return sorted((m for m in self.db.find("marks", class_code=cls["code"], exam=exam)), key=lambda m: m["roll_no"])

    def missing(self, class_code: str, exam: str) -> list[dict]:
        """Active students who do not yet have all subjects for the exam."""
        exam = validate_choice(exam, EXAMS, "exam")
        out = []
        for s in self.students.list(class_code):
            rec = self._record(s["roll_no"], exam)
            lacking = [sub for sub in SUBJECTS if not rec or sub not in rec["subjects"]]
            if lacking:
                out.append({"roll_no": s["roll_no"], "name": s["name"], "subjects": lacking})
        return out

    def delete(self, roll_no: str, exam: str) -> None:
        rec = self.get(roll_no, exam)
        if self.is_published(rec["class_code"], rec["exam"]):
            raise SMSError("Results are published and locked.")
        self.db.delete("marks", "id", rec["id"])
        log_activity(self.db, self.actor, "MARKS_DELETED", rec["id"])
