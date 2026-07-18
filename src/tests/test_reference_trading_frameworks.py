from src.tests.trading_framework_test_data import context_for, framework_frame
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext, FrameworkDirection, FrameworkSignal


def test_reference_frameworks_emit_expected_entry_decisions():
    expected = {
        "triple_screen_trading": FrameworkSignal.BUY,
        "turtle_trading": FrameworkSignal.BUY,
        "ichimoku_cloud_trading": FrameworkSignal.BUY,
        "bollinger_mean_reversion": FrameworkSignal.BUY,
        "donchian_breakout": FrameworkSignal.BUY,
    }
    for name, signal in expected.items():
        decision = load_trading_framework(name).execute(context_for(name))
        assert decision.signal is signal, (name, decision.to_dict())
        assert decision.risk.risk_fraction is not None
        assert "order" not in decision.to_dict()


def test_reference_exit_rules_use_supplied_position_state():
    frame = framework_frame()
    frame.loc[frame.index[-1], "close"] = frame.iloc[-1]["BOLLINGER_MIDDLE"] + 1
    decision = load_trading_framework("bollinger_mean_reversion").execute(
        FrameworkContext({"execution": frame}, FrameworkDirection.LONG),
    )
    assert decision.signal is FrameworkSignal.EXIT_LONG


def test_long_short_range_breakout_false_break_and_gap_scenarios():
    # Bearish rally across Triple Screen's three completed screens.
    triple = context_for("triple_screen_trading")
    trend = triple.frames["trend"].copy(); setup = triple.frames["setup"].copy(); entry = triple.frames["entry"].copy()
    trend.loc[trend.index[-1], ["close", "EMA", "MACD_HISTOGRAM"]] = [90.0, 100.0, -1.0]
    setup.loc[setup.index[-1], ["RSI", "STOCHASTIC_K", "FORCE_INDEX"]] = [75.0, 80.0, -1.0]
    entry.loc[entry.index[-1], "close"] = entry.iloc[-2]["low"] - 1.0
    bearish = load_trading_framework("triple_screen").execute(FrameworkContext({"trend": trend, "setup": setup, "entry": entry}))
    assert bearish.signal is FrameworkSignal.SELL

    # Sideways/range extreme is handled by the mean-reversion framework.
    assert load_trading_framework("bollinger_mean_reversion").execute(context_for("bollinger_mean_reversion")).signal is FrameworkSignal.BUY

    # A nominal channel break without volume is a predictable false-break rejection.
    false_break = context_for("donchian_breakout").frames["execution"].copy()
    false_break.loc[false_break.index[-1], "volume"] = false_break.iloc[-1]["VOLUME_SMA"] / 2
    rejected = load_trading_framework("donchian_breakout").execute(FrameworkContext({"execution": false_break}))
    assert rejected.signal is FrameworkSignal.NO_TRADE and rejected.warnings

    # A completed gap beyond the prior channel remains a structured volatility-breakout decision.
    gap = context_for("donchian_breakout").frames["execution"].copy()
    gap.loc[gap.index[-1], ["open", "close", "high"]] = [130.0, 131.0, 132.0]
    assert load_trading_framework("donchian_breakout").execute(FrameworkContext({"execution": gap})).signal is FrameworkSignal.BUY

    # Zero-volatility risk data never produces non-finite stop/target levels.
    quiet = context_for("turtle_trading").frames["execution"].copy()
    quiet.loc[quiet.index[-1], "ATR"] = 0.0
    quiet_decision = load_trading_framework("turtle").execute(FrameworkContext({"execution": quiet}))
    assert quiet_decision.risk.stop_loss is None and quiet_decision.risk.take_profit is None


if __name__ == "__main__":
    test_reference_frameworks_emit_expected_entry_decisions()
    test_reference_exit_rules_use_supplied_position_state()
    test_long_short_range_breakout_false_break_and_gap_scenarios()
    print("test_reference_trading_frameworks passed")
