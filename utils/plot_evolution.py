import pandas as pd
import matplotlib.pyplot as plt

from .current_asset_value import invested_cash, history_ticker


# ── Helpers ───────────────────────────────────────────────────────────────────


def _nearest_close(hist: pd.DataFrame, date: pd.Timestamp) -> float:
    idx = hist["Date"].sub(date).abs().idxmin()
    nearest = hist.loc[idx, "Date"]
    distance = pd.bdate_range(min(date, nearest), max(date, nearest))
    if len(distance) - 1 > 5:
        print(
            f"Warning: nearest data point for {date.date()} is {nearest.date()} ({len(distance)-1} business days away)"
        )
    return hist.loc[idx, "Close"]


def _weekly_spine(first_date: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(
        start=first_date, end=pd.Timestamp.today().normalize(), freq="W-MON"
    )


# ── Pipeline steps ────────────────────────────────────────────────────────────


def _fetch_price_histories(
    purchase_history: pd.DataFrame, ref_currency: str, first_date: pd.Timestamp
) -> tuple[dict, dict]:
    ticker_histories = {
        ticker: history_ticker(ticker, first_date)
        for ticker in purchase_history["yf_name"].unique()
        if ticker != "--"
    }
    non_ref_units = {u for u in purchase_history["Unit"].unique() if u != ref_currency}

    usd_to_ref = (
        history_ticker(f"USD{ref_currency}=x", first_date)
        if ref_currency != "USD"
        else None
    )

    unit_histories = {}
    for unit in non_ref_units:
        if unit == "USD":
            unit_histories["USD"] = usd_to_ref
        else:
            unit_to_usd = history_ticker(f"{unit}USD=x", first_date)
            if ref_currency == "USD":
                unit_histories[unit] = unit_to_usd
            else:
                merged = (
                    unit_to_usd[["Date", "Close"]]
                    .merge(
                        usd_to_ref[["Date", "Close"]],
                        on="Date",
                        suffixes=("_a", "_b"),
                        how="outer",
                    )
                    .sort_values("Date")
                    .ffill()
                )
                merged["Close"] = merged["Close_a"] * merged["Close_b"]
                unit_histories[unit] = merged[["Date", "Close"]].reset_index(drop=True)

    return ticker_histories, unit_histories


def _annotate_purchases(
    purchase_history: pd.DataFrame,
    ticker_histories: dict,
    unit_histories: dict,
    ref_currency: str,
    splits: pd.DataFrame = None,
) -> pd.DataFrame:
    def price_at(row):
        if row["yf_name"] == "--":
            return 1.0
        return _nearest_close(ticker_histories[row["yf_name"]], row["Date"])

    def fx_at(row):
        if row["Unit"] == ref_currency:
            return 1.0
        return _nearest_close(unit_histories[row["Unit"]], row["Date"])

    purchase_history["unit_price"] = purchase_history.apply(price_at, axis=1)
    purchase_history["exchange_rate"] = purchase_history.apply(fx_at, axis=1)
    purchase_history["invested_cash"] = purchase_history.apply(invested_cash, axis=1)

    if splits is not None and not splits.empty:
        for _, split_row in splits.iterrows():
            mask = (purchase_history["yf_name"] == split_row["yf_name"]) & (
                purchase_history["Date"] < split_row["Date"]
            )
            purchase_history.loc[mask, "invested_cash"] /= split_row["Split"]

    return purchase_history


def _build_timeseries(
    purchase_history: pd.DataFrame,
    ticker_histories: dict,
    unit_histories: dict,
    ref_currency: str,
    first_date: pd.Timestamp,
    splits: pd.DataFrame = None,
) -> pd.DataFrame:
    dates = _weekly_spine(first_date)

    # Invested cash: cumulative sum of purchases converted at purchase-date FX (step function)
    invested = (
        purchase_history.groupby("Date")["invested_cash"]
        .sum()
        .cumsum()
        .reindex(dates, method="ffill")
        .fillna(0)
    )

    # Portfolio value: for each ticker, cumulative quantity × current price × current FX
    position_values = {}
    for tag in purchase_history["yf_name"].unique():
        tag_df = purchase_history[purchase_history["yf_name"] == tag]

        qty = (
            tag_df.groupby("Date")["Quantity"]
            .sum()
            .cumsum()
            .reindex(dates, method="ffill")
            .fillna(0)
        )

        if splits is not None and not splits.empty:
            for _, split_row in splits[splits["yf_name"] == tag].iterrows():
                qty[qty.index < split_row["Date"]] /= split_row["Split"]

        if tag == "--":
            price = pd.Series(1.0, index=dates)
        else:
            price = (
                ticker_histories[tag]
                .set_index("Date")["Close"]
                .reindex(dates, method="ffill")
                .bfill()
            )
            if price.isna().all():
                raise ValueError(f"No price data available for ticker '{tag}'")

        unit = tag_df["Unit"].iloc[0]
        if unit == ref_currency:
            fx = pd.Series(1.0, index=dates)
        else:
            fx = (
                unit_histories[unit]
                .set_index("Date")["Close"]
                .reindex(dates, method="ffill")
                .bfill()
            )
            if fx.isna().all():
                raise ValueError(
                    f"No FX data available for unit '{unit}' to '{ref_currency}'"
                )

        position_values[tag] = qty * price * fx

    portfolio_value = pd.DataFrame(position_values).sum(axis=1)

    return pd.DataFrame(
        {
            "Date": dates,
            "invested_cash": invested.values,
            "portfolio_value": portfolio_value.values,
        }
    )


# ── Plotting ──────────────────────────────────────────────────────────────────


def _plot(df: pd.DataFrame, unit_histories: dict, ref_currency: str) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    axes[0].set_title("Portfolio value")
    axes[0].plot(
        df["Date"], df["invested_cash"], drawstyle="steps-post", label="Invested cash"
    )
    axes[0].plot(df["Date"], df["portfolio_value"], label="Portfolio value")
    axes[0].set_ylabel(f"Value ({ref_currency})")
    axes[0].legend()

    axes[1].set_title("Benefits")
    axes[1].plot(df["Date"], df["portfolio_value"] - df["invested_cash"])
    axes[1].axhline(0, color="black", linestyle="--", linewidth=0.75)
    axes[1].set_ylabel(f"Benefits ({ref_currency})")

    axes[2].set_title("Yield (%)")
    axes[2].plot(df["Date"], 100 * df["portfolio_value"] / df["invested_cash"] - 100)
    axes[2].axhline(0, color="black", linestyle="--", linewidth=0.75)
    axes[2].set_ylabel("Percentage (%)")

    axes[3].set_title("Exchange rates")
    for unit, hist in unit_histories.items():
        axes[3].plot(hist["Date"], hist["Close"], label=f"{unit}/{ref_currency}")
    axes[3].set_ylabel(f"Rate (to {ref_currency})")
    axes[3].legend()

    for ax in axes:
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="both", linestyle="--", linewidth=0.5, color="lightgray")

    fig.tight_layout()
    plt.show()


