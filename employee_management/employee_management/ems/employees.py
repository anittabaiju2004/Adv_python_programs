"""Employee Management module: employees (add / view / search / update /
exit / delete), salary revisions, and department & designation management."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from datetime import date

from .auth import AuthManager
from .database import JSONDatabase
from .utils import (DEFAULT_DEPARTMENTS, EMP_ID_PREFIX, EMP_ID_START, EMPLOYMENT_TYPES, GENDERS, MAX_AGE,
                    MAX_BASIC, MIN_AGE, MIN_BASIC, DATE_FMT, EMSError, NotFoundError, ValidationError,
                    age_on, now_str, parse_date, validate_amount, validate_choice, validate_date,
                    validate_email, validate_name, validate_pan, validate_phone, validate_text)


# ====================================================================== model
@dataclass
class Employee:
    emp_id: str
    name: str
    gender: str
    dob: str
    phone: str
    email: str
    department: str
    designation: str
    join_date: str
    basic_salary: float
    employment_type: str = "Permanent"
    pan: str = ""
    address: str = ""
    bank_account: str = ""
    ifsc: str = ""
    status: str = "ACTIVE"                    # ACTIVE | EXITED
    exit_date: str | None = None
    exit_reason: str | None = None
    salary_history: list = field(default_factory=list)
    created_at: str = field(default_factory=now_str)
    updated_at: str = field(default_factory=now_str)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Employee":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def age(self) -> int:
        return age_on(parse_date(self.dob), date.today())

    @property
    def experience_years(self) -> float:
        end = parse_date(self.exit_date) if self.exit_date else date.today()
        return round((end - parse_date(self.join_date)).days / 365.25, 1)


# ================================================================ departments
class DepartmentManager:
    def __init__(self, db: JSONDatabase):
        self.db = db
        if not self.db.all("departments"):
            for name, titles in DEFAULT_DEPARTMENTS.items():
                self.db.insert("departments", {"name": name, "designations": list(titles), "created_at": now_str()})

    @staticmethod
    def _clean_name(value: str, field: str) -> str:
        text = validate_text(value, field, 40, required=True)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 &/.\-]*", text):
            raise ValidationError(f"{field} must start with a letter.")
        return text

    def list(self) -> list[dict]:
        return sorted(self.db.all("departments"), key=lambda d: d["name"])

    def names(self) -> list[str]:
        return [d["name"] for d in self.list()]

    def get(self, name: str) -> dict:
        for d in self.db.all("departments"):
            if d["name"].lower() == str(name or "").strip().lower():
                return d
        raise NotFoundError(f"Department '{name}' not found.")

    def match_designation(self, department: str, designation: str) -> tuple[str, str]:
        dept = self.get(department)
        for t in dept["designations"]:
            if t.lower() == str(designation or "").strip().lower():
                return dept["name"], t
        raise ValidationError(f"'{designation}' is not a designation in {dept['name']}. "
                              f"Options: {', '.join(dept['designations'])}")

    def headcount(self) -> dict[str, int]:
        counts = Counter(e["department"] for e in self.db.find("employees", status="ACTIVE"))
        return {d: counts.get(d, 0) for d in self.names()}

    def add(self, name: str) -> dict:
        name = self._clean_name(name, "Department name")
        if name.lower() in (n.lower() for n in self.names()):
            raise ValidationError(f"Department '{name}' already exists.")
        return self.db.insert("departments", {"name": name, "designations": [], "created_at": now_str()})

    def rename(self, old: str, new: str) -> int:
        dept = self.get(old)
        new = self._clean_name(new, "Department name")
        if new.lower() != dept["name"].lower() and new.lower() in (n.lower() for n in self.names()):
            raise ValidationError(f"Department '{new}' already exists.")
        self.db.update("departments", "name", dept["name"], {"name": new})
        return self.db.update_where("employees", {"department": new, "updated_at": now_str()},
                                    department=dept["name"])

    def delete(self, name: str) -> None:
        dept = self.get(name)
        if self.db.find("employees", department=dept["name"]):
            raise EMSError(f"Cannot delete '{dept['name']}': employees (current or past) belong to it. "
                           "Move them to another department first.")
        self.db.delete("departments", "name", dept["name"])

    def add_designation(self, department: str, title: str) -> None:
        dept = self.get(department)
        title = self._clean_name(title, "Designation")
        if title.lower() in (t.lower() for t in dept["designations"]):
            raise ValidationError(f"'{title}' already exists in {dept['name']}.")
        self.db.update("departments", "name", dept["name"], {"designations": dept["designations"] + [title]})

    def remove_designation(self, department: str, title: str) -> None:
        dept_name, title = self.match_designation(department, title)
        if self.db.find("employees", department=dept_name, designation=title, status="ACTIVE"):
            raise EMSError(f"Cannot remove '{title}': active employees hold this designation.")
        dept = self.get(dept_name)
        self.db.update("departments", "name", dept_name,
                       {"designations": [t for t in dept["designations"] if t != title]})


# ================================================================== employees
class EmployeeManager:
    def __init__(self, db: JSONDatabase, auth: AuthManager | None = None):
        self.db = db
        self.auth = auth or AuthManager(db)
        self.departments = DepartmentManager(db)

    def _next_id(self) -> str:
        nums = [int(e["emp_id"][len(EMP_ID_PREFIX):]) for e in self.db.all("employees")
                if e["emp_id"][len(EMP_ID_PREFIX):].isdigit()]
        return f"{EMP_ID_PREFIX}{max(nums) + 1 if nums else EMP_ID_START}"

    def _validate(self, data: dict, current: Employee | None = None) -> dict:
        out = {}
        if "name" in data:
            out["name"] = validate_name(data["name"])
        if "gender" in data:
            out["gender"] = validate_choice(data["gender"], GENDERS, "gender")
        if "phone" in data:
            out["phone"] = validate_phone(data["phone"])
        if "email" in data:
            out["email"] = validate_email(data["email"])
        if "pan" in data:
            out["pan"] = validate_pan(data["pan"])
        if "address" in data:
            out["address"] = validate_text(data["address"], "Address", 200)
        if "employment_type" in data:
            out["employment_type"] = validate_choice(data["employment_type"], EMPLOYMENT_TYPES, "employment type")
        if "basic_salary" in data:
            out["basic_salary"] = validate_amount(data["basic_salary"], "Basic salary", MIN_BASIC, MAX_BASIC)
        if "bank_account" in data:
            acc = re.sub(r"\s", "", str(data["bank_account"] or ""))
            if acc and not re.fullmatch(r"\d{9,18}", acc):
                raise ValidationError("Bank account number must be 9-18 digits.")
            out["bank_account"] = acc
        if "ifsc" in data:
            ifsc = str(data["ifsc"] or "").strip().upper()
            if ifsc and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc):
                raise ValidationError("IFSC must look like SBIN0001234.")
            out["ifsc"] = ifsc
        if "dob" in data or "join_date" in data:
            dob = parse_date(data.get("dob") or (current.dob if current else None), "Date of birth")
            join = parse_date(validate_date(data.get("join_date") or (current.join_date if current else None),
                                            "Joining date", allow_future=True), "Joining date")
            if (join - date.today()).days > 90:
                raise ValidationError("Joining date can be at most 90 days in the future.")
            if not MIN_AGE <= age_on(dob, join) <= MAX_AGE:
                raise ValidationError(f"Employee must be {MIN_AGE}-{MAX_AGE} years old on the joining date.")
            out["dob"], out["join_date"] = dob.strftime(DATE_FMT), join.strftime(DATE_FMT)
        if "department" in data or "designation" in data:
            dept = data.get("department") or (current.department if current else "")
            desig = data.get("designation") or (current.designation if current else "")
            out["department"], out["designation"] = self.departments.match_designation(dept, desig)
        # uniqueness
        for key in ("email", "phone", "pan"):
            if out.get(key):
                clash = next((e for e in self.db.all("employees") if e.get(key) == out[key]
                              and (not current or e["emp_id"] != current.emp_id)), None)
                if clash:
                    raise ValidationError(f"{key.upper() if key == 'pan' else key.title()} already belongs to "
                                          f"{clash['emp_id']} ({clash['name']}).")
        return out

    # ---------------------------------------------------------------- crud
    REQUIRED = ("name", "gender", "dob", "phone", "email", "department", "designation", "join_date", "basic_salary")

    def add(self, **data) -> tuple[Employee, str]:
        """Add an employee and create their login. Returns (employee, temporary_password)."""
        missing = [k for k in self.REQUIRED if not str(data.get(k) or "").strip()]
        if missing:
            raise ValidationError(f"Required: {', '.join(m.replace('_', ' ') for m in missing)}.")
        unknown = set(data) - {f.name for f in fields(Employee)}
        if unknown:
            raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")
        clean = self._validate(data)
        emp = Employee(emp_id=self._next_id(), **clean)
        emp.salary_history = [{"date": emp.join_date, "old": None, "new": emp.basic_salary, "reason": "Joining"}]
        self.db.insert("employees", emp.to_dict())
        password = self.auth.create_employee_login(emp.emp_id)
        return emp, password

    def get(self, emp_id: str) -> Employee:
        rec = self.db.find_one("employees", emp_id=str(emp_id or "").strip().upper())
        if not rec:
            raise NotFoundError(f"Employee '{emp_id}' not found.")
        return Employee.from_dict(rec)

    SORTS = {"id": lambda e: e.emp_id, "name": lambda e: e.name.lower(),
             "salary": lambda e: -e.basic_salary, "joining": lambda e: e.join_date,
             "department": lambda e: (e.department, e.name.lower())}

    def list(self, status: str | None = "ACTIVE", department: str | None = None,
             designation: str | None = None, sort_by: str = "id") -> list[Employee]:
        emps = [Employee.from_dict(r) for r in self.db.all("employees")]
        if status:
            emps = [e for e in emps if e.status == status.upper()]
        if department:
            dept = self.departments.get(department)["name"]
            emps = [e for e in emps if e.department == dept]
        if designation:
            emps = [e for e in emps if e.designation.lower() == designation.lower()]
        if sort_by not in self.SORTS:
            raise ValidationError(f"Sort by one of: {', '.join(self.SORTS)}")
        return sorted(emps, key=self.SORTS[sort_by])

    def search(self, keyword: str, include_exited: bool = False) -> list[Employee]:
        k = str(keyword or "").strip().lower()
        if not k:
            return self.list(None if include_exited else "ACTIVE")
        return [e for e in self.list(None if include_exited else "ACTIVE")
                if k in e.emp_id.lower() or k in e.name.lower() or k in e.email or k in e.phone
                or k in e.department.lower() or k in e.designation.lower()]

    EDITABLE = {"name", "gender", "dob", "phone", "email", "pan", "address", "department", "designation",
                "employment_type", "join_date", "bank_account", "ifsc"}

    def update(self, emp_id: str, **changes) -> Employee:
        emp = self.get(emp_id)
        if "basic_salary" in changes:
            raise ValidationError("Use salary revision to change the basic salary (keeps history).")
        changes = {k: v for k, v in changes.items() if v is not None}
        bad = set(changes) - self.EDITABLE
        if bad:
            raise ValidationError(f"Cannot update: {', '.join(sorted(bad))}")
        if not changes:
            raise ValidationError("Nothing to update.")
        clean = self._validate(changes, current=emp)
        clean["updated_at"] = now_str()
        return Employee.from_dict(self.db.update("employees", "emp_id", emp.emp_id, clean))

    def revise_salary(self, emp_id: str, new_basic, reason: str = "Annual increment",
                      effective: str | None = None) -> Employee:
        emp = self.get(emp_id)
        if not emp.is_active:
            raise EMSError("Cannot revise salary of an exited employee.")
        new_basic = validate_amount(new_basic, "New basic salary", MIN_BASIC, MAX_BASIC)
        if new_basic == emp.basic_salary:
            raise ValidationError("New salary is the same as the current salary.")
        entry = {"date": validate_date(effective or date.today().strftime(DATE_FMT), "Effective date"),
                 "old": emp.basic_salary, "new": new_basic,
                 "reason": validate_text(reason, "Reason", 80) or "Revision"}
        return Employee.from_dict(self.db.update("employees", "emp_id", emp.emp_id,
                                                 {"basic_salary": new_basic, "updated_at": now_str(),
                                                  "salary_history": emp.salary_history + [entry]}))

    def exit_employee(self, emp_id: str, exit_date: str, reason: str) -> Employee:
        """Mark an employee as exited (resigned / terminated) and disable their login.
        Records are kept for reports and payroll history."""
        emp = self.get(emp_id)
        if not emp.is_active:
            raise EMSError(f"{emp.emp_id} has already exited.")
        d = validate_date(exit_date, "Exit date")
        if d < emp.join_date:
            raise ValidationError("Exit date cannot be before the joining date.")
        if self.auth.get(emp.emp_id):
            self.auth.set_active(emp.emp_id, False)
        return Employee.from_dict(self.db.update("employees", "emp_id", emp.emp_id,
                                                 {"status": "EXITED", "exit_date": d, "updated_at": now_str(),
                                                  "exit_reason": validate_text(reason, "Reason", 100) or "Resigned"}))

    def rehire(self, emp_id: str) -> Employee:
        emp = self.get(emp_id)
        if emp.is_active:
            raise EMSError(f"{emp.emp_id} is already active.")
        if self.auth.get(emp.emp_id):
            self.auth.set_active(emp.emp_id, True)
        return Employee.from_dict(self.db.update("employees", "emp_id", emp.emp_id,
                                                 {"status": "ACTIVE", "exit_date": None, "exit_reason": None,
                                                  "updated_at": now_str()}))

    def delete(self, emp_id: str) -> dict:
        """Permanently delete an employee and all their attendance, leave,
        payroll records and login. Returns counts removed."""
        emp = self.get(emp_id)
        removed = {c: self.db.delete_where(c, emp_id=emp.emp_id) for c in ("attendance", "leaves", "payroll")}
        self.auth.delete_login(emp.emp_id)
        self.db.delete("employees", "emp_id", emp.emp_id)
        return removed

    def summary(self) -> dict:
        active = self.list()
        return {
            "active": len(active),
            "exited": len(self.list("EXITED")),
            "by_department": self.departments.headcount(),
            "by_type": dict(Counter(e.employment_type for e in active)),
            "by_gender": dict(Counter(e.gender for e in active)),
            "avg_experience": round(sum(e.experience_years for e in active) / len(active), 1) if active else 0,
        }
