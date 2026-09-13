"""
Step 2 isolation tests: hand-written actions fed directly to validate_action(),
no agent involved. Confirms accept/reject/re-prompt behavior including the
scenario 6 cumulative-consequence check, before Step 3 (logging) is built on top.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from env.microgrid_env import MicrogridEnv, MicrogridState
from dsl.action_bounding import validate_action


def test_valid_discharge_rate_accepted():
    env = MicrogridEnv()  # default: soc=80, reserve_min=15
    result = validate_action("set_battery_discharge_rate", {"rate_kw": 10}, env)
    assert result.accepted is True
    assert result.disposition == "approved"


def test_out_of_range_rate_rejected_or_reprompt():
    env = MicrogridEnv()
    result = validate_action("set_battery_discharge_rate", {"rate_kw": 999}, env)
    assert result.accepted is False
    assert any("outside allowed range" in r for r in result.reasons)


def test_unknown_action_type_rejected_by_zone_policy():
    env = MicrogridEnv()
    result = validate_action("launch_missiles", {}, env)
    assert result.accepted is False
    assert any("not permitted in this zone" in r for r in result.reasons)


def test_rate_of_change_violation_caught():
    env = MicrogridEnv(MicrogridState(battery_discharge_rate_kw=0))
    # jump from 0 to 40 kW in one action exceeds max_delta=25
    result = validate_action("set_battery_discharge_rate", {"rate_kw": 40}, env)
    assert result.accepted is False
    assert any("rate-of-change" in r for r in result.reasons)


def test_scenario_6_cumulative_drain_caught_even_though_instant_action_in_bounds():
    # soc=20, reserve_min=15: a 10kW discharge rate is individually in-bounds
    # (within [0,50] range, within 25 kW/step rate-of-change from 0), but
    # would drain 10 kWh over the hour, leaving soc=10 < reserve 15.
    env = MicrogridEnv(MicrogridState(
        battery_soc_kwh=20.0, battery_reserve_min_kwh=15.0, battery_discharge_rate_kw=0
    ))
    result = validate_action("set_battery_discharge_rate", {"rate_kw": 10}, env)
    assert result.accepted is False, "consequence check should have caught cumulative breach"
    assert any("breach battery reserve" in r for r in result.reasons)
    # confirm env state was NOT mutated by the check itself
    assert env.state.battery_discharge_rate_kw == 0


def test_safe_low_discharge_rate_passes_consequence_check():
    env = MicrogridEnv(MicrogridState(
        battery_soc_kwh=20.0, battery_reserve_min_kwh=15.0, battery_discharge_rate_kw=0
    ))
    # 2 kW/hr discharge leaves soc=18, above reserve of 15 -> should pass
    result = validate_action("set_battery_discharge_rate", {"rate_kw": 2}, env)
    assert result.accepted is True


def test_load_shed_within_range_accepted():
    env = MicrogridEnv()
    result = validate_action("shed_load", {"amount_kw": 20}, env)
    assert result.accepted is True


def test_load_shed_out_of_range_rejected():
    env = MicrogridEnv()
    result = validate_action("shed_load", {"amount_kw": 500}, env)
    assert result.accepted is False


def test_missing_required_param_does_not_crash_and_is_needs_reprompt():
    # Regression test: a real (non-mock) agent can produce a malformed
    # proposal missing a required key. Before REQUIRED_PARAMS was added,
    # this would raise an uncaught KeyError inside the consequence check
    # (env.state.battery_discharge_rate_kw = params["rate_kw"]) instead of
    # returning a clean, loggable disposition.
    env = MicrogridEnv()
    result = validate_action("set_battery_discharge_rate", {}, env)
    assert result.accepted is False
    assert result.disposition == "needs_reprompt"
    assert any("missing required param 'rate_kw'" in r for r in result.reasons)


def test_missing_required_param_with_zero_reprompt_budget_is_rejected():
    env = MicrogridEnv()
    result = validate_action("shed_load", {}, env, reprompt_budget=0)
    assert result.accepted is False
    assert result.disposition == "rejected"


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