# ── Public API ────────────────────────────────────────────────────────────────


def compute_total_invested(
    purchase_history: pd.DataFrame, ref_currency: str, splits: pd.DataFrame = None
) -> float:
    """Return total cash invested at purchase-date prices, split-adjusted."""
    purchase_history = purchase_history.copy()
    purchase_history["Date"] = pd.to_datetime(
        purchase_history["Date"], format="%d/%m/%y"
    )
    first_date = purchase_history["Date"].min()
    ticker_histories, unit_histories = _fetch_price_histories(
        purchase_history, ref_currency, first_date
    )
    purchase_history = _annotate_purchases(
        purchase_history, ticker_histories, unit_histories, ref_currency, splits
    )
    return purchase_history["invested_cash"].sum()


def export_history_with_values(
    purchase_history: pd.DataFrame,
    ref_currency: str,
    output_path: str,
    splits: pd.DataFrame = None,
) -> None:
    purchase_history = purchase_history.copy()
    purchase_history["Date"] = pd.to_datetime(
        purchase_history["Date"], format="%d/%m/%y"
    )
    first_date = purchase_history["Date"].min()

    ticker_histories, unit_histories = _fetch_price_histories(
        purchase_history, ref_currency, first_date
    )
    purchase_history = _annotate_purchases(
        purchase_history, ticker_histories, unit_histories, ref_currency, splits
    )

    purchase_history[f"order_value_{ref_currency}"] = purchase_history["invested_cash"]

    def _portfolio_value_at(date: pd.Timestamp) -> float:
        past = purchase_history[purchase_history["Date"] <= date]
        total = 0.0
        for tag in past["yf_name"].unique():
            if tag == "BTC-USD":
                continue
            tag_past = past[past["yf_name"] == tag]
            qty = tag_past["Quantity"].sum()
            if splits is not None and not splits.empty:
                for _, split_row in splits[splits["yf_name"] == tag].iterrows():
                    if date < split_row["Date"]:
                        qty /= split_row["Split"]
            price = 1.0 if tag == "--" else _nearest_close(ticker_histories[tag], date)
            unit = tag_past["Unit"].iloc[0]
            fx = (
                1.0
                if unit == ref_currency
                else _nearest_close(unit_histories[unit], date)
            )
            total += qty * price * fx
        return total

    purchase_history[f"portfolio_value_{ref_currency}"] = purchase_history[
        "Date"
    ].apply(_portfolio_value_at)

    purchase_history[
        [
            "Date",
            "yf_name",
            "Unit",
            "Quantity",
            f"order_value_{ref_currency}",
            f"portfolio_value_{ref_currency}",
        ]
    ].to_csv(output_path, index=False)


def plot_evolution_value(
    purchase_history: pd.DataFrame, ref_currency: str, splits: pd.DataFrame = None
) -> None:
    purchase_history["Date"] = pd.to_datetime(
        purchase_history["Date"], format="%d/%m/%y"
    )
    first_date = purchase_history["Date"].min()

    ticker_histories, unit_histories = _fetch_price_histories(
        purchase_history, ref_currency, first_date
    )
    purchase_history = _annotate_purchases(
        purchase_history, ticker_histories, unit_histories, ref_currency, splits
    )
    df = _build_timeseries(
        purchase_history,
        ticker_histories,
        unit_histories,
        ref_currency,
        first_date,
        splits,
    )
    _plot(df, unit_histories, ref_currency)
