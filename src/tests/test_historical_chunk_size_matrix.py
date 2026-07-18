import tempfile
import pandas as pd
from src.tests.historical_test_data import historical_case,stable_columns

def test_historical_chunk_size_matrix():
    frameworks=("ema_ribbon_trend","stochastic_pullback_trend","opening_range_breakout","heikin_ashi_trend","triple_screen_trading","support_resistance_bounce")
    with tempfile.TemporaryDirectory() as root:
        for name in frameworks:
            for size in (1,5,6,10,40):
                _,_,_,continuous,chunked,_=historical_case(name,40,size,root,run_name=f"matrix_{name}_{size}")
                columns=stable_columns(continuous)
                pd.testing.assert_frame_equal(continuous[columns],chunked[columns],check_dtype=False,obj=f"{name} chunk size {size}")
if __name__=="__main__":test_historical_chunk_size_matrix();print("test_historical_chunk_size_matrix passed")
