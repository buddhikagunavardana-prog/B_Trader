import pytest

from src.research.frameworks.historical.campaign.aggregation import enforce_structural_schema


@pytest.mark.parametrize("field", ["PnL", "ROI", "win_rate", "profit_factor", "drawdown", "Sharpe", "framework_score", "rank", "winner", "best framework", "recommendation"])
def test_prohibited_profitability_and_ranking_fields_are_rejected(field):
    with pytest.raises(ValueError, match="prohibited fields"):
        enforce_structural_schema({field: 1})


def test_allowed_structural_fields_are_accepted():
    enforce_structural_schema({"framework_name": "ema_ribbon_trend", "valid_row_count": 10, "direction_counts": {"long": 1}})
