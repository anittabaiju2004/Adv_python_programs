"""Admin Panel: business dashboard, system statistics and the activity log."""
from __future__ import annotations

from datetime import date

from .customers import CustomerManager
from .database import JSONDatabase
from .products import ProductManager
from .purchases import PurchaseManager
from .reports import ReportGenerator
from .suppliers import SupplierManager


class AdminPanel:
    def __init__(self, db: JSONDatabase, report_dir="."):
        self.db = db
        self.products = ProductManager(db)
        self.reports = ReportGenerator(db, report_dir)

    def dashboard(self, today: date | None = None) -> dict:
        today = today or date.today()
        month_start = today.replace(day=1)
        t = self.reports.sales_report(today, today)
        m = self.reports.sales_report(month_start, today)
        mp = self.reports.profit_report(month_start, today)
        val = self.products.valuation()
        return {
            "date": today.isoformat(),
            "today_sales": t["grand_total"], "today_invoices": t["invoices"],
            "month_sales": m["grand_total"], "month_invoices": m["invoices"],
            "month_profit": mp["gross_profit"], "month_margin": mp["margin"],
            "top_products": mp["products"][:5],
            "stock_value": val["cost_value"], "products": val["products"],
            "low_stock": self.products.low_stock(), "out_of_stock": self.products.out_of_stock(),
            "receivable": round(sum(x["receivable"] for x in CustomerManager(self.db).receivables()), 2),
            "payable": round(sum(x["payable"] for x in SupplierManager(self.db).payables()), 2),
            "open_orders": len(PurchaseManager(self.db).list("ORDERED")),
        }

    def system_stats(self) -> dict:
        return {name: len(self.db.all(name)) for name in ("users", "categories", "products", "suppliers", "customers",
                                                           "purchases", "sales", "stock_movements", "activity")}

    def activity(self, limit: int = 40, user: str | None = None) -> list[dict]:
        log = self.db.all("activity")
        if user:
            log = [a for a in log if a["user"] == user.lower()]
        return log[::-1][:limit]
