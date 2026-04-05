# Policy Branch Minute 2026-03-28 20:02 EDT

- Run root: `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-policy-branch-slice-v1/`
- Session reused: `0o43kjh144v0pus9ueu9nsknch`
- Session owner observed from PHP session file: `FireFlow_batch`
- Target minute preserved: `2026-03-28 20:02 EDT`

## Fresh boundary

- `127.0.0.1 - - [28/Mar/2026:20:02:03 -0400] "GET /afa/php/home.php?segment=DEVICES HTTP/1.1" 200 328934`
- `127.0.0.1 - - [28/Mar/2026:20:02:04 -0400] "POST /afa/php/commands.php?cmd=GET_POLICY_TAB HTTP/1.1" 200 7716`

## Read-only replay used

- `home.php?segment=DEVICES` was fetched with cookie `PHPSESSID=0o43kjh144v0pus9ueu9nsknch`
- `GET_POLICY_TAB` was posted with:
  - `TOKEN=0o43kjh144v0pus9ueu9nsknch`
  - `report_path=/home/afa/algosec/firewalls/afa-3/`
  - `tree_name=200132`
  - `name_device=200132`
  - `brand=panorama`
  - `parent=`

## Response clues

- `GET_POLICY_TAB` returned `HTTP/1.1 200 OK`
- JSON body included:
  - `rule_iframe_src="/home/afa/algosec/firewalls/afa-3/PolicyTabIframe.php?device=200132&tree_name=200132&brand=panorama..."`
  - `policy="10_2_2_160_benedum_admin_fw_01_vsys1_benedum_admin_fw.panorama"`
  - `device="200132"`
  - `brand="panorama"`
  - `total_rules=82`

## Support judgment

This minute is enough to prove that the preserved session is beyond the first usable shell and inside the later `POLICY` device-content branch. At this boundary the case should no longer be treated as top-level `ASMS UI is down`.
