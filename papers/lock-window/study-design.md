# W5.2 — Session-lock window study design

Branch: `phase/p5-survey` · Deliverable: study design for the session-lock window measurement · Feeds the taxonomy paper's Class-K defender-controls section (`papers/taxonomy/outline.md` §3, §7): the lock screen with automatic timeout is the cheapest Class-K mitigation, and its *real-world deployment* is the unmeasured quantity.

**Governance status (read first):** this document designs, but does **not authorize**, any field work. The fleet charter's governance gate **GX.1** requires `docs/governance/policy.md` to land on `master` before any W5.2 field work; until the coordinator merges that gate, the fallback path (§4) is the only executable track. No observation of any real facility may begin on the strength of this file alone.

## 1. Research questions

- **RQ1 (prevalence):** In shared and public computing environments, what fraction of observed workstation sessions are left *unattended while unlocked* ("unattended-unlocked prevalence")?
- **RQ2 (policy timeout):** What screen-lock timeout do organizations actually deploy, and how does deployed policy differ from published policy ("lock-timeout distribution", observed vs. stated)?
- **RQ3 (exposure window):** Given RQ1 and RQ2, what is the expected *window* during which a Class-K keystroke-injection attack (taxonomy §3) finds an unlocked, unattended machine — and how does that window compare with the sub-three-second execution time of the repo's Win+R chain?

RQ3 is the payoff: it converts the taxonomy's "lock screens + automatic timeouts" control from advice into a measured quantity.

## 2. Primary path — observation of public terminals (human-subjects)

### 2.1 Why this is human-subjects research

Even though the study never interacts with, interviews, or identifies any person, it is systematic observation of *identifiable living individuals' behavior* (whether an operator remains within reach of a terminal, for how long, at what times). Under the Common Rule (45 CFR §46.102(e)), data about behavior that investigators can readily ascertain, collected in a context where subjects reasonably expect privacy (a semi-private workplace such as a hospital medication room or a staffed library desk), constitutes human-subjects research. The expected determination path is **exempt or expedited review**: observation of public behavior where investigators do not interact and do not record identifying information is a candidate for exemption under 45 CFR §46.104(d)(2) — but that determination belongs to the IRB, not to this project, so the protocol is submitted for determination rather than self-classified. Venues: public library terminals, airport gate-area internet kiosks, hospital registration desks (site-owner permitting), campus computer labs.

### 2.2 Consent approach

- **Passive notice, no interaction.** Observers do not approach subjects. A "study in progress" placard with contact information is posted where required by the venue or IRB.
- **Waiver of documentation of consent requested** under §46.117(c): the research is minimal risk, involves no interaction, and signing consent forms would be the only identifying record collected — the waiver *reduces* identifiability risk.
- **De-identification at capture.** The observation record contains no names, no faces, no screen content, no user IDs. Recorded fields only: venue class (library/airport/hospital/lab), station ID within venue, timestamp, terminal state (locked/unlocked/unknown), operator present (yes/no, "within arm's reach" operationalized as ≤ 1 m), and whether input activity occurred. Coders are trained to record *states*, never *persons*.
- **No photography of screens or people.** If any image is needed for venue layout, it is taken before observation hours with venue permission and contains no subjects.
- **Aggregation before publication:** venue categories are reported only with ≥ 5 observations per reported cell; raw timing rows are never published with venue identity attached.

### 2.3 Explicit IRB checklist (protocol submission package)

Every item is a required attachment before submission; the study does not start while any box is unchecked:

