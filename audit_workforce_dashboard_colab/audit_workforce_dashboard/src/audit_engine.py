from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from src.country_config import CountryMarketConfig, get_country_market


@dataclass
class AuditConfig:
    duplicate_window_days: int = 7
    high_risk_threshold: float = 70.0
    review_threshold: float = 45.0
    quantity_z_threshold: float = 2.0


def _safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return (numerator / denominator * 100).replace([np.inf, -np.inf], np.nan).fillna(0)


def _money(value: float, symbol: str, code: str) -> str:
    try:
        return f"{symbol}{float(value):,.2f} {code}"
    except Exception:
        return f"{symbol}0.00 {code}"


def _normalise_transaction_money(tx: pd.DataFrame, market_config: CountryMarketConfig) -> pd.DataFrame:
    """Create BDT and local-currency columns from flexible input schemas.

    Supported transaction columns:
    - unit_price_bdt + invoice_total_bdt: already in BDT
    - unit_price_local + invoice_total_local: selected country currency
    - unit_price + invoice_total: selected country currency
    """
    tx = tx.copy()
    fx = max(float(market_config.bdt_per_currency), 0.000001)

    if "unit_price_bdt" in tx.columns:
        tx["unit_price_bdt"] = pd.to_numeric(tx["unit_price_bdt"], errors="coerce").fillna(0)
    elif "unit_price_local" in tx.columns:
        tx["unit_price_bdt"] = pd.to_numeric(tx["unit_price_local"], errors="coerce").fillna(0) * fx
    elif "unit_price" in tx.columns:
        tx["unit_price_bdt"] = pd.to_numeric(tx["unit_price"], errors="coerce").fillna(0) * fx
    else:
        tx["unit_price_bdt"] = 0

    if "invoice_total_bdt" in tx.columns:
        tx["invoice_total_bdt"] = pd.to_numeric(tx["invoice_total_bdt"], errors="coerce").fillna(0)
    elif "invoice_total_local" in tx.columns:
        tx["invoice_total_bdt"] = pd.to_numeric(tx["invoice_total_local"], errors="coerce").fillna(0) * fx
    elif "invoice_total" in tx.columns:
        tx["invoice_total_bdt"] = pd.to_numeric(tx["invoice_total"], errors="coerce").fillna(0) * fx
    else:
        tx["invoice_total_bdt"] = tx["unit_price_bdt"] * pd.to_numeric(tx.get("quantity", 0), errors="coerce").fillna(0)

    tx["unit_price_local"] = tx["unit_price_bdt"] / fx
    tx["invoice_total_local"] = tx["invoice_total_bdt"] / fx
    return tx


