# P6 Mobile-Lure — Defender Parity Map (W6.4)

> **AUTHORIZATION — LAB ONLY.** Mirror-image companion to
> `mobile/docs/surface-taxonomy.md` (authorized security research,
> `docs/governance/policy.md` §1). For every chain class in the inventory
> (`mobile/inventory/chain-classes.csv` — all historical, already-patched,
> per policy §7), this map states what a **defender** sees and controls, and
> — honestly — where the defender sees nothing. Detection guidance ships at
> parity with the offensive scaffolding (policy §5).

Class IDs are the shared ones from the taxonomy. Each row's *evidence column*
is where the rig (`mobile/rig/`) can supply a first-hand measurement.

## 1. Platform-wide controls (apply to every class)

| Control | What it does | Source |
|---|---|---|
| Google Play Protect | Scans apps at install (including sideloads) and continuously on-device; flags known-malware and riskware before/after install | play.google.com/about/play-protect |
| Platform auto-update | Chrome/WebView/Safari engine + OS security patches ship through the store/OTA; the historical classes below are closed on current builds precisely because of this | developer.android.com/develop/ui/views/layout/webapps/managing-webview; source.android.com/docs/security/bulletin |
| Android Enterprise / MDM | Managed Google Play, app allow/denylists, "block unknown sources" user restriction, work-profile separation | developer.android.com/work |

## 2. Per-class parity

### C1 — JS-bridge RCE (`addJavascriptInterface` family) · CVE-2012-6636, CVE-2014-1939, CVE-2014-7224

