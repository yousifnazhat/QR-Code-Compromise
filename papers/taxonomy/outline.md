# W5.1 — Taxonomy paper outline: "One Symbol, Three Attacks: Separating Camera, Keystroke, and Session Trust Failures in QR-Code Security"

Branch: `phase/p5-survey` · Deliverable: W5.1 taxonomy paper (target venue: ACM workshop short paper, see `papers/venues.md`) · Bibliography: `papers/taxonomy/sources.bib` (every key cited below is defined there and web-verified).

This is the full per-section claim outline. Every section states its claims and the citations that support them — there are no stub sections. Where a claim depends on the repo's own work, the producing phase is named.

## Thesis (explicit)

The security literature and industry reporting use "quishing" as an umbrella term for QR-code attacks. That usage conflates two fundamentally different trust-boundary failures: **(a)** camera-based *lure* attacks, where the victim's own phone feeds a URL into the browser trust model, and **(b)** *scanner-as-HID keystroke injection*, where a USB barcode scanner replays a QR code's contents as keystrokes into a host — no camera, no browser, no URL parsing, and no victim intent. This paper separates those two classes, adds the third distinct class of **(c)** *session-token hijacking*, and shows that each class implies different prerequisites, victim actions, defender controls, and detection signals. Conflating the classes produces control gaps: the controls recommended for quishing do nothing against keystroke injection, and vice versa.

## §1 Introduction

Claims:

