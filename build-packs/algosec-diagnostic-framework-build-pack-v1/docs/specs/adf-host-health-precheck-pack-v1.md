# ADF Host Health Pre-Check Pack V1

## Purpose

`Host Health Pre-Check` is a shared ADF command pack.

Every major playbook should start with this same Linux host check before it
moves into subsystem-specific diagnostics.

Examples:

- `ASMS UI is down`
- `FireFlow Backend`
- `Messaging and Data`

This pack exists because support engineers troubleshoot the Linux host and the
application stack together. Disk, inode, memory, OOM, CPU, and load checks are
fast, common, and useful in almost every case.

The point is not to collect raw Linux facts for their own sake.

The point is to answer a systems question early:

- can the host still support useful work for the application components and the
  system as a whole

Each command should help the engineer decide whether current host pressure is
already enough to break Apache, Keycloak, Metro, logs, temp-file work, or the
next subsystem branch.

## Standard Rules

- Keep the command order the same in every playbook.
- Prefer `-h` or `--human-readable` where supported.
- Keep the wording the same in every playbook unless a check truly needs a
  subsystem-specific addition.
- Use the ADF language standard labels:
  - `Check`
  - `Run`
  - `Verification`
  - `Linux note`
  - `Known working example`

## Standard Command Sequence

### 1. Check storage pressure on runtime filesystems

- `Run`: `df -h`
- `Verification`: Main runtime filesystems still have enough free space for
  logs, temp files, and service work.
- `Linux note`: Storage pressure means the filesystem is close to full.
  Apache, Keycloak, Metro, installers, and log writers may all fail to do
  useful work.

### 2. Check inode pressure on runtime filesystems

- `Run`: `df -ih`
- `Verification`: Main runtime filesystems still have free inodes for logs,
  temp files, sockets, and service output.
- `Linux note`: A filesystem can still have free disk space but fail when it
  has no free inodes left. That can block useful work even when `df -h` still
  looks fine.

### 3. Check memory pressure on JVM-backed services

- `Run`: `free -h`
- `Verification`: Available memory is still present and swap is not carrying
  active pressure for the host.
- `Linux note`: Memory pressure means the server is low on available memory.
  Java services may slow down, hang, fail health checks, or get killed later.

### 4. Check current host load pressure

- `Run`: `uptime`
- `Verification`: Load is not unexpectedly high for the host and does not
  already explain the application symptom.
- `Linux note`: Load average shows how busy the server is. High load can mean
  CPU pressure, blocked work, or heavy I/O wait before you even reach the
  application-specific branches.

### 5. Check recent memory-kill pressure

- `Run`: `journalctl -k --since "24 hours ago" --no-pager | grep -i -E "out of memory|oom|killed process"`
- `Verification`: No recent Out Of Memory lines are returned.
- `Linux note`: OOM means Out Of Memory. Linux may kill a process to protect
  the server. If this happened recently, downstream UI symptoms may only be
  the visible side effect.

### 6. Check which process owns CPU pressure right now

- `Run`: `ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 10`
- `Verification`: No unexpected process is consuming enough CPU to starve the
  rest of the system.
- `Linux note`: This shows which process currently owns CPU pressure. It helps
  identify whether the engineer should stop at host pressure before moving into
  the next subsystem branch.

## Scope Boundary

This shared pack is the first-pass host check.

It should answer:

- is the host healthy enough for the next subsystem checks to mean anything

It should not become:

- a broad Linux forensic sweep
- a random list of commands with no system interpretation

It does not include deeper follow-up checks such as:

- file-handle limits
- file locks
- broad noisy error-log sweeps
- deeper process forensics

Those belong in follow-up packs or subsystem-specific branches after the shared
host pre-check.

## Reuse Guidance

- Reuse this pack at the start of every major playbook.
- Keep the commands read-only.
- Add `Known working example` output from the target appliance where helpful,
  but do not change the command sequence or the core wording casually.
- If a playbook needs one extra host-level check, place it after this shared
  pack rather than rewriting the pack itself.
