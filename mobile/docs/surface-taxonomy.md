# P6 Mobile-Lure — Post-Scan URL Attack-Surface Taxonomy (W6.1)

> **AUTHORIZATION — LAB ONLY.** Research scaffolding for the QR-Code-Compromise
> project (authorized security research). Everything in `mobile/` is exercised
> only on emulators, owned test devices, and deliberately vulnerable lab builds
> per `docs/governance/policy.md` §1. Chain classes demonstrated in the rig use
> **historical, already-patched** vulnerabilities (policy §7). Any *novel*
> vulnerability found in third-party software is routed through **coordinated
> disclosure** (policy §7: private vendor report, embargo, class analysis as
> the published output) — never a weaponized exploit for an unpatched consumer
> surface.

## 1. Scope and chain model

A QR code is a URL carrier: the phone-side chain begins the moment the scanned
URL is *opened*. The post-scan chain is modeled as four stages:

```
S (scan + present) → U (open URL) → E (execution surface fires) → C (callback/session)
```

The P6 research question is: **which E surfaces exist on a modern phone, what
code runs on them, how much user consent they require, and what a defender
sees when they fire.** The QR step itself is commodity machinery already built
by P2 (`qr-ducky sheet`, reused unchanged — see `mobile/qr/README.md`).

Every surface below lists: (a) what code runs, (b) user-consent level, (c)
historical exploitation classes (all already-patched — see
`mobile/inventory/chain-classes.csv` for the evidence rows), and (d) defender
detection signals (expanded in `mobile/docs/defender-parity.md`, the
mirror-image of this taxonomy).

**Class IDs are shared across all P6 docs.** C1–C6 are the historical chain
classes in the inventory; M0 is the non-shell profile class, documented here
but explicitly *not* the shell end-state.

| ID | Chain class | Stage(s) | Inventory rows |
|---|---|---|---|
| C1 | JS-bridge RCE (`addJavascriptInterface` family) | U→E→shell | CVE-2012-6636, CVE-2014-1939, CVE-2014-7224 |
| C2 | WebView same-origin / file-scheme bypass | U→E (pivot) | CVE-2014-6041 |
| C3 | Browser/WebView engine n-day (renderer RCE) | U→E→shell | CVE-2016-4622, CVE-2018-17463, CVE-2019-5782, CVE-2020-6418 |
| C4 | `intent://` / custom-scheme handler abuse | U→E (component reach) | CVE-2014-3502, CVE-2016-4782, CVE-2017-5096, CVE-2017-17553 |
| C5 | Page-embedded media-decoder RCE | U→E→shell | CVE-2015-1538 |
| C6 | Install-flow / package-signature bypass | U→(download/consent)→shell | CVE-2013-4787, CVE-2017-13156 |
| C7 | Hybrid-framework app-bridge input-validation flaws | U→E→shell (app-authored bridge) | CVE-2012-6637, CVE-2015-5207, CVE-2015-5208 |
| M0 | MDM/enrollment **profile** class (non-shell) | U→consent→policy control | documented below; no CVE rows |

---

## 2. Surfaces

### S1 — Browser renderers (Chrome on Android, Safari on iOS)

- **What code runs.** The scanned URL opens in a full browser: a sandboxed
  renderer executes attacker-influenced HTML/JS (V8 in Chrome, JavaScriptCore
  in Safari). Renderers are the *first* post-scan execution surface — no
  install, no extra permission dialog; the page runs with the privileges of
  the renderer sandbox.
- **User-consent level.** Lowest: a scan action plus (on some scanner apps) a
  tap on the decoded-URL preview. Many scanner apps auto-open on decode
  (see S5).
