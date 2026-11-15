"""Result Processing: totals, averages, percentages, subject and overall
grades, pass/fail, division, rank list, class and subject toppers, class
statistics and student progress across exams."""
from __future__ import annotations

from collections import Counter

from .attendance import AttendanceManager
from .database import JSONDatabase
from .marks import MarksManager, subject_grade
from .students import StudentManager
from .utils import (ABSENT, EXAMS, FINAL_EXAM, GRADES, MIN_ATTENDANCE, PASS_MARK, SUBJECT_MAX, SUBJECTS, SMSError,
                    division, grade_for, validate_choice)


class ResultProcessor:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.marks = MarksManager(db)
        self.students = StudentManager(db)
        self.attendance = AttendanceManager(db)

    # -------------------------------------------------------------- student
    def student_result(self, roll_no: str, exam: str) -> dict:
        s = self.students.get(roll_no)
        rec = self.marks.get(s["roll_no"], exam)
        subjects, total, points, failed = [], 0.0, [], []
        for sub in SUBJECTS:
            m = rec["subjects"].get(sub)
            if m is None:
                raise SMSError(f"{s['roll_no']} has no {sub} mark for {rec['exam']}.")
            value = 0 if m == ABSENT else m
            ok = m != ABSENT and m >= PASS_MARK
            if not ok:
                failed.append(sub)
            g = subject_grade(m)
            points.append(0 if m == ABSENT else grade_for(m)[1])
            subjects.append({"subject": sub, "marks": m, "max": SUBJECT_MAX, "grade": g,
                             "result": "PASS" if ok else ("ABSENT" if m == ABSENT else "FAIL")})
            total += value
        maximum = SUBJECT_MAX * len(SUBJECTS)
        percent = round(total / maximum * 100, 2)
        passed = not failed
        grade, _, remark = grade_for(percent) if passed else ("F", 0, "Fail")
        att = self.attendance.student_summary(s["roll_no"])
        eligible = rec["exam"] != FINAL_EXAM or not att["shortage"]
        return {"roll_no": s["roll_no"], "name": s["name"], "class_code": s["class_code"], "exam": rec["exam"],
                "subjects": subjects, "total": round(total, 1), "max_total": maximum,
                "average": round(total / len(SUBJECTS), 2), "percent": percent, "grade": grade, "remark": remark,
                "gpa": round(sum(points) / len(points), 2), "passed": passed, "failed_subjects": failed,
                "result": "PASS" if passed else "FAIL", "division": division(percent, passed),
                "attendance": att["percent"], "attendance_shortage": att["shortage"], "eligible": eligible}

    # ---------------------------------------------------------------- class
    def class_result(self, class_code: str, exam: str) -> dict:
        """Results for every student with marks, a rank list (passed students by total,
        ties share a rank: 1, 2, 2, 4), toppers and statistics."""
        exam = validate_choice(exam, EXAMS, "exam")
        rows, incomplete = [], []
        for m in self.marks.class_marks(class_code, exam):
            try:
                rows.append(self.student_result(m["roll_no"], exam))
            except SMSError:
                incomplete.append(m["roll_no"])
        passed = sorted((r for r in rows if r["passed"]), key=lambda r: (-r["total"], r["roll_no"]))
        rank = 0
        for i, r in enumerate(passed, 1):
            if i == 1 or r["total"] != passed[i - 2]["total"]:
                rank = i
            r["rank"] = rank
        for r in rows:
            r.setdefault("rank", None)
        rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, -r["total"], r["roll_no"]))
        toppers = [r for r in passed if r["rank"] == 1]
        subject_stats = {}
        for sub in SUBJECTS:
            vals = [(r, next(x for x in r["subjects"] if x["subject"] == sub)) for r in rows]
            appeared = [(r, x) for r, x in vals if x["marks"] != ABSENT]
            nums = [x["marks"] for _, x in appeared]
            best = max(nums) if nums else None
            subject_stats[sub] = {
                "appeared": len(appeared), "absent": len(vals) - len(appeared),
                "passed": sum(1 for _, x in vals if x["result"] == "PASS"),
                "pass_percent": round(sum(1 for _, x in vals if x["result"] == "PASS") / len(vals) * 100, 1) if vals else 0,
                "average": round(sum(nums) / len(nums), 1) if nums else 0, "highest": best,
                "lowest": min(nums) if nums else None,
                "toppers": [r["name"] for r, x in appeared if x["marks"] == best] if best is not None else []}
        grades = Counter(r["grade"] for r in rows)
        return {"class_code": class_code.upper(), "exam": exam, "published": self.marks.is_published(class_code, exam),
                "rows": rows, "incomplete": incomplete, "appeared": len(rows), "passed": len(passed),
                "failed": len(rows) - len(passed),
                "pass_percent": round(len(passed) / len(rows) * 100, 1) if rows else 0.0,
                "class_average": round(sum(r["percent"] for r in rows) / len(rows), 2) if rows else 0.0,
                "highest": max((r["percent"] for r in rows), default=0), "lowest": min((r["percent"] for r in rows), default=0),
                "toppers": toppers, "subject_stats": subject_stats,
                "grade_distribution": {g: grades.get(g, 0) for _, g, _, _ in GRADES},
                "distinctions": sum(1 for r in rows if r["division"] == "First Class with Distinction"),
                "not_eligible": [r for r in rows if not r["eligible"]]}

    def rank_of(self, roll_no: str, exam: str) -> int | None:
        s = self.students.get(roll_no)
        for r in self.class_result(s["class_code"], exam)["rows"]:
            if r["roll_no"] == s["roll_no"]:
                return r["rank"]
        return None

    def progress(self, roll_no: str) -> list[dict]:
        """A student's results across all exams that have complete marks."""
        out = []
        for exam in EXAMS:
            try:
                r = self.student_result(roll_no, exam)
                r["rank"] = self.rank_of(roll_no, exam)
                out.append(r)
            except SMSError:
                continue
        return out

    def shortage_students(self, class_code: str) -> list[dict]:
        return [r for r in self.attendance.class_summary(class_code)["students"] if r["percent"] < MIN_ATTENDANCE and r["days"]]
