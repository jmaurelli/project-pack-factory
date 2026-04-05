# Headless Browser Proof Host Dependency Evidence

Recorded at: `2026-03-31T20:33:13Z`

## Summary

The root browser-proof wrapper is functioning, but the current host cannot
launch the downloaded Playwright Chromium runtime because required shared
libraries are missing.

This is a host-level blocker, not a PackFactory wrapper defect.

## Proof Report Evidence

Schema-valid fail-closed report:

- [proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260331t201817z/proof-report.json)

Key failure line from that report:

```text
libatk-1.0.so.0: cannot open shared object file: No such file or directory
```

## Direct Shared-Library Inspection

Command run:

```bash
ldd /home/orchadmin/project-pack-factory/.pack-state/browser-proof-runtime/playwright-browsers/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell
```

Missing libraries observed:

- `libatk-1.0.so.0`
- `libatk-bridge-2.0.so.0`
- `libatspi.so.0`
- `libXcomposite.so.1`
- `libXdamage.so.1`
- `libXfixes.so.3`
- `libXrandr.so.2`
- `libgbm.so.1`
- `libasound.so.2`

## Interpretation

The current failure happens before browser navigation and before any DOM-level
ADF assertions run.

That means:

- the request-file wrapper path is working
- the schema/report path is working
- runtime provisioning under `.pack-state/browser-proof-runtime/` is working
- but Chromium cannot start on this host yet

## Rerun Path After Host Provisioning

Once the missing host libraries are installed, rerun:

```bash
python3 tools/run_browser_proof.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/tmp/browser-proof-request.json \
  --output json
```
