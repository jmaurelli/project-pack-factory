# Restart Memory Guide

Restart memory is local continuity state for the next Codex session.

Use it for:

- the last important decision
- the next recommended action
- a blocker worth preserving
- an operator preference that should not be rediscovered
- a communication pattern or alignment risk worth carrying forward
- a business-review closeout that should refresh continuity for the next session

When a session produces a candidate stable pattern, prefer
`distill-session-memory` first. That keeps weak signals inspectable in
`.pack-state/session-distillation/` before they are promoted into durable
assistant memory.

Business-review closeout can also leave a weak carry-forward distillation so
repeated closeouts become richer inspectable history instead of one-off notes.

Do not use it as a replacement for PackFactory lifecycle, readiness, or
deployment state.
