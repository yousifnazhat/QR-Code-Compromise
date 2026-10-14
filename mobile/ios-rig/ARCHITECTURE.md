# P6 iOS Rig — Layered Architecture (W6.8)

> **AUTHORIZATION — LAB ONLY.** iOS Simulator and owned devices only
> (`docs/governance/policy.md` §1). Historical/patched-classes-only posture
> per policy §7; novel findings → coordinated disclosure. **Xcode is the LAST
> item in the project plan — nothing below may assume it exists.** The layer
> design is built so the whole rig is testable on a machine without Xcode
> (guard layer green, sim layer honestly red/skipped).

## 0. Design rule: the rig must be fully specified before Xcode exists

The lab Mac currently has Command Line Tools only (`xcode-select -p` →
`/Library/Developer/CommandLineTools`, no `simctl`). Therefore the rig is
specified in two halves:

- **Specified + green now** (no Xcode needed): L0 guard behavior, L4 listener
  behavior, and the *contracts* of L1–L3 — validated by
  `mobile/ios-rig/tests/` (see §6 and the test results in the phase report).
- **Specified + honestly red/skipped now**: anything that *executes* simctl
  (L1–L3). Tests for those exist, are named, and skip with the reason
  "requires Xcode + simulator runtime (physical slot)". They are the
  definition of done for the Xcode-later run: install Xcode → the skipped
  tests run; the rig is done when they are green.

Layering (bottom = environment, top = research end-state):

```
L4  Kali-side session verification   listener_stub.py (reused, OS-agnostic)
L3  Device log capture               simctl spawn … log stream, P6RIG markers
L2  URL delivery / scheme dispatch   simctl openurl (http arm + p6rigdemo:// arm)
L1  Simulator lifecycle              simctl list / boot / bootstatus
L0  Environment detection & guard    xcrun simctl probe → exit 2 + instructions
```

