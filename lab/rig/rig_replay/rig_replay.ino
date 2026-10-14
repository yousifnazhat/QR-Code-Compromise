/*
 * rig_replay — HID keystroke replay rig (W0.3)
 * QR-Code-Compromise / Phase P0 Foundations
 *
 * Hardware: Arduino Pro Micro (ATmega32U4) — native USB HID.
 * Library:  Arduino "Keyboard" (bundled with Arduino AVR core, no extra deps).
 *
 * Purpose: lab-only keystroke-injection test rig. Text payloads arrive over
 * the USB CDC serial port and are replayed as HID keystrokes with a
 * configurable prefix (e.g. GUI+r to open a Run prompt), suffix (e.g. ENTER),
 * base rate (cps) and inter-key jitter. Every keystroke is ALSO reported back
 * over serial as a contract-#1 (COORDINATION.md) JSONL event so the replay
 * side has ground-truth timing without needing a capture hook on the target.
 *
 * AUTHORIZATION: for use ONLY on systems you own or have written
 * authorization to test. This device is functionally a keystroke injector
 * (a "rubber ducky"); do not connect it to any machine without consent.
 *
 * Serial protocol (115200 baud, LF- or CRLF-terminated lines):
 *   ID <rig-id>        set persistent rig id (EEPROM), replies OK ID
 *   SESSION <sess-id>  set session label for emitted events
 *   PREFIX <tokens>    key tokens typed before payload, e.g. "GUI r"
 *   SUFFIX <tokens>    key tokens typed after payload,  e.g. "ENTER"
 *   CPS <n>            base typing rate, chars/sec 1..200 (default 20)
 *   JITTER <ms>        0..250 ms random extra inter-key delay (default 15)
 *   TEST <text>        one-shot: prefix + text + suffix, typed immediately
 *   <chunk>            (streaming) fragment, <=47 bytes + LF; typed as keys
 *   END                (streaming) type suffix, leave streaming mode
 *   ABORT              (streaming) stop immediately, release all keys
 *   STATUS             print current configuration
 *   PING               replies PONG
 *
 * Streaming mode / flow control: the host sends a line of at most 47 bytes
 * plus LF; the rig types the fragment (LF stripped) and only then replies
 * "ACK". The host must wait for ACK before the next fragment. A bare LF
 * (empty fragment) types a newline/ENTER key. The literal fragment "END"
 * terminates streaming mode. See lab/rig/README.md and send_payload.py.
 *
 * Replies: "OK ..." on success, "ERR <reason>" on bad input. JSONL keystroke
 * events interleave with replies, one per line:
 *   {"ts_ms":123456,"event":"keydown","keycode":65,"source":"rig",
 *    "device":"rig-pro-micro-01","session":"sess-017"}
 * ts_ms = millis() (rig-local monotonic clock, wraps at 2^32 ms ~= 49 days).
 * keycode = USB HID usage id (decimal), modifiers reported by their usage id
 * (LeftGUI=227 etc.); shifted characters report the base usage (as a real
 * keyboard would).
 */

#include <Keyboard.h>
#include <EEPROM.h>

// ---------------- configuration ----------------

#define SERIAL_BAUD   115200
#define RIG_LINE_MAX 96         // command line buffer
#define CHUNK_MAX     48          // streaming fragment buffer (<=47 + LF)
#define DEF_CPS       20
#define DEF_JITTER_MS 15
#define EEPROM_MAGIC  0xA5
#define EEPROM_ADDR   0

char   rigId[33]  = "rig-pro-micro-01";
char   sessionId[33] = "sess-000";
char   prefixTokens[RIG_LINE_MAX] = "";   // e.g. "GUI r"
char   suffixTokens[RIG_LINE_MAX] = "";   // e.g. "ENTER"
uint8_t cps        = DEF_CPS;
uint8_t jitterMs   = DEF_JITTER_MS;

char    lineBuf[RIG_LINE_MAX];
uint8_t lineLen = 0;
bool    streaming = false;
char    chunkBuf[CHUNK_MAX];
uint8_t chunkLen = 0;

// ---------------- prototypes (explicit; Arduino auto-gen is brittle) ------
uint8_t asciiToUsage(char c, bool *shift);
uint8_t tokenToUsage(const char *tok);
uint8_t modifierToArduino(uint8_t usage);
void emitEvent(const __FlashStringHelper *event, uint8_t usage);
void settleDelay();
void interKeyDelay();
void tapUsage(uint8_t usage, bool shift, uint8_t modUsage);
void typeText(const char *s, uint8_t len);
void typeTokens(const char *tokens);
void handleCommand(char *line);
void handleChunk();

