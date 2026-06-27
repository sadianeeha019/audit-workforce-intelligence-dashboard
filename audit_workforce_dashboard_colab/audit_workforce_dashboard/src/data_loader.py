from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_sample_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    benchmarks = pd.read_csv(DATA_DIR / "market_benchmarks.csv")
    work_logs = pd.read_csv(DATA_DIR / "work_logs.csv")
    planned_tasks = pd.read_csv(DATA_DIR / "planned_tasks.csv")
    return transactions, benchmarks, work_logs, planned_tasks
