---
title: Linux host under pressure
description: Use this when multiple services are acting strangely and the host itself may be the real problem.
sidebar:
  label: Linux host under pressure
  order: 3
---

Use this when multiple services are acting strangely and the host itself may be the real problem.

## Cockpit layout

<div class="proto-cockpit-shell">
  <div class="proto-cockpit-topbar">
    <div class="proto-panel proto-cockpit-strip">
      <p class="proto-kicker">Case mode</p>
      <p>Live triage over SSH. Reduce guesswork. Keep the next command visible.</p>
    </div>
    <div class="proto-panel proto-cockpit-strip">
      <p class="proto-kicker">Core surfaces</p>
      <div class="proto-chip-row">
        <span class="proto-chip">disk</span>
        <span class="proto-chip">memory</span>
        <span class="proto-chip">inodes</span>
        <span class="proto-chip">locks</span>
      </div>
    </div>
  </div>
  <div class="proto-cockpit-grid">
    <aside class="proto-cockpit-nav proto-panel">
      <p class="proto-kicker">Quick jump</p>
      <div class="proto-cockpit-jumps"><a class="proto-cockpit-jump" href="#host-step-1">
  <span class="proto-route-step">Step 1</span>
  <strong>Disk</strong>
</a>
<a class="proto-cockpit-jump" href="#host-step-2">
  <span class="proto-route-step">Step 2</span>
  <strong>Memory</strong>
</a>
<a class="proto-cockpit-jump" href="#host-step-3">
  <span class="proto-route-step">Step 3</span>
  <strong>File pressure</strong>
</a>
<a class="proto-cockpit-jump" href="#host-step-4">
  <span class="proto-route-step">Step 4</span>
  <strong>Logs</strong>
</a></div>
    </aside>
    <div class="proto-cockpit-main">
      <div class="proto-panel proto-cockpit-strip">
        <p class="proto-kicker">Command deck</p>
        <p>Keep the next command and the healthy reference close together so the engineer can glance left and run right.</p>
      </div>
<details id="host-step-1" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 1</span>
  <span class="proto-step-heading">
    <strong>Disk</strong>
    <span>Check disk first. Confirm /, /var, and /data still have free space.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check disk first. Confirm /, /var, and /data still have free space.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Disk pressure is one of the fastest ways to make many unrelated services fail at once.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check disk usage</p>

```bash
df -h
```

**Healthy output:** Critical filesystems still have free space.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- A service cannot write logs, temp files, or state when the host is full.
</div>

**Known-good output:**

```text
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   60G   18G   43G  30% /
/dev/mapper/rl-var    20G   11G    9G  56% /var
/dev/mapper/rl-data  240G   22G  219G   9% /data
```

</div>

</details>

<details id="host-step-2" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 2</span>
  <span class="proto-step-heading">
    <strong>Memory</strong>
    <span>Check memory pressure next. Confirm the host still has available memory and no recent OOM events.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check memory pressure next. Confirm the host still has available memory and no recent OOM events.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>When memory is low, Linux may kill processes and create scattered symptoms across the application stack.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check memory usage</p>

```bash
free -h
```

**Healthy output:** Available memory is present and swap is not heavily used.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This is the fastest memory snapshot for triage.
</div>

**Known-good output:**

```text
              total        used        free      shared  buff/cache   available
Mem:           64Gi        32Gi       6.4Gi       3.0Gi        25Gi        28Gi
Swap:          24Gi          0B        24Gi
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check recent OOM events</p>

```bash
journalctl -k --since '-24 hours' --no-pager | grep -i -E 'out of memory|oom|killed process' | tail -n 20
```

**Healthy output:** No recent OOM lines are returned.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This confirms whether Linux has already started killing processes.
</div>

**Known-good output:**

```text
No output
```

</div>

</details>

<details id="host-step-3" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 3</span>
  <span class="proto-step-heading">
    <strong>File pressure</strong>
    <span>Check inode and file pressure. Confirm the host is not out of inodes and not trapped by stale file locks.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check inode and file pressure. Confirm the host is not out of inodes and not trapped by stale file locks.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Disk space alone does not explain many Linux failures. Inodes and locks matter too.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check inode usage</p>

```bash
df -ih
```

**Healthy output:** Critical filesystems still have free inodes.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Inode exhaustion looks like a file error even when normal disk space appears free.
</div>

**Known-good output:**

```text
Filesystem          Inodes IUsed IFree IUse% Mounted on
/dev/mapper/rl-root    30M  360K   30M    2% /
/dev/mapper/rl-var     12M  210K   12M    2% /var
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check for common stale lock files</p>

```bash
find /var/lock /var/run /tmp -maxdepth 2 -type f | head -n 20
```

**Healthy output:** No suspicious stale application lock files are blocking normal service behavior.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- A stale lock can stop one service, a batch job, or an application restart even when the host looks healthy.
</div>

</div>

</details>

<details id="host-step-4" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 4</span>
  <span class="proto-step-heading">
    <strong>Logs</strong>
    <span>Check kernel and service logs. Look for pressure signals that repeat across more than one service.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check kernel and service logs. Look for pressure signals that repeat across more than one service.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Shared host pressure usually leaves clues in more than one place.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Review kernel warnings</p>

```bash
journalctl -k -n 80 --no-pager
```

**Healthy output:** No recurring OOM, IO, mount, or filesystem warnings appear.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Kernel warnings often reveal the host-level issue before application logs explain it clearly.
</div>

</div>

</details>

    </div>
  </div>
</div>

<script>
(() => {
  const openHashTarget = () => {
    const rawHash = window.location.hash;
    if (!rawHash || rawHash.length < 2) return;
    const target = document.getElementById(decodeURIComponent(rawHash.slice(1)));
    if (!target) return;
    const details = target.matches('details') ? target : target.closest('details');
    if (details) details.open = true;
  };
  window.addEventListener('hashchange', openHashTarget);
  openHashTarget();
})();
</script>
