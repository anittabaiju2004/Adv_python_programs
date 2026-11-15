"""Leaderboard: per-quiz and overall rankings from exam attempts only.

Per quiz: each student's best attempt, ranked by percentage, then faster time,
then earlier submission. Overall: average of each student's best percentage
across the quizzes they attempted (minimum number of quizzes configurable)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from .database import JSONDatabase
from .results import ResultManager

PERIODS = {"all": None, "week": 7, "month": 30}


def _since(period: str) -> str | None:
    days = PERIODS.get(period)
    return (date.today() - timedelta(days=days)).isoformat() if days else None


class Leaderboard:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.results = ResultManager(db)

    def _names(self) -> dict:
        return {u["username"]: u["name"] for u in self.db.all("users")}

    def for_quiz(self, quiz_id: str, period: str = "all", top: int | None = 10) -> list[dict]:
        since = _since(period)
        best: dict[str, dict] = {}
        for r in self.results.list(quiz_id=quiz_id, mode="Exam", start=since):
            cur = best.get(r["username"])
            key = (-r["percent"], r["duration_sec"], r["submitted_at"])
            if not cur or key < (-cur["percent"], cur["duration_sec"], cur["submitted_at"]):
                best[r["username"]] = r
        rows = sorted(best.values(), key=lambda r: (-r["percent"], r["duration_sec"], r["submitted_at"]))
        names, out, rank = self._names(), [], 0
        for i, r in enumerate(rows, 1):
            if i == 1 or (r["percent"], r["duration_sec"]) != (rows[i - 2]["percent"], rows[i - 2]["duration_sec"]):
                rank = i                                      # standard competition ranking (1, 2, 2, 4)
            out.append({"rank": rank, "username": r["username"], "name": names.get(r["username"], r["username"]),
                        "percent": r["percent"], "grade": r["grade"], "duration_sec": r["duration_sec"],
                        "date": r["submitted_at"][:10], "result_id": r["result_id"]})
        return out[:top] if top else out

    def overall(self, period: str = "all", min_quizzes: int = 1, top: int | None = 10) -> list[dict]:
        since = _since(period)
        best = defaultdict(dict)                              # username -> quiz_id -> best percent
        for r in self.results.list(mode="Exam", start=since):
            if r["percent"] > best[r["username"]].get(r["quiz_id"], -1):
                best[r["username"]][r["quiz_id"]] = r["percent"]
        names = self._names()
        rows = [{"username": u, "name": names.get(u, u), "quizzes": len(q), "average": round(sum(q.values()) / len(q), 2),
                 "points": round(sum(q.values()), 1)} for u, q in best.items() if len(q) >= min_quizzes]
        rows.sort(key=lambda x: (-x["average"], -x["quizzes"], x["username"]))
        rank = 0
        for i, row in enumerate(rows, 1):
            if i == 1 or (row["average"], row["quizzes"]) != (rows[i - 2]["average"], rows[i - 2]["quizzes"]):
                rank = i
            row["rank"] = rank
        return rows[:top] if top else rows

    def rank_of(self, username: str, quiz_id: str | None = None) -> dict | None:
        rows = self.for_quiz(quiz_id, top=None) if quiz_id else self.overall(top=None)
        for row in rows:
            if row["username"] == username:
                return {**row, "out_of": len(rows)}
        return None
