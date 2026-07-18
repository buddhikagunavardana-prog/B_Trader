from __future__ import annotations

import inspect
import json
from pathlib import Path

import pandas as pd

from src.indicators.registry import indicator_registry


REPORT_PATH = Path("reports/indicator_framework_inventory.csv")

PHASE_23_3 = {
    "accelerator_oscillator", "schaff_trend_cycle", "kst", "smi_ergodic",
    "demarker", "qstick", "relative_vigor_index", "center_of_gravity",
    "chande_forecast_oscillator", "pretty_good_oscillator",
    "stochastic_momentum_index", "psychological_line", "rainbow_oscillator",
    "true_range", "volatility_stop", "atr_bands", "fractal_chaos_bands",
    "moving_std_channel", "donchian_width", "keltner_width",
    "parkinson_volatility", "garman_klass_volatility", "klinger_oscillator",
    "price_volume_trend", "volume_oscillator", "twiggs_money_flow",
    "volume_weighted_macd", "intraday_intensity_index", "money_flow_volume",
    "volume_zone_oscillator", "net_volume", "vwap_deviation",
    "money_flow_oscillator",
}

PHASE_23_4 = {
    "t3_moving_average", "jurik_moving_average_approximation",
    "double_smoothed_ema", "triple_smoothed_ema", "gaussian_moving_average",
    "ehlers_super_smoother", "ehlers_roofing_filter",
    "sine_weighted_moving_average", "dynamic_momentum_index", "laguerre_rsi",
    "inverse_fisher_rsi", "correlation_trend_indicator",
    "trend_trigger_factor", "wavetrend_oscillator", "squeeze_momentum",
    "cycle_identifier", "rogers_satchell_volatility", "yang_zhang_volatility",
    "close_to_close_volatility", "median_absolute_deviation",
    "average_daily_range", "relative_average_true_range",
    "coefficient_of_variation", "inverse_fair_value_gap", "liquidity_sweep",
    "equal_highs", "equal_lows", "breaker_block",
}

DISPLAY_NAMES = {
    "kst": "Know Sure Thing (KST)",
    "smi_ergodic": "SMI Ergodic",
    "relative_vigor_index": "Relative Vigor Index",
    "chande_forecast_oscillator": "Chande Forecast Oscillator",
    "pretty_good_oscillator": "Pretty Good Oscillator",
    "atr_bands": "ATR Bands",
    "vwap_deviation": "VWAP Deviation",
    "volume_weighted_macd": "Volume Weighted MACD",
    "t3_moving_average": "T3 Moving Average",
    "jurik_moving_average_approximation": "Jurik Moving Average Approximation",
    "ehlers_super_smoother": "Ehlers Super Smoother",
    "ehlers_roofing_filter": "Ehlers Roofing Filter",
    "wavetrend_oscillator": "WaveTrend Oscillator",
    "relative_average_true_range": "Relative Average True Range",
}

NOTES = {
    "elder_ray_index": "Canonical mapping for requested Elder Ray Index.",
    "ppo": "PPO_HISTOGRAM maps the requested standalone PPO Histogram.",
    "standard_deviation": "Canonical mapping for requested Standard Deviation.",
    "price_channels": "Canonical mapping for requested Price Channel.",
    "force_index": "Canonical mapping for Elder Force Index with standard EMA smoothing.",
    "klinger_oscillator": "Canonical mapping for Klinger Oscillator and Klinger Volume Oscillator.",
    "price_volume_trend": "Canonical mapping for Price Volume Trend and Volume Price Trend (VPT).",
    "psychological_line": "Momentum replacement for the mapped Elder Ray request.",
    "rainbow_oscillator": "Momentum replacement for the mapped PPO Histogram request.",
    "parkinson_volatility": "Volatility replacement for mapped Standard Deviation.",
    "garman_klass_volatility": "Volatility replacement for mapped Price Channel.",
    "net_volume": "Volume replacement for the duplicate VPT naming request.",
    "vwap_deviation": "Volume replacement for the duplicate Klinger naming request.",
    "money_flow_oscillator": "Volume replacement for mapped Elder Force Index.",
    "fair_value_gap": "Experimental causal three-candle approximation.",
    "order_block": "Experimental causal prior-candle approximation.",
    "market_structure": "Experimental causal BOS/CHoCH approximation.",
    "linear_regression_trend": "Canonical mapping for Least Squares Moving Average (LSMA).",
    "zscore": "Canonical mapping for requested Z-Score.",
    "sine_weighted_moving_average": "Trend replacement for mapped Least Squares Moving Average.",
    "coefficient_of_variation": "Statistical replacement for mapped Z-Score.",
    "jurik_moving_average_approximation": "Experimental volatility-adaptive approximation; not a proprietary JMA implementation.",
    "ehlers_super_smoother": "Experimental causal two-pole filter approximation.",
    "ehlers_roofing_filter": "Experimental causal high-pass plus smoothing approximation.",
    "cycle_identifier": "Experimental lag-autocorrelation cycle-strength approximation.",
    "inverse_fair_value_gap": "Experimental event when a confirmed FVG is later closed through; no persistent zone.",
    "liquidity_sweep": "Experimental event at wick rejection of a previously confirmed swing level.",
    "equal_highs": "Experimental event confirmed after the swing right-side delay; tolerance-based level match.",
    "equal_lows": "Experimental event confirmed after the swing right-side delay; tolerance-based level match.",
    "breaker_block": "Experimental event when a prior order-block approximation is invalidated with confirmed structure.",
}


def build_indicator_inventory() -> pd.DataFrame:
    """Build a registry-backed, deterministic indicator inventory."""
    previous: dict[str, dict] = {}
    if REPORT_PATH.exists():
        frame = pd.read_csv(REPORT_PATH).fillna("")
        if "Canonical Name" in frame.columns:
            previous = {
                row["Canonical Name"]: row.to_dict()
                for _, row in frame.iterrows()
            }

    rows = []
    root = Path.cwd().resolve()
    for number, name in enumerate(indicator_registry.list_names(), start=1):
        definition = indicator_registry.get(name)
        source = Path(inspect.getsourcefile(definition["callable"]) or "")
        try:
            source_text = source.resolve().relative_to(root).as_posix()
        except ValueError:
            source_text = source.as_posix()
        old = previous.get(name, {})
        display = DISPLAY_NAMES.get(
            name,
            str(old.get("Display Name") or name.replace("_", " ").title()),
        )
        stability = definition["stability"].title()
        rows.append({
            "Number": number,
            "Canonical Name": name,
            "Display Name": display,
            "Category": definition["category"].replace("_", " ").title(),
            "Status": (
                "Added Phase 23.4" if name in PHASE_23_4
                else "Added Phase 23.3" if name in PHASE_23_3
                else str(old.get("Status") or "Existing")
            ),
            "Source File": source_text,
            "Registered": "Yes",
            "Tested": "Phase 23.5 Release Gate",
            "Required Columns": "; ".join(definition["required_columns"]),
            "Output Columns": "; ".join(definition["output_columns"]),
            "Default Parameters": json.dumps(definition["default_parameters"], sort_keys=True),
            "Dependencies": "; ".join(definition["dependencies"]),
            "Stability": stability,
            "Notes": NOTES.get(name, str(old.get("Notes") or "")),
        })
    return pd.DataFrame(rows)


def write_indicator_inventory(path: Path = REPORT_PATH) -> Path:
    """Write the current registry inventory as UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    build_indicator_inventory().to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_indicator_inventory())
