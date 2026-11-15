"""Student Management: classes and student records (CRUD, search, status,
student portal logins)."""
from __future__ import annotations

import re
from datetime import date

from .auth import log_activity
from .database import JSONDatabase
from .utils import (GENDERS, STUDENT_STATUSES, NotFoundError, SMSError, ValidationError, age_on, hash_password,
                    now_str, parse_date, temporary_password, validate_choice, validate_email, validate_int,
                    validate_name, validate_phone, validate_text)


# ==================================================================== classes
class ClassManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor

    def add(self, code: str, name: str, course: str, academic_year: str, semester=1, class_teacher: str = "") -> dict:
        code = str(code or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2,6}-\d{4}[A-Z]?", code):
            raise ValidationError("Class code must look like BCA-2024 or MCA-2025A.")
        if self.db.find_one("classes", code=code):
            raise ValidationError(f"Class {code} already exists.")
        if not re.fullmatch(r"\d{4}-\d{2}", str(academic_year or "").strip()):
            raise ValidationError("Academic year must look like 2025-26.")
        if class_teacher and not self.db.find_one("users", username=class_teacher.lower()):
            raise ValidationError(f"No staff user '{class_teacher}'.")
        c = {"code": code, "name": validate_text(name, "Class name", 60, required=True),
             "course": validate_text(course, "Course", 60, required=True), "academic_year": academic_year.strip(),
             "semester": validate_int(semester, "Semester", 1, 10), "class_teacher": class_teacher.lower(),
             "created_at": now_str()}
        self.db.insert("classes", c)
        log_activity(self.db, self.actor, "CLASS_ADDED", code)
        return c

    def get(self, code: str) -> dict:
        c = self.db.find_one("classes", code=str(code or "").strip().upper())
        if not c:
            raise NotFoundError(f"Class '{code}' not found.")
        return c

    def list(self) -> list[dict]:
        return sorted(self.db.all("classes"), key=lambda c: c["code"])

    def codes(self) -> list[str]:
        return [c["code"] for c in self.list()]

    def update(self, code: str, **changes) -> dict:
        c = self.get(code)
        clean = {}
        if changes.get("name"):
            clean["name"] = validate_text(changes["name"], "Class name", 60, required=True)
        if changes.get("semester"):
            clean["semester"] = validate_int(changes["semester"], "Semester", 1, 10)
        if changes.get("academic_year"):
            if not re.fullmatch(r"\d{4}-\d{2}", changes["academic_year"].strip()):
                raise ValidationError("Academic year must look like 2025-26.")
            clean["academic_year"] = changes["academic_year"].strip()
        if changes.get("class_teacher") is not None and "class_teacher" in changes:
            t = changes["class_teacher"].lower()
            if t and not self.db.find_one("users", username=t):
                raise ValidationError(f"No staff user '{t}'.")
            clean["class_teacher"] = t
        if not clean:
            raise ValidationError("Nothing to update.")
        log_activity(self.db, self.actor, "CLASS_UPDATED", c["code"])
        return self.db.update("classes", "code", c["code"], clean)

    def delete(self, code: str) -> None:
        c = self.get(code)
        if self.db.find("students", class_code=c["code"]):
            raise SMSError(f"Class {c['code']} has students.")
        self.db.delete("classes", "code", c["code"])
        log_activity(self.db, self.actor, "CLASS_DELETED", c["code"])


