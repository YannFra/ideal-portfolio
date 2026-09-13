import unittest

import pandas as pd

from utils.orders import get_list_of_orders


class GetListOfOrdersTests(unittest.TestCase):
    def test_excludes_non_rebalanced_holding_from_capital_and_weights(self):
        assets = pd.DataFrame(
            {
                "yf_name": ["A", "B", "BTC-USD"],
                "position_in_SGD": [60.0, 30.0, 10.0],
                "p_overall": [60.0, 30.0, 10.0],
                "exchange_rate": [1.0, 1.0, 1.0],
                "unit_price": [1.0, 1.0, 1.0],
            }
        )
        portfolio = pd.DataFrame(
            {
                "Product": ["Asset A", "Asset B", "Bitcoin"],
                "yf_name": ["A", "B", "BTC-USD"],
                "p_overall": [50.0, 50.0, 0.0],
                "Rebalance": [True, True, False],
                "exchange_rate": [1.0, 1.0, 1.0],
                "unit_price": [1.0, 1.0, 1.0],
            }
        )

        orders = get_list_of_orders(assets, portfolio, "SGD")

        self.assertNotIn("BTC-USD", orders["yf_name"].tolist())
        self.assertAlmostEqual(orders["p_real"].sum(), 100.0, places=3)
        self.assertAlmostEqual(orders["p_desired"].sum(), 100.0, places=3)
        self.assertAlmostEqual(orders["order_in_SGD"].sum(), 0.0, places=3)

    def test_cash_influx_remains_available_for_rebalancing(self):
        assets = pd.DataFrame(
            {
                "yf_name": ["A", "B", "BTC-USD", "CASH"],
                "position_in_SGD": [60.0, 30.0, 10.0, 10.0],
                "p_overall": [54.545, 27.273, 9.091, 9.091],
                "exchange_rate": [1.0, 1.0, 1.0, 1.0],
                "unit_price": [1.0, 1.0, 1.0, 1.0],
            }
        )
        portfolio = pd.DataFrame(
            {
                "Product": ["Asset A", "Asset B", "Bitcoin"],
                "yf_name": ["A", "B", "BTC-USD"],
                "p_overall": [45.0, 45.0, 10.0],
                "Rebalance": [True, True, False],
                "exchange_rate": [1.0, 1.0, 1.0],
                "unit_price": [1.0, 1.0, 1.0],
            }
        )

        orders = get_list_of_orders(assets, portfolio, "SGD")

        self.assertAlmostEqual(orders["p_real"].sum(), 90.0, places=3)
        self.assertAlmostEqual(orders["p_desired"].sum(), 100.0, places=3)
        self.assertAlmostEqual(orders["order_in_SGD"].sum(), 10.0, places=3)


if __name__ == "__main__":
    unittest.main()
