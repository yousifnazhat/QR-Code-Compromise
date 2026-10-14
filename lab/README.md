# lab/ — Phase P0 Foundations

Foundations for the QR-Code-Compromise study: baseline reproduction of the
README chain (W0.1), scanner bench harness (W0.2, hardware-gated), and the
HID replay rig (W0.3). All modules emit or consume contract #1
(`docs/contracts/`, see COORDINATION.md) JSONL keystroke events.

| Directory | Deliverable | Status |
|---|---|---|
| `baseline/` | W0.1 PoC reproduction kit (payload builder, QR gen, listener scripts in `scripts/`) | software complete, smoke-tested |
| `capture/` | target-side keystroke hook (macOS + Windows) | software complete, smoke-tested |
| `rig/` | W0.3 ATmega32U4 HID replay firmware + host driver | software complete; **flashing is a physical slot** |

## Hardware-gated status (COORDINATION.md rule 5)

* **W0.2 scanner bench — expected-but-blocked (needs human):** real QR
  scanners, printed codes, and the Windows victim VM. The software side it
  feeds is ready: `capture/` (contract-#1 logs with `--source scanner`),
  P1's `data/scanners.csv` / `data/symbology.csv` schemas, and the QR
  generator in `baseline/`. Bench results land in P1's `data/raw/`, not
  here.
* **W0.3 physical steps:** flashing `rig/rig_replay/rig_replay.ino` onto a
  Pro Micro and replaying payloads against the lab victim VM.
* Baseline chain validation (scan → shell on listener) also needs the
  bench; `baseline/build_poc.py` output verification is software-only.

## Lab-only posture

Everything here is dual-use; each module carries an authorization note.
Lab-only on owned VMs/hardware with written authorization; placeholder
addresses only (`10.99.12.233` is documented EXAMPLE-ONLY); no default C2
endpoints in committed code (GX.2). Generated attack artifacts
(`baseline/out/`) are gitignored and never committed.
