# Findings

Every figure below comes from `analysis/run_all.py` and is written to
`findings/results/` as CSV. File names are given per section.

## 1. Data quality

### 1.1 Duplicate products are repetition, not conflict
`quality_duplicates.csv`

`products.csv` has 19,326 rows and **8,746 of them are exact duplicates**, across
757 SKUs. The usual danger with a duplicated key is that the copies disagree and
dropping them silently picks a winner. Here **zero** of the 757 disagree on any
column, so `drop_duplicates()` needs no tie-break rule and loses nothing. 10,580
distinct products remain. `tests/test_load.py` asserts this, so if a future
extract does contain conflicting twins, the suite says so rather than the
analysis quietly choosing one.

### 1.2 Prices are text, and the dot does two jobs
`quality_price_formats.csv`

Money arrives as strings in which `.` is both a decimal point and a thousands
separator: `18.99` is nineteen euros, `1.137.99` is one thousand one hundred and
thirty-seven. **36,169 of the 293,983 order lines (12.3 %) carry two dots.**
`pd.to_numeric` does not raise on those — it returns `NaN` — so a naive parse
drops an eighth of all transactions without a word. That behaviour is pinned in
`test_naive_parsing_would_silently_lose_the_two_dot_rows`.

### 1.3 377 prices are shifted by an unknowable amount
`quality_price_formats.csv`

The same two-dot format appears in `products.price` for 377 products, but there
the decimal point is also displaced. The six most expensive have never been
sold, which suggests the corrupted prices are simply dead stock — but across the
whole group **206 of 377 have real sales**, so they cannot be waved away.

Comparing each to the median price actually paid and asking which power of ten
gets closest:

| divisor | products |
|---|---:|
| 10 | 157 |
| 100 | 44 |
| 1000 | 4 |

Dividing all of them by ten reproduces the undamaged rows' ratio to the price
paid almost exactly — **1.184**, against 1.113 for prices with no dot and 1.209
for prices with one — which is exactly what makes it dangerous: the aggregate
agrees while a fifth of the individual products are out by a factor of ten or a
hundred. The string length does not separate them either (among seven-digit
values 92 want 10, 36 want 100, one wants 1000).

They are therefore excluded, not guessed. Cost: 377 of 10,580 products, 3.6 %.
Benefit: the catalogue's most expensive item goes from a MacBook Pro 15" at
**€35,255** to an Apple iMac Pro 27-inch 18-core Xeon at **€15,339**, which is
what that machine actually cost in 2017.

### 1.4 `promo_price` is unusable
`quality_promo_price_verdict.csv`

83 % of `promo_price` values are *higher* than the list price, with the decimal
one place too far right. Of 7,848 products with sales, **6,784 are closer after
dividing by ten and 1,064 are already correct**, and no column distinguishes
them. Decimal count nearly works and then does not: among three-decimal values,
6,781 want ÷10 but 473 do not.

The decisive test is to allow hindsight — pick, for each product, whichever
reading lands closer to the price customers actually paid. Even then the
**median error is 1.1 %** and only **69.4 %** land within 5 %. A column that
cannot reach the right answer when handed the answer cannot support a discount
report.

All discounts in this project are therefore computed as list price
(`products.price`) against transaction price (`orderlines.unit_price`), two
independently verifiable fields.

### 1.5 March 2017 lost its completion status
`quality_completion_by_month.csv`

| month | completed | total orders | completed % |
|---|---:|---:|---:|
| 2017-02 | 2,274 | 12,182 | 18.7 |
| **2017-03** | **202** | **10,726** | **1.9** |
| 2017-04 | 1,632 | 9,943 | 16.4 |

Revenue for March 2017 computes to €117,009 against €607,088 in February — an
81 % collapse that reads as a business crisis. The order count says otherwise:
10,726 orders, squarely between its neighbours. Demand was normal and the status
field was not written. Median completion across every other month is **20.9 %**.
The month is excluded from the revenue series.

## 2. Discounts
`discount_summary.csv`, `discount_by_brand.csv`

Of 7,620 products that have both a usable list price and real sales, **6,878
(90.3 %) were sold below list**. Among those, the median discount is **16.9 %**,
the middle half runs **9.2 %–27.8 %**, and the top 5 % exceed **56.8 %**.

