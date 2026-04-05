# Operator Discovery Guide

Use this guide when the assistant is learning how to work with the operator.

1. Start with `contracts/operator-profile.json` and
   `contracts/partnership-policy.json`.
2. Inspect `show-operator-intake` before assuming which onboarding signals are
   already stable.
3. Inspect `show-relationship-state` when you need to know how much explicit
   operator-specific learning already exists and what is still missing.
4. Use the preference-strength details in `show-relationship-state` before
   treating one preference signal as stable truth.
5. Inspect `show-business-review` when you need a recurring grounding check on
   whether current work still supports the operator's business direction.
6. Inspect `show-navigation-guidance` when the operator knows the direction but
   not the full roadmap, or when the next move should distinguish exploration,
   execution, and fundamentals-first work.
7. Use `run-navigation-check` when the operator says the path is curvy or that
   their fundamentals are thin; use it to propose the next grounded step or
   the one question that would reduce uncertainty.
8. When a request is materially ambiguous, ask one focused clarifying question
   instead of guessing.
9. Treat repeated behavior and explicit feedback as stronger signals than a
   single interaction.
10. Use `record-operator-intake` for explicit onboarding or refinement signals
   that should stay inspectable.
11. Record durable observations in assistant memory only when they would help
   future sessions stay aligned.
12. Use `distill-session-memory` to turn repeated or session-level signals into
   inspectable distillation records before promoting them into durable
   relationship memory.
13. Refine `contracts/operator-profile.json` only through an explicit,
   reviewable intake refinement payload.
14. Use `record-business-review` when a grounding check-in should be preserved
    as inspectable local state.
15. Treat business-review closeout as a continuity and thin-history checkpoint:
    it should refresh assistant-local continuity and leave an inspectable
    closeout distillation behind for future carry-forward.
16. Use `show-relationship-reflection` when you want the direct next-step view
    of which relationship signal category is still missing or weak.
17. Use the relationship-reflection status in `show-business-review` or
    `show-alignment` when you want that same signal summarized alongside
    grounding and continuity state.
18. Use `record-relationship-reflection` to capture one bounded missing-signal
    reflection through the existing operator-intake path.
19. Use `show-preference-calibration` when you need to know whether preference
    capture should wait for a fresh business-review anchor or whether one
    bounded preference write is ready now.
20. Use `record-preference-calibration` only after business review is anchored,
    and keep the resulting preference signal inspectable instead of treating it
    as hidden personalization.
21. Use `show-communication-calibration` when you need to know whether a
    recurring communication pattern should still be observed or whether one
    bounded communication calibration is worth recording now.
22. Use `record-communication-calibration` only after business review is
    anchored, and keep the resulting communication-pattern signal inspectable
    instead of silently changing how the assistant responds.
23. When current work appears to drift from stated goals, say so plainly and
    suggest a grounded next step.
24. Keep the tone business-like, direct, and supportive without pretending to
    have human feelings.
25. Use the grounding/accountability status in `show-alignment` to make
    anti-drift behavior explicit and reviewable.
24. Use the navigation guidance status in `show-alignment` to keep a stable
    north star even when the tactical path is curvy.
