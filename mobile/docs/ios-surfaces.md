# P6 Mobile-Lure — iOS Post-Scan URL Attack-Surface Taxonomy (W6.6)

> **AUTHORIZATION — LAB ONLY.** Research scaffolding for the QR-Code-Compromise
> project (authorized security research). Everything in `mobile/` is exercised
> only on the iOS Simulator, owned test devices, and deliberately vulnerable
> lab builds per `docs/governance/policy.md` §1. Historical classes cited here
> are **public, already-patched** vulnerabilities (policy §7). Any *novel*
> finding is routed through **coordinated disclosure** (policy §7: private
> vendor report, embargo, class-analysis-only publication) — never a
> weaponized exploit for an unpatched consumer surface.

## 1. Scope and the iOS contrast thesis

Same chain model as the Android taxonomy
(`mobile/docs/surface-taxonomy.md`): **S (scan + present) → U (open URL) →
E (execution surface fires) → C (callback/session)**. The QR is still just a
URL carrier.

The central iOS finding, stated up front:

> **The Android C1 class (`addJavascriptInterface` reflection RCE) is absent
> on iOS by platform design.** iOS exposes no automatic object-method binding
> to web content. The WKWebView bridge primitive is *message-passing* —
> `WKScriptMessageHandler` hands the app a JSON-ish message and the **app
> author writes the code** that acts on it
> (developer.apple.com/documentation/webkit/wkscriptmessagehandler). There is
> no reflection surface for page JS to walk into `Runtime.exec`-style
> machinery. The price of that design is that the chain burden moves from the
> **platform** to the **app author**: the iOS analogue of C1 is **C7 —
> app-authored bridge input-validation flaws** (public, patched examples:
> Apache Cordova iOS, CVE-2015-5207/CVE-2015-5208), where the framework or
> app validates bridge input badly. That asymmetry is the contrast finding
> this phase documents, and it is why the iOS rig
> (`mobile/ios-rig/`) demonstrates a *deliberately flawed-by-design app
> bridge* rather than a platform hole.

**Class IDs are shared with the Android docs and the inventory.** C7 is new
in this extension; classes C1–C6 and M0 are defined in
`mobile/docs/surface-taxonomy.md`.

| ID | Chain class | iOS existence | Inventory rows (iOS side) |
|---|---|---|---|
| C1 | JS-bridge RCE (`addJavascriptInterface`) | **ABSENT by design** (message-passing bridges; no reflection binding) | — |
| C2 | WebView same-origin / file-scheme bypass | No comparable historical CVE row; WKWebView isolates content per-app with restricted default surface | — |
| C3 | Browser/WebView engine n-day (renderer RCE) | **YES** — WebKit is the only engine (see §2) | CVE-2016-4622, CVE-2012-3748, CVE-2018-4233, CVE-2021-1879 |
| C4 | `intent://` / custom-scheme handler abuse | **YES** (shape differs: scheme hijacking, no intent/parcel surface) | documented class (see §4); app-level CVEs land under C7 |
| C5 | Page-embedded media-decoder RCE | **YES** — decoder-in-renderer path | CVE-2010-1797 (FreeType CFF via MobileSafari) |
| C6 | Install-flow / package-signature bypass | **DOESN'T MAP** — mandatory code signing, no sideload consent chain (see §6) | — |
| C7 | Hybrid-framework app-bridge input-validation flaws | **YES — the iOS C1-analogue class** | CVE-2012-6637, CVE-2015-5207, CVE-2015-5208 |
| M0 | MDM/enrollment profile class (non-shell) | **YES — strongest on iOS** (see §7) | documented class |

---

## 2. iS1 — Safari/WebKit: the only real engine

- **What code runs.** On iOS, every browser and every embedded web view runs
  **WebKit** — App Review requires apps that browse the web to use the
  WebKit framework and WebKit JavaScript (App Store Review Guidelines 2.5.6,
  developer.apple.com/app-store/review/guidelines/). So the scanned URL's
  first execution surface is always the same engine family: JavaScriptCore
  + WebKit's sandboxed rendering path, whether in Safari,
  SFSafariViewController, or a WKWebView.
- **User-consent level.** Same as Android S1: lowest. The decoded URL opens in
  Safari (or an in-app SFSafariViewController) on tap; iOS's Camera app even
  has built-in QR recognition that surfaces decoded URLs as a notification —
  the scan-to-open gap is *platform-integrated* (see §5).