1. Public and industry reporting treats "QR attack" as a single phenomenon — e.g., IBM's threat framing centers on QR codes as malicious *URL delivery* to phones [nadeau2024quishing] — yet the three classes in §2–§4 fail three *different* trust models (phone browser, host HID stack, service authenticator).
2. The defining property of each class is **which component consumes the code, and which trust model therefore adjudicates it**: the phone's scanner app and browser (Class L), the host's USB HID stack and whatever GUI element holds keyboard focus (Class K), the service's login flow (Class S).
3. Roadmap: §2 Class L, §3 Class K (this repository's contribution), §4 Class S, §5 comparative analysis, §6 the conflation argument against related work, §7 defender mapping, §8 scope and ethics.

## §2 Class L — QR as LURE (camera-based quishing)

**Mechanism.** An attacker prints, stickers, or embeds (email/parking meter/restaurant) a QR code that encodes a URL. The victim scans it *with their own phone camera*; a reader app decodes the URL and typically opens the browser. The defense line is the **browser trust model**: URL preview, TLS indicators, password-manager autofill, security warnings. The QR code is a delivery vehicle for a URL — the attack succeeds only if the human completes the web action (credential entry, app install, payment).

**Prerequisites.** (i) Victim carries a camera plus a reader app (native camera QR support has made this near-universal); (ii) the code is placed in the victim's attention path; (iii) reader behavior auto-navigates without preview; (iv) attacker controls a destination site. No attacker presence at any victim machine is required — this is a remote, mass-scalable class.

**Victim action required.** Two voluntary actions: *scan*, then *interact*. Empirical baselines: in Vidas et al.'s field experiments, 85% of people who scanned a planted code subsequently visited the associated URL, and curiosity was the dominant motive [vidas2013qrishing]; in Sharevski et al.'s 173-participant COVID-digital-passport pretext, 67% were willing to sign up with existing Google or Facebook credentials and convenience was the single most cited factor [sharevski2022gonequishing]. Kowalewski et al. add current susceptibility/awareness measurements and show the awareness gap persists at population scale [kowalewski2025scanned].

**Defender controls.**
- URL preview with forced confirmation before navigation (reader-side).
- Usable security indicators on the code itself and warning design — Sharevski et al. develop and test both a Quishing Awareness Scale (QAS) and warning indicators [sharevski2022gonequishing].
- Awareness training targeted at the measured lowest-scoring groups [kowalewski2025scanned].
- Email-gateway QR/URL extraction — with the documented caveat that payload extraction itself fetches content [trad2025quishing].

**Detection signals.**
- Pre-visit URL/domain reputation feeds (content-centric: the signal is *where the code leads*).
- QR-structure ML **without** payload extraction: pixel-pattern classifiers reach AUC 0.9106 (XGBoost) and 0.9133 after feature reduction on a generated phishing/benign QR dataset [trad2025quishing].
- Landing-page telemetry (phishing-kit fingerprints) once navigation occurs.

**Prior art anchors.** Vidas et al. [vidas2013qrishing]; Sharevski et al. [sharevski2022gonequishing]; Kowalewski et al. [kowalewski2025scanned]; Trad & Chehab [trad2025quishing]; trend framing by IBM [nadeau2024quishing]; the survey lineage of Kieseberg et al. [kieseberg2010qr] and Krombholz et al. [krombholz2014qrsurvey].

## §3 Class K — QR as KEYSTROKE STORE (this repository: scanner-as-HID injection)

**Mechanism.** A USB QR/barcode scanner enumerates as an **HID keyboard**. A printed or displayed QR code is therefore a *stored keystroke script*: scanning it replays the encoded string into whatever GUI element holds keyboard focus, at scanner speed (tens to hundreds of characters per second; the exact cadence envelope is measured by P1's `data/scanners.csv` matrix). The canonical chain is Win+R → payload one-liner → staged download and execution [qrcc2026repo]. Crucially, the QR code is never *interpreted* — nothing parses a URL, no camera sees the code, no browser is involved. The code is transparent text, and the trust failure is the host's unconditional trust of HID devices.

**Prerequisites.** (i) Physical reach of an attacker or accomplice to a workstation where a scanner is attached — precisely the *locked-in-cabinet / mobile cart* setting where USB drives are blocked or impractical but the scanner is a trusted, already-enumerated input device [qrcc2026repo]; (ii) a scanner that presents as a HID keyboard (the BadUSB lineage established that USB devices can masquerade as keyboards [nohl2014badusb]; commodity QR scanners do it legitimately, which is what makes them unremarkable to operators); (iii) an execution entry point reachable purely by keystrokes — Run dialog, terminal, or a kiosk scan field (see W5.3 `papers/nonwindows/feasibility-plan.md` for the per-OS entry-point map).

**Victim action required.** **None.** The attacker presses Win+R and scans; the compromise completes in under three seconds and the paper evidence is shreddable on the way out [qrcc2026repo]. This zero-victim-action property is the decisive separation from Class L (two voluntary actions) and Class S (one voluntary action by a deceived phone owner).

**Defender controls.**
- HID device allowlisting / USB mediation enforcing permissions by device descriptor — the GoodUSB architecture for the Linux USB stack [tian2015goodusb].
- Lock screens with automatic timeouts: the W5.2 lock-window study (`papers/lock-window/study-design.md`) exists because this control is the cheapest Class-K mitigation and its *real-world prevalence* is unmeasured [qrcc2026repo].
- Application control / runner removal: PowerShell Constrained Language Mode and denying script runners (M1038), and limiting hardware installation (M1034) [mitre2025t1674].
- Kiosk hardening: no auto-execute scan fields (W5.3).

**Detection signals.** Aligned with ATT&CK Input Injection T1674, Detection Strategy DET0568, analytics AN1567–AN1569 [mitre2025t1674]:
- Rogue HID enumeration + rapid keystroke bursts with no interactive user in front of the machine (AN1567).
- Linux: `/sys/bus/usb/devices/` enumeration followed by script launch (bash/python) with no interactive user activity (AN1568).
- macOS: I/O-Registry HID enumeration (`ioreg -p IOUSB`) correlated with rapid script execution targeting osascript/PowerShell equivalents (AN1569).
- Cadence: keystroke-timing classification of human vs. scanner input — the repo's P4 dataset is built from the contract-#1 keystroke event log (`source: human|scanner`, per-session labels), giving these analytics exactly the labeled timing data they require. Rubber Ducky-style tools established that injection cadence is machine-like and distinguishable from typing [hak52026ducky]; our contribution is the scanner-specific timing envelope from real hardware.

**Prior art anchors.** BadUSB [nohl2014badusb]; GoodUSB [tian2015goodusb]; USB Rubber Ducky and DuckyScript [hak52026ducky]; ATT&CK T1674/DET0568 [mitre2025t1674]; this repository [qrcc2026repo].

## §4 Class S — QR as SESSION TOKEN (QRLJacking)

**Mechanism.** In "Login with QR code" flows, the displayed QR code *is an authentication bearer token*: scanning it with the service's own mobile app approves the session that is currently displayed on the requesting machine. The attacker initiates a client-side QR session, clones the rotating code into a phishing page (a refresh script keeps it valid), and sends the page to the victim; when the victim scans with the *targeted service's app*, the victim authenticates the attacker's session [elnouby2026qrjacking]. The QR code here is neither lure-URL nor keystroke text — it is a **credential**.

**Prerequisites.** (i) The service exposes QR login (WhatsApp Web, WeChat, Alibaba/AliPay, Yandex services and others were reported vulnerable at disclosure [elnouby2026qrjacking]); (ii) the attacker runs a code-refresh/relay script — the OWASP writeup notes some services lacked code expiry, removing even that obstacle; (iii) the victim has the targeted mobile app installed.

**Victim action required.** One scan — but with the service's authenticator app, not a generic reader. The phone's owner *approves* the attacker's desktop session without knowing it.

**Defender controls** (from the OWASP recommendations [elnouby2026qrjacking]): session-confirmation prompts showing device/network characteristics of the session being approved; IP/geolocation binding between code request and confirmation device; short code expiry; login notifications; and limiting QR login to contexts where it is genuinely needed.

**Detection signals.** Session-geometry-centric: confirmation device and code-request origin differ in network or geography; impossible-travel patterns; new-device fingerprints at login; QR-session relay timing (code issued in one browser, confirmed from a phone in a different network moments later).

**Prior art anchors.** The OWASP QRLJacking project [elnouby2026qrjacking].

## §5 Comparative analysis

Comparison table (one row per class; columns: consuming component · trust model abused · attacker network presence at scan time · victim action required · payload medium · primary detection surface):

| Class | Consuming component | Trust model abused | Victim action | Payload medium | Primary detection surface |
|---|---|---|---|---|---|
| L — LURE | Phone scanner app → browser | Browser URL/security indicators | Scan + interact (2 voluntary) | Web page | Content: URL/landing-page, QR-pixel ML |
| K — KEYSTROKE STORE | Host USB HID stack → focused GUI element | Host trusts HID unconditionally | **None** | Keystroke text (one-liner → staged download) | Cadence + ancestry: enumeration, timing, process parentage |
| S — SESSION TOKEN | Service login flow | "Scan = approve device" | Scan with service app (1) | Session grant | Session geometry: origin mismatch, impossible travel |

Claims:

1. Class K is the only class with **zero victim action** — the human is bypassed, not deceived. Classes L and S both require a deceived phone owner; every awareness-based defense works on L (and S, partially), and *none* work on K.
2. Detection surfaces are disjoint: L is content-centric (URL), K is cadence/ancestry-centric (enumeration + timing + process lineage), S is session-geometry-centric. A SOC staffed for quishing has no sensor for Class K and vice versa.
3. Controls map differently (the §7 table): preview/indicators (L) do nothing for K; HID allowlisting and lock timeouts (K) do nothing for L; session-confirmation UX (S) addresses neither L nor K.

## §6 Related work and the conflation argument

Claims:

1. The survey era predates "quishing" and treated the QR code as *data to be decoded*: Kieseberg et al. examined QR structure and reader-side attacks [kieseberg2010qr], and Krombholz et al. systematized use cases, attack scenarios, and usable-security challenges [krombholz2014qrsurvey] — both closest to a Class-L framing, years before the term existed.
2. The HID/USB literature developed in parallel and never connected to QR symbology: BadUSB showed USB firmware masquerading as keyboards [nohl2014badusb]; GoodUSB built descriptor-based mediation defenses [tian2015goodusb]; the USB Rubber Ducky commoditized keystroke injection [hak52026ducky]. Class K is exactly this engine, with a commodity *barcode scanner* substituting for the ducky — the repo's own framing: "The QR and a scanner can be equivalent to that of a rubber ducky, with its rapid keystrokes and its relative concealment" [qrcc2026repo].
3. Current empirical and detection work stays inside Class L: user-susceptibility studies [kowalewski2025scanned] and QR-structure ML detection [trad2025quishing] both assume the phone-camera/browser path.
4. MITRE only formalized Input Injection as T1674 in March 2025 [mitre2025t1674]; enterprise detection guidance for keystroke injection is recent and thin, leaving Class K under-mapped relative to its practical feasibility in scanner-equipped environments (healthcare carts, POS, logistics) [qrcc2026repo].
5. **Thesis restated.** The taxonomy is the bridge across these disjoint literatures: one symbol, three trust failures. Neither side cites the other; the classes are separable and must be separated because their controls and detections do not transfer.

## §7 Defender mapping (controls × signals per class)

Table: per class, the top three controls and the observable signal each produces, cross-referenced to the repo deliverables that operationalize them:

| Class | Control | Signal produced | Repo deliverable |
|---|---|---|---|
| L | Reader URL preview + confirm | Navigation telemetry, blocked-URL events | — (out of repo scope; cite [sharevski2022gonequishing]) |
| L | QR-structure ML screening | Classifier score on decoded pixels | [trad2025quishing] baseline |
| K | HID allowlisting / GoodUSB mediation | Blocked rogue-descriptor enumeration events | [tian2015goodusb] architecture |
| K | Lock screen + auto-timeout | Idle→lock state transitions (the attacked window) | **W5.2 lock-window study** (`papers/lock-window/study-design.md`) |
| K | Keystroke-cadence detection | human-vs-scanner timing classification | **P4 detector + dataset** (contract #1 labels) |
| K | Runner removal / CLM | Script-block events | P3 W3.4 AMSI/CLM matrix |
| S | Session confirmation UX | Denied anomalous approvals | [elnouby2026qrjacking] recommendations |
| S | Origin/geo binding | Impossible-travel login alerts | — |

## §8 Scope, ethics, limitations

1. **Authorization posture.** Lab-only, per the fleet charter: owned VMs/hardware, written authorization for anything field-adjacent, GX.1 governance gate before any W5.2 field work. Every attack class is presented here *with its defender controls and detection signals in the same section* — the taxonomy is a defensive artifact as much as an attack description.
2. **Limitations.** The taxonomy covers attacks where the QR code's *role in the trust architecture* is the distinguishing property. Payload-data roles (Wi-Fi join strings, vCard/contact injection, calendar invites) are data-injection into apps, not OS execution, and are noted as out of scope; they inherit class boundaries from the consuming app rather than defining new classes.
3. **Threats to validity of the class boundaries.** Composite attacks exist (a Class-L lure page that then requests a Class-S QR login); the paper classifies by the *terminal trust failure*, and composites are chains across classes, not counterexamples.
4. Hardware-gated items (physical scanner quirks) log expected-but-blocked status in the owning phase directories per merge rule 5, so the taxonomy's Class-K claims carry a per-scanner feasibility pointer to P1's `data/scanners.csv` matrix.

## Citation keys used (all in `papers/taxonomy/sources.bib`)

`kieseberg2010qr`, `vidas2013qrishing`, `krombholz2014qrsurvey`, `tian2015goodusb`, `nohl2014badusb`, `hak52026ducky`, `mitre2025t1674`, `sharevski2022gonequishing`, `kowalewski2025scanned`, `trad2025quishing`, `elnouby2026qrjacking`, `nadeau2024quishing`, `qrcc2026repo`.