def audit_transactions(
    transactions: pd.DataFrame,
    market_benchmarks: pd.DataFrame,
    config: AuditConfig | None = None,
    market_config: CountryMarketConfig | None = None,
) -> pd.DataFrame:
    """Audit transactions against country-adjusted market benchmarks.

    Required transaction columns:
    transaction_id, submitted_date, builder_name, builder_email, department, vendor,
    item_name, quantity, document_status, plus one of:
    - unit_price_bdt/invoice_total_bdt, or
    - unit_price_local/invoice_total_local, or
    - unit_price/invoice_total.

    Required benchmark columns:
    item_name, global_market_price_bdt, local_market_price_bdt,
    tax_transport_margin_pct, allowed_deviation_pct.
    """
    cfg = config or AuditConfig()
    market = market_config or get_country_market("Bangladesh")
    tx = _normalise_transaction_money(transactions.copy(), market)
    bm = market_benchmarks.copy()
    fx = max(float(market.bdt_per_currency), 0.000001)

    tx["submitted_date"] = pd.to_datetime(tx["submitted_date"], errors="coerce")
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").fillna(0)
    tx["document_status"] = tx.get("document_status", "missing").astype(str)

    for col in ["global_market_price_bdt", "local_market_price_bdt", "tax_transport_margin_pct", "allowed_deviation_pct"]:
        if col in bm.columns:
            bm[col] = pd.to_numeric(bm[col], errors="coerce")

    bm["tax_transport_margin_pct"] = bm["tax_transport_margin_pct"].fillna(0)
    bm["allowed_deviation_pct"] = bm["allowed_deviation_pct"].fillna(15)

    # Country-aware expected price. For Bangladesh, multiplier=1 and additional cost=0.
    # For other countries, benchmark is adjusted by a local market multiplier and extra landed cost.
    bm["country_adjusted_base_bdt"] = bm["local_market_price_bdt"] * float(market.local_market_multiplier)
    bm["expected_unit_price_bdt"] = bm["country_adjusted_base_bdt"] * (
        1 + (bm["tax_transport_margin_pct"] + float(market.additional_landed_cost_pct)) / 100
    )

    audited = tx.merge(
        bm[
            [
                "item_name",
                "global_market_price_bdt",
                "local_market_price_bdt",
                "country_adjusted_base_bdt",
                "tax_transport_margin_pct",
                "allowed_deviation_pct",
                "expected_unit_price_bdt",
                "benchmark_source",
            ]
        ],
        on="item_name",
        how="left",
    )

    audited["benchmark_missing"] = audited["expected_unit_price_bdt"].isna()
    audited["expected_unit_price_bdt"] = audited["expected_unit_price_bdt"].fillna(
        audited.groupby("item_name")["unit_price_bdt"].transform("median")
    )
    audited["expected_unit_price_bdt"] = audited["expected_unit_price_bdt"].fillna(audited["unit_price_bdt"].median())
    audited["allowed_deviation_pct"] = audited["allowed_deviation_pct"].fillna(15)

    audited["expected_unit_price_local"] = audited["expected_unit_price_bdt"] / fx
    audited["global_market_price_local"] = audited["global_market_price_bdt"] / fx
    audited["local_market_price_local"] = audited["local_market_price_bdt"] / fx

    audited["price_deviation_pct"] = _safe_pct(
        audited["unit_price_bdt"] - audited["expected_unit_price_bdt"],
        audited["expected_unit_price_bdt"],
    )
    audited["estimated_overbilling_bdt"] = np.where(
        audited["price_deviation_pct"] > audited["allowed_deviation_pct"],
        (audited["unit_price_bdt"] - audited["expected_unit_price_bdt"]) * audited["quantity"],
        0,
    )
    audited["estimated_overbilling_bdt"] = audited["estimated_overbilling_bdt"].clip(lower=0)
    audited["estimated_overbilling_local"] = audited["estimated_overbilling_bdt"] / fx

    duplicate_cols = ["vendor", "item_name", "quantity", "invoice_total_bdt"]
    audited = audited.sort_values("submitted_date")
    audited["duplicate_possible"] = False
    for _, group in audited.groupby(duplicate_cols, dropna=False):
        if len(group) <= 1:
            continue
        dates = group["submitted_date"].tolist()
        indexes = group.index.tolist()
        for i in range(len(indexes)):
            for j in range(i + 1, len(indexes)):
                if pd.notna(dates[i]) and pd.notna(dates[j]):
                    if abs((dates[j] - dates[i]).days) <= cfg.duplicate_window_days:
                        audited.loc[[indexes[i], indexes[j]], "duplicate_possible"] = True

    audited["quantity_zscore"] = 0.0
    for _, group in audited.groupby("item_name"):
        std = group["quantity"].std(ddof=0)
        mean = group["quantity"].mean()
        if std and not np.isnan(std):
            audited.loc[group.index, "quantity_zscore"] = (group["quantity"] - mean) / std
    audited["quantity_outlier"] = audited["quantity_zscore"].abs() >= cfg.quantity_z_threshold

    audited["missing_document"] = audited["document_status"].str.lower().fillna("").ne("complete")
    audited["invoice_mismatch"] = (
        (audited["unit_price_bdt"] * audited["quantity"] - audited["invoice_total_bdt"]).abs()
        > np.maximum(5.0, audited["invoice_total_bdt"] * 0.01)
    )

    price_risk = (
        (audited["price_deviation_pct"].clip(lower=0) / audited["allowed_deviation_pct"].replace(0, 15)) * 60
    ).clip(upper=60)
    duplicate_risk = audited["duplicate_possible"].astype(int) * 20
    doc_risk = audited["missing_document"].astype(int) * 12
    qty_risk = audited["quantity_outlier"].astype(int) * 12
    mismatch_risk = audited["invoice_mismatch"].astype(int) * 12
    benchmark_risk = audited["benchmark_missing"].astype(int) * 5

    audited["audit_risk_score"] = (
        price_risk + duplicate_risk + doc_risk + qty_risk + mismatch_risk + benchmark_risk
    ).clip(upper=100).round(1)

    audited["audit_level"] = np.select(
        [
            audited["audit_risk_score"] >= cfg.high_risk_threshold,
            audited["audit_risk_score"] >= cfg.review_threshold,
        ],
        ["High Risk", "Needs Review"],
        default="Pass",
    )

    audited["selected_country"] = market.country_name
    audited["currency_code"] = market.currency_code
    audited["currency_symbol"] = market.currency_symbol
    audited["suggested_action"] = audited.apply(_suggested_action, axis=1)
    audited["query_message"] = audited.apply(generate_query_message, axis=1)

    output_cols = [
        "transaction_id",
        "submitted_date",
        "builder_name",
        "builder_email",
        "department",
        "vendor",
        "item_name",
        "selected_country",
        "currency_code",
        "quantity",
        "unit_price_local",
        "invoice_total_local",
        "expected_unit_price_local",
        "unit_price_bdt",
        "invoice_total_bdt",
        "expected_unit_price_bdt",
        "price_deviation_pct",
        "estimated_overbilling_local",
        "estimated_overbilling_bdt",
        "duplicate_possible",
        "quantity_outlier",
        "missing_document",
        "invoice_mismatch",
        "benchmark_missing",
        "audit_risk_score",
        "audit_level",
        "suggested_action",
        "query_message",
    ]
    existing_cols = [col for col in output_cols if col in audited.columns]
    return audited[existing_cols].sort_values(["audit_risk_score", "price_deviation_pct"], ascending=False)


