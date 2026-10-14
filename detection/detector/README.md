# W4.2 — Timing-injection detector baseline

**AUTHORIZATION / POSTURE**: lab-only, defensive security research on
keystroke-injection detection, performed on the owned lab VMs and rig
described in `lab/` (P0). This module contains no offensive
functionality: it reads contract-#1 JSONL capture logs and flags
machine-generated keystroke sessions.

## What this is

A deliberately minimal, interpretable baseline for detecting
QR-scanner-as-HID keystroke injection from **timing alone**:

1. `features.py` — per-session inter-arrival statistics
   (mean/std/min/median/kurtosis/CV), burst metrics (fraction of
   inter-arrivals under 15 ms, burst regularity = 1 − CV of the burst
   sub-distribution, longest burst run), session-level aggregation.
   Features are **content-free**: no key identities, no payloads.
2. `baseline.py` — a single-feature threshold detector (session
   flagged injected iff `ia_mean < threshold`) whose threshold is
   chosen on a train split by accuracy; plus a stratified
   session-level train/test split and a precision / recall / FPR /
   FNR / F1 evaluation harness.
3. `pipeline.py` — end-to-end CLI:
   `python3 -m detection.detector.pipeline capture.jsonl`.

## Why a threshold baseline

The synthetic generator (W4.1) puts wedge bursts at 1–10 ms
inter-arrivals with near-zero variance against human medians around
90 ms — a >10× separation. A threshold detector makes the signal
explicit, is trivially auditable, and sets the floor that any more
complex model must beat to justify itself. On the committed synthetic
sample it reaches recall 1.0 / FPR 0.0 (see
`synthetic_baseline_eval.txt`), with a >60 ms decision margin.

## Related work and how this differs

**QUACK — “Making the (Rubber) Ducky Talk: A Systematic Study of
Keystroke Dynamics for HID Injection Detection” (Lotto, Marchiori,
Conti — arXiv:2604.15845)**. QUACK systematically studies
timing-only, user-agnostic, content-free HID-injection detection using
hold and flight times with lightweight classifiers, and shows (a)
speed/regularity heuristics are evaded by slower or randomized
attackers, (b) detection depends on exposure to structurally distinct
generator strategies rather than model complexity, and (c) physical
HID validation remains necessary. Our baseline is exactly the
“lightweight, timing-only” direction QUACK endorses, but sits at the
simplest end: one threshold on flight-time mean. QUACK’s
evadability finding is the key limitation we inherit and is the
stated motivation for keeping the detector a baseline rather than a
claim. Two structural differences: contract #1 captures keydown (and
optionally keyup) events, so hold time features are only available
when P0’s hook emits keyup (our extractor uses keydown flights only);
and QUACK evaluates cross-generator transfer on adversarially
randomized timing — our generator produces unhardened bursts, so our
numbers are a *floor*, not an evasion-resistance result.

**Karantzas — “Forensic Log Based Detection For Keystroke Injection
‘BadUsb’ Attacks” (arXiv:2302.04541)**. This is the *host-artifact*
track: post-hoc detection through Windows forensic logs (Sysmon EID 1
process lineage, PowerShell script-block logging, etc.). It is
complementary, not competing: it answers “what did the injection
leave behind?” while timing detection answers “is this input stream
human?”. Our operationalization of that track is W4.3 —
`detection/runbook.md` maps each P3 payload (contract #4) to its
expected artifacts (RunMRU, Sysmon EID 1 lineage, PowerShell EID
4104, AMSI EID 1116, Prefetch, ShimCache) with collection commands.
A defensible posture uses both: timing detection to catch the input,
forensic logging to scope what ran.

## Deliberately out of scope

- **Deep learning / heavyweight ML.** The charter for W4.2 is a
  baseline; QUACK’s result that model complexity does not drive
  detection quality supports keeping this threshold-simple until real
  capture data (P0/P1 hardware runs) demands more.
- **Behavioral authentication** (per-user profiles/enrollment) — the
  research goal is user-agnostic detection.
- **Key-content analysis.** Content-free by design (privacy +
  QUACK’s observation that retaining key identities exposes
  sensitive content).
- **Evasion-hardened attackers** (slow/randomized injection). The
  synthetic generator is unhardened; adversarial-timing robustness is
  future work once real scanner captures exist.
- **Real-data claims.** All metrics in `synthetic_baseline_eval.txt`
  are SYNTHETIC-BASELINE numbers on generator output. No physical
  capture has yet fed this detector — hardware-gated until the P0/P1
  runs land.
