# lab/baseline — W0.1 PoC reproduction kit

Reproduces the repo README's QR-scanner compromise chain
(`Win+R` → keystroke payload → reverse shell) as **reproducible lab
software**, replacing manual steps (web QR generator, PowerShell console
encoding) with one script.

> **AUTHORIZATION — LAB ONLY.** This kit exists to reproduce a documented
> attack chain on **owned lab VMs with written authorization** (GX.1). The
> embedded payload calls back to `10.99.12.233` — a **PLACEHOLDER address,
> EXAMPLE ONLY**; it must never point at real infrastructure (GX.2). If you
> run any part of this chain, you are responsible for having authorization.

## Contents

| File | Purpose |
|---|---|
| `build_poc.py` | builds payload → `-Enc` one-liner → downloader one-liner → QR PNG+PDF |
| `out/` (generated, gitignored) | payload.ps1, 1.txt, one-liners, qr-inline.*, qr-staged.* |
| `../scripts/nc_listener.sh` | reverse-shell listener (README step 3) |
| `../scripts/http_server.sh` | staging HTTP server (README step 4) |

Only dependency: **segno** (approved): `pip install segno`.

## The chain being reproduced

1. **Reverse shell** (README steps 1–2): a PowerShell TCP reverse shell is
   one-lined and base64-encoded (UTF-16LE, matching
   `[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes(...))`),
   producing `powershell -NoP -NonI -W Hidden -Exec Bypass -Enc <b64>`.
   This is what gets hosted as `1.txt`.
2. **Staging server** (steps 3–4): `nc_listener.sh` on 7775 (shell
   callback), `http_server.sh` on 7776 (hosts `1.txt`).
3. **QR keystroke payload** (steps 5–6): the downloader one-liner is
   encoded as a QR code; on the victim, `Win+R` + a scan types it into the
   Run prompt and ENTER executes it: hidden PowerShell downloads `1.txt`
   to `%TEMP%\1.ps1` and runs it → shell lands on the listener.
4. **Attack phase**: the physical act — opening Run and scanning the code —
   is W0.2/W1 territory; on the bench it is done with the replay rig
   (`lab/rig/`) or a real scanner, always on the lab victim VM.

## Staging walkthrough (all software steps)

```bash
# 0. attacker lab VM (Kali or any Unix with python3 + segno)
pip install segno

# 1. build everything: payload, one-liners, QR PNG+PDF (into lab/baseline/out/)
python3 lab/baseline/build_poc.py            # placeholder host 10.99.12.233
#    or, for your lab network: --host <lab-attacker-IP>

# 2. listeners (two terminals)
lab/scripts/nc_listener.sh 7775 &            # reverse shell will land here
lab/scripts/http_server.sh 7776 lab/baseline/out   # hosts 1.txt

# 3. print the QR (qr-staged.pdf is print-exact at scale 4 / border 4)
#    -- PHYSICAL SLOT: printout + scanner bench, see below
```

## Attack walkthrough (lab victim VM — authorized Windows 10 box)

**Do this only on your lab VM with the listener running.**

1. Start the capture hook first if you want timing data:
   `python capture_keystrokes.py --session sess-w01 --source scanner`
   (from `lab/capture/`).
2. Physical slot: scan `qr-staged.png/pdf` with the bench scanner
   (W0.2), or replay the same string with the rig
   (`send_payload.py --port ... --payload out/one-liner-downloader.txt
   --prefix "GUI r" --suffix ENTER`).
3. The Run prompt receives the downloader one-liner, ENTER executes it,
   the victim pulls `1.txt` from the staging server and the shell appears
   on the netcat listener.
4. Takedown: close the listener, delete `%TEMP%\1.ps1` on the victim,
   record the session JSONL for P4.

Two QR variants are produced:

* `qr-staged.*` — downloader one-liner (~160 chars): the **faithful
  reproduction** of the README chain (scan → fetch → execute).
* `qr-inline.*` — the entire `-Enc` one-liner (~2 KB): the inline variant
  with no staging server (README step 2's file content, typed directly).
  Both matter for W3.2 (inline vs staged).

## Verification performed (P0 smoke)

`build_poc.py` was run on macOS with segno 1.6.6: 4 text outputs + QR
PNG/PDF pairs generated; sizes and QR version/EC reported in the phase
report. Decode/scanner reliability of the printed codes is deliberately
**not** claimed here — that is the W0.2 scanner bench (physical slot) and
P1's `data/symbology.csv`.

## Physical capture slots left open (human steps)

1. **Print** `qr-staged.pdf` (print-exact) and/or `qr-inline.pdf`.
2. **Scanner bench (W0.2):** real QR scanner + victim VM runs; record
   contract-#1 JSONL from `lab/capture/` with `--source scanner`.
3. **Rig flash + replay (W0.3 physical):** flash `lab/rig/rig_replay/`
   onto a Pro Micro, replay the downloader one-liner against the lab VM.
