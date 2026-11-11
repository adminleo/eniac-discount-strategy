"""The parsing decisions, pinned.

These are not syntax checks. Each one fails if a future change quietly reverts
a decision that was settled by measurement against the transaction data.
"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eniac import load  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class TestNumberParsing(unittest.TestCase):
    def test_one_dot_is_a_decimal_point(self):
        s = pd.Series(["18.99", "399.00", "68.39"])
        self.assertEqual(list(load.to_number(s)), [18.99, 399.00, 68.39])

    def test_two_dots_means_the_first_is_a_thousands_separator(self):
        s = pd.Series(["1.137.99", "2.565.99"])
        self.assertEqual(list(load.to_number(s)), [1137.99, 2565.99])

    def test_a_plain_integer_survives(self):
        self.assertEqual(list(load.to_number(pd.Series(["59"]))), [59.0])

    def test_naive_parsing_would_silently_lose_the_two_dot_rows(self):
        # The reason _strip_thousands exists: pd.to_numeric does not raise on
        # these, it returns NaN, so 12.3 % of orderlines would vanish quietly.
        s = pd.Series(["1.137.99"])
        self.assertTrue(pd.to_numeric(s, errors="coerce").isna().all())
        self.assertFalse(load.to_number(s).isna().any())

    def test_shifted_prices_are_dropped_not_guessed(self):
        # Blanket division fits the median and breaks individual rows; the
        # digit count does not say which divisor a row needs. So these become
        # NA rather than a plausible-looking wrong number.
        s = pd.Series(["59.99", "1.639.792"])
        kept = load.to_number(s, drop_shifted=False)
        dropped = load.to_number(s, drop_shifted=True)
        self.assertAlmostEqual(kept.iloc[1], 1639.792, places=3)
        self.assertEqual(dropped.iloc[0], 59.99)
        self.assertTrue(pd.isna(dropped.iloc[1]))


@unittest.skipUnless(os.path.isdir(DATA), "course dataset not present")
class TestAgainstTheRealFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(os.path.join(DATA, "products.csv"))
        cls.t = load.load(DATA)

    def test_duplicate_products_are_pure_repetition(self):
        """If a duplicate SKU ever disagrees with its twin, dropping them
        silently picks a winner and this test is the warning."""
        dup = self.raw[self.raw["sku"].duplicated(keep=False)]
        per_sku = dup.groupby("sku").nunique()
        cols = [c for c in per_sku.columns if c != "sku"]
        self.assertEqual(int((per_sku[cols] > 1).any(axis=1).sum()), 0)

    def test_deduplication_keeps_every_distinct_sku(self):
        self.assertEqual(self.t["products"]["sku"].nunique(),
                         self.raw["sku"].nunique())

    def test_no_order_line_price_is_lost_to_parsing(self):
        lines = self.t["orderlines"]
        self.assertEqual(int(lines["unit_price_eur"].isna().sum()), 0)

    def test_prices_stay_in_a_believable_range(self):
        """The guard that would have caught the EUR 352,559 MacBook."""
        price = self.t["products"]["price_eur"].dropna()
        self.assertGreater(price.min(), 0)
        self.assertLess(price.max(), 20_000)

    def test_most_products_still_have_a_price(self):
        p = self.t["products"]
        self.assertGreater(p["price_eur"].notna().mean(), 0.95)


if __name__ == "__main__":
    unittest.main(verbosity=2)
