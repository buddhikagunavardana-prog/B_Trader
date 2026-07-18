from __future__ import annotations

from typing import Any, Mapping
from dataclasses import dataclass
import json,hashlib

import numpy as np
import pandas as pd

from src.indicators.registry import indicator_registry
from src.research.frameworks.exceptions import ResearchPreparationError
from src.research.frameworks.models import FrameworkResearchConfiguration, PreparedTimeframeData, PreparationMode
from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.utilities.timeframe import validate_completed_bar_frame

@dataclass(frozen=True)
class IndicatorRequest:
    canonical_name:str;parameters:Mapping[str,Any];output_alias:str;component:str|None=None
    @property
    def fingerprint(self):return hashlib.sha256(json.dumps({"name":self.canonical_name,"parameters":dict(self.parameters)},sort_keys=True).encode()).hexdigest()[:12]

def compute_indicator_requests(frame:pd.DataFrame,requests:tuple[IndicatorRequest,...]):
    aliases=set();fingerprints={};provenance=[]
    for request in requests:
        if request.output_alias in aliases:raise ResearchPreparationError(f"duplicate output alias: {request.output_alias}")
        aliases.add(request.output_alias);definition=indicator_registry.get(request.canonical_name);indicator_registry.validate_parameters(request.canonical_name,dict(request.parameters));outputs=definition["output_columns"]
        if request.output_alias in frame.columns:raise ResearchPreparationError(f"output collision: {request.output_alias}")
        if request.fingerprint not in fingerprints:fingerprints[request.fingerprint]=indicator_registry.calculate(request.canonical_name,frame,dict(request.parameters))
        result=fingerprints[request.fingerprint]
        if len(outputs)==1:value=result
        else:
            if request.component not in outputs:raise ResearchPreparationError(f"multi-output request requires a valid component: {request.canonical_name}")
            position=outputs.index(request.component)
            if isinstance(result,pd.DataFrame):value=result[request.component]
            elif isinstance(result,dict):value=result[request.component]
            elif isinstance(result,(tuple,list)):value=result[position]
            else:raise ResearchPreparationError(f"unsupported multi-output result: {request.canonical_name}")
        frame[request.output_alias]=value
        provenance.append({"canonical_indicator":request.canonical_name,"parameter_fingerprint":request.fingerprint,"output_alias":request.output_alias,"component":request.component or outputs[0],"actual_output_columns":[request.output_alias],"source":"indicator_registry","status":"computed","first_valid_row":int(frame[request.output_alias].first_valid_index() is not None)})
    frame.attrs.setdefault("indicator_request_provenance",[]).extend(provenance)
    return provenance


def _record_derived(frame,name,outputs,parameters):
    fingerprint=hashlib.sha256(json.dumps({"name":name,"parameters":parameters},sort_keys=True).encode()).hexdigest()[:12]
    frame.attrs.setdefault("indicator_request_provenance",[]).append({"canonical_indicator":name,"parameter_fingerprint":fingerprint,"output_aliases":list(outputs),"actual_output_columns":list(outputs),"source":"causal_preparation","status":"computed"})


def _request_missing(frame, name, parameters, aliases):
    return tuple(IndicatorRequest(name,parameters,alias,component) for component,alias in aliases if alias not in frame.columns)


def _compute_heikin_ashi(frame):
    close=(frame["open"]+frame["high"]+frame["low"]+frame["close"])/4.0
    open_values=pd.Series(index=frame.index,dtype=float)
    if len(frame):
        open_values.iloc[0]=(frame["open"].iloc[0]+frame["close"].iloc[0])/2.0
        for index in range(1,len(frame)):open_values.iloc[index]=(open_values.iloc[index-1]+close.iloc[index-1])/2.0
    frame["HA_OPEN"]=open_values;frame["HA_CLOSE"]=close
    frame["HA_HIGH"]=pd.concat([frame["high"],open_values,close],axis=1).max(axis=1)
    frame["HA_LOW"]=pd.concat([frame["low"],open_values,close],axis=1).min(axis=1)


