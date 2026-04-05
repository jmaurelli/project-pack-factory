# Headless Browser Proof Post-Provisioning Validation

Recorded at: `2026-04-01T14:19:33Z`

## Summary

After the host-level Ubuntu 24.04 browser dependencies were installed, the
PackFactory browser-proof path moved from fail-closed launch failure to a full
passing end-to-end proof.

This validates both parts of the follow-up:

- the host-readiness check now reports `ready`
- the real browser proof now gets past launch, navigates the live ADF page, and
  passes its page-level assertions

## Host Readiness Evidence

Schema-valid readiness report:

- [host-readiness-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-host-readiness-adf_field_manual_hash_target_opens-20260401t141715z/host-readiness-report.json)

Key result:

- `readiness_status`: `ready`
- `missing_shared_libraries`: `[]`

## Browser Proof Evidence

Schema-valid passing proof report:

- [proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260401t141715z/proof-report.json)

The proof now confirms:

- the browser launches successfully
- the page loads at `ASMS UI is down`
- the overview link for Step 3 is present
- the Step 3 card starts collapsed
- clicking the overview link lands on `#manual-ui-and-proxy-step-3`
- the target Step 3 card opens automatically after navigation
- the summary count `7 commands` matches the detected run-block count

## Interpretation

The earlier host-library blocker is no longer active on this host.

That means the PackFactory browser-proof control plane is now fully usable for
the bounded ADF field-manual proving-ground recipe on this machine.

## Validation

Commands rerun:

```bash
python3 tools/browser_proof_host_readiness.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --proof-kind adf_field_manual_hash_target_opens \
  --output json

python3 tools/run_browser_proof.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/tmp/browser-proof-request.json \
  --output json

python3 tools/validate_factory.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output json
```
