"""QR sheet generator (W2.1): segno -> PDF (P1's stdlib writer) or PNG.

The PDF path reuses `qrducky.pdfsheet.PDFSheet` — the PROVEN stdlib-only
writer extracted from P1's tools/gen_test_sheets.py (1-bit flate images,
Helvetica core font, A4 portrait) — so both P1's sweep sheets and qr-ducky's
payload sheets share one PDF implementation. The QR matrix is packed with a
4-module quiet zone, drawn at the exact requested physical module size (mm),
framed by alignment crop marks and a parameter label.

`--png` raster path stays on segno's save(). Scannability heuristics warn
(structured, to stderr via the CLI) when parameters leave the empirically
safe print region; thresholds are placeholders pending P1's symbology
calibration data (data/symbology.csv, contract #3).
"""

import re
from dataclasses import dataclass, field
from typing import List

import segno

from .pdfsheet import A4_H_MM, A4_W_MM, MARGIN_MM, PDFSheet

QUIET_MODULES = 4  # QR spec quiet zone

#: Placeholder thresholds pending P1 symbology calibration (W1.3).
HEURISTICS = {
    "min_module_mm": 2.0,   # below this, consumer scanners get unreliable
    "warn_version": 15,      # very dense symbols scan poorly from paper
}

class SheetError(ValueError):
    pass

@dataclass
class SheetResult:
    path: str
    fmt: str                     # "pdf" | "png"
    version: int
    ec: str
    module_count: int
    module_mm: float
    block_mm: float               # physical size incl. quiet zone
    chars: int
    warnings: List[str] = field(default_factory=list)

def _version_int(qr: segno.QRCode) -> int:
    """segno 2.x reports version as e.g. 'M3' or '6'; coerce to int."""
    m = re.search(r"\d+", str(qr.version))
    return int(m.group(0)) if m else 0

def make_qr(text: str, ec: str = "M") -> segno.QRCode:
    ec = ec.upper()
    if ec not in ("L", "M", "Q", "H"):
        raise SheetError(f"unknown EC level {ec!r} (choose L, M, Q or H)")
    try:
        return segno.make(text, error=ec, boost_error=False)
    except segno.DataOverflowError as e:
        raise SheetError(
            f"payload does not fit a QR code at EC {ec} ({e}); "
            f"use a higher-throughput mode (b64 > hex == alnum) or lower EC"
        ) from e

def _heuristic_warnings(result: SheetResult) -> List[str]:
    w = []
    if result.module_mm < HEURISTICS["min_module_mm"]:
        w.append(
            f"module {result.module_mm}mm is below the "
            f"{HEURISTICS['min_module_mm']}mm reliability threshold "
            f"(placeholder value; P1 symbology data will recalibrate)")
    if result.version >= HEURISTICS["warn_version"]:
        w.append(
            f"QR version {result.version} is dense "
            f"(>={HEURISTICS['warn_version']}); print quality and scan "
            f"distance tolerances shrink — verify on the bench (P0)")
    return w

def make_pdf(qr: segno.QRCode, out: str, module_mm: float,
             label: str = "") -> SheetResult:
    """Render `qr` as a one-page A4 PDF via the P1 writer, with crop marks."""
    matrix = [list(map(bool, row)) for row in qr.matrix]
    n = len(matrix)
    total_modules = n + 2 * QUIET_MODULES
    block_mm = total_modules * module_mm
    usable_mm = A4_W_MM - 2 * MARGIN_MM
    if block_mm > usable_mm:
        raise SheetError(
            f"QR block {block_mm:.1f}mm exceeds usable page width "
            f"({usable_mm:.0f}mm): lower --module or use a compact mode")

    pdf = PDFSheet("qr-ducky payload sheet")
    name, cols, rows = pdf.add_image(matrix, QUIET_MODULES)
    assert cols == rows == total_modules

    x0 = (A4_W_MM - block_mm) / 2.0
    y0 = (A4_H_MM - block_mm) / 2.0 - 12.0  # leave room for label below
    pdf.image(name, x0, y0, block_mm, block_mm)

    # Alignment crop marks: L shapes just outside the four block corners.
    off, arm = 6.0, 12.0
    for cx, cy, ox, oy in (
        (x0, y0, -1, -1), (x0 + block_mm, y0, +1, -1),
        (x0, y0 + block_mm, -1, +1), (x0 + block_mm, y0 + block_mm, +1, +1),
    ):
        hx, hy = cx + ox * off, cy + oy * off
        pdf.line(hx, hy, hx - ox * arm, hy)   # arm running back toward block
        pdf.line(hx, hy, hx, hy - oy * arm)

    if label:
        pdf.text(x0, y0 - 7.0, 8.0, label)

    pdf.build(out)
    return SheetResult(
        path=out, fmt="pdf", version=_version_int(qr), ec=qr.error,
        module_count=n, module_mm=module_mm, block_mm=block_mm, chars=0)

def make_png(qr: segno.QRCode, out: str, module_mm: float,
             dpi: int = 300) -> SheetResult:
    """Raster path (segno); scale chosen so 1 module == module_mm at `dpi`."""
    scale = max(1, round(module_mm / 25.4 * dpi))
    qr.save(out, kind="png", scale=scale, border=QUIET_MODULES)
    return SheetResult(
        path=out, fmt="png", version=_version_int(qr), ec=qr.error,
        module_count=len(qr.matrix), module_mm=module_mm,
        block_mm=(len(qr.matrix) + 2 * QUIET_MODULES) * module_mm, chars=0)

def build_sheet(qr_text: str, out: str, module_mm: float = 4.0, ec: str = "M",
                label: str = "") -> SheetResult:
    """End-to-end sheet: QR text -> PDF or PNG (by extension) + heuristics."""
    qr = make_qr(qr_text, ec)
    if out.lower().endswith(".png"):
        result = make_png(qr, out, module_mm)
        result.warnings.append(
            f"PNG raster at 300dpi (scale="
            f"{max(1, round(module_mm / 25.4 * 300))} px/module); prefer the "
            f"vector PDF for print fidelity")
    else:
        result = make_pdf(qr, out, module_mm, label=label)
    result.chars = len(qr_text)
    result.warnings.extend(_heuristic_warnings(result))
    return result