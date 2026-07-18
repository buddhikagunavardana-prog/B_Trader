from __future__ import annotations
from src.research.frameworks.state.models import PositionState,PositionStatus,SetupState,SetupStatus,StateSnapshot
from src.research.frameworks.state.session_state import SessionConfiguration,session_snapshot

STATEFUL_SETUPS={"inside_bar_breakout","opening_range_breakout","rsi_pullback_trend","support_resistance_bounce","bollinger_squeeze_breakout"}
class ResearchStateController:
 def __init__(self,framework,session=None,cooldown_bars=0,allow_repeated_entries=False,reverse_on_opposite_signal=False):self.framework=framework;self.position=PositionState(framework=framework);self.setup=SetupState(framework=framework);self.session_config=session or SessionConfiguration();self.cooldown_bars=cooldown_bars;self.allow_repeated=allow_repeated_entries;self.reverse=reverse_on_opposite_signal
 def snapshot(self,timestamp):return StateSnapshot(self.position.to_dict(),self.setup.to_dict(),session_snapshot(timestamp,self.session_config))
 def apply(self,decision,timestamp):
  prev_pos=self.position.status;prev_setup=self.setup.status;sig=decision.signal.value;transition="none";setup_transition="none"
  self.position.bars_in_state+=1
  if self.framework in STATEFUL_SETUPS:
   self.setup.bars_alive+=1
   if sig in {"buy","sell"}:
    self.setup.status=SetupStatus.CONSUMED;self.setup.setup_id=self.setup.setup_id or f"{self.framework}:{timestamp.isoformat()}";self.setup.trigger_timestamp=timestamp;self.setup.trigger_count+=1;setup_transition=f"{prev_setup.value}->consumed"
   elif self.setup.status is SetupStatus.NONE:
    self.setup.status=SetupStatus.ARMED;self.setup.setup_id=f"{self.framework}:{timestamp.isoformat()}";self.setup.created_timestamp=timestamp;self.setup.armed_timestamp=timestamp;setup_transition="none->armed"
   elif self.setup.bars_alive>self.setup.maximum_bars_alive:self.setup.status=SetupStatus.EXPIRED;setup_transition=f"{prev_setup.value}->expired"
  if self.position.status is PositionStatus.FLAT and sig in {"buy","sell"}:
   self.position.status=PositionStatus.LONG_ACTIVE if sig=="buy" else PositionStatus.SHORT_ACTIVE;self.position.direction="long" if sig=="buy" else "short";self.position.entry_signal_timestamp=timestamp;self.position.activation_timestamp=timestamp;self.position.entry_reason=decision.entry_reason;self.position.bars_in_state=0;transition=f"flat->{self.position.status.value}"
  elif self.position.status is PositionStatus.LONG_ACTIVE and sig=="exit_long" or self.position.status is PositionStatus.SHORT_ACTIVE and sig=="exit_short":
   self.position.status=PositionStatus.FLAT;self.position.direction="flat";self.position.exit_request_timestamp=timestamp;self.position.latest_exit_reason=decision.exit_reason;transition=f"{prev_pos.value}->flat"
  elif sig in {"buy","sell"} and not self.allow_repeated:transition="repeated_entry_suppressed"
  self.position.transition_reason=transition
  session=session_snapshot(timestamp,self.session_config);session.pop("entry_allowed",None)
  return {"research_position_state":self.position.status.value,"previous_position_state":prev_pos.value,"position_transition":transition,"bars_in_position_state":self.position.bars_in_state,"setup_state":self.setup.status.value,"previous_setup_state":prev_setup.value,"setup_id":self.setup.setup_id,"setup_age":self.setup.bars_alive,"setup_transition":setup_transition,**session,"state_warning":"","state_valid":True}
 def final_summary(self):return self.snapshot(self.position.activation_timestamp or __import__('pandas').Timestamp.now(tz='UTC')).to_dict()