// ---------------- HID usage tables (USB HID usage ids, decimal) ----------
// Modifiers
#define U_LCTRL 0xE0  // 224
#define U_LSHIFT 0xE1 // 225
#define U_LALT  0xE2   // 226
#define U_LGUI  0xE3   // 227  ("Windows key" / Command)
#define U_RCTRL 0xE4
#define U_RSHIFT 0xE5
#define U_RALT  0xE6
#define U_RGUI  0xE7
// Specials
#define U_ENTER 0x28  // 40
#define U_ESC   0x29  // 41
#define U_BKSP  0x2A  // 42
#define U_TAB   0x2B  // 43
#define U_SPACE 0x2C  // 44

// ASCII -> HID usage id for printable US-layout characters.
// Returns usage id or 0 if unmapped. *shift set when Shift is required.
uint8_t asciiToUsage(char c, bool *shift) {
  *shift = false;
  if (c >= 'a' && c <= 'z') return (uint8_t)(0x04 + (c - 'a'));
  if (c >= 'A' && c <= 'Z') { *shift = true; return (uint8_t)(0x04 + (c - 'A')); }
  if (c >= '1' && c <= '9') return (uint8_t)(0x1E + (c - '1'));
  switch (c) {
    case '0': return 0x27;
    case ' ': return U_SPACE;
    case '\n': return U_ENTER;
    case '\t': return U_TAB;
    case '-': case '_': *shift = (c == '_'); return 0x2D;
    case '=': case '+': *shift = (c == '+'); return 0x2E;
    case '[': case '{': *shift = (c == '{'); return 0x2F;
    case ']': case '}': *shift = (c == '}'); return 0x30;
    case '\\': case '|': *shift = (c == '|'); return 0x31;
    case ';': case ':': *shift = (c == ':'); return 0x33;
    case '\'': case '"': *shift = (c == '"'); return 0x34;
    case '`': case '~': *shift = (c == '~'); return 0x35;
    case ',': case '<': *shift = (c == '<'); return 0x36;
    case '.': case '>': *shift = (c == '>'); return 0x37;
    case '/': case '?': *shift = (c == '?'); return 0x38;
    default: return 0; // unmappable
  }
}

// Keyword -> HID usage id for token names (PREFIX/SUFFIX/TEST tokens).
// Returns usage id, or 0 if unknown.
uint8_t tokenToUsage(const char *tok) {
  if (!strcasecmp(tok, "GUI") || !strcasecmp(tok, "WINDOWS")) return U_LGUI;
  if (!strcasecmp(tok, "CTRL"))  return U_LCTRL;
  if (!strcasecmp(tok, "SHIFT"))  return U_LSHIFT;
  if (!strcasecmp(tok, "ALT"))   return U_LALT;
  if (!strcasecmp(tok, "RGUI"))  return U_RGUI;
  if (!strcasecmp(tok, "RCTRL")) return U_RCTRL;
  if (!strcasecmp(tok, "RSHIFT"))return U_RSHIFT;
  if (!strcasecmp(tok, "RALT"))  return U_RALT;
  if (!strcasecmp(tok, "ENTER") || !strcasecmp(tok, "RETURN")) return U_ENTER;
  if (!strcasecmp(tok, "ESC"))   return U_ESC;
  if (!strcasecmp(tok, "BACKSPACE")) return U_BKSP;
  if (!strcasecmp(tok, "TAB"))   return U_TAB;
  if (!strcasecmp(tok, "SPACE")) return U_SPACE;
  if (!strncasecmp(tok, "F", 1) && tok[1] >= '1' && tok[1] <= '9' && !tok[2]) {
    uint8_t n = tok[1] - '0';
    if (n >= 1 && n <= 12) return (uint8_t)(0x3A + (n - 1)); // F1..F12: 58..69
  }
  if (strlen(tok) == 1) {        // single printable char token
    bool dummy;
    return asciiToUsage(tok[0], &dummy);
  }
  return 0;
}

// ---------------- contract #1 JSONL emitter ----------------

void emitEvent(const __FlashStringHelper *event, uint8_t usage) {
  Serial.print(F("{\"ts_ms\":"));
  Serial.print(millis());
  Serial.print(F(",\"event\":\""));
  Serial.print(event);
  Serial.print(F("\",\"keycode\":"));
  Serial.print(usage);
  Serial.print(F(",\"source\":\"rig\",\"device\":\""));
  Serial.print(rigId);
  Serial.print(F("\",\"session\":\""));
  Serial.print(sessionId);
  Serial.println(F("\"}"));
}

// ---------------- keystroke primitives ----------------

