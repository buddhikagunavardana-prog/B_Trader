import pandas as pd

from src.tests.trading_framework_test_data import context_for, framework_frame
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext, FrameworkSignal
from src.trading_frameworks.registry import trading_framework_registry


def test_future_rows_cannot_change_historical_decisions():
    for name in (
        "triple_screen_trading", "turtle_trading", "ichimoku_cloud_trading",
        "bollinger_mean_reversion", "donchian_breakout",
    ):
        framework = load_trading_framework(name)
        context = context_for(name, 100)
        role = framework.execution_role
        cutoff = context.frames[role].index[-20]
        before = framework.execute(context, cutoff).to_dict()
        changed = {key: value.copy(deep=True) for key, value in context.frames.items()}
        for frame in changed.values():
            mask = frame.index > cutoff
            frame.loc[mask, :] = 999999.0
        after = framework.execute(FrameworkContext(changed), cutoff).to_dict()
        assert before == after, name


def test_multi_timeframe_alignment_excludes_unfinished_future_screen():
    context = context_for("triple_screen_trading", 100)
    cutoff = context.frames["entry"].index[-1]
    baseline = load_trading_framework("triple_screen").execute(context, cutoff).to_dict()
    trend = context.frames["trend"].copy()
    future = trend.iloc[[-1]].copy()
    future.index = [cutoff + pd.Timedelta(hours=3)]
    future.loc[:, ["close", "EMA", "MACD_HISTOGRAM"]] = [-1000.0, 1000.0, -100.0]
    extended = FrameworkContext({"trend": pd.concat([trend, future]), "setup": context.frames["setup"], "entry": context.frames["entry"]})
    assert load_trading_framework("triple_screen").execute(extended, cutoff).to_dict() == baseline


def test_breakout_uses_prior_channel_not_current_channel():
    frame = framework_frame()
    frame.loc[frame.index[-1], "close"] = frame.iloc[-2]["DONCHIAN_UPPER"] + 1.0
    frame.loc[frame.index[-1], "DONCHIAN_UPPER"] = 1_000_000.0
    decision = load_trading_framework("donchian_breakout").execute(FrameworkContext({"execution": frame}))
    assert decision.signal is FrameworkSignal.BUY


if __name__ == "__main__":
    test_future_rows_cannot_change_historical_decisions()
    test_multi_timeframe_alignment_excludes_unfinished_future_screen()
    test_breakout_uses_prior_channel_not_current_channel()
    print("test_trading_framework_causality passed")
