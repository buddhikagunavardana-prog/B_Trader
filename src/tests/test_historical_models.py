from src.research.frameworks.historical.models import ChunkStatus, RunStatus, OverlapMode

def test_historical_models():
    assert {item.value for item in ChunkStatus}=={"planned","running","completed","failed","cancelled","corrupt","skipped","superseded"}
    assert RunStatus.RECOVERABLE.value=="recoverable" and OverlapMode.DEPENDENCY_AWARE.value=="dependency_aware"
if __name__=="__main__":test_historical_models();print("test_historical_models passed")
