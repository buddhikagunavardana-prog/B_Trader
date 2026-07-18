from src.tests.framework_expansion_test_data import config, data
from src.trading_frameworks.loader import load_trading_framework
from src.trading_frameworks.models import FrameworkContext
from src.utils.trading_framework_performance import _context


NEW_15 = (
    "elder_impulse_system", "connors_rsi_mean_reversion", "stochastic_pullback_trend",
    "williams_r_reversal", "cci_trend_pullback", "chandelier_exit_trend",
    "price_channel_trend", "heikin_ashi_trend", "aroon_trend",
    "momentum_acceleration_breakout", "volume_expansion_breakout",
    "nr4_nr7_volatility_breakout", "pin_bar_rejection",
    "engulfing_confirmation_trend", "pivot_range_breakout",
)


def run_framework_contract(name):
    framework = load_trading_framework(name)
    source = data(name)
    snapshots = {role: frame.copy(deep=True) for role, frame in source.items()}
    first = framework.execute(FrameworkContext(source))
    second = framework.execute(FrameworkContext(source))
    assert first.to_dict() == second.to_dict()
    assert all(source[role].equals(snapshot) for role, snapshot in snapshots.items())
    assert 0 <= first.confidence <= 1
    assert first.framework == name and first.framework_version == "1.0.0"
    try:
        load_trading_framework(name, {"unknown_parameter": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown parameter accepted")


def directional_scenario(name, side):
    frame = _context(name, 140).frames["execution"].copy(deep=True)
    q, p, r = frame.index[-3], frame.index[-2], frame.index[-1]
    bullish = side == "long"
    if name == "elder_impulse_system":
        frame.loc[[q,p,r],"EMA"]=[101,100,102] if bullish else [100,101,99]; frame.loc[[q,p,r],"MACD_HISTOGRAM"]=[1,0,2] if bullish else [0,1,-1]; frame.loc[r,"ADX"]=30
    elif name == "connors_rsi_mean_reversion":
        frame.loc[p:r,"CONNORS_RSI"]=[5,15] if bullish else [95,85]; frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1)
    elif name == "stochastic_pullback_trend":
        frame.loc[frame.index[-6]:p,"STOCHASTIC_K"]=20 if bullish else 80; frame.loc[p:r,"STOCHASTIC_K"]=[10,30] if bullish else [90,70]; frame.loc[p:r,"STOCHASTIC_D"]=[20,20] if bullish else [80,80]; frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1);frame.loc[r,"ADX"]=30
    elif name == "williams_r_reversal":
        frame.loc[frame.index[-6]:p,"WILLIAMS_R"]=-90 if bullish else -10; frame.loc[p:r,"WILLIAMS_R"]=[-80,-60] if bullish else [-20,-40]; frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1)
    elif name == "cci_trend_pullback":
        frame.loc[frame.index[-6]:p,"CCI"]=-120 if bullish else 120; frame.loc[p:r,"CCI"]=[-80,0] if bullish else [80,0]; frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1);frame.loc[r,"ADX"]=30
    elif name == "chandelier_exit_trend":
        if bullish: frame.loc[q,"CHANDELIER_LONG"]=frame.loc[p,"close"]+10;frame.loc[p,"CHANDELIER_LONG"]=frame.loc[r,"close"]-1;frame.loc[r,"EMA"]=frame.loc[r,"close"]-1
        else: frame.loc[q,"CHANDELIER_SHORT"]=frame.loc[p,"close"]-10;frame.loc[p,"CHANDELIER_SHORT"]=frame.loc[r,"close"]+1;frame.loc[r,"EMA"]=frame.loc[r,"close"]+1
    elif name in {"price_channel_trend","momentum_acceleration_breakout","volume_expansion_breakout"}:
        if bullish: frame.loc[p,"PRICE_CHANNEL_UPPER"]=frame.loc[p,"close"]+1;frame.loc[r,"close"]=frame.loc[p,"close"]+2;frame.loc[r,"EMA"]=frame.loc[r,"close"]-1
        else: frame.loc[p,"PRICE_CHANNEL_LOWER"]=frame.loc[p,"close"]-1;frame.loc[r,"close"]=frame.loc[p,"close"]-2;frame.loc[r,"EMA"]=frame.loc[r,"close"]+1
        if name=="momentum_acceleration_breakout": frame.loc[p:r,"ROC"]=[1,3] if bullish else [-1,-3];frame.loc[p:r,"MOMENTUM"]=[1,3] if bullish else [-1,-3]
        if name=="volume_expansion_breakout": frame.loc[p,"VOLUME_SMA"]=1000;frame.loc[r,"volume"]=2000
    elif name == "heikin_ashi_trend":
        frame.loc[p,["HA_OPEN","HA_CLOSE"]]=[101,100] if bullish else [100,101]; frame.loc[r,["HA_OPEN","HA_CLOSE"]]=[100,101] if bullish else [101,100];frame.loc[r,"HA_LOW"]=100 if bullish else 99;frame.loc[r,"HA_HIGH"]=102 if bullish else 101;frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1);frame.loc[r,"ADX"]=30
    elif name == "aroon_trend":
        frame.loc[p,["AROON_UP","AROON_DOWN"]]=[50,50];frame.loc[r,["AROON_UP","AROON_DOWN"]]=[80,20] if bullish else [20,80];frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1)
    elif name == "nr4_nr7_volatility_breakout":
        frame.loc[p,"NR4"]=True;frame.loc[r,"close"]=frame.loc[p,"high"]+1 if bullish else frame.loc[p,"low"]-1
    elif name == "pin_bar_rejection":
        if bullish: frame.loc[r,["open","high","low","close","SUPPORT","RESISTANCE","ATR"]]=[100,100.3,98,100.2,98,105,1]
        else: frame.loc[r,["open","high","low","close","SUPPORT","RESISTANCE","ATR"]]=[100,102,99.7,99.8,95,102,1]
    elif name == "engulfing_confirmation_trend":
        frame.loc[r,"bullish_engulfing"]=bullish;frame.loc[r,"bearish_engulfing"]=not bullish;frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1);frame.loc[r,"ADX"]=30
    elif name == "pivot_range_breakout":
        level=frame.loc[p,"close"]+(1 if bullish else -1);frame.loc[[p,r],"PRIOR_PIVOT_R1" if bullish else "PRIOR_PIVOT_S1"]=level;frame.loc[r,"close"]=level+(1 if bullish else -1);frame.loc[r,"EMA"]=frame.loc[r,"close"]+(-1 if bullish else 1)
    return FrameworkContext({"execution":frame})
