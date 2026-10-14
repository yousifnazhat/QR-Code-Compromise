# Research Governance Policy (GX.1/GX.2)

This policy governs all work in the QR-Code-Compromise project. It is binding for every phase, branch, and contributor.

## 1. Scope: lab-only

- All techniques, payloads, and tooling are exercised **exclusively on hardware and VMs owned by the project**.
- Any use on systems not owned by the operator requires **prior written authorization** (penetration-test engagement scope, or equivalent permission from the system owner).
- The only exception path for field-adjacent work is §4 (human-subjects/IRB), and it **gates** W5.2 (session-lock-window study) until satisfied.

## 2. Placeholder infrastructure rule (dual-use hygiene)

- No live/default C2 endpoints, hostnames, IPs, or URLs in any committed artifact. Placeholders only: `attacker.example` (RFC 2606) and RFC1918 example ranges, marked example-only.
- Per-target configuration lives in uncommitted files (`payloads/targets.toml`, bench `serial_port` in `qrducky.toml`) that are gitignored; only `*.example` templates are committed.
- Tools must refuse to run without explicit target configuration (e.g., `run_matrix.py` exits 2 without a targets file; `qr-ducky bench` live mode exits 3 without a rig).
- Demo payload bodies must decode to benign content (e.g., `Write-Output` demo strings); attack-capable bodies are templates with `<PLACEHOLDER>` markers.

## 3. Data handling

- Raw bench logs land under `data/raw/` (gitignored) and `lab/baseline/out/` (gitignored); regenerate via the committed tools.
- Released datasets (detection keystroke-timing data) must be: collected from consenting project members, labeled (`source: human|scanner|rig` per contract #1), de-identified (no hostnames, usernames, or content keystrokes), and documented with collection methodology.
- No PHI and no identifiable healthcare facility data, ever. The healthcare framing of the research refers to device classes and published policy, not to observed clinical environments.

## 4. Human-subjects work (W5.2 gate)

- Field observation of terminals (session-lock-window study) is human-subjects-adjacent research: it requires IRB review (or documented institutional equivalent) **before** any data collection. The checklist and consent/de-identification rules live in `papers/lock-window/study-design.md`.
- If IRB is unavailable, the study degrades to the policy-survey fallback (published screen-lock policy corpora) — this is not a blocker, it is a scope reduction.
- Observations of public terminals that proceed under an approved protocol must record no identifying information about persons or organizations.

## 5. Release checklist (GX.2)

Before any public release of tooling:
- [ ] No default infrastructure (per §2) — verified by grep for endpoint patterns
- [ ] Authorization/lab-only statement present in README and in each dual-use module's docs
- [ ] Defensive output (detection tooling, runbook, mitigation guidance) ships at parity with offensive tooling
- [ ] Test suites green from a clean environment
- [ ] This policy file is included and current

## 6. Attribution and license

- MIT license (see LICENSE). Cite this repository and the companion papers for derived research.
- Prior art integrated in this project's bibliography is credited in `papers/taxonomy/sources.bib`.
