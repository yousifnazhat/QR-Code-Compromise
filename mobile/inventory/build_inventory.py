#!/usr/bin/env python3
"""build_inventory.py — P6 known chain-class inventory from PUBLIC data (W6.2).

Patch-history archaeology for the QR-Code-Compromise project: mines the
NVD CVE API (2.0) and the Android Security Bulletin pages for the historical,
ALREADY-PATCHED vulnerability classes that implement stages of the
QR -> URL -> code-execution chain on a phone. No novel-vulnerability research
happens here; every row is a public, vendor-patched historical bug.

Sources (all public):
  - NVD CVE API 2.0:  https://services.nvd.nist.gov/rest/json/cves/2.0
  - Android Security Bulletins: https://source.android.com/docs/security/bulletin

AUTHORIZATION -- LAB ONLY (docs/governance/policy.md §1, §7). This script only
reads public vulnerability records; it builds nothing weaponized.

Usage:
    python3 build_inventory.py [--out-dir DIR]

Stdlib only (Python >= 3.9). No API key required (NVD anonymous rate limit:
5 requests / 30 s -> we sleep 6 s between requests).

Outputs (in --out-dir, default: script directory):
    chain-classes.csv  — one row per CVE: class, affected, patch ref,
                         public writeup, chain stage, NVD enrichment,
                         bulletin attribution.
    chain-classes.md   — human-readable grouped table + mining appendix.

Exit codes: 0 success, 1 any NVD/bulletin fetch failed after retries.
"""

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_PAGE = "https://nvd.nist.gov/vuln/detail/{cve}"
UA = "QR-Code-Compromise-P6-inventory/1.0 (research; contact via repo)"
SLEEP_S = 6  # anonymous NVD rate limit hygiene
RETRIES = 3

