# Concept Note: Auditable Constraint Architecture for Agentic AI in Energy OT Systems

## 1. Problem Statement

As autonomous AI agents move from advisory/chatbot roles into systems capable of issuing real-world control actions, operational technology (OT) environments — energy grids, industrial control systems (ICS), SCADA infrastructure — introduce a risk surface that existing agentic AI safety research does not address. Chatbot-era safety work focuses on prompt injection, hallucination, and conversational harms; OT security research focuses on human-operated or classically automated systems. Neither line of work answers the operational question regulators are now asking:

> **How can an autonomous AI agent's real-time control decisions in OT environments be constrained to a bounded, human-auditable action space, with a verifiable and low-latency human override path, without violating the real-time performance requirements of the control loop it operates in?**

This is a systems/architecture problem, not a policy problem: it requires a concrete, implementable mediation layer between an agent's decision output and the physical actuation it triggers, validated empirically rather than proposed conceptually.

## 2. Why Now / Regulatory Pressure

Multiple 2026 developments converge on this requirement:
- **NIST AI Agent Standards Initiative** (announced Feb 2026) — first multi-year federal effort scoped specifically to security controls for autonomous agent systems; no enforceable agent-specific standard exists yet.
- **EU AI Act** — classifies AI in critical infrastructure as high-risk, requiring logging, human oversight, and the ability to be overridden/stopped.
- **NIS2 / IEC 62443 / NERC CIP** — existing OT-security frameworks that any agentic-AI architecture must be shown compliant with, not exempt from.
- Industry survey data (Gravitee State of AI Agent Security 2026, CSA State of AI Cybersecurity 2026) consistently shows agent deployment far outpacing governance: mean monitoring coverage across deployed agents is around 52%, and most organizations report significant gaps between agent security policy and enforced practice.

Net effect: the compliance requirement ("governed, logged, stoppable") exists before the validated technical architecture that satisfies it does. That gap is the paper's reason to exist.

## 3. Preliminary Gap Claim

| Line of work | Representative source(s) | Domain | Validated implementation? | OT-specific? |
|---|---|---|---|---|
| General agentic AI trustworthiness surveys | Qi et al. 2026, "Towards Trustworthy Agentic AI" (arXiv 2605.23989) | LLM agents, general-purpose | Conceptual/survey | No |
| Agentic AI enterprise security/governance | CSA State of AI Cybersecurity 2026; Gravitee 2026 reports | Enterprise IT | Survey/industry data | No |
| OT/ICS red-teaming & offensive capability of AI agents | Dragos OT CTF benchmarking (CAI, arXiv 2511.05119) | ICS, offensive security | Empirical (attacker side) | Yes, but attacker-focused, not defensive-architecture-focused |
| Agentic AI + critical infrastructure frameworks | e.g. JCSTS 2026 quantum/agentic workflow framework paper | Energy/water/finance | Conceptual framework, cross-walk to standards | Partially |
| **Target contribution** | — | **Energy OT, defensive/architectural** | **Empirically validated on a simulated testbed** | **Yes, purpose-built** |

*(This table is a seed — expand it during the full systematic review in Phase 1; aim for 25–40 papers minimum before finalizing the gap claim in the manuscript.)*

### 3.1 Closest neighboring work found so far (initial pass)

| Paper | Venue | What it does | Gap relative to this project |
|---|---|---|---|
| Saber & Kundur, "Large Language Models as Explainable Cyberattack Detectors for Energy ICS" | ACM EnergySP 2026 (co-located w/ e-Energy) | Uses LLMs for explainable intrusion **detection** on Modbus/SCADA traffic | Detection, not action-constraint governance — the agent here is diagnostic, not actuating; complements but doesn't compete with an action-bounding architecture |
| CIP hybrid AI/LLM decision-support architecture (industrial batch/beverage plant) | AI (MDPI) 2026 | LLM agent gives conversational diagnostic support to human operators over SCADA data | Advisory only — human remains sole actuator, so the override-latency and action-bounding problem doesn't arise the way it does for an actuating agent |
| AgentSpec | ICSE 2026 | Customizable **runtime enforcement** for safe LLM agents (general-purpose) | Directly relevant as a candidate enforcement mechanism to build on or benchmark against — but general-purpose, not OT-validated, no real-time/control-loop latency treatment |
| Pro²Guard | arXiv 2508.00500 | Proactive runtime enforcement via probabilistic model checking | Same relationship as AgentSpec — a general mechanism worth adapting, not an OT-validated one |
| "Constraint Drift" position paper | arXiv 2605.10481 | Argues safety constraints must be *maintained as execution state* across an agent's full trajectory, not just asserted at output | Directly supports the auditability requirement in this project's architecture — good citation for why logging must be trajectory-level, not just final-decision-level |
| "Three-Layer Probabilistic Assume-Guarantee Architecture" | arXiv 2605.18672 | Position paper arguing structural (not just prompted) safety layers are required for LLM agent deployment | Theoretical support for a layered-architecture approach; no empirical OT validation |

