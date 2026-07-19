from telegram import Update
from telegram.ext import ContextTypes

from src.telegram.formatter import format_status


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to B Trader Assistant!\n\n"
        "Type /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start\n"
        "/help\n"
        "/status"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_status())


async def ping_command(update, context):
    await update.message.reply_text(
        "🏓 Pong\n\n"
        "Server : Online"
    )


async def version_command(update, context):
    await update.message.reply_text(
        "B Trader\n\n"
        "Version : 0.02\n"
        "Phase : 26.2"
    )


async def frameworks_command(update, context):
    await update.message.reply_text(
        "Loaded Frameworks\n\n"
        "SMC\n"
        "Trend Following\n"
        "Momentum\n"
        "Mean Reversion\n"
        "...\n"
        "Total : 50"
    )