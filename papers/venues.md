# P5 — Venue targets matched to outputs

Branch: `phase/p5-survey` · Deliverable: where each repo output publishes. Each mapping names the output, the venue, the submission style, and the fit rationale. **Dates marked "(historical pattern)" are approximations from recent editions; the current-year CFP page is authoritative and must be confirmed before committing to a deadline.**

## 1. Hardware/scanner matrix (P1 W1.x: `data/scanners.csv`, `data/symbology.csv`) + live demo → BSides + DEF CON villages

**Primary: DEF CON Hardware Hacking Village (HHV)** — the scanner-as-HID matrix is exactly village material: real hardware, a table demo ("scan this paper, watch the box pop a shell on the demo laptop"), and an audience that immediately understands the BadUSB lineage.

**Secondary: BSides (local/regional, e.g., BSides Cleveland/Detroit/Anywhere)** — rolling CFPs, lower barrier, good for early versions and feedback before DEF CON; BSides "Anywhere" style virtual tracks also fit a hardware-demo-lite talk.

**Submission-style notes:**
- Village talks are typically **15–45 min, slides + live demo**, announced on the village's own CFP/speaker-signup (some villages take talk sign-ups as late as weeks before, unlike main-track conferences).
- Demo-first format: lead with the printed QR + scanner on a locked-down demo laptop; the matrix data (which scanners are attackable, at what CPS, with what quirks) is the handout/QR-linked page.
- Style guidance: villages reward **working artifacts** over papers — bring the scanner fleet, the printed sheets, and a one-page results card; no proceedings/impact-factor consideration.
- Framing requirement (project posture): every talk opens with the authorization/lab-only framing and closes on defender controls (HID allowlisting, lock timeouts) — same structure as the taxonomy paper §7.
- Main-track DEF CON is **not** the target: the 45-min village format matches better than the main-conference speaker track for hardware demo content.

## 2. Detection paper (P4 W4.1–W4.4: timing dataset + detector + runbook) → USENIX Security / EuroUSEC

**Primary: USENIX Security Symposium** — the detection contribution (keystroke-cadence dataset with human|scanner labels per contract #1, detector, artifact runbook, allowlisting feasibility) is a systems-security measurement + detection paper; recent editions run **two submission cycles per year** (a fall and a spring/summer cycle — historical pattern: abstract deadlines roughly Oct–Nov and Mar–Apr; confirm the current CFP).

**Secondary: ACM EuroUSEC / USENIX Security workshops** — the dataset's human-factors side (operator behavior, timing outliers) fits the EuroUSEC usable-security workshop audience; a EuroUSEC short/workshop paper can precede the full USENIX paper without burning the contribution (check the current CFP's resubmission policy).

**Submission-style notes:**
- USENIX Security full-paper format: **13 pages excluding references/appendices**, two-column; **abstract deadline ~1 week before full-paper deadline**; the paper must be fully formed at abstract time.
- Expect **shepherding** for conditionally accepted papers and a **revision cycle** — plan the calendar accordingly.
- Submit the detector + dataset for the **artifact evaluation badge** (usable-artifact or reproduced tiers): the dataset is the paper's centerpiece, and the runbook (P4 W4.3) is essentially a pre-built artifact appendix. Budget time for the artifact badge review process.
- Double-anonymous policy varies by cycle — check the current CFP; the repo's own GitHub artifacts (contract #1 logs) may need anonymized mirrors for the submission version.
- Fit rationale to state in the paper: keystroke-injection detection is newly formalized in ATT&CK (T1674 created March 2025 [mitre2025t1674]), and there is no published scanner-cadence dataset — the paper fills that gap with defender-facing analytics (AN1567–AN1569 mapping).

## 3. Taxonomy survey (W5.1: `papers/taxonomy/`) → ACM workshop

**Primary: ACM WiSec (ACM Conference on Security and Privacy in Wireless and Mobile Networks)** — the taxonomy is about the collision of mobile-device trust (Class L/S: phones, cameras, apps) with host/HID trust (Class K): WiSec's scope sits exactly on that boundary, and a **short paper** is the right size for a taxonomy + related-work unification.

**Secondary: ACM AISec (ACM Workshop on Artificial Intelligence and Security)** — if the QR-structure-ML angle (pairing with [trad2025quishing]'s detector class) is foregrounded, AISec's short-paper track fits; note this reframes the contribution toward ML-for-security rather than pure taxonomy.

**Submission-style notes:**
- ACM workshop format: **ACM `sigconf` two-column template**, short papers typically **4–6 pages** (WiSec short) or **6–8 pages** (workshop full) — check the current CFP page for exact limits; **ACM CCS workshop-adjacent deadlines are usually ~2–3 months before the parent conference** (historical pattern for AISec; WiSec deadlines have run ~Oct–Dec for a spring conference — confirm).
- Include the **CSL (conflicts / prior-art) statement** if the workshop requires it: the survey unifies [kieseberg2010qr], [krombholz2014qrsurvey] (survey lineage), [nohl2014badusb]/[tian2015goodusb]/[hak52026ducky] (HID lineage), and [elnouby2026qrjacking] (session lineage) — the related-work section IS the contribution, so the positioning must be airtight (all entries web-verified in `sources.bib`).
- WiSec has both a **full paper and a short paper track**; the taxonomy targets the short track (4–6 pp) with the comparative tables (outline §5, §7) as the visual centerpiece.
- The workshop paper cites the full bib (`papers/taxonomy/sources.bib`, 13 verified entries) — BibTeX-ready.

## 4. Additional mappings (secondary outputs)

- **W5.2 lock-window study (`papers/lock-window/study-design.md`)** → **SOUPS** (Symposium on Usable Privacy and Security) if the primary IRB path runs (observational human-subjects measurement is squarely SOUPS/EuroUSEC material), or → **EuroUSEC/workshop** short paper if the fallback policy-survey path runs (desk-research measurement). SOUPS style: ~8–12 pages excluding refs, ACM format, pre-registration-friendly.
- **W5.3 non-Windows feasibility (`papers/nonwindows/feasibility-plan.md`)** → **village writeup / BSides talk segment** (demo-first results, pre-registered negatives included: the macOS negative is a *publishable result* and village audiences appreciate documented negatives), and as a section of the hardware-matrix handout (mapping 1).
- **Sequencing (merge-order aware):** the taxonomy (3) can go out first — it cites only published work + repo framing; the detection paper (2) waits on P4 data; the hardware talk (1) waits on P1 matrix completion; W5.2 (4) is gated on the GX.1 policy merge regardless of venue.

## Common submission-style rules (all venues)

1. **Authorization framing first**: every submission opens with the lab-only/authorized-engagement posture and presents defender controls and detection signals alongside attack descriptions (project contract; taxonomy §8).
2. **Citation discipline**: only entries from `papers/taxonomy/sources.bib` (web-verified, with verification notes) are cited for external claims; repo-internal claims cite the producing phase's data files.
3. **No undisclosed C2 endpoints** in any submitted artifact (GX.2): submission artifacts are built from the same repo content, so this is inherited automatically — state it in the submission cover notes where relevant.