**118 products were sold above their list price.** That is not a discount
strategy, it is a fifth data defect, and it is reported rather than clipped.

Discounting is a brand decision, not a blanket policy:

| brand | products | median list price | median discount |
|---|---:|---:|---:|
| NewerTech | 119 | €60.99 | **45.5 %** |
| Griffin | 128 | €29.99 | 35.0 % |
| Otterbox | 112 | €34.99 | 34.0 % |
| … | | | |
| BenQ | 44 | €327.00 | **0.0 %** |
| Repair | 96 | €69.99 | **0.0 %** |
| iFixit | 149 | €26.99 | **0.0 %** |

Cheap accessories carry deep and frequent discounts; several brands are never
discounted at all. Any board-level statement of the form "we discount by X" is
describing a distribution with two modes.

## 3. Seasonality and special dates
`revenue_by_month.csv`, `revenue_top_days.csv`, `black_friday_lift.csv`

The data runs 2017-01-01 to 2018-03-14: **one** Black Friday, **one** Christmas,
**one** summer. Seasonality is a pattern that repeats and nothing here repeats,
so what follows describes a single cycle and does not extrapolate.

**Black Friday, 24 November 2017: €723,120 in one day.** That is **18.2×** the
median November day (€39,814) and **24.7 %** of the entire month. The five
highest-revenue days in fifteen months are 23, 24, 25, 26 and 27 November 2017 —
Black Friday week owns the top of the table outright, ahead of anything in
December.

November 2017 as a whole took €2.92M against a €859k median month. December
(€1.87M) and January 2018 (€1.93M) stay elevated, so the Christmas period is
real but secondary to the single Friday.

The monthly series also appears to show a summer dip. It rests on one summer and
should not be planned against.

## 4. Product categories and price distribution
`category_type_verdict.csv`, `category_brand_coverage.csv`,
`price_distribution_by_brand.csv`

`products.type` is the obvious candidate and the wrong one: **126 distinct
values, 91.5 % of them purely numeric**, 50 missing, and its most common value
covers 10.3 % of the catalogue. It is an internal identifier.

The first three characters of a SKU are a brand code, and they resolve against
`brands.csv` for **98.0 %** of products — 184 distinct brands. That is the
grouping to report on.

| brand | products | 25th pct | median | 75th pct |
|---|---:|---:|---:|---:|
| Pack (bundles) | 1,409 | €618 | **€1,141** | €2,281 |
| Apple | 2,074 | €85 | **€769** | €2,008 |
| QNAP | 119 | €324 | €543 | €1,269 |
| Western Digital | 212 | €125 | €170 | €256 |
| NewerTech | 141 | €29.99 | €60.99 | €95.99 |
| Griffin | 157 | €29.99 | **€29.99** | €44.99 |

Two notes. Apple's inter-quartile range spans €85 to €2,008 — the brand covers
cables and workstations alike, so "Apple" is a useful reporting label and a
useless pricing segment. And two of the largest "brands" are not brands at all:
`Pack` (1,409 bundles) and `Repair` (96 services) are product kinds that happen
to share the prefix convention. A reporting hierarchy should carry both axes.

## 5. How data collection should be improved

1. **Write numbers as numbers.** One locale, one separator, a fixed scale. The
   two-dot format cost 12.3 % of transaction rows to a silent `NaN` and made 377
   product prices unrecoverable.
2. **Fix the decimal shift at the source.** `promo_price` and the 377 prices
   share one defect — a point written one or two places too far right. It is
   trivial upstream and unrecoverable downstream.
3. **Make `promo_price` a discount, not a price**, or drop it. A percentage
   cannot be shifted into nonsense by a formatting bug, and it is what the
   business actually wants to know.
4. **Deduplicate on write.** 45 % of the product file is repetition.
5. **Treat order status as required.** March 2017 shows a month can keep its
   orders and lose its outcome, which looks exactly like a crash in every chart
   drawn from it.
6. **Keep a field for "why".** 118 products sold above list price. Without a
   reason code, that is indistinguishable from another formatting bug.