**Read on the gap after this pass:** the mechanisms this project needs (runtime enforcement, constraint-state maintenance, layered assume-guarantee structure) exist as *general-purpose* proposals in 2026 literature — but none have been adapted and empirically validated against a real-time OT control loop with actuation, nor benchmarked against IEC 62443 / NERC CIP requirements. That's a sharper, more defensible gap claim than "nobody has looked at this at all": the contribution is the **domain adaptation and empirical validation**, not the invention of runtime enforcement as a concept. Cite AgentSpec/Pro²Guard/Constraint-Drift as the mechanisms you are adapting, not as competitors you're beating.

## 4. Proposed Contribution

A four-component reference architecture — action-space bounding, real-time decision-explanation logging, bounded-latency human override, and tamper-evident audit trail — implemented and evaluated against a simulated energy OT testbed under both nominal and adversarial/edge-case conditions, benchmarked against explicit, falsifiable success criteria (below), and cross-walked against IEC 62443 / NIST AI RMF / NERC CIP requirements.

## 5. Falsifiable Success Criteria (lock before building)

1. **Containment:** ≥ X% of out-of-bound agent actions blocked pre-execution (target TBD after baseline testing — do not set this number aspirationally).
2. **Override latency:** human override path completes within a latency budget appropriate to the simulated control loop (define per scenario — grid protection loops vs. slower dispatch decisions have very different budgets).
3. **Auditability:** 100% of executed and blocked actions reconstructable from logs alone, independent of agent self-report.
4. **Performance cost:** measurable latency/throughput overhead the constraint layer adds to nominal agent operation (report honestly — a real overhead number is more credible than an implausible "negligible").

## 5a. Additional Grounding Found in Literature Pass

A directly relevant 2025 paper — "Autonomous Control Leveraging LLMs: An Agentic Framework for Next-Generation Industrial Automation" (arXiv 2507.07115) — already implements something close to component 1 (action-space bounding): an action → simulate → validate loop where, if no valid action is found within an iteration budget, control hands off to a conservative fallback policy or human operator. This is useful both as a citation and as a candidate pattern to adapt directly, and its "iteration budget exhausted → fallback" logic is a concrete mechanism for meeting the containment success criterion (Section 5, item 1).

General-purpose agent-governance literature (Arthur.ai, Galileo, 2026) converges on a **risk-tiered override gate** design worth adapting for OT: gate depth scales with reversibility, blast radius, and domain sensitivity; irreversible/high-blast-radius actions get approve-before-act (synchronous) gates, lower-risk actions get review-after-act (asynchronous) gates; and — critically for a control-loop context — **deny-by-default on timeout**, not allow-by-default, when a human doesn't respond in time. This maps cleanly onto OT's own hazard classification practices (SIL levels in IEC 61508/62443) and gives Component 3 (bounded-latency override) a concrete design pattern rather than an invented one.

## 6. Immediate Next Steps

- [ ] Expand Section 3 into a full systematic literature review (target: 25–40 papers, structured search log across IEEE Xplore, Springer Link, ACM DL, arXiv)
- [ ] Select testbed: GridLAB-D / PyPSA (grid-side) vs. OpenPLC + SCADA HMI (general ICS) — decide based on which better supports the chosen evaluation scenarios
- [ ] Draft architecture diagram (component + data-flow)
- [ ] Set up version-controlled repo with containerized environment for reproducibility
- [ ] Shortlist 3–4 target venues (IEEE Access / IEEE Trans. Industrial Informatics / Springer critical-infrastructure-protection journal / an ICS-security workshop for a faster first submission)

## 7. Decisions Locked

- **Agent implementation: LLM-based, tool-calling agent** (not RL). Rationale: aligns with NORA's Agentic AI priority and the 2026 literature base being adapted (AgentSpec, Pro²Guard, constraint-drift); natural-language reasoning traces make "explainable decision logging" implementable and auditable in a way an RL policy's internals are not. RL comparison flagged as future work.
- **Testbed: open-source simulator first (OpenPLC + lightweight SCADA HMI), NORCICS access deferred to a later stretch phase.** Rationale: avoids institutional-access lead time as a blocker for the first paper; a working validated prototype becomes the stronger pitch for NORCICS access on the maritime/energy follow-up project, rather than requesting access speculatively.
- Remaining open question: single-sector (energy) framing vs. sector-agnostic framing with energy as validation case — revisit once the architecture draft (Phase 2) makes the trade-off concrete.
