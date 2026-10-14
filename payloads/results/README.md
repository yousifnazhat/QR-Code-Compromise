# Kill-chain results (contract #4)

`killchain.csv` is the landing zone for verdicts from VM runs of the P3
payload matrix. It is filled in by the human operator — VM execution is a
**manual physical slot**; no tool in this repository executes payloads.

Schema (frozen in `COORDINATION.md` contract #4):

```
payload_id,runner,mitigation,verdict
```

| Column    | Meaning                                                        |
|-----------|----------------------------------------------------------------|
| `payload_id` | Manifest ID, one of: `ps-enc-001`, `mshta-001`, `curl-001`, `certutil-001`, `msiexec-001`, `unc-001` (locked set) |
| `runner`  | Must equal the `runner` field of that manifest entry           |
| `mitigation` | Mitigation state on the VM during the run, e.g. `defender-rtp-on`, `defender-rtp-off+amsi-on`, `applocker-script-enforce`, `wdac-audit` — free text, one state per row |
| `verdict` | One of the vocabulary below                                    |

## Verdict vocabulary

| Verdict    | Meaning |
|------------|---------|
| `bypass`   | The template ran end-to-end: command executed, and the payload's intended action completed. No mitigation stopped any stage. |
| `blocked`  | A mitigation stopped the chain outright (e.g. AMSI scan aborted the script, Defender quarantined the drop, AppLocker refused execution). Nothing downstream ran. |
| `partial`  | Some stages ran and some were stopped (e.g. download succeeded but on-execution detection killed it; command executed but AMSI stripped the payload action). |

## How rows land

1. Boot the target VM from the P0 baseline snapshot (see the `p0-foundations`
   lab docs) and set the mitigation state to record.
2. Generate the QR/keystroke artifacts with P2's `qr-ducky` CLI from the
   rendered command printed by `run_matrix.py --dry-run`, or replay via the
   P0 rig.
3. Run the template, observe the expected artifacts for that template
   (listed by `run_matrix.py --dry-run`, template headers in
   `payloads/templates/`), and perform the CLEANUP steps from the header.
4. Append one row per `(payload_id, mitigation_state)` combination.
5. Re-run `python3 payloads/validate_manifest.py` — it checks that every row
   references a known manifest ID with the matching runner and a valid
   verdict.

Raw evidence (screenshots, event-log exports, ETW traces) belongs in
`payloads/results/raw/` (gitignored).
