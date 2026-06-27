# Project Brief: Country-Aware Transaction Audit & Workforce Forecasting Dashboard

## Goal

Build an automation dashboard that helps an organization detect suspicious transaction/bill entries and forecast workforce load for the upcoming work period.

## Module 1: Country-Aware Transaction Audit

The transaction audit module checks submitted bills against market benchmark data. The dashboard includes a country/market selector so the comparison can be adjusted for Bangladesh or another country.

### Key Capabilities

- Select country/market from the sidebar.
- Use Bangladesh by default.
- Choose another built-in country or use custom settings.
- Adjust currency display, market multiplier, and extra tax/transport/landed cost.
- Support transaction amounts in BDT or selected local currency.
- Detect high price deviation, duplicate invoice risk, missing documents, unusual quantity, and invoice mismatch.
- Generate query messages for the transaction builder.

### Why this matters

A transaction that looks expensive in one country may be normal in another country because of currency, taxes, transport, import cost, and local market conditions. The country selector makes the audit fairer.

## Module 2: Workload Forecasting

The workforce module estimates workload pressure using operational work data only. It does not diagnose mental health.

### Key Capabilities

- Forecast workload for 3 to 14 days.
- Default forecast is 7 days.
- User can input standard working hours/day.
- Estimate expected task count, expected work hours, pressure score, and rest recommendation.
- Show employee-wise and department-wise workload pressure.

### Ethical Boundary

The system must not monitor private messages, keystrokes, webcam data, screenshots, or health records. It should support workload balancing, not employee surveillance.

## Tech Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly

## Run Options

- Local laptop/PC using `streamlit run app.py`
- Google Colab using the included `Audit_Workforce_Dashboard_Colab.ipynb`
