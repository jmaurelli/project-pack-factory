# ASMS UI post-home modules systems pass

Date: 2026-03-25

## What changed
- Refined the ASMS UI Step 4 model so the first checks after `/afa/php/home.php` stay on immediate home-shell follow-ups and light Metro refresh traffic.
- Regenerated the appliance-backed support baseline and rebuilt the Starlight site from `dist/candidates/adf-baseline`.

## What the observed post-home path shows now
- The first observed activity after `/afa/php/home.php` was not a broad subsystem fan-out.
- The earliest post-home follow-ups were `FireFlowBridge.js`, `logo.php`, `GET /afa/getStatus`, `POST /afa/api/v1/bridge/refresh`, and `GET /afa/api/v1/license`.
- These are best treated as immediate ASMS home-shell and home-refresh checks that stay inside the ASMS playbook for now.
- `ms-watchdog` issue-center count calls appeared in the same time window, but from a different client address, so they currently look like a later subsystem candidate rather than the first post-home stop point for the reproduced browser flow.

## Support-useful model now encoded
- Keep `FireFlowBridge.js` and basic home-shell assets inside the ASMS UI playbook as immediate post-home checks.
- Keep Metro heartbeat and light bridge-refresh traffic inside the ASMS UI playbook as the first post-home app checks.
- Do not assume that every later subsystem route must appear in the first post-home second.
- Treat Notification Center and similar issue-count activity as a later subsystem candidate unless the reproduced browser minute proves it is the first failing stop point.

## Regeneration and verification
- `generate-support-baseline --target-label algosec-lab` passed.
- `generate-starlight-site --artifact-root dist/candidates/adf-baseline` passed.
- `pnpm build` passed for `dist/candidates/adf-baseline/starlight-site`.
- `http://127.0.0.1:18082/playbooks/asms-ui-is-down/` returned `HTTP/1.0 200 OK` after the rebuild.

## Recommended next move
- Follow the first later subsystem candidate from the post-home view, likely Notification Center or watchdog-linked issue counts, but keep it separate from the immediate ASMS home-shell path unless the reproduced browser flow shows it as the real first stop point.
