import pandas as pd
from src.research.frameworks.state import ResearchStateController
from src.trading_frameworks.models import FrameworkDecision,FrameworkSignal,FrameworkDirection
def d(signal,direction):return FrameworkDecision("inside_bar_breakout",pd.Timestamp("2026-01-01",tz="UTC"),signal,direction,.8,"test")
def test_position_setup_and_repeated_entry_transitions():
 c=ResearchStateController("inside_bar_breakout");t=pd.Timestamp("2026-01-01",tz="UTC");a=c.apply(d(FrameworkSignal.BUY,FrameworkDirection.LONG),t);assert a["position_transition"]=="flat->long_active" and a["setup_state"]=="consumed";b=c.apply(d(FrameworkSignal.BUY,FrameworkDirection.LONG),t+pd.Timedelta(minutes=5));assert b["position_transition"]=="repeated_entry_suppressed"
if __name__=="__main__":test_position_setup_and_repeated_entry_transitions();print("test_framework_state_controller passed")
