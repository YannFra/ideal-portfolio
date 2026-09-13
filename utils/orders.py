import pandas as pd


def get_list_of_orders(
    assets_breakdown: pd.DataFrame, portfolio_breakdown: pd.DataFrame, currency: str
) -> pd.DataFrame:
    # Merge the two dataframes
    merged_df = assets_breakdown.merge(
        portfolio_breakdown, on="yf_name", how="outer", suffixes=("_real", "_desired")
    )

    # Holdings explicitly excluded from rebalancing must not affect either the
    # available capital or the current/desired weights of the tradable assets.
    if "Rebalance" in merged_df:
        rebalance = merged_df["Rebalance"]
        excluded = rebalance.eq(False).fillna(False)
        excluded |= (
            rebalance.astype("string").str.strip().str.lower().eq("false").fillna(False)
        )
    else:
        excluded = pd.Series(False, index=merged_df.index)

    position_column = f"position_in_{currency}"
    excluded_tickers = merged_df.loc[excluded, "yf_name"]
    available_assets = assets_breakdown.loc[
        ~assets_breakdown["yf_name"].isin(excluded_tickers)
    ]
    available_capital = available_assets[position_column].fillna(0.0).sum()
    if available_capital == 0:
        raise ValueError("Cannot calculate orders with no rebalanceable capital")

    merged_df = merged_df.loc[~excluded & (merged_df["yf_name"] != "CASH")].copy()
    merged_df.reset_index(drop=True, inplace=True)

    # Select the desired columns to create the df order
    order = merged_df[
        [
            "Product",
            "yf_name",
            "p_overall_desired",
            position_column,
            "exchange_rate_desired",
            "unit_price_desired",
        ]
    ].copy()
    order.rename(
        columns={
            "p_overall_desired": "p_desired",
        },
        inplace=True,
    )
    order[position_column] = order[position_column].fillna(0.0)
    order["p_real"] = order[position_column] / available_capital * 100
    order["p_desired"] = order["p_desired"].fillna(0.0)

    desired_total = order["p_desired"].sum()
    if desired_total == 0:
        raise ValueError("Cannot calculate orders with no desired allocation")
    order["p_desired"] = order["p_desired"] / desired_total * 100

    order = order[~((order["p_desired"] == 0) & (order["p_real"] == 0))]
    order["difference"] = order["p_desired"] - order["p_real"]
    order[f"order_in_{currency}"] = order["difference"] * available_capital / 100
    order["order_in_shares"] = (
        order[f"order_in_{currency}"]
        / order["exchange_rate_desired"]
        / order["unit_price_desired"]
    )

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
