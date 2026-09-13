"""
Action-space bounding engine + policy DSL (Component 1).

Sits between a proposed agent action and the environment's apply_action().
No action reaches the environment without passing through validate_action()
first. Built and tested in isolation (hand-written actions, no agent yet)
per Step 2 of the implementation sequence.

DSL design: deliberately small, three primitive types only.
    - RangeConstraint: numeric param must fall within [min, max]
    - RateOfChangeConstraint: numeric param must not change by more than
      `max_delta` from the current environment value in one action
    - ZonePermission: action_type must be in the allowed set for the
      calling agent's declared zone (maps loosely to IEC 62443
      zone/conduit segmentation; single-zone for this testbed)

REQUIRED_PARAMS is checked before range/rate-of-change/consequence logic
touches params, so a malformed or incomplete proposal from a real agent
becomes a clean needs_reprompt/rejected result instead of an uncaught
KeyError downstream -- this matters once a real (non-mock) agent can
produce genuinely malformed output.

Consequence check: before final acceptance, re-runs the environment's
own would_breach_reserve_within() prediction -- this is what catches
scenario 6 (individually in-bounds action, unsafe cumulative effect).
"""

from dataclasses import dataclass, field
from typing import Optional
from env.microgrid_env import MicrogridEnv, ActionType, ActionResult


@dataclass
class RangeConstraint:
    param: str
    min_value: float
    max_value: float

    def check(self, params: dict) -> Optional[str]:
        val = params.get(self.param)
        if val is None:
            return None
        if not (self.min_value <= val <= self.max_value):
            return (
                f"{self.param}={val} outside allowed range "
                f"[{self.min_value}, {self.max_value}]"
            )
        return None


@dataclass
class RateOfChangeConstraint:
    param: str
    current_value_fn: str  # attribute name on env.state to compare against
    max_delta: float

    def check(self, params: dict, env: MicrogridEnv) -> Optional[str]:
        val = params.get(self.param)
        if val is None:
            return None
        current = getattr(env.state, self.current_value_fn)
        delta = abs(val - current)
        if delta > self.max_delta:
            return (
                f"{self.param} change of {delta} exceeds max rate-of-change "
                f"{self.max_delta} (current={current}, proposed={val})"
            )
        return None


@dataclass
class ZonePermission:
    allowed_actions: set[str]

    def check(self, action_type: str) -> Optional[str]:
        if action_type not in self.allowed_actions:
            return f"action '{action_type}' not permitted in this zone"
        return None


@dataclass
class ValidationResult:
    accepted: bool
    disposition: str  # "approved" | "rejected" | "needs_reprompt"
    reasons: list[str] = field(default_factory=list)


# ---- Policy for the microgrid/BEMS testbed, thresholds per evaluation-scenarios doc ----

ZONE_POLICY = ZonePermission(allowed_actions={
    "set_battery_discharge_rate",
    "set_battery_charge_rate",
    "shed_load",
    "restore_load",
    "switch_supply_source",
    "schedule_soh_diagnostic",
    "adjust_dr_schedule",
    "no_action",
})

RANGE_POLICIES = {
    "set_battery_discharge_rate": RangeConstraint("rate_kw", 0, 50),
    "set_battery_charge_rate": RangeConstraint("rate_kw", 0, 50),
    "shed_load": RangeConstraint("amount_kw", 0, 40),
}

REQUIRED_PARAMS = {
    "set_battery_discharge_rate": ["rate_kw"],
    "set_battery_charge_rate": ["rate_kw"],
    "shed_load": ["amount_kw"],
    "restore_load": ["load_id"],
    "switch_supply_source": ["source"],
    "schedule_soh_diagnostic": [],
    "adjust_dr_schedule": [],
    "no_action": [],
}

RATE_OF_CHANGE_POLICIES = {
    "set_battery_discharge_rate": RateOfChangeConstraint(
        "rate_kw", "battery_discharge_rate_kw", max_delta=25
    ),
}

CONSEQUENCE_CHECK_ACTIONS = {"set_battery_discharge_rate"}
CONSEQUENCE_CHECK_HORIZON_MINUTES = 60  # matches scenario 6's "within the hour"


def validate_action(
    action_type: ActionType,
    params: dict,
    env: MicrogridEnv,
    reprompt_budget: int = 1,
) -> ValidationResult:
    """
    Validate a proposed action against the DSL policy and the environment's
    own consequence-prediction. Does NOT mutate env state -- callers apply
    the action separately via env.apply_action() only if accepted.
    """
    reasons = []

    zone_violation = ZONE_POLICY.check(action_type)
    if zone_violation:
        reasons.append(zone_violation)

    if not zone_violation:
        for key in REQUIRED_PARAMS.get(action_type, []):
            if key not in params:
                reasons.append(f"missing required param '{key}' for action '{action_type}'")

    range_policy = RANGE_POLICIES.get(action_type)
    if range_policy and not reasons:
        v = range_policy.check(params)
        if v:
            reasons.append(v)

    roc_policy = RATE_OF_CHANGE_POLICIES.get(action_type)
    if roc_policy and not reasons:
        v = roc_policy.check(params, env)
        if v:
            reasons.append(v)

    if reasons:
        disposition = "needs_reprompt" if reprompt_budget > 0 else "rejected"
        return ValidationResult(accepted=False, disposition=disposition, reasons=reasons)

    if action_type in CONSEQUENCE_CHECK_ACTIONS:
        original_rate = env.state.battery_discharge_rate_kw
        env.state.battery_discharge_rate_kw = params["rate_kw"]
        would_breach = env.would_breach_reserve_within(CONSEQUENCE_CHECK_HORIZON_MINUTES)
        env.state.battery_discharge_rate_kw = original_rate
        if would_breach:
            return ValidationResult(
                accepted=False,
                disposition="rejected",
                reasons=[
                    f"projected to breach battery reserve within "
                    f"{CONSEQUENCE_CHECK_HORIZON_MINUTES} min at this discharge rate"
                ],
            )

    return ValidationResult(accepted=True, disposition="approved", reasons=[])