- **Historical exploitation classes.** **C3 (WebKit n-day family)** — all
  patched, all public:
  - CVE-2016-4622 (WebKit memory corruption; iOS 9.3.3 / Safari 9.1.2 —
    public advisory ZDI-16-485),
  - CVE-2012-3748 (WebKit race condition via JavaScript arrays; iOS 6.0.1 /
    Safari 6.0.2 — NVD),
  - CVE-2018-4233 (WebKit; iOS 11.4 / Safari 11.1.2 — NVD/Apple advisory),
  - CVE-2021-1879 (WebKit universal cross-site scripting; fixed out-of-band
    in iOS 12.5.2 / 14.4.2 with **Apple acknowledging in-the-wild
    exploitation** — NVD, Apple advisory).
  And the **C5 (decoder-in-page) class**: CVE-2010-1797 — FreeType CFF
  Type2 CharStrings stack overflows, reachable from MobileSafari by
  rendering a crafted PDF/font, publicized by the jailbreakme.com page
  exploit; fixed in iOS 4.0.2 (NVD).
- **Defender detection signals.** WebKit publishes security advisory pages
  (webkit.org/security/); Apple ships out-of-band security updates for
  exploited WebKit bugs (CVE-2021-1879) and documents fraud/phishing
  warnings in Safari (Apple Platform Security guide,
  support.apple.com/guide/security/welcome/web). Patch latency via OTA is
  the defender-visible metric (see `defender-parity.md` iOS rows).

## 3. iS2 — WKWebView + WKScriptMessageHandler (the C1-less bridge)

- **What code runs.** `WKWebView` runs web content **out-of-process**; the
  page never shares a process or a Java/object namespace with the app. The
  only page→app channel is explicit: `window.webkit.messageHandlers.<name>
  .postMessage(...)` delivered to a handler the app registered
  (developer.apple.com/documentation/webkit/wkscriptmessagehandler,
  WKWebView docs developer.apple.com/documentation/webkit/wkwebview).
  Whatever code runs on a message is **app-authored**.
- **User-consent level.** Silent, like Android S2 — a page can attempt a
  `postMessage` at any time; whether anything happens is up to the app's
  handler.
- **Historical exploitation classes.** The documented, patched family is
  **C7**: Apache Cordova iOS — CVE-2015-5207 (URL-whitelist bypass →
  arbitrary resource load), CVE-2015-5208 ("execute arbitrary plugins via a
  link", NVD), and cross-platform CVE-2012-6637 (non-anchored domain
  whitelist regex in the bridge, Cordova/PhoneGap ≤ 3.3.0/2.9.0). These are
  exactly the shape of the rig's deliberately flawed demo handler
  (`mobile/ios-rig/demo-app/`): an app that trusts a message's payload and
  executes it.
- **Defender detection signals.** App Store review + platform static
  analysis; enterprise managed-app configurations; in-app bridge abuse is
  otherwise invisible to the OS (no platform marker — same honest gap as
  Android C1). See `defender-parity.md` §C7.

## 4. iS3 — URL schemes + universal links (associated domains)

- **What code runs.** Custom URL schemes (`myapp://`) declared via
  `CFBundleURLTypes` dispatch the URL to the first/registered handler app,
  with attacker-controlled path/query parsed by the app. Universal links
  (`https://` + `apple-app-site-association` on the domain) skip the
  ambiguity by verifying the domain's entitlement — Apple introduced them
  precisely because **custom schemes can be claimed by any other installed
  app** (documented in Apple's universal-links guide,
  developer.apple.com/documentation/xcode/allowing-apps-and-websites-to-link-to-your-content).
- **User-consent level.** Scheme dispatch is app-declared and
  prompt-free; universal links open without a prompt once the association
  is valid.
- **Historical exploitation classes.** **C4-shaped scheme abuse**
  (hijacking/dispatch manipulation) is a documented research class on iOS —
  the platform mitigation story (universal links replacing schemes) is the
  primary-source-backed statement of the attack surface. CVE'd, already
  patched instances at the *framework* level live under C7 (Cordova iOS
  whitelist/scheme rows). Unlike Android there is no `intent://`-style
  serialized-component surface — a meaningful structural narrowing.
- **Defender detection signals.** Scheme dispatch is not logged for the
  user; MDM can restrict apps entirely; universal-link associations are
  auditable (the AASA file is fetchable per domain). See
  `defender-parity.md` §C4 (iOS column).

## 5. iS4 — QR-scanner app URL handling + built-in Camera QR recognition

- **What code runs.** Same scan→open gap as Android S5, with two iOS
  specifics: (a) the stock **Camera app decodes QR codes natively** and
  presents the URL as a notification — one tap opens Safari, making the
  stock scan-to-open path unusually consistent; (b) third-party scanners
  open URLs in SFSafariViewController or an in-app WKWebView, whose bridges
  are only as safe as the scanner app's handler (C7 surface).
- **User-consent level.** One tap (Camera) to zero (scanner apps that
  auto-open) — the CMU "QRishing" measurement of user susceptibility to
  exactly this trust gap applies cross-platform (Vidas et al., FC 2013 USEC,
  andrew.cmu.edu/user/nicolasc/publications/Vidas-USEC13.pdf).