def _compute_nr_setups(frame):
    candle_range=frame["high"]-frame["low"]
    frame["NR4"]=(candle_range<=candle_range.rolling(4).min()).fillna(False)
    frame["NR7"]=(candle_range<=candle_range.rolling(7).min()).fillna(False)


def _compute_prior_session_pivots(frame,session_configuration):
    values=dict(session_configuration or {});timezone=values.get("timezone","UTC");start=values.get("start","00:00")
    local=frame.index.tz_convert(timezone);hour,minute=map(int,start.split(":"));boundary=local.normalize()+pd.Timedelta(hours=hour,minutes=minute)
    labels=boundary.where(local>=boundary,boundary-pd.Timedelta(days=1))
    grouped=frame.groupby(labels).agg({"high":"max","low":"min","close":"last"})
    previous=grouped.shift(1);pivot=(previous.high+previous.low+previous.close)/3.0
    r1=2*pivot-previous.low;s1=2*pivot-previous.high
    mapping=pd.Series(grouped.index.astype(str),index=grouped.index).shift(1)
    frame["PRIOR_PIVOT"]=pd.Series(labels,index=frame.index).map(pivot)
    frame["PRIOR_PIVOT_R1"]=pd.Series(labels,index=frame.index).map(r1)
    frame["PRIOR_PIVOT_S1"]=pd.Series(labels,index=frame.index).map(s1)
    frame["PRIOR_SESSION_ID"]=pd.Series(labels,index=frame.index).map(mapping).fillna("UNAVAILABLE")


def _attach(frame: pd.DataFrame, output: Any, columns: tuple[str, ...]) -> None:
    if isinstance(output, pd.Series):
        frame[columns[0]] = output
    elif isinstance(output, pd.DataFrame):
        for column in columns:
            frame[column] = output[column]
    elif isinstance(output, (tuple, list)):
        for column, value in zip(columns, output):
            frame[column] = value
    elif isinstance(output, dict):
        for column, value in zip(columns, output.values()):
            frame[column] = value
    else:
        raise ResearchPreparationError(f"unsupported indicator output: {type(output)!r}")


