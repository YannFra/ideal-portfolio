import pandas as pd


def get_list_of_orders(
    assets_breakdown: pd.DataFrame, portfolio_breakdown: pd.DataFrame, currency: str
):
    # Merge the two dataframes
    merged_df = assets_breakdown.merge(
        portfolio_breakdown, on="yf_name", how="outer", suffixes=("_real", "_desired")
    )
    merged_df = merged_df[merged_df["yf_name"] != "CASH"]
    merged_df.reset_index(drop=True, inplace=True)

    # Select the desired columns to create the df order
    total_invested = assets_breakdown[f"position_in_{currency}"].sum()
    order = merged_df[
        [
            "Product",
            "yf_name",
            "p_overall_real",
            "p_overall_desired",
            "exchange_rate_desired",
            "unit_price_desired",
        ]
    ].copy()
    order.rename(
        columns={
            "p_overall_real": "p_real",
            "p_overall_desired": "p_desired",
        },
        inplace=True,
    )
    order.fillna(0.0, inplace=True)
    order["difference"] = order["p_desired"] - order["p_real"]
    order[f"order_in_{currency}"] = order["difference"] * total_invested / 100
    order["order_in_shares"] = (
        order[f"order_in_{currency}"]
        / order["exchange_rate_desired"]
        / order["unit_price_desired"]
    )

    print(
        "Orders to pass to rebalance the existing portfolio:\n",
        order[
            [
                "Product",
                "yf_name",
                "p_desired",
                "p_real",
                f"order_in_{currency}",
                "order_in_shares",
            ]
        ]
        .sort_values(by=f"order_in_{currency}", ascending=False, key=abs)
        .round(3),
    )
    print("previous values rounded at 0.1")
