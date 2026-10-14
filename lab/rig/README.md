# lab/rig — HID replay rig (W0.3)

An Arduino Pro Micro (ATmega32U4) flashed as a **lab-only keystroke
injection rig**: text payloads arrive over USB serial and are replayed as
HID keyboard strokes with configurable prefix (e.g. `GUI r`), suffix
(e.g. `ENTER`), rate (`CPS`) and inter-key jitter. While typing, the rig
emits one **contract-#1 JSONL keystroke event per line back over serial**,
giving replay-side ground truth for the P4 timing dataset without needing a
capture hook on the target.

> **AUTHORIZATION — LAB ONLY.** This device is functionally a keystroke
> injector (a "rubber ducky"). Use it only on systems you own or have
> **written authorization** to test. Never connect it to a machine you do
> not have permission to test. Do not commit payloads containing real
> infrastructure (GX.2: no default C2 endpoints).

## Contents

| File | Purpose |
|---|---|
| `rig_replay/rig_replay.ino` | Firmware (Arduino Keyboard library, no extra libs) |
| `send_payload.py` | Host driver (stdlib-only; `pyserial` is the single optional dependency for live serial) |

## Hardware & wiring

* Arduino Pro Micro (ATmega32U4, 5 V or 3.3 V — either works for USB HID).
* **No wiring beyond USB.** The board's native USB port is both the HID
  keyboard and the control serial port (USB CDC). Nothing else is connected.
* Optional: a momentary switch between GND and RST gives a one-tap way to
  enter the bootloader if a bad payload ever locks the sketch.

## Flashing (physical slot — human step)

No automated flashing in this repo; flashing is a physical bench step.

1. Install the Arduino IDE; Boards Manager → install **Arduino AVR Boards**
   (bundled Keyboard/EEPROM libraries, nothing else needed).
2. Open `rig_replay/rig_replay.ino`; select board **Arduino Micro**,
   select the Pro Micro's serial port.
3. If the port doesn't appear: hold GND→RST twice quickly (bootloader),
   then flash immediately.
4. Serial monitor at **115200 baud** should print `RIG READY rig-pro-micro-01`.

**Smoke without a payload:** in the serial monitor send:

```
SESSION sess-smoke
PREFIX GUI r
SUFFIX ENTER
TEST hello
```

Expect `OK ...` replies interleaved with JSONL events like
`{"ts_ms":4123,"event":"keydown","keycode":8,"source":"rig","device":"rig-pro-micro-01","session":"sess-smoke"}`.

## Serial protocol (115200, LF/CRLF lines)

| Command | Meaning |
|---|---|
| `ID <rig-id>` | set persistent rig id (EEPROM) |
| `SESSION <sess-id>` | session label for emitted events (contract #1) |
| `PREFIX <tokens>` | keys typed before payload, e.g. `GUI r` |
| `SUFFIX <tokens>` | keys typed after payload, e.g. `ENTER` |
| `CPS <n>` | base typing rate 1..200 chars/sec (default 20) |
| `JITTER <ms>` | 0..250 ms random extra inter-key delay (default 15) |
| `TEST <text>` | one-shot prefix + text + suffix replay |
| `BEGIN` | type prefix, enter **streaming mode** |
| *(streaming)* `<fragment>` | ≤47 bytes + LF; typed as keys; rig replies `ACK` |
| *(streaming)* `END` | type suffix, leave streaming mode |
| *(streaming)* `ABORT` | stop immediately, release all keys |
| `STATUS` | print current configuration |
| `PING` | replies `PONG` |

Token grammar for PREFIX/SUFFIX: space-separated `GUI CTRL SHIFT ALT RGUI
RCTRL RSHIFT RALT ENTER ESC BACKSPACE TAB SPACE F1..F12` or any single
printable character. Leading modifier tokens are held while the first
non-modifier token is tapped, then released (so `GUI r` opens Run, `CTRL
SHIFT t` opens a new tab).

**Streaming flow control:** the host sends a fragment of at most 47 bytes,
LF-terminated; the rig types it and only then replies `ACK`. The host must
wait for `ACK` before the next fragment (stop-and-wait keeps the 64-byte
AVR serial buffer safe at any CPS). A bare LF (empty fragment) types a
newline/ENTER. The literal fragment `END` terminates the stream. CR is
stripped by the rig and cannot be typed.

## JSONL event output (contract #1)

One event per line, UTF-8, emitted on the same serial port:

```json
{"ts_ms":123456,"event":"keydown","keycode":65,"source":"rig","device":"rig-pro-micro-01","session":"sess-017"}
```

* `ts_ms` — `millis()`, rig-local monotonic ms (wraps at ~49 days; sessions
  are minutes long, so wrap is a non-issue).
* `keycode` — USB HID usage id (decimal). Modifiers report their usage id
  (LeftGUI = 227, …); shifted characters report the base usage, exactly as a
  real keyboard would.
* `event` — `keydown` / `keyup`.
* `source` is always `"rig"`; `device` is the rig id; `session` is the label
  set via `SESSION`.

## Host driver

```
python3 send_payload.py --port /dev/ttyACM0 --payload payload.txt \
    --prefix "GUI r" --suffix ENTER --cps 20 --jitter 15 \
    --session sess-001 --out rig-events.jsonl
```

`--dry-run` prints the whole protocol conversation without a port (useful
to verify chunking). `pyserial` is the single non-stdlib dependency and only
for live use — the import is guarded and `--dry-run` needs nothing.

## Safety notes

* **Physical kill switch:** unplugging USB aborts the replay instantly.
  `ABORT` over serial also stops mid-stream and releases held keys.
* The rig holds no payloads in flash; payloads exist only in host memory
  and transit the serial link, so the device is inert when re-powered.
* `Keyboard.releaseAll()` is issued on every exit path (END, ABORT, boot).
* Keep CPS realistic for the study (10–90 cps is the human-vs-scanner
  range of interest); >200 cps is refused.
* Label every session (`SESSION`) so P4 can join rig events with target-side
  capture logs.
