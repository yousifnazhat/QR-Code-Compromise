# P6RigDemo — deliberately flawed-by-design bridge app (lab only)

> **AUTHORIZATION — LAB ONLY** (`docs/governance/policy.md` §1/§7). iOS
> Simulator / owned devices only. The flaw demonstrated here is the **app
> author's own bridge design** (C7 class), because iOS has *no* platform-level
> `addJavascriptInterface` analogue — that absence is the phase's contrast
> finding (`mobile/docs/ios-surfaces.md` §1). Historical, patched examples of
> the class: Cordova iOS CVE-2015-5207 / CVE-2015-5208
> (`mobile/inventory/chain-classes.csv`).

## Creating the project (**physical slot** — needs Xcode)

Current Xcode templates regenerate project files, so build the shell by hand
once (~2 minutes), then paste in the committed sources:

1. Xcode → **File → New → Project → iOS App**, name **`P6RigDemo`**,
   Interface: *SwiftUI* (default), Language: *Swift*.
2. In the new project, delete the contents of the generated `P6RigDemoApp.swift`
   and replace them with **`P6RigDemo/P6RigDemoApp.swift`** from this directory.
3. Add **`P6RigDemo/AppDelegate.swift`** and **`P6RigDemo/ViewController.swift`**
   to the app target (drag into Xcode, check the target box).
4. Register the custom scheme (the C4-reachability measurement): Target →
   **Info** tab → **URL Types** → add:
   - Identifier: `com.qrcompromise.p6rigdemo`
   - URL Schemes: `p6rigdemo`
5. Allow cleartext HTTP **for lab runs only** (the staging server is plain
   HTTP on the lab host): Target → **Info** → add
   `NSAppTransportSecurity` → `NSAllowsLocalNetworking = YES`
   (if your staging host is not local, use an HTTPS staging URL instead).
6. **Build & Run** on the booted simulator (`mobile/ios-rig/harness/sim_boot.sh`).

## Honest notes

- The `exec` arm of the demo bridge runs `/bin/sh -c <cmd>` — on the
  **simulator** this executes on the host Mac (simulator apps are native);
  real iOS apps cannot fork processes. The exec arm is therefore a
  simulator-only measurement aid proving page JS reached app-process code;
  the `mark`/`callback` arms behave identically on device. Rig demo bodies are
  benign markers only (policy §2).
- The bridge handler performs **no origin check, no schema validation, no
  command allowlist** — that is the deliberate C7 flaw. Everything it does on
  a message is this app's own code, which is precisely the iOS-vs-Android
  contrast: on Android the platform once handed every app this footgun
  (C1); on iOS the platform doesn't, so we have to write the footgun.
