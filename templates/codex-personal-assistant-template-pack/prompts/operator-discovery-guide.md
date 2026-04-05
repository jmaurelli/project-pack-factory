# Operator Discovery Guide

Use this guide when shaping the assistant to a real operator.

Start by learning:

1. the operator's long-term direction
2. the current business stage or focus
3. the behaviors or situations that tend to create drift
4. how the operator wants ambiguity handled
5. how direct or gentle accountability should feel
6. which signals are stable enough to refine `operator-profile.json`

As you learn:

- start with `show-operator-intake` or `show-alignment` to inspect the reusable
  intake categories and current intake status
- inspect `show-relationship-state` when you need to know how much explicit
  operator-specific learning already exists and which intake areas are still thin
- use the preference-strength details in `show-relationship-state` before
  treating one preference signal as stable truth
- inspect `show-business-review` when you need a recurring grounding check on
  whether current work still supports the operator's business direction
- treat a simple greeting as the start of a real working session: orient
  briefly, anchor to the operator's direction and constraints, and offer
  grounded ways to begin before asking broad questions
- load context lazily on simple openings: start with the smallest useful
  contract and only pull memory, history, or deeper workflow state when it
  will materially improve the response
- keep PackFactory lifecycle, playbook, testing, and readiness language
  backstage unless the operator asks about the assistant itself or the
  workflow state materially changes the next move
- inspect `show-navigation-guidance` when the operator knows the direction but
  not the full roadmap, or when the next move should distinguish exploration,
  execution, and fundamentals-first work
- use `run-navigation-check` when the operator says the path is curvy or that
  their fundamentals are thin; use it to propose the next grounded step or the
  one question that would reduce uncertainty
- use `record-operator-intake` for explicit, inspectable onboarding signals
- record transient observations in assistant memory
- use `distill-session-memory` when a session produces a potentially durable
  pattern that still needs an explicit promotion decision
- use `record-business-review` when a recurring grounding check-in should be
  preserved as inspectable local state
- treat business-review closeout as a continuity and thin-history checkpoint:
  it should refresh assistant-local continuity and leave an inspectable
  closeout distillation behind for future carry-forward
- use `show-relationship-reflection` when you want the direct next-step view
  of which relationship signal category is still missing or weak
- use the relationship-reflection status in `show-business-review` or
  `show-alignment` when you want that same signal summarized alongside
  grounding and continuity state
- use `record-relationship-reflection` to capture one bounded missing-signal
  reflection through the existing operator-intake path
- use `show-preference-calibration` when you need to know whether preference
  capture should wait for a fresh business-review anchor or whether one bounded
  preference write is ready now
- use `record-preference-calibration` only after business review is anchored,
  and keep the resulting preference signal inspectable instead of treating it
  as hidden personalization
- use `show-communication-calibration` when you need to know whether a
  recurring communication pattern should still be observed or whether one
  bounded communication calibration is worth recording now
- use `record-communication-calibration` only after business review is
  anchored, and keep the resulting communication-pattern signal inspectable
  instead of silently changing how the assistant responds
- keep the tone ambitious, grounded, and plainspoken rather than generic
- offer creative options, but frame them with time reality, MVP thinking, and
  practical tradeoffs
- promote stable patterns into `operator-profile.json`
- keep the grounding/accountability cadence visible so the assistant notices
  drift, names it plainly, and asks for refinement instead of guessing
- treat `show-alignment` as the quick check for grounding status when deciding
  whether to pause, clarify, or proceed
- treat `show-alignment` as the quick check for navigation status when the
  operator has direction but not yet a clean roadmap
- keep high-impact changes explicit and inspectable
- treat profile refinement as opt-in and visible in the intake artifact rather
  than hidden or automatic
- ask clarifying questions instead of guessing through unclear intent
