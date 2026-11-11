"""The data-quality assessment, as measurements rather than adjectives.

Each function returns a frame the analysis prints and writes to
findings/results/. The conclusions they support are in findings/FINDINGS.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .load import to_number


def duplicate_report(products_raw: pd.DataFrame) -> pd.DataFrame:
    """Are the duplicate SKUs repetition, or conflicting records?"""
    dup = products_raw[products_raw["sku"].duplicated(keep=False)]
    per_sku = dup.groupby("sku").nunique()
    cols = [c for c in per_sku.columns if c != "sku"]
    return pd.DataFrame({
        "metric": ["rows", "exact duplicate rows", "skus appearing more than once",
                   "such skus whose rows disagree on any column"],
        "value": [len(products_raw), int(products_raw.duplicated().sum()),
                  int(dup["sku"].nunique()),
                  int((per_sku[cols] > 1).any(axis=1).sum())],
    })


def promo_price_verdict(products_raw: pd.DataFrame,
                        lines: pd.DataFrame) -> pd.DataFrame:
    """Can `promo_price` be repaired? Measured against what customers paid.

    `promo_price` looks like a discounted price with its decimal point one place
    too far right — 83 % of rows exceed the list price. Dividing by ten fixes
    most of them. The question is whether *which* rows need it can be told from
    the data, and the answer is no.
    """
    promo = to_number(products_raw["promo_price"])
    paid = lines.groupby("sku")["unit_price_eur"].median().rename("paid")
    m = (pd.DataFrame({"sku": products_raw["sku"], "promo": promo})
         .drop_duplicates("sku").set_index("sku").join(paid, how="inner"))
    m = m[(m["paid"] > 0) & m["promo"].notna()]

    err_as_is = (m["promo"] / m["paid"] - 1).abs()
    err_div10 = (m["promo"] / 10 / m["paid"] - 1).abs()
    oracle = np.minimum(err_as_is, err_div10)

    return pd.DataFrame({
        "metric": ["skus with sales and a promo_price",
                   "closer when taken as-is", "closer when divided by ten",
                   "median error of the better rule, picked per row with hindsight (%)",
                   "share the better rule gets within 5 % of the price paid (%)"],
        "value": [len(m), int((err_as_is < err_div10).sum()),
                  int((err_div10 <= err_as_is).sum()),
                  round(float(oracle.median() * 100), 1),
                  round(float((oracle < 0.05).mean() * 100), 1)],
    })


def completion_by_month(orders: pd.DataFrame) -> pd.DataFrame:
    """Share of orders reaching `Completed`, by month.

    One month breaks the pattern badly enough to invalidate any revenue figure
    computed from it.
    """
    t = (orders.set_index("created_date")
         .groupby([pd.Grouper(freq="ME"), "state"]).size().unstack(fill_value=0))
    t["total"] = t.sum(axis=1)
    t["completed_pct"] = (100 * t["Completed"] / t["total"]).round(1)
    return t.reset_index()


def price_parse_coverage(products_raw: pd.DataFrame,
                         lines: pd.DataFrame) -> pd.DataFrame:
    """How the `price` column is formatted, and whether the odd ones sold.

    The six most expensive rows have never been sold, which invites the
    conclusion that the corrupted prices are all dead stock. They are not:
    across the whole two-dot group, 205 of 377 products have real sales. They
    cannot be waved away as unsold, and they cannot be parsed either — see
    `load.to_number`. They are excluded, and this is the size of that exclusion.
    """
    products_raw = products_raw.drop_duplicates()
    sold = set(lines["sku"])
    dots = products_raw["price"].astype("string").str.count(r"\.")
    rows = []
    for n, label in [(0, "no dot (e.g. '59')"), (1, "one dot (e.g. '59.99')"),
                     (2, "two dots (e.g. '1.639.792')")]:
        sub = products_raw[dots == n]
        rows.append({"price_format": label, "skus": len(sub),
                     "ever_sold": int(sub["sku"].isin(sold).sum()),
                     "ever_sold_pct": round(100 * float(sub["sku"].isin(sold).mean()), 1)})
    missing = products_raw[products_raw["price"].isna()]
    rows.append({"price_format": "missing", "skus": len(missing),
                 "ever_sold": int(missing["sku"].isin(sold).sum()),
                 "ever_sold_pct": round(100 * float(missing["sku"].isin(sold).mean()), 1)})
    return pd.DataFrame(rows)
