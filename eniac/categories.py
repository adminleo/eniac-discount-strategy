"""Classifying products, and why it is not the column named `type`.

The brief asks how products should be grouped to simplify reporting. The
obvious candidate fails and a less obvious one works.
"""
from __future__ import annotations

import pandas as pd


def type_column_verdict(products: pd.DataFrame) -> pd.DataFrame:
    """`products.type` is an identifier wearing the name of a category."""
    t = products["type"].astype("string")
    numeric_share = pd.to_numeric(t, errors="coerce").notna().mean()
    return pd.DataFrame({
        "metric": ["distinct values", "missing", "values that are purely numeric (%)",
                   "most common value", "its share of all products (%)"],
        "value": [int(t.nunique()), int(t.isna().sum()),
                  round(100 * float(numeric_share), 1),
                  str(t.value_counts().index[0]),
                  round(100 * float(t.value_counts().iloc[0] / len(t)), 1)],
    })


def brand_coverage(products: pd.DataFrame, brands: pd.DataFrame) -> pd.DataFrame:
    """The first three characters of a SKU are a brand code."""
    known = products["brand_code"].isin(set(brands["short"]))
    return pd.DataFrame({
        "metric": ["products", "whose three-letter prefix is a known brand",
                   "coverage (%)", "distinct brands present"],
        "value": [len(products), int(known.sum()),
                  round(100 * float(known.mean()), 1),
                  int(products.loc[known, "brand_code"].nunique())],
    })


def price_distribution_by_brand(products: pd.DataFrame,
                               min_skus: int = 40) -> pd.DataFrame:
    d = products[products["price_eur"].notna()].copy()
    d["brand"] = d["brand"].fillna("(unmatched prefix)")
    g = (d.groupby("brand")["price_eur"]
         .agg(skus="size", p25=lambda s: s.quantile(0.25), median="median",
              p75=lambda s: s.quantile(0.75), max="max")
         .reset_index())
    return (g[g["skus"] >= min_skus].sort_values("median", ascending=False)
            .round(2).reset_index(drop=True))
