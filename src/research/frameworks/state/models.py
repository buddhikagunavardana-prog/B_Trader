from __future__ import annotations
from dataclasses import asdict,dataclass,field
from enum import Enum
from typing import Any
import pandas as pd

class PositionStatus(str,Enum):
 FLAT="flat";PENDING_LONG="pending_long";PENDING_SHORT="pending_short";LONG_ACTIVE="long_active";SHORT_ACTIVE="short_active";EXIT_PENDING="exit_pending";COOLDOWN="cooldown"
class SetupStatus(str,Enum):
 NONE="none";FORMING="forming";ARMED="armed";TRIGGERED="triggered";EXPIRED="expired";INVALIDATED="invalidated";CONSUMED="consumed"
class SessionType(str,Enum):
 CONTINUOUS_24_7="continuous_24_7";DAILY_SESSION="daily_session";OVERNIGHT_SESSION="overnight_session"

@dataclass
class PositionState:
 status:PositionStatus=PositionStatus.FLAT;direction:str="flat";framework:str="";setup_id:str|None=None;entry_signal_timestamp:pd.Timestamp|None=None;activation_timestamp:pd.Timestamp|None=None;exit_request_timestamp:pd.Timestamp|None=None;bars_in_state:int=0;bars_since_entry_signal:int=0;stop_proposal:dict=field(default_factory=dict);target_proposal:dict=field(default_factory=dict);trailing_proposal:dict=field(default_factory=dict);maximum_holding_period:int|None=None;entry_reason:str="";latest_exit_reason:str="";transition_reason:str="initial";cooldown_reason:str="";cooldown_bars_total:int=0;cooldown_bars_remaining:int=0;cooldown_started_at:pd.Timestamp|None=None;pending_reversal_direction:str|None=None;warnings:list[str]=field(default_factory=list);metadata:dict=field(default_factory=dict)
 def to_dict(self):
  d=asdict(self);d["status"]=self.status.value
  for k in ("entry_signal_timestamp","activation_timestamp","exit_request_timestamp","cooldown_started_at"):
   d[k]=None if d[k] is None else pd.Timestamp(d[k]).isoformat()
  return d
@dataclass
class SetupState:
 status:SetupStatus=SetupStatus.NONE;setup_id:str|None=None;framework:str="";direction:str="flat";setup_type:str="";created_timestamp:pd.Timestamp|None=None;armed_timestamp:pd.Timestamp|None=None;trigger_timestamp:pd.Timestamp|None=None;expiration_timestamp:pd.Timestamp|None=None;source_level:float|None=None;bars_alive:int=0;maximum_bars_alive:int=5;trigger_count:int=0;consumed_timestamp:pd.Timestamp|None=None;expiration_reason:str="";invalidation_reason:str="";metadata:dict=field(default_factory=dict);reason:str=""
 def to_dict(self):
  d=asdict(self);d["status"]=self.status.value
  for k,v in list(d.items()):
   if "timestamp" in k and v is not None:d[k]=pd.Timestamp(v).isoformat()
  return d
@dataclass(frozen=True)
class StateSnapshot:
 position:dict;setup:dict;session:dict
 def to_dict(self):return {"position":self.position,"setup":self.setup,"session":self.session}