# --------------------------------------------------------------------------
# Curated seeds: class -> historical, already-patched CVEs.
# Every chain class maps to a stage of S(scan) -> U(open URL) -> E(exec) -> C(callback).
# "writeup" = verified public writeup/advisory/exploit page (all pre-patch, all public).
# --------------------------------------------------------------------------
SEEDS = [
    # C1 — JS-bridge RCE (addJavascriptInterface family)
    dict(class_id="C1", cve="CVE-2012-6636",
         affected="Android API < 17 (apps with targetSdk < 17 stay exposed on later OS builds)",
         patch_ref="Android 4.2 (API 17): only @JavascriptInterface methods exposed to apps targeting 17+",
         writeup="Metasploit: Android Browser and WebView addJavascriptInterface Code Execution",
         writeup_url="https://www.rapid7.com/db/modules/exploit/android/browser/webview_addjavascriptinterface",
         chain_stage="U->E: URL->WebView page JS->bridge object->Java Reflection->Runtime.exec (shell)"),
    dict(class_id="C1", cve="CVE-2014-1939",
         affected="Android before 4.4 (SearchBox object exposed via BrowserFrame.java)",
         patch_ref="Android 4.4 (KTU84P)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL->WebView->exposed SearchBox bridge object->code execution"),
    dict(class_id="C1", cve="CVE-2014-7224",
         affected="Android prior to 4.4.0 (accessibility / accessibilityTraversal objects)",
         patch_ref="Android 4.4 (KTU84P)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL->WebView->accessibility bridge objects->code execution"),
    # C2 — WebView same-origin / file-scheme bypass
    dict(class_id="C2", cve="CVE-2014-6041",
         affected="Android WebView before 4.4",
         patch_ref="Android 4.4 (KTU84P)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL->WebView->NUL-char SOP bypass->local-file theft (pivot stage)"),
    # C3 — browser/WebView engine n-day (renderer RCE)
    dict(class_id="C3", cve="CVE-2016-4622",
         affected="Apple iOS before 9.3.3; Safari before 9.1.2; tvOS before 9.2.2",
         patch_ref="Apple iOS 9.3.3 (HT206900)",
         writeup="ZDI-16-485: Apple Safari Array.slice OOB access",
         writeup_url="https://www.zerodayinitiative.com/advisories/ZDI-16-485/",
         chain_stage="U->E: URL->Safari renderer->memory corruption->RCE (shell)"),
    dict(class_id="C3", cve="CVE-2018-17463",
         affected="Google Chrome before 70.0.3538.64 (V8)",
         patch_ref="Chrome 70.0.3538.64 stable (2018-10)",
         writeup="Chrome Releases: Stable Channel Update for Desktop (Oct 2018)",
         writeup_url="https://chromereleases.googleblog.com/2018/10/stable-channel-update-for-desktop.html",
         chain_stage="U->E: URL->Chrome renderer->V8 type confusion->RCE (shell)"),
    dict(class_id="C3", cve="CVE-2019-5782",
         affected="Google Chrome before 72.0.3626.81 (V8)",
         patch_ref="Chrome 72.0.3626.81 stable (2019-01)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL->Chrome renderer->V8 optimization bug->RCE (shell)"),
    dict(class_id="C3", cve="CVE-2020-6418",
         affected="Google Chrome before 80.0.3987.122 (V8; exploited in the wild)",
         patch_ref="Chrome 80.0.3987.122 stable (2020-02)",
         writeup="Chrome Releases: Stable Channel Update for Desktop (Feb 2020, in-the-wild ack)",
         writeup_url="https://chromereleases.googleblog.com/2020/02/stable-channel-update-for-desktop_24.html",
         chain_stage="U->E: URL->Chrome renderer->V8 type confusion->RCE (shell)"),
    # C4 — intent:// / custom-scheme handler abuse
    dict(class_id="C4", cve="CVE-2014-3502",
         affected="Apache Cordova Android before 3.5.1 (and apps built on it)",
         patch_ref="Apache Cordova Android 3.5.1 (vendor advisory, 2014-08)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL with crafted URI scheme->Cordova WebView bridge->launch arbitrary apps"),
    dict(class_id="C4", cve="CVE-2016-4782",
         affected="Lenovo SHAREit before 3.5.98_ww on Android < 4.2",
         patch_ref="SHAREit 3.5.98_ww (Lenovo advisory, 2016)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: crafted intent: URL->scheme handler->unspecified impact in handler app"),
    dict(class_id="C4", cve="CVE-2017-5096",
         affected="Google Chrome before 60.0.3112.78 for Android",
         patch_ref="Chrome 60.0.3112.78 stable (2017-07)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: page navigation between schemes->insufficient policy enforcement->policy bypass"),
    dict(class_id="C4", cve="CVE-2017-17553",
         affected="Dolphin Browser for Android 12.0.2",
         patch_ref="Dolphin Browser update (2018)",
         writeup=None, writeup_url=None,
         chain_stage="U->E: URL->insecure Intent URI parsing->native component launch"),
    # C5 — page-embedded media-decoder RCE
    dict(class_id="C5", cve="CVE-2015-1538",
         affected="Android before 5.1.1 LMY48I (libstagefright)",
         patch_ref="Nexus Security Bulletin 2015-08-01 (LMY48I)",
         writeup="jduck/cve-2015-1538-1: public stsc MP4 atom exploit",
         writeup_url="https://github.com/jduck/cve-2015-1538-1",
         chain_stage="U->E: URL->page embeds crafted MP4->libstagefright integer overflow->RCE (shell)"),
    # C6 — install-flow / package-signature bypass
    dict(class_id="C6", cve="CVE-2013-4787",
         affected="Android 1.6 Donut through 4.2 Jelly Bean (APK signature verification)",
         patch_ref="Android 4.3+ (Google bug 8219321; Bluebox disclosure 2013-07)",
         writeup="ZDNET: Google releases fix to OEMs for Bluebox 'Master Key' Android security hole",
         writeup_url="http://www.zdnet.com/google-releases-fix-to-oems-for-blue-security-android-security-hole-7000017782/",
         chain_stage="U->download/consent: URL->trojaned APK accepted as same-signature update->install->code on device"),
    dict(class_id="C6", cve="CVE-2017-13156",
         affected="Android 5.1.1 through 8.0 (ART / v1 APK signature scheme)",
         patch_ref="Android Security Bulletin 2017-12-01 (A-64211847)",
         writeup="Guardsquare: Janus vulnerability (CVE-2017-13156) analysis",
         writeup_url="https://www.guardsquare.com/blog/new-android-vulnerability-allows-attackers-to-modify-apps-without-affecting-their-signatures-guardsquare",
         chain_stage="U->download/consent: URL->DEX-prepended APK passes v1 signature->install as update->code on device"),
]

CLASS_NAMES = {
    "C1": "JS-bridge RCE (addJavascriptInterface family)",
    "C2": "WebView same-origin / file-scheme bypass",
    "C3": "Browser/WebView engine n-day (renderer RCE)",
    "C4": "intent:// and custom-scheme handler abuse",
    "C5": "Page-embedded media-decoder RCE",
    "C6": "Install-flow / package-signature bypass",
}

# Keyword mining pass: shows the NVD keyword corpus for each class family.
# Rows found here are candidates only; the inventory itself is the curated
# seed set enriched with live NVD data.
KEYWORD_QUERIES = ["addJavascriptInterface", "intent scheme"]

# Android Security Bulletin pages mined for CVE->bulletin attribution.
BULLETIN_PAGES = [
    ("ASB-2015-08", "https://source.android.com/docs/security/bulletin/2015-08-01"),
    ("ASB-2017-12", "https://source.android.com/docs/security/bulletin/2017-12-01"),
]

