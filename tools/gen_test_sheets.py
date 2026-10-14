#!/usr/bin/env python3
"""
gen_test_sheets.py -- multi-page PDF test-code sheets for P1 (W1.3 symbology
reliability + W1.2 wedge quirk sweeps).

AUTHORIZATION: lab-only measurement tool for the QR-Code-Compromise study.
It renders benign, caller-supplied test payloads onto printable sheets for
scanning with OWNED, AUTHORIZED barcode readers. It is a measurement aid,
not a payload delivery tool.

Symbology plugins
-----------------
QR is fully implemented (segno). Data Matrix / PDF417 / Aztec / Code 128
are stubbed behind the SymbologyPlugin interface; candidate encoder
libraries are named on each stub and in tools/README.md so they slot in
later without touching the layout/PDF code.

Usage
-----
    python3 tools/gen_test_sheets.py                       # default QR sweep
    python3 tools/gen_test_sheets.py --out data/test-sheets/qr-sweep.pdf
        --payload "P1-SYM-001" --ec L,M,Q,H --module 2,3,4,5,6,7,8
        --symbology qr --quiet-zone 4 --media paper
    python3 tools/gen_test_sheets.py --list-plugins

IMPORTANT: print at 100% scale ("Actual size", no fit-to-page); every page
carries a 10 mm calibration bar to verify scale with a ruler before any
scan session. Each cell prints its symbol at the nominal physical module
size given by --module, so paper/distance/angle sweeps (contract #3,
data/symbology.csv) can reference an exact printed condition.
"""

import argparse
import os
import sys
import zlib

MM = 72.0 / 25.4  # PDF points per millimetre
A4_W_MM, A4_H_MM = 595.28 / MM, 841.89 / MM  # portrait A4
MARGIN_MM = 10.0
HEADER_MM = 14.0  # page header + calibration bar zone

# ---------------------------------------------------------------------------
# Symbology plugin interface
# ---------------------------------------------------------------------------


class RenderedCode(object):
    """A rendered symbol: boolean matrix (True = dark module) + parameters."""

    def __init__(self, matrix, quiet_zone, params):
        self.matrix = [list(row) for row in matrix]
        self.quiet_zone = int(quiet_zone)
        self.params = params  # human-readable label fragments


class SymbologyPlugin(object):
    """Interface: turn (payload, options) into a RenderedCode.

    A plugin that cannot run (missing encoder library) MUST raise
    PluginNotImplemented; candidate libraries live on the class so
    --list-plugins can report what to install.
    """

    name = "base"
    label = "BASE"
    candidates = ()

    def render(self, payload, options):  # pragma: no cover - interface
        raise NotImplementedError


class PluginNotImplemented(NotImplementedError):
    pass


class QRPlugin(SymbologyPlugin):
    name = "qr"
    label = "QR"
    candidates = ("segno",)

    def render(self, payload, options):
        import segno  # deferred: keep imports stdlib-only until used
        qr = segno.make(payload, error=options.get("ec_level", "M"),
                        micro=False)  # force QR Code, never Micro QR
        return RenderedCode(
            qr.matrix,
            options.get("quiet_zone", 4),
            {"EC": qr.error, "ver": "v%s" % qr.version},
        )

def _stub(name, label, candidates):
    class _Stub(SymbologyPlugin):
        def render(self, payload, options):
            raise PluginNotImplemented(
                "%s: no encoder installed. Candidate libraries: %s. "
                "Implement a SymbologyPlugin subclass here to slot it in."
                % (self.name, ", ".join(self.candidates))
            )

    _Stub.name = name
    _Stub.label = label
    _Stub.candidates = tuple(candidates)
    return _Stub


