# P1 tools — Hardware & Symbology Taxonomy (W1.1–W1.4)

**Authorization:** all tools in this directory are lab-only measurement
aids for the QR-Code-Compromise study. They render benign test payloads and
record human-observed decode results for OWNED, AUTHORIZED barcode readers
and owned VMs/hardware, under the lab governance policy (GX.1). They send
nothing anywhere and are not payload delivery tools. No default C2
endpoints exist anywhere in this phase.

## Tools

| Tool | Purpose |
|---|---|
| `gen_test_sheets.py` | multi-page PDF test-code sheets sweeping EC levels × module sizes at exact physical sizes (W1.3), incl. `--structured-append N` symbol groups (W1.4) |
| `scanlog.py` | interactive/piped recorder appending rows to `data/symbology.csv` (contract #3); `--validate` checks the CSV |
| `descriptor_dump.sh` | one-shot macOS/Linux USB+HID descriptor extraction feeding the scanner class matrix (W1.1) |

## gen_test_sheets.py

Print at **100% scale** ("Actual size"); every page carries a 10 mm
calibration bar — verify with a ruler before scanning.

```bash
python3 tools/gen_test_sheets.py                  # QR L/M/Q/H × 2–8mm, 28 conditions
python3 tools/gen_test_sheets.py --list-plugins
python3 tools/gen_test_sheets.py --structured-append 3 --ec M --module 4 \
    --payload "<long test payload>" --out data/test-sheets/sa-group.pdf
```

PDF generation is stdlib-only (zlib flate + 1-bit images + Helvetica);
QR encoding uses `segno` (the only approved third-party library). Decode
of rendered sheets was verified with OpenCV's QRCodeDetector: all page-1
codes and EC=H variants decode to the exact payload.

## Symbology plugin status + candidate libraries

`gen_test_sheets.py` has a plugin interface (`SymbologyPlugin.render() ->
RenderedCode`). QR is implemented; the rest are stubs that name their
candidate encoders. **Verify current PyPI/homebrew names before adopting** —
listed as candidates because none were evaluated in this phase:

| Symbology | Status | Candidate libraries |
|---|---|---|
| QR | implemented (segno) | segno |
| Data Matrix | stub | `zint` (via `pylibzint` bindings or the `zint` CLI), `treepoem` (wraps libdmtx; encode), `pylibdmtx` + `dmtxwrite` |
| PDF417 | stub | `zint` (pylibzint/CLI), `pdf417` PyPI package family, `treepoem` (limited) |
| Aztec | stub | `zint` (pylibzint/CLI), `treepoem` (limited) |
| Code 128 | stub | `python-barcode`, `zint` (pylibzint/CLI) |

A single `zint` dependency (or its `pylibzint` bindings) would cover all
four stubs in one move; `python-barcode` alone also covers Code 128 with
no C dependencies. To slot one in: subclass `SymbologyPlugin`, return a
`RenderedCode(matrix, quiet_zone, params)`, register it in `PLUGINS`.

## scanlog.py

```bash
python3 tools/scanlog.py --validate            # schema-check data/symbology.csv
python3 tools/scanlog.py record                # interactive session
python3 tools/scanlog.py record --stopwatch    # Enter-key per decode timing (tty)
printf 'QR\nM\npaper\n4.0\n15\n0\n3\n1.2,1.5,1.1\n' | python3 tools/scanlog.py record
```

Validation enforces the frozen contract #3 header, field count/types,
`0 <= successes <= attempts`, and mean-time/successes consistency.

## descriptor_dump.sh

```bash
tools/descriptor_dump.sh                # -> data/raw/usb-dump-<ts>/ (gitignored)
tools/descriptor_dump.sh /tmp/mydump    # explicit dir
```

macOS: `system_profiler SPUSBDataType` (text+XML), `ioreg` USB plane and
HID class dumps. Linux: `lsusb -v`, `lsusb -t`, `usbhid-dump`, sysfs
class-code copies. Each run writes `CLASSIFICATION-NOTES.txt` explaining
how to classify HID-wedge vs CDC-serial vs vendor-driver from the dumps
and how to derive `descriptor_hash` for `data/scanners.csv`.
