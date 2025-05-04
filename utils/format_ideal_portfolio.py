import pandas as pd
from treelib import Tree

from rich import print

# TODO: Look for human errors when filling the csv
# TODO: Return warning if the sum of the probabilities is not 100
# TODO: Return warning if different probabilities are given to the same category


def format_ideal_portfolio(portfolio_csv: pd.DataFrame) -> pd.DataFrame:
    # Remove empty rows and columns
    portfolio_csv.dropna(axis=0, how="all", inplace=True)
    portfolio_csv.dropna(axis=1, how="all", inplace=True)

    # Verify that columns do not have empty spaces at the beginning or end
    portfolio_csv.columns = portfolio_csv.columns.str.strip()

    # Replace missing values for the probability of the same category
    levels = [c for c in portfolio_csv.columns if c.startswith("L") and c[1:].isdigit()]
    portfolio_csv.fillna(
        {
            f"p_{level}": portfolio_csv.groupby(levels[: i + 1])[
                f"p_{level}"
            ].transform("first")
            for i, level in enumerate(levels)
        },
        inplace=True,
    )

    # TODO: Force every category to have its sum of probabilties equal to 1

    # Find path and leaf probabilities
    portfolio_csv["tree_path"] = ""
    portfolio_csv["p_overall"] = 1.0
    for level in levels:
        # Add level name to the path
        portfolio_csv["tree_path"] += " - " + portfolio_csv[level].astype(str)

        # Calculate the importance of each category
        non_nans = portfolio_csv[f"p_{level}"].notna()
        portfolio_csv.loc[non_nans, "p_overall"] *= (
            portfolio_csv.loc[non_nans, f"p_{level}"] / 100
        )

    # Divide by the amount of identical leaves
    portfolio_csv["tree_path"] = portfolio_csv.groupby("tree_path")[
        "tree_path"
    ].transform("count")
    portfolio_csv["p_overall"] = portfolio_csv["p_overall"] / portfolio_csv["tree_path"]
    portfolio_csv["p_overall"] *= (1 / portfolio_csv["p_overall"].sum()) * 100
    portfolio_csv.drop(columns="tree_path", inplace=True)
    portfolio_csv = portfolio_csv.sort_values(by="p_overall", ascending=False)
    portfolio_csv.reset_index(drop=True, inplace=True)

    # Return the breakdown of the portfolio
    retrieve_tree_structure(portfolio_csv)

    return


def _name_node(category: str, percentage: float):
    return category + f" ({round(percentage)}%)"


def retrieve_tree_structure(portfolio_csv: pd.DataFrame) -> pd.DataFrame:
    # Intitialize the tree tha tsummarizes the portfolio
    tree = Tree()
    tree.create_node("Portfolio", "portfolio")  # root node

    # Name of the different nodes in the tree
    levels = [c for c in portfolio_csv.columns if c.startswith("L") and c[1:].isdigit()]

    # Add the first layer to the root "portfolio"
    unique_combinations = portfolio_csv[["L1", "p_L1"]].drop_duplicates()
    for _, (child, child_weight) in unique_combinations.iterrows():
        child_name = _name_node(child, child_weight)
        tree.create_node(child_name, child_name, parent="portfolio")

    # Add the other layers
    for i_lv in range(1, len(levels)):
        unique_combinations = (
            portfolio_csv[[f"L{i_lv}", f"p_L{i_lv}", f"L{i_lv+1}", f"p_L{i_lv+1}"]]
            .drop_duplicates()
            .dropna(axis=0)
        )
        for _, (
            parent,
            weigth_parent,
            child,
            weight_child,
        ) in unique_combinations.iterrows():
            parent_name = _name_node(parent, weigth_parent)
            child_name = _name_node(child, weight_child)
            tree.create_node(child_name, child_name, parent=parent_name)

    # Based on the last layer, add the Tags to the tree
    for tag in portfolio_csv["Tag"].unique():
        row_tag = portfolio_csv[portfolio_csv.Tag == tag]
        n_levels = len(
            [
                c
                for c in row_tag.dropna(axis=1).columns
                if c.startswith("L") and c[1:].isdigit()
            ]
        )

        parent_name = _name_node(
            row_tag[f"L{n_levels}"].iloc[0], row_tag[f"p_L{n_levels}"].iloc[0]
        )

        final_tag = f"{tag} - p={row_tag['p_overall'].iloc[0]:.2f}"
        tree.create_node(final_tag, tag, parent=parent_name)

    print("Structure of the theoretical portfolio:")
    print(tree.show(stdout=False))

    return tree