# PLUGINS: QR is live. The stubs below are ready-to-fill slots; candidate
# encoder libraries are listed in tools/README.md (W1.3 non-QR sweeps).
PLUGINS = {
    "qr": QRPlugin,
    "datamatrix": _stub(
        "datamatrix", "DM",
        ("zint (pylibzint)", "treepoem (libdmtx)", "pylibdmtx + dmtxwrite"),
    ),
    "pdf417": _stub(
        "pdf417", "PDF417",
        ("zint (pylibzint)", "pdf417 (PyPI)", "treepoem (limited)"),
    ),
    "aztec": _stub(
        "aztec", "Aztec",
        ("zint (pylibzint)", "treepoem (limited)"),
    ),
    "code128": _stub(
        "code128", "Code128",
        ("python-barcode", "zint (pylibzint)"),
    ),
}


# ---------------------------------------------------------------------------
# Minimal stdlib PDF writer: pages, Helvetica text, 1-bit flate images
# ---------------------------------------------------------------------------

def _pdf_escape(text):
    out = []
    for ch in text:
        if ch in "()\\":
            out.append("\\" + ch)
        elif 32 <= ord(ch) < 127:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


class PDFSheet(object):
    """Accumulates drawn pages; build() emits a single-file PDF.

    Only PDF-1.4 basics are used: Type1 Helvetica (no embedding needed),
    1-bit DeviceGray XObject images with FlateDecode (stdlib zlib), and
    content streams that are also flate-compressed.
    """

    def __init__(self, title):
        self.title = title
        self.image_bodies = []  # list[bytes] full PDF object bodies
        self.image_names = []   # XObject names, same order as image_bodies
        self.pages_ops = [[]]   # list[list[str]] content-stream operators

    # -- images ------------------------------------------------------------
    def add_image(self, matrix, quiet_zone):
        """Pack a boolean matrix + quiet zone into a 1-bit flate image.

        Sample value 0 = black (dark module), 1 = white; rows are padded
        to byte boundaries with white. Returns (name, cols, rows) where
        cols/rows include the quiet zone (module counts).
        """
        rows = len(matrix) + 2 * quiet_zone
        cols = len(matrix[0]) + 2 * quiet_zone
        packed = bytearray()
        for r in range(rows):
            mr = r - quiet_zone
            for i in range(0, cols, 8):
                byte = 0
                for b in range(8):
                    c = i + b
                    if c >= cols:
                        dark = False  # pad bits are white
                    else:
                        mc = c - quiet_zone
                        in_sym = 0 <= mr < len(matrix) and 0 <= mc < len(matrix[0])
                        dark = bool(in_sym and matrix[mr][mc])
                    byte = (byte << 1) | (0 if dark else 1)
                packed.append(byte)
        comp = zlib.compress(bytes(packed), 9)
        name = "Im%d" % (len(self.image_bodies) + 1)
        self.image_names.append(name)
        body = (
            "<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            "/ColorSpace /DeviceGray /BitsPerComponent 1 "
            "/Filter /FlateDecode /Length %d >>\nstream\n" % (cols, rows, len(comp))
        ).encode("ascii") + comp + b"\nendstream"
        self.image_bodies.append(body)
        return name, cols, rows

    # -- drawing -----------------------------------------------------------
    def _ops(self):
        return self.pages_ops[-1]

    def image(self, xobj_name, x_mm, y_mm, w_mm, h_mm):
        """Draw image scaled to w_mm x h_mm with lower-left at (x_mm, y_mm).

        Coordinates are mm from the page's lower-left corner.
        """
        self._ops().append(
            "q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q"
            % (w_mm * MM, h_mm * MM, x_mm * MM, y_mm * MM, xobj_name)
        )

    def text(self, x_mm, y_mm, size_pt, s):
        self._ops().append(
            "BT /F1 %s Tf %.2f %.2f Td (%s) Tj ET"
            % (size_pt, x_mm * MM, y_mm * MM, _pdf_escape(s))
        )

    def line(self, x1_mm, y1_mm, x2_mm, y2_mm, width_pt=0.4):
        self._ops().append(
            "%.2f w %.2f %.2f m %.2f %.2f l S"
            % (width_pt, x1_mm * MM, y1_mm * MM, x2_mm * MM, y2_mm * MM)
        )

    def frame(self, x_mm, y_mm, w_mm, h_mm, width_pt=0.3):
        self._ops().append(
            "%.2f w %.2f %.2f %.2f %.2f re S"
            % (width_pt, x_mm * MM, y_mm * MM, w_mm * MM, h_mm * MM)
        )

    def new_page(self):
        if self.pages_ops[-1]:
            self.pages_ops.append([])

    # -- assembly ---------------------------------------------------------
    def build(self, path):
        """Assemble and write the PDF. Returns (page_count, byte_count)."""
        # Drop trailing, still-empty page slot.
        if self.pages_ops and not self.pages_ops[-1]:
            self.pages_ops.pop()
        n_img = len(self.image_bodies)
        n_pages = len(self.pages_ops)
        # Object numbering: 1 catalog, 2 pages tree, 3..(2+n_img) images,
        # 3+n_img font, 4+n_img shared resources, then per page: content,
        # page object.
        font_num = 3 + n_img
        res_num = 4 + n_img
        content_nums, page_nums = [], []
        nxt = 5 + n_img
        for _ in range(n_pages):
            content_nums.append(nxt)
            page_nums.append(nxt + 1)
            nxt += 2

        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join("%d 0 R" % n for n in page_nums)
        objects.append(
            ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pages)).encode("ascii")
        )
        objects.extend(self.image_bodies)
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        xobj_dict = " ".join(
            "/%s %d 0 R" % (name, 3 + i) for i, name in enumerate(self.image_names)
        )
        objects.append(
            ("<< /Font << /F1 %d 0 R >> /XObject << %s >> >>" % (font_num, xobj_dict)).encode("ascii")
        )
        for ops, cnum, pnum in zip(self.pages_ops, content_nums, page_nums):
            comp = zlib.compress("\n".join(ops).encode("latin-1"), 9)
            objects.append(
                ("<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(comp)).encode("ascii")
                + comp
                + b"\nendstream"
            )
            objects.append(
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
                    "/Resources %d 0 R /Contents %d 0 R >>"
                    % (A4_W_MM * MM, A4_H_MM * MM, res_num, cnum)
                ).encode("ascii")
            )

        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for i, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += ("%d 0 obj\n" % i).encode("ascii") + body + b"\nendobj\n"
        xref_at = len(out)
        out += ("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii")
        out += b"0000000000 65535 f \n"
        for off in offsets:
            out += ("%010d 00000 n \n" % off).encode("ascii")
        out += (
            "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref_at)
        ).encode("ascii")
        with open(path, "wb") as fh:
            fh.write(bytes(out))
        return n_pages, len(out)


