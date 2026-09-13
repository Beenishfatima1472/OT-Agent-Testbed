"""
Step 4 isolation tests: the override gate tested with fake responders
(no real time, no agent, no environment) — pure logic verification before
Step 5 wires it into the full pipeline.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dsl.override_gate import (
    classify_risk_tier, route_for_override, RiskTier, OverrideResponse, GateResult
)


def test_high_tier_actions_classified_correctly():
    assert classify_risk_tier("set_battery_discharge_rate") == RiskTier.HIGH
    assert classify_risk_tier("shed_load") == RiskTier.HIGH
    assert classify_risk_tier("switch_supply_source") == RiskTier.HIGH


def test_low_tier_actions_classified_correctly():
    assert classify_risk_tier("schedule_soh_diagnostic") == RiskTier.LOW
    assert classify_risk_tier("adjust_dr_schedule") == RiskTier.LOW


def test_unclassified_action_fails_closed_to_high_tier():
    # the critical safety-default test: an action type nobody explicitly
    # classified must NOT silently bypass human review
    assert classify_risk_tier("some_new_action_nobody_configured") == RiskTier.HIGH


def test_high_tier_approved_response_routes_correctly():
    result = route_for_override(
        "shed_load",
        responder=lambda: OverrideResponse(approved=True, operator_id="op-1"),
    )
    assert result.disposition == "overridden_approved"
    assert result.operator_id == "op-1"


def test_high_tier_denied_response_routes_correctly():
    result = route_for_override(
        "shed_load",
        responder=lambda: OverrideResponse(approved=False, operator_id="op-2"),
    )
    assert result.disposition == "overridden_denied"
    assert result.operator_id == "op-2"


def test_high_tier_timeout_denies_by_default():
    # THE core safety property: no response within budget -> DENIED, never allowed
    result = route_for_override("shed_load", responder=lambda: None)
    assert result.disposition == "timed_out_denied"


def test_low_tier_routes_async_without_blocking():
    calls = {"count": 0}
    def responder_should_never_be_called():
        calls["count"] += 1
        return OverrideResponse(approved=True, operator_id="unused")
    result = route_for_override("adjust_dr_schedule", responder=responder_should_never_be_called)
    assert result.disposition == "auto_approved_async"
    assert calls["count"] == 0, "async/low-tier path must not invoke the synchronous responder"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} -> {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
