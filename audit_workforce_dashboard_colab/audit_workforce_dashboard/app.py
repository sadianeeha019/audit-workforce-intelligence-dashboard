from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.audit_engine import audit_summary, audit_transactions
from src.country_config import COUNTRY_MARKETS, CountryMarketConfig, get_country_market
from src.data_loader import load_sample_data
from src.workload_engine import WorkloadConfig, build_workload_forecast, workload_summary

st.set_page_config(
    page_title="Transaction Audit & Workforce Forecasting Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def get_data():
    return load_sample_data()


def metric_card(label: str, value, help_text: str | None = None):
    st.metric(label=label, value=value, help=help_text)


def format_money(value: float, market: CountryMarketConfig) -> str:
    return f"{market.currency_symbol}{value:,.0f} {market.currency_code}"


def build_custom_market() -> CountryMarketConfig:
    st.sidebar.caption("Custom country settings. Use demo rates or replace with your own verified FX/market data.")
    country_name = st.sidebar.text_input("Custom country name", value="Other Country")
    currency_code = st.sidebar.text_input("Currency code", value="LOCAL")
    currency_symbol = st.sidebar.text_input("Currency symbol", value="¤")
    bdt_per_currency = st.sidebar.number_input(
        "BDT equivalent for 1 local currency unit",
        min_value=0.0001,
        value=1.0,
        step=0.1,
        help="Example: if 1 USD ≈ 118 BDT, enter 118. Replace demo value with verified rate.",
    )
    market_multiplier = st.sidebar.number_input(
        "Local market multiplier",
        min_value=0.10,
        max_value=5.00,
        value=1.00,
        step=0.05,
        help="Use >1 if the selected market is usually more expensive than the benchmark, <1 if cheaper.",
    )
    landed_cost = st.sidebar.number_input(
        "Extra tax / transport / landed cost %",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
    )
    return CountryMarketConfig(country_name, currency_code.upper(), currency_symbol, bdt_per_currency, market_multiplier, landed_cost)


transactions, benchmarks, work_logs, planned_tasks = get_data()

st.sidebar.title("Dashboard Menu")
page = st.sidebar.radio(
    "Choose a page",
    [
        "Executive Overview",
        "Transaction Audit",
        "Vendor Risk",
        "Workload Forecast",
        "Query Messages",
        "Data & Ethics Notes",
    ],
)

st.sidebar.markdown("---")
st.sidebar.subheader("Market / Country Settings")
country_option = st.sidebar.selectbox(
    "Select transaction market",
    options=list(COUNTRY_MARKETS.keys()) + ["Other / Custom"],
    index=0,
    help="This adjusts benchmark price, currency display, and overbilling calculation for the selected market.",
)

if country_option == "Other / Custom":
    market_config = build_custom_market()
else:
    market_config = get_country_market(country_option)

st.sidebar.info(
    f"Market: {market_config.country_name}\n\n"
    f"Currency: {market_config.currency_code}\n\n"
    f"Demo FX: 1 {market_config.currency_code} = {market_config.bdt_per_currency:,.2f} BDT\n\n"
    f"Market multiplier: {market_config.local_market_multiplier:.2f}\n\n"
    f"Extra landed cost: {market_config.additional_landed_cost_pct:.1f}%"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Workload Settings")
normal_daily_hours = st.sidebar.number_input(
    "Standard working hours per day",
    min_value=4.0,
    max_value=14.0,
    value=8.0,
    step=0.5,
    help="Change this to see how workload pressure and rest recommendation update.",
)
forecast_days = st.sidebar.slider("Forecast window", min_value=3, max_value=14, value=7, step=1)

st.sidebar.markdown("---")
st.sidebar.caption(
    "MVP built with sample data. Replace CSV files in the data folder with real company data when deploying. "
    "Demo FX rates are placeholders, not live financial rates."
)

workload_config = WorkloadConfig(forecast_days=forecast_days, normal_daily_hours=normal_daily_hours)
audited = audit_transactions(transactions, benchmarks, market_config=market_config)
forecast = build_workload_forecast(work_logs, planned_tasks, config=workload_config)

if page == "Executive Overview":
    st.title("AI-Powered Transaction Audit & Workforce Forecasting Dashboard")
    st.write(
        "This MVP checks bills against country-adjusted benchmark prices, flags audit risks, generates query messages, "
        "and forecasts workload pressure using operational work data only."
    )

    a_sum = audit_summary(audited)
    w_sum = workload_summary(forecast)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Transactions", a_sum["total_transactions"])
    with c2:
        metric_card("Flagged Transactions", a_sum["flagged_transactions"])
    with c3:
        metric_card("Possible Overbilling", format_money(a_sum["estimated_overbilling_local"], market_config))
    with c4:
        metric_card("High Workload Employees", w_sum["high_pressure_employees"])

    c5, c6, c7 = st.columns(3)
    with c5:
        metric_card("Selected Market", market_config.country_name)
    with c6:
        metric_card("Standard Daily Hours", f"{normal_daily_hours:.1f}h")
    with c7:
        metric_card("Forecast Window", f"{forecast_days} days")

    st.subheader("Audit Risk Distribution")
    audit_counts = audited["audit_level"].value_counts().reset_index()
    audit_counts.columns = ["audit_level", "count"]
    st.plotly_chart(px.bar(audit_counts, x="audit_level", y="count", text="count"), use_container_width=True)

    st.subheader(f"Next {forecast_days}-Day Workload Pressure")
    st.plotly_chart(
        px.bar(
            forecast,
            x="employee_name",
            y="workload_pressure_score",
            color="pressure_level",
            hover_data=["department", "expected_7d_tasks", "expected_7d_hours", "recommendation"],
        ),
        use_container_width=True,
    )

    st.subheader("Top Risk Items")
    top_risk = audited.head(8)[
        [
            "transaction_id",
            "department",
            "vendor",
            "item_name",
            "selected_country",
            "currency_code",
            "unit_price_local",
            "expected_unit_price_local",
            "price_deviation_pct",
            "audit_risk_score",
            "audit_level",
            "suggested_action",
        ]
    ]
    st.dataframe(top_risk, use_container_width=True, hide_index=True)

elif page == "Transaction Audit":
    st.title("Transaction / Bill Audit")
    st.write(
        "Upload real transaction data or use the sample data. The audit engine compares submitted unit price "
        "against a country-adjusted benchmark and checks duplicate, quantity, document, and invoice mismatch risks."
    )

    st.info(
        "For uploaded CSV, you can use either BDT columns `unit_price_bdt`, `invoice_total_bdt` or selected-market "
        "currency columns `unit_price_local`, `invoice_total_local`."
    )

    uploaded_tx = st.file_uploader("Optional: upload transaction CSV", type=["csv"])
    if uploaded_tx is not None:
        custom_tx = pd.read_csv(uploaded_tx)
        audited_view = audit_transactions(custom_tx, benchmarks, market_config=market_config)
    else:
        audited_view = audited

    level_filter = st.multiselect(
        "Filter audit level",
        options=sorted(audited_view["audit_level"].unique()),
        default=sorted(audited_view["audit_level"].unique()),
    )
    filtered = audited_view[audited_view["audit_level"].isin(level_filter)]

    c1, c2, c3, c4 = st.columns(4)
    summary = audit_summary(filtered)
    with c1:
        metric_card("Rows Displayed", summary["total_transactions"])
    with c2:
        metric_card("Flagged", summary["flagged_transactions"])
    with c3:
        metric_card("High Risk", summary["high_risk_transactions"])
    with c4:
        metric_card("Overbilling Estimate", format_money(summary["estimated_overbilling_local"], market_config))

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download audited transactions as CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="audited_transactions_country_adjusted.csv",
        mime="text/csv",
    )

    st.subheader("Price Deviation by Transaction")
    st.plotly_chart(
        px.scatter(
            filtered,
            x="expected_unit_price_local",
            y="unit_price_local",
            color="audit_level",
            size="audit_risk_score",
            hover_data=["transaction_id", "vendor", "item_name", "selected_country", "price_deviation_pct"],
            labels={
                "expected_unit_price_local": f"Expected Unit Price ({market_config.currency_code})",
                "unit_price_local": f"Submitted Unit Price ({market_config.currency_code})",
            },
        ),
        use_container_width=True,
    )

elif page == "Vendor Risk":
    st.title("Vendor Risk Analysis")
    vendor = audited.groupby("vendor", as_index=False).agg(
        transactions=("transaction_id", "count"),
        avg_risk_score=("audit_risk_score", "mean"),
        flagged_count=("audit_level", lambda s: (s != "Pass").sum()),
        estimated_overbilling_local=("estimated_overbilling_local", "sum"),
        duplicate_cases=("duplicate_possible", "sum"),
    )
    vendor["avg_risk_score"] = vendor["avg_risk_score"].round(1)
    vendor["estimated_overbilling_local"] = vendor["estimated_overbilling_local"].round(2)
    vendor = vendor.sort_values("avg_risk_score", ascending=False)

    st.dataframe(vendor, use_container_width=True, hide_index=True)
    st.plotly_chart(
        px.bar(
            vendor,
            x="vendor",
            y="avg_risk_score",
            text="avg_risk_score",
            hover_data=["transactions", "flagged_count", "estimated_overbilling_local", "duplicate_cases"],
        ),
        use_container_width=True,
    )

elif page == "Workload Forecast":
    st.title(f"{forecast_days}-Day Workload Forecast")
    st.warning(
        "This module does not diagnose mental health. It estimates workload pressure using operational work data only: "
        "task load, deadlines, backlog, overtime, task complexity, and rest hours."
    )

    st.info(
        f"Current standard working hour input: {normal_daily_hours:.1f} hours/day. "
        "Change it from the sidebar to see pressure score and rest recommendation update."
    )

    c1, c2, c3, c4 = st.columns(4)
    w_sum = workload_summary(forecast)
    with c1:
        metric_card("Employees", w_sum["employees"])
    with c2:
        metric_card("High Pressure", w_sum["high_pressure_employees"])
    with c3:
        metric_card(f"Expected {forecast_days}D Tasks", f"{w_sum['total_expected_7d_tasks']:.0f}")
    with c4:
        metric_card("Suggested Rest Hours", f"{w_sum['total_suggested_rest_hours']:.1f}")

    st.dataframe(forecast, use_container_width=True, hide_index=True)

    st.subheader("Pressure Score by Employee")
    st.plotly_chart(
        px.bar(
            forecast,
            x="employee_name",
            y="workload_pressure_score",
            color="pressure_level",
            hover_data=["department", "expected_7d_tasks", "expected_7d_hours", "suggested_additional_rest_hours_7d"],
        ),
        use_container_width=True,
    )

    st.subheader(f"Expected {forecast_days}-Day Hours vs Tasks")
    st.plotly_chart(
        px.scatter(
            forecast,
            x="expected_7d_tasks",
            y="expected_7d_hours",
            color="pressure_level",
            size="workload_pressure_score",
            hover_data=["employee_name", "department", "recommendation"],
        ),
        use_container_width=True,
    )

elif page == "Query Messages":
    st.title("Auto-Generated Query Messages")
    flagged = audited[audited["audit_level"] != "Pass"].copy()
    st.write("These messages can be sent to the transaction creator/builder before approval.")

    if flagged.empty:
        st.success("No flagged transactions for the current market settings.")
    else:
        selected_id = st.selectbox("Select flagged transaction", flagged["transaction_id"].tolist())
        selected = flagged[flagged["transaction_id"] == selected_id].iloc[0]

        st.subheader("Message Preview")
        st.text_area("Query message", selected["query_message"], height=260)

        st.subheader("Flagged Transaction Details")
        st.dataframe(
            flagged[
                [
                    "transaction_id",
                    "builder_name",
                    "builder_email",
                    "vendor",
                    "item_name",
                    "selected_country",
                    "currency_code",
                    "unit_price_local",
                    "expected_unit_price_local",
                    "price_deviation_pct",
                    "audit_risk_score",
                    "audit_level",
                    "suggested_action",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

elif page == "Data & Ethics Notes":
    st.title("Data Schema, Deployment & Ethics Notes")
    st.subheader("Transaction data required")
    st.code(
        "transaction_id, submitted_date, builder_name, builder_email, department, vendor, "
        "item_name, quantity, document_status, plus unit_price_bdt/invoice_total_bdt OR "
        "unit_price_local/invoice_total_local",
        language="text",
    )

    st.subheader("Benchmark data required")
    st.code(
        "item_name, global_market_price_bdt, local_market_price_bdt, "
        "tax_transport_margin_pct, allowed_deviation_pct, benchmark_source",
        language="text",
    )

    st.subheader("Country / market settings")
    st.markdown(
        """
- Select **Bangladesh** when your submitted amount and benchmark should be evaluated in BDT.
- Select another country to convert display currency and adjust expected benchmark using market multiplier and landed cost.
- Select **Other / Custom** when you need a custom country, currency, FX rate, market multiplier, and tax/transport cost.
- Demo FX values are placeholders. In production, connect a verified FX/market API.
        """
    )

    st.subheader("Workload data required")
    st.code(
        "date, employee_id, employee_name, department, tasks_assigned, tasks_completed, "
        "backlog, hours_worked, urgent_tasks, avg_complexity, rest_hours",
        language="text",
    )

    st.subheader("Important limitations")
    st.markdown(
        """
- This MVP uses sample data, not live market APIs.
- Audit flags are decision-support signals, not final fraud proof.
- Workload score is not a medical or mental-health diagnosis.
- Do not collect private messages, screenshots, keystrokes, webcam data, or personal health data.
- Employees should know what data is used and why.
- Final approval should remain with a human reviewer.
        """
    )

    st.subheader("Suggested next upgrades")
    st.markdown(
        """
1. Connect to ERP/accounting database.
2. Add live FX rate and market benchmark APIs.
3. Add role-based access control.
4. Add email/Teams/Slack integration for query messages.
5. Add audit trail for every reviewer action.
6. Train a supervised model after collecting enough resolved audit cases.
        """
    )