// Press+release a single usage with optional shift. Emits JSONL events.
// Token/usage values use HID usage ids; ASCII printable chars are also
// accepted directly (Keyboard library maps them internally).
void tapUsage(uint8_t usage, bool shift, uint8_t modUsage) {
  if (shift) { Keyboard.press(KEY_LEFT_SHIFT); emitEvent(F("keydown"), U_LSHIFT); }
  if (modUsage) { Keyboard.press(modifierToArduino(modUsage)); emitEvent(F("keydown"), modUsage); }
  Keyboard.press(usage);
  emitEvent(F("keydown"), usage);
  settleDelay();
  Keyboard.release(usage);
  emitEvent(F("keyup"), usage);
  if (modUsage) { Keyboard.release(modifierToArduino(modUsage)); emitEvent(F("keyup"), modUsage); }
  if (shift) { Keyboard.release(KEY_LEFT_SHIFT); emitEvent(F("keyup"), U_LSHIFT); }
  interKeyDelay();
}

uint8_t modifierToArduino(uint8_t usage) {
  switch (usage) {
    case U_LCTRL:  return KEY_LEFT_CTRL;
    case U_LSHIFT: return KEY_LEFT_SHIFT; // (only reached for explicit tokens)
    case U_LALT:   return KEY_LEFT_ALT;
    case U_LGUI:   return KEY_LEFT_GUI;
    case U_RCTRL:  return KEY_RIGHT_CTRL;
    case U_RSHIFT: return KEY_RIGHT_SHIFT;
    case U_RALT:   return KEY_RIGHT_ALT;
    case U_RGUI:   return KEY_RIGHT_GUI;
  }
  return 0;
}

void settleDelay()   { delay(10); }        // press->release hold time
void interKeyDelay() {
  uint16_t base = (uint16_t)(1000UL / cps);
  uint16_t jit  = (jitterMs == 0) ? 0 : random(0, jitterMs);
  delay(base + jit);
}

// Type a NUL-terminated string of printable ASCII (or a raw buffer in
// streaming mode). Emits one keydown/keyup JSONL pair per character.
void typeText(const char *s, uint8_t len) {
  for (uint8_t i = 0; i < len; i++) {
    char c = s[i];
    bool shift = false;
    uint8_t usage = asciiToUsage(c, &shift);
    if (usage == 0) { // unmappable: skip, but report over serial
      Serial.print(F("ERR SKIP 0x"));
      Serial.println((uint8_t)c, HEX);
      continue;
    }
    tapUsage(usage, shift, 0);
  }
}

// Type a token sequence such as "GUI r": leading modifier tokens are held
// while the first non-modifier token is tapped, then everything releases.
void typeTokens(const char *tokens) {
  if (!tokens || !tokens[0]) return;
  char buf[RIG_LINE_MAX];
  strncpy(buf, tokens, RIG_LINE_MAX - 1);
  buf[RIG_LINE_MAX - 1] = 0;

  uint8_t mods[4]; uint8_t nMods = 0;
  bool pending = false;

  char *tok = strtok(buf, " ");
  while (tok) {
    uint8_t usage = tokenToUsage(tok);
    if (usage == 0) { Serial.print(F("ERR BADTOKEN ")); Serial.println(tok); return; }
    bool isMod = (usage >= U_LCTRL);
    if (isMod) {
      if (nMods < 4) mods[nMods++] = usage;
      Keyboard.press(modifierToArduino(usage));
      emitEvent(F("keydown"), usage);
      pending = true;
    } else {
      tapUsage(usage, false, 0);
      // release held modifiers after the non-modifier key
      while (nMods) {
        Keyboard.release(modifierToArduino(mods[--nMods]));
        emitEvent(F("keyup"), mods[nMods]);
      }
      pending = false;
    }
    tok = strtok(NULL, " ");
  }
  if (pending) { // trailing lone modifiers: tap-and-release them
    while (nMods) {
      Keyboard.release(modifierToArduino(mods[--nMods]));
      emitEvent(F("keyup"), mods[nMods]);
    }
  }
}

// ---------------- command handling ----------------

void loadRigId() {
  if (EEPROM.read(EEPROM_ADDR) != EEPROM_MAGIC) return;
  uint8_t len = EEPROM.read(EEPROM_ADDR + 1);
  if (len == 0 || len > 32) return;
  for (uint8_t i = 0; i < len; i++) rigId[i] = EEPROM.read(EEPROM_ADDR + 2 + i);
  rigId[len] = 0;
}

void saveRigId(const char *id) {
  uint8_t len = strlen(id);
  EEPROM.update(EEPROM_ADDR, EEPROM_MAGIC);
  EEPROM.update(EEPROM_ADDR + 1, len);
  for (uint8_t i = 0; i < len; i++) EEPROM.update(EEPROM_ADDR + 2 + i, id[i]);
  strncpy(rigId, id, 32); rigId[32] = 0;
}

void copyArg(char *dst, size_t cap, const char *arg) {
  strncpy(dst, arg, cap - 1);
  dst[cap - 1] = 0;
}

