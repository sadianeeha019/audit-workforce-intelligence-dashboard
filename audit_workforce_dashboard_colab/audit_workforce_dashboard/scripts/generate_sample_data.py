from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

rng = np.random.default_rng(42)

items = [
    ("Laptop", 78000, 82000, 8, 12, "Internal vendor survey + online market average"),
    ("Router", 12500, 13200, 6, 15, "ICT equipment benchmark"),
    ("Network Switch", 28000, 30000, 7, 12, "ICT equipment benchmark"),
    ("Office Chair", 8500, 9000, 5, 18, "Furniture market survey"),
    ("Printer Toner", 4200, 4500, 4, 15, "Office supplies benchmark"),
    ("SSD 1TB", 9800, 10400, 5, 12, "Computer accessories survey"),
    ("Server RAM 32GB", 19000, 20500, 8, 12, "Hardware supplier quote average"),
    ("UPS 1200VA", 14500, 15200, 6, 15, "Power equipment benchmark"),
]
benchmarks = pd.DataFrame(
    items,
    columns=[
        "item_name",
        "global_market_price_bdt",
        "local_market_price_bdt",
        "tax_transport_margin_pct",
        "allowed_deviation_pct",
        "benchmark_source",
    ],
)
benchmarks.to_csv(DATA / "market_benchmarks.csv", index=False)

vendors = ["Alpha Traders", "MetroTech", "Eastern Supplies", "Nexus IT", "Prime Office Mart"]
departments = ["IT", "HR", "Finance", "Operations", "Admin"]
builders = [
    ("Rahim Ahmed", "rahim@example.com"),
    ("Nusrat Jahan", "nusrat@example.com"),
    ("Sadia Islam", "sadia@example.com"),
    ("Tanvir Hasan", "tanvir@example.com"),
    ("Farhana Najnin", "farhana@example.com"),
]

rows = []
start = pd.Timestamp("2026-06-01")
for i in range(80):
    item = benchmarks.sample(1, random_state=int(rng.integers(1, 999999))).iloc[0]
    builder_name, builder_email = builders[int(rng.integers(0, len(builders)))]
    qty = int(rng.choice([1, 1, 2, 2, 3, 4, 5, 8, 10]))
    expected = item.local_market_price_bdt * (1 + item.tax_transport_margin_pct / 100)
    multiplier = rng.normal(1.02, 0.10)

    # Inject anomalies.
    if i in [7, 18, 39, 52, 61]:
        multiplier = rng.uniform(1.30, 1.65)
    if i in [25, 64]:
        qty = int(rng.choice([25, 35, 50]))
    unit_price = round(expected * multiplier, 2)
    total = round(unit_price * qty, 2)
    if i in [12, 45]:
        total = round(total * rng.uniform(1.08, 1.18), 2)

    rows.append(
        {
            "transaction_id": f"TX-{1000+i}",
            "submitted_date": (start + pd.Timedelta(days=int(rng.integers(0, 25)))).date(),
            "builder_name": builder_name,
            "builder_email": builder_email,
            "department": departments[int(rng.integers(0, len(departments)))],
            "vendor": vendors[int(rng.integers(0, len(vendors)))],
            "item_name": item.item_name,
            "quantity": qty,
            "unit_price_bdt": unit_price,
            "invoice_total_bdt": total,
            "document_status": rng.choice(["Complete", "Complete", "Complete", "Missing quotation", "Incomplete invoice"]),
        }
    )

# Add a deliberate duplicate pair.
dup = rows[10].copy()
dup["transaction_id"] = "TX-1999"
dup["submitted_date"] = (pd.to_datetime(rows[10]["submitted_date"]) + pd.Timedelta(days=3)).date()
rows.append(dup)

transactions = pd.DataFrame(rows)
transactions.to_csv(DATA / "transactions.csv", index=False)

employees = [
    ("E001", "Ayesha Rahman", "IT Automation"),
    ("E002", "Mahin Khan", "IT Automation"),
    ("E003", "Rafi Ahmed", "Finance"),
    ("E004", "Nabila Islam", "Operations"),
    ("E005", "Tasnima Akter", "Admin"),
    ("E006", "Hasan Mahmud", "IT Support"),
    ("E007", "Mim Chowdhury", "HR"),
    ("E008", "Sajid Karim", "Procurement"),
]

log_rows = []
log_start = pd.Timestamp("2026-05-25")
for emp_id, name, dept in employees:
    base_load = rng.integers(4, 11)
    backlog = rng.integers(1, 8)
    for d in range(30):
        date = log_start + pd.Timedelta(days=d)
        assigned = max(0, int(rng.normal(base_load, 2)))
        completed = max(0, int(rng.normal(base_load - 1, 2)))
        backlog = max(0, backlog + assigned - completed)
        urgent = int(rng.choice([0, 0, 1, 1, 2, 3]))
        complexity = float(np.clip(rng.normal(3, 0.8), 1, 5).round(1))
        hours = float(np.clip(6.5 + assigned * 0.35 + urgent * 0.45 + complexity * 0.25 + rng.normal(0, 0.8), 5, 12).round(1))
        rest = float(np.clip(24 - hours - rng.normal(8, 1.0), 3, 10).round(1))
        log_rows.append(
            {
                "date": date.date(),
                "employee_id": emp_id,
                "employee_name": name,
                "department": dept,
                "tasks_assigned": assigned,
                "tasks_completed": completed,
                "backlog": backlog,
                "hours_worked": hours,
                "urgent_tasks": urgent,
                "avg_complexity": complexity,
                "rest_hours": rest,
            }
        )
work_logs = pd.DataFrame(log_rows)
work_logs.to_csv(DATA / "work_logs.csv", index=False)

plan_rows = []
future_start = log_start + pd.Timedelta(days=30)
for emp_id, name, dept in employees:
    for d in range(1, 11):
        planned = int(rng.integers(2, 9))
        urgent_flag = int(rng.choice([0, 0, 0, 1, 1, 2]))
        if emp_id in ["E001", "E006"] and d <= 7:
            planned += int(rng.integers(3, 8))
            urgent_flag += int(rng.integers(1, 3))
        plan_rows.append(
            {
                "due_date": (future_start + pd.Timedelta(days=d)).date(),
                "employee_id": emp_id,
                "employee_name": name,
                "department": dept,
                "planned_tasks": planned,
                "planned_complexity": float(np.clip(rng.normal(3.2, 0.8), 1, 5).round(1)),
                "urgent_flag": urgent_flag,
            }
        )
planned_tasks = pd.DataFrame(plan_rows)
planned_tasks.to_csv(DATA / "planned_tasks.csv", index=False)

print("Sample data generated in", DATA)
