from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class WorkloadConfig:
    forecast_days: int = 7
    normal_daily_hours: float = 8.0
    high_pressure_threshold: float = 70.0
    medium_pressure_threshold: float = 45.0


def build_workload_forecast(
    work_logs: pd.DataFrame,
    planned_tasks: pd.DataFrame,
    config: WorkloadConfig | None = None,
) -> pd.DataFrame:
    """Estimate next-7-day workload pressure from operational work data only.

    This is not a mental-health diagnosis. It uses task load, deadline urgency,
    backlog, overtime, and task complexity to support fair workload planning.
    """
    cfg = config or WorkloadConfig()
    logs = work_logs.copy()
    plan = planned_tasks.copy()

    logs["date"] = pd.to_datetime(logs["date"], errors="coerce")
    plan["due_date"] = pd.to_datetime(plan["due_date"], errors="coerce")

    numeric_cols = [
        "tasks_assigned",
        "tasks_completed",
        "backlog",
        "hours_worked",
        "urgent_tasks",
        "avg_complexity",
        "rest_hours",
    ]
    for col in numeric_cols:
        if col in logs.columns:
            logs[col] = pd.to_numeric(logs[col], errors="coerce").fillna(0)

    for col in ["planned_tasks", "planned_complexity", "urgent_flag"]:
        if col in plan.columns:
            plan[col] = pd.to_numeric(plan[col], errors="coerce").fillna(0)

    recent_cutoff = logs["date"].max() - pd.Timedelta(days=13)
    recent = logs[logs["date"] >= recent_cutoff].copy()

    recent_agg = recent.groupby(["employee_id", "employee_name", "department"], as_index=False).agg(
        recent_daily_assigned=("tasks_assigned", "mean"),
        recent_daily_completed=("tasks_completed", "mean"),
        current_backlog=("backlog", "last"),
        recent_daily_hours=("hours_worked", "mean"),
        recent_daily_urgent=("urgent_tasks", "mean"),
        recent_complexity=("avg_complexity", "mean"),
        recent_daily_rest=("rest_hours", "mean"),
    )

    start_date = logs["date"].max() + pd.Timedelta(days=1)
    end_date = start_date + pd.Timedelta(days=cfg.forecast_days - 1)
    plan_7d = plan[(plan["due_date"] >= start_date) & (plan["due_date"] <= end_date)].copy()

    if len(plan_7d):
        plan_agg = plan_7d.groupby(["employee_id"], as_index=False).agg(
            planned_7d_tasks=("planned_tasks", "sum"),
            urgent_7d_tasks=("urgent_flag", "sum"),
            avg_planned_complexity=("planned_complexity", "mean"),
        )
    else:
        plan_agg = pd.DataFrame(columns=["employee_id", "planned_7d_tasks", "urgent_7d_tasks", "avg_planned_complexity"])

    forecast = recent_agg.merge(plan_agg, on="employee_id", how="left")
    forecast[["planned_7d_tasks", "urgent_7d_tasks", "avg_planned_complexity"]] = forecast[
        ["planned_7d_tasks", "urgent_7d_tasks", "avg_planned_complexity"]
    ].fillna(0)

    forecast["expected_7d_tasks"] = (
        forecast["recent_daily_assigned"] * cfg.forecast_days * 0.45
        + forecast["planned_7d_tasks"] * 0.55
        + forecast["current_backlog"] * 0.25
    ).round(1)

    forecast["expected_7d_hours"] = (
        forecast["recent_daily_hours"] * cfg.forecast_days * 0.50
        + forecast["expected_7d_tasks"] * (0.55 + forecast["recent_complexity"].clip(1, 5) * 0.09)
    ).round(1)

    task_load_score = _minmax_score(forecast["expected_7d_tasks"])
    overtime_score = ((forecast["expected_7d_hours"] - cfg.normal_daily_hours * cfg.forecast_days).clip(lower=0) / 18 * 100).clip(upper=100)
    backlog_score = _minmax_score(forecast["current_backlog"])
    urgency_score = ((forecast["urgent_7d_tasks"] + forecast["recent_daily_urgent"] * 2) / 8 * 100).clip(upper=100)
    complexity_score = ((forecast[["recent_complexity", "avg_planned_complexity"]].max(axis=1).clip(1, 5) - 1) / 4 * 100)
    rest_deficit_score = ((cfg.normal_daily_hours - forecast["recent_daily_rest"].clip(upper=cfg.normal_daily_hours)) / cfg.normal_daily_hours * 100).clip(0, 100)

    forecast["workload_pressure_score"] = (
        task_load_score * 0.30
        + urgency_score * 0.22
        + overtime_score * 0.20
        + backlog_score * 0.14
        + complexity_score * 0.09
        + rest_deficit_score * 0.05
    ).round(1)

    forecast["pressure_level"] = np.select(
        [
            forecast["workload_pressure_score"] >= cfg.high_pressure_threshold,
            forecast["workload_pressure_score"] >= cfg.medium_pressure_threshold,
        ],
        ["High", "Medium"],
        default="Low",
    )

    forecast["suggested_additional_rest_hours_7d"] = (
        ((forecast["workload_pressure_score"] - 60).clip(lower=0) / 10 * 1.5)
        + ((forecast["expected_7d_hours"] - cfg.normal_daily_hours * cfg.forecast_days).clip(lower=0) / 6)
    ).clip(0, 10).round(1)

    forecast["recommendation"] = forecast.apply(_recommendation, axis=1)

    return forecast.sort_values("workload_pressure_score", ascending=False)


def _minmax_score(series: pd.Series) -> pd.Series:
    minimum = series.min()
    maximum = series.max()
    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - minimum) / (maximum - minimum) * 100).clip(0, 100)


def _recommendation(row: pd.Series) -> str:
    score = float(row.get("workload_pressure_score", 0))
    rest = float(row.get("suggested_additional_rest_hours_7d", 0))
    if score >= 80:
        return f"Critical load risk: pause new assignments, redistribute urgent work, and plan about {rest:.1f} extra rest hours."
    if score >= 70:
        return f"High load: assign backup support and plan about {rest:.1f} extra rest hours."
    if score >= 45:
        return "Medium load: monitor deadlines and avoid adding urgent tasks without removing lower-priority work."
    return "Normal load: continue current plan."


def workload_summary(forecast: pd.DataFrame) -> Dict[str, float]:
    return {
        "employees": int(len(forecast)),
        "high_pressure_employees": int((forecast["pressure_level"] == "High").sum()),
        "avg_pressure_score": float(forecast["workload_pressure_score"].mean()) if len(forecast) else 0,
        "total_expected_7d_tasks": float(forecast["expected_7d_tasks"].sum()),
        "total_suggested_rest_hours": float(forecast["suggested_additional_rest_hours_7d"].sum()),
    }
