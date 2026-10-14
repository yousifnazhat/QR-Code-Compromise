# P6 Known Chain-Class Inventory — historical, already-patched (W6.2)

> **AUTHORIZATION — LAB ONLY.** Patch-history archaeology for the
> QR-Code-Compromise project (authorized security research). Every
> entry below is a **public, vendor-patched** historical vulnerability,
> mined from NVD (services.nvd.nist.gov) and the Android Security
> Bulletins (source.android.com) on 2026-10-14. Regenerate:
> `python3 mobile/inventory/build_inventory.py`. This inventory
> contains no novel-vulnerability research; any *new* finding goes
> through coordinated disclosure per `docs/governance/policy.md` §7.

Generated: 2026-10-14 · Source APIs: NVD CVE API 2.0 · Android Security Bulletin pages · Rows: 22 · Classes: C1, C2, C3, C4, C5, C6, C7

## C1 — JS-bridge RCE (addJavascriptInterface family)

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2012-6636](https://nvd.nist.gov/vuln/detail/CVE-2012-6636) | Android API < 17 (apps with targetSdk < 17 stay exposed on later OS builds) | Android 4.2 (API 17): only @JavascriptInterface methods exposed to apps targeting 17+ | [Metasploit: Android Browser and WebView addJavascriptInterface Code Execution](https://www.rapid7.com/db/modules/exploit/android/browser/webview_addjavascriptinterface) | U->E: URL->WebView page JS->bridge object->Java Reflection->Runtime.exec (shell) |
| [CVE-2014-1939](https://nvd.nist.gov/vuln/detail/CVE-2014-1939) | Android before 4.4 (SearchBox object exposed via BrowserFrame.java) | Android 4.4 (KTU84P) | [NVD record (references in nvd_refs column)](https://nvd.nist.gov/vuln/detail/CVE-2014-1939) | U->E: URL->WebView->exposed SearchBox bridge object->code execution |
| [CVE-2014-7224](https://nvd.nist.gov/vuln/detail/CVE-2014-7224) | Android prior to 4.4.0 (accessibility / accessibilityTraversal objects) | Android 4.4 (KTU84P) | [NVD record (references in nvd_refs column)](https://nvd.nist.gov/vuln/detail/CVE-2014-7224) | U->E: URL->WebView->accessibility bridge objects->code execution |

## C2 — WebView same-origin / file-scheme bypass

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2014-6041](https://nvd.nist.gov/vuln/detail/CVE-2014-6041) | Android WebView before 4.4 | Android 4.4 (KTU84P) | [NVD reference: https://community.rapid7.com/community/metasploit/blog/2014/09/15/major-android-bug-is-a-privacy-disaster-cve-2014-6041](https://community.rapid7.com/community/metasploit/blog/2014/09/15/major-android-bug-is-a-privacy-disaster-cve-2014-6041) | U->E: URL->WebView->NUL-char SOP bypass->local-file theft (pivot stage) |

## C3 — Browser/WebView engine n-day (renderer RCE)

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2016-4622](https://nvd.nist.gov/vuln/detail/CVE-2016-4622) | Apple iOS before 9.3.3; Safari before 9.1.2; tvOS before 9.2.2 | Apple iOS 9.3.3 (HT206900) | [ZDI-16-485: Apple Safari Array.slice OOB access](https://www.zerodayinitiative.com/advisories/ZDI-16-485/) | U->E: URL->Safari renderer->memory corruption->RCE (shell) |
| [CVE-2018-17463](https://nvd.nist.gov/vuln/detail/CVE-2018-17463) | Google Chrome before 70.0.3538.64 (V8) | Chrome 70.0.3538.64 stable (2018-10) | [Chrome Releases: Stable Channel Update for Desktop (Oct 2018)](https://chromereleases.googleblog.com/2018/10/stable-channel-update-for-desktop.html) | U->E: URL->Chrome renderer->V8 type confusion->RCE (shell) |
| [CVE-2019-5782](https://nvd.nist.gov/vuln/detail/CVE-2019-5782) | Google Chrome before 72.0.3626.81 (V8) | Chrome 72.0.3626.81 stable (2019-01) | [NVD reference: https://chromereleases.googleblog.com/2019/01/stable-channel-update-for-desktop.html](https://chromereleases.googleblog.com/2019/01/stable-channel-update-for-desktop.html) | U->E: URL->Chrome renderer->V8 optimization bug->RCE (shell) |
| [CVE-2020-6418](https://nvd.nist.gov/vuln/detail/CVE-2020-6418) | Google Chrome before 80.0.3987.122 (V8; exploited in the wild) | Chrome 80.0.3987.122 stable (2020-02) | [Chrome Releases: Stable Channel Update for Desktop (Feb 2020, in-the-wild ack)](https://chromereleases.googleblog.com/2020/02/stable-channel-update-for-desktop_24.html) | U->E: URL->Chrome renderer->V8 type confusion->RCE (shell) |
| [CVE-2012-3748](https://nvd.nist.gov/vuln/detail/CVE-2012-3748) | Apple iOS before 6.0.1; Safari before 6.0.2 (WebKit race condition) | iOS 6.0.1 / Safari 6.0.2 (Apple advisory) | [NVD reference: http://support.apple.com/kb/HT5567](http://support.apple.com/kb/HT5567) | U->E: URL->Safari/WebKit->JavaScript-array race->arbitrary code execution |
| [CVE-2018-4233](https://nvd.nist.gov/vuln/detail/CVE-2018-4233) | Apple iOS before 11.4; Safari before 11.1.2; iTunes/iCloud for Windows (WebKit) | iOS 11.4 / Safari 11.1.2 (Apple advisory HT208848) | [NVD reference: https://support.apple.com/HT208848](https://support.apple.com/HT208848) | U->E: URL->Safari/WebKit->memory corruption->code execution |
| [CVE-2021-1879](https://nvd.nist.gov/vuln/detail/CVE-2021-1879) | Apple iOS before 12.5.2/14.4.2; watchOS before 7.3.3 (WebKit; Apple acknowledged in-the-wild exploitation) | iOS 12.5.2 / 14.4.2, watchOS 7.3.3 (out-of-band Apple update, 2021-03) | [NVD reference: https://support.apple.com/en-us/HT212256](https://support.apple.com/en-us/HT212256) | U->E: URL->Safari/WebKit->universal cross-site scripting->same-origin break (session hijack / payload pivot) |

## C4 — intent:// and custom-scheme handler abuse

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2014-3502](https://nvd.nist.gov/vuln/detail/CVE-2014-3502) | Apache Cordova Android before 3.5.1 (and apps built on it) | Apache Cordova Android 3.5.1 (vendor advisory, 2014-08) | [NVD reference: http://cordova.apache.org/announcements/2014/08/04/android-351.html](http://cordova.apache.org/announcements/2014/08/04/android-351.html) | U->E: URL with crafted URI scheme->Cordova WebView bridge->launch arbitrary apps |
| [CVE-2016-4782](https://nvd.nist.gov/vuln/detail/CVE-2016-4782) | Lenovo SHAREit before 3.5.98_ww on Android < 4.2 | SHAREit 3.5.98_ww (Lenovo advisory, 2016) | [NVD record (references in nvd_refs column)](https://nvd.nist.gov/vuln/detail/CVE-2016-4782) | U->E: crafted intent: URL->scheme handler->unspecified impact in handler app |
| [CVE-2017-5096](https://nvd.nist.gov/vuln/detail/CVE-2017-5096) | Google Chrome before 60.0.3112.78 for Android | Chrome 60.0.3112.78 stable (2017-07) | [NVD reference: https://chromereleases.googleblog.com/2017/07/stable-channel-update-for-desktop.html](https://chromereleases.googleblog.com/2017/07/stable-channel-update-for-desktop.html) | U->E: page navigation between schemes->insufficient policy enforcement->policy bypass |
| [CVE-2017-17553](https://nvd.nist.gov/vuln/detail/CVE-2017-17553) | Dolphin Browser for Android 12.0.2 | Dolphin Browser update (2018) | [NVD reference: https://github.com/VerSprite/research/blob/master/advisories/VS-2017-002.md](https://github.com/VerSprite/research/blob/master/advisories/VS-2017-002.md) | U->E: URL->insecure Intent URI parsing->native component launch |

## C5 — Page-embedded media-decoder RCE

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2015-1538](https://nvd.nist.gov/vuln/detail/CVE-2015-1538) | Android before 5.1.1 LMY48I (libstagefright) | Nexus Security Bulletin 2015-08-01 (LMY48I) · also in ASB-2015-08 | [jduck/cve-2015-1538-1: public stsc MP4 atom exploit](https://github.com/jduck/cve-2015-1538-1) | U->E: URL->page embeds crafted MP4->libstagefright integer overflow->RCE (shell) |
| [CVE-2010-1797](https://nvd.nist.gov/vuln/detail/CVE-2010-1797) | FreeType before 2.4.2, as used in Apple iOS before 4.0.2 (MobileSafari) | iOS 4.0.2 (FreeType 2.4.2); publicized via the jailbreakme.com page-JS exploit | [NVD reference: http://support.apple.com/kb/HT4291](http://support.apple.com/kb/HT4291) | U->E: URL->MobileSafari renders crafted PDF/font (CFF Type2 CharStrings)->stack overflow->RCE (shell) |

## C6 — Install-flow / package-signature bypass

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2013-4787](https://nvd.nist.gov/vuln/detail/CVE-2013-4787) | Android 1.6 Donut through 4.2 Jelly Bean (APK signature verification) | Android 4.3+ (Google bug 8219321; Bluebox disclosure 2013-07) | [ZDNET: Google releases fix to OEMs for Bluebox 'Master Key' Android security hole](http://www.zdnet.com/google-releases-fix-to-oems-for-blue-security-android-security-hole-7000017782/) | U->download/consent: URL->trojaned APK accepted as same-signature update->install->code on device |
| [CVE-2017-13156](https://nvd.nist.gov/vuln/detail/CVE-2017-13156) | Android 5.1.1 through 8.0 (ART / v1 APK signature scheme) | Android Security Bulletin 2017-12-01 (A-64211847) · also in ASB-2017-12 | [Guardsquare: Janus vulnerability (CVE-2017-13156) analysis](https://www.guardsquare.com/blog/new-android-vulnerability-allows-attackers-to-modify-apps-without-affecting-their-signatures-guardsquare) | U->download/consent: URL->DEX-prepended APK passes v1 signature->install as update->code on device |

## C7 — Hybrid-framework app-bridge input-validation flaws (app-authored bridges)

Taxonomy surface: `mobile/docs/surface-taxonomy.md` · Defender mirror: `mobile/docs/defender-parity.md`

| CVE | Affected | Patch reference | Public writeup | Chain stage |
|---|---|---|---|---|
| [CVE-2012-6637](https://nvd.nist.gov/vuln/detail/CVE-2012-6637) | Apache Cordova 3.3.0 and earlier; Adobe PhoneGap 2.9.0 and earlier (all platforms incl. iOS) | Cordova 3.4.0 / PhoneGap 2.9.1 (anchored domain-whitelist regex) | [NVD record (references in nvd_refs column)](https://nvd.nist.gov/vuln/detail/CVE-2012-6637) | U->E: URL->hybrid-app bridge->non-anchored whitelist regex bypass->bridge API reachable from attacker origin |
| [CVE-2015-5207](https://nvd.nist.gov/vuln/detail/CVE-2015-5207) | Apache Cordova iOS before 4.0.0 | Cordova iOS 4.0.0 (vendor advisory, 2015) | [NVD reference: http://jvn.jp/en/jp/JVN35341085/index.html](http://jvn.jp/en/jp/JVN35341085/index.html) | U->E: URL->WKWebView hybrid app->URL-whitelist bypass->arbitrary resource load (bridge pivot) |
| [CVE-2015-5208](https://nvd.nist.gov/vuln/detail/CVE-2015-5208) | Apache Cordova iOS before 4.0.0 | Cordova iOS 4.0.0 (vendor advisory, 2015) | [NVD reference: http://jvn.jp/en/jp/JVN41772178/index.html](http://jvn.jp/en/jp/JVN41772178/index.html) | U->E: crafted link->Cordova iOS bridge->arbitrary plugin execution (app-process code) |

## Appendix A — NVD keyword mining (candidate corpus)

Keyword queries are run against the live NVD API to show the
candidate corpus for each class family. Inventory membership is
curated (verified class + public writeup); these are candidates only.

- `keywordSearch=addJavascriptInterface` — totalResults: 2; sampled ids: CVE-2014-1939, CVE-2014-7224
- `keywordSearch=intent scheme` — totalResults: 21; sampled ids: CVE-2014-3502, CVE-2016-4782, CVE-2017-5096, CVE-2017-17553, CVE-2018-17472, CVE-2020-8954, CVE-2021-29370, CVE-2023-36612, CVE-2023-39507, CVE-2024-41918, CVE-2024-55642, CVE-2025-57452, CVE-2025-12080, CVE-2026-31804, CVE-2026-35394, CVE-2026-44245, CVE-2026-69078, CVE-2026-73335, CVE-2026-102675, CVE-2026-92862

## Appendix B — Android Security Bulletin mining

- [ASB-2015-08](https://source.android.com/docs/security/bulletin/2015-08-01): 21 CVE ids on the page; inventory matches: CVE-2015-1538
- [ASB-2017-12](https://source.android.com/docs/security/bulletin/2017-12-01): 47 CVE ids on the page; inventory matches: CVE-2017-13156

## Method / reproducibility

- One NVD API 2.0 call per CVE (`cveId=` lookup), 6 s spacing, no API
  key (anonymous rate limit). Descriptions and reference URLs are the
  live NVD values at generation time.
- Bulletin pages fetched as HTML and mined with a CVE-id regex.
- All rows are **historical and already patched**; `patch_ref` names the
  vendor fix that closed each bug. This is the Stage-1 evidence base
  for the Stage-2 rig reproductions (`mobile/rig/README.md`).
