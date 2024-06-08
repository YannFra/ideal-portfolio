import pandas as pd
from .current_asset_value import access_current_asset_value


def provide_breakdown_existing_assets(
    purchase_history: pd.DataFrame, cash_influx: float, ref_currency: str
) -> pd.DataFrame:
    """Find the existing positions and their amount in the current portfolio"""

    # Get the total amount of each position
    assets_breakdown = purchase_history.groupby(["yf_name", "Unit"]).sum()[["Quantity"]]
    assets_breakdown.reset_index(inplace=True)

    # Get the unit price of each asset and the exchange rate of its currency to `currency`
    access_current_asset_value(assets_breakdown, ref_currency)

    # Add a line to account for the addition/withdrawal of cash
    if cash_influx > 0:
        assets_breakdown.loc[len(assets_breakdown)] = [
            "CASH",
            ref_currency,
            cash_influx,
            1,
            1,
        ]

    # Calculate the position of each asset in the portfolio
    assets_breakdown["position"] = (
        assets_breakdown["unit_price"] * assets_breakdown["Quantity"]
    )
    assets_breakdown[f"position_in_{ref_currency}"] = (
        assets_breakdown["position"] * assets_breakdown["exchange_rate"]
    )
    assets_breakdown["p_overall"] = (
        assets_breakdown[f"position_in_{ref_currency}"]
        / assets_breakdown[f"position_in_{ref_currency}"].sum()
    ) * 100

    assets_breakdown = assets_breakdown.sort_values(by="p_overall", ascending=False)
    assets_breakdown.reset_index(drop=True, inplace=True)
    print(
        "Breakdown of each asset in the existing portfolio:\n",
        assets_breakdown[["yf_name", f"position_in_{ref_currency}", "p_overall"]],
        "\n",
    )

    return assets_breakdown