def _suggested_action(row: pd.Series) -> str:
    reasons: List[str] = []
    if row.get("price_deviation_pct", 0) > row.get("allowed_deviation_pct", 15):
        reasons.append("collect updated market quotations")
    if row.get("duplicate_possible", False):
        reasons.append("verify possible duplicate invoice")
    if row.get("missing_document", False):
        reasons.append("attach missing supporting documents")
    if row.get("quantity_outlier", False):
        reasons.append("justify unusual quantity")
    if row.get("invoice_mismatch", False):
        reasons.append("correct invoice total mismatch")
    if row.get("benchmark_missing", False):
        reasons.append("add verified benchmark source")
    return "; ".join(reasons) if reasons else "no action required"


def generate_query_message(row: pd.Series) -> str:
    if row.get("audit_level") == "Pass":
        return ""

    reasons: List[str] = []
    deviation = float(row.get("price_deviation_pct", 0))
    symbol = row.get("currency_symbol", "")
    code = row.get("currency_code", "")
    country = row.get("selected_country", "selected market")
    submitted = _money(row.get("unit_price_local", 0), symbol, code)
    expected = _money(row.get("expected_unit_price_local", 0), symbol, code)

    if deviation > float(row.get("allowed_deviation_pct", 15)):
        reasons.append(
            f"submitted unit price {submitted} is {deviation:.1f}% above the {country} expected benchmark {expected}"
        )
    if bool(row.get("duplicate_possible", False)):
        reasons.append("a possible duplicate transaction was detected")
    if bool(row.get("missing_document", False)):
        reasons.append("supporting documents are incomplete")
    if bool(row.get("quantity_outlier", False)):
        reasons.append("quantity is unusual compared with similar transactions")
    if bool(row.get("invoice_mismatch", False)):
        reasons.append("invoice total does not match quantity × unit price")
    if bool(row.get("benchmark_missing", False)):
        reasons.append("no verified benchmark source is available for this item")

    reason_text = "; ".join(reasons) if reasons else "the transaction requires manual review"
    return (
        f"Dear {row.get('builder_name', 'Transaction Builder')},\n\n"
        f"Transaction {row.get('transaction_id')} for {row.get('item_name')} has been flagged as "
        f"{row.get('audit_level')} with an audit risk score of {row.get('audit_risk_score')}/100. "
        f"Reason: {reason_text}.\n\n"
        "Please perform a proper market survey and submit at least 2-3 vendor quotations, "
        "price justification, and corrected supporting documents before approval.\n\n"
        "Regards,\nAutomated Audit Dashboard"
    )


def audit_summary(audited: pd.DataFrame) -> Dict[str, float]:
    return {
        "total_transactions": int(len(audited)),
        "flagged_transactions": int((audited["audit_level"] != "Pass").sum()) if len(audited) else 0,
        "high_risk_transactions": int((audited["audit_level"] == "High Risk").sum()) if len(audited) else 0,
        "estimated_overbilling_bdt": float(audited["estimated_overbilling_bdt"].sum()) if len(audited) else 0.0,
        "estimated_overbilling_local": float(audited["estimated_overbilling_local"].sum()) if len(audited) and "estimated_overbilling_local" in audited else 0.0,
        "average_risk_score": float(audited["audit_risk_score"].mean()) if len(audited) else 0.0,
    }
