"""Minimal stdlib-only PDF writer — pages, Helvetica text, 1-bit flate images.

EXTRACTED from tools/gen_test_sheets.py (P1 hardware-matrix, merge bbb1775 on
master) so qr-ducky's sheet path (W2.1) reuses the same PROVEN PDF internals
instead of a second, parallel PDF implementation. P1's writer is verified
generating 20-page sweep sheets and fresh single-condition sheets.

Only PDF-1.4 basics are used: Type1 Helvetica (no embedding), 1-bit
DeviceGray XObject images with FlateDecode (stdlib zlib), and flate-compressed
content streams. Keep this module byte-compatible with the P1 original unless
a change is coordinated (see qrducky/contract-amendments.md for the note).
"""

import zlib

MM = 72.0 / 25.4  # PDF points per millimetre
A4_W_MM, A4_H_MM = 595.28 / MM, 841.89 / MM  # portrait A4
MARGIN_MM = 10.0

def _pdf_escape(text):
    out = []
    for ch in text:
        if ch in "()\\":
            out.append("\\" + ch)
        elif ord(ch) < 32:
            out.append("\\%03o" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)

class PDFSheet(object):
    """Accumulates drawn pages; build() emits a single-file PDF."""

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
                        in_sym = (0 <= mr < len(matrix)
                                  and 0 <= mc < len(matrix[0]))
                        dark = bool(in_sym and matrix[mr][mc])
                    byte = (byte << 1) | (0 if dark else 1)
                packed.append(byte)
        comp = zlib.compress(bytes(packed), 9)
        name = "Im%d" % (len(self.image_bodies) + 1)
        self.image_names.append(name)
        body = (
            "<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            "/ColorSpace /DeviceGray /BitsPerComponent 1 "
            "/Filter /FlateDecode /Length %d >>\nstream\n"
            % (cols, rows, len(comp))
        ).encode("ascii") + comp + b"\nendstream"
        self.image_bodies.append(body)
        return name, cols, rows

    # -- drawing -----------------------------------------------------------
    def _ops(self):
        return self.pages_ops[-1]

    def image(self, xobj_name, x_mm, y_mm, w_mm, h_mm):
        """Draw image scaled to w_mm x h_mm with lower-left at (x_mm, y_mm)."""
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

    def new_page(self):
        if self.pages_ops[-1]:
            self.pages_ops.append([])

    # -- assembly ---------------------------------------------------------
    def build(self, path):
        """Assemble and write the PDF. Returns (page_count, byte_count)."""
        if self.pages_ops and not self.pages_ops[-1]:
            self.pages_ops.pop()
        n_img = len(self.image_bodies)
        n_pages = len(self.pages_ops)
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
            ("<< /Type /Pages /Kids [%s] /Count %d >>"
             % (kids, n_pages)).encode("ascii")
        )
        objects.extend(self.image_bodies)
        objects.append(b"<< /Type /Font /Subtype /Type1 "
                       b"/BaseFont /Helvetica >>")
        xobj_dict = " ".join(
            "/%s %d 0 R" % (name, 3 + i)
            for i, name in enumerate(self.image_names)
        )
        objects.append(
            ("<< /Font << /F1 %d 0 R >> /XObject << %s >> >>"
             % (font_num, xobj_dict)).encode("ascii")
        )
        for ops, cnum, pnum in zip(self.pages_ops, content_nums, page_nums):
            comp = zlib.compress("\n".join(ops).encode("latin-1"), 9)
            objects.append(
                ("<< /Length %d /Filter /FlateDecode >>\nstream\n"
                 % len(comp)).encode("ascii") + comp + b"\nendstream"
            )
            objects.append(
                ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
                 "/Resources %d 0 R /Contents %d 0 R >>"
                 % (A4_W_MM * MM, A4_H_MM * MM, res_num, cnum)).encode("ascii")
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