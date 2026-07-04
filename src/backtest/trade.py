from dataclasses import dataclass


@dataclass
class Trade:
    symbol: str
    side: str
    entry_price: float
    exit_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    result: str = ""
    pnl_percent: float = 0.0