import pandas as pd
from src.research.frameworks.state.session_state import SessionConfiguration,session_snapshot
from src.research.frameworks.state.models import SessionType
def test_daily_overnight_and_continuous_sessions():
 t=pd.Timestamp("2026-07-18 10:00",tz="UTC");a=session_snapshot(t,SessionConfiguration(SessionType.DAILY_SESSION,"UTC","09:30","16:00"));assert a["session_state"]=="active" and a["opening_range_complete"]
 o=session_snapshot(pd.Timestamp("2026-07-18 23:00",tz="UTC"),SessionConfiguration(SessionType.OVERNIGHT_SESSION,"UTC","22:00","06:00"));assert o["session_state"]=="active" and o["session_id"]
if __name__=="__main__":test_daily_overnight_and_continuous_sessions();print("test_framework_session_calendar passed")
