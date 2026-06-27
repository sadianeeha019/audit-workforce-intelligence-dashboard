# AI-Powered Transaction Audit & Workforce Forecasting Dashboard

A working MVP dashboard that supports two business goals:

1. **Country-aware transaction / bill audit**: Checks whether submitted bills look accurate compared with market benchmarks, selected country/currency settings, document status, invoice totals, quantity patterns, and duplicate-risk signals.
2. **Workload forecasting**: Forecasts employee workload pressure for a selected upcoming window and lets the user change the standard daily working hours from the dashboard.

> Important: The workload module does **not** diagnose mental health. It estimates workload pressure from work-related signals such as assigned tasks, deadlines, backlog, overtime, task complexity, and rest hours.

---

## New Features in This Version

- **Google Colab compatible** run instructions.
- **Country / market selector** in the sidebar.
- Built-in country options: Bangladesh, India, United States, United Kingdom, United Arab Emirates, Singapore.
- **Other / Custom** option for any country.
- Editable currency code, symbol, BDT conversion rate, local market multiplier, and landed cost percentage.
- Transaction upload supports either BDT columns or selected-market local currency columns.
- **Standard working hours input** so workload pressure changes dynamically.
- Adjustable forecast window from 3 to 14 days.

---

## Features

### Transaction Audit Module

- Compares submitted unit price with country-adjusted expected benchmark unit price.
- Calculates price deviation percentage.
- Estimates possible overbilling amount in selected currency and BDT.
- Detects possible duplicate transactions within a configurable time window.
- Detects quantity outliers.
- Detects missing documents.
- Detects invoice total mismatch.
- Produces audit risk score from 0 to 100.
- Generates automatic query messages for transaction builders.

### Workload Forecasting Module

- Uses recent task completion history and planned upcoming tasks.
- Forecasts expected tasks for the selected forecast window.
- Estimates expected working hours.
- Uses your selected standard working hours/day.
- Calculates workload pressure score.
- Classifies pressure level as Low, Medium, or High.
- Recommends task redistribution or additional rest hours when needed.

### Dashboard Pages

- Executive Overview
- Transaction Audit
- Vendor Risk
- Workload Forecast
- Query Messages
- Data & Ethics Notes

---

## Project Structure

```text
 audit_workforce_dashboard/
 ├── app.py
 ├── requirements.txt
 ├── README.md
 ├── PROJECT_BRIEF.md
 ├── Audit_Workforce_Dashboard_Colab.ipynb
 ├── data/
 │   ├── transactions.csv
 │   ├── market_benchmarks.csv
 │   ├── work_logs.csv
 │   └── planned_tasks.csv
 ├── scripts/
 │   └── generate_sample_data.py
 └── src/
     ├── __init__.py
     ├── audit_engine.py
     ├── workload_engine.py
     ├── country_config.py
     └── data_loader.py
```

---

## How to Run in Google Colab

### Option A: Use the included notebook

1. Upload `Audit_Workforce_Dashboard_Colab.ipynb` to Colab.
2. Upload this project ZIP when the notebook asks for it.
3. Run all cells.
4. Colab will open the Streamlit dashboard on port `8501`.

### Option B: Copy these commands into a Colab notebook

Upload the project ZIP first, then run:

```python
from google.colab import files
uploaded = files.upload()
zip_name = next(iter(uploaded.keys()))
```

```python
import zipfile, os, shutil
extract_dir = "/content/audit_dashboard_project"
shutil.rmtree(extract_dir, ignore_errors=True)
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(zip_name, "r") as z:
    z.extractall(extract_dir)

# Find project folder automatically
for root, dirs, files_ in os.walk(extract_dir):
    if "app.py" in files_ and "requirements.txt" in files_:
        project_dir = root
        break
print("Project folder:", project_dir)
```

```python
%cd $project_dir
!pip -q install -r requirements.txt
```

```python
!streamlit run app.py --server.port 8501 --server.headless true > streamlit.log 2>&1 &
from google.colab import output
output.serve_kernel_port_as_window(8501)
```

---

## How to Run Locally

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate it

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

---

## Input Data Schemas

### `transactions.csv`

For BDT input:

```text
transaction_id, submitted_date, builder_name, builder_email, department, vendor,
item_name, quantity, unit_price_bdt, invoice_total_bdt, document_status
```

For selected country/local currency input:

```text
transaction_id, submitted_date, builder_name, builder_email, department, vendor,
item_name, quantity, unit_price_local, invoice_total_local, document_status
```

### `market_benchmarks.csv`

```text
item_name, global_market_price_bdt, local_market_price_bdt,
tax_transport_margin_pct, allowed_deviation_pct, benchmark_source
```

### `work_logs.csv`

```text
date, employee_id, employee_name, department, tasks_assigned, tasks_completed,
backlog, hours_worked, urgent_tasks, avg_complexity, rest_hours
```

### `planned_tasks.csv`

```text
due_date, employee_id, employee_name, department, planned_tasks,
planned_complexity, urgent_flag
```

---

## Country-Aware Transaction Audit Logic

For Bangladesh:

```text
expected_unit_price_bdt = local_market_price_bdt × (1 + tax_transport_margin_pct / 100)
```

For another country:

```text
country_adjusted_base_bdt = local_market_price_bdt × local_market_multiplier
expected_unit_price_bdt = country_adjusted_base_bdt × (1 + (tax_transport_margin_pct + extra_landed_cost_pct) / 100)
```

Currency display:

```text
amount_local_currency = amount_bdt / bdt_per_currency
```

Price deviation:

```text
price_deviation_pct = (submitted_unit_price_bdt - expected_unit_price_bdt) / expected_unit_price_bdt × 100
```

> Demo FX rates are placeholders. In production, replace them with verified live FX and market benchmark APIs.

---

## Workload Pressure Logic

The workload score uses:

```text
Workload Pressure Score =
(Task Load × 0.30)
+ (Urgency × 0.22)
+ (Overtime × 0.20)
+ (Backlog × 0.14)
+ (Complexity × 0.09)
+ (Rest Deficit × 0.05)
```

The overtime part changes when you edit **Standard working hours per day** in the sidebar.

Pressure levels:

```text
0–44.9   = Low
45–69.9  = Medium
70–100   = High
```

---

## Ethical and Privacy Rules

Do **not** collect:

- Private messages
- Keystrokes
- Webcam data
- Screenshots
- Personal health records
- Medical or mental-health labels

Use only work-related operational data. The goal is workload balance, not surveillance.

---

## Suggested Upgrades

- Connect to ERP/accounting database.
- Add live market benchmark APIs.
- Add live FX rate conversion.
- Add role-based access control.
- Add email/Teams/Slack integration.
- Store query response history.
- Add reviewer approval workflow.
- Train a supervised risk model after collecting enough reviewed cases.
