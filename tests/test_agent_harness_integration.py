"""
Step 5 integration tests: full pipeline, mock agents standing in for the LLM.
These are the FIRST tests that exercise components together rather than in
isolation -- per the implementation sequence, this is where integration bugs
that isolated unit tests structurally cannot catch are expected to surface.

Covers scenarios 1-5 (nominal) plus a reprompt case and a timeout-deny case
(scenario 9) end-to-end.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from env.microgrid_env import MicrogridEnv, MicrogridState
from dsl.audit_log import AuditLog
from dsl.override_gate import OverrideResponse
from dsl.agent_harness import run_pipeline, make_mock_agent, default_deny_responder


def approving_responder():
    return OverrideResponse(approved=True, operator_id="op-integration-test")


def denying_responder():
    return OverrideResponse(approved=False, operator_id="op-integration-test")


# --- Scenario 1: battery discharge setpoint during demand spike (HIGH tier, nominal) ---

def test_scenario1_nominal_discharge_approved_with_human_approval():
    env = MicrogridEnv()
    log = AuditLog()
    agent = make_mock_agent(
        "Demand spike detected; discharging battery at 10kW to cover load.",
        "set_battery_discharge_rate", {"rate_kw": 10},
    )
    result = run_pipeline(agent, env, log, override_responder=approving_responder)
    assert result.final_disposition == "approved"
    assert env.state.battery_discharge_rate_kw == 10
    # auditability: every step of this cycle must be in the log
    assert len(result.log_entry_seqs) >= 1
    ok, _ = log.verify_chain()
    assert ok


# --- Scenario 2: load-shedding at feeder capacity (HIGH tier) ---

def test_scenario2_load_shed_denied_by_human_does_not_mutate_env():
    env = MicrogridEnv()
    log = AuditLog()
    start_load = env.state.feeder_load_kw
    agent = make_mock_agent(
        "Feeder approaching capacity; proposing load shed of 20kW.",
        "shed_load", {"amount_kw": 20},
    )
    result = run_pipeline(agent, env, log, override_responder=denying_responder)
    assert result.final_disposition == "denied"
    assert env.state.feeder_load_kw == start_load, "denied action must not mutate environment state"


# --- Scenario 3: supply source switch (HIGH tier, nominal) ---

def test_scenario3_supply_switch_approved():
    env = MicrogridEnv()
    log = AuditLog()
    agent = make_mock_agent(
        "Grid price signal high; switching to battery-only supply.",
        "switch_supply_source", {"source": "battery"},
    )
    result = run_pipeline(agent, env, log, override_responder=approving_responder)
    assert result.final_disposition == "approved"
    assert env.state.supply_source == "battery"


# --- Scenario 4: SoH diagnostic scheduling (LOW tier, async, no human wait) ---

def test_scenario4_maintenance_scheduling_auto_approved_async_no_human_call():
    env = MicrogridEnv()
    log = AuditLog()
    calls = {"count": 0}
    def responder_should_not_be_called():
        calls["count"] += 1
        return OverrideResponse(approved=True, operator_id="unused")
    agent = make_mock_agent(
        "Scheduling routine SoH diagnostic.",
        "schedule_soh_diagnostic", {"delay_ticks": 60},
    )
    result = run_pipeline(agent, env, log, override_responder=responder_should_not_be_called)
    assert result.final_disposition == "approved"
    assert calls["count"] == 0, "LOW-tier action must not invoke the synchronous responder"
    assert env.state.soh_diagnostic_scheduled_tick is not None


# --- Scenario 5: DR schedule adjustment (LOW tier) ---

def test_scenario5_dr_schedule_adjustment_async():
    env = MicrogridEnv()
    log = AuditLog()
    agent = make_mock_agent(
        "Adjusting demand-response schedule for tomorrow.",
        "adjust_dr_schedule", {"delay_ticks": 1440},
    )
    result = run_pipeline(agent, env, log, override_responder=default_deny_responder)
    assert result.final_disposition == "approved"  # LOW tier never reaches the responder


# --- Reprompt path: DSL rejects first proposal, agent revises, second passes ---

def test_reprompt_path_agent_revises_after_dsl_violation():
    env = MicrogridEnv()
    log = AuditLog()
    agent = make_mock_agent(
        "Discharging at 999kW to cover a huge spike.",
        "set_battery_discharge_rate", {"rate_kw": 999},   # out of range, will be rejected
        reprompt_action=("set_battery_discharge_rate", {"rate_kw": 10}),  # revised, valid
    )
    result = run_pipeline(agent, env, log, override_responder=approving_responder, max_reprompts=1)
    assert result.final_disposition == "approved"
    assert result.params["rate_kw"] == 10
    # both the rejected first attempt AND the final disposition must be in the log
    assert len(result.log_entry_seqs) == 2
    dispositions = [log.all_entries()[s].disposition for s in result.log_entry_seqs]
    assert "needs_reprompt" in dispositions
    assert "overridden_approved" in dispositions


# --- Scenario 9: override timeout denies by default, end-to-end ---

def test_scenario9_timeout_denies_by_default_end_to_end():
    env = MicrogridEnv()
    log = AuditLog()
    start_load = env.state.feeder_load_kw
    agent = make_mock_agent(
        "Proposing load shed.", "shed_load", {"amount_kw": 20},
    )
    # default_deny_responder simulates "no human responded in time"
    result = run_pipeline(agent, env, log, override_responder=default_deny_responder)
    assert result.final_disposition == "denied"
    assert env.state.feeder_load_kw == start_load, "timed-out action must never mutate environment state"
    final_entry = log.all_entries()[result.log_entry_seqs[-1]]
    assert final_entry.disposition == "timed_out_denied"


# --- Auditability across a full run: everything reconstructable from log alone ---

def test_full_multi_action_run_fully_reconstructable_from_log():
    env = MicrogridEnv()
    log = AuditLog()
    agent1 = make_mock_agent("r1", "shed_load", {"amount_kw": 20})
    agent2 = make_mock_agent("r2", "schedule_soh_diagnostic", {"delay_ticks": 60})
    agent3 = make_mock_agent("r3", "set_battery_discharge_rate", {"rate_kw": 999})  # will be rejected outright (no reprompt_action)

    run_pipeline(agent1, env, log, override_responder=approving_responder)
    run_pipeline(agent2, env, log, override_responder=default_deny_responder)
    run_pipeline(agent3, env, log, override_responder=default_deny_responder, max_reprompts=0)

    ok, bad_seq = log.verify_chain()
    assert ok, f"chain broken at {bad_seq}"
    dispositions = log.reconstruct_dispositions()
    assert dispositions[0] == "overridden_approved"
    assert dispositions[1] == "auto_approved_async"
    assert dispositions[2] == "rejected"


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
