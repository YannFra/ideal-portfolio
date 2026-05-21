import pandas as pd
import argparse
from utils.current_asset_value import provide_breakdown_existing_assets
from utils.orders import get_list_of_orders
from utils.current_asset_value import access_current_asset_value
from utils.format_ideal_portfolio import format_ideal_portfolio
from utils.plot_evolution import (
    plot_evolution_value,
    export_history_with_values,
    compute_total_invested,
)
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
parser.add_argument("--currency", type=str, help="Currency of reference", default="SGD")
parser.add_argument("--no-example", default=False, action="store_true")
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
access_current_asset_value(portfolio_structure, args.currency)

# Load the purchase history to know the existing portfolio
purchase_history = pd.read_csv(path_portfolio + "_history.csv")
assets_breakdown = provide_breakdown_existing_assets(
    purchase_history, args.investment, args.currency
)

# Load stock splits
splits = pd.read_csv(path_portfolio + "_split.csv")
splits["Date"] = pd.to_datetime(splits["Date"], dayfirst=True)

# Print total invested cash at purchase-date prices alongside current portfolio gain/loss
total_invested = compute_total_invested(
    purchase_history.copy(), args.currency, splits=splits
)
portfolio_value = assets_breakdown[f"position_in_{args.currency}"].sum()
pct_diff = (portfolio_value - total_invested) / total_invested * 100
print(
    f"Total invested cash: {total_invested:.2f} {args.currency}  |  {pct_diff:+.2f}%\n"
)

# Get the list of orders to be made to rebalance the portfolio
get_list_of_orders(assets_breakdown, portfolio_structure, args.currency)

# Export history enriched with order value and portfolio value at each order
export_history_with_values(
    purchase_history.copy(),
    args.currency,
    path_portfolio + "_history_with_values.csv",
    splits=splits,
)

# Some plots to see the evolution of the portfolio
plot_evolution_value(purchase_history.copy(), args.currency, splits=splits)
