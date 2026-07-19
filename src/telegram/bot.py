from telegram.ext import Application, CommandHandler

from src.telegram.commands import (
    frameworks_command,
    help_command,
    ping_command,
    start_command,
    status_command,
    version_command,
)
from src.telegram.config import get_bot_token


def create_application() -> Application:
    application = Application.builder().token(get_bot_token()).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(
        CommandHandler("frameworks", frameworks_command)
    )

    return application


def main() -> None:
    app = create_application()

    print("B Trader Telegram Bot Started...")

    app.run_polling()


if __name__ == "__main__":
    main()