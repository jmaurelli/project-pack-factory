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

### 1. Check disk space

- `Run`: `df -h`
- `Verification`: Main filesystems have free space and are not near `100%`
  use.
- `Linux note`: Disk pressure means the filesystem is close to full. Services
  may fail to write logs, temp files, or runtime data.

### 2. Check inode usage

- `Run`: `df -ih`
- `Verification`: Main filesystems have free inodes and are not near `100%`
  inode use.
- `Linux note`: A filesystem can still have free disk space but fail when it
  has no free inodes left.

### 3. Check memory

- `Run`: `free -h`
- `Verification`: Available memory is present and swap is not under heavy use.
- `Linux note`: Memory pressure means the server is low on available memory.
  The server may slow down, use swap, or kill a process.

### 4. Check system load

- `Run`: `uptime`
- `Verification`: Load is not unexpectedly high for the host.
- `Linux note`: Load average shows how busy the server is. High load can mean
  CPU pressure, blocked work, or heavy I/O wait.

### 5. Check recent OOM events

- `Run`: `journalctl -k --since "24 hours ago" --no-pager | grep -i -E "out of memory|oom|killed process"`
- `Verification`: No recent Out Of Memory lines are returned.
- `Linux note`: OOM means Out Of Memory. Linux may kill a process to protect
  the server.

### 6. Check top CPU consumers

- `Run`: `ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 10`
- `Verification`: No unexpected process is consuming excessive CPU.
- `Linux note`: This shows which processes are using the most CPU right now.
  It helps identify a process that may be starving the rest of the system.

## Scope Boundary

This shared pack is the first-pass host check.

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
