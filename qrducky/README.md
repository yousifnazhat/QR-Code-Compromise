# qrducky — qr-ducky tooling (P2)

QR-scanner-as-HID-keyboard keystroke-injection tooling for the
QR-Code-Compromise research project. Implements **contract #2** of
`COORDINATION.md`:

```
qr-ducky encode --payload <file|-> --mode alnum|hex|b64 [--layout US|DE|FR]
qr-ducky sheet  --payload <file> --out <pdf> [--module 4mm] [--ec M]
qr-ducky bench  --target <vm-name> [--repeat N]
```

Config via `qrducky.toml` (`--config`, `$QRDUCKY_CONFIG`, `./qrducky.toml`).
Exit 0 = success; nonzero = failure with a structured JSON log on stderr.
Additive flags beyond contract #2 are listed in `contract-amendments.md`.

## AUTHORIZATION — LAB ONLY

This package is **dual-use research tooling**: it encodes payloads for
keystroke-injection attacks and drives a HID replay rig. Use it **only on
systems you own or have written authorization to test** (GX.1/GX.2,
`docs/governance/policy.md`). There are **no default endpoints** anywhere in
this code: engagement/bench targets must be declared explicitly in
`qrducky.toml`; example URLs use `attacker.example` (documentation reserved
name, RFC 2606-style lab placeholder). Do not commit payloads containing real
infrastructure.

## Modules

| Module | Purpose |
|---|---|
| `qrducky.layouts` | HID usage-ID -> char tables for US/DE(QWERTZ)/FR(AZERTY), incl. dead keys |
| `qrducky.keystrokes` | naive-US vs layout-native keystroke streams + layout simulation |
| `qrducky.encoder` | W2.2 layout-safe encoders (`alnum`, `hex`, `b64`) + reference decoders + PS decode hints |
| `qrducky.sheet` | W2.1 print sheets: segno QR -> PDF (via `pdfsheet`) / PNG, module size, quiet zone, crop marks, EC pinning |
| `qrducky.pdfsheet` | stdlib-only PDF writer (extracted from P1 `tools/gen_test_sheets.py`) |
| `qrducky.engagement` | W2.3 per-target variant tagging (`--beacon-id`) |
| `qrducky.bench` | W2.4 calibration harness speaking the P0 rig serial protocol |

## The layout-safe encoder (W2.2 — research core)

A QR scanner configured as a US-layout HID keyboard emits **positional**
keystrokes; the target OS interprets them through its **active layout**. The
simulation matrix (payload -> encoded text -> simulated keystrokes -> decoded
equality) yields:

| mode | US-naive stream | DE | FR | note |
|---|---|---|---|---|
| `b64` | ok | **FAIL** | **FAIL** | `+`, `/`, `=` sit on DE/FR dead-key/alt positions; y/z swap on DE; a/q/z/w/m remap on FR |
| `hex` | ok | ok | **FAIL** | FR digits require Shift (& é " ' ( - è _ ç à) |
| `alnum` | ok | ok | ok | bytes -> pairs of the 20 letters whose key positions are identical on US/DE/FR |

`alnum` uses `BCDEFGHIJKLNOPRSTUVX` (excludes A M Q W Y Z: remapped or absent
on FR; y/z swap on DE) with a length-prefix pair (payloads <= 399 bytes —
ample for Win+R one-liners), so **one US-configured scanner stream survives
all three layouts with zero target knowledge**. `tests/test_encoder.py`
demonstrates b64 failing DE/FR while alnum/hex pass, and hex's FR limit.
Decoding on the target is P3's runner problem (contract #4 `layout_safe`);
`qrducky.encoder` ships the authoritative reference decoders and US-syntax
PowerShell decode hints.

## Install & smoke

```
python3 -m venv .venv && .venv/bin/pip install -e .[dev]
.venv/bin/qr-ducky encode --payload payload.txt --mode alnum
.venv/bin/qr-ducky sheet  --payload payload.txt --out sheet.pdf --module 3 --ec M
.venv/bin/qr-ducky bench  --target vm-alpha --payload payload.txt --dry-run
```

`bench --dry-run` needs no hardware and prints the full P0 rig protocol
conversation (SESSION/PREFIX/SUFFIX/CPS/JITTER + BEGIN -> <=47-byte
fragments with ACK -> END, mirroring `lab/rig/send_payload.py`). Live
calibration additionally needs `serial_port` filled in `qrducky.toml` and
`pip install qrducky[bench]` (pyserial); the rig then emits contract-#1
JSONL events, summarized as stats.

## Hardware-gated slots

- `bench` live mode: attach the P0 rig, fill `[bench.targets.*].serial_port`,
  focus the target VM (PREFIX `GUI r` opens Run), run without `--dry-run`.
- Sheet scan validation thresholds (`HEURISTICS` in `qrducky/sheet.py`) are
  placeholders pending P1's `data/symbology.csv` calibration data.