"""Sheet generator tests (W2.1): PDF/PNG artifacts and scannability heuristics."""

import os

import pytest

import segno

from qrducky import build_sheet, make_pdf, make_png, make_qr, SheetError

class TestPdf:
    def test_pdf_written_and_wellformed(self, tmp_path):
        out = str(tmp_path / "sheet.pdf")
        r = build_sheet("powershell -c IEX('hello')", out,
                        module_mm=4.0, ec="M",
                        label="qr-ducky test label")
        assert os.path.isfile(out)
        raw = open(out, "rb").read()
        assert raw.startswith(b"%PDF-1.4")
        assert raw.rstrip().endswith(b"%%EOF")
        assert r.fmt == "pdf" and r.ec == "M"
        assert r.version >= 1
        assert r.module_count in (21, 25, 29)  # plausible symbol sizes
        assert r.block_mm == (r.module_count + 8) * 4.0
        assert r.warnings == []

    def test_pdf_content_stream_contains_modules_and_marks(self, tmp_path):
        out = str(tmp_path / "s.pdf")
        make_pdf(make_qr("abc"), out, module_mm=4.0, label="L")
        raw = open(out, "rb").read()
        assert raw.startswith(b"%PDF-1.4")
        assert b"/FlateDecode" in raw    # 1-bit flate image XObject (P1 writer)
        assert b"Helvetica" in raw      # core font, no embedding


    def test_ec_is_exact_no_boosting(self, tmp_path):
        # segno boosts EC silently; we pin the requested level.
        r = build_sheet("powershell -c IEX", str(tmp_path / "a.pdf"), ec="M")
        assert r.ec == "M"
        r2 = build_sheet("powershell -c IEX", str(tmp_path / "b.pdf"), ec="L")
        assert r2.ec == "L"

    def test_module_size_controls_block(self, tmp_path):
        small = build_sheet("x", str(tmp_path / "s.pdf"), module_mm=2.0)
        big = build_sheet("x", str(tmp_path / "b.pdf"), module_mm=6.0)
        assert abs(big.block_mm - small.block_mm * 3) < 0.01

class TestPng:
    def test_png_written(self, tmp_path):
        out = str(tmp_path / "sheet.png")
        r = build_sheet("powershell -c IEX", out, module_mm=4.0, ec="M")
        assert os.path.isfile(out)
        assert open(out, "rb").read(8) == b"\x89PNG\r\n\x1a\n"
        assert r.fmt == "png"
        assert any("raster" in w for w in r.warnings)

class TestHeuristics:
    def test_small_module_warns(self, tmp_path):
        r = build_sheet("x", str(tmp_path / "s.pdf"), module_mm=1.0)
        assert any("below" in w for w in r.warnings)

    def test_dense_symbol_warns(self, tmp_path):
        text = "https://attacker.example/stage?" + "A" * 1000
        r = build_sheet(text, str(tmp_path / "d.pdf"), module_mm=0.4)
        assert r.version >= 15
        assert any("dense" in w for w in r.warnings)

    def test_oversized_block_rejected(self, tmp_path):
        with pytest.raises(SheetError):
            build_sheet("A" * 900, str(tmp_path / "big.pdf"), module_mm=10.0)

    def test_payload_too_large_rejected(self, tmp_path):
        with pytest.raises(SheetError):
            build_sheet("A" * 4000, str(tmp_path / "big.pdf"), module_mm=4.0)

    def test_bad_ec_rejected(self):
        with pytest.raises(SheetError):
            make_qr("x", "X")
