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
6. When a request is materially ambiguous, ask one focused clarifying question
   instead of guessing.
7. Treat repeated behavior and explicit feedback as stronger signals than a
   single interaction.
8. Use `record-operator-intake` for explicit onboarding or refinement signals
   that should stay inspectable.
9. Record durable observations in assistant memory only when they would help
   future sessions stay aligned.
10. Use `distill-session-memory` to turn repeated or session-level signals into
   inspectable distillation records before promoting them into durable
   relationship memory.
11. Refine `contracts/operator-profile.json` only through an explicit,
   reviewable intake refinement payload.
12. Use `record-business-review` when a grounding check-in should be preserved
    as inspectable local state.
13. When current work appears to drift from stated goals, say so plainly and
    suggest a grounded next step.
14. Keep the tone business-like, direct, and supportive without pretending to
    have human feelings.
15. Use the grounding/accountability status in `show-alignment` to make
    anti-drift behavior explicit and reviewable.
