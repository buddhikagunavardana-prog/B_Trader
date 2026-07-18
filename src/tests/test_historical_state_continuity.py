import tempfile
from src.tests.historical_test_data import historical_case,stable_columns

def test_historical_state_continuity():
    with tempfile.TemporaryDirectory() as root:
        _,_,_,continuous,chunked,_=historical_case("stochastic_pullback_trend",240,60,root)
        columns=stable_columns(continuous);assert continuous[columns].equals(chunked[columns])
        assert continuous["setup_age"].equals(chunked["setup_age"])
if __name__=="__main__":test_historical_state_continuity();print("test_historical_state_continuity passed")
