from __future__ import annotations
from dataclasses import dataclass
from datetime import time
from zoneinfo import ZoneInfo
import pandas as pd
from src.research.frameworks.state.models import SessionType

@dataclass(frozen=True)
class SessionConfiguration:
 session_type:SessionType=SessionType.CONTINUOUS_24_7;timezone:str="UTC";start:str="00:00";end:str="23:59";opening_range_minutes:int=30;entry_cutoff:str="23:59";weekdays:tuple[int,...]=(0,1,2,3,4,5,6)
 def to_dict(self):return {**self.__dict__,"session_type":self.session_type.value,"weekdays":list(self.weekdays)}
 @classmethod
 def from_mapping(cls,values=None):
  data=dict(values or {})
  if "session_type" in data and isinstance(data["session_type"],str):data["session_type"]=SessionType(data["session_type"])
  if "weekdays" in data:data["weekdays"]=tuple(data["weekdays"])
  return cls(**data)
def session_snapshot(timestamp,configuration:SessionConfiguration):
 ts=pd.Timestamp(timestamp)
 if ts.tzinfo is None:ts=ts.tz_localize("UTC")
 ts=ts.tz_convert(ZoneInfo(configuration.timezone)); start_h,start_m=map(int,configuration.start.split(":"));end_h,end_m=map(int,configuration.end.split(":"));start=ts.normalize()+pd.Timedelta(hours=start_h,minutes=start_m);end=ts.normalize()+pd.Timedelta(hours=end_h,minutes=end_m)
 if configuration.session_type is SessionType.OVERNIGHT_SESSION and end<=start:
  if ts<end:start-=pd.Timedelta(days=1)
  else:end+=pd.Timedelta(days=1)
 active=ts.weekday() in configuration.weekdays and start<=ts<=end
 sid=f"{start.strftime('%Y-%m-%d')}_{configuration.timezone.replace('/','-')}_{configuration.start}"
 return {"session_id":sid,"session_state":"active" if active else "closed","session_open":start.isoformat(),"session_close":end.isoformat(),"opening_range_complete":ts>=start+pd.Timedelta(minutes=configuration.opening_range_minutes),"entry_allowed":active and ts.time()<=time(*map(int,configuration.entry_cutoff.split(':')))}
