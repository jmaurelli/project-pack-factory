# ASMS UI canonical-template split

Date: 2026-03-29

This checkpoint separates the reusable canonical template from the real
operator playbook.

What changed:

- `canonical-playbook-template` is now a placeholder-only reference page.
- The real `ASMS UI is down` playbook now publishes separately at
  `/playbooks/asms-ui-is-down/`.
- The site overview now points operators to the live playbook first and keeps
  the template secondary.
- The sidebar now lists `Playbooks` before `Canonical Template`.

Local generated pages:

- `dist/candidates/adf-baseline/starlight-site/src/content/docs/canonical-playbook-template.md`
- `dist/candidates/adf-baseline/starlight-site/src/content/docs/playbooks/asms-ui-is-down.md`
- `dist/candidates/adf-baseline/starlight-site/src/content/docs/index.md`

Validation:

- `validate-project-pack` passed.
- `generate-starlight-site` passed.

Why this matters:

- Support engineers now have one clean operator route to open during a live
  customer session.
- The canonical template stays available for future playbooks without being
  confused with live diagnostic guidance.
