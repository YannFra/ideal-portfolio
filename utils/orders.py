import pandas as pd


def get_list_of_orders(
    assets_breakdown: pd.DataFrame, portfolio_breakdown: pd.DataFrame, currency: str
) -> pd.DataFrame:
    # Merge the two dataframes
    merged_df = assets_breakdown.merge(
        portfolio_breakdown, on="yf_name", how="outer", suffixes=("_real", "_desired")
    )
    merged_df = merged_df[merged_df["yf_name"] != "CASH"]
    merged_df = merged_df[merged_df["Rebalance"] != False]  # noqa: E712
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
            "exchange_rate_real",
            "unit_price_real",
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
    order = order[~((order["p_desired"] == 0) & (order["p_real"] == 0))]
    order["difference"] = order["p_desired"] - order["p_real"]
    order[f"order_in_{currency}"] = order["difference"] * total_invested / 100

    # For positions not in the ideal portfolio, fall back to the real price
    unit_price = order["unit_price_desired"].where(
        order["unit_price_desired"] != 0, order["unit_price_real"]
    )
    exchange_rate = order["exchange_rate_desired"].where(
        order["exchange_rate_desired"] != 0, order["exchange_rate_real"]
    )
    order["order_in_shares"] = (
        order[f"order_in_{currency}"]
        / exchange_rate.replace(0, float("nan"))
        / unit_price.replace(0, float("nan"))
    ).fillna(0)

    return (
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
        .round(3)
        .reset_index(drop=True)
    )
