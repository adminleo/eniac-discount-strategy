"""Discounts, computed from list price against the price actually paid.

`promo_price` is not used — see `quality.promo_price_verdict`. The list price in
`products.price` and the transaction price in `orderlines.unit_price` are both
independently verifiable, and their ratio is the discount that was really given
rather than the one the catalogue claims.
"""
from __future__ import annotations

import pandas as pd


def per_sku(products: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """One row per product that has both a list price and real sales."""
    paid = (lines.groupby("sku")
            .agg(lines_sold=("id", "size"),
                 units=("product_quantity", "sum"),
                 median_paid_eur=("unit_price_eur", "median"))
            .reset_index())
    m = products.merge(paid, on="sku", how="inner")
    m = m[(m["price_eur"] > 0) & (m["median_paid_eur"] > 0)].copy()
    m["discount_pct"] = (1 - m["median_paid_eur"] / m["price_eur"]) * 100
    return m


def summary(d: pd.DataFrame) -> pd.DataFrame:
    """How many products are discounted, and by how much."""
    discounted = d["discount_pct"] > 0.5
    above_list = d["discount_pct"] < -0.5
    q = d.loc[discounted, "discount_pct"].quantile([0.25, 0.5, 0.75, 0.95])
    return pd.DataFrame({
        "metric": ["products with a list price and real sales",
                   "ever sold below list price", "ever sold below list price (%)",
                   "sold above list price (a separate data problem)",
                   "median discount among discounted products (%)",
                   "25th percentile (%)", "75th percentile (%)", "95th percentile (%)"],
        "value": [len(d), int(discounted.sum()),
                  round(100 * float(discounted.mean()), 1), int(above_list.sum()),
                  round(float(q[0.5]), 1), round(float(q[0.25]), 1),
                  round(float(q[0.75]), 1), round(float(q[0.95]), 1)],
    })


def by_brand(d: pd.DataFrame, min_skus: int = 25) -> pd.DataFrame:
    """Discount depth and price level per brand."""
    g = (d.assign(brand=d["brand"].fillna("(unmatched prefix)"))
         .groupby("brand")
         .agg(skus=("sku", "size"),
              median_price_eur=("price_eur", "median"),
              median_discount_pct=("discount_pct", "median"),
              units=("units", "sum"))
         .reset_index())
    return (g[g["skus"] >= min_skus]
            .sort_values("median_discount_pct", ascending=False)
            .round(2).reset_index(drop=True))
