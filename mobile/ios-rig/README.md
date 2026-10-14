# P6 iOS Simulator Lab Rig (W6.8)
> **Layered design:** `ARCHITECTURE.md` (L0 guard → L1 lifecycle → L2 URL
> delivery → L3 log capture → L4 listener) — per-layer contracts, failure
> modes, and the physical-slot boundary. **The test suite
> (`tests/`, `python3 -m unittest discover -s mobile/ios-rig/tests -v`) is the
> definition of done for the Xcode-later run**: guard-path and listener tests
> are green on this no-Xcode Mac; sim-path tests are defined and skip with an
> explicit reason until Xcode exists.

> **AUTHORIZATION — LAB ONLY.** iOS Simulator and **owned devices only**
> (`docs/governance/policy.md` §1). This rig reproduces the **C7 class —
> app-authored bridge input-validation flaws** — on a deliberately
> flawed-by-design demo app (policy §7 posture: historical, already-patched
> exemplars are the Cordova iOS rows in `mobile/inventory/chain-classes.csv`;
> our demo simply re-creates the flawed *shape* for measurement). Any *novel*
> finding discovered while working with the rig goes through coordinated
> disclosure per policy §7.

## 1. Why this rig demonstrates an app flaw, not a platform hole

iOS has no `addJavascriptInterface` analogue: `WKScriptMessageHandler` is
message-passing and the bridge's behavior is 100% app-authored code
(developer.apple.com/documentation/webkit/wkscriptmessagehandler). The
Android C1 chain class (platform reflection RCE) is **absent by platform
design** — stated as the phase's contrast finding in
`mobile/docs/ios-surfaces.md` §1. So the demonstrable iOS chain class is:

```
QR sheet (URL payload, printed via qr-ducky sheet)
   → scan/open  (physical slot, or simctl openurl = the instrumented U stage)
   → URL lands in the demo app's WKWebView (or Safari — control arm)
   → page JS postMessage to p6rigBridge  (E stage)
   → deliberately unvalidated handler runs marker command / proof callback
     (app-process code)
   → TCP session to the Kali-side listener stub  (C stage)
```

Session end-state is the same benign verification line as the Android rig
(`P6RIG-SESSION ...`) — a *proof of session*, not a shell, per policy §2.

## 2. Setup — **physical slot for the human**

This Mac currently has **Command Line Tools only — no Xcode**; every harness
script detects that and exits 2 with these exact steps:

1. Install **Xcode** (Mac App Store or developer.apple.com/xcode).
2. `sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer`
3. `xcodebuild -runFirstLaunch` (installs the iOS Simulator platform).
4. Build the demo app per `demo-app/README.md` (new Xcode project + paste the
   committed sources, register `p6rigdemo` scheme).

## 3. What this rig CAN vs CANNOT measure (honest constraints)

| CAN measure (on the simulator) | Why |
|---|---|
| Scheme dispatch (C4-shape reachability): which component receives `p6rigdemo://` | `xcrun simctl openurl` delivers it; log markers record the handoff |
| Bridge behavior in the demo app (C7): message → app-process marker command → callback | the demo handler is instrumented (`P6RIG` markers via unified logging) |
| Scan→open gap on the *stock* iOS UX | optional physical slot: scan the printed sheet with a lab phone (Camera's built-in QR recognition → notification → Safari) |
| Enrollment/profile UX (M0) where the runtime allows | profile install flows are viewable on-simulator for research note-taking; enterprise enrollment needs managed infrastructure and is documented, not automated |

| CANNOT measure here | Why / what would be needed |
|---|---|
| Historical WebKit n-days (C3 rows: CVE-2016-4622, CVE-2012-3748, CVE-2018-4233, CVE-2021-1879) | current Xcode ships only recent simulator runtimes — no 2016-era iOS runtimes; reproducing them needs **old owned hardware iPhones** kept at old iOS versions (and would be measurement-only, still policy §7) |
| C5 iOS row (CVE-2010-1797, FreeType via MobileSafari) | same runtime problem, plus the bug predates the simulator era's toolchain; old owned hardware only |
| C6 install/signature class | **does not exist on iOS** — no consumer sideload chain; mandatory code signing (`mobile/docs/ios-surfaces.md` §6). Not a tooling gap — a platform property |
| Jailbreak-level primitives | out of scope: no jailbreaking in P6 (owned devices stay stock except the deliberately vulnerable app) |
| Real-device exec-arm behavior | simulator apps run natively on the host; real iOS apps cannot fork processes — see the honesty note in `demo-app/P6RigDemo/ViewController.swift` |

## 4. Running the chain

Machine-readable definition with all steps, expected markers, and the control
arm: `harness/run_manifest.json`.

```sh
# 0. Xcode slot done (§2), simulator booted:
mobile/ios-rig/harness/sim_list.sh
mobile/ios-rig/harness/sim_boot.sh

# 1. listener (REUSES the Android rig's OS-agnostic stub; explicit host/port only):
python3 mobile/rig/harness/listener_stub.py --host <lab-ip> --port 4445

# 2. staging server + payload (placeholders per policy §2):
python3 -m http.server 8000 --directory mobile/ios-rig/staging
cp mobile/ios-rig/staging/payload.example.html mobile/ios-rig/staging/payload.html  # edit host/port

# 3. telemetry capture (separate terminal):
mobile/ios-rig/harness/capture_logs.sh

# 4. U stage — plain-URL arm (Safari — this is the CONTROL ARM):
mobile/ios-rig/harness/open_url.sh "http://<lab-ip>:8000/payload.html"
#    → expect NO BRIDGE_* markers (no bridge exists in Safari)

# 5. U stage — scheme arm (loads the page inside the demo app = E stage fires):
mobile/ios-rig/harness/open_url.sh "p6rigdemo://demo?url=http%3A%2F%2F<lab-ip>%3A8000%2Fpayload.html"
#    → expect BRIDGE_REACHED → BRIDGE_EXEC → BRIDGE_CALLBACK sent,
#      and the listener prints 'P6RIG-SESSION ios=...' VERIFIED
```

## 5. Telemetry to capture

| Capture | Command | Why |
|---|---|---|
| Chain markers (U→E→C) | `mobile/ios-rig/harness/capture_logs.sh` | unified-log markers, in order |
| Scheme-dispatch record | same log, `scheme dispatch: p6rigdemo -> …` line | C4-shape reachability evidence |
| Session proof | `listener_stub.py` output | C stage verified, peer IP/port + wall-clock |
| Control arm | plain-URL open in Safari | **no** markers — proves the class is the demo app's own bridge, not Safari/page activity |

## 6. Files

```
mobile/ios-rig/
├── ARCHITECTURE.md          ← layered design (L0–L4) + test plan (§6)
├── README.md                ← this file (constraints)
├── harness/
│   ├── sim_list.sh          # xcrun simctl list (guards: exit 2 without Xcode)
│   ├── sim_boot.sh           # xcrun simctl boot + bootstatus
│   ├── open_url.sh           # xcrun simctl openurl (U stage; scheme + http arms)
│   ├── capture_logs.sh       # xcrun simctl spawn ... log stream, P6RIG predicate
│   └── run_manifest.json     # chain definition, expected markers, control arm
├── staging/
│   └── payload.example.html  # benign message-posting page (placeholders §2)
├── demo-app/
    ├── README.md             # project-creation physical slot + honesty notes
    └── P6RigDemo/            # Swift sources (App entry, AppDelegate, ViewController w/ flawed bridge)
└── tests/                   ← definition-of-done suite (guard+listener green now;
                               run: python3 -m unittest discover -s mobile/ios-rig/tests -v)
```

The listener is **not** duplicated: `mobile/rig/harness/listener_stub.py` is
OS-agnostic (stdlib sockets) and serves both rigs.

## 7. Scope limits

- Simulator + owned devices only; the demo app's flaw is *ours*, not a
  third-party's; nothing here touches a consumer surface.
- Historical classes are cited from the patched inventory; they are **not
  reproduced here** (no old runtimes) — see the CANNOT table.
- Novel findings (if any emerge) → policy §7 coordinated disclosure, embargo,
  class-analysis-only publication.