# =================================================================== students
class StudentManager:
    def __init__(self, db: JSONDatabase, actor: str = "system"):
        self.db = db
        self.actor = actor
        self.classes = ClassManager(db, actor)

    def _next_roll(self, class_code: str) -> str:
        """BCA-2024 -> BCA24001, BCA24002, ..."""
        letters, year = class_code.split("-")
        prefix = f"{letters}{year[2:4]}"
        nums = [int(s["roll_no"][len(prefix):]) for s in self.db.find("students", class_code=class_code)
                if s["roll_no"].startswith(prefix) and s["roll_no"][len(prefix):].isdigit()]
        return f"{prefix}{(max(nums) + 1) if nums else 1:03d}"

    def _clean(self, data: dict, current: dict | None = None) -> dict:
        out = {}
        if "name" in data:
            out["name"] = validate_name(data["name"])
        if "gender" in data:
            out["gender"] = validate_choice(data["gender"], GENDERS, "gender")
        if "dob" in data:
            dob = parse_date(data["dob"], "Date of birth")
            if not 15 <= age_on(dob, date.today()) <= 60:
                raise ValidationError("Student must be 15-60 years old.")
            out["dob"] = dob.isoformat()
        if "phone" in data:
            out["phone"] = validate_phone(data["phone"])
        if "email" in data:
            out["email"] = validate_email(data["email"])
        if "guardian_name" in data:
            out["guardian_name"] = validate_name(data["guardian_name"], "Guardian name") if data["guardian_name"] else ""
        if "guardian_phone" in data:
            out["guardian_phone"] = validate_phone(data["guardian_phone"], required=False)
        if "address" in data:
            out["address"] = validate_text(data["address"], "Address", 200)
        if "admission_date" in data:
            d = parse_date(data["admission_date"] or date.today(), "Admission date")
            if d > date.today():
                raise ValidationError("Admission date cannot be in the future.")
            out["admission_date"] = d.isoformat()
        for key in ("phone", "email"):
            if out.get(key):
                clash = next((s for s in self.db.all("students") if s.get(key) == out[key]
                              and (not current or s["roll_no"] != current["roll_no"])), None)
                if clash:
                    raise ValidationError(f"{key.title()} already belongs to {clash['roll_no']} ({clash['name']}).")
        return out

    # ---------------------------------------------------------------- crud
    def add(self, name: str, gender: str, dob: str, phone: str, class_code: str, email: str = "",
            guardian_name: str = "", guardian_phone: str = "", address: str = "", admission_date=None) -> tuple[dict, str]:
        """Add a student and create their read-only portal login. Returns (student, temporary_password)."""
        cls = self.classes.get(class_code)
        clean = self._clean({"name": name, "gender": gender, "dob": dob, "phone": phone, "email": email,
                             "guardian_name": guardian_name, "guardian_phone": guardian_phone, "address": address,
                             "admission_date": admission_date})
        s = {"roll_no": self._next_roll(cls["code"]), **clean, "class_code": cls["code"], "status": "ACTIVE",
             "created_at": now_str(), "updated_at": now_str()}
        self.db.insert("students", s)
        temp = temporary_password()
        h, salt = hash_password(temp)
        self.db.insert("users", {"username": s["roll_no"].lower(), "password_hash": h, "salt": salt, "role": "student",
                                 "roll_no": s["roll_no"], "name": s["name"], "phone": s["phone"], "email": s["email"],
                                 "active": True, "must_change_password": True, "failed_attempts": 0,
                                 "created_at": now_str(), "last_login": None})
        log_activity(self.db, self.actor, "STUDENT_ADDED", f"{s['roll_no']} {s['name']}")
        return s, temp

    def get(self, roll_no: str) -> dict:
        s = self.db.find_one("students", roll_no=str(roll_no or "").strip().upper())
        if not s:
            raise NotFoundError(f"Student '{roll_no}' not found.")
        return s

    def list(self, class_code: str | None = None, status: str | None = "ACTIVE", sort_by: str = "roll") -> list[dict]:
        ss = self.db.all("students")
        if class_code:
            ss = [s for s in ss if s["class_code"] == self.classes.get(class_code)["code"]]
        if status:
            ss = [s for s in ss if s["status"] == status.upper()]
        key = {"roll": lambda s: s["roll_no"], "name": lambda s: s["name"].lower()}.get(sort_by)
        if not key:
            raise ValidationError("Sort by 'roll' or 'name'.")
        return sorted(ss, key=key)

    def search(self, keyword: str, include_inactive: bool = True) -> list[dict]:
        k = str(keyword or "").strip().lower()
        digits = "".join(c for c in k if c.isdigit())
        return [s for s in self.list(status=None if include_inactive else "ACTIVE")
                if not k or k in s["name"].lower() or k == s["roll_no"].lower() or k == s["email"]
                or (len(digits) >= 4 and digits in s["phone"]) or k in s.get("guardian_name", "").lower()]

    def update(self, roll_no: str, **changes) -> dict:
        s = self.get(roll_no)
        changes = {k: v for k, v in changes.items() if v is not None}
        if "class_code" in changes:
            raise ValidationError("Use 'transfer' to move a student to another class.")
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._clean(changes, s)
        clean["updated_at"] = now_str()
        if "name" in clean:
            self.db.update("users", "username", s["roll_no"].lower(), {"name": clean["name"]})
        log_activity(self.db, self.actor, "STUDENT_UPDATED", f"{s['roll_no']}: {', '.join(k for k in clean if k != 'updated_at')}")
        return self.db.update("students", "roll_no", s["roll_no"], clean)

    def set_status(self, roll_no: str, status: str) -> dict:
        s = self.get(roll_no)
        status = validate_choice(status, STUDENT_STATUSES, "status")
        self.db.update("users", "username", s["roll_no"].lower(), {"active": status == "ACTIVE"})
        log_activity(self.db, self.actor, "STUDENT_STATUS", f"{s['roll_no']} -> {status}")
        return self.db.update("students", "roll_no", s["roll_no"], {"status": status, "updated_at": now_str()})

    def delete(self, roll_no: str, purge: bool = False) -> dict:
        """Delete a student. If marks or attendance exist, `purge=True` is needed (they are
        removed too); otherwise mark the student as LEFT instead."""
        s = self.get(roll_no)
        counts = {"marks": len(self.db.find("marks", roll_no=s["roll_no"])),
                  "attendance": sum(1 for a in self.db.all("attendance") if s["roll_no"] in a["records"])}
        if (counts["marks"] or counts["attendance"]) and not purge:
            raise SMSError(f"{s['roll_no']} has {counts['marks']} mark record(s) and attendance on "
                           f"{counts['attendance']} day(s). Mark the student as LEFT, or delete with purge.")
        self.db.delete_where("marks", roll_no=s["roll_no"])
        with self.db.editing("attendance") as days:
            for d in days:
                d["records"].pop(s["roll_no"], None)
        self.db.delete("users", "username", s["roll_no"].lower())
        self.db.delete("students", "roll_no", s["roll_no"])
        log_activity(self.db, self.actor, "STUDENT_DELETED", s["roll_no"])
        return counts

    def summary(self) -> dict:
        ss = self.db.all("students")
        active = [s for s in ss if s["status"] == "ACTIVE"]
        return {"total": len(ss), "active": len(active),
                "by_class": {c: sum(1 for s in active if s["class_code"] == c) for c in self.classes.codes()},
                "by_gender": {g: sum(1 for s in active if s["gender"] == g) for g in GENDERS}}
