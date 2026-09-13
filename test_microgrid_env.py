"""
Step 1 isolation tests: verify the environment model behaves correctly with
NO agent, NO constraint layer, and NO DSL involved — hand-driven actions only.
Per the implementation sequence, later components' evaluations are only
trustworthy if this passes first.

Run with: python -m pytest tests/test_microgrid_env.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from env.microgrid_env import MicrogridEnv, MicrogridState


def test_battery_discharges_over_time():
    env = MicrogridEnv()
    start_soc = env.state.battery_soc_kwh
    env.apply_action("set_battery_discharge_rate", {"rate_kw": 30})
    env.tick(60)  # one simulated hour
    assert env.state.battery_soc_kwh == start_soc - 30, (
        f"expected {start_soc - 30}, got {env.state.battery_soc_kwh}"
    )


def test_battery_does_not_go_negative():
    env = MicrogridEnv(MicrogridState(battery_soc_kwh=5.0))
    env.apply_action("set_battery_discharge_rate", {"rate_kw": 100})
    env.tick(60)
    assert env.state.battery_soc_kwh == 0.0


def test_battery_does_not_exceed_capacity():
    env = MicrogridEnv(MicrogridState(battery_soc_kwh=95.0, battery_capacity_kwh=100.0))
    env.apply_action("set_battery_charge_rate", {"rate_kw": 100})
    env.tick(60)
    assert env.state.battery_soc_kwh == 100.0


def test_load_shed_reduces_feeder_load():
    env = MicrogridEnv()
    start_load = env.state.feeder_load_kw
    env.apply_action("shed_load", {"amount_kw": 20})
    assert env.state.feeder_load_kw == start_load - 20
    assert env.state.load_shed_active is True


def test_supply_source_switch():
    env = MicrogridEnv()
    assert env.state.supply_source == "grid"
    env.apply_action("switch_supply_source", {"source": "battery"})
    assert env.state.supply_source == "battery"


def test_would_breach_reserve_within_predicts_correctly():
    # scenario 6: individually-fine discharge rate that breaches reserve within the hour
    env = MicrogridEnv(MicrogridState(battery_soc_kwh=20.0, battery_reserve_min_kwh=15.0))
    env.apply_action("set_battery_discharge_rate", {"rate_kw": 10})  # 10 kWh over 60 min
    assert env.would_breach_reserve_within(60) is True   # 20 - 10 = 10 < 15 reserve
    assert env.would_breach_reserve_within(10) is False  # 20 - 1.67 = 18.3 > 15 reserve


def test_unknown_action_rejected():
    env = MicrogridEnv()
    result = env.apply_action("not_a_real_action", {})
    assert result.accepted is False


def test_history_is_recorded_every_tick():
    env = MicrogridEnv()
    env.tick(5)
    assert len(env.history) == 6  # initial state + 5 ticks


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