- **Historical exploitation classes.** C3 — engine n-days. Verifiable public
  examples, all patched and each with a public writeup/exploit: CVE-2018-17463
  (V8 incorrect side-effect annotation, fixed in Chrome 70.0.3538.64 — Google
  Chrome Releases, "Stable Channel Update for Desktop",
  <https://chromereleases.googleblog.com/2018/10/stable-channel-update-for-desktop.html>),
  CVE-2019-5782 (V8 incorrect optimization assumptions, fixed in Chrome
  72.0.3626.81), CVE-2020-6418 (V8 type confusion, fixed in Chrome
  80.0.3987.122; Google acknowledged in-the-wild exploitation — Chrome
  Releases blog, <https://chromereleases.googleblog.com/2020/02/stable-channel-update-for-desktop_24.html>),
  and on iOS CVE-2016-4622 (WebKit, fixed in iOS 9.3.3 / Safari 9.1.2 —
  public advisory ZDI-16-485, <https://www.zerodayinitiative.com/advisories/ZDI-16-485/>).
  Sources: NVD records for each CVE (nvd.nist.gov), Google Chrome Releases
  blog, ZDI advisory.
- **Defender detection signals.** Safe Browsing interstitials before the page
  renders; forced auto-update through the platform store; renderer crash
  telemetry; site isolation limiting a renderer bug's reach (see
  `defender-parity.md` §C3).

### S2 — In-app WebViews and JS bridges (`addJavascriptInterface` class)

- **What code runs.** Thousands of non-browser apps render web content in
  `android.webkit.WebView`. If the app registers Java objects via
  `addJavascriptInterface()`, **JavaScript on the page can call that Java
  object's methods — app-process code, running with the app's UID**. This is
  the single most-studied post-scan code-execution primitive on Android.
- **User-consent level.** Page render happens silently inside the host app.
  The classic attack needs the URL to reach the vulnerable *app's* WebView
  (via its own scheme handler, an embedded ad/web view, or a redirect from
  the browser).
- **Historical exploitation classes.**
  - **C1 (JS-bridge reflection RCE).** On Android < 4.2 / for apps targeting
    API < 17, the exposed Java object was reachable through *Java Reflection*,
    letting page JS call `Runtime.exec()` — full RCE from a rendered page.
    CVE-2012-6636 (Android API before 17, NVD: "allows remote attackers to
    execute arbitrary methods of Java objects by using the Java Reflection
    API"); CVE-2014-1939 (SearchBox object via `BrowserFrame.java`,
    Android before 4.4); CVE-2014-7224 (accessibility and
    `accessibilityTraversal` objects, Android prior to 4.4.0). Public
    exploit: Metasploit `android/browser/webview_addjavascriptinterface`
    (<https://www.rapid7.com/db/modules/exploit/android/browser/webview_addjavascriptinterface>).
    The platform fix: since API 17 only methods annotated
    `@JavascriptInterface` are exposed *to apps targeting 17+* — the
    reflection block keys on the **app's** `targetSdkVersion`, so
    legacy-target apps remain vulnerable on any OS build
    (<https://developer.android.com/reference/android/webkit/WebView#addJavascriptInterface>,
    <https://developer.android.com/reference/android/webkit/JavascriptInterface>).
  - **C2 (same-origin / file-scheme bypass).** CVE-2014-6041 — Android WebView
    before 4.4 let page JS bypass same-origin policy via a `\u0000` in an
    `onclick="window.open(...)"` attribute, enabling local-file theft as a
    post-render pivot (NVD).
  - The hybrid C4-over-WebView case: Apache Cordova < 3.5.1 (CVE-2014-3502)
    parsed crafted URL schemes inside the WebView bridge itself
    (NVD; Apache Cordova security advisory, August 2014).
- **Defender detection signals.** WebView is an updatable system component
  (<https://developer.android.com/develop/ui/views/layout/webapps/managing-webview>);
  enterprise policies can block legacy-`targetSdk` sideloads; static analysis
  of an APK reveals bridge-object exposure (see `defender-parity.md` §C1–C2).

### S3 — `intent://` deep links and custom-scheme handlers

- **What code runs.** A page (or scanner app) can trigger *native app
  components* without any install or permission prompt: `intent://` URIs are
  parsed by the browser into Android Intents, and custom schemes
  (`myapp://`) dispatch to whichever app registered the scheme. The launched
  component is exported application code receiving attacker-controlled extras.
- **User-consent level.** None-to-one-tap: Chrome historically launched
  BROWSABLE-category intent URIs with no prompt (Chrome documents the
  restrictions it added — explicit components and non-BROWSABLE categories
  are stripped: <https://developer.chrome.com/docs/android/intents>).
- **Historical exploitation classes.** **C4** — policy-enforcement and
  parsing bugs in the scheme-handling path: CVE-2017-5096 (Chrome for
  Android < 60.0.3112.78, "insufficient policy enforcement during navigation
  between different schemes", NVD), CVE-2016-4782 (Lenovo SHAREit before
  3.5.98_ww, crafted `intent:` URL — NVD), CVE-2017-17553 (Dolphin Browser
  12.0.2, insecure parsing of the Intent URI scheme — NVD), CVE-2014-3502
  (Apache Cordova Android < 3.5.1, crafted URI scheme opens arbitrary apps —
  NVD). App-side intent-redirection (delivering a nested Intent to a
  privileged component) is the modern continuation of this class — e.g.
  Samsung's publicly CVE'd intent-redirection fixes (CVE-2021-25377,
  CVE-2021-25379; NVD).
- **Defender detection signals.** Intent launches are not user-visible;
  defense is structural: Chrome's `intent://` restrictions, scheme-handler
  allowlists in enterprise MDM, `android:exported` auditing (see
  `defender-parity.md` §C4).

### S4 — App links (assetlinks `autoVerify`)

- **What code runs.** Android App Links (`https://` links to a verified
  domain) bypass the browser and open the owning app's handler directly. The
  OS verifies the app against `/.well-known/assetlinks.json` on the target
  domain
  (<https://developer.android.com/training/app-links/verify-android-applinks>).
- **User-consent level.** Zero prompts once the app is installed and
  auto-verified; the handler runs with the app's process privileges.
- **Historical exploitation classes.** Mostly **C4-adjacent
  link-hijacking**: mis-verification (a domain's assetlinks statement
  declaring an attacker-relevant app) or unverified `https` links falling back
  to disambiguation dialogs. Google's own documentation warns that incorrect
  `autoVerify` deployment silently reverts to a chooser dialog
  (<https://developer.android.com/training/app-links/verify-android-applinks>).
  No canonical single CVE; treated as a documented abuse class alongside C4
  and exercised in the rig only for *reachability* measurement.
- **Defender detection signals.** App-link verification state is inspectable
  per package (`pm get-app-links` / domain-verification tooling); enterprise
  can restrict which apps may claim domains (see `defender-parity.md` §C4).

### S5 — QR-scanner apps' URL handling (the scan→open gap)

- **What code runs.** The scanner app itself is the first decision point:
  it either (a) auto-opens the decoded URL, (b) shows it for a user tap, or
  (c) renders it in its own **in-app browser/WebView** — sometimes with its
  own JS bridges. Class (c) converts a scanning app into a C1/C2 target and
  (a)/(c) skip the S1 consent step entirely.
- **User-consent level.** Zero (auto-open) to one tap (preview), varying by
  app — no platform-consistent rule. CMU's "QRishing" study measured user
  susceptibility to exactly this scan-to-open trust gap (Vidas, Owusu, Wang,
  Zeng, Cranor, Christin, *QRishing: The Susceptibility of Smartphone Users
  to QR Code Phishing Attacks*, FC 2013 USEC workshops;
  <https://www.andrew.cmu.edu/user/nicolasc/publications/Vidas-USEC13.pdf>).
- **Historical exploitation classes.** C1/C2 when the in-app view uses
  legacy bridges; C4 when the app passes the URL to arbitrary intent
  handlers. Historical in-app-browser implementations shipped exactly this
  bug family (e.g., CVE-2012-2635, Dolphin Browser HD WebView
  mis-implementation, NVD). This surface is where the rig measures the whole
  U→E gap on a deliberately vulnerable build (see `mobile/rig/README.md`).
- **Defender detection signals.** Per-app URL behavior is auditable only by
  static review of the scanner app; auto-open is not logged by the platform
  (see `defender-parity.md` §S5 gap note).

### S6 — Install flows (APK sideload consent steps)

- **What code runs.** If the post-scan page pivots from script-execution to
  **payload installation** (download an APK, then PackageInstaller executes
  it on user confirmation), the attacker needs the consent chain to succeed.
  Android's consent ladder: "install unknown apps" is per-source-app
  (Settings), PackageInstaller shows package name/permissions, and Play
  Protect scans at install and periodically
  (<https://play.google.com/about/play-protect/>).
- **User-consent level.** Highest of all surfaces — multiple explicit taps
  required; historically the weakest link was not the prompt but the
  **signature layer** behind it.
- **Historical exploitation classes.** **C6** — signature-verification
  bypasses that make a *trojaned update to an already-installed app* install
  without raising any prompt beyond the normal one:
  CVE-2013-4787 ("Master Key", Android 1.6–4.2: APK modified in a way that
  does not violate the cryptographic signature — NVD; Bluebox Security
  disclosure, July 2013), and CVE-2017-13156 ("Janus", Android 5.0–8.0: v1
  signature bypass by prepending a DEX to an APK, patched in the Android
  Security Bulletin 2017-12-01,
  <https://source.android.com/docs/security/bulletin/2017-12-01>; public
  analysis: Guardsquare, guardsquare.com; public exploit: Metasploit
  `android/local/janus`,
  <https://www.rapid7.com/db/modules/exploit/android/local/janus/>).
- **Defender detection signals.** Play Protect scan verdicts, install-source
  logging, enterprise "block unknown sources" policy; platform fixes moved
  current builds to the v2/v3 APK signature schemes (see
  `defender-parity.md` §C6).

### S7 — MDM/enrollment profile class (M0) — **documented separately, not the shell goal**

- **What code runs.** Nothing on first contact: a page offers an enrollment
  or configuration *profile* (Apple: configuration profiles — Apple Platform
  Deployment guide,
  <https://support.apple.com/guide/deployment/plan-your-configuration-profiles-dep9a318a393/web>;
  Android: device-admin/enterprise enrollment,
  <https://developer.android.com/work>). If the user consents, the *policy
  plane* is attacker-influenced: VPN configuration, credential/Wi-Fi payloads,
  certificate trust, app restrictions.
- **User-consent level.** One explicit "Install/Trust" tap on a profile that
  most users cannot evaluate. iOS shows repeated warnings; Android's device
  admin enrollment shows activation screens.
- **Why it is a separate class (M0).** The end-state is **policy and
  credential control, not code execution** — no shell, no memory-corruption
  chain. P6 documents it for completeness of the *surface* map and for its
  defender-visible fingerprints, and explicitly does **not** treat it as a
  substitute for the shell end-state. No inventory CVE rows; no rig chain.
- **Defender detection signals.** New-profile notifications and UEM-console
  enrollment events are among the loudest telemetry a defender has — unlike
  every C-class, M0 cannot be silent (see `defender-parity.md` §M0).

---

## 3. Cross-references

- Evidence rows for C1–C7 (all historical, all patched, all with public
  sources): `mobile/inventory/chain-classes.csv` (regenerate:
  `mobile/inventory/build_inventory.py`).
- Mirror-image defender view: `mobile/docs/defender-parity.md`.
- Rig reproduction plan (C1 on a deliberately vulnerable API-16-era build):
  `mobile/rig/README.md`.
- Research staging and disclosure gating (policy §7):
  `mobile/docs/research-plan.md`.
- iOS taxonomy (W6.6, same class IDs): `mobile/docs/ios-surfaces.md` —
  includes the Android-vs-iOS contrast table and the C1-absent-by-design
  finding for iOS bridge surfaces; iOS rig: `mobile/ios-rig/README.md`.