WRITEUP_REF_HINTS = (
    "jvn.jp", "rapid7.com", "chromereleases.googleblog.com", "projectzero",
    "zerodayinitiative.com", "guardsquare.com", "github.com", "exploit-db",
    "cordova.apache.org", "support.apple", "googleblog", "exodusintel",
)


def http_get(url: str, timeout: int = 30) -> bytes:
    """GET with retries; sleeps on 403/429 (NVD anonymous rate limiting)."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last_err = "HTTP %s for %s" % (e.code, url)
            if e.code in (403, 429):
                time.sleep(12)
                continue
            raise
        except urllib.error.URLError as e:
            last_err = "%s for %s" % (e.reason, url)
            time.sleep(5)
    raise RuntimeError("fetch failed after %d retries: %s" % (RETRIES, last_err))


def nvd_cve(cve_id: str) -> dict:
    """One NVD record (description + references), respecting rate limits."""
    url = "%s?cveId=%s" % (NVD_API, cve_id)
    data = json.loads(http_get(url).decode("utf-8"))
    for item in data.get("vulnerabilities", []):
        if item["cve"]["id"] == cve_id:
            return item["cve"]
    raise RuntimeError("CVE %s not found in NVD" % cve_id)


def nvd_keyword(query: str, limit: int = 20) -> dict:
    url = ("%s?keywordSearch=%s&resultsPerPage=%d"
           % (NVD_API, urllib.request.quote(query), limit))
    data = json.loads(http_get(url).decode("utf-8"))
    ids = [v["cve"]["id"] for v in data.get("vulnerabilities", [])]
    return {"query": query, "total": data.get("totalResults", 0), "ids": ids}


def bulletin_cves(label: str, url: str) -> dict:
    raw = http_get(url).decode("utf-8", errors="replace")
    text = html.unescape(raw)
    ids = sorted(set(re.findall(r"CVE-\d{4}-\d{4,7}", text)))
    return {"bulletin": label, "url": url, "cves": ids}


def pick_writeup(cve: dict, seed_writeup_url, seed_writeup):
    """Seed writeup wins; otherwise promote a writeup-ish NVD reference."""
    if seed_writeup_url:
        return seed_writeup, seed_writeup_url
    for ref in cve.get("references", []):
        url = ref.get("url", "")
        if any(h in url for h in WRITEUP_REF_HINTS):
            return "NVD reference: %s" % url, url
    return "NVD record (references in nvd_refs column)", NVD_PAGE.format(cve=cve["id"])


def build(out_dir: Path) -> int:
    rows = []
    print("== P6 inventory: mining NVD for %d historical chain entries ==" % len(SEEDS))
    for i, seed in enumerate(SEEDS, 1):
        cve = nvd_cve(seed["cve"])
        desc = next((d["value"] for d in cve["descriptions"] if d["lang"] == "en"), "")
        refs = "; ".join(sorted({r["url"] for r in cve.get("references", [])}))
        w_label, w_url = pick_writeup(cve, seed["writeup_url"], seed["writeup"])
        rows.append({
            "class_id": seed["class_id"],
            "class": CLASS_NAMES[seed["class_id"]],
            "cve": seed["cve"],
            "affected": seed["affected"],
            "patch_ref": seed["patch_ref"],
            "public_writeup": w_label,
            "writeup_url": w_url,
            "chain_stage": seed["chain_stage"],
            "nvd_url": NVD_PAGE.format(cve=seed["cve"]),
            "nvd_description": desc,
            "nvd_refs": refs,
            "bulletin": "",
            "status": "historical / already patched",
        })
        print("  [%2d/%d] %-4s %-15s %s" % (i, len(SEEDS), seed["class_id"], seed["cve"],
                                            desc[:60] + ("..." if len(desc) > 60 else "")))
        time.sleep(SLEEP_S)

    print("== Android Security Bulletin mining ==")
    bulletins = []
    for label, url in BULLETIN_PAGES:
        b = bulletin_cves(label, url)
        bulletins.append(b)
        print("  %s: %d CVE ids mentioned (%s)" % (label, len(b["cves"]), url))
        for row in rows:
            if row["cve"] in b["cves"]:
                row["bulletin"] = ("%s %s" % (row["bulletin"], label)).strip()
        time.sleep(2)

    print("== NVD keyword mining (class-family corpus, candidates only) ==")
    keywords = []
    for q in KEYWORD_QUERIES:
        kw = nvd_keyword(q)
        keywords.append(kw)
        seeded = [i for i in kw["ids"] if i in {r["cve"] for r in rows}]
        print("  '%s': totalResults=%d; sampled=%s; already in inventory: %s"
              % (q, kw["total"], kw["ids"], seeded))
        time.sleep(SLEEP_S)

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "chain-classes.csv"
    md_path = out_dir / "chain-classes.md"
    write_csv(csv_path, rows)
    write_md(md_path, rows, bulletins, keywords)
    print("== wrote %s (%d rows) and %s ==" % (csv_path, len(rows), md_path))
    return 0


def write_csv(path: Path, rows) -> None:
    cols = ["class_id", "class", "cve", "affected", "patch_ref", "public_writeup",
            "writeup_url", "chain_stage", "nvd_url", "nvd_description", "nvd_refs",
            "bulletin", "status"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_md(path: Path, rows, bulletins, keywords) -> None:
    today = time.strftime("%Y-%m-%d")
    lines = []
    lines.append("# P6 Known Chain-Class Inventory — historical, already-patched (W6.2)")
    lines.append("")
    lines.append("> **AUTHORIZATION — LAB ONLY.** Patch-history archaeology for the")
    lines.append("> QR-Code-Compromise project (authorized security research). Every")
    lines.append("> entry below is a **public, vendor-patched** historical vulnerability,")
    lines.append("> mined from NVD (services.nvd.nist.gov) and the Android Security")
    lines.append("> Bulletins (source.android.com) on %s. Regenerate:" % today)
    lines.append("> `python3 mobile/inventory/build_inventory.py`. This inventory")
    lines.append("> contains no novel-vulnerability research; any *new* finding goes")
    lines.append("> through coordinated disclosure per `docs/governance/policy.md` §7.")
    lines.append("")
    lines.append("Generated: %s · Source APIs: NVD CVE API 2.0 · Android Security"
                 " Bulletin pages · Rows: %d · Classes: %s"
                 % (today, len(rows), ", ".join(sorted(CLASS_NAMES))))
    lines.append("")
    for cid in sorted(CLASS_NAMES):
        crows = [r for r in rows if r["class_id"] == cid]
        lines.append("## %s — %s" % (cid, CLASS_NAMES[cid]))
        lines.append("")
        lines.append("Taxonomy surface: `mobile/docs/surface-taxonomy.md` · "
                     "Defender mirror: `mobile/docs/defender-parity.md`")
        lines.append("")
        lines.append("| CVE | Affected | Patch reference | Public writeup | Chain stage |")
        lines.append("|---|---|---|---|---|")
        for r in crows:
            wl = "[%s](%s)" % (r["public_writeup"], r["writeup_url"]) if r["writeup_url"] else r["public_writeup"]
            extra = " · also in %s" % r["bulletin"] if r["bulletin"] else ""
            lines.append("| [%s](%s) | %s | %s%s | %s | %s |"
                         % (r["cve"], r["nvd_url"], r["affected"], r["patch_ref"], extra,
                            wl, r["chain_stage"]))
        lines.append("")
    lines.append("## Appendix A — NVD keyword mining (candidate corpus)")
    lines.append("")
    lines.append("Keyword queries are run against the live NVD API to show the")
    lines.append("candidate corpus for each class family. Inventory membership is")
    lines.append("curated (verified class + public writeup); these are candidates only.")
    lines.append("")
    for kw in keywords:
        lines.append("- `keywordSearch=%s` — totalResults: %d; sampled ids: %s"
                     % (kw["query"], kw["total"], ", ".join(kw["ids"]) or "(none)"))
    lines.append("")
    lines.append("## Appendix B — Android Security Bulletin mining")
    lines.append("")
    for b in bulletins:
        matched = [r["cve"] for r in rows if r["bulletin"] and b["bulletin"] in r["bulletin"]]
        lines.append("- [%s](%s): %d CVE ids on the page; inventory matches: %s"
                     % (b["bulletin"], b["url"], len(b["cves"]),
                        ", ".join(matched) or "(none)"))
    lines.append("")
    lines.append("## Method / reproducibility")
    lines.append("")
    lines.append("- One NVD API 2.0 call per CVE (`cveId=` lookup), 6 s spacing, no API")
    lines.append("  key (anonymous rate limit). Descriptions and reference URLs are the")
    lines.append("  live NVD values at generation time.")
    lines.append("- Bulletin pages fetched as HTML and mined with a CVE-id regex.")
    lines.append("- All rows are **historical and already patched**; `patch_ref` names the")
    lines.append("  vendor fix that closed each bug. This is the Stage-1 evidence base")
    lines.append("  for the Stage-2 rig reproductions (`mobile/rig/README.md`).")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the P6 known chain-class inventory (public data only).")
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent),
                    help="output directory (default: this script's directory)")
    args = ap.parse_args(argv)
    try:
        return build(Path(args.out_dir))
    except Exception as e:
        print("FATAL: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
