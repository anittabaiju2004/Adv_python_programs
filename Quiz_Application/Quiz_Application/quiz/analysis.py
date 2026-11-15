"""Performance Analysis: student and quiz statistics, strengths and weak
areas, score trends, and matplotlib charts."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .database import JSONDatabase
from .results import ResultManager
from .utils import DIFFICULTIES, GRADES, QuizError

WEAK_THRESHOLD = 60.0        # category accuracy below this (with enough answers) is a weak area
MIN_ANSWERS = 5


class PerformanceAnalyzer:
    def __init__(self, db: JSONDatabase):
        self.db = db
        self.results = ResultManager(db)

    @staticmethod
    def _accuracy(answers: list[dict], key: str) -> dict[str, dict]:
        acc = defaultdict(lambda: {"answered": 0, "correct": 0, "total": 0})
        for a in answers:
            s = acc[a[key]]
            s["total"] += 1
            if a["status"] != "SKIPPED":
                s["answered"] += 1
            s["correct"] += a["status"] == "CORRECT"
        for s in acc.values():
            s["accuracy"] = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0.0
        return dict(acc)

    def student(self, username: str) -> dict:
        rs = sorted(self.results.list(username), key=lambda r: (r["submitted_at"], r["result_id"]))
        if not rs:
            return {"username": username, "attempts": 0}
        exams = [r for r in rs if r["mode"] == "Exam"]
        answers = [a for r in rs for a in r["answers"]]
        by_cat = self._accuracy(answers, "category")
        by_diff = self._accuracy(answers, "difficulty")
        weak = [c for c, s in by_cat.items() if s["total"] >= MIN_ANSWERS and s["accuracy"] < WEAK_THRESHOLD]
        strong = [c for c, s in by_cat.items() if s["total"] >= MIN_ANSWERS and s["accuracy"] >= 80]
        first, last = [r["percent"] for r in rs[:3]], [r["percent"] for r in rs[-3:]]
        n_q = sum(len(r["answers"]) for r in rs)
        return {
            "username": username, "attempts": len(rs), "exams": len(exams), "practice": len(rs) - len(exams),
            "average": round(sum(r["percent"] for r in rs) / len(rs), 1),
            "exam_average": round(sum(r["percent"] for r in exams) / len(exams), 1) if exams else None,
            "best": max(r["percent"] for r in rs), "passed": sum(r["passed"] for r in exams),
            "pass_rate": round(sum(r["passed"] for r in exams) / len(exams) * 100, 1) if exams else None,
            "certificates": sum(1 for r in exams if r["certificate_code"]),
            "questions_answered": n_q, "accuracy": round(sum(a["status"] == "CORRECT" for a in answers) / n_q * 100, 1),
            "avg_sec_per_question": round(sum(r["duration_sec"] for r in rs) / n_q, 1) if n_q else 0,
            "by_category": by_cat, "by_difficulty": {d: by_diff[d] for d in DIFFICULTIES if d in by_diff},
            "weak_areas": sorted(weak, key=lambda c: by_cat[c]["accuracy"]), "strengths": sorted(strong),
            "improvement": round(sum(last) / len(last) - sum(first) / len(first), 1) if len(rs) >= 4 else None,
            "trend": [(r["submitted_at"][:10], r["percent"], r["mode"]) for r in rs],
        }

    def quiz(self, quiz_id: str) -> dict:
        rs = self.results.list(quiz_id=quiz_id, mode="Exam")
        if not rs:
            return {"quiz_id": quiz_id, "attempts": 0}
        pct = [r["percent"] for r in rs]
        qstats = defaultdict(lambda: {"attempts": 0, "correct": 0, "text": ""})
        for r in rs:
            for a in r["answers"]:
                s = qstats[a["question_id"]]
                s["attempts"] += 1
                s["correct"] += a["status"] == "CORRECT"
                s["text"] = a["text"]
        hardest = sorted(({"question_id": k, **v, "correct_pct": round(v["correct"] / v["attempts"] * 100, 1)}
                          for k, v in qstats.items() if v["attempts"] >= 2), key=lambda x: x["correct_pct"])[:5]
        grades = Counter(r["grade"] for r in rs)
        return {"quiz_id": quiz_id, "title": rs[0]["quiz_title"], "attempts": len(rs),
                "students": len({r["username"] for r in rs}), "average": round(sum(pct) / len(pct), 1),
                "highest": max(pct), "lowest": min(pct),
                "pass_rate": round(sum(r["passed"] for r in rs) / len(rs) * 100, 1),
                "avg_duration": round(sum(r["duration_sec"] for r in rs) / len(rs), 1),
                "time_ups": sum(r["time_up"] for r in rs),
                "grade_distribution": {g: grades.get(g, 0) for _, g, _ in GRADES}, "hardest": hardest}

    # --------------------------------------------------------------- charts
    @staticmethod
    def _plt():
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt

    def student_charts(self, username: str, out_dir: Path | str) -> list[Path]:
        """Score trend line and category accuracy bar chart (PNG)."""
        s = self.student(username)
        if not s["attempts"]:
            raise QuizError("No quiz attempts yet.")
        plt = self._plt()
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        fig, ax = plt.subplots(figsize=(8, 3.6))
        xs = list(range(1, len(s["trend"]) + 1))
        ax.plot(xs, [t[1] for t in s["trend"]], color="#2a6f97", marker="o", linewidth=2, label="Score %")
        exam_x = [x for x, t in zip(xs, s["trend"]) if t[2] == "Exam"]
        ax.scatter(exam_x, [t[1] for t in s["trend"] if t[2] == "Exam"], s=70, facecolors="none",
                   edgecolors="#d1495b", linewidths=1.6, label="Exam attempt", zorder=3)
        ax.axhline(50, color="#999", linestyle="--", linewidth=1)
        ax.set_ylim(0, 105)
        ax.set_xlabel("Attempt")
        ax.set_ylabel("Score %")
        ax.set_title(f"Score trend — {username}")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right", fontsize=8)
        p = out / f"trend_{username}.png"
        fig.savefig(p, dpi=120, bbox_inches="tight")
        plt.close(fig)
        paths.append(p)
        cats = sorted(s["by_category"].items(), key=lambda kv: kv[1]["accuracy"])
        fig, ax = plt.subplots(figsize=(8, 0.5 * len(cats) + 1.4))
        colors = ["#d1495b" if v["accuracy"] < WEAK_THRESHOLD else "#2e9d5b" if v["accuracy"] >= 80 else "#edae49"
                  for _, v in cats]
        ax.barh([c for c, _ in cats], [v["accuracy"] for _, v in cats], color=colors)
        for i, (_, v) in enumerate(cats):
            ax.text(v["accuracy"] + 1, i, f"{v['accuracy']:.0f}% ({v['correct']}/{v['total']})", va="center", fontsize=8)
        ax.set_xlim(0, 115)
        ax.set_xlabel("Accuracy %")
        ax.set_title("Accuracy by category (red = weak, green = strong)")
        p = out / f"categories_{username}.png"
        fig.savefig(p, dpi=120, bbox_inches="tight")
        plt.close(fig)
        paths.append(p)
        return paths

    def quiz_chart(self, quiz_id: str, out_dir: Path | str) -> Path:
        q = self.quiz(quiz_id)
        if not q["attempts"]:
            raise QuizError("No exam attempts for this quiz yet.")
        plt = self._plt()
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 3.4))
        grades = list(q["grade_distribution"])
        ax.bar(grades, [q["grade_distribution"][g] for g in grades],
               color=["#2e9d5b", "#55a868", "#8fbf5f", "#edae49", "#f28e2b", "#d1495b"])
        ax.set_title(f"Grade distribution — {q['title']}")
        ax.set_ylabel("Attempts")
        from matplotlib.ticker import MaxNLocator
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))     # attempts are whole numbers
        ax.grid(axis="y", alpha=0.3)
        p = out / f"grades_{quiz_id}.png"
        fig.savefig(p, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return p