def _compute_missing(frame: pd.DataFrame, framework: BaseTradingFramework, role: str, configuration=None) -> list[str]:
    computed: list[str] = []
    required = set(framework.schema.required_columns_by_role[role])
    if framework.metadata.name=="ema_ribbon_trend":
        requests=tuple(IndicatorRequest("ema",{"period":period},f"EMA_{period}") for period in (8,13,21,34,55) if f"EMA_{period}" not in frame.columns)
        if requests:compute_indicator_requests(frame,requests);computed.extend(r.output_alias for r in requests)
    if framework.metadata.name=="dual_moving_average_crossover":
        requests=tuple(IndicatorRequest("ema",{"period":framework.parameters[key]},alias) for key,alias in (("fast_period","EMA_FAST"),("slow_period","EMA_SLOW")) if alias not in frame.columns)
        if requests:compute_indicator_requests(frame,requests);computed.extend(r.output_alias for r in requests)
    p=framework.parameters;name=framework.metadata.name;requests=[]
    request_specs={
        "elder_impulse_system":(("ema",{"period":p.get("ema_period",13)},(("EMA","EMA"),)),("macd",{"fast":p.get("fast_period",12),"slow":p.get("slow_period",26),"signal":p.get("signal_period",9)},(("MACD_HISTOGRAM","MACD_HISTOGRAM"),)),("atr",{"period":p.get("atr_period",14)},(("ATR","ATR"),))),
        "connors_rsi_mean_reversion":(("connors_rsi",{"rsi_period":p.get("rsi_period",3),"streak_period":p.get("streak_period",2),"rank_period":p.get("rank_period",100),"source":"close"},(("CONNORS_RSI","CONNORS_RSI"),)),("ema",{"period":p.get("trend_ema_period",200)},(("EMA","EMA"),))),
        "stochastic_pullback_trend":(("stochastic",{"k_period":p.get("k_period",14),"d_period":p.get("d_period",3)},(("STOCHASTIC_K","STOCHASTIC_K"),("STOCHASTIC_D","STOCHASTIC_D"))),),
        "williams_r_reversal":(("williams_r",{"period":p.get("williams_period",14)},(("WILLIAMS_R","WILLIAMS_R"),)),),
        "cci_trend_pullback":(("cci",{"period":p.get("cci_period",20)},(("CCI","CCI"),)),),
        "chandelier_exit_trend":(("chandelier_exit",{"period":p.get("lookback",22),"atr_period":p.get("atr_period",22),"multiplier":p.get("atr_multiplier",3)},(("CHANDELIER_LONG","CHANDELIER_LONG"),("CHANDELIER_SHORT","CHANDELIER_SHORT"))),),
        "price_channel_trend":(("price_channels",{"period":p.get("channel_period",20)},(("PRICE_CHANNEL_UPPER","PRICE_CHANNEL_UPPER"),("PRICE_CHANNEL_MIDDLE","PRICE_CHANNEL_MIDDLE"),("PRICE_CHANNEL_LOWER","PRICE_CHANNEL_LOWER"))),),
        "aroon_trend":(("aroon",{"period":p.get("aroon_period",25)},(("AROON_UP","AROON_UP"),("AROON_DOWN","AROON_DOWN"))),),
        "momentum_acceleration_breakout":(("price_channels",{"period":p.get("channel_period",20)},(("PRICE_CHANNEL_UPPER","PRICE_CHANNEL_UPPER"),("PRICE_CHANNEL_MIDDLE","PRICE_CHANNEL_MIDDLE"),("PRICE_CHANNEL_LOWER","PRICE_CHANNEL_LOWER"))),("roc",{"period":p.get("roc_period",10)},(("ROC","ROC"),)),("momentum",{"period":p.get("momentum_period",10)},(("MOMENTUM","MOMENTUM"),))),
        "volume_expansion_breakout":(("price_channels",{"period":p.get("channel_period",20)},(("PRICE_CHANNEL_UPPER","PRICE_CHANNEL_UPPER"),("PRICE_CHANNEL_MIDDLE","PRICE_CHANNEL_MIDDLE"),("PRICE_CHANNEL_LOWER","PRICE_CHANNEL_LOWER"))),("volume_sma",{"period":p.get("volume_period",20)},(("VOLUME_SMA","VOLUME_SMA"),))),
    }
    for indicator,parameters,aliases in request_specs.get(name,()):requests.extend(_request_missing(frame,indicator,parameters,aliases))
    common_periods=(("ema",{"period":p.get("ema_period",p.get("trend_ema_period",50))},(("EMA","EMA"),)),("atr",{"period":p.get("atr_period",14)},(("ATR","ATR"),)),("adx",{"period":p.get("adx_period",14)},(("ADX","ADX"),)))
    for indicator,parameters,aliases in common_periods:
        requested_aliases={request.output_alias for request in requests}
        if aliases[0][1] in required and aliases[0][1] not in requested_aliases:requests.extend(_request_missing(frame,indicator,parameters,aliases))
    if requests:compute_indicator_requests(frame,tuple(requests));computed.extend(request.output_alias for request in requests)
    if name=="heikin_ashi_trend" and not {"HA_OPEN","HA_HIGH","HA_LOW","HA_CLOSE"}.issubset(frame.columns):_compute_heikin_ashi(frame);computed.extend(["HA_OPEN","HA_HIGH","HA_LOW","HA_CLOSE"]);_record_derived(frame,"heikin_ashi",("HA_OPEN","HA_HIGH","HA_LOW","HA_CLOSE"),{"initialization":"raw_midpoint"})
    if name=="nr4_nr7_volatility_breakout" and not {"NR4","NR7"}.issubset(frame.columns):_compute_nr_setups(frame);computed.extend(["NR4","NR7"]);_record_derived(frame,"nr4_nr7",("NR4","NR7"),{"windows":[4,7]})
    if name=="pivot_range_breakout" and not {"PRIOR_PIVOT","PRIOR_PIVOT_R1","PRIOR_PIVOT_S1","PRIOR_SESSION_ID"}.issubset(frame.columns):_compute_prior_session_pivots(frame,configuration.session_configuration if configuration else {});computed.extend(["PRIOR_PIVOT","PRIOR_PIVOT_R1","PRIOR_PIVOT_S1","PRIOR_SESSION_ID"]);_record_derived(frame,"prior_session_pivots",("PRIOR_PIVOT","PRIOR_PIVOT_R1","PRIOR_PIVOT_S1","PRIOR_SESSION_ID"),dict(configuration.session_configuration if configuration else {}))
    for name in framework.metadata.required_indicators:
        definition = indicator_registry.get(name)
        outputs = tuple(definition["output_columns"])
        needed = required.intersection(outputs)
        if needed and not needed.issubset(frame.columns):
            _attach(frame, indicator_registry.calculate(name, frame), outputs)
            computed.extend(column for column in outputs if column in required)
    if framework.metadata.name in {"turtle_trading", "donchian_breakout"} and role == "execution":
        entry_period = int(framework.parameters.get("entry_period", framework.parameters.get("channel_period", 20)))
        exit_period = int(framework.parameters["exit_period"])
        entry = indicator_registry.calculate("donchian_channel", frame, {"period": entry_period})
        exit_channel = indicator_registry.calculate("donchian_channel", frame, {"period": exit_period})
        _attach(frame, entry, ("DONCHIAN_UPPER", "DONCHIAN_MIDDLE", "DONCHIAN_LOWER"))
        _attach(frame, exit_channel, ("DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_MIDDLE", "DONCHIAN_EXIT_LOWER"))
        computed.extend(["DONCHIAN_UPPER", "DONCHIAN_LOWER", "DONCHIAN_EXIT_UPPER", "DONCHIAN_EXIT_LOWER"])
    return sorted(set(computed))