- **Historical exploitation classes.** C7 via scanner-embedded hybrid
  webviews; C3/C5 in the rendering path behind the open. The rig's
  `open_url.sh` (`xcrun simctl openurl`) is the instrumented equivalent of
  this step.
- **Defender detection signals.** Same honest gap as Android S5: auto-open is
  not a platform-logged event. See `defender-parity.md` §S5/iS4 row.

## 6. iS5 — Install flows: why C6 doesn't map

- **What code runs.** On stock iOS there is **no APK-equivalent sideload
  consent chain**: apps install through the App Store (reviewed, signed), or
  through enterprise/in-house distribution which requires a **managed or
  trusted enterprise certificate** plus explicit user profile consent.
  There is no PackageInstaller-style "install unknown app" toggle that a
  scanned URL can walk the user through, and all executable code must be
  code-signed for the platform to run it (Apple Platform Security guide,
  support.apple.com/guide/security/welcome/web).
- **Why C6 (signature-bypass install class) doesn't map.** C6's Android
  rows (Master Key CVE-2013-4787, Janus CVE-2017-13156) abuse the *system's
  own signature-verification layer*, which iOS consumers never exercise
  because there is no consumer-facing install surface other than the store.
  The closest iOS abuse class is **M0-adjacent**: phishing a user into
  installing an enterprise-signed payload — which is a *policy/consent*
  attack with loud telemetry, not a signature bypass.
- **Defender detection signals.** Enterprise-signing abuse is visible and
  revocable (certificate revocation kills every app signed by it — a
  kill-switch Android's class lacks); MDM sees every install it manages. See
  `defender-parity.md` §C6/§M0 iOS rows.

## 7. iS6 — MDM configuration profiles (M0): the strongest iOS story

- **What code runs.** Nothing until consent: a page offers an enrollment or
  configuration *profile*; the user must explicitly install it (Settings
  shows repeated, unmissable warnings — Apple Platform Deployment guide,
  support.apple.com/guide/deployment/plan-your-configuration-profiles-dep9a318a393/web).
- **End-state: policy and credential influence, NOT code execution** —
  documented as the separate M0 class, not a shell substitute (same framing
  as Android S7).
- **Why iOS is the stronger M0 story:** profile installation and device
  enrollment are visible to both the user (Settings > General > VPN & Device
  Management) and the UEM console at fleet level, and profiles cannot
  install silently — the class is loud by construction.

---

## 8. Android-vs-iOS contrast table

| Chain class | Android | iOS | Why |
|---|---|---|---|
| C1 platform JS-bridge RCE | **YES** (historical: CVE-2012-6636 family) | **ABSENT** | iOS bridges are message-passing (`WKScriptMessageHandler`); no reflection-exposed object graph from page JS. Burden moves to app authors → C7. |
| C2 WebView SOP/file bypass | **YES** (historical: CVE-2014-6041) | no comparable historical row | WKWebView is out-of-process with a restricted default surface; no committed inventory row — structural, not evidence-backed, so not claimed |
| C3 engine n-day renderer RCE | **YES** (V8/Chrome rows) | **YES** (WebKit rows incl. ITW CVE-2021-1879) | Both platforms render attacker-influenced content in a complex engine; iOS centralizes it (WebKit mandate), Android splits Chrome/V8 vs WebView |
| C4 scheme/deep-link abuse | **YES** (`intent://` rows) | **YES** (scheme hijacking shape) | Android's serialized `intent://` extras surface has no iOS equivalent; iOS narrows abuse to scheme hijacking, mitigated by universal links |
| C5 page-embedded decoder RCE | **YES** (Stagefright CVE-2015-1538) | **YES** (FreeType/PDF CVE-2010-1797) | Both platforms have historical decoder-in-renderer paths |
| C6 install/signature bypass | **YES** (Master Key, Janus) | **DOESN'T MAP** | No consumer sideload chain; mandatory code signing; nearest analogue is enterprise-cert abuse (M0-adjacent, loud + revocable) |
| C7 app-authored bridge flaws | YES (Cordova Android rows sit in C4/C7 family) | **YES — the iOS C1-analogue** | Framework/app bridge validation (Cordova iOS CVE-2015-5207/5208, cross-platform CVE-2012-6637) |
| M0 profile class | YES | **YES, loudest** | Visible profile UX + UEM events; cannot be silent |

## 9. Cross-references

- Evidence rows: `mobile/inventory/chain-classes.csv` (C3/C5/C7 iOS rows).
- iOS rig (deliberately flawed-by-design WKScriptMessageHandler demo +
  simctl harness): `mobile/ios-rig/README.md`.
- Defender mirror, including iOS controls (App Store review, MDM, signing,
  WebKit hardening): `mobile/docs/defender-parity.md`.
- Android taxonomy (class definitions): `mobile/docs/surface-taxonomy.md`.
- Disclosure gating for any novel finding: `docs/governance/policy.md` §7;
  staging: `mobile/docs/research-plan.md`.
