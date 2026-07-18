from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from src.trading_frameworks.base import BaseTradingFramework
from src.trading_frameworks.exceptions import FrameworkConfigurationError
from src.trading_frameworks.models import FrameworkContext, FrameworkDecision, FrameworkDirection, FrameworkMetadata, FrameworkSignal, FrameworkStability, ParameterDefinition, ParameterType
from src.trading_frameworks.schema import FrameworkSchema
from src.trading_frameworks.utilities.signals import atr_risk, finite_number


def period(name, default, text): return ParameterDefinition(name, ParameterType.PERIOD, default, text, 1, 500)
def number(name, default, text, low=0.0, high=100.0): return ParameterDefinition(name, ParameterType.FLOAT, default, text, low, high)
def boolean(name, default, text): return ParameterDefinition(name, ParameterType.BOOLEAN, default, text)
def choice(name, default, values, text): return ParameterDefinition(name, ParameterType.ENUM, default, text, allowed_values=values)


RISK_PARAMETERS = (
    number("atr_stop_multiple", 2.0, "ATR multiple used for the advisory stop.", .1, 20),
    number("reward_multiple", 2.0, "Reward multiple used for the advisory target.", .1, 20),
    number("risk_fraction", .01, "Advisory fractional risk suggestion.", .0001, .1),
)


@dataclass(frozen=True)
class RuleSpec:
    name: str; display: str; category: str; kind: str
    dependencies: tuple[str, ...]; columns: tuple[str, ...]
    parameters: tuple[ParameterDefinition, ...]; aliases: tuple[str, ...] = ()
    regimes: tuple[str, ...] = ("trend",); incompatible: tuple[str, ...] = ("directionless",)
    notes: str = "Completed-bar causal reference implementation; requires later market research."
    optional_dependencies: tuple[str, ...] = ()
    attribution: str = "B Trader professional reference implementation"
    state_requirements: tuple[str, ...] = ("event_consumption",)
    minimum_history: int = 2


