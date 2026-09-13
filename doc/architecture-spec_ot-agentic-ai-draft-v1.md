# Draft Architecture Specification v1: Auditable Constraint Layer for LLM Agents in OT Environments

## System Overview

The architecture sits as a mediation layer between an LLM-based, tool-calling agent and the OT actuators (simulated PLCs / SCADA points) it is permitted to influence. The agent never calls actuators directly — every proposed action passes through this layer before (possibly) reaching the physical/simulated world.

```
[LLM Agent] --proposed action--> [Constraint Layer] --validated action--> [OpenPLC / Simulated Actuators]
                                        |         ^
                              [Decision Log]  [Override Gate]
                                        |         ^
                                        v         |
                                  [Audit Store] [Human Operator Console]
```

## Component 1 — Action-Space Bounding Engine

**Function:** Validate every proposed agent action against a formally defined permitted-action envelope before execution.

**Design (adapted from arXiv 2507.07115's action→simulate→validate loop):**
1. Agent proposes an action (structured tool call, not free text — e.g. `set_setpoint(tag="CIP_TEMP_1", value=85)`).
2. Action is checked against a declarative policy (allowed tags, value ranges, rate-of-change limits) — this is the equivalent of AgentSpec-style runtime enforcement, adapted with OT-specific bounds (e.g. sourced from IEC 62443 zone/conduit definitions).
3. Action is run through a **simulated consequence check** (predict resulting state) before real/simulated execution — catches actions that are individually in-bounds but produce an out-of-bounds *system* state.
4. If validation fails: iteration budget allows one bounded re-prompt of the agent with the violation reason; if still invalid, fallback to Component 3 (override gate), not silent rejection — silent rejection breaks auditability.

**Open implementation question:** where policy bounds come from — hand-authored per testbed scenario initially; a stretch goal is deriving them semi-automatically from IEC 62443 zone/conduit models.

## Component 2 — Real-Time Explanation & Decision Logging

**Function:** Every proposed action — approved, modified, or blocked — produces a structured rationale trace *before* execution, addressing the "constraint drift" failure mode (arXiv 2605.10481): safety-relevant context must be preserved across the full trajectory, not just asserted once.

**Design:**
- Log schema: `{timestamp, agent_reasoning_trace, proposed_action, policy_check_result, final_disposition, operator_id_if_overridden}`.
- Reasoning trace captured at proposal time, not reconstructed after the fact — LLM tool-calling frameworks (LangChain/AutoGen-style middleware, per the industrial-automation paper) already expose this hook.
- This log is the input to both Component 4 (audit store) and the evaluation harness (Phase 3) — containment and auditability success criteria are measured directly against it.

## Component 3 — Bounded-Latency Human Override Gate

**Function:** Risk-tiered approval gate, adapted from the Arthur.ai/Galileo governance pattern to OT hazard classification.

**Design:**
- Gate tier determined by blast radius + reversibility, mapped onto existing OT concepts: SIL-adjacent actions (per IEC 61508/62443) → synchronous, approve-before-act; low-risk/reversible actions → asynchronous, review-after-act.
- **Deny-by-default on timeout** — an unanswered high-tier request does not fall through to execution; this is the single most important safety property to validate empirically (Section 5 criterion 2).
- Latency budget is scenario-specific and must be defined per control loop before evaluation (a grid protection action and a maintenance-scheduling action do not share a budget) — this is a key parameter to sweep during Phase 3 evaluation, not a single fixed number.

## Component 4 — Tamper-Evident Audit Trail

**Function:** Make the Component 2 log independently verifiable — "auditable" has to mean provably unaltered, not just "we kept a log file."

**Design (implementation-simple version for v1):** append-only, hash-chained log (each entry includes the hash of the previous entry) — sufficient to detect tampering without requiring a full blockchain/distributed-ledger implementation, which would be disproportionate engineering for a first paper. Note in Limitations that a distributed/multi-party version is future work if the threat model requires resistance to a compromised single log host.

## What Changes Before This Is "Done"

This is a v1 draft to react to, not a final spec. Decisions resolved:
- **Policy language (Component 1):** small purpose-built DSL (range, rate-of-change, zone-permission primitives) rather than reusing OPA/Rego — deliberate choice, since an OT-native constraint language is itself part of the contribution.
- **Reasoning-trace logging framework (Component 2):** custom, minimal harness (thin wrapper around direct LLM API calls), not LangChain/AutoGen — avoids framework version-drift undermining reproducibility.
- **Scope and latency budgets (Component 3):** architecture is explicitly scoped to **supervisory/dispatch-tier** actions (latency budget: low seconds to tens of seconds) and **maintenance/scheduling-tier** actions (latency budget: minutes). **Protection-tier control (millisecond-scale, e.g. IEC 61850 GOOSE-messaging-speed breaker/relay logic) is explicitly out of scope** — LLM agent inference latency cannot meet protection-tier budgets, so this boundary is stated as a deliberate design decision in the paper, not a limitation discovered later.

Remaining before Phase 3 build starts:
- Finalize the DSL's constraint primitive set against the two chosen scenario tiers
- Define the exact scenario set (which specific supervisory and maintenance-tier actions the evaluation will cover) — feeds directly into Phase 3 evaluation-scenario design
