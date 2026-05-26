import yfinance as yf
import pandas as pd


def history_ticker(ticker: str, date: pd.Timestamp = None) -> pd.DataFrame:
    """Get the df of the history of `ticker` from `date` to today"""

    if date is None:
        date = pd.Timestamp.today().normalize()

    try:
        ticker_yahoo = yf.Ticker(ticker)
        today = pd.Timestamp.today()
        months_since_date = (
            (today.year - date.year) * 12 + (today.month - date.month) + 1
        )
        ticker_history = ticker_yahoo.history(period=f"{months_since_date}mo")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data for '{ticker}': {e}") from e

    if ticker_history.empty:
        raise ValueError(
            f"No price data returned for '{ticker}' — check the ticker symbol"
        )

    if ticker_history.index.tz is not None:
        ticker_history.index = ticker_history.index.tz_localize(None)
    ticker_history.reset_index(inplace=True)

    return ticker_history


def get_last_quote(ticker: str, date: pd.Timestamp = None) -> float:
    """Finds the latest `ticker` price with Yahoo Finance"""

    if ticker == "--":
        return 1.0

    ticker_history = history_ticker(ticker, date)
    if date is None or date == pd.Timestamp.today().normalize():
        return ticker_history["Close"].dropna().iloc[-1]

    return ticker_history.loc[ticker_history["Date"].sub(date).abs().idxmin(), "Close"]


def exchange_rate(x: str, ref_currency: str, date: pd.Timestamp = None) -> float:
    """Find the latest available exchange rate between x and the reference currency via USD."""
    if x == ref_currency:
        return 1.0
    if x == "USD":
        return get_last_quote(f"USD{ref_currency}=x", date)
    if ref_currency == "USD":
        return get_last_quote(f"{x}USD=x", date)
    return get_last_quote(f"{x}USD=x", date) * get_last_quote(
        f"USD{ref_currency}=x", date
    )


def invested_cash(x: pd.Series) -> float:
    return x["unit_price"] * x["exchange_rate"] * x["Quantity"]


def access_current_asset_value(
    df: pd.DataFrame, ref_currency: str, date: pd.Timestamp = None
):
    """Find the latest exchange rate and unit price for each asset in df"""

    df["unit_price"] = df["yf_name"].apply(lambda x: get_last_quote(x, date))
    df["exchange_rate"] = df["Unit"].apply(
        lambda x: exchange_rate(x, ref_currency, date)
    )


def provide_breakdown_existing_assets(
    purchase_history: pd.DataFrame,
    cash_influx: float,
    ref_currency: str,
    date: pd.Timestamp = None,
) -> pd.DataFrame:
    """Find the existing positions and their amount in the current portfolio"""

    # Get the total amount of each position
    assets_breakdown = purchase_history.copy()
    assets_breakdown = assets_breakdown.groupby(["yf_name", "Unit"]).sum()[["Quantity"]]
    assets_breakdown.reset_index(inplace=True)

    # Get the unit price of each asset and the exchange rate of its currency to `currency`
    access_current_asset_value(assets_breakdown, ref_currency, date)

    # Add a line to account for the addition/withdrawal of cash
    if cash_influx > 0:
        cash_row = pd.DataFrame(
            [
                {
                    "yf_name": "CASH",
                    "Unit": ref_currency,
                    "Quantity": cash_influx,
                    "unit_price": 1,
                    "exchange_rate": 1,
                }
            ]
        )
        assets_breakdown = pd.concat([assets_breakdown, cash_row], ignore_index=True)

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

    return assets_breakdown
