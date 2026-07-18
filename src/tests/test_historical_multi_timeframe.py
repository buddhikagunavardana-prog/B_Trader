import tempfile
from src.tests.historical_test_data import historical_case,stable_columns

def test_historical_multi_timeframe():
    with tempfile.TemporaryDirectory() as root:
        _,_,_,continuous,chunked,_=historical_case("triple_screen_trading",240,60,root)
        assert continuous[stable_columns(continuous)].equals(chunked[stable_columns(chunked)])
if __name__=="__main__":test_historical_multi_timeframe();print("test_historical_multi_timeframe passed")
