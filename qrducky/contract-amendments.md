# Contract amendments proposed by P2 (qrducky)

Frozen contract #2 (COORDINATION.md) is implemented as specified. The
additions below are **additive, non-breaking** CLI surface — listed here per
the charter's amendment procedure (coordinator review; PRs would touch only
`docs/contracts/` on master). Nothing P0/P3 consumes was changed or
renarrowed.

## #2 qr-ducky CLI — additive flags

```
qr-ducky encode --payload <file|-> --mode alnum|hex|b64 [--layout US|DE|FR]
                [--json] [--config qrducky.toml]
                [--beacon-id <id> --engage-target <name>]        # W2.3
qr-ducky sheet  --payload <file> --out <pdf|png> [--module 4mm] [--ec M]
                [--mode alnum|hex|b64] [--layout US|DE|FR]
                [--png]                                            # also .png next to .pdf
                [--beacon-id <id> --engage-target <name>]          # W2.3
                [--config qrducky.toml]
qr-ducky bench  --target <vm-name> [--repeat N]
                [--payload <file>] [--dry-run] [--config qrducky.toml]
```

Rationale:
- `--json` on encode: P3 needs the keystroke stream + decoder hint machine-
  readably; stdout text stays bare for shell use.
- `--config`: config discovery (`--config` > `$QRDUCKY_CONFIG` > `./qrducky.toml`)
  needs an explicit override for reproducible runs.
- `--mode/--layout/--png` on sheet: P0 prints encoded payload sheets, not
  raw payload text; PNG was requested for benches without vector printers.
- `bench --payload/--dry-run`: bench must not invent payloads (GX.2 posture —
  payloads are always explicit) and must be exercisable without the rig.
  Dry-run emits the exact P0 rig protocol conversation (exit 0); live mode
  without rig/pyserial exits 3 with a structured boundary record.

Exit codes (documented, unchanged in kind): 0 success, 1 runtime failure,
2 usage/config failure, 3 documented not-implemented boundary.

## Non-amendment notes (code reuse)

- `qrducky/pdfsheet.py` is P1's stdlib PDF writer (`tools/gen_test_sheets.py`,
  merge bbb1775) extracted as a package module so P1 sweep sheets and
  qr-ducky payload sheets share one PDF path. No interface change; noted here
  at the coordinator's request. Keep byte-compatible with the P1 original
  unless coordinated.
- `bench` speaks P0's rig serial protocol (lab/rig/README.md): same
  command words, same <=47-byte fragment framing, same ACK stop-and-wait.
  One protocol, no second invention.