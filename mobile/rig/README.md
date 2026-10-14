# P6 Android Emulator Lab Rig (W6.3)

> **AUTHORIZATION — LAB ONLY.** Emulator and **owned devices only**
> (`docs/governance/policy.md` §1). This rig reproduces **historical,
> already-patched** vulnerability classes (policy §7) on **deliberately
> vulnerable builds** (legacy API levels) to measure the QR→URL→code-execution
> chain and capture defender telemetry. It is not pointed at any consumer
> device or unpatched surface; any *novel* finding discovered while working
> with it goes through coordinated disclosure per policy §7.

## 1. What this rig measures

The historical **C1 chain class** (`addJavascriptInterface` reflection RCE —
CVE-2012-6636 family; see `mobile/inventory/chain-classes.csv`) as the
canonical demonstrable path:

```
QR sheet (URL payload, printed via qr-ducky sheet)
   → scan/open  (physical slot, or load_url.sh = adb VIEW intent)
   → URL lands in the rig app's WebView  (U stage)
   → page JS reaches window.Android bridge  (E stage)
   → bridge runs app-process command (the class's Runtime.exec primitive)
   → benign session callback to the Kali-side listener stub  (C stage)
```

The app's bridge body is **benign-by-default** (policy §2): it proves the
execution primitive with marker commands and a TCP session-proof line
(`P6RIG-SESSION device=<Build.FINGERPRINT>`) instead of a real reverse shell.
That proof-of-session is the rig's end-state measurement — the historical
exploits shipped a shell on exactly this reachability.

The same rig doubles as the control-arm measurement: the same URL opened in
the stock browser (no bridge) must produce **no** `BRIDGE_*` markers.

## 2. Setup

### 2.1 Android SDK / Studio — **physical slot for the human**

The SDK install is interactive and machine-specific; it is intentionally not
automated. On the lab box:

1. Install **Android Studio** (developer.android.com/studio), which brings the
   SDK, emulator, and `platform-tools` (adb).
2. In Studio: **Settings → Languages & Frameworks → Android SDK → SDK Tools**,
   tick **Android SDK Command-line Tools (latest)**.
3. Make sure these are on PATH (`$ANDROID_HOME` default on macOS:
   `~/Library/Android/sdk`): `emulator/`, `cmdline-tools/latest/bin/`
   (sdkmanager/avdmanager), `platform-tools/` (adb).

### 2.2 Create the AVD (any time after SDK install)

```sh
mobile/rig/harness/create_avd.sh 22 x86_64        # default; API 22, x86_64
```

The script runs (and documents) the canonical commands:

```sh
sdkmanager  "platforms;android-22" "system-images;android-22;default;x86_64"
avdmanager create avd -n p6rig-api22 -k "system-images;android-22;default;x86_64" -d pixel
```

**Why API 22:** modern Android refuses to *install* apps with
`targetSdk < 23`; API 22 still accepts the rig app's `targetSdk 16`, which is
what keeps the C1 reflection window open — the Android 4.2 (API 17) fix gates
Java-Reflection access to bridge objects on the **app's** `targetSdkVersion`
(developer.android.com/reference/android/webkit/WebView#addJavascriptInterface).
Exit code 2 = SDK missing; the script prints the exact commands to run.

### 2.3 Build + install the target app — **physical slot for the human**

Open `mobile/rig/target-app` in Android Studio → **Build → Build APK(s)**,
then:

```sh
adb install -r mobile/rig/target-app/app/build/outputs/apk/debug/app-debug.apk
```

The app (`com.qrcompromise.p6rig`) is the classic public C1 example: a
WebView whose `VulnBridge` object is registered without any
`@JavascriptInterface` annotation, in an app targeting API 16.

## 3. Running the chain

Everything below assumes `<kali-ip>` is **your lab box's** address (policy §2:
the committed example uses RFC 5737 documentation space `192.0.2.10` only).

```sh
# 0. emulator + app up (see §2)
# 1. Kali side: session listener + staging server
python3 mobile/rig/harness/listener_stub.py --host <kali-ip> --port 4444
python3 -m http.server 8000 --directory mobile/rig/staging

# 2. staging page: copy the example, substitute YOUR lab host
cp mobile/rig/staging/payload.example.html mobile/rig/staging/payload.html
#    (edit the Android.callback("192.0.2.10", 4444) line)

# 3. print the URL as a QR sheet (reuses P2 machinery — mobile/qr/README.md)
mobile/qr/url_sheet.sh "http://<kali-ip>:8000/payload.html" out/p6-sheet.pdf

# 4. U stage: hand the URL to the emulator (what a scanner app would do)
mobile/rig/harness/load_url.sh "http://<kali-ip>:8000/payload.html" --pkg com.qrcompromise.p6rig

# 5. optional physical slot: scan the printed sheet with a lab phone and open
#    the URL — observes the real scan→open gap; the adb path is the
#    reproducible instrumented equivalent.
```

The machine-readable definition of these steps, with the expected marker
sequences, is `mobile/rig/harness/run_manifest.json`.

## 4. Telemetry to capture

| Capture | Command | Why |
|---|---|---|
| Chain markers (U→E→C timeline) | `adb logcat -s P6RIG P6RIGQR chromium` | the marker set proves each chain stage in order: `loading url=…` → `BRIDGE_REACHED mark=…` → `BRIDGE_EXEC cmd=…` → `BRIDGE_CALLBACK sent` |
| Session proof (Kali side) | `listener_stub.py` output | `P6RIG-SESSION device=<Build.FINGERPRINT>` + peer IP/port + wall-clock — verifies the C stage without a shell |
| Package evidence | `adb shell dumpsys package com.qrcompromise.p6rig` | shows `targetSdk=16` — the C1 gate condition |
| Control arm | same URL via stock browser (`load_url.sh` without `--pkg`) | **no** `BRIDGE_*` markers expected — proves markers track the vulnerable class, not generic page activity |
| Install-time signals (Stage 2, C6 class) | PackageInstaller prompts on a sideload | the consent-ladder baseline for `defender-parity.md` §C6 |

Logcat markers are the canonical device-side telemetry; all rig measurements
(timestamps, ordering, session proof) go into the Stage-2 run record
(`mobile/docs/research-plan.md` Stage 2).

## 5. Files

```
mobile/rig/
├── README.md                 ← this file
├── harness/
│   ├── create_avd.sh         # AVD creation (avdmanager commands; exit 2 = SDK slot)
│   ├── load_url.sh           # adb shell am start -a android.intent.action.VIEW -d <url>
│   ├── listener_stub.py      # Kali-side session-verification listener (stdlib, no defaults)
│   └── run_manifest.json     # machine-readable chain definition + expected markers
├── staging/
│   └── payload.example.html  # benign example page (placeholders per policy §2)
└── target-app/               # deliberately vulnerable Android Studio project
    └── app/src/main/java/com/qrcompromise/p6rig/MainActivity.java   # the C1 example
```

## 6. Scope limits

- **Emulator + owned devices only** — nothing here runs against hardware or
  accounts the project does not own.
- Historical classes only: the rig app is vulnerable *by construction* at a
  legacy API level; every chain class it can demonstrate is public and
  already patched (inventory, `mobile/inventory/`).
- No attack payloads: bridge demo bodies are benign markers (policy §2).
- Novel-research hooks (if any emerge from Stage 3) are disclosed per policy
  §7 — coordinated, embargoed, class-level output only.
