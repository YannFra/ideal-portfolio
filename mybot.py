import logging
import os
import asyncio
from datetime import time
import pandas as pd
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

from utils.current_asset_value import (
    provide_breakdown_existing_assets,
    access_current_asset_value,
    exchange_rate,
)
from utils.orders import get_list_of_orders
from utils.format_ideal_portfolio import format_ideal_portfolio
from utils.plot_evolution import compute_total_invested

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_ID = int(os.environ["MY_ID"])
PORTFOLIO_PATH: str = os.getenv("PORTFOLIO_PATH", "example_portfolio/")
CURRENCY: str = os.getenv("CURRENCY", "SGD")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def owner_only(handler):
    """Decorator: ignore anyone who isn't you."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None or user.id != MY_ID:
            logging.warning(f"Blocked message from {user.id if user else 'unknown'}")
            return
        return await handler(update, context)

    return wrapper


def _load_data(cash_influx: float = 0) -> tuple:
    """Load and compute all portfolio data. Runs in a thread (blocking I/O)."""
    portfolio_structure = pd.read_csv(PORTFOLIO_PATH + "_ideal_portfolio.csv")
    format_ideal_portfolio(portfolio_structure)
    access_current_asset_value(portfolio_structure, CURRENCY)

    purchase_history = pd.read_csv(PORTFOLIO_PATH + "_history.csv")
    assets_breakdown = provide_breakdown_existing_assets(
        purchase_history, cash_influx, CURRENCY
    )

    splits = pd.read_csv(PORTFOLIO_PATH + "_split.csv")
    splits["Date"] = pd.to_datetime(splits["Date"], dayfirst=True)

    return portfolio_structure, purchase_history, assets_breakdown, splits


@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Available commands</b>\n"
        "/portfolio — total value and invested cash\n"
        "/breakdown — per-asset breakdown\n"
        "/orders [amount] — rebalancing orders, optional cash injection\n"
        "/structure — ideal portfolio structure\n"
        "/history — last 5 history entries\n"
        "/add ticker unit qty — add an entry to history\n"
        "/currency [code] — show or change currency\n"
        "/path [path] — show or change portfolio path",
        parse_mode="HTML",
    )


@owner_only
async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text(f"Your ID: {u.id}\nName: {u.full_name}")


@owner_only
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Computing portfolio...")

    def _compute():
        _, purchase_history, assets_breakdown, splits = _load_data()
        pv = assets_breakdown[f"position_in_{CURRENCY}"].sum()
        extra = [c for c in ["USD", "SGD", "EUR"] if c != CURRENCY]
        conversions = {c: pv * exchange_rate(CURRENCY, c) for c in extra}
        conversion_str = "  |  ".join(f"{int(v)} {c}" for c, v in conversions.items())
        total_invested = compute_total_invested(
            purchase_history.copy(), CURRENCY, splits=splits
        )
        pct_diff = (pv - total_invested) / total_invested * 100
        return pv, conversion_str, total_invested, pct_diff

    pv, conversion_str, total_invested, pct_diff = await asyncio.to_thread(_compute)

    msg = (
        f"<b>Total value:</b> {int(pv)} {CURRENCY}  |  {conversion_str}\n"
        f"<b>Invested:</b> {int(total_invested)} {CURRENCY}  |  {pct_diff:+.2f}%"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


@owner_only
async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Computing breakdown...")

    def _compute():
        _, _, assets_breakdown, _ = _load_data()
        return assets_breakdown.loc[
            assets_breakdown["p_overall"] != 0,
            ["yf_name", f"position_in_{CURRENCY}", "p_overall"],
        ]

    breakdown_df = await asyncio.to_thread(_compute)

    rows = "\n".join(
        f"{row['yf_name']}: {int(row[f'position_in_{CURRENCY}'])} {CURRENCY} ({row['p_overall']:.2f}%)"
        for _, row in breakdown_df.iterrows()
    )
    await update.message.reply_text(f"<b>Breakdown</b>\n{rows}", parse_mode="HTML")


@owner_only
async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cash_influx = float(context.args[0]) if context.args else 0
    except ValueError:
        await update.message.reply_text("Usage: /orders [amount]  e.g. /orders 10000")
        return

    await update.message.reply_text("Computing orders...")

    def _compute():
        portfolio_structure, _, assets_breakdown, _ = _load_data(cash_influx)
        return get_list_of_orders(assets_breakdown, portfolio_structure, CURRENCY)

    orders_df = await asyncio.to_thread(_compute)

    rows = "\n".join(
        f"{row['yf_name']}: {int(row['order_in_shares']):+} shares, {int(row[f'order_in_{CURRENCY}']):+} {CURRENCY} ({row['p_real']:.2f}% → {row['p_desired']:.2f}%)"
        for _, row in orders_df.iterrows()
    )
    msg = f"<b>Rebalancing orders</b>\n{rows}"
    await update.message.reply_text(msg, parse_mode="HTML")


@owner_only
async def structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def _compute():
        portfolio_structure = pd.read_csv(PORTFOLIO_PATH + "_ideal_portfolio.csv")
        return format_ideal_portfolio(portfolio_structure)

    tree_str = await asyncio.to_thread(_compute)
    await update.message.reply_text(tree_str)


@owner_only
async def path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PORTFOLIO_PATH
    if not context.args:
        await update.message.reply_text(f"Portfolio path: {PORTFOLIO_PATH}")
        return
    PORTFOLIO_PATH = context.args[0].rstrip("/") + "/"
    await update.message.reply_text(f"Portfolio path set to {PORTFOLIO_PATH}")


@owner_only
async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENCY
    if not context.args:
        await update.message.reply_text(f"Default currency: {CURRENCY}")
        return
    CURRENCY = context.args[0].upper()
    await update.message.reply_text(f"Currency set to {CURRENCY}")


@owner_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text(
            "Usage: /add <ticker> <unit> <quantity>\ne.g. /add NVDA USD 5"
        )
        return
    ticker, unit, quantity_str = context.args
    try:
        quantity = float(quantity_str)
    except ValueError:
        await update.message.reply_text("Quantity must be a number.")
        return

    date = update.message.date.strftime("%d/%m/%y")
    history_path = PORTFOLIO_PATH + "_history.csv"
    history = pd.read_csv(history_path)
    new_row = pd.DataFrame(
        [
            {
                "Date": date,
                "yf_name": ticker.upper(),
                "Unit": unit.upper(),
                "Quantity": quantity,
            }
        ]
    )
    pd.concat([history, new_row], ignore_index=True).to_csv(history_path, index=False)

    await update.message.reply_text(
        f"Added: {ticker.upper()} {quantity:+g} {unit.upper()} on {date}"
    )


@owner_only
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_csv(PORTFOLIO_PATH + "_history.csv").tail(5)
    rows = "\n".join(
        f"{row['Date']}  {row['yf_name']}: {row['Quantity']:+g} {row['Unit']}"
        for _, row in df.iterrows()
    )
    await update.message.reply_text(f"<b>Last 5 entries</b>\n{rows}", parse_mode="HTML")


async def daily_portfolio(context: ContextTypes.DEFAULT_TYPE):
    def _compute():
        _, purchase_history, assets_breakdown, splits = _load_data()
        pv = assets_breakdown[f"position_in_{CURRENCY}"].sum()
        extra = [c for c in ["USD", "SGD", "EUR"] if c != CURRENCY]
        conversions = {c: pv * exchange_rate(CURRENCY, c) for c in extra}
        conversion_str = "  |  ".join(f"{int(v)} {c}" for c, v in conversions.items())
        total_invested = compute_total_invested(
            purchase_history.copy(), CURRENCY, splits=splits
        )
        pct_diff = (pv - total_invested) / total_invested * 100
        return pv, conversion_str, total_invested, pct_diff

    pv, conversion_str, total_invested, pct_diff = await asyncio.to_thread(_compute)
    await context.bot.send_message(
        chat_id=MY_ID,
        text=(
            f"<b>Weekly portfolio</b>\n"
            f"<b>Total value:</b> {int(pv)} {CURRENCY}  |  {conversion_str}\n"
            f"<b>Invested:</b> {int(total_invested)} {CURRENCY}  |  {pct_diff:+.2f}%"
        ),
        parse_mode="HTML",
    )


async def daily_orders(context: ContextTypes.DEFAULT_TYPE):
    def _compute():
        portfolio_structure, _, assets_breakdown, _ = _load_data()
        return get_list_of_orders(assets_breakdown, portfolio_structure, CURRENCY)

    orders_df = await asyncio.to_thread(_compute)
    rows = "\n".join(
        f"{row['yf_name']}: {int(row['order_in_shares']):+} shares, {int(row[f'order_in_{CURRENCY}']):+} {CURRENCY} ({row['p_real']:.2f}% → {row['p_desired']:.2f}%)"
        for _, row in orders_df.iterrows()
    )
    await context.bot.send_message(
        chat_id=MY_ID,
        text=f"<b>Daily orders</b>\n{rows}",
        parse_mode="HTML",
    )


@owner_only
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("breakdown", breakdown))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CommandHandler("structure", structure))
    app.add_handler(CommandHandler("currency", currency))
    app.add_handler(CommandHandler("path", path))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.job_queue.run_daily(
        daily_orders, time=time(10, 0), days=(0, 1, 2, 3, 4)
    )  # 6pm SGT = 10:00 UTC, weekdays only
    app.job_queue.run_daily(
        daily_portfolio, time=time(10, 0), days=(6,)
    )  # 6pm SGT = 10:00 UTC, Sunday only
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