# ---------------------------------------------------------------------------
# Test cells + shelf layout at nominal physical sizes
# ---------------------------------------------------------------------------


class Cell(object):
    """One printable condition: a symbol at an exact physical size + labels."""

    LABEL_H_MM = 9.0   # two label lines above the symbol
    PAD_MM = 3.0       # breathing room at the bottom of the cell

    def __init__(self, cond_id, plugin_label, code, mod_mm, ec, payload, media):
        self.cond_id = cond_id
        self.plugin_label = plugin_label
        self.code = code
        self.mod_mm = mod_mm
        self.ec = ec
        self.payload = payload
        self.media = media
        self.xobj = None
        self.img_cols = self.img_rows = 0
        self.img_w_mm = self.img_h_mm = 0.0
        self.w_mm = self.h_mm = 0.0

    def prepare(self, sheet):
        self.xobj, self.img_cols, self.img_rows = sheet.add_image(
            self.code.matrix, self.code.quiet_zone
        )
        self.img_w_mm = self.img_cols * self.mod_mm
        self.img_h_mm = self.img_rows * self.mod_mm
        self.w_mm = self.img_w_mm
        self.h_mm = self.LABEL_H_MM + self.img_h_mm + self.PAD_MM

    def label_lines(self):
        p = dict(self.code.params)
        p.setdefault("EC", self.ec)
        sa = p.get("SA")
        return (
            "%s  %s  EC=%s  module=%gmm  media=%s%s" % (
                self.cond_id, self.plugin_label, p.get("EC", "NA"),
                self.mod_mm, self.media,
                "  SA=%s" % sa if sa else "",
            ),
            "payload: %s  |  %s data mods/side, QZ=%d" % (
                self.payload[:40],
                self.img_cols - 2 * self.code.quiet_zone,
                self.code.quiet_zone,
            ),
        )

    def draw(self, sheet, x_mm, y_top_mm):
        """Draw the cell with its top edge y_top_mm below the page header."""
        top_mm = A4_H_MM - MARGIN_MM - HEADER_MM - y_top_mm  # from page bottom
        label1, label2 = self.label_lines()
        sheet.text(x_mm, top_mm - 3.0, 6.5, label1)
        sheet.text(x_mm, top_mm - 6.2, 5.5, label2)
        img_y = top_mm - self.LABEL_H_MM - self.img_h_mm
        sheet.image(self.xobj, x_mm, img_y, self.img_w_mm, self.img_h_mm)
        sheet.frame(x_mm - 1.5, img_y - 1.5, self.img_w_mm + 3.0, self.h_mm + 1.0)


