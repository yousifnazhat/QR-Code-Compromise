"""Contract-#1 keystroke JSONL loader and strict validator.

Input format (COORDINATION.md, contract #1) — one event per line, UTF-8::

    {"ts_ms": 123456789, "event": "keydown", "keycode": 65,
     "source": "human|scanner|rig", "device": "model-or-rig-id",
     "session": "sess-017"}

Strictness notes (P4's reading of the frozen contract):
- All six fields are mandatory; none may be null.
- ``source`` MUST be exactly ``human``, ``scanner`` or ``rig`` — these
  labels build the P4 dataset, so anything else is a contract break,
  not a warning.
- ``event`` MUST be ``keydown`` or ``keyup``. The frozen contract
  example shows ``keydown``; ``keyup`` is accepted because the P0
  capture hook (lab/capture/) is expected to emit full HID transitions.
  Any other event type is rejected — if P0 needs more types, the
  contract must be amended, not the validator loosened.
- ``ts_ms`` is a monotonic millisecond integer; ``keycode`` an HID
  usage ID 0-255.
"""

from typing import Any, Dict, Iterator, List

__all__ = [
    "JsonlValidationError",
    "REQUIRED_FIELDS",
    "VALID_SOURCES",
    "KNOWN_EVENTS",
    "validate_event",
    "iter_events",
    "load_events",
    "load_sessions",
]

REQUIRED_FIELDS = ("ts_ms", "event", "keycode", "source", "device", "session")
VALID_SOURCES = ("human", "scanner", "rig")
KNOWN_EVENTS = ("keydown", "keyup")


class JsonlValidationError(ValueError):
    """Raised when a JSONL line violates contract #1."""

    def __init__(self, path: str, line_no: int, message: str):
        self.path = path
        self.line_no = line_no
        self.message = message
        super().__init__("%s:%d: %s" % (path, line_no, message))


def _is_int(value: Any) -> bool:
    # bool is an int subclass; the contract means real integers.
    return isinstance(value, int) and not isinstance(value, bool)


def validate_event(event: Any) -> List[str]:
    """Return a list of contract-#1 violations (empty = valid)."""
    if not isinstance(event, dict):
        return ["event is not a JSON object"]

    errors = []
    for field in REQUIRED_FIELDS:
        if field not in event:
            errors.append("missing required field %r" % field)
    if errors:
        return errors  # cannot check further without the fields present

    if not _is_int(event["ts_ms"]) or event["ts_ms"] < 0:
        errors.append("ts_ms must be a non-negative integer (monotonic ms)")
    if not isinstance(event["event"], str) or event["event"] not in KNOWN_EVENTS:
        errors.append(
            "event must be one of %s, got %r" % (KNOWN_EVENTS, event["event"])
        )
    if not _is_int(event["keycode"]) or not 0 <= event["keycode"] <= 255:
        errors.append("keycode must be an integer HID usage id in 0..255")
    if event["source"] not in VALID_SOURCES:
        errors.append("source must be one of %s, got %r" % (VALID_SOURCES, event["source"]))
    for field in ("device", "session"):
        if not isinstance(event[field], str) or not event[field]:
            errors.append("%s must be a non-empty string" % field)
    return errors


def iter_events(path: str) -> Iterator[Dict[str, Any]]:
    """Yield validated events from a contract-#1 JSONL file ('-' = stdin)."""
    if path == "-":
        import sys
        handle = sys.stdin
        close = False
    else:
        handle = open(path, "r", encoding="utf-8")
        close = True
    try:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            import json
            try:
                event = json.loads(stripped)
            except ValueError as exc:
                raise JsonlValidationError(path, line_no, "invalid JSON: %s" % exc)
            errors = validate_event(event)
            if errors:
                raise JsonlValidationError(path, line_no, "; ".join(errors))
            yield event
    finally:
        if close:
            handle.close()


def load_events(path: str) -> List[Dict[str, Any]]:
    """Load every event from a contract-#1 JSONL file."""
    return list(iter_events(path))


def load_sessions(path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Group validated events by session id, each sorted by ts_ms."""
    sessions: Dict[str, List[Dict[str, Any]]] = {}
    for event in iter_events(path):
        sessions.setdefault(event["session"], []).append(event)
    for events in sessions.values():
        events.sort(key=lambda e: e["ts_ms"])
    return sessions