class RuleBasedFramework(BaseTradingFramework):
    spec: RuleSpec
    minimum_history = {"execution": 2}

    def __init__(self, parameters=None):
        super().__init__(parameters)
        p = self.parameters
        if "fast_period" in p and "slow_period" in p and p["fast_period"] >= p["slow_period"]:
            raise FrameworkConfigurationError("fast_period must be less than slow_period")
        if "entry_threshold" in p and "exit_threshold" in p and p["exit_threshold"] >= p["entry_threshold"]:
            raise FrameworkConfigurationError("exit_threshold must be below entry_threshold")
        if {"long_entry", "exit_level", "short_entry"}.issubset(p) and not p["long_entry"] < p["exit_level"] < p["short_entry"]:
            raise FrameworkConfigurationError("Connors RSI thresholds must satisfy long_entry < exit_level < short_entry")
        if {"long_setup", "long_trigger"}.issubset(p) and p["long_setup"] >= p["long_trigger"]:
            raise FrameworkConfigurationError("long setup threshold must be below long trigger threshold")
        if {"short_setup", "short_trigger"}.issubset(p) and p["short_setup"] <= p["short_trigger"]:
            raise FrameworkConfigurationError("short setup threshold must be above short trigger threshold")
        if {"strong_threshold", "weak_threshold"}.issubset(p) and p["strong_threshold"] <= p["weak_threshold"]:
            raise FrameworkConfigurationError("strong threshold must exceed weak threshold")
        if {"minimum_wick_ratio", "maximum_body_ratio"}.issubset(p) and p["minimum_wick_ratio"] <= 1:
            raise FrameworkConfigurationError("minimum_wick_ratio must exceed 1")
        if {"oversold", "long_recovery", "exit_level", "short_recovery", "overbought"}.issubset(p) and not p["oversold"] < p["long_recovery"] < p["exit_level"] < p["short_recovery"] < p["overbought"]:
            raise FrameworkConfigurationError("Williams %R thresholds must be strictly ordered")
        if {"long_pullback", "short_pullback"}.issubset(p) and p["long_pullback"] >= p["short_pullback"]:
            raise FrameworkConfigurationError("long pullback must be below short pullback")

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        f=context.frames["execution"]; r=f.iloc[-1]; p=f.iloc[-2]; q=f.iloc[-3] if len(f)>2 else p; k=self.spec.kind
        if not all(finite_number(r[c]) for c in self.schema.required_columns_by_role["execution"] if c not in {"volume","PRIOR_SESSION_ID"}):
            return self.no_trade(timestamp,"Required values are not warmed up.")
        long=short=False; exit_long=exit_short=False; reason="No completed-bar event."; diagnostics={"event_based":True,"kind":k}
        if k=="supertrend": long=r.close>r.SUPERTREND and r.SUPERTREND_DIRECTION>0 and r.close>r.EMA and r.ADX>=self.parameters["minimum_adx"]; short=r.close<r.SUPERTREND and r.SUPERTREND_DIRECTION<0 and r.close<r.EMA and r.ADX>=self.parameters["minimum_adx"]
        elif k=="ribbon":
            cols=["EMA_8","EMA_13","EMA_21","EMA_34","EMA_55"]; vals=[r[c] for c in cols]; prev=[p[c] for c in cols]; long=all(vals[i]>vals[i+1] for i in range(4)) and r.close>vals[0] and not all(prev[i]>prev[i+1] for i in range(4)); short=all(vals[i]<vals[i+1] for i in range(4)) and r.close<vals[0] and not all(prev[i]<prev[i+1] for i in range(4))
        elif k=="dual_ma": long=p.EMA_FAST<=p.EMA_SLOW and r.EMA_FAST>r.EMA_SLOW; short=p.EMA_FAST>=p.EMA_SLOW and r.EMA_FAST<r.EMA_SLOW
        elif k=="adx": long=p.PLUS_DI<=p.MINUS_DI and r.PLUS_DI>r.MINUS_DI and r.ADX>=self.parameters["minimum_adx"] and r.close>r.EMA; short=p.MINUS_DI<=p.PLUS_DI and r.MINUS_DI>r.PLUS_DI and r.ADX>=self.parameters["minimum_adx"] and r.close<r.EMA
        elif k=="sar": long=p.PARABOLIC_SAR_DIRECTION<=0 and r.PARABOLIC_SAR_DIRECTION>0 and r.close>r.EMA; short=p.PARABOLIC_SAR_DIRECTION>=0 and r.PARABOLIC_SAR_DIRECTION<0 and r.close<r.EMA
        elif k=="squeeze":
            was=p.BOLLINGER_UPPER<=p.KELTNER_UPPER and p.BOLLINGER_LOWER>=p.KELTNER_LOWER; now=r.BOLLINGER_UPPER<=r.KELTNER_UPPER and r.BOLLINGER_LOWER>=r.KELTNER_LOWER; long=was and not now and r.close>p.BOLLINGER_UPPER; short=was and not now and r.close<p.BOLLINGER_LOWER
        elif k=="keltner": long=p.close<=p.KELTNER_UPPER and r.close>p.KELTNER_UPPER; short=p.close>=p.KELTNER_LOWER and r.close<p.KELTNER_LOWER
        elif k=="atr_breakout": long=r.close>p.close+self.parameters["breakout_multiple"]*p.ATR; short=r.close<p.close-self.parameters["breakout_multiple"]*p.ATR
        elif k=="opening_range":
            session_start=timestamp.normalize(); start=int(f.index.searchsorted(session_start,side="left")); day=f.iloc[start:]; n=self.parameters["opening_bars"]
            if len(day)<=n:return self.no_trade(timestamp,"Opening range is not complete.")
            high=day.iloc[:n].high.max(); low=day.iloc[:n].low.min(); prev=day.iloc[-2].close; long=prev<=high and r.close>high; short=prev>=low and r.close<low
        elif k=="rsi_pullback": long=p.RSI<=self.parameters["long_setup"] and r.RSI>self.parameters["long_trigger"] and r.close>r.EMA; short=p.RSI>=self.parameters["short_setup"] and r.RSI<self.parameters["short_trigger"] and r.close<r.EMA
        elif k=="macd": long=p.MACD<=p.MACD_SIGNAL and r.MACD>r.MACD_SIGNAL and r.MACD_HISTOGRAM>0 and r.close>r.EMA; short=p.MACD>=p.MACD_SIGNAL and r.MACD<r.MACD_SIGNAL and r.MACD_HISTOGRAM<0 and r.close<r.EMA
        elif k=="vwap": long=r.close<r.VWAP and r.VWAP_DEVIATION<=-self.parameters["deviation_threshold"] and r.RSI<=self.parameters["rsi_oversold"]; short=r.close>r.VWAP and r.VWAP_DEVIATION>=self.parameters["deviation_threshold"] and r.RSI>=self.parameters["rsi_overbought"]
        elif k=="zscore": long=p.ZSCORE<=-self.parameters["entry_threshold"] and r.ZSCORE>p.ZSCORE; short=p.ZSCORE>=self.parameters["entry_threshold"] and r.ZSCORE<p.ZSCORE
        elif k=="inside_bar":
            if len(f)<3:return self.no_trade(timestamp,"Inside-bar setup needs three rows.")
            m=f.iloc[-3]; inside=p.high<=m.high and p.low>=m.low; long=inside and r.close>m.high; short=inside and r.close<m.low
        elif k=="sr_bounce": long=p.low<=p.SUPPORT and r.close>p.SUPPORT and r.RSI<50; short=p.high>=p.RESISTANCE and r.close<p.RESISTANCE and r.RSI>50
        elif k=="elder_impulse":
            bull=r.EMA>p.EMA and r.MACD_HISTOGRAM>p.MACD_HISTOGRAM and ("ADX" not in r or r.ADX>=self.parameters["minimum_adx"]); bear=r.EMA<p.EMA and r.MACD_HISTOGRAM<p.MACD_HISTOGRAM and ("ADX" not in r or r.ADX>=self.parameters["minimum_adx"]); prev_bull=p.EMA>q.EMA and p.MACD_HISTOGRAM>q.MACD_HISTOGRAM; prev_bear=p.EMA<q.EMA and p.MACD_HISTOGRAM<q.MACD_HISTOGRAM; long=bull and not prev_bull;short=bear and not prev_bear;exit_long=context.current_position is FrameworkDirection.LONG and not bull;exit_short=context.current_position is FrameworkDirection.SHORT and not bear;diagnostics.update({"impulse_state":"bullish" if bull else "bearish" if bear else "neutral","ema_slope":float(r.EMA-p.EMA),"histogram_change":float(r.MACD_HISTOGRAM-p.MACD_HISTOGRAM)})
        elif k=="connors_rsi":
            long=p.CONNORS_RSI<=self.parameters["long_entry"] and r.CONNORS_RSI>self.parameters["long_entry"] and r.close>r.EMA;short=p.CONNORS_RSI>=self.parameters["short_entry"] and r.CONNORS_RSI<self.parameters["short_entry"] and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.CONNORS_RSI>=self.parameters["exit_level"];exit_short=context.current_position is FrameworkDirection.SHORT and r.CONNORS_RSI<=self.parameters["exit_level"];diagnostics.update({"connors_rsi":float(r.CONNORS_RSI),"components":{"rsi_period":self.parameters["rsi_period"],"streak_period":self.parameters["streak_period"],"rank_period":self.parameters["rank_period"]}})
        elif k=="stochastic_pullback":
            history=f.iloc[-(self.parameters["setup_expiry_bars"]+2):-1];long_setup=bool((history.STOCHASTIC_K<=self.parameters["long_pullback"]).any());short_setup=bool((history.STOCHASTIC_K>=self.parameters["short_pullback"]).any());long=long_setup and p.STOCHASTIC_K<=p.STOCHASTIC_D and r.STOCHASTIC_K>r.STOCHASTIC_D and r.close>r.EMA and r.ADX>=self.parameters["minimum_adx"];short=short_setup and p.STOCHASTIC_K>=p.STOCHASTIC_D and r.STOCHASTIC_K<r.STOCHASTIC_D and r.close<r.EMA and r.ADX>=self.parameters["minimum_adx"];exit_long=context.current_position is FrameworkDirection.LONG and r.STOCHASTIC_K<r.STOCHASTIC_D;exit_short=context.current_position is FrameworkDirection.SHORT and r.STOCHASTIC_K>r.STOCHASTIC_D;diagnostics.update({"pullback_setup":long_setup or short_setup,"stochastic_k":float(r.STOCHASTIC_K),"stochastic_d":float(r.STOCHASTIC_D)})
        elif k=="williams_reversal":
            history=f.iloc[-(self.parameters["setup_expiry_bars"]+2):-1];long_setup=bool((history.WILLIAMS_R<=self.parameters["oversold"]).any());short_setup=bool((history.WILLIAMS_R>=self.parameters["overbought"]).any());long=long_setup and p.WILLIAMS_R<=self.parameters["long_recovery"] and r.WILLIAMS_R>self.parameters["long_recovery"] and r.close>r.EMA;short=short_setup and p.WILLIAMS_R>=self.parameters["short_recovery"] and r.WILLIAMS_R<self.parameters["short_recovery"] and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.WILLIAMS_R>=self.parameters["exit_level"];exit_short=context.current_position is FrameworkDirection.SHORT and r.WILLIAMS_R<=self.parameters["exit_level"];diagnostics.update({"setup_armed":long_setup or short_setup,"williams_r":float(r.WILLIAMS_R)})
        elif k=="cci_pullback":
            history=f.iloc[-(self.parameters["setup_expiry_bars"]+2):-1];long_setup=bool((history.CCI<=self.parameters["long_setup"]).any());short_setup=bool((history.CCI>=self.parameters["short_setup"]).any());long=long_setup and p.CCI<=self.parameters["long_trigger"] and r.CCI>self.parameters["long_trigger"] and r.close>r.EMA and r.ADX>=self.parameters["minimum_adx"];short=short_setup and p.CCI>=self.parameters["short_trigger"] and r.CCI<self.parameters["short_trigger"] and r.close<r.EMA and r.ADX>=self.parameters["minimum_adx"];exit_long=context.current_position is FrameworkDirection.LONG and r.CCI<self.parameters["long_trigger"];exit_short=context.current_position is FrameworkDirection.SHORT and r.CCI>self.parameters["short_trigger"];diagnostics.update({"setup_armed":long_setup or short_setup,"cci":float(r.CCI)})
        elif k=="chandelier":
            bull=r.close>p.CHANDELIER_LONG and r.close>r.EMA;bear=r.close<p.CHANDELIER_SHORT and r.close<r.EMA;long=bull and not (p.close>q.CHANDELIER_LONG);short=bear and not (p.close<q.CHANDELIER_SHORT);exit_long=context.current_position is FrameworkDirection.LONG and r.close<p.CHANDELIER_LONG;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>p.CHANDELIER_SHORT;diagnostics.update({"long_trailing_level":float(p.CHANDELIER_LONG),"short_trailing_level":float(p.CHANDELIER_SHORT)})
        elif k=="price_channel":
            long=p.close<=p.PRICE_CHANNEL_UPPER and r.close>p.PRICE_CHANNEL_UPPER and r.close>r.EMA;short=p.close>=p.PRICE_CHANNEL_LOWER and r.close<p.PRICE_CHANNEL_LOWER and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.close<p.PRICE_CHANNEL_MIDDLE;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>p.PRICE_CHANNEL_MIDDLE;diagnostics.update({"prior_upper":float(p.PRICE_CHANNEL_UPPER),"prior_lower":float(p.PRICE_CHANNEL_LOWER),"channel_variant":"price_channel_prior_completed"})
        elif k=="heikin_ashi":
            body=abs(r.HA_CLOSE-r.HA_OPEN);bull=r.HA_CLOSE>r.HA_OPEN and r.HA_OPEN-r.HA_LOW<=body*self.parameters["maximum_wick_fraction"] and r.close>r.EMA and r.ADX>=self.parameters["minimum_adx"];bear=r.HA_CLOSE<r.HA_OPEN and r.HA_HIGH-r.HA_OPEN<=body*self.parameters["maximum_wick_fraction"] and r.close<r.EMA and r.ADX>=self.parameters["minimum_adx"];prev_bull=p.HA_CLOSE>p.HA_OPEN;prev_bear=p.HA_CLOSE<p.HA_OPEN;long=bull and not prev_bull;short=bear and not prev_bear;exit_long=context.current_position is FrameworkDirection.LONG and not bull;exit_short=context.current_position is FrameworkDirection.SHORT and not bear;diagnostics.update({"heikin_ashi_state":"bullish" if bull else "bearish" if bear else "neutral","initialization":"first HA open is midpoint of first raw open/close"})
        elif k=="aroon":
            bull=r.AROON_UP>=self.parameters["strong_threshold"] and r.AROON_DOWN<=self.parameters["weak_threshold"] and r.close>r.EMA;bear=r.AROON_DOWN>=self.parameters["strong_threshold"] and r.AROON_UP<=self.parameters["weak_threshold"] and r.close<r.EMA;prev_bull=p.AROON_UP>=self.parameters["strong_threshold"] and p.AROON_DOWN<=self.parameters["weak_threshold"];prev_bear=p.AROON_DOWN>=self.parameters["strong_threshold"] and p.AROON_UP<=self.parameters["weak_threshold"];long=bull and not prev_bull;short=bear and not prev_bear;exit_long=context.current_position is FrameworkDirection.LONG and r.AROON_UP<=r.AROON_DOWN;exit_short=context.current_position is FrameworkDirection.SHORT and r.AROON_DOWN<=r.AROON_UP;diagnostics.update({"aroon_up":float(r.AROON_UP),"aroon_down":float(r.AROON_DOWN),"aroon_oscillator":float(r.AROON_UP-r.AROON_DOWN)})
        elif k=="momentum_acceleration":
            long=p.close<=p.PRICE_CHANNEL_UPPER and r.close>p.PRICE_CHANNEL_UPPER and r.ROC>self.parameters["minimum_roc"] and r.ROC>p.ROC and r.MOMENTUM>p.MOMENTUM and r.close>r.EMA;short=p.close>=p.PRICE_CHANNEL_LOWER and r.close<p.PRICE_CHANNEL_LOWER and r.ROC<-self.parameters["minimum_roc"] and r.ROC<p.ROC and r.MOMENTUM<p.MOMENTUM and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.close<p.PRICE_CHANNEL_MIDDLE;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>p.PRICE_CHANNEL_MIDDLE;diagnostics.update({"roc_acceleration":float(r.ROC-p.ROC),"prior_breakout_level":float(p.PRICE_CHANNEL_UPPER if long else p.PRICE_CHANNEL_LOWER),"false_break":False})
        elif k=="volume_expansion":
            relative_volume=float(r.volume/p.VOLUME_SMA) if p.VOLUME_SMA>0 else 0.0;long=p.close<=p.PRICE_CHANNEL_UPPER and r.close>p.PRICE_CHANNEL_UPPER and relative_volume>=self.parameters["relative_volume_threshold"] and r.close>r.EMA;short=p.close>=p.PRICE_CHANNEL_LOWER and r.close<p.PRICE_CHANNEL_LOWER and relative_volume>=self.parameters["relative_volume_threshold"] and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.close<p.PRICE_CHANNEL_MIDDLE;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>p.PRICE_CHANNEL_MIDDLE;diagnostics.update({"relative_volume":relative_volume,"volume_valid":bool(p.VOLUME_SMA>0),"false_break":bool((r.close>p.PRICE_CHANNEL_UPPER or r.close<p.PRICE_CHANNEL_LOWER) and relative_volume<self.parameters["relative_volume_threshold"])})
        elif k=="nr_breakout":
            mode=self.parameters["range_mode"];setup=bool(p.NR4) if mode=="nr4" else bool(p.NR7) if mode=="nr7" else bool(p.NR4 or p.NR7);long=setup and r.close>p.high;short=setup and r.close<p.low;exit_long=context.current_position is FrameworkDirection.LONG and r.close<(p.high+p.low)/2;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>(p.high+p.low)/2;diagnostics.update({"setup_type":"NR7" if bool(p.NR7) else "NR4" if bool(p.NR4) else "none","setup_id":f"nr:{f.index[-2].isoformat()}","setup_high":float(p.high),"setup_low":float(p.low)})
        elif k=="pin_bar":
            candle_range=max(float(r.high-r.low),1e-12);body=max(abs(float(r.close-r.open)),1e-12);lower=min(float(r.open),float(r.close))-float(r.low);upper=float(r.high)-max(float(r.open),float(r.close));body_ratio=body/candle_range;near_support=abs(float(r.low-r.SUPPORT))<=float(r.ATR)*self.parameters["level_tolerance_atr"];near_resistance=abs(float(r.high-r.RESISTANCE))<=float(r.ATR)*self.parameters["level_tolerance_atr"];long=lower/body>=self.parameters["minimum_wick_ratio"] and body_ratio<=self.parameters["maximum_body_ratio"] and near_support and r.close>r.open;short=upper/body>=self.parameters["minimum_wick_ratio"] and body_ratio<=self.parameters["maximum_body_ratio"] and near_resistance and r.close<r.open;exit_long=context.current_position is FrameworkDirection.LONG and r.close<r.SUPPORT;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>r.RESISTANCE;diagnostics.update({"pattern_id":f"pin:{timestamp.isoformat()}","body_ratio":body_ratio,"lower_wick_ratio":lower/body,"upper_wick_ratio":upper/body,"confirmed_level":bool(near_support or near_resistance)})
        elif k=="engulfing":
            relaxed_bull=r.close>r.open and p.close<p.open and r.open<=p.close and r.close>=p.open;relaxed_bear=r.close<r.open and p.close>p.open and r.open>=p.close and r.close<=p.open;bull_pattern=bool(r.bullish_engulfing) or (self.parameters["engulfing_mode"]=="relaxed" and relaxed_bull);bear_pattern=bool(r.bearish_engulfing) or (self.parameters["engulfing_mode"]=="relaxed" and relaxed_bear);long=bull_pattern and r.close>r.EMA and r.ADX>=self.parameters["minimum_adx"];short=bear_pattern and r.close<r.EMA and r.ADX>=self.parameters["minimum_adx"];exit_long=context.current_position is FrameworkDirection.LONG and bear_pattern;exit_short=context.current_position is FrameworkDirection.SHORT and bull_pattern;diagnostics.update({"pattern_id":f"engulfing:{timestamp.isoformat()}","mode":self.parameters["engulfing_mode"],"trend_confirmed":bool((long or short))})
        elif k=="pivot_range":
            long=p.close<=r.PRIOR_PIVOT_R1 and r.close>r.PRIOR_PIVOT_R1 and r.close>r.EMA;short=p.close>=r.PRIOR_PIVOT_S1 and r.close<r.PRIOR_PIVOT_S1 and r.close<r.EMA;exit_long=context.current_position is FrameworkDirection.LONG and r.close<r.PRIOR_PIVOT;exit_short=context.current_position is FrameworkDirection.SHORT and r.close>r.PRIOR_PIVOT;diagnostics.update({"prior_session_id":str(r.PRIOR_SESSION_ID),"pivot":float(r.PRIOR_PIVOT),"resistance":float(r.PRIOR_PIVOT_R1),"support":float(r.PRIOR_PIVOT_S1),"prior_completed_session_only":True})
        if exit_long:return self._exit_result(timestamp,FrameworkSignal.EXIT_LONG,"Framework exit condition confirmed.",diagnostics)
        if exit_short:return self._exit_result(timestamp,FrameworkSignal.EXIT_SHORT,"Framework exit condition confirmed.",diagnostics)
        if long:return self._result(timestamp,FrameworkSignal.BUY,FrameworkDirection.LONG,r,1,"Completed bullish event confirmed.",diagnostics)
        if short:return self._result(timestamp,FrameworkSignal.SELL,FrameworkDirection.SHORT,r,-1,"Completed bearish event confirmed.",diagnostics)
        return self.no_trade(timestamp,reason)

    def _result(self,timestamp,signal,direction,row,side,reason,diagnostics=None):
        risk=atr_risk(float(row.close),row.ATR,side,self.parameters["atr_stop_multiple"],self.parameters["reward_multiple"],self.parameters["risk_fraction"],True,maximum_holding_period=self.parameters.get("maximum_holding_period"))
        return FrameworkDecision(self.metadata.name,timestamp,signal,direction,.8,reason,risk,diagnostics or {"event_based":True})

    def _exit_result(self,timestamp,signal,reason,diagnostics):
        return FrameworkDecision(self.metadata.name,timestamp,signal,FrameworkDirection.FLAT,.75,reason,diagnostics=diagnostics)


