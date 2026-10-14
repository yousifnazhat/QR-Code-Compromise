# QR-Code-Compromise — QR Scanner-as-HID Research Bench

> Can a QR scanner compromise your system? This repository measures the question instead of asserting it.

**Origin:** started as a single-PoC writeup (see [ORIGIN-WRITEUP.md](ORIGIN-WRITEUP.md)) demonstrating a reverse shell via `Win+R` + a printed QR code on a USB keyboard-wedge scanner. It is now a six-phase research bench covering both sides of the vector: payload engineering and detection.

> [!WARNING]
> **Authorized lab research only.** Everything here is built for owned hardware and owned VMs. Written authorization is required for anything engagement-adjacent. No default C2 endpoints exist in this repo — all hosts are placeholders (`attacker.example`, RFC1918 example IPs) and real targets must be configured explicitly. See [docs/governance/policy.md](docs/governance/policy.md).

## The vector in one paragraph

A USB barcode/QR scanner configured as a HID keyboard wedge ("keyboard wedge" mode) is a trusted input device. A scanned code becomes keystrokes — at machine speed — into whatever has focus. On an unattended, unlocked Windows session, `Win+R` + one scan is equivalent to a USB Rubber Ducky attack, with no USB port needed and a paper-shreddable payload.

## Repository map

| Directory | Phase | Contents |
|---|---|---|
| [`lab/`](lab/) | P0 | HID replay rig firmware + host driver (`lab/rig/`), target-VM keystroke capture hook (`lab/capture/` — contract-#1 JSONL producer), baseline PoC reproduction kit (`lab/baseline/`) |
| [`data/`](data/) + [`tools/`](tools/) | P1 | Hardware/symbology measurement machinery: printable test sheets (28-condition QR sweep, Structured Append group), `scanlog.py` recorder, `descriptor_dump.sh` for HID-vs-CDC classification |
| [`qrducky/`](qrducky/) | P2 | `qr-ducky` CLI: layout-safe payload encoder (US/DE/FR-robust `alnum` mode), QR sheet generator (PDF/PNG), engagement beacon mode, calibration bench speaking the rig protocol |
| [`payloads/`](payloads/) | P3 | Run-dialog payload corpus (6 template classes: powershell-enc, mshta, curl, certutil, msiexec, UNC), manifest + validator, kill-chain matrix runner, AMSI/CLM matrix |
| [`detection/`](detection/) | P4 | Keystroke-timing injection detector (dataset tooling, features, baseline classifier), blue-team artifact runbook (36 rows), HID allowlisting feasibility toolkit |
| [`papers/`](papers/) | P5 | QR threat taxonomy (lure / keystroke-store / session-token) with verified bibliography, session-lock-window study design (IRB path), non-Windows feasibility plans, venue targets |
| [`COORDINATION.md`](COORDINATION.md) | fleet | Worktree/branch layout, frozen interface contracts, merge rules |

## Quickstart

```bash
# qr-ducky: encode a payload layout-safely, print a sheet, dry-run the bench
pip install -e './qrducky[dev]'
echo -n "powershell -nop -w hidden -enc <b64>" > payload.txt
qr-ducky encode --payload payload.txt --mode alnum      # survives US/DE/FR layouts
qr-ducky sheet  --payload payload.txt --out sheet.pdf --module 4 --ec M
qr-ducky bench  --target vm-alpha --payload payload.txt --dry-run

# payload corpus: render the matrix (never executes — VM runs are manual)
python3 payloads/validate_manifest.py                   # contract #4 conformance
python3 payloads/run_matrix.py payloads/targets.toml.example --dry-run

# detection: run the timing detector on the committed synthetic baseline
uv run --with pytest python -m pytest detection/tests -q
uv run python -m detection.detector.pipeline detection/dataset/samples/synthetic-baseline.jsonl --label source
```

**▶ End-to-end walkthrough** — payload → printed QR → the scan moment → execution → evidence collection: [`docs/tutorials/scan-to-execution.md`](docs/tutorials/scan-to-execution.md)

Test suites: `qrducky/` 98 tests · `detection/` 57 tests · `payloads/` validator + negative-path checks.

## Research status

| Workstream | Software | Remaining (physical) |
|---|---|---|
| W0.1/W0.3 baseline + rig | ✅ done | flash firmware; bench smoke |
| W0.2 scanner bench | — | procurement (3–5 imagers incl. BCMA-class) |
| W1.1–W1.4 hardware/symbology taxonomy | ✅ tooling done | descriptor dumps, sweep scans, SA protocol |
| W2.1–W2.4 qr-ducky | ✅ done | live bench against victim VM |
| W3.1–W3.4 payload engineering | ✅ corpus done | VM kill-chain exercises → `killchain.csv` |
| W4.1–W4.4 detection | ✅ synthetic baseline done | real contract-#1 logs → un-synthetic metrics; allowlist verdicts |
| W5.1–W5.3 survey | ✅ outlines/designs done | IRB gate (W5.2), GNOME/kiosk VM tests (W5.3) |

## Coordination & governance

This project is developed on a git-worktree fleet with frozen interface contracts — see [COORDINATION.md](COORDINATION.md) before contributing. Governance, authorization, and release policy: [docs/governance/policy.md](docs/governance/policy.md).

## License

MIT — see [LICENSE](LICENSE). The original writeup that started this project: [ORIGIN-WRITEUP.md](ORIGIN-WRITEUP.md).
