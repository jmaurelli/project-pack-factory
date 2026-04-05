# REPORTS Branch Exact Minute

- Run id: `algosec-diagnostic-framework-build-pack-v1-reports-branch-slice-v2`
- Observed minute: `2026-03-28 19:27 EDT`
- Boundary: later-content REPORTS branch after the first usable shell
- Method: reused one live AFA web session on the lab, loaded `home.php?segment=DEVICES`, extracted the matching in-page token, and replayed `GET_REPORTS` from localhost on the target host

## Apache Window

- `127.0.0.1 - - [28/Mar/2026:19:27:29 -0400] "GET /afa/php/home.php?segment=DEVICES HTTP/1.1" 200 328934`
- `127.0.0.1 - - [28/Mar/2026:19:27:30 -0400] "GET /afa/php/commands.php?cmd=GET_REPORTS&TOKEN=<redacted> HTTP/1.1" 200 99`

## Response

- `GET_REPORTS` returned `bCmdStatus=true` with an empty table payload (`recordsTotal=0`).
- The same session still rendered `AlgoSec - Home` and the standard shell markers before the REPORTS request.

## Support Judgment

This case has crossed out of top-level `GUI down` for this session. The useful next branch is REPORTS-specific content or downstream workflow behavior, not the first-shell or Metro-backed home-shell boundary.

## Residual Risk

This checkpoint reused an already-live authenticated web session instead of reproducing REPORTS from a fresh login minute.
