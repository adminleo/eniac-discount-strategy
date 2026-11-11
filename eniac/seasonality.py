"""Revenue over time, and what the single Black Friday in the data does to it.

The dataset runs 2017-01-01 to 2018-03-14: fourteen and a half months. That
contains exactly one Black Friday and one Christmas, which is enough to measure
what happened and not enough to call anything seasonal. A season is a pattern
that repeats; one occurrence is an event. The functions below therefore describe
the cycle rather than fitting one.
"""
from __future__ import annotations

import pandas as pd

# March 2017 completed only 1.9 % of its orders against a 20.9 % median across
# every other month, while its total order count is ordinary. The demand is
# there and the completion status is missing, so revenue for that month is not
# low — it is absent. Any revenue series that includes it reads as a crash.
BROKEN_REVENUE_MONTHS = ("2017-03",)


def completed_lines(orders: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Order lines belonging to orders that were actually completed and paid."""
    completed = set(orders.loc[orders["state"] == "Completed", "order_id"])
    return lines[lines["id_order"].isin(completed)].copy()


def revenue_by_month(lines_completed: pd.DataFrame,
                     drop_broken: bool = True) -> pd.DataFrame:
    s = (lines_completed.set_index("date")["line_revenue_eur"]
         .resample("ME").sum().rename("revenue_eur").reset_index())
    s["month"] = s["date"].dt.strftime("%Y-%m")
    s["excluded"] = s["month"].isin(BROKEN_REVENUE_MONTHS)
    # The final month stops mid-March, so it is partial for a different reason.
    s.loc[s["month"] == "2018-03", "excluded"] = True
    if drop_broken:
        s = s[~s["excluded"]]
    return s[["month", "revenue_eur", "excluded"]].round(2).reset_index(drop=True)


def top_days(lines_completed: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    d = lines_completed.set_index("date")["line_revenue_eur"].resample("D").sum()
    out = d.sort_values(ascending=False).head(n).rename("revenue_eur").reset_index()
    out["day"] = out["date"].dt.strftime("%Y-%m-%d (%a)")
    return out[["day", "revenue_eur"]].round(2)


def black_friday_lift(lines_completed: pd.DataFrame,
                      day: str = "2017-11-24") -> pd.DataFrame:
    """That one day against a typical day in its own month."""
    d = lines_completed.set_index("date")["line_revenue_eur"].resample("D").sum()
    ts = pd.Timestamp(day)
    month = d[d.index.strftime("%Y-%m") == ts.strftime("%Y-%m")]
    return pd.DataFrame({
        "metric": [f"revenue on {day}", "median day that month",
                   "times the median day", "share of the whole month (%)"],
        "value": [round(float(d.get(ts, 0)), 2), round(float(month.median()), 2),
                  round(float(d.get(ts, 0) / month.median()), 1),
                  round(100 * float(d.get(ts, 0) / month.sum()), 1)],
    })
