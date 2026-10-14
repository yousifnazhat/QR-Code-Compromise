# Phase Fleet — Coordination Charter

Multi-worktree research layout. One repo, six phase branches, disjoint directories so merges never conflict. The coordinator (orchestrator agent) owns `master`, the interface contracts, and integration order.

## Fleet map

| Worktree | Branch | Phase charter | Owns (in-repo dirs) |
|---|---|---|---|
| `main/` | `master` | Governance (GX.1–2), integration, releases | `docs/contracts/`, `docs/governance/` |
| `p0-foundations/` | `phase/p0-foundations` | W0.1 lab baseline · W0.2 scanner bench · W0.3 HID replay rig | `lab/` |
| `p1-hardware-matrix/` | `phase/p1-hardware-matrix` | W1.1 scanner class matrix · W1.2 wedge quirks · W1.3 symbology reliability · W1.4 Structured Append | `data/` |
| `p2-tooling/` | `phase/p2-tooling` | W2.1 qr-ducky generator · W2.2 layout-safe encoder · W2.3 engagement mode · W2.4 calibration harness | `qrducky/` |
| `p3-payloads/` | `phase/p3-payloads` | W3.1 LOLBin kill-chain · W3.2 inline vs staged · W3.3 anti-forensics · W3.4 AMSI/CLM matrix | `payloads/` |
| `p4-detection/` | `phase/p4-detection` | W4.1 timing dataset · W4.2 detector · W4.3 artifact runbook · W4.4 allowlisting feasibility | `detection/` |
| `p5-survey/` | `phase/p5-survey` | W5.1 taxonomy paper · W5.2 lock-window study · W5.3 non-Windows targets | `papers/` |
| `p6-mobile-lure/` | `phase/p6-mobile-lure` | W6.1 mobile URL-surface taxonomy · W6.2 known chain-class inventory · W6.3 emulator rig · W6.4 defender parity · W6.5 novel-chain research (disclosure-gated per policy §7) · W6.6 iOS surface taxonomy · W6.7 iOS chain-class inventory · W6.8 iOS simulator rig | `mobile/` |

Scope rule: commits land only in your phase's directories. Shared contracts live in `docs/contracts/` and change only via coordinator-approved PR.

## Interface contracts (frozen until amended)

### 1. Keystroke event log — P0 produces, P4 consumes
JSONL, one event per line, UTF-8, written by `lab/capture/` (target-VM hook) and `lab/rig/` (replay rig):
```json
{"ts_ms": 123456789, "event": "keydown", "keycode": 65, "source": "human|scanner|rig", "device": "model-or-rig-id", "session": "sess-017"}
```
`ts_ms` = monotonic ms. `source` and `session` are mandatory labels — P4's dataset is built from these.

### 2. qr-ducky CLI — P2 implements, P0/P3 consume
```
qr-ducky encode --payload <file|-> --mode alnum|hex|b64 [--layout US|DE|FR]   # layout-safe encoding (W2.2)
qr-ducky sheet  --payload <file> --out <pdf> [--module 4mm] [--ec M]           # print sheet (W2.1)
qr-ducky bench  --target <vm-name> [--repeat N]                                # calibration harness (W2.4)
```
Exit codes: 0 success, 1 runtime, 2 usage/config, 3 documented not-implemented boundary (structured JSON log to stderr; config discovery `--config` > `$QRDUCKY_CONFIG` > `./qrducky.toml`).

**Additive flags (coordinator-approved, 2026-10-14):** `encode --json` (machine-readable keystroke stream + decoder hint); `sheet --mode/--layout/--png` (P0 prints encoded sheets; PNG for benches without vector printers); `encode|sheet --beacon-id ID --engage-target NAME` (W2.3 — target must be declared in `[engagement.targets]`, no default endpoints, GX.2); `bench --payload F --dry-run` (bench must not invent payloads; dry-run emits the exact `lab/rig` protocol conversation, live mode without rig/pyserial exits 3). `bench` speaks P0's rig serial protocol verbatim (`lab/rig/README.md`) — one protocol, no second invention. `qrducky/pdfsheet.py` is P1's stdlib PDF writer extracted as a package module (byte-compatible with `tools/gen_test_sheets.py`; keep in sync or coordinate).

### 3. Hardware/symbology matrices — P1 produces, P2 defaults + P5 consume
- `data/scanners.csv`: `model,vendor,interface,attackable,descriptor_hash,prefix,suffix,min_delay_ms,max_cps,notes`
- `data/symbology.csv`: `symbology,ec_level,medium,module_mm,distance_cm,angle_deg,attempts,successes,mean_decode_s`
One row per observation. Raw logs under `data/raw/` (gitignored).

### 4. Payload manifest — P3 produces, P4 runbook consumes
`payloads/manifest.yaml`, one entry per payload:
```yaml
- id: mshta-001
  runner: winr | powershell | mshta | curl | certutil | msiexec | unc
  staging: inline | staged
  layout_safe: true|false
  win_build: "1909"
  amsi: bypassed|blocked|na
  notes: ""
```
Kill-chain verdicts go to `payloads/results/killchain.csv` (columns: `payload_id,runner,mitigation,verdict`).
**Locked ID set (frozen 2026-10-14; P3 manifest @8276995, P4 runbook keys to this verbatim):** `ps-enc-001`, `mshta-001`, `curl-001`, `certutil-001`, `msiexec-001`, `unc-001` — names and order immutable without coordinator approval. Runner↔ID binding: powershell→ps-enc-001, mshta→mshta-001, curl→curl-001, certutil→certutil-001, msiexec→msiexec-001, unc→unc-001.

### 5. Detection artifacts — P4 produces
`detection/dataset/` (built from contract #1 logs + labels), `detection/detector/`, `detection/runbook.md` (artifacts per contract #4 payload exercised).

## Merge & integration rules

1. Phase branches PR into `master` — no direct commits to `master` except contracts/governance by coordinator.
2. Integration order: `p0` → `p1` → `p2` → (`p3` ∥ `p4`) → `p5`. Dependencies are on **data**, not on branch existence — build ahead of the order, merge in it.
3. Rebase onto `master` before opening a PR: `git fetch origin && git rebase master` inside the worktree.
4. Contract amendments: open a PR touching only `docs/contracts/`; coordinator merges or rejects; consumers re-sync after.
5. Hardware-gated items (W0.2, W1.x physical scans) log expected-but-blocked status in the phase dir so software tracks don't stall on them.

## Governance

Lab-only. Owned VMs/hardware, written authorization for anything field-adjacent. `docs/governance/policy.md` (GX.1) lands on `master` before any W5.2 field work. No default C2 endpoints in any committed code (GX.2).
