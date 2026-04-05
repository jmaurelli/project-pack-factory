# ASMS UI BusinessFlow and FireFlow systems pass

Date: 2026-03-25

## What changed
- Converted the BusinessFlow and FireFlow authenticated-path discovery into the ADF build-pack source and regenerated appliance-backed artifacts.
- Rebuilt the Starlight site from `dist/candidates/adf-baseline` and repointed the review server on port 18082 to that static output.

## What the observed path shows now
- The observed ASMS UI login path is still legacy-first: `/seikan/login/setup` and `POST /afa/php/SuiteLoginSessionValidation.php?clean=false` happen before later named modules.
- BusinessFlow is now the first named operational checkpoint in the customer-visible authenticated path. Apache showed `/BusinessFlow` redirects before submit and `POST /BusinessFlow/rest/v1/login` during sign-in.
- FireFlow remains a later auth-coupled module for now. Apache showed `CheckAuthentication` during sign-in and `FireFlowBridge.js` immediately after `/afa/php/home.php`.
- Keycloak remains in the observed auth chain, but not as the first post-shell hop and not as the first named module the engineer should chase.

## Support-useful checks now encoded
- BusinessFlow shallow and deep health through Apache.
- FireFlow auth-coupled checks using `CheckAuthentication`, `CommandsDispatcher`, and `FireFlowBridge.js` log correlation.
- Apache correlation that keeps the reproduced order honest instead of collapsing everything into a Keycloak-first model.

## Regeneration and verification
- `generate-support-baseline --target-label algosec-lab` passed and wrote to `dist/candidates/adf-baseline`.
- `generate-starlight-site --artifact-root dist/candidates/adf-baseline` passed.
- `pnpm build` passed for `dist/candidates/adf-baseline/starlight-site`.
- `http://127.0.0.1:18082/playbooks/asms-ui-is-down/` returned `HTTP/1.0 200 OK` from the rebuilt `adf-baseline` static site.

## Recommended next move
- Follow the authenticated path one level deeper into the first post-home customer-visible modules so ADF can decide whether BusinessFlow and FireFlow should stay inside the ASMS path or grow into richer subsystem-aware playbooks later.
