# AlgoSec Lab Downstream Target

This directory stores the downstream target context for the controlled AlgoSec
lab appliance used by ADF.

In the current split-host model, this appliance is no longer the PackFactory
remote Codex host.

It is the downstream application target reached from the remote ADF runtime on
`adf-dev`.

The current live PackFactory remote-runtime request files now live under:

- `docs/remote-targets/adf-dev/`

## Downstream Target

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

For the current split-host model, read those notes as the downstream
`adf-dev -> algosec-lab` connection constraints rather than as the PackFactory
root remote-runtime contract.

## Connection Profile

- `target-connection-profile.json`
- `lab-target-inventory.json`

This is the current pack-local profile for the `adf-dev -> algosec-lab` hop.

It records:

- target label
- SSH destination defaults
- non-login shell launcher defaults
- timeout defaults
- bounded retry defaults

The inventory file is a separate planning surface for alternate labs. Keep
`target-connection-profile.json` as the active single-target helper input, and
use `lab-target-inventory.json` to remember other candidate lab IPs and quick
feature probes without breaking the current helper flow.

The staged build pack on `adf-dev` can use that profile through the pack-local
CLI commands:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-preflight --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-heartbeat --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-shell-command --project-root . --command "hostname" --output json
```

## Historical Direct-Host Request

The `remote-autonomy-run-request.json` in this directory is a retained
historical artifact from the earlier direct-to-appliance bootstrap path.

Do not use it as the default request for the current split-host `adf-dev`
runtime model.

Use `docs/remote-targets/adf-dev/README.md` for the current PackFactory
request surfaces.

## FireFlow Lab Selection Note

Before spending more FireFlow-mapping effort on a candidate lab, probe:

```bash
/usr/share/fireflow/local/sbin/fireflow_activation.sh isEnabled
```

That is the better quick capability check for whether FireFlow is enabled on
the target appliance. The script checks the appliance-local activation marker
`/usr/share/fireflow/local/etc/site/fireflow_enabled`.

Use `/home/afa/.fa/config` as supporting context, especially:

```bash
grep -E '^FireFlow_configured=' /home/afa/.fa/config
```

Treat the activation script plus indicator file as the primary gate, and treat
the config value as supporting context rather than as the only enablement
signal. Neither check is full proof that the whole FireFlow workflow path is
healthy, but together they are a much better early routing signal than the
older `fireflow_enable` heuristic.
