import pandas as pd
from utils.load_positions import load_portfolio
from utils.assets_breakdown import provide_breakdown_existing_assets
from utils.orders import get_list_of_orders
from utils.current_asset_value import access_current_asset_value
import argparse


# External inputs
parser = argparse.ArgumentParser(description="Calculate portfolio breakdown.")
parser.add_argument(
    "--investment",
    type=float,
    help="Addition/Substraction to the portfolio value in default currency",
    default=0,
)
parser.add_argument("--currency", type=str, help="Currency of reference", default="USD")
parser.add_argument(
    "--no-example", default=False, action=argparse.BooleanOptionalAction
)
args = parser.parse_args()

if args.no_example:
    path_portfolio = "your_portfolio/"
else:
    path_portfolio = "example_portfolio/"

if args.investment > 0.0:
    print(f"Amount of added money to the portfolio: {args.investment}")
elif args.investment < 0.0:
    print(f"Amount of withdrawn money from the portfolio: {args.investment}")

# Load the portfolio and its strategy
portfolio_structure, portfolio_breakdown = load_portfolio(path_portfolio)
access_current_asset_value(portfolio_breakdown, args.currency)

# Load the purchase history to know the existing portfolio
purchase_history = pd.read_csv(path_portfolio + "_history.csv")
assets_breakdown = provide_breakdown_existing_assets(
    purchase_history, args.investment, args.currency
)
total_invested = assets_breakdown["position_X"].sum()
print("Portfolio total value:", total_invested, args.currency, "\n")

# Get the list of orders to be made to rebalance the portfolio
get_list_of_orders(assets_breakdown, portfolio_breakdown)
