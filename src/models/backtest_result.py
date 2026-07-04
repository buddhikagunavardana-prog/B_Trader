from dataclasses import dataclass, field


@dataclass
class BacktestResult:
    initial_balance: float
    final_balance: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    roi_pct: float

    total_trades: int
    wins: int
    losses: int
    win_rate: float

    total_pnl_pct: float
    profit_factor: float
    total_fees: float = 0.0

    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    expectancy: float = 0.0

    trades: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)

    def to_dict(self):
        return {
            "initial_balance": round(self.initial_balance, 2),
            "final_balance": round(self.final_balance, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "net_profit": round(self.net_profit, 2),
            "roi_pct": round(self.roi_pct, 2),
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "profit_factor": round(self.profit_factor, 2),
            "total_fees": round(self.total_fees, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "expectancy": round(self.expectancy, 2),
            "trades": self.trades,
            "equity_curve": self.equity_curve,
        }