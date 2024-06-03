import pandas as pd


def load_portfolio(path_portfolio: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Load the theoretical meta structure of the portfolio
    portfolio_structure = pd.read_csv(path_portfolio + "_categories.csv")
    portfolio_structure.sort_values(by="Ratio", ascending=False, inplace=True)
    portfolio_structure.reset_index(drop=True, inplace=True)
    print("Meta-structure of the portfolio:\n", portfolio_structure, "\n")

    # Percentage of each asset in the portfolio
    portfolio_breakdown = pd.concat(
        {
            category: _load_df_category(path_portfolio, category)
            for category in portfolio_structure.Category
        }
    )
    portfolio_breakdown["p_category"] = portfolio_breakdown["Category"].apply(
        lambda x: portfolio_structure.set_index("Category").loc[x, "Ratio"]
    )
    portfolio_breakdown["p_overall"] = (
        portfolio_breakdown["p_category"] * portfolio_breakdown["p_desired"]
    )
    portfolio_breakdown.sort_values(by="p_overall", ascending=False, inplace=True)
    portfolio_breakdown.reset_index(drop=True, inplace=True)
    print(
        "Breakdown of each asset in the theoretical portfolio:\n",
        portfolio_breakdown[["Asset", "Category", "p_overall"]],
        "\n",
    )

    return portfolio_structure, portfolio_breakdown


def _load_df_category(path_portfolio: str, category: str) -> pd.DataFrame:
    """Load each df part of the split"""

    # Load the dataset
    df = pd.read_csv(path_portfolio + f"{category}.csv")
    df["Category"] = category

    # Verify that columns yf_name, Quantity, and p_desired exist
    if any([c not in df.columns for c in ["yf_name", "p_desired"]]):
        raise Exception(f"{category}.csv - columns ['yf_name', 'p_desired'] needed")

    # Verify that there are no NaNs in yf_name, Quantity, and p_desired
    if df[["yf_name", "p_desired"]].isna().sum().sum():
        raise Exception(f"{category}.csv - contains NaNs in ['yf_name', 'p_desired']")

    # Verify that the sum oft he probabilities is equal to 1
    if round(df["p_desired"].sum(), 5) != 1.0:
        raise Exception(f"{category}.csv - desired probabilities do not sum to 1")

    return df