- **Structural control (the fix):** since API 17, only `@JavascriptInterface`
  methods are exposed, and the gate keys on the **app's** `targetSdkVersion`
  (developer.android.com/reference/android/webkit/WebView#addJavascriptInterface).
  The mirror-image rule for defenders: **legacy-`targetSdk` apps are the C1
  residue class** — and modern Android (since 10/11 era) refuses to *install*
  apps targeting SDK < 23, which raises the bar for the residue.
- **Install-time telemetry:** Play Protect scan verdicts on the sideload;
  PackageInstaller's "built for an older version" warning/install block;
  enterprise policy can reject legacy-target sideloads outright.
- **Static detection:** APK review/scanners flag bridge registrations
  (public app-sec guidance, e.g. the OWASP Mobile Application Security
  project's WebView checks).
- **Runtime gap (honest):** on a stock build there is **no logcat marker** for
  a page calling a bridge method — nothing distinguishes benign JS-bridge
  traffic from malicious. The rig's `P6RIG BRIDGE_*` markers
  (`mobile/rig/harness/run_manifest.json`) exist only because our build is
  instrumented; that is the measurement the Stage-2 runs record.
- **Rig evidence slot:** C1 chain markers + control arm (no markers in the
  stock browser) — the parity experiment for this row.

### C2 — WebView same-origin / file-scheme bypass · CVE-2014-6041

- **Structural control:** modern WebView defaults hardened (file access off
  by default on current API levels; developer guidance at
  developer.android.com/develop/ui/views/layout/webapps/managing-webview);
  WebView itself is an updatable component, so the 2014-era SOP-bypass family
  is long closed on updated builds.
- **Telemetry:** none platform-side for page-origin violations in
  third-party apps; WebView Safe Browsing interstitials surface only
  known-bad URLs, not origin-bypass logic bugs.
- **Defender action:** policy hardening for managed fleets (block apps that
  enable file access + JS on untrusted origins in the enterprise app
  review); the residue is unreviewed sideloaded apps — same residue class
  as C1.

### C3 — Browser/WebView engine n-day (renderer RCE) · CVE-2016-4622, CVE-2018-17463, CVE-2019-5782, CVE-2020-6418

- **Structural control:** renderer sandboxing + site isolation limits reach;
  forced auto-update (store/OTA) is the primary defense — every listed CVE
  was closed by a routine update.
- **Telemetry:** renderer crashes (silenced by the attacker in the
  historical exploits), vendor crash statistics, and — crucially —
  **vendor-side in-the-wild detection** (CVE-2020-6418 was acknowledged as
  exploited in the wild by Google's own release notes: Chrome Releases,
  Feb 2020). Defenders' practical signal is *patch latency*, not
  per-exploitation telemetry.
- **Defender action:** enforce update policies; browser/WebView versions are
  the audit line item (enterprise consoles expose WebView/engine version).

### C4 — `intent://` and scheme-handler abuse · CVE-2014-3502, CVE-2016-4782, CVE-2017-5096, CVE-2017-17553

- **Structural control:** Chrome's `intent://` parser strips explicit
  components and non-BROWSABLE categories (documented behavior:
  developer.chrome.com/docs/android/intents); the CVEs in the inventory are
  the historical failures of exactly this policy layer, all patched.
- **Telemetry: none.** Intent launches are not user-visible and not logged
  for the user; this is the **largest blind spot** in the map — a QR-scanned
  URL that silently dispatches into a scheme handler leaves no consumer-side
  trace.
- **Defender action:** enterprise app-control (allowlist which apps may be
  installed at all — the handler app is the target, not the browser);
  `android:exported`/intent-filter audits in app review; domain-verification
  state inspection for app links (see S4).

### C5 — Page-embedded media-decoder RCE · CVE-2015-1538 (Stagefright class)

- **Structural control:** the 2015 Stagefright class is the reason the
  **Android Security Bulletin / monthly OTA cadence exists**
  (source.android.com/docs/security/bulletin; the Aug 2015 bulletin page
  carries this CVE). Post-Stagefright hardening: integer-overflow
  protections and sandboxes around mediaserver (Google Android Security
  2016 Year in Review, source.android.com).
- **Telemetry:** media crashes (mediadrm/stagefright log tags on
  engineering builds); on consumer builds, the defender-facing signal is
  again patch latency + vendor crash statistics.
- **Defender action:** patch-level enforcement (`ro.build.version.security`)
  in MDM baselines — the ASB level is a directly auditable device property.

### C6 — Install-flow / package-signature bypass · CVE-2013-4787 (Master Key), CVE-2017-13156 (Janus)

- **Structural control:** the signature-scheme fixes (v2/v3 APK signatures;
  Janus closed in the 2017-12-01 ASB,
  source.android.com/docs/security/bulletin/2017-12-01) mean current builds
  reject DEX-prepended or duplicate-entry APKs; Google's signing docs and
  the app-signing guides (e.g. OWASP MASTG test coverage that calls out
  Janus-class residue) cover the audit.
- **Telemetry:** this class is **loud** for defenders relative to the others:
  install prompts, Play Protect verdicts, install-source logging, and UEM
  app-install events all fire — but only if the operator is watching
  *sideloads* as a category.
- **Defender action:** block unknown sources via MDM user restrictions
  (developer.android.com/work); treat "update installed for app X from a
  non-store source" as an incident-grade signal.

### M0 — MDM/enrollment profile class (non-shell) · documented in taxonomy §S7

- **What defenders see:** the **loudest telemetry in the whole map** —
  iOS/Android both surface profile installation and device-admin activation
  through visible UI (Apple configuration-profile flow, Apple Platform
  Deployment guide,
  support.apple.com/guide/deployment/plan-your-configuration-profiles-dep9a318a393/web;
  Android device-admin activation screens) and, for managed fleets, UEM
  enrollment events in the admin console.
- **Parity note:** M0 is why the taxonomy documents it as a *separate,
  non-shell* class — attacker value is policy/credential influence with
  consent-level visibility, unlike the silent C-classes. A defender who can
  see enrollment/profile events is defended here even without any
  memory-corruption understanding.

## 3. Parity table (class × defender view)

| Class | Install-time control | Runtime telemetry | Residue class (what defenders must still police) |
|---|---|---|---|
| C1 | targetSdk gate + Play Protect + install blocks | **none on stock builds** (rig markers are instrumentation) | legacy-target sideloaded apps w/ bridges |
| C2 | WebView defaults hardened on update | none | unreviewed apps enabling file+JS |
| C3 | auto-update channel | renderer crashes (suppressed in real exploits) | patch latency |
| C4 | Chrome intent:// policy | **none** — silent dispatch | installed handler apps (app control) |
| C5 | monthly ASB/OTA | media crashes (mostly vendor-side) | old patch levels |
| C6 | signature-scheme fixes + install prompts + Play Protect | prompts + install-source logs | "non-store update" events |
| M0 | profile/admin activation UI | enrollment events (UEM) | users ignoring consent screens |

**Cross-links:** class definitions and surfaces — `surface-taxonomy.md`;
evidence rows — `mobile/inventory/chain-classes.csv`; rig measurement —
`mobile/rig/README.md`; staged research — `research-plan.md` (novel findings
→ policy §7 coordinated disclosure).