void handleCommand(char *line) {
  // split first word
  char *space = strchr(line, ' ');
  char *arg = NULL;
  if (space) { *space = 0; arg = space + 1; }

  if (!strcasecmp(line, "PING")) { Serial.println(F("PONG")); }
  else if (!strcasecmp(line, "ID")) {
    if (!arg || !arg[0]) { Serial.println(F("ERR ID NEEDS VALUE")); return; }
    saveRigId(arg);
    Serial.print(F("OK ID ")); Serial.println(rigId);
  }
  else if (!strcasecmp(line, "SESSION")) {
    if (!arg || !arg[0]) { Serial.println(F("ERR SESSION NEEDS VALUE")); return; }
    copyArg(sessionId, sizeof(sessionId), arg);
    Serial.print(F("OK SESSION ")); Serial.println(sessionId);
  }
  else if (!strcasecmp(line, "PREFIX")) {
    copyArg(prefixTokens, sizeof(prefixTokens), arg ? arg : "");
    Serial.print(F("OK PREFIX ")); Serial.println(prefixTokens);
  }
  else if (!strcasecmp(line, "SUFFIX")) {
    copyArg(suffixTokens, sizeof(suffixTokens), arg ? arg : "");
    Serial.print(F("OK SUFFIX ")); Serial.println(suffixTokens);
  }
  else if (!strcasecmp(line, "CPS")) {
    int v = arg ? atoi(arg) : 0;
    if (v < 1 || v > 200) { Serial.println(F("ERR CPS RANGE 1..200")); return; }
    cps = (uint8_t)v;
    Serial.print(F("OK CPS ")); Serial.println(cps);
  }
  else if (!strcasecmp(line, "JITTER")) {
    int v = arg ? atoi(arg) : -1;
    if (v < 0 || v > 250) { Serial.println(F("ERR JITTER RANGE 0..250")); return; }
    jitterMs = (uint8_t)v;
    Serial.print(F("OK JITTER ")); Serial.println(jitterMs);
  }
  else if (!strcasecmp(line, "STATUS")) {
    Serial.print(F("ID "));      Serial.println(rigId);
    Serial.print(F("SESSION "));Serial.println(sessionId);
    Serial.print(F("PREFIX ")); Serial.println(prefixTokens);
    Serial.print(F("SUFFIX ")); Serial.println(suffixTokens);
    Serial.print(F("CPS "));    Serial.println(cps);
    Serial.print(F("JITTER ")); Serial.println(jitterMs);
  }
  else if (!strcasecmp(line, "TEST")) {
    if (!arg || !arg[0]) { Serial.println(F("ERR TEST NEEDS TEXT")); return; }
    Serial.println(F("OK REPLAY-START"));
    typeTokens(prefixTokens);
    typeText(arg, strlen(arg));
    typeTokens(suffixTokens);
    Serial.println(F("OK REPLAY-DONE"));
  }
  else if (!strcasecmp(line, "BEGIN")) {
    Serial.println(F("OK STREAMING"));  // host waits for this before chunks
    typeTokens(prefixTokens);
    streaming = true;
    chunkLen = 0;
  }
  else if (!strcasecmp(line, "ABORT")) {
    streaming = false;
    Keyboard.releaseAll();
    Serial.println(F("OK ABORTED"));
  }
  else {
    Serial.print(F("ERR UNKNOWN "));
    Serial.println(line);
  }
}

// ---------------- streaming chunk handler ----------------

void handleChunk() {
  chunkBuf[chunkLen] = 0;
  if (!strcmp(chunkBuf, "END")) {
    typeTokens(suffixTokens);
    streaming = false;
    Serial.println(F("OK DONE"));
  } else {
    typeText(chunkBuf, chunkLen);
    Serial.println(F("ACK"));
  }
  chunkLen = 0;
}

// ---------------- setup / loop ----------------

void setup() {
  Serial.begin(SERIAL_BAUD);
  Keyboard.begin();
  randomSeed(analogRead(0) ^ millis());
  loadRigId();
  Serial.print(F("RIG READY "));
  Serial.println(rigId);
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (streaming) {
      if (c == '\r') continue;                 // tolerate CRLF
      if (c == '\n') { handleChunk(); continue; }
      if (chunkLen < CHUNK_MAX - 1) chunkBuf[chunkLen++] = c;
      // else: silently drop overflow (host must keep chunks <= 47 bytes)
    } else {
      if (c == '\r') continue;
      if (c == '\n') {
        if (lineLen) { lineBuf[lineLen] = 0; handleCommand(lineBuf); }
        lineLen = 0;
      } else if (lineLen < RIG_LINE_MAX - 1) {
        lineBuf[lineLen++] = c;
      }
    }
  }
}
