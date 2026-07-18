from src.research.frameworks.historical.integrity import validate_historical_run

def validate_no_gaps_or_duplicates(plan):
    expected=0
    for chunk in plan.chunks:
        if chunk.logical_start!=expected:return False
        expected=chunk.logical_end+1
    return expected==plan.execution_row_count

def validate_memory_bound(plan,sources):
    estimates=[]
    for chunk in plan.chunks:
        estimate=0
        for source in sources.values():
            rows=min(source.row_count(),chunk.expected_input_row_count)
            sample=source.read_rows(0,min(rows,100))
            estimate+=int(sample.memory_usage(index=True,deep=True).sum())*max(rows,1)//max(len(sample),1)
        estimates.append(estimate)
    return {"valid":max(estimates,default=0)<=plan.config.maximum_memory_bytes,"maximum_estimated_bytes":max(estimates,default=0),"estimates":estimates}
