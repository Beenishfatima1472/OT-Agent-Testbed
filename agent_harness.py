"""
Agent harness (Step 5): wires proposal -> validate_action() -> (if HIGH tier)
route_for_override() -> AuditLog.append() -> env.apply_action() into one
end-to-end pipeline.

Agent interface is deliberately decoupled from any specific LLM API: an
AgentFn takes optional feedback (violation reasons from a rejected/reprompt
disposition) and returns (reasoning_trace, action_type, params). This is
the seam where a real LLM call plugs in — see call_llm_agent() below for
the wiring point (network-dependent, not exercised in this sandbox) and
make_mock_agent() for the deterministic stand-in used in isolation tests.

No production/network calls happen in this module by default.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from env.microgrid_env import MicrogridEnv, ActionType
from dsl.action_bounding import validate_action
from dsl.override_gate import classify_risk_tier, route_for_override, RiskTier, OverrideResponse
from dsl.audit_log import AuditLog


# (reasoning_trace, action_type, params); feedback is None on first attempt,
# a list of violation reason strings on a re-prompt attempt.
AgentFn = Callable[[Optional[list[str]]], tuple[str, str, dict]]
OverrideResponder = Callable[[], Optional[OverrideResponse]]


@dataclass
class PipelineResult:
    final_disposition: str
    action_type: str
    params: dict
    log_entry_seqs: list[int]


def default_deny_responder() -> Optional[OverrideResponse]:
    """No human available in this call context -> counts as a timeout -> denied."""
    return None


def run_pipeline(
    agent_fn: AgentFn,
    env: MicrogridEnv,
    audit_log: AuditLog,
    override_responder: OverrideResponder = default_deny_responder,
    max_reprompts: int = 1,
) -> PipelineResult:
    """
    Runs one full proposal-to-disposition cycle. Every step, successful or
    not, is logged — that's the auditability property under test.
    """
    log_seqs = []
    feedback: Optional[list[str]] = None
    attempts = 0

    while True:
        reasoning, action_type, params = agent_fn(feedback)
        result = validate_action(action_type, params, env, reprompt_budget=max_reprompts - attempts)

        if result.accepted:
            break

        entry = audit_log.append(reasoning, action_type, params, result.disposition, result.reasons)
        log_seqs.append(entry.seq)

        if result.disposition == "needs_reprompt" and attempts < max_reprompts:
            feedback = result.reasons
            attempts += 1
            continue

        # exhausted reprompt budget or hard-rejected
        return PipelineResult(
            final_disposition="rejected", action_type=action_type,
            params=params, log_entry_seqs=log_seqs,
        )

    # Passed the DSL. Now the independent risk-tier/oversight layer decides
    # whether it still needs human review, regardless of policy validity.
    tier = classify_risk_tier(action_type)

    if tier == RiskTier.HIGH:
        gate_result = route_for_override(action_type, override_responder)
        if gate_result.disposition == "overridden_approved":
            env.apply_action(action_type, params)
        entry = audit_log.append(
            reasoning, action_type, params, gate_result.disposition,
            [], operator_id=gate_result.operator_id,
        )
        log_seqs.append(entry.seq)
        final = "approved" if gate_result.disposition == "overridden_approved" else "denied"
        return PipelineResult(final, action_type, params, log_seqs)

    # LOW tier: execute immediately, log as async-reviewable
    env.apply_action(action_type, params)
    entry = audit_log.append(reasoning, action_type, params, "auto_approved_async", [])
    log_seqs.append(entry.seq)
    return PipelineResult("approved", action_type, params, log_seqs)


# ---- Agent implementations ----

def make_mock_agent(reasoning: str, action_type: str, params: dict,
                     reprompt_action: Optional[tuple[str, dict]] = None) -> AgentFn:
    """
    Deterministic stand-in for an LLM agent, used in isolation tests.
    If reprompt_action is given, a second call (when feedback is not None)
    returns that revised action instead of repeating the original.
    """
    def agent_fn(feedback: Optional[list[str]]) -> tuple[str, str, dict]:
        if feedback is not None and reprompt_action is not None:
            revised_type, revised_params = reprompt_action
            return (
                f"Revising after feedback {feedback}: proposing {revised_type} with {revised_params}",
                revised_type, revised_params,
            )
        return (reasoning, action_type, params)
    return agent_fn


def call_llm_agent(system_prompt: str, model: str = "claude-sonnet-4-6") -> AgentFn:
    """
    WIRING POINT for a real LLM call — not exercised in this sandbox
    (no network access here). Intended usage once network is available:

        import anthropic
        client = anthropic.Anthropic()

        def agent_fn(feedback):
            user_content = "Propose the next action." if feedback is None else \\
                f"Your last proposal was rejected: {feedback}. Propose a revised action."
            response = client.messages.create(
                model=model, max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            # parse response.content for a structured tool-call-style action
            # (reasoning_trace, action_type, params) -- exact parsing depends
            # on whether tool use or structured JSON output is used.
            ...
        return agent_fn

    Raises NotImplementedError here deliberately so this stub is never
    accidentally used as if it were a working agent.
    """
    raise NotImplementedError(
        "call_llm_agent requires network access and an API client not "
        "available in this sandbox. See docstring for the wiring pattern "
        "to implement once running in an environment with API access."
    )