def draw_page_header(sheet, page_no, total_pages, payload, quiet):
    top = A4_H_MM - MARGIN_MM
    sheet.text(MARGIN_MM, top - 4.0, 8.5,
               "QR-Code-Compromise P1 test sheet -- print at 100%% scale "
               "(page %d/%d)" % (page_no, total_pages))
    sheet.text(MARGIN_MM, top - 8.0, 6.0,
               "payload: %s   quiet zone: %d modules   "
               "verify the bar below is exactly 10.0 mm before scanning"
               % (payload, quiet))
    bar_y = top - 12.5
    x0 = MARGIN_MM
    sheet.line(x0, bar_y, x0 + 10.0, bar_y, width_pt=1.2)
    for dx in (0.0, 5.0, 10.0):
        sheet.line(x0 + dx, bar_y - 0.8, x0 + dx, bar_y + 0.8, width_pt=0.8)
    sheet.text(x0 + 12.0, bar_y - 1.0, 5.5, "10 mm calibration bar")


def layout_cells(cells):
    """Greedy shelf packing: pages of rows; returns list of pages, each a
    list of rows, each a list of (cell, x_mm). y offsets are per row."""
    usable_w = A4_W_MM - 2 * MARGIN_MM
    usable_h = A4_H_MM - 2 * MARGIN_MM - HEADER_MM
    gap = 6.0
    pages, cur_page, cur_row = [], [], []
    x, y, shelf_h = MARGIN_MM, 0.0, 0.0

    def end_row():
        nonlocal cur_row, x, y, shelf_h
        if cur_row:
            cur_page.append(cur_row)
            cur_row = []
        y += shelf_h + gap
        x, shelf_h = MARGIN_MM, 0.0

    def end_page():
        nonlocal cur_page, x, y, shelf_h
        end_row()
        if cur_page:
            pages.append(cur_page)
            cur_page = []
        x, y, shelf_h = MARGIN_MM, 0.0, 0.0

    for cell in cells:
        if shelf_h > 0.0 and x + gap + cell.w_mm > MARGIN_MM + usable_w:
            end_row()
        if y + cell.h_mm > usable_h:
            end_page()
        cur_row.append((cell, x))
        shelf_h = max(shelf_h, cell.h_mm)
        x += cell.w_mm + gap
    end_page()
    return pages


