import pandas as pd


def get_list_of_orders(
    assets_breakdown: pd.DataFrame, portfolio_breakdown: pd.DataFrame
):
    # Merge the two dataframes
    merged_df = assets_breakdown.merge(
        portfolio_breakdown, on="yf_name", how="outer", suffixes=("_real", "_desired")
    )
    merged_df = merged_df[merged_df["yf_name"] != "CASH"]
    merged_df.reset_index(drop=True, inplace=True)

    # Select the desired columns to create the df order
    total_invested = assets_breakdown["position_X"].sum()
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
    order["order_in_X"] = order["difference"] * total_invested
    order["order_in_shares"] = (
        order["order_in_X"]
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
                "order_in_X",
                "order_in_shares",
            ]
        ].sort_values(by="order_in_X", ascending=False, key=abs),
    )