def prepare_timeframe_data(
    configuration: FrameworkResearchConfiguration,
    framework: BaseTradingFramework,
    timeframe_data: Mapping[str, pd.DataFrame],
) -> dict[str, PreparedTimeframeData]:
    roles = set(framework.metadata.timeframe_roles)
    if set(timeframe_data) != roles:
        raise ResearchPreparationError(f"timeframe data roles must be exactly {sorted(roles)}")
    prepared: dict[str, PreparedTimeframeData] = {}
    for role in framework.metadata.timeframe_roles:
        source = timeframe_data[role]
        validate_completed_bar_frame(source, role)
        frame = source.copy(deep=True)
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        else:
            frame.index = frame.index.tz_convert("UTC")
        warnings: list[str] = []
        numeric = list(frame.select_dtypes(include="number").columns)
        infinite = int(np.isinf(frame[numeric].to_numpy()).sum()) if numeric else 0
        if infinite:
            frame[numeric] = frame[numeric].replace([np.inf, -np.inf], np.nan)
            warnings.append(f"sanitized {infinite} infinite values to NaN")
        required = tuple(framework.schema.required_columns_by_role[role])
        missing = [column for column in required if column not in frame.columns]
        computed: list[str] = []
        if missing and configuration.preparation_mode is PreparationMode.COMPUTE_MISSING:
            try:
                computed = _compute_missing(frame, framework, role, configuration)
            except (KeyError, ValueError) as error:
                raise ResearchPreparationError(f"cannot compute indicators for role '{role}': {error}") from error
            missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ResearchPreparationError(f"role '{role}' missing precomputed columns: {', '.join(missing)}")
        valid_mask = frame[list(required)].notna().all(axis=1)
        first_valid = pd.Timestamp(frame.index[valid_mask.argmax()]) if valid_mask.any() else None
        warmup_rows = int((~valid_mask).cumprod().sum()) if len(valid_mask) else 0
        indicator_columns = tuple(column for column in required if column not in {"open", "high", "low", "close", "volume"})
        prepared[role] = PreparedTimeframeData(
            role, configuration.timeframe_roles[role], frame, indicator_columns, first_valid,
            pd.Timestamp(frame.index[-1]) if len(frame) else None, len(frame), warmup_rows,
            {"mode": configuration.preparation_mode.value, "timezone": "UTC", "source_preserved": True, "computed_columns": computed,"indicator_requests":list(frame.attrs.get("indicator_request_provenance",[])),"dependency_request_fingerprints":sorted({item["parameter_fingerprint"] for item in frame.attrs.get("indicator_request_provenance",[])})}, tuple(warnings),
        )
    return prepared
