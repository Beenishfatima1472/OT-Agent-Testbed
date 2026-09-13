# Research Statement

## Auditable Constraint Architectures for Agentic AI in Operational Technology Environments

### Research Vision

Autonomous AI agents are moving from advisory, conversational roles into systems capable of issuing real-world control actions. In operational technology (OT) environments — energy grids, industrial control systems, maritime infrastructure — this shift introduces a risk surface that current agentic AI safety research does not address: existing work is built almost entirely around chatbot-era harms (prompt injection, hallucination, conversational misuse), while OT security research is built around human-operated or classically automated systems. Neither tradition answers the question regulators, standards bodies, and infrastructure operators are now asking in practice — how an autonomous agent's control decisions can be bounded, explained, and safely overridden without violating the real-time and safety-integrity requirements the infrastructure itself imposes.

My research agenda addresses this gap directly: developing and empirically validating architectures that make agentic AI systems auditable, constrainable, and compliant-by-design when deployed in critical infrastructure.

### Motivation and Timeliness

This agenda is motivated by a convergence of regulatory and technical pressure arriving faster than the underlying research base. The EU AI Act classifies AI systems in critical infrastructure as high-risk, mandating logging, human oversight, and override capability. NIS2 and sector frameworks (IEC 62443, NERC CIP) impose parallel requirements. The NIST AI Agent Standards Initiative, launched in early 2026, is the first sustained federal effort aimed specifically at security controls for autonomous agent systems — and no enforceable, agent-specific standard yet exists. Industry data shows deployment sharply outpacing governance: reported agent-monitoring coverage sits around half of deployed systems, with widening gaps between stated policy and enforced practice.

At the same time, 2025–2026 research has produced general-purpose mechanisms — runtime enforcement frameworks for LLM agents, formal treatments of "constraint drift" across agent trajectories, layered assume-guarantee architectures — that have not been adapted to, or empirically validated against, real-time OT control loops with actual physical or simulated actuation. My contribution is this domain adaptation and validation: taking mechanisms proven in general-purpose settings and demonstrating, with a working testbed, that they can be made to satisfy the specific latency, safety-integrity, and auditability requirements OT environments impose.

### Specific Aims

**Aim 1 — Architecture.** Design a four-component reference architecture mediating between an LLM-based, tool-calling agent and OT actuation: an action-space bounding engine (validating proposed actions against a declarative, OT-native policy language before execution), a real-time decision-logging layer (capturing reasoning traces at proposal time to prevent safety-relevant context from degrading across an agent's trajectory), a risk-tiered human override gate (deny-by-default on timeout, gate depth scaled to action reversibility and blast radius, mapped onto existing OT hazard classification), and a tamper-evident audit trail (hash-chained, independently verifiable).

**Aim 2 — Validation.** Implement the architecture against a simulated OT testbed (OpenPLC-based) and evaluate it under both nominal and adversarial/edge-case conditions against pre-registered, falsifiable success criteria: containment rate of out-of-bound actions, override-gate latency under a scenario-appropriate budget, completeness of audit-trail reconstruction independent of agent self-report, and measured performance overhead relative to unconstrained agent operation.

**Aim 3 — Compliance grounding.** Cross-walk the architecture and evaluation results against IEC 62443, the NIST AI RMF, and NERC CIP, demonstrating that the design is compliance-oriented by construction rather than retrofitted.

### Scope

The initial architecture is deliberately scoped to supervisory/dispatch-tier and maintenance/scheduling-tier control decisions, where response-time budgets (seconds to minutes) are compatible with LLM inference latency and synchronous or asynchronous human review. Millisecond-scale protection-tier control (e.g., breaker/relay logic) is explicitly excluded — no LLM-based agent can meet those timing requirements, and the architecture does not claim otherwise. This boundary is a stated design decision, not a limitation discovered post hoc, and clarifies where agentic AI governance is a meaningful addition to OT operations versus where deterministic, sub-second systems remain the only appropriate mechanism.

### Expected Contributions

1. A reference architecture for auditable, constrained agentic AI in OT contexts, empirically validated rather than proposed conceptually.
2. A small, purpose-built policy language expressive enough for OT-native constraints (value ranges, rate-of-change limits, zone/conduit-based permissions), evaluated as part of the containment mechanism.
3. Empirical latency, containment, and auditability results against pre-registered criteria, providing a concrete benchmark for future work in this space.
4. A methodology transferable to a planned follow-on study extending the validated architecture to maritime autonomy systems, aligned with an active dual-use research call.

### Broader Significance

This work sits inside a research area — agentic AI in critical infrastructure — named as a distinct 2026 priority by national AI research strategy (NORA) and directly within the sectorial scope (energy, manufacturing, smart districts) of applied cybersecurity research centers such as NORCICS. It responds to a concrete, near-term need: infrastructure operators and regulators require validated architectures for governing autonomous agents before large-scale agentic deployment in these environments becomes routine, not after. The methodology and evaluation framework developed here are intended to generalize beyond the energy-sector validation case to other OT domains, including maritime autonomy, where dual-use safety and governance concerns are structurally similar.
