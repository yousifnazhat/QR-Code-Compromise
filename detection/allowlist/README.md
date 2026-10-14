# W4.4 — HID allowlisting feasibility

**AUTHORIZATION / POSTURE**: lab-only defensive research. This toolkit
parses USB HID report descriptors dumped from OWNED lab hardware to
evaluate whether HID allowlisting (as offered by endpoint-protection
products) can block QR-scanner keystroke injection. No firmware
modification, no injection functionality.

## The hypothesis

Endpoint-protection HID allowlists gate devices on their HID report
descriptor — typically "standard keyboard descriptors are allowed,
anything else (vendor pages, unusual usages) prompts or blocks".

The W4.4 hypothesis is that a 2D barcode imager in HID keyboard-wedge
mode presents a descriptor **indistinguishable from a standard
keyboard**:

- usage page 0x01 (Generic Desktop), usage 0x06 (Keyboard),
  collection (Application);
- usage page 0x07 (Keyboard/Keypad) for the modifier byte + key array;
- optionally a consumer/media page alongside — exactly like ordinary
  consumer keyboards.

If true, descriptor-level allowlisting is *blind* to keyboard-wedge
imagers (and to any injection device that faithfully emulates a
keyboard): the device is admitted as a keyboard, then the wedge
behavior — decode QR payload, emit it as keystrokes at machine speed —
never appears at the descriptor layer. Detection must then come from
**behavior** (W4.2 timing analysis, host artifacts in W4.3), not
device identity. The 1D/2D scanner matrix from P1 (`data/scanners.csv`,
contract #3, `descriptor_hash` column) gives us the empirical evidence
to test this per-model.

`descriptor_parser.py` quantifies this: given a descriptor, it
reports the declared usage pages/usages and one of four verdicts —

| verdict               | meaning                                    | allowlist outcome |
|-----------------------|--------------------------------------------|-------------------|
| `standard_keyboard`   | keyboard pages only (common consumer extras allowed) | admitted |
| `keyboard_plus_vendor`| keyboard pages + vendor-defined pages     | not admitted (review) |
| `vendor_defined`      | vendor pages, no keyboard declaration     | not admitted (review) |
| `other`               | neither (mouse/digitizer/etc.)            | not admitted (review) |

Vendor pages: 0xFF00–0xFFFF, plus the ubiquitous single-byte page
0xFF. `standard_keyboard` includes pages seen on ordinary consumer
keyboards (Generic Desktop, Keyboard, LED, Button, Consumer, Digitizer,
Generic Device Controls).

## Usage

```
python3 -m detection.allowlist.descriptor_parser "<hex bytes>"     # inline hex
python3 -m detection.allowlist.descriptor_parser dump.txt         # from file
python3 -m detection.allowlist.descriptor_parser - --json < dump  # stdin, JSON out
```

Hex input accepts whitespace/comma-separated bytes, `0x` prefixes,
and unpadded byte runs (`05010906A101`).

## Analysis protocol (physical slots — human steps)

The P1 hardware matrix (W1.1) owns the scanner bench; this package
is the analysis side. Steps requiring hands on hardware are marked
below; nothing in this directory requires them to run.

1. **[P0/P1 physical]** Dump each bench scanner's HID descriptor
   using P1's `descriptor_dump.sh` (e.g. `lsusb -v` / `usbhid-dump`,
   or Windows device path queries) while the scanner is in
   keyboard-wedge mode. The dump lands in `data/raw/` (gitignored)
   and the descriptor hash goes into `data/scanners.csv`.
2. **[P4 software]** Feed each dumped descriptor to this parser:
   `python3 -m detection.allowlist.descriptor_parser <dump>` and
   record the verdict per scanner model.
3. **[P4 analysis]** For every model whose wedge-mode descriptor
   classifies `standard_keyboard`, the hypothesis holds for that
   model: descriptor-level allowlisting would admit it. Aggregate
   results into the W4.4 feasibility table (verdicts per model →
   share of attack-capable scanners that would be admitted).
4. **[Human decision point]** If a non-trivial share of attack-capable
   scanners are `standard_keyboard` at the descriptor layer, the
   W4.4 conclusion is negative for descriptor-only allowlists and
   positive for behavioral detection (W4.2) — feeding the P5 survey's
   defensive-guidance section.

## Status

Software complete; step 1 is hardware-gated on P1's bench runs
(scanner matrix W1.1). No real descriptors have been analyzed yet —
verdicts so far are limited to the standard USB HID spec keyboard
example used in unit tests.