Each harness script embeds L0 as its first act, so no script can reach L1–L3
on a machine without Xcode. (L0 is duplicated per script rather than shared —
the scripts must be standalone copy-paste-able for the human's physical slot.)

## L0 — Xcode/simctl environment detection + guard layer

- **Contract.** Before any simctl call, a script MUST probe
  `xcrun simctl help`; if unavailable it MUST exit **2** and print on stderr
  the exact install instructions: (1) install Xcode (App Store /
  developer.apple.com/xcode), (2) `sudo xcode-select --switch
  /Applications/Xcode.app/Contents/Developer`, (3) `xcodebuild
  -runFirstLaunch`, (4) re-run. Exit 2 follows the project convention
  "usage/config failure" (same as `create_avd.sh` in the Android rig).
- **Inputs:** none. **Outputs:** none (early return) — or implicit
  permission-to-proceed for L1+.
- **Failure modes:** no Xcode (this machine — *tested, green*); Xcode present
  but no iOS Simulator platform (L1 surfaces it via `simctl list`); license
  not accepted (`xcodebuild -runFirstLaunch` covers).
- **Physical-slot boundary:** everything above L0 stays red until the human
  installs Xcode. No script may guess around it.

## L1 — Simulator lifecycle

- **Contract.** `sim_list.sh` lists available devices (`xcrun simctl list
  devices available`); `sim_boot.sh [<udid-or-name>]` boots the named (or
  first available iPhone) device and blocks until booted
  (`xcrun simctl bootstatus <dev> -b`). Exit 2 with the L0 block if no device
  is found.
- **Inputs:** optional device UDID/name (default: first iPhone in the list).
- **Outputs:** booted simulator; UDID on stdout for the human to reuse in
  `--dev`.
- **Failure modes:** no runtime images (no devices listed) → exit 2 with
  "create one in Xcode > Devices & Simulators"; wrong UDID → simctl's own
  error (surfaced, exit ≠ 0).
- **Physical-slot boundary:** device/runtime creation is Xcode-GUI territory;
  the rig scripts never create devices (creation is a one-time human action).

## L2 — URL delivery + scheme dispatch

- **Contract.** `open_url.sh <url> [--dev <udid|booted>]` hands the URL to the
  simulator via `xcrun simctl openurl` (exit 2 on L0 failure, missing URL, or
  no booted device). Two arms by scheme:
  - `http(s)://` → opens in Safari — **control arm** (must produce no
    `BRIDGE_*` markers),
  - `p6rigdemo://demo?url=<encoded>` → dispatches to the demo app's
    registered scheme, which loads the inner URL in its WKWebView —
    **measurement arm** (U→E→C markers expected).
- **Inputs:** URL; optional device. **Outputs:** simctl exit status; the
  scheme arm's effect is observable only through L3 (log markers) — by
  design, scheme dispatch has no other user-visible trace (documented blind
  spot in `defender-parity.md` §C4).
- **Failure modes:** demo app not installed → iOS shows "cannot open" behavior
  and nothing is dispatched (the human's slot: build the demo app first);
  malformed inner URL → the demo app logs `scheme dispatch` with the
  verbatim payload (part of the deliberate C7 flaw) and fails to load.
- **Physical-slot boundary:** the demo app build is an Xcode-GUI slot
  (`demo-app/README.md`).

## L3 — Device log capture

- **Contract.** `capture_logs.sh [--dev <dev>] [--all]` streams the device
  unified log: `xcrun simctl spawn <dev> log stream --predicate
  'eventMessage CONTAINS "P6RIG"'` (or unpredicated with `--all`). Ctrl-C
  ends the stream. Exit 2 on L0 failure or no device.
- **Inputs:** device selector; predicate flag. **Outputs:** live marker
  stream; the marker grammar is frozen in `harness/run_manifest.json`
  (`U stage: loading…` → `BRIDGE_REACHED` → `BRIDGE_EXEC` →
  `BRIDGE_CALLBACK sent`) — the ordered marker timeline *is* the U→E→C
  measurement.
- **Failure modes:** `log stream` requires the simulator to be booted
  (surfaced); predicate mismatch yields silence (control-arm check uses
  exactly this).
- **Physical-slot boundary:** none beyond L0/L1 — but without Xcode nothing
  emits markers, so L3 tests stay skipped.

## L4 — Kali-side session verification

- **Contract.** REUSE, do not duplicate: `mobile/rig/harness/listener_stub.py`
  (stdlib sockets; explicit `--host`/`--port`, no defaults — policy §2).
  Binds only where told, accepts a session, prints the proof line +
  `VERIFIED`. OS-agnostic by design (works for the Android rig on the Kali
  box and the iOS rig on any lab Mac).
- **Inputs:** `--host`, `--port`, `--forever`. **Outputs:** timestamped
  session log lines.
- **Failure modes:** port in use → exit 2; empty session → "not verified".
- **Physical-slot boundary:** none — fully testable now (green test suite in
  `tests/test_listener.py`).

## 6. Test suite — the definition of done

`mobile/ios-rig/tests/` (stdlib `unittest`, runnable with any python3):

| Test module | Class | Covers | Expected on this no-Xcode Mac |
|---|---|---|---|
| `test_guard_paths.py` | L0 | every harness script exits 2 with the exact install instructions; usage errors; guard-first ordering | **GREEN** |
| `test_sim_paths.py` | L1–L3 | device listing, boot, openurl delivery arms, marker capture against the run-manifest grammar | **SKIPPED** with reason `requires Xcode + simulator runtime (physical slot)` |
| `test_listener.py` | L4 | listener accept/verify, explicit-binding rule, usage errors | **GREEN** |

Run: `python3 -m unittest discover -s mobile/ios-rig/tests -v`

The sim-path tests are the acceptance criteria for the Xcode-later run: once
Xcode exists, they run unmodified; the rig is done when they are green
(plus the demo app's marker flow observed once by the human).

## 7. Files (implementation fills in behind the contracts)

```
mobile/ios-rig/
├── ARCHITECTURE.md           ← this file
├── README.md                 (constraints, chain, telemetry)
├── harness/                  (L0–L3 scripts + run_manifest.json)
├── staging/payload.example.html
├── demo-app/                 (deliberately flawed-by-design WKScriptMessageHandler app)
└── tests/                    (§6 — green/red evidence, definition of done)
```
