"""Run every analysis and write the results to findings/results/.

    python3 analysis/run_all.py [data_dir]

Each table printed here is also written as a CSV, so every number quoted in the
README and in findings/FINDINGS.md can be traced to the file that produced it.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eniac import categories, discounts, load, quality, seasonality  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "findings", "results")
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data")


def emit(name: str, df: pd.DataFrame, head: int | None = 12) -> None:
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
    print(f"\n### {name}  ({len(df)} rows)")
    print(df.head(head).to_string(index=False) if head else df.to_string(index=False))


def main() -> int:
    raw_products = pd.read_csv(os.path.join(DATA, "products.csv"))
    t = load.load(DATA)
    orders, lines, products, brands = (t["orders"], t["orderlines"],
                                       t["products"], t["brands"])
    print(f"orders {len(orders):,} | orderlines {len(lines):,} | "
          f"products {len(products):,} (from {len(raw_products):,}) | brands {len(brands):,}")

    print("\n" + "=" * 70 + "\nDATA QUALITY\n" + "=" * 70)
    emit("quality_duplicates", quality.duplicate_report(raw_products))
    emit("quality_price_formats", quality.price_parse_coverage(raw_products, lines))
    emit("quality_promo_price_verdict", quality.promo_price_verdict(raw_products, lines))
    comp = quality.completion_by_month(orders)
    emit("quality_completion_by_month",
         comp[["created_date", "Completed", "total", "completed_pct"]], head=20)

    print("\n" + "=" * 70 + "\nQ1/Q2  DISCOUNTS\n" + "=" * 70)
    d = discounts.per_sku(products, lines)
    emit("discount_summary", discounts.summary(d), head=None)
    emit("discount_by_brand", discounts.by_brand(d), head=15)

    print("\n" + "=" * 70 + "\nQ3  SEASONALITY AND SPECIAL DATES\n" + "=" * 70)
    lc = seasonality.completed_lines(orders, lines)
    emit("revenue_by_month", seasonality.revenue_by_month(lc, drop_broken=False), head=20)
    emit("revenue_top_days", seasonality.top_days(lc))
    emit("black_friday_lift", seasonality.black_friday_lift(lc), head=None)

    print("\n" + "=" * 70 + "\nQ4/Q5  CATEGORIES AND PRICES\n" + "=" * 70)
    emit("category_type_verdict", categories.type_column_verdict(products), head=None)
    emit("category_brand_coverage", categories.brand_coverage(products, brands), head=None)
    emit("price_distribution_by_brand",
         categories.price_distribution_by_brand(products), head=15)

    print(f"\nWrote {len(os.listdir(OUT))} files to findings/results/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
