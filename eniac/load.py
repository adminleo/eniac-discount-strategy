"""Read the four CSVs and turn their text-formatted numbers into numbers.

Every decision in here was settled by measurement against the transactions in
`orderlines`, not by inspection. `tools/evidence.py` reproduces the checks and
`tests/test_load.py` pins the outcomes.
"""
from __future__ import annotations

import pandas as pd

TABLES = ("orders", "orderlines", "products", "brands")


def _strip_thousands(s: pd.Series) -> pd.Series:
    """Remove a thousands separator, where the value has one.

    These columns arrive as text with a dot for both roles: `18.99` is a
    decimal, `1.137.99` is one thousand one hundred thirty-seven and ninety-nine
    cents. A value with two dots has a thousands separator first; a value with
    one dot or none does not. 36,169 of the 293,983 rows in `orderlines`
    (12.3 %) carry two dots, so this is not an edge case — and pd.to_numeric on
    the raw column turns all of them into NaN without complaining.
    """
    s = s.astype("string").str.strip()
    two_dots = s.str.count(r"\.") == 2
    return s.where(~two_dots, s.str.replace(".", "", n=1, regex=False))


def to_number(s: pd.Series, drop_shifted: bool = False) -> pd.Series:
    """Parse a money column.

    With `drop_shifted`, values that carried a thousands separator are returned
    as NA instead of a number, because in `products.price` those same values
    also have their decimal point shifted an unknown number of places.

    That is measured, not assumed. 377 of the 10,580 products have a two-dot
    price and 205 of them have real sales, so the group cannot be dismissed as
    dead stock. Comparing each one to the median price actually paid and asking
    which power of ten gets closest:

        divide by 10   -> 157 products
        divide by 100  ->  44 products
        divide by 1000 ->   4 products

    A single blanket divisor is therefore wrong for a fifth of the group. The
    obvious tie-break, the length of the string, does not separate them either:
    among seven-digit values 92 want 10, 36 want 100 and one wants 1000; among
    eight-digit values, 65, 7 and 3. Nothing in the row says which.

    Dividing all of them by ten reproduces the *median* ratio of the undamaged
    rows almost exactly (1.184, against 1.113 for prices with no dot and 1.209
    for prices with one), which is precisely what makes the mistake tempting:
    the aggregate looks right while individual products are off by a factor of
    ten. It put a MacBook Pro 15" in the catalogue at EUR 35,255.
    """
    raw = s.astype("string").str.strip()
    had_separator = raw.str.count(r"\.") == 2
    out = pd.to_numeric(_strip_thousands(raw), errors="coerce")
    if drop_shifted:
        out = out.where(~had_separator)
    return out


def load(data_dir: str) -> dict[str, pd.DataFrame]:
    """Read the four files, parse dates and money, drop exact duplicates."""
    import os

    frames = {t: pd.read_csv(os.path.join(data_dir, f"{t}.csv")) for t in TABLES}

    orders = frames["orders"]
    orders["created_date"] = pd.to_datetime(orders["created_date"])

    lines = frames["orderlines"]
    lines["date"] = pd.to_datetime(lines["date"])
    lines["unit_price_eur"] = to_number(lines["unit_price"])
    lines["line_revenue_eur"] = lines["unit_price_eur"] * lines["product_quantity"]

    products = frames["products"]
    # 8,746 of the 19,326 rows are exact duplicates: 757 SKUs appear more than
    # once and not one of them disagrees with its twin on any column. So this is
    # pure repetition rather than conflicting records, and dropping it needs no
    # tie-break rule. Worth checking rather than assuming — duplicate keys that
    # *do* conflict are the normal case and require a decision.
    products = products.drop_duplicates().reset_index(drop=True)
    products["price_eur"] = to_number(products["price"], drop_shifted=True)
    products["brand_code"] = products["sku"].str[:3]

    brands = frames["brands"]
    products = products.merge(
        brands.rename(columns={"short": "brand_code", "long": "brand"}),
        on="brand_code", how="left",
    )

    return {"orders": orders, "orderlines": lines,
            "products": products, "brands": brands}
