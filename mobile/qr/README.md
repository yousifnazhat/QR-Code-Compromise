# P6 QR Reuse — `qr-ducky sheet` for mobile-lure URLs

> **AUTHORIZATION — LAB ONLY.** Print QR sheets for **your lab staging
> URLs only** (`docs/governance/policy.md` §1). The P6 end-state under study
> is the URL-reachable chain classes (all demonstrated with historical,
> already-patched bugs per policy §7); the QR is just the carrier.

P6 introduces **no new QR machinery**. The phone-side chain starts at a URL,
so the entire QR step is the P2 tool that already exists (contract #2 in
`COORDINATION.md`):

```
qr-ducky sheet --payload <file> --out <pdf> [--module 4mm] [--ec M]
                [--mode alnum|hex|b64] [--layout US|DE|FR] [--png]
```

The only P6-specific note: **the payload file is just the staging URL
string.** No encoding games are needed on the mobile path (there is no HID
keyboard involved — the phone's scanner app decodes the URL itself), so the
raw string goes straight into the sheet.

## One-line wrapper

`mobile/qr/url_sheet.sh <url> <out.pdf> [extra sheet flags]` writes the URL to
a temp payload file and calls the existing `qr-ducky sheet` CLI verbatim:

```sh
mobile/qr/url_sheet.sh "http://192.0.2.10:8000/payload.html" out/p6-sheet.pdf --png
```

(`192.0.2.10` is RFC 5737 documentation space — use your own lab host.)

The wrapper resolves the CLI as: `$QRDUCKY_CMD` → `qr-ducky` on PATH →
repo fallback `PYTHONPATH=qrducky python3 -m qrducky.cli` (needs Python ≥ 3.11
for `tomllib`). Install the CLI once: `pip install -e qrducky`.

## Where it fits in the rig

The full loop is defined in `mobile/rig/harness/run_manifest.json`:
print the staging-URL sheet → (physical slot) scan it with a lab phone or
hand the URL to the emulator via `mobile/rig/harness/load_url.sh` → chain
proceeds per `mobile/rig/README.md`. Module size / EC tuning for scan
reliability is P1's territory (`data/symbology.csv`); defaults are fine for
lab distances.

## Rules

- Payload = a URL you control, on hosts you control (policy §2: no default
  endpoints; the committed example uses documentation-reserved addresses).
- Nothing else in P6 re-implements QR encoding, layout, or sheeting — if a
  need appears, it goes back to P2 as a contract question.
