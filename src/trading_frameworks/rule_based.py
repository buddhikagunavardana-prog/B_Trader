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

    def generate_decision(self, context: FrameworkContext, timestamp: pd.Timestamp | None) -> FrameworkDecision:
        f=context.frames["execution"]; r=f.iloc[-1]; p=f.iloc[-2]; k=self.spec.kind
        if not all(finite_number(r[c]) for c in self.schema.required_columns_by_role["execution"] if c not in {"volume"}):
            return self.no_trade(timestamp,"Required values are not warmed up.")
        long=short=False; reason="No completed-bar event."
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
        if long:return self._result(timestamp,FrameworkSignal.BUY,FrameworkDirection.LONG,r,1,"Completed bullish event confirmed.")
        if short:return self._result(timestamp,FrameworkSignal.SELL,FrameworkDirection.SHORT,r,-1,"Completed bearish event confirmed.")
        return self.no_trade(timestamp,reason)

    def _result(self,timestamp,signal,direction,row,side,reason):
        risk=atr_risk(float(row.close),row.ATR,side,self.parameters["atr_stop_multiple"],self.parameters["reward_multiple"],self.parameters["risk_fraction"],True,maximum_holding_period=self.parameters.get("maximum_holding_period"))
        return FrameworkDecision(self.metadata.name,timestamp,signal,direction,.8,reason,risk,{"event_based":True})


def build_rule_framework(spec: RuleSpec, module_name: str):
    metadata=FrameworkMetadata(spec.name,spec.display,spec.category,spec.notes,("execution",),{"execution":"15m"},spec.dependencies,spec.columns,FrameworkStability.STABLE,spec.aliases,compatible_market_regimes=spec.regimes,incompatible_market_regimes=spec.incompatible,tags=(spec.category,"event_based"),reference_notes=spec.notes)
    schema=FrameworkSchema(metadata,spec.parameters+RISK_PARAMETERS,{"execution":spec.columns},"Completed-bar event entry.","Opposite event or downstream position-aware exit.","ATR-based advisory controls.","Stateless; no orders or balances.")
    cls=type("".join(part.title() for part in spec.name.split("_"))+"Framework",(RuleBasedFramework,),{"spec":spec,"schema":schema})
    cls.__module__=module_name
    return cls