def build_rule_framework(spec: RuleSpec, module_name: str):
    metadata=FrameworkMetadata(spec.name,spec.display,spec.category,spec.notes,("execution",),{"execution":"15m"},spec.dependencies,spec.columns,FrameworkStability.STABLE,spec.aliases,attribution=spec.attribution,optional_indicators=spec.optional_dependencies,compatible_market_regimes=spec.regimes,incompatible_market_regimes=spec.incompatible,tags=(spec.category,"event_based","research_only"),reference_notes=spec.notes,causality_notes="All rolling references and pattern events use completed rows at or before the decision timestamp; channel breakouts use prior-row levels.",research_limitations="Synthetic structural validation only; no profitability, ranking, optimization, or execution claims.",state_policy_requirements=spec.state_requirements,execution_warning="Advisory research proposals only; never sizes or places orders.")
    schema=FrameworkSchema(metadata,spec.parameters+RISK_PARAMETERS,{"execution":spec.columns},"Completed-bar event entry.","Opposite event or downstream position-aware exit.","ATR-based advisory controls.","Stateless; no orders or balances.")
    cls=type("".join(part.title() for part in spec.name.split("_"))+"Framework",(RuleBasedFramework,),{"spec":spec,"schema":schema,"minimum_history":{"execution":spec.minimum_history}})
    cls.__module__=module_name
    return cls
