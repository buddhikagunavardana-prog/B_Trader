import pandas as pd


SCORE_WEIGHTS = {
    "roi": 25,
    "profit_factor": 20,
    "win_rate": 15,
    "max_drawdown": 15,
    "trade_count": 10,
    "expectancy": 10,
    "stability": 5,
}

NORMALIZATION_LIMITS = {
    "roi_target": 50,
    "profit_factor_target": 2,
    "win_rate_target": 60,
    "max_drawdown_limit": 40,
    "trade_count_target": 200,
    "expectancy_target": 20,
}


class StrategyScoringEngine:
    def __init__(
        self,
        weights: dict | None = None,
        limits: dict | None = None,
    ):
        self.weights = weights or SCORE_WEIGHTS
        self.limits = limits or NORMALIZATION_LIMITS

    def _positive_score(self, value, target) -> float:
        if pd.isna(value):
            return 0.0

        return float(max(0, min(float(value), target)) / target * 100)

    def _drawdown_score(self, value) -> float:
        if pd.isna(value):
            return 0.0

        drawdown = abs(float(value))
        limit = self.limits["max_drawdown_limit"]

        return float((1 - min(drawdown, limit) / limit) * 100)

    def _stability_score(self, row) -> float:
        drawdown_score = self._drawdown_score(row["Max Drawdown %"])
        trade_score = self._positive_score(
            row["Trades"],
            self.limits["trade_count_target"],
        )
        profit_factor_score = self._positive_score(
            row["Profit Factor"],
            self.limits["profit_factor_target"],
        )
        roi_score = self._positive_score(
            row["ROI %"],
            self.limits["roi_target"],
        )

        return (
            drawdown_score * 0.40
            + trade_score * 0.25
            + profit_factor_score * 0.20
            + roi_score * 0.15
        )

    def score_row(self, row) -> dict:
        scores = {
            "ROI Score": self._positive_score(
                row["ROI %"],
                self.limits["roi_target"],
            ),
            "Profit Factor Score": self._positive_score(
                row["Profit Factor"],
                self.limits["profit_factor_target"],
            ),
            "Win Rate Score": self._positive_score(
                row["Win Rate %"],
                self.limits["win_rate_target"],
            ),
            "Max Drawdown Score": self._drawdown_score(row["Max Drawdown %"]),
            "Trade Count Score": self._positive_score(
                row["Trades"],
                self.limits["trade_count_target"],
            ),
            "Expectancy Score": self._positive_score(
                row["Expectancy"],
                self.limits["expectancy_target"],
            ),
        }
        scores["Stability Score"] = self._stability_score(row)

        final_score = (
            scores["ROI Score"] * self.weights["roi"]
            + scores["Profit Factor Score"] * self.weights["profit_factor"]
            + scores["Win Rate Score"] * self.weights["win_rate"]
            + scores["Max Drawdown Score"] * self.weights["max_drawdown"]
            + scores["Trade Count Score"] * self.weights["trade_count"]
            + scores["Expectancy Score"] * self.weights["expectancy"]
            + scores["Stability Score"] * self.weights["stability"]
        ) / sum(self.weights.values())

        scores["Final Score"] = round(final_score, 2)
        scores["Stability Score"] = round(scores["Stability Score"], 2)

        return scores

    def score_report(self, report: pd.DataFrame) -> pd.DataFrame:
        scored_report = report.copy()
        score_rows = scored_report.apply(self.score_row, axis=1)
        score_df = pd.DataFrame(score_rows.tolist(), index=scored_report.index)

        return pd.concat([scored_report, score_df], axis=1)
