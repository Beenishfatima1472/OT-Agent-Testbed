# Implementation Sequence — Phase 3 Build

Ordered so each layer is independently testable before the next is built on top of it. Building top-down (agent first) makes early bugs impossible to localize; this order avoids that.

## Step 1 — Simulated process environment (build and test alone first)
- OpenPLC instance modeling the microgrid/BEMS: battery state, feeder load, grid-import status, demand-response schedule.
- Discrete accelerated-time loop (fixed ticks) wired in from the start, not retrofitted later.
- **Test in isolation:** manually drive setpoints/actions via script (no agent, no constraint layer yet) and confirm the physics/state model behaves correctly — battery drains and recharges plausibly, feeder capacity threshold triggers correctly, etc. Do not proceed until this is solid; every later component's evaluation depends on this being trustworthy.

## Step 2 — Action-space bounding engine + DSL (Component 1)
- Define the DSL grammar (range, rate-of-change, zone-permission primitives) against the actual scenario thresholds from the evaluation design doc.
- Implement the simulate→validate consequence-check step.
- **Test in isolation:** feed hand-written valid and invalid actions directly (no agent yet) and confirm correct accept/reject/re-prompt behavior, including scenario 6-style cumulative violations.

## Step 3 — Decision logging (Component 2)
- Structured log schema, hash-chaining (Component 4 folded in here since it's a property of the same log, not a separate build step).
- **Test in isolation:** confirm every disposition from Step 2's test actions produces a complete, correctly chained log entry; deliberately corrupt one entry and confirm tamper detection works.

## Step 4 — Override gate (Component 3)
- Risk-tier classification logic, synchronous/asynchronous routing, deny-by-default-on-timeout.
- **Test in isolation:** simulate both a timely and a timed-out human response and confirm correct disposition and logging in each case (this directly tests scenario 9 before the agent is even in the loop).

## Step 5 — Custom LLM agent harness
- Thin wrapper: proposal → Component 1 → Component 3 (if needed) → Component 2 logs → execution against Step 1's environment.
- Only now does the full pipeline exist end-to-end.
- **Test:** run scenarios 1–5 (nominal) first — these should mostly pass cleanly and validate the pipeline wiring itself.

## Step 6 — Full adversarial evaluation
- Run scenarios 6–10 against the complete pipeline.
- Collect containment rate, override latency, audit-completeness, and performance-overhead metrics against the pre-registered success criteria.
- This is the data that goes into the paper's Results section.

## Step 7 — Analysis and writing
- Populate the manuscript structure from the research statement and concept note.
- Report results honestly, including any scenarios where the architecture underperformed — a paper that reports a failure mode and analyzes it is more credible than one claiming a clean sweep.

## Why This Order

Each step produces something independently verifiable before the next step depends on it. If Step 5's end-to-end pipeline misbehaves, you'll know immediately whether the bug is in the agent harness itself or inherited from a component that was already tested alone in Steps 1–4 — that isolation is what makes debugging tractable and what makes the eventual results trustworthy rather than a black box.
