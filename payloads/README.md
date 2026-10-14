# P3 — Payload Engineering corpus (W3)

Templates and tooling for studying Run-dialog keystroke-injection
kill-chains (QR-scanner-as-HID → Win+R → LOLBin one-liner), for the
QR-Code-Compromise research project.

> **AUTHORIZATION NOTICE — READ FIRST**
>
> Everything in this directory is **authorized-lab-security-research
> material**. It is designed to be exercised only on:
>
> - lab target VMs owned by the researcher,
> - under the project's written authorization (see `docs/governance/policy.md`
>   on `master`, GX.1),
> - with **placeholder infrastructure only** — every hostname/IP in this
>   corpus is `attacker.example` (RFC 2606 reserved) or an RFC1918 `10.x`
>   address explicitly marked example-only. There are **no live or default
>   C2 endpoints** anywhere in this phase (GX.2).
>
> Using these templates against systems you do not own or are not
> authorized to test is illegal in most jurisdictions. The maintainers do
> not condone such use.

## Corpus layout

```
payloads/
├── manifest.yaml          # contract #4 manifest (frozen; P4 runbook consumes)
├── validate_manifest.py   # schema validator for manifest + killchain.csv
├── run_matrix.py          # renderer + plan/dry-run runner (never executes)
├── targets.toml.example   # placeholder targets file (copy → targets.toml, gitignored)
├── templates/             # one Run-dialog one-liner class per file
│   ├── ps-enc-001.txt     # powershell -enc inline baseline
│   ├── mshta-001.txt      # mshta remote .hta (staged)
│   ├── curl-001.txt       # curl.exe download+exec (Win10 1803+, staged)
│   ├── certutil-001.txt   # certutil -urlcache download+exec (staged)
│   ├── msiexec-001.txt    # msiexec UNC .msi install (staged)
│   └── unc-001.txt        # plain UNC exe (staged control, minimal keystrokes)
├── results/
│   ├── killchain.csv      # contract #4 verdict landing zone (header only until VM runs)
│   └── README.md          # verdict vocabulary + how rows land
└── docs/
    ├── amsi-clm-matrix.md # W3.4: Win10 build → PS version → AMSI/CLM presence
    └── capacity-notes.md   # W3.2: QR v40 capacity vs template lengths
```

The manifest ID set (`ps-enc-001 … unc-001`) is **locked** by coordinator
decision: P4's detection runbook keys to these IDs verbatim. Changing it
requires the contract-amendment flow in `COORDINATION.md`.

## Template file format

Each `templates/<id>.txt` is a `#`-prefixed header followed by the command
line. Header keys: `TEMPLATE`, `CLASS`, `AUTHORIZATION`, `PURPOSE`,
`PREREQUISITES`, `CLEANUP`, and one or more `ARTIFACT` lines (the expected
artifacts that feed P4's W4.3 artifact runbook). Command bodies contain
`<PLACEHOLDER>` markers rendered from `targets.toml`.

## Usage

```sh
cd payloads/
cp targets.toml.example targets.toml     # fill in YOUR authorized lab placeholders
python3 validate_manifest.py             # schema check (contract #4)
python3 run_matrix.py targets.toml --dry-run   # exact commands + artifact plans
python3 run_matrix.py targets.toml            # execution plan only
```

`run_matrix.py` **requires** `targets.toml` and **never executes anything**:
VM execution is a manual physical slot for the human operator, recorded in
`results/killchain.csv` (see `results/README.md` for the
`bypass|blocked|partial` verdict vocabulary).

## Manifest field semantics

Contract #4 fields, as used here:

| Field | Semantics |
|---|---|
| `id` | Locked ID set; `templates/<id>.txt` must exist |
| `runner` | Contract enum of the LOLBin entry point |
| `staging` | `inline` (payload body is keystroke-injected) or `staged` (body fetched at runtime over HTTP/SMB) |
| `layout_safe` | Whether the rendered command is expected to survive P2's W2.2 layout-safe encoder (US/DE/FR); `false` entries are pending the encoder/bench cross-check |
| `win_build` | Minimum Windows 10 build for this runner form (`"any"` = all builds) |
| `amsi` | AMSI outcome `bypassed\|blocked\|na`; `na` until VM runs land results in `results/killchain.csv` |
| `notes` | Cross-references and caveats |

## Related phases

- **P0** (`lab/`): target-VM baseline, keystroke capture/replay.
- **P2** (`qrducky/`): `qr-ducky encode --payload <rendered command> --mode …`
  turns a rendered template into a QR; layout-safe encoding for
  `layout_safe: false` templates is tracked there (W2.2).
- **P4** (`detection/`): consumes this manifest's IDs and per-template
  ARTIFACT lists for the W4.3 artifact runbook.

## Anti-forensics notes (W3.3)

Each template header carries `CLEANUP` and `ARTIFACT` lines — that is the
anti-forensics content of this phase. What the operator can clean vs. what
cannot be cleaned, per kill-chain step:

- **Cleanable in-lab:** Run MRU registry values (`HKCU\...\Explorer\RunMRU`),
  dropped files in `%TEMP%`, stopped processes, closed SMB sessions,
  prefetch files (admin).
- **Not keystroke-cleanable (detection side intentionally keeps them):**
  PowerShell ETW events 4103/4104 if script-block logging is on,
  MsiInstaller eventlog rows from msiexec-001, Defender quarantine records,
  and the HTTP UA strings / SMB session logs on the (lab) staging side.
  These persist **by design** — they are exactly the artifacts P4's W4.3
  runbook keys on, so the lab baseline snapshot (P0) is the reset mechanism,
  not in-guest deletion.
- **Run-dialog MRU is the cheapest cross-template artifact:** every template
  leaves the full command string there; clearing it is step 1 of every
  CLEANUP block.
