# W1.4 — QR Structured Append (SA) Scanner Behavior Test Protocol

**Authorization:** lab-only. Physical scans are performed by the human
operator on OWNED, AUTHORIZED barcode readers, on owned hardware, inside the
lab. No field use.

## Purpose

Determine how the scanner classes recorded in `data/scanners.csv` (W1.1)
behave when presented with QR **Structured Append** symbol groups
(ISO/IEC 18004 section on SA): a payload split across 2–16 symbols, each
carrying SA position/partition headers. Three behaviors matter for the
wedge attack model:

1. **reassemble** — scanner buffers symbols and emits the concatenation
   (only after the last symbol or immediately per symbol);
2. **partial/none** — scanner emits each symbol's fragment separately, or
   refuses/fails to decode SA symbols at all;
3. **ordering** — whether emission order follows SA headers (symbol
   position 1..N) or physical scan order.

Behavior 1 changes keystroke-injection economics (multi-code payloads
without per-symbol length limits); behaviors 2–3 bound them.

## Tool support status (verified)

- **segno 1.6.6 supports Structured Append.** Verified:
  `segno.make_sequence(content, error=..., symbol_count=N, boost_error=False)`
  returns a `QRCodeSequence` of N QR codes (not Micro QR) with SA
  position/partition headers; max N = 16 per the QR spec. No tool gap.
- `tools/gen_test_sheets.py --structured-append N` renders the full group
  through the same PDF pipeline at exact physical module sizes; each cell
  is labeled `SA=i/N`.
- Cross-check performed: a standalone render of symbol 1/3 decodes with an
  **empty payload** in a non-SA-aware decoder (OpenCV), i.e. the SA header
  is present and the decoder refuses partial content — expected, and a
  preview of what non-SA wedge scanners will do.

## Building the test symbols

Reproduce the committed sheet, or generate variants:

```bash
# committed 3-symbol group, EC M, 4 mm modules, page-per-symbol PDF:
python3 tools/gen_test_sheets.py --structured-append 3 --ec M --module 4 \
    --payload "A-sa-test-001 A-sa-test-001 A-sa-test-001 A-sa-test-001 A-sa-test-001 A-sa-test-001" \
    --out data/test-sheets/sa-group.pdf

# 2-symbol group on screen media, 2 mm modules (for screen-display scans):
python3 tools/gen_test_sheets.py --structured-append 2 --ec H --module 2 \
    --payload "SA-SCREEN-TEST 0123456789 ABCDEFGHIJ KLMNOPQRST" \
    --media screen --out data/test-sheets/sa-screen.pdf
```

Notes:
- Payload must be long enough to actually split (else segno may return fewer
  symbols); keep the EC pinned with the single `--ec` level — the tool
  passes `boost_error=False` so sheets match the recorded condition.
- `--structured-append` requires `--symbology qr` and exactly one `--ec`.
- Print at **100% scale**; verify the 10 mm calibration bar with a ruler.

## What to scan (per scanner under test)

Record each session in `data/symbology.csv` via
`python3 tools/scanlog.py` with `symbology = qr-sa` and the condition
fields. Perform at least:

| Step | Action | What it probes |
|---|---|---|
| S1 | Scan symbols 1→3 in order, one full pass each | basic reassembly; where output appears (after 1st, per-symbol, or only after 3rd) |
| S2 | Scan symbols 3→1 (reverse order) | does output order follow SA headers or scan order? |
| S3 | Scan 2, then 1, then 3 | out-of-order header handling |
| S4 | Scan 1, scan unrelated single QR, scan 2, 3 | does the buffer reset on unrelated symbols? |
| S5 | Scan 1, wait >10 s, scan 2, 3 | buffering timeout (record approx. timeout if it resets) |
| S6 | Scan only symbol 2 (partial group) | does the scanner emit the fragment, refuse, or hang? |

Repeat S1 `attempts` times (default 3) to get `successes` and
`mean_decode_s` for the CSV row. A scan session = a scanner pointed at the
sheet, with the scanner's output captured in a text editor or the lab's
keystroke logger (P0 rig), so exact emitted bytes, timing and ordering are
observable.

## Verdicts to record

For each scanner, record a `verdict` line in `data/raw/sa-notes/<model>.txt`
(raw logs are gitignored) and summarize it in `data/scanners.csv` `notes`:

| Verdict value | Meaning |
|---|---|
| `reassemble-in-order` | full payload emitted once, correctly ordered by SA headers |
| `reassemble-scan-order` | full payload emitted, ordering follows scan order (headers only used as glue) |
| `per-symbol-fragments` | each scan emits only that symbol's fragment |
| `refuse-sa` | SA symbols do not decode at all (no output / error beep) |
| `partial-hang` | first symbol(s) decode; group never completes (buffer reset mid-group) |

Also record for `reassemble-*` verdicts **when** the payload is emitted:
after every symbol (streaming) vs only after the final symbol (buffered).

## Capture slots for the human (physically gated)

- [ ] Print `data/test-sheets/sa-group.pdf` at 100% scale, verify 10 mm bar
- [ ] For each scanner in `data/scanners.csv`: run S1–S6 above
- [ ] Record `data/symbology.csv` rows (`symbology=qr-sa`) + verdict notes
- [ ] If a scanner reassembles: note emitted delimiter/terminator between
      fragments (feeds P2 layout-safe encoder and P3 payload chunking)
