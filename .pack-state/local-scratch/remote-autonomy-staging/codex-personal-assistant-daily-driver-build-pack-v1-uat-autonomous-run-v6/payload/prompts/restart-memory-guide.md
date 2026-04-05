# Restart Memory Guide

Restart memory is local continuity state for the next Codex session.

Use it for:

- the last important decision
- the next recommended action
- a blocker worth preserving
- an operator preference that should not be rediscovered
- a goal or alignment risk worth keeping in view
- a stable communication pattern that improves future collaboration

When a session produces a candidate stable pattern, prefer
`distill-session-memory` first. That keeps weak signals inspectable in
`.pack-state/session-distillation/` before they are promoted into durable
assistant memory.

Prefer explicit contracts first. Use memory for continuity and adaptation, not
as a replacement for PackFactory lifecycle, readiness, or deployment state.
