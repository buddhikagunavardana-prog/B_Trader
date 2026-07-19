import os


def get_bot_token() -> str:
    token = os.getenv("BTRADER_TELEGRAM_TOKEN")

    if not token:
        raise RuntimeError(
            "Environment variable 'BTRADER_TELEGRAM_TOKEN' is not set."
        )

    return token