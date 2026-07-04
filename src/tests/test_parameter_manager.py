from parameters.parameter_manager import ParameterManager

pm = ParameterManager()

pm.update_nested(
    ["indicators", "ema", "fast"],
    10
)

pm.update_nested(
    ["exit_rules", "stop_loss_percent"],
    1.5
)

data = pm.load()

print(data["indicators"]["ema"])
print(data["exit_rules"])