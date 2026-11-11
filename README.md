# Eniac's discount strategy — what the data can and cannot tell you

Eniac is a European online retailer of Apple products and compatible
accessories. The board wants to know how deep its discounts go, how they
interact with the calendar, and how products should be grouped for reporting.

The dataset they handed over is corrupted, and the interesting part of this
project is which corruptions can be repaired and which cannot. Three columns
look repairable and are not. Deciding that honestly changes several headline
numbers — in one case by a factor of ten.

## What the board asked, and the answers

| Question | Answer |
|---|---|
| How many products are discounted? | **90.3 %** of products with a list price and real sales (6,878 of 7,620) were sold below list at least some of the time. |
| How big are the discounts? | Median **16.9 %**. Half fall between **9.2 %** and **27.8 %**; the top 5 % exceed **56.8 %**. |
| How do seasonality and special dates affect sales? | The data covers one Black Friday and one Christmas, so this cannot be answered as *seasonality* — see below. What can be measured: **Black Friday 2017 took €723,120 in a day, 18.2× a typical November day and 24.7 % of the whole month.** The five highest-revenue days in fifteen months are all Black Friday week. |
| How should products be classified? | Not by `type`, which is an internal identifier: 126 values, 91.5 % purely numeric. By **brand**, read from the first three characters of the SKU — that resolves against `brands.csv` for **98.0 %** of products. |
| How are prices distributed across categories? | Strongly skewed and brand-determined. Median list price **€769** for Apple against **€29.99** for Griffin; bundles ("Pack") sit highest at **€1,141**. |
| How could data collection be improved? | Four specific defects, each with a measurement, in [findings/FINDINGS.md](findings/FINDINGS.md). |

## The part worth reading: three traps

**`promo_price` cannot be used, and that is provable.** It looks like a
discounted price whose decimal point sits one place too far right — 83 % of
rows exceed the list price. Dividing by ten fixes most of them: of 7,848
products with sales, 6,784 land closer after ÷10 and 1,064 are already correct.
Nothing in the row says which group it belongs to. And even picking the better
rule for each row *with hindsight*, by comparing against the price customers
actually paid, the median error is 1.1 % and only **69.4 %** land within 5 %.
A column that cannot reach the right answer even when told the answer is not a
column you report discounts from. Discounts here come from list price against
transaction price instead, both independently verifiable.

**A blanket divisor fixes the average and breaks the rows.** 377 products have a
price like `1.639.792`. Stripping the thousands separator and dividing by ten
reproduces the undamaged rows' ratio to the price paid almost exactly — 1.184,
against 1.113 and 1.209 for the clean groups. It is the kind of agreement that
ends an investigation. But per product the needed divisor is 10 for 157 of them,
100 for 44, and 1000 for 4, and the length of the string does not separate them:
among seven-digit values 92 want 10, 36 want 100 and one wants 1000. The
aggregate was right while individual products were out by a factor of ten — it
had listed a MacBook Pro 15" at **€35,255**. These 377 prices are excluded, and
the most expensive product in the cleaned catalogue is now an Apple iMac Pro
27-inch 18-core at **€15,339**, which is what that machine cost in 2017.

**March 2017 did not crash, it lost its paperwork.** Revenue for the month comes
out at €117,009 against €607,088 in February — an 81 % collapse, and a tempting
story. But the month's *order* count is ordinary (10,726, between February's
12,182 and April's 9,943). What is missing is completion: **1.9 % of March
orders reach `Completed`, against a 20.9 % median across every other month.**
Demand was normal; the status field was not written. The month is excluded from
the revenue series rather than explained.

## On the seasonality question

The orders run from 2017-01-01 to 2018-03-14. Fourteen and a half months holds
one Black Friday, one Christmas and one January. A season is a pattern that
repeats, and nothing here repeats, so the honest output is a description of one
cycle and an explicit refusal to extrapolate. The Black Friday effect is large
enough to be worth acting on regardless; the "summer dip" that the monthly chart
appears to show rests on a single summer and should not be planned against.

## Running it

```bash
python3 analysis/run_all.py          # writes every table to findings/results/
python3 -m unittest discover -s tests -v
```

The dataset is bootcamp-provided and is not in this repository. Place
`orders.csv`, `orderlines.csv`, `products.csv` and `brands.csv` in `data/`, or
pass a directory: `python3 analysis/run_all.py /path/to/data`.

```
eniac/      load.py (parsing decisions), quality.py, discounts.py,
            seasonality.py, categories.py
analysis/   run_all.py — every table, written to findings/results/ as CSV
tests/      the decisions pinned, so a future change cannot quietly revert one
findings/   FINDINGS.md and the CSV output of every query
```

Only pandas and numpy are required. Every number in this README is produced by
`analysis/run_all.py` and written to `findings/results/`.
