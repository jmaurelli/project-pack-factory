# AlgoSec Lab Remote Target

This directory stores the reusable remote target configuration for the
controlled AlgoSec lab appliance used by ADF.

## Current Target

- Host: `10.167.2.150`
- User: `root`
- Target label: `algosec-lab`

## Notes

- This appliance lands in the AlgoSec interactive menu on login.
- To reach the shell, press `a` at the menu prompt.
- `Ctrl+C` may also work as an escape path, but `a` is the expected path.
- Remote Codex shell work may need non-login shell commands if the appliance
  profile drops back into the menu.
- Key-based SSH access is configured locally through `~/.ssh/config`.
- Secrets such as passwords and private keys are not stored in this repo.

## Request File

- `remote-autonomy-run-request.json`

Use that request file with:

```bash
python3 tools/prepare_remote_autonomy_target.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/algosec-lab/remote-autonomy-run-request.json --output json
python3 tools/push_build_pack_to_remote.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/algosec-lab/remote-autonomy-run-request.json --output json
python3 tools/run_remote_autonomy_loop.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/algosec-lab/remote-autonomy-run-request.json --output json
```
