"""Unit tests for contract-#1 JSONL validation and loading."""

import json

import pytest

from detection.dataset.load import (
    JsonlValidationError,
    iter_events,
    load_sessions,
    validate_event,
)
from detection.dataset.synth import generate_dataset

VALID = {
    "ts_ms": 123456789,
    "event": "keydown",
    "keycode": 65,
    "source": "human",
    "device": "kbd-01",
    "session": "sess-017",
}


def test_valid_event_passes():
    assert validate_event(VALID) == []


def test_valid_event_all_sources():
    for source in ("human", "scanner", "rig"):
        event = dict(VALID, source=source)
        assert validate_event(event) == []


@pytest.mark.parametrize("field", list(VALID))
def test_missing_required_field_reported(field):
    event = dict(VALID)
    del event[field]
    errors = validate_event(event)
    assert any(field in e for e in errors)


def test_bad_source_rejected():
    errors = validate_event(dict(VALID, source="dolphin"))
    assert any("source" in e for e in errors)


def test_bad_event_type_rejected():
    errors = validate_event(dict(VALID, event="keypress"))
    assert any("event" in e for e in errors)


def test_keycode_range_enforced():
    assert validate_event(dict(VALID, keycode=256))
    assert validate_event(dict(VALID, keycode=-1))
    assert validate_event(dict(VALID, keycode=255)) == []


def test_ts_ms_type_enforced():
    # bool is an int subclass but not a valid monotonic timestamp
    assert validate_event(dict(VALID, ts_ms=True))
    assert validate_event(dict(VALID, ts_ms="123"))
    assert validate_event(dict(VALID, ts_ms=-5))


def test_device_and_session_must_be_nonempty_strings():
    assert validate_event(dict(VALID, device=""))
    assert validate_event(dict(VALID, session=""))


def test_non_object_rejected():
    assert validate_event([1, 2, 3])
    assert validate_event("keydown")


def test_jsonl_roundtrip_groups_and_sorts_sessions(tmp_path):
    # deliberately out-of-order timestamps across two sessions
    lines = [
        dict(VALID, ts_ms=30, session="s1"),
        dict(VALID, ts_ms=10, session="s2"),
        dict(VALID, ts_ms=20, session="s1"),
        dict(VALID, ts_ms=5, event="keyup", keycode=65, session="s2"),
    ]
    path = tmp_path / "capture.jsonl"
    path.write_text(
        "\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")

    sessions = load_sessions(str(path))
    assert sorted(sessions) == ["s1", "s2"]
    assert [e["ts_ms"] for e in sessions["s1"]] == [20, 30]
    assert [e["ts_ms"] for e in sessions["s2"]] == [5, 10]


def test_invalid_json_reports_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(
        json.dumps(VALID) + "\nnot json at all\n", encoding="utf-8")
    with pytest.raises(JsonlValidationError) as exc:
        list(iter_events(str(path)))
    assert exc.value.line_no == 2
    assert "invalid JSON" in str(exc.value)


def test_validation_error_reports_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(
        json.dumps(dict(VALID, source="alien")) + "\n", encoding="utf-8")
    with pytest.raises(JsonlValidationError) as exc:
        list(iter_events(str(path)))
    assert exc.value.line_no == 1
    assert "source" in str(exc.value)


def test_blank_lines_skipped(tmp_path):
    path = tmp_path / "blank.jsonl"
    path.write_text("\n\n" + json.dumps(VALID) + "\n\n", encoding="utf-8")
    events = list(iter_events(str(path)))
    assert len(events) == 1


def test_synthetic_generator_output_is_contract_valid(tmp_path):
    # The generator must emit only fully-valid contract-#1 events.
    events = generate_dataset(seed=1, human_sessions=3,
                             scanner_sessions=3, rig_sessions=2,
                             min_keys=10, max_keys=15)
    for event in events:
        assert validate_event(event) == []
    path = tmp_path / "synth.jsonl"
    path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    sessions = load_sessions(str(path))
    assert len(sessions) == 8  # 3 human + 3 scanner + 2 rig


def test_loader_rejects_undocumented_source_from_file(tmp_path):
    path = tmp_path / "trap.jsonl"
    path.write_text(
        json.dumps(dict(VALID, source="scanner ")) + "\n", encoding="utf-8")
    with pytest.raises(JsonlValidationError):
        list(iter_events(str(path)))
