from __future__ import annotations

from src.research.frameworks.state.policies.models import LevelRecord, LevelState, PolicyConfiguration, PolicyDecision, PolicyReasonCode


def evaluate_level_test(level: LevelRecord, bar_number: int, broken: bool, config: PolicyConfiguration) -> PolicyDecision:
    level.age += 1
    if level.age > config.level_max_age_bars:
        level.state = LevelState.RETIRED
        return PolicyDecision(False, PolicyReasonCode.LEVEL_INVALIDATED, "Level retired after maximum age.", "retire_level")
    if broken:
        level.state = LevelState.BROKEN
        level.break_count += 1
        return PolicyDecision(False, PolicyReasonCode.LEVEL_INVALIDATED, "Confirmed level was structurally broken.", "invalidate_level")
    if level.last_test_bar is not None and bar_number - level.last_test_bar <= config.level_retest_cooldown_bars:
        return PolicyDecision(False, PolicyReasonCode.LEVEL_RETEST_COOLDOWN, "Level retest separation is insufficient.")
    level.state = LevelState.TESTING
    level.test_count += 1
    level.last_test_bar = bar_number
    return PolicyDecision(True, PolicyReasonCode.ALLOWED, "Confirmed historical level may be tested.", "test_level")
