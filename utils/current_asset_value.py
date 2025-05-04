import yfinance as yf
import pandas as pd


from rich import print
import os


def load_data(ticker: str, date: pd.Timestamp, verbose:bool=True) -> pd.DataFrame:

    os.makedirs(os.path.join("data", ticker), exist_ok=True)

    if date == None:
        date = pd.Timestamp.today().normalize()

    # Create the folder if it does not exist
    ds_name = date.strftime("%Y-%m-%d")+ ".csv"
    ds_path = os.path.join("data", ticker, ds_name)
    if os.path.exists(ds_path):
        if verbose:
            print(f"File already exists: {ds_path}")
        ticker_history = pd.read_csv(ds_path)
        ticker_history["Date"] = pd.to_datetime(ticker_history["Date"])
    else:
        if verbose:
            print(f"Created file: {ds_path}")
        ticker_history = _history_ticker(ticker, date)
        ticker_history.to_csv(ds_path, index=False)
    return ticker_history 
    

def _history_ticker(ticker: str, date: pd.Timestamp) -> pd.DataFrame:
    """Get the df of the history of `ticker` from `date` to today"""

    try:
        ticker_yahoo = yf.Ticker(ticker)
    except Exception as e:
        raise Exception(f"Failed to retrieve data for ticker {ticker}: {e}")

    today = pd.Timestamp.today()
    months_since_date = (today.year - date.year) * 12 + (today.month - date.month) + 1
    ticker_history = ticker_yahoo.history(period=f"{months_since_date}mo")
    ticker_history.index = ticker_history.index.tz_localize(None)
    ticker_history.reset_index(inplace=True)

    return ticker_history


def get_last_quote(ticker: str, date: pd.Timestamp = None, verbose: bool = True) -> float:
    """Finds the latest `ticker` price with Yahoo Finance"""

    # Return 1.0 if it is cash, i.e. if "--"
    if ticker == "--":
        return 1.0

    # Otherwise, create the ticker to retrieve the data
    # Return the last quote if no specific `date` is provided
    # ticker_data = load_data(ticker, date)
    # if date is None or date == pd.Timestamp.today().normalize():
    #     try:
    #         ticker_yahoo = yf.Ticker(ticker)
    #     except Exception as e:
    #         raise Exception(f"Failed to retrieve data for ticker {ticker}: {e}")
    #     ticker_history = ticker_yahoo.history()
    #     quote = ticker_history.iloc[-1]["Close"]
    #     return quote
    
    

    # Get the quote for the closest date if a specific `date` is provided
    ticker_history = load_data(ticker, date, verbose = verbose)
    if date is None or date == pd.Timestamp.today().normalize():
        return ticker_history["Close"].iloc[-1]
    
    return ticker_history.loc[
                ticker_history["Date"].sub(date).abs().idxmin(), "Close"
            ]

    # Look up to two days before or after (week-end)
    for i in range(3):
        try:
            return ticker_history.loc[
                ticker_history["Date"] == date - pd.Timedelta(days=i), "Close"
            ].values[0]
        except Exception:
            pass
        try:
            return ticker_history.loc[
                ticker_history["Date"] == date + pd.Timedelta(days=i), "Close"
            ].values[0]
        except Exception:
            pass
    print("issue quote", ticker, date)


def exchange_rate(x: str, ref_currency: str, date: pd.Timestamp = None, verbose = True) -> float:
    """Find the latest available exchange rate between x and the reference currency"""
    # Do nothing if the asset currency is already the one of refernce
    # TODO: generalise beyond USD
    if x == ref_currency:
        return 1.0

    return get_last_quote(f"{x}{ref_currency}=x", date, verbose=verbose)


def invested_cash(x: pd.Series) -> float:
    return x["unit_price"] * x["exchange_rate"] * x["Quantity"]


def access_current_asset_value(
    df: pd.DataFrame, ref_currency: str, date: pd.Timestamp = None, verbose: bool = True
):
    """Find the latest exchange rate and unit price for each asset in df"""


    df["unit_price"] = df["yf_name"].apply(lambda x: get_last_quote(x, date, verbose=verbose))
    df["exchange_rate"] = df["Unit"].apply(
        lambda x: exchange_rate(x, ref_currency, date, verbose=verbose)
    )


def provide_breakdown_existing_assets(
    purchase_history: pd.DataFrame,
    cash_influx: float,
    ref_currency: str,
    date: pd.Timestamp = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Find the existing positions and their amount in the current portfolio"""

    # Get the total amount of each position
    assets_breakdown = purchase_history.copy()
    assets_breakdown = assets_breakdown.groupby(["yf_name", "Unit"]).sum()[["Quantity"]]
    assets_breakdown.reset_index(inplace=True)

    # Get the unit price of each asset and the exchange rate of its currency to `currency`
    access_current_asset_value(assets_breakdown, ref_currency, date, verbose=verbose)

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
    if verbose:
        print(
            "Breakdown of each asset in the existing portfolio:\n",
            assets_breakdown[["yf_name", f"position_in_{ref_currency}", "p_overall", "Quantity"]],
        )
        total_invested = assets_breakdown[f"position_in_{ref_currency}"].sum()
        print("Portfolio total value:", total_invested, ref_currency, "\n")

    return assets_breakdown
