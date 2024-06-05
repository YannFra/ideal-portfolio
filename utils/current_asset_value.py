import yfinance as yf
import pandas as pd

from currency_converter import CurrencyConverter


def _get_last_quote(ticker: str) -> float:
    """Finds the latest ticker price with Yahoo Finance"""

    # Return 1.0 if it is cash, i.e. if "--"
    if ticker == "--":
        return 1.0

    # Otherwise, retrieve the last available closing price of the ticker
    try:
        ticker_yahoo = yf.Ticker(ticker)
    except Exception as e:
        raise Exception(f"Failed to retrieve data for ticker {ticker}: {str(e)}")
    data = ticker_yahoo.history()
    last_quote = data["Close"].iloc[-1]
    return last_quote


def _exchange_rate(x: str, ref_currency: str) -> float:
    """Find the latest available exchange rate between x and the reference currency"""
    if x == ref_currency:
        return 1.0
    c = CurrencyConverter()
    return c.convert(1, x, ref_currency)


def access_current_asset_value(df: pd.DataFrame, ref_currency: str):
    """Find the latest exchange rate and unit price for each asset in df"""

    df["unit_price"] = df["yf_name"].apply(_get_last_quote)
    df["exchange_rate"] = df["Unit"].apply(lambda x: _exchange_rate(x, ref_currency))
