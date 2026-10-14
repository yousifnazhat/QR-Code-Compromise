"""Bench harness tests (W2.4): P0 rig protocol framing + dry-run orchestration."""

import pytest

from qrducky.bench import BenchError, BenchNotImplemented, RigChannel, \
    bench_stats, iter_fragments, run_bench
from qrducky.config import load_config

PAYLOAD = "powershell -c IEX" + "X" * 200   # 215 chars -> 5 fragments

@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "qrducky.toml").write_text(
        "[bench]\ndefault_repeat = 5\n"
        "\n[bench.targets.vm-alpha]\nserial_port = \"\"\nbaud = 115200\n"
        "layout = \"US\"\n")
    (tmp_path / "p.txt").write_text(PAYLOAD)
    return load_config(str(tmp_path / "qrducky.toml")), str(tmp_path / "p.txt")

class TestFraming:
    def test_fragments_respect_limit(self):
        frags = list(iter_fragments("A" * 200))
        assert all(len(f) <= 47 for f in frags)
        assert "".join(frags) == "A" * 200

    def test_never_yields_end_fragment(self):
        payload = "X" + "END" * 20 + "Y"
        frags = list(iter_fragments(payload))
        assert "END" not in frags            # literal terminator never emitted
        assert "".join(frags) == payload     # and nothing is lost splitting it

    def test_empty_payload_no_fragments(self):
        assert list(iter_fragments("")) == []

class TestDryRun:
    def test_protocol_conversation_matches_p0_rig(self, cfg):
        cfg, payload = cfg
        res = run_bench(cfg, "vm-alpha", repeat=2, payload_arg=payload,
                        dry_run=True)
        conv = "\n".join(res.conversation)
        assert "> SESSION bench-vm-alpha-001" in conv
        assert "> PREFIX GUI r" in conv
        assert "> SUFFIX ENTER" in conv
        assert "> CPS 20" in conv
        assert "> JITTER 15" in conv
        assert "> BEGIN" in conv and "> END" in conv
        assert "< DRY ACK" in conv            # stop-and-wait flow control
        # fragments sent between BEGIN and END, all <=47 bytes
        body = res.conversation[res.conversation.index("> BEGIN") + 1:
                                res.conversation.index("> END")]
        sent = [l[2:] for l in body if l.startswith("> ") and l != "> END"]
        assert all(len(f) <= 47 for f in sent)
        assert "".join(sent) == PAYLOAD
        assert res.runs[1]["session"] == "bench-vm-alpha-002"
        stats = bench_stats(res)
        assert stats["dry_run"] is True and stats["total_events"] == 0

    def test_stats_shape_live_empty(self, cfg):
        cfg, payload = cfg
        stats = bench_stats(run_bench(cfg, "vm-alpha", payload_arg=payload,
                                      dry_run=True))
        assert stats["payload_bytes"] == len(PAYLOAD.encode())
        assert "duration_ms" not in stats    # no live events in dry-run

class TestLiveBoundary:
    def test_live_without_port_is_structured_boundary(self, cfg):
        cfg, payload = cfg
        with pytest.raises(BenchNotImplemented) as ei:
            run_bench(cfg, "vm-alpha", payload_arg=payload)
        assert "serial_port" in str(ei.value)
        assert ei.value.target == "vm-alpha"

    def test_undeclared_target_raises_config_error(self, cfg):
        cfg, _ = cfg
        from qrducky.config import ConfigError
        with pytest.raises(ConfigError):
            run_bench(cfg, "ghost", payload_arg="x", dry_run=True)

    def test_missing_payload_rejected(self, cfg):
        cfg, _ = cfg
        from qrducky.config import ConfigError
        with pytest.raises(ConfigError):
            run_bench(cfg, "vm-alpha", dry_run=True)   # no implicit payload

    def test_bad_cps_rejected(self, cfg, tmp_path):
        cfg, payload = cfg
        # cps out of rig range 1..200
        cfg.bench["targets"]["vm-alpha"]["cps"] = 500
        from qrducky.config import ConfigError
        with pytest.raises(ConfigError):
            run_bench(cfg, "vm-alpha", payload_arg=payload, dry_run=True)

    def test_rigchannel_timeout_in_dry_run(self):
        ch = RigChannel(None, dry_run=True)
        assert ch.read_line("OK").startswith("< DRY OK")