from src.research.run_management.run_identity import stable_identity_hash

CLEAN_STATE={"position":{"status":"flat","direction":"flat"},"setup":{"status":"none"},"continuity":{"previous_session_id":None,"last_event_side":None,"event_reset":True}}

def continuity_state(final_summary):
    if not final_summary:return CLEAN_STATE
    return {key:final_summary.get(key,{}) for key in ("position","setup","session","continuity")}

def state_fingerprint(state):return stable_identity_hash(state)