- [ ] 1. Protocol summary (this document §1–§5, RQs, design, metrics, analysis plan).
- [ ] 2. IRB application form, submitted through the sponsoring institution's system (determination requested: exempt under §46.104(d)(2) *or* expedited; IRB decides).
- [ ] 3. Justification for waiver of documentation of consent (§46.117(c)) and for waiver of consent itself where applicable (§46.116) — no-interaction, minimal-risk argument.
- [ ] 4. Site authorization letters from each venue owner/operator (library administration, airport operator, hospital research administration) — *written permission precedes any hospital-adjacent observation*.
- [ ] 5. **GX.1 gate confirmation:** `docs/governance/policy.md` merged on `master` (coordinator's confirmation, not assumption).
- [ ] 6. Data management plan (DMP): fields captured (§2.2), retention (raw notes destroyed after digitization; aggregate data retained ≤ 3 years), storage (encrypted project volume, access limited to named study staff).
- [ ] 7. De-identification SOP (the §2.2 rules, written as an observer-training procedure with a signed attestation per observer).
- [ ] 8. Observer training records (CITI Human Subjects Research certification or institutional equivalent, plus a 1-hour coding-calibration session).
- [ ] 9. Risks and mitigations table (§5) in IRB-facing language.
- [ ] 10. Adverse-event / complaint reporting path (venue contact + IRB contact + PI), printed on the observer materials.
- [ ] 11. Conflict-of-interest statement (none: no venue is an employer or client of any study staff).
- [ ] 12. Pre-registration of RQs/metrics/analysis plan (OSF or equivalent) to prevent post-hoc metric switching.

### 2.4 Design and metrics

- **Sampling.** Scan-walk observation at randomized intervals per venue (stratified by hour-of-day and weekday/weekend); target ≥ 6 observation hours per venue class, ≥ 4 venue classes, powered for RQ1.
- **Power.** To estimate unattended-unlocked prevalence with ±5% absolute margin at 95% confidence (worst case p = 0.5) requires **n ≈ 385 observed active sessions**; the plan targets **n = 500+** to allow per-class breakdowns.
- **Metrics.**
  - *Unattended-unlocked prevalence* (primary): # sessions where the terminal is unlocked AND no operator within arm's reach, ÷ # observed active sessions; per environment class, with Wilson 95% CIs.
  - *Lock-timeout observed*: elapsed idle-time from last observed input to automatic lock, where observable; reported as distribution (median/IQR) per OS/venue class.
  - *Time-to-attendance-return*: for unattended-unlocked sessions, how long the operator stays away; right-censored at observation-window end (Kaplan–Meier reporting).
  - *Kiosk-mode share*: fraction of observed terminals presenting a restricted shell vs. full desktop — a direct W5.3 input.
- **Reliability.** Two independent coders for 10% of venue-hours; inter-rater reliability on the attended/unlocked coding must reach **Cohen's κ ≥ 0.8** before solo coding proceeds.
- **Analysis plan (pre-registered).** Prevalence CIs (Wilson); timeout distribution (median/IQR + per-policy comparisons); RQ3 exposure window = prevalence × mean unattended duration, compared against the repo's measured attack execution time (P4 timing dataset) as a ratio.

## 3. Risks (primary path)

| Risk | Severity | Mitigation |
|---|---|---|
| Observer misidentifies person or records identifying detail | High (privacy) | State-only capture fields; no photography; §2.2 SOP; immediate discarding of any note that names a person |
| Bystander/superior challenges observer (assumed to be surveillance) | Medium | Site placard + venue authorization letter carried by observer; immediate stand-down and IRB contact if challenged |
| Venue rescinds permission mid-study | Medium | Multiple venues pre-arranged; analysis plan tolerates unequal venue contribution (prevalence is per-class) |
| Timestamps + venue could re-identify a staff member's routine | Medium | Aggregate-only publication (§2.2 k ≥ 5); hour-of-day reported in 4-hour bins, not exact times |
| IRB determines the study is *not* exempt (e.g., venue reclassifies context as private) | Process | Accept determination; either revise to fully consented interaction study or fall back to §4 |
| Data loss / theft of observation notes | Medium | Paper notes digitized within 24 h, then shredded; encrypted storage in DMP |

## 4. Fallback path — screen-lock policy survey (no human subjects)

If the IRB determination is unfavorable, the GX.1 gate is not merged, or venue authorizations cannot be obtained, W5.2 still produces a publishable measurement from **public documents only** (desk research; no IRB requirement; may proceed independently of GX.1):

- **Corpus.** Published screen-lock policies of universities, hospital systems, and government agencies (freely published policy PDFs); security benchmarks — NIST SP 800-53 control **AC-11** (session lock) and its parameters, CIS Benchmarks per-OS lock values (Windows `Interactive logon: Machine inactivity limit`, GNOME `lock-delay`/`idle-delay`, macOS screensaver lock), and enterprise device-management baselines (e.g., Windows GPO defaults, Jamf/Intune guidance).
- **Metrics.** *Stated lock-timeout distribution*: minutes across corpus, median/IQR, and the share of environments with **no stated policy at all** (a policy-absence rate). Secondary: stated prevalence of kiosk/limited-functionality modes; explicit vs. default-only enforcement language.
- **Sampling rule (pre-registered).** Top-N by published size for each organization class, collected over a fixed 2-week window; extraction done by two coders with the same κ ≥ 0.8 gate.
- **Honest limitation (stated in the paper):** the fallback measures *stated* policy, not deployed behavior — the gap between stated and deployed timeouts is exactly what the primary path exists to close, and the paper says so rather than implying equivalence.

## 5. Reporting

Results feed `papers/taxonomy/outline.md` §3/§7 as the Class-K control quantification, and the detection paper's motivation (P4: the attacked window is the detector's reaction budget). Both paths report: metric definition, sampling frame, CIs/distributions, and the full risk table. The paper version includes the IRB determination text and venue-class list (de-identified per §2.2).
