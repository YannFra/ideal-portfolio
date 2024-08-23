import pandas as pd


import matplotlib.pyplot as plt
import numpy as np


from .current_asset_value import (
    get_last_quote,
    exchange_rate,
    invested_cash,
    provide_breakdown_existing_assets,
    history_ticker,
)


def _augment_timestamp(df: pd.DataFrame, first_date: pd.Timestamp = None):
    """Augment the dataframe with a timestamp column"""
    if first_date is None:
        first_date = df["Date"].min()
    else:
        first_date = min(df["Date"].min(), first_date)
    last_date = pd.Timestamp.today().normalize()
    added_dates = pd.date_range(start=first_date, end=last_date, freq="W-MON")
    df = pd.concat([df, pd.DataFrame({"Date": added_dates})])
    df = df.sort_values(by="Date").ffill().fillna(0).reset_index(drop=True)
    return df


def plot_evolution_value(purchase_history: pd.DataFrame, ref_currency: str):
    # Be sure that dates can be used (TimesTamp format)
    purchase_history["Date"] = pd.to_datetime(
        purchase_history["Date"], format="%d/%m/%y"
    )

    # Get the amount of cash invested PER POSITION
    purchase_history["unit_price"] = purchase_history.apply(
        lambda x: get_last_quote(x["yf_name"], x["Date"]), axis=1
    )
    purchase_history["exchange_rate"] = purchase_history.apply(
        lambda x: exchange_rate(x["Unit"], ref_currency, x["Date"]), axis=1
    )
    purchase_history["invested_cash"] = purchase_history.apply(invested_cash, axis=1)

    # Get the amount of cash invested PER DATE
    # Add inputs in df for each Monday since the beginning of the strategy
    df_portfolio_value = (
        purchase_history[["Date", "invested_cash"]].groupby("Date").sum().cumsum()
    )
    df_portfolio_value.reset_index(inplace=True)
    df_portfolio_value = _augment_timestamp(df_portfolio_value)

    # Get the value of the portfolio overtime PER DATE
    for date in df_portfolio_value.Date.tolist():
        # Keep the orders run before that date...
        df_date = purchase_history[purchase_history["Date"] <= date].drop(
            columns="Date"
        )

        # ... and get the resulting breakdown at that Date, to get the portfolio value then
        assets_breakdown = provide_breakdown_existing_assets(
            df_date, 0, ref_currency, date=date, verbose=False
        )
        df_portfolio_value.loc[
            df_portfolio_value["Date"] == date, "portfolio_value"
        ] = assets_breakdown[f"position_in_{ref_currency}"].sum()

    # Reproduce df_portfolio_value for each tag
    histories = {}
    for tag in purchase_history["yf_name"].unique():
        histories[tag] = (
            purchase_history[purchase_history["yf_name"] == tag][
                ["Date", "Quantity", "invested_cash"]
            ]
            .groupby("Date")
            .sum()
            .cumsum()
        )
        histories[tag].reset_index(inplace=True)
        histories[tag] = _augment_timestamp(
            histories[tag], purchase_history["Date"].min()
        )

        if tag == "--":
            histories[tag]["position_value"] = histories[tag]["Quantity"]
        else:
            history_tag = history_ticker(tag, purchase_history["Date"].min())
            histories[tag] = histories[tag].merge(
                history_tag[["Date", "Close"]], on="Date", how="left"
            )
            histories[tag].loc[histories[tag]["Close"] == 0, "Close"] = np.nan
            histories[tag] = histories[tag].ffill().fillna(0)
            histories[tag].rename(columns={"Close": "position_value"}, inplace=True)
            histories[tag]["position_value"] *= histories[tag]["Quantity"]

        unit = purchase_history[purchase_history["yf_name"] == tag]["Unit"].iloc[0]
        if unit != ref_currency:
            history_unit = history_ticker(
                f"{unit}{ref_currency}=x", purchase_history["Date"].min()
            )[["Date", "Close"]]
            histories[tag] = histories[tag].merge(
                history_unit[["Date", "Close"]], on="Date", how="left"
            )
            histories[tag].rename(columns={"Close": "exchange_rate"}, inplace=True)
            histories[tag]["position_value"] = (
                histories[tag]["position_value"] * histories[tag]["exchange_rate"]
            )

    # Do the plot
    # Two rows, one for the portfolio as a whole, one for the individual positions
    fig, axes = plt.subplots(2, 3, figsize=(20, 10))

    # OVERALL PORTFOLIO
    # Invested Cash vs Return vs Inflation vs Saving account
    axes[0, 0].set_title("Evolution of the portfolio value")
    axes[0, 0].plot(
        df_portfolio_value["Date"],
        df_portfolio_value["invested_cash"],
        drawstyle="steps-post",
        label="invested cash",
    )
    axes[0, 0].plot(
        df_portfolio_value["Date"],
        df_portfolio_value["portfolio_value"],
        label="portfolio value",
    )
    axes[0, 0].set_ylabel(f"Value (in {ref_currency})")
    axes[0, 0].legend()

    # Benefits (in ref_currency)
    axes[0, 1].set_title(f"Evolution of the benefits (in {ref_currency})")
    axes[0, 1].plot(
        df_portfolio_value["Date"],
        df_portfolio_value["portfolio_value"] - df_portfolio_value["invested_cash"],
        label="Benefits",
    )
    axes[0, 1].axhline(0, color="black", linestyle="--", linewidth=0.75)
    axes[0, 1].set_ylabel(f"Benefits (in {ref_currency})")

    # Yield (in %)
    axes[0, 2].set_title("Portfolio yield (in %)")
    axes[0, 2].plot(
        df_portfolio_value["Date"],
        100
        * (df_portfolio_value["portfolio_value"] / df_portfolio_value["invested_cash"])
        - 100,
        label="Percentage",
    )
    axes[0, 2].axhline(0, color="black", linestyle="--", linewidth=0.75)
    axes[0, 2].set_ylabel("Percentage (in %)")

    # INDIVIDUAL POSITIONS
    axes[1, 0].set_title("Evolution of the assets value")
    for tag, df_tag in histories.items():
        axes[1, 0].plot(
            df_tag["Date"], df_tag["invested_cash"], drawstyle="steps-post", label=tag
        )
        # axes[0, 0].plot(df_portfolio_value["Date"], df_portfolio_value["portfolio_value"], label = "portfolio value")
        axes[1, 0].set_ylabel(f"Value (in {ref_currency})")
        axes[1, 0].legend()

        axes[1, 1].set_title(f"Evolution of the benefits (in {ref_currency})")
        axes[1, 1].plot(
            df_tag["Date"],
            df_tag["position_value"] - df_tag["invested_cash"],
            label=tag,
        )
        axes[1, 1].axhline(0, color="black", linestyle="--", linewidth=0.75)
        axes[1, 1].set_ylabel(f"Benefits (in {ref_currency})")

        # Yield (in %)
        axes[1, 2].set_title("Portfolio yield (in %)")
        axes[1, 2].plot(
            df_tag["Date"],
            100 * (df_tag["position_value"] / df_tag["invested_cash"]) - 100,
            label=tag,
        )
        axes[1, 2].axhline(0, color="black", linestyle="--", linewidth=0.75)
        axes[1, 2].set_ylabel("Percentage (in %)")

    for ax in axes.flatten():
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", linewidth=0.5, color="lightgray")

    fig.tight_layout()
    plt.show()
