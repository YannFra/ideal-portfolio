import pandas as pd

# TODO: Look for human errors when filling the csv
# TODO: Return warning if the sum of the probabilities is not 100
# TODO: Return warning if different probabilities are given to the same category


def format_ideal_portfolio(portfolio_csv: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Remove empty rows and columns
    portfolio_csv.dropna(axis=0, how="all", inplace=True)
    portfolio_csv.dropna(axis=1, how="all", inplace=True)

    # Verify that columns do not have empty spaces at the beginning or end
    portfolio_csv.columns = portfolio_csv.columns.str.strip()
    levels = [c for c in portfolio_csv.columns if c.startswith("L") and c[1:].isdigit()]

    for i, level in enumerate(levels):
        # Replace missing values for the probability fo the same category
        portfolio_csv[f"p_{level}"].fillna(
            portfolio_csv.groupby(levels[: i + 1])[f"p_{level}"].transform("first"),
            inplace=True,
        )

    # TODO: Force every category to have the sum of its probabiltiies to sum to 1

    # Calculate the overall importance of every postion
    portfolio_csv["p_overall"] = 1.0
    for level in levels:
        non_nans = portfolio_csv[f"p_{level}"].notna()
        portfolio_csv.loc[non_nans, "p_overall"] *= (
            portfolio_csv.loc[non_nans, f"p_{level}"] / 100
        )
    portfolio_csv["p_overall"] *= (1 / portfolio_csv["p_overall"].sum()) * 100

    portfolio_csv = portfolio_csv.sort_values(by="p_overall", ascending=False)
    portfolio_csv.reset_index(drop=True, inplace=True)
    print(
        "Breakdown of each asset in the theoretical portfolio:\n",
        portfolio_csv[["Product", "Tag", "p_overall"]],
        "\n",
    )
    return portfolio_csv
