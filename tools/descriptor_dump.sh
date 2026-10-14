#!/usr/bin/env bash
#
# descriptor_dump.sh -- one-shot USB/HID descriptor extraction for P1 W1.1
# (scanner class matrix: HID-wedge vs CDC-serial vs vendor-driver).
#
# AUTHORIZATION: lab-only hardware inventory tool for the QR-Code-Compromise
# study. It only READS local OS device listings for OWNED, AUTHORIZED
# barcode scanners. It does not communicate with any device.
#
# Usage:
#   tools/descriptor_dump.sh [output-dir]
#
#   output-dir defaults to data/raw/usb-dump-<timestamp>/ (gitignored).
#   Prints a summary to stdout; full dumps land in the output dir along
#   with CLASSIFICATION-NOTES.txt (how to read the dumps).
#
# Exit codes: 0 = dumps written; 1 = unsupported platform or failure.

set -euo pipefail

OUT="${1:-}"

if [[ -z "$OUT" ]]; then
  HERE="$(cd "$(dirname "$0")/.." && pwd)"
  OUT="$HERE/data/raw/usb-dump-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$OUT"

UNAME_S="$(uname -s)"

if [[ "$UNAME_S" == "Darwin" ]]; then
  # --- macOS ---------------------------------------------------------------
  # system_profiler: human-readable + XML tree of all USB devices with
  #   Vendor ID / Product ID / bcdDevice and (for HID wedges) interface
  #   class lines "03 .. 01 .. 01" (class/subclass/protocol = HID/boot kbd).
  system_profiler SPUSBDataType          > "$OUT/system_profiler-usb.txt" 2>&1
  system_profiler SPUSBDataType -xml     > "$OUT/system_profiler-usb.xml" 2>&1
  # ioreg USB plane: full property tree (registry entries under IOUSBDevice),
  #   includes idVendor/idProduct/bcdDevice, interface class/subclass/protocol.
  ioreg -p IOUSB -l -w 0                 > "$OUT/ioreg-IOUSB-plane.txt" 2>&1
  # ioreg HID plane: when a device exposes a HID interface, its IOHIDDevice
  #   registry entry can carry the raw HID ReportDescriptor data blob.
  ioreg -r -c IOHIDDevice -l -w 0        > "$OUT/ioreg-IOHIDDevice.txt" 2>&1 || true
  ioreg -r -c IOHIDInterface -l -w 0     > "$OUT/ioreg-IOHIDInterface.txt" 2>&1 || true
  # USB device/interface properties as seen by AppleUSBHost (VID/PID/serial).
  ioreg -r -c IOUSBHostDevice -l -w 0    > "$OUT/ioreg-IOUSBHostDevice.txt" 2>&1 || true

  PLATFORM="macOS"
