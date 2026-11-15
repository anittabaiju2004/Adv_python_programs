"""Result Management: storing attempts (with a snapshot of each question so
later edits do not change history), review, attempt counts, best attempts and
certificate verification."""
from __future__ import annotations

from .database import JSONDatabase
from .utils import NotFoundError, certificate_code, parse_date


class ResultManager:
    def __init__(self, db: JSONDatabase):
        self.db = db

    def save(self, result: dict) -> dict:
        result = {"result_id": f"RS{len(self.db.all('results')) + 1:05d}", **result}
        if result["mode"] == "Exam" and result["passed"]:
            result["certificate_code"] = certificate_code(result["result_id"], result["username"], result["percent"])
        else:
            result["certificate_code"] = None
        self.db.insert("results", result)
        return result

    def get(self, result_id: str) -> dict:
        r = self.db.find_one("results", result_id=str(result_id or "").strip().upper())
        if not r:
            raise NotFoundError(f"Result '{result_id}' not found.")
        return r

    def list(self, username: str | None = None, quiz_id: str | None = None, mode: str | None = None,
             start=None, end=None) -> list[dict]:
        rs = self.db.all("results")
        if username:
            rs = [r for r in rs if r["username"] == username]
        if quiz_id:
            rs = [r for r in rs if r["quiz_id"] == quiz_id.upper()]
        if mode:
            rs = [r for r in rs if r["mode"] == mode]
        if start:
            rs = [r for r in rs if r["submitted_at"][:10] >= parse_date(start).isoformat()]
        if end:
            rs = [r for r in rs if r["submitted_at"][:10] <= parse_date(end).isoformat()]
        return sorted(rs, key=lambda r: (r["submitted_at"], r["result_id"]), reverse=True)

    def attempt_count(self, username: str, quiz_id: str, mode: str = "Exam") -> int:
        return len(self.list(username, quiz_id, mode))

    def best(self, username: str, quiz_id: str) -> dict | None:
        rs = self.list(username, quiz_id, "Exam")
        return min(rs, key=lambda r: (-r["percent"], r["duration_sec"], r["submitted_at"])) if rs else None

    def certificates(self, username: str) -> list[dict]:
        return [r for r in self.list(username, mode="Exam") if r["certificate_code"]]

    def verify_certificate(self, result_id: str, code: str) -> dict:
        """Check a certificate: the code must match the stored result (and its recomputed HMAC)."""
        try:
            r = self.get(result_id)
        except NotFoundError:
            return {"valid": False, "reason": "No such certificate ID."}
        expected = certificate_code(r["result_id"], r["username"], r["percent"])
        if not r["certificate_code"] or str(code or "").strip().upper() != expected:
            return {"valid": False, "reason": "Verification code does not match."}
        u = self.db.find_one("users", username=r["username"]) or {}
        return {"valid": True, "name": u.get("name", r["username"]), "quiz": r["quiz_title"], "percent": r["percent"],
                "grade": r["grade"], "date": r["submitted_at"][:10]}
