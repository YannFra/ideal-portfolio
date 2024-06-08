# ideal-portfolio

This project aims at testing a portfolio strategy in hope of finding the ideal one. Upon choosing its components and the importance they should have, the code returns the list of orders that should have been placed now for the portfolio to be created or to be rebalanced if inputed an existing portfolio composition.

> :warning: **This code does not provide financial advice. The provided example is solely to demonstrate how the code functions and should not be regarded as financial advice. This project is intended only for creating hypothetical portfolios and not for executing trades based on the outputs of this code. Use it at your own risk. The creators are not liable for any financial losses resulting from actions taken based on this code. Always consult a qualified financial advisor before making investment decisions.**:

## How does it Work? - a Simple Example

> [!NOTE]
> This repo uses [Poetry](https://python-poetry.org/) to manage dependencies. Once you have Poetry installed, run the following command to install dependencies:
> ```shell
> poetry install
> ```
> And you are good to go!

We propose a simple example to test the code and see its capabilities. Simply run the following command line:
```
poetry run python portfolio.py
```

The structure of the portfolio is described in `_categories.csv`, where each line corresponds to a category and its relative importance in the portfolio structure. In our case, we can see two categories in `_categories.csv`, `crypto` and `stock`, with a respective importance of 30 and 70%. For each category, an associated file needs to be added: `crypto.csv` and `stock.csv` in our case. Each file contains its objects (stocks, ETFs, cryptocurrencies, ...) and their respective importance. As long as the importances sums to 1 and as long as a valid Yahoo Finance tag is provided for each object, the code will run as expected. For your own application, you can define different categories and input different objects, e.g. `offense` and `defense`, or `etf`, `stock`, and `bond`.

The file `_history.csv` is also needed for the repository to work as intended. It contains the purchase and sell history since the creation of the portfolio, and is needed to estimate the existing portfolio positions, and compare them with the theoretical ones defined in `_categories.csv`.

## How to Run the Code for your Own Portfolio?

Simply create your own files in `your_portfolio` and run
```
poetry run python portfolio.py --no-example
```