elif [[ "$UNAME_S" == "Linux" ]]; then
  # --- Linux ---------------------------------------------------------------
  # lsusb (usbutils) is the canonical descriptor source: -v dumps full config
  #   descriptors including bInterfaceClass/bInterfaceProtocol and, for HID,
  #   the parsed Report Descriptor (usage pages, usages, report sizes).
  #   Without root some fields show as "(?)", note this in capture slots.
  if command -v lsusb >/dev/null 2>&1; then
    lsusb -v   > "$OUT/lsusb-verbose.txt" 2>&1 || true
    lsusb -t   > "$OUT/lsusb-tree.txt" 2>&1 || true
  else
    echo "lsusb not found (apt: usbutils / dnf: usbutils)" > "$OUT/lsusb-verbose.txt"
  fi
  # usbhid-dump (usbutils) extracts RAW HID report descriptors per device,
  #   the gold standard for classifying HID-wedge behavior. Requires root.
  if command -v usbhid-dump >/dev/null 2>&1; then
    { usbhid-dump 2>&1 || echo "usbhid-dump needs root: sudo usbhid-dump"; } \
      > "$OUT/usbhid-dump.txt"
  else
    echo "usbhid-dump not found (part of usbutils >= 7.x; needs root)" \
      > "$OUT/usbhid-dump.txt"
  fi
  # sysfs fallback: always available, one file per interface's class codes.
  SYSUSB="$OUT/sysfs-usb"
  mkdir -p "$SYSUSB"
  for d in /sys/bus/usb/devices/*/; do
    [[ -d "$d" ]] || continue
    name="$(basename "$d")"
    mkdir -p "$SYSUSB/$name"
    for f in idVendor idProduct bcdDevice product manufacturer serial \
             bDeviceClass bInterfaceClass; do
      [[ -r "$d/$f" ]] && cp "$d/$f" "$SYSUSB/$name/$f" 2>/dev/null || true
    done
  done

  PLATFORM="Linux"
else
  echo "unsupported platform: $UNAME_S (need Darwin or Linux)" >&2
  exit 1
fi

cat > "$OUT/CLASSIFICATION-NOTES.txt" <<'NOTES'
CLASSIFICATION NOTES (W1.1: HID-wedge vs CDC-serial vs vendor-driver)

How to classify a scanner from these dumps:

1. HID-wedge (keys arrive as if typed):
   - macOS system_profiler: device shows "Interface Class: 03 .. 01 .. 01"
     (bInterfaceClass=03 HID, subclass=01 boot, protocol=01 keyboard) and
     usually a name like "Barcode Scanner" + "Keyboard".
   - macOS ioreg: classes AppleUSBHIDKeyboard / IOHIDDevice exist under the
     device; ioreg-IOHIDDevice.txt may contain a "ReportDescriptor" data
     blob -- the raw HID descriptor.
   - Linux lsusb -v: "bInterfaceClass 3 Human Interface Device",
     "bInterfaceProtocol 1 Keyboard", followed by "Report Descriptor"
     with Usage Page (Generic Desktop), Usage (Keyboard), and KeyCode
     arrays (usage codes 0x04-0xE7 = alphanumeric keys).
   - Attackable-as-HID: yes (subject to prefix/suffix/min_delay/max_cps
     quirks recorded in data/scanners.csv).

2. CDC-serial (data via serial port, needs driver/app):
   - lsusb -v: bInterfaceClass 2 (CDC Control) + 0x0A (CDC Data) pair, or
     bDeviceClass 0x02 / 0xEF with CDC functional descriptors.
   - macOS: appears as "Vendor-Specific" + com.apple.driver.usb.cdc.ecm
     entries / a tty.* device in /dev; NOT an IOHIDDevice.
   - Attackable-as-HID: no (no keystroke interface); still log it in
     data/scanners.csv with interface=cdc-serial, attackable=no.

3. Vendor-driver (proprietary protocol):
   - bInterfaceClass 0xFF (vendor-specific) or a custom bulk/interrupt
     protocol with no HID and no CDC descriptors.
   - Attackable-as-HID: no unless it ALSO exposes a separate HID keyboard
     interface (some 2-in-1 scanners do -- look for MULTIPLE interfaces).

descriptor_hash for data/scanners.csv:
   sha256 of the most descriptive dump for that device, e.g.
   macOS: shasum -a 256 <this-dir>/system_profiler-usb.txt
   Linux: sha256sum <this-dir>/lsusb-verbose.txt
   (Note: timestamps inside dumps make hashes unstable across runs; hash
   only the per-device descriptor section or note the dump date in notes.)

macOS caveats:
   - Apple Silicon machines may hide VID/PID for some built-in ports in
     system_profiler; cross-check with ioreg dumps.
   - Some Apple Silicon machines return an EMPTY SPUSBDataType tree (a
     privacy/entitlement quirk); in that case rely on the ioreg dumps --
     ioreg-IOUSB-plane.txt lists every attached USB device with
     idVendor/idProduct even when system_profiler shows nothing.
   - macOS does NOT expose parsed HID report descriptors in text dumps;
     the raw "ReportDescriptor" bytes in ioreg can be decoded by hand
     (see USB HID spec, section 6.2.2) or pasted into an online parser.
   - For per-device granularity on Linux use: lsusb -v -d <vid>:<pid>.
NOTES

echo "platform:            $PLATFORM"
echo "output dir:          $OUT"
if [[ "$PLATFORM" == "macOS" ]]; then
  # count attached USB devices from the readable dump
  n="$(grep -cE '^\s+(Barcode|Composite|Keyboard|USB).+:$|^\s+[A-Za-z0-9].+:$' \
        "$OUT/system_profiler-usb.txt" || true)"
  echo "raw dump files:      $(ls "$OUT" | wc -l | tr -d ' ')"
  echo "note: inspect $OUT/system_profiler-usb.txt for attached devices"
fi
echo "next: classify each scanner per $OUT/CLASSIFICATION-NOTES.txt and"
echo "      record rows in data/scanners.csv (W1.1)."
