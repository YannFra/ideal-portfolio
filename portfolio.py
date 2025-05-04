import pandas as pd
import argparse
from utils.current_asset_value import provide_breakdown_existing_assets
from utils.orders import get_list_of_orders
from utils.current_asset_value import access_current_asset_value
from utils.format_ideal_portfolio import format_ideal_portfolio
from utils.plot_evolution import plot_evolution_value
from rich import print
# yf.enable_debug_mode()


# External inputs
parser = argparse.ArgumentParser(description="Calculate portfolio breakdown.")
parser.add_argument(
    "--investment",
    type=float,
    help="Addition/Substraction to the portfolio value in default currency",
    default=0,
)
parser.add_argument("--currency", type=str, help="Currency of reference", default="USD")
parser.add_argument("--no-example", default=False, action="store_true")
parser.add_argument("--verbose", default=False, action="store_true")
args = parser.parse_args()

# Path of the structure and purchase history
if args.no_example:
    path_portfolio = "your_portfolio/"
else:
    path_portfolio = "example_portfolio/"

# Log regarding the change in amount of invested cash
if args.investment > 0.0:
    print(f"{args.investment}{args.currency} added to the portfolio")
elif args.investment < 0.0:
    print(f"{args.investment}{args.currency} removed from the portfolio")

# Load the portfolio and its strategy
portfolio_structure = pd.read_csv(path_portfolio + "_ideal_portfolio.csv")

# Summarize the structure of the portfolio
format_ideal_portfolio(portfolio_structure)
access_current_asset_value(portfolio_structure, args.currency, verbose=args.verbose)

# Load the purchase history to know the existing portfolio
purchase_history = pd.read_csv(path_portfolio + "_history.csv")
assets_breakdown = provide_breakdown_existing_assets(
    purchase_history, args.investment, args.currency, verbose=args.verbose
)

# Get the list of orders to be made to rebalance the portfolio
get_list_of_orders(assets_breakdown, portfolio_structure, args.currency)


plot_evolution_value(purchase_history.copy(), args.currency, verbose=args.verbose)
