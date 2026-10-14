# AMSI / CLM matrix — W3.4: Windows 10 build → PowerShell version → AMSI / CLM presence

Reference table for choosing lab target builds and predicting which
mitigations each template runs into. Researched from public documentation;
sources cited per row below the table. All entries are for **Windows 10
desktop** unless noted.

## Matrix

| Win10 build (OS) | Inbox PowerShell | AMSI in PS console / `-enc` | AMSI in WSH engines (VBScript/JScript, incl. mshta-hosted script) | Automatic CLM under AppLocker/WDAC enforcement |
|---|---|---|---|---|
| 1507 (TH1) | 5.0.10240 | Yes — PS 5.0 introduced AMSI integration | No | No |
| 1511 (TH2) | 5.0.10586 | Yes | No | No |
| 1607 (RS1) | 5.1.14393 | Yes | No | No |
| 1703 (RS2) | 5.1.15063 | Yes | No | No |
| 1709 (RS3, FCU) | 5.1.16299 | Yes | **Yes** — AMSI integrated into Windows Script Host / VBScript / JScript | **Yes** — PS automatically enters ConstrainedLanguage under enforced application-control policy |
| 1803 (RS4) | 5.1.17134 | Yes | Yes | Yes |
| 1809 (RS5) | 5.1.17763 | Yes | Yes | Yes |
| 1903/1909 (19H1/19H2) | 5.1.18362/.18363 | Yes | Yes | Yes |
| 2004/20H2 (2004/19042) | 5.1.19041 | Yes | Yes | Yes |
| 21H1/21H2/22H2 | 5.1 (19041+) | Yes | Yes | Yes |

## Notes and implications for the P3 corpus

- **ps-enc-001** (`powershell -enc`): AMSI scans the decoded script content
  from PS 5.0 on **every Win10 build**; `-enc` hides the script from the
  command line, not from AMSI. On builds ≥1709 with an enforced
  AppLocker/WDAC policy, the console additionally starts in
  ConstrainedLanguage, which blocks many inline-script idioms (e.g. Add-Type,
  arbitrary COM) before AMSI is even reached.
- **mshta-001**: the script engines executed inside `mshta.exe` are
  AMSI-instrumented from 1709 (JScript/VBScript integration); on older
  builds (1507–1703) mshta-hosted script is not AMSI-scanned. This makes
  1607 vs 1709 an interesting comparison pair for the kill-chain matrix.
- **curl-001 / certutil-001 / msiexec-001 / unc-001**: no script engine, so
  AMSI/CLM are not applicable by construction (manifest `amsi: na` is
  structural, not a bypass claim); on-access AV / application control still
  apply to the fetched or remote binary.
- **PowerShell 7.x** (optional side-by-side install): also AMSI-integrated
  on Windows; not inbox on any Win10 build and out of scope for the matrix.
- **.NET 4.8+**: `System.Management.Automation` uses AMSI via the CLR-host
  integration; irrelevant to the inbox table but relevant if the lab adds
  .NET-based tooling.

## Sources

1. Microsoft Learn — *Antimalware Scan Interface (AMSI)* (component list:
   UAC, PowerShell scripts/interactive/dynamic code evaluation, Windows
   Script Host (`wscript.exe`/`cscript.exe`), JavaScript and VBScript,
   Office VBA; "integrated into these components of Windows 10"):
   https://learn.microsoft.com/en-us/windows/win32/amsi/antimalware-scan-interface-portal
2. Microsoft Learn — *about_Language_Modes* ("PowerShell automatically runs
   in ConstrainedLanguage mode when it's running under a system application
   control policy" — AppLocker and WDAC):
   https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_language_modes
3. PowerShell Team blog — *PowerShell Constrained Language Mode*
   (Nov 2, 2017; describes the Windows 10 Fall Creators Update (1709)
   behavior where enforced application-control policy forces CLM):
   https://devblogs.microsoft.com/powershell/powershell-constrained-language-mode/
4. Graeber & Christel — *The Rise and Fall of AMSI* (2018) — timeline of
   AMSI integration, including the Windows Script Host (VBScript/JScript)
   integration in the 1709 wave. Secondary research source; the exact
   backport/KB picture for WSH should be re-verified against the lab's
   patch level because servicing updates changed integration points.
   https://www.mdsec.com/2018/05/the-rise-and-fall-of-amsi/ (talk material
   summarized across public write-ups)
5. Microsoft Learn — *Windows PowerShell system requirements* (Windows 10
   1507/1511 ship PowerShell 5.0; 1607+ ship 5.1):
   https://learn.microsoft.com/en-us/powershell/scripting/windows-powershell/install/windows-powershell-system-requirements

**Verification status:** rows are compiled from the sources above; cells
marked with behavior changes (1709 WSH-AMSI) rest partly on secondary
research and MUST be confirmed on the actual lab VM images before kill-chain
rows are recorded as `blocked`/`bypass` in `results/killchain.csv`.
