# ADF Successor adf-dev Basic Backup Install

## Summary

Installed a basic second-backup surface for the staged successor build-pack on
`adf-dev`.

## Scope

- staged the successor build-pack onto `adf-dev` through the PackFactory
  prepare and push workflow
- installed a user-cron backup entry for the staged successor pack
- ran one manual backup immediately to verify archive creation and metadata

## Installed Schedule

- host: `adf-dev`
- user: `adf`
- schedule: `17 3 * * *`
- wrapper script:
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1/job/run-pack-backup.sh`

## Backup Result

- backup root:
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1`
- first archive:
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1/archives/algosec-diagnostic-framework-successor-build-pack-v1-backup-20260403t015717z.tar.gz`
- wrapper-proof archive:
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1/archives/algosec-diagnostic-framework-successor-build-pack-v1-backup-20260403t015736z.tar.gz`
- manifests:
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1/manifests/algosec-diagnostic-framework-successor-build-pack-v1-backup-20260403t015717z.json`
  and
  `/home/adf/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1/manifests/algosec-diagnostic-framework-successor-build-pack-v1-backup-20260403t015736z.json`
- retention: `7`

## Verification Notes

- `prepare_remote_autonomy_target.py` passed for the successor `adf-dev`
  request
- `push_build_pack_to_remote.py` passed and staged the successor build-pack to
  the canonical remote path
- the cron block was present in `crontab -l`
- the manual backup created the first compressed archive plus manifest JSON
- the installed wrapper script also ran successfully and appended JSON output to
  the backup log
- the current remote verification bundle is preserved locally under
  `dist/candidates/adf-dev-backup-baseline/`