def build_cells(args, plugin):
    cells = []
    n = 0
    sa_n = args.structured_append
    if sa_n < 1:
        raise ValueError("--structured-append must be >= 1")
    for ec in args.ec:
        seq = None
        if sa_n > 1:
            import segno
            seq = segno.make_sequence(args.payload, error=ec,
                                      symbol_count=sa_n,
                                      boost_error=False)
        for mod in args.module:
            if seq is not None:
                # W1.4: one cell per Structured Append symbol, per module size
                for i, q in enumerate(seq, start=1):
                    n += 1
                    code = RenderedCode(
                        q.matrix, args.quiet_zone,
                        {"EC": q.error, "SA": "%d/%d" % (i, sa_n)},
                    )
                    cells.append(Cell("C%02d" % n, plugin.label, code,
                                      mod, ec, args.payload, args.media))
            else:
                n += 1
                code = plugin.render(args.payload, {
                    "ec_level": ec, "quiet_zone": args.quiet_zone,
                })
                cells.append(Cell(
                    "C%02d" % n, plugin.label, code, mod, ec,
                    args.payload, args.media,
                ))
    return cells


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate multi-page PDF test-code sheets (P1 W1.3).")
    ap.add_argument("--out", default="data/test-sheets/qr-sweep.pdf")
    ap.add_argument("--payload", default="P1-SYM-001",
                    help="test payload text encoded in every symbol "
                         "(printable ASCII, one line)")
    ap.add_argument("--ec", default="L,M,Q,H", help="comma list of QR EC levels")
    ap.add_argument("--module", default="2,3,4,5,6,7,8",
                    help="comma list of module sizes in mm")
    ap.add_argument("--symbology", default="qr", choices=sorted(PLUGINS))
    ap.add_argument("--media", default="paper",
                    help="label describing the print medium (paper, screen, label, ...)")
    ap.add_argument("--quiet-zone", type=int, default=4,
                    help="quiet zone in modules (ISO minimum 4)")
    ap.add_argument("--list-plugins", action="store_true",
                    help="list symbology plugins and their status")
    ap.add_argument("--structured-append", type=int, default=1, metavar="N",
                    help="split payload across N QR Structured Append "
                         "symbols (2..16; W1.4). Requires --symbology qr "
                         "and a single --ec level")
    args = ap.parse_args(argv)

    if args.list_plugins:
        for name, cls in sorted(PLUGINS.items()):
            state = "implemented" if name == "qr" else "STUB"
            print("%-10s %-8s %-11s candidates: %s"
                  % (name, cls.label, state, ", ".join(cls.candidates)))
        return 0

    if not all(32 <= ord(c) < 127 for c in args.payload):
        ap.error("payload must be printable ASCII")
    if args.quiet_zone < 4:
        ap.error("quiet zone below ISO minimum of 4 modules")
    try:
        args.ec = [e.strip().upper() for e in args.ec.split(",") if e.strip()]
        args.module = [float(m) for m in args.module.split(",") if m.strip()]
    except ValueError:
        ap.error("bad --ec or --module list")
    if not args.ec or not args.module:
        ap.error("empty --ec or --module list")
    for m in args.module:
        if not (0.5 <= m <= 20.0):
            ap.error("module size %g mm outside printable range 0.5-20" % m)
    if args.structured_append > 1:
        if args.symbology != "qr":
            ap.error("--structured-append requires --symbology qr")
        if not (2 <= args.structured_append <= 16):
            ap.error("--structured-append N must be 2..16 (ISO limit)")
        if len(args.ec) != 1:
            ap.error("--structured-append requires exactly one --ec level")

    plugin = PLUGINS[args.symbology]()
    cells = build_cells(args, plugin)  # raises PluginNotImplemented for stubs

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    sheet = PDFSheet("P1 symbology sweep (%s)" % args.symbology)
    for c in cells:
        c.prepare(sheet)
    pages = layout_cells(cells)
    for pno, page in enumerate(pages, start=1):
        draw_page_header(sheet, pno, len(pages), args.payload, args.quiet_zone)
        y = 0.0
        for row in page:
            shelf_h = max(cell.h_mm for cell, _ in row)
            for cell, x in row:
                cell.draw(sheet, x, y)
            y += shelf_h + 6.0
        sheet.new_page()

    n_pages, n_bytes = sheet.build(args.out)
    print("wrote %s" % args.out)
    print("conditions: %d  (%d EC levels x %d module sizes)"
          % (len(cells), len(args.ec), len(args.module)))
    print("pages: %d   size: %.1f KiB" % (n_pages, n_bytes / 1024.0))
    for c in cells:
        print("  %s  EC=%-2s module=%gmm -> %.0fx%.0fmm symbol" % (
            c.cond_id, c.ec, c.mod_mm, c.img_w_mm, c.img_h_mm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
