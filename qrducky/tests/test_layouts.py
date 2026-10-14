"""Layout table and simulation ground-truth tests (W2.2)."""

import pytest

from qrducky import (LAYOUTS, PORTABLE_LETTERS, naive_us_keystrokes,
                    native_keystrokes, simulate, LayoutError)

class TestKnownRemaps:
    """The classic HID-injection layout traps, verified against our tables."""

    def test_de_y_z_swapped(self):
        assert simulate(naive_us_keystrokes("y"), "DE") == "z"
        assert simulate(naive_us_keystrokes("z"), "DE") == "y"

    def test_fr_a_q_swapped(self):
        assert simulate(naive_us_keystrokes("a"), "FR") == "q"
        assert simulate(naive_us_keystrokes("q"), "FR") == "a"

    def test_fr_z_w_swapped(self):
        assert simulate(naive_us_keystrokes("z"), "FR") == "w"
        assert simulate(naive_us_keystrokes("w"), "FR") == "z"

    def test_fr_m_key_absent(self):
        # US-m position has no key on AZERTY -> nothing is typed.
        assert simulate(naive_us_keystrokes("m"), "FR") == "\u2205"

    def test_fr_digits_shifted_required(self):
        # FR number row unshifted is & é " ' ( - è _ ç à.
        assert simulate(naive_us_keystrokes("5"), "FR") == "("
        assert simulate(naive_us_keystrokes("0"), "FR") == "à"
        # Native FR keystrokes for digits use SHIFT -> digits appear.
        assert simulate(native_keystrokes("5", "FR"), "FR") == "5"

    def test_de_equals_is_acute_dead(self):
        # US '=' position is the ´ dead key on DE: the standard reason
        # base64 breaks on German targets.
        assert simulate(naive_us_keystrokes("="), "DE") == "acute(dead)"
        # Native DE '=' is Shift+0.
        assert simulate(native_keystrokes("=", "DE"), "DE") == "="

    def test_de_slash_is_hyphen(self):
        # US-/ position is the QWERTZ hyphen key: "/" types "-".
        assert simulate(naive_us_keystrokes("/"), "DE") == "-"

class TestPortability:
    def test_portable_letters_survive_all_layouts(self):
        for ch in PORTABLE_LETTERS:
            ks = naive_us_keystrokes(ch)
            for layout in ("US", "DE", "FR"):
                assert simulate(ks, layout) == ch, (ch, layout)

    def test_excluded_letters_are_not_portable(self):
        for ch in "AMQWYZ":
            ks = naive_us_keystrokes(ch)
            broken = [L for L in ("US", "DE", "FR")
                      if simulate(ks, L) != ch]
            assert broken, f"{ch} should be layout-broken but was portable"

    def test_native_keystrokes_reproduce_text_on_own_layout(self):
        for ch in ("a", "Z", "5", "=", "/", ":", ";", "?"):
            for layout in ("US", "DE", "FR"):
                ks = native_keystrokes(ch, layout)
                assert simulate(ks, layout) == ch, (layout, ch)

    def test_de_slash_is_minus(self):
        # US-/ position is the QWERTZ hyphen key: "/" types "-".
        assert simulate(naive_us_keystrokes("/"), "DE") == "-"
        assert simulate(native_keystrokes("/", "DE"), "DE") == "/"


    def test_native_keystroke_rejects_untypeable_char(self):
        # On FR there is no key at the US-m position, but 'm' IS typeable via
        # the AZERTY m key — the reverse map must find it.
        assert simulate(native_keystrokes("m", "FR"), "FR") == "m"
        with pytest.raises(LayoutError):
            native_keystrokes("\t", "US")  # tab has no entry in our tables

    def test_french_m_positional_dead_key(self):
        # US-m usage (0x10) is absent on FR — the simulated stream drops it.
        assert simulate(naive_us_keystrokes("m"), "FR") != "m"

class TestTableIntegrity:
    def test_us_letters_complete(self):
        for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
            assert LAYOUTS["US"][0x04 + i][0] == ch

    def test_de_is_qwertz(self):
        # Top row reads q w e r t z: US-y position produces z.
        assert LAYOUTS["DE"][0x1C][0] == "z"

    def test_fr_is_azerty(self):
        assert LAYOUTS["FR"][0x14][0] == "a"  # A at US-q position
        assert LAYOUTS["FR"][0x1A][0] == "z"  # Z at US-w position
        assert LAYOUTS["FR"][0x04][0] == "q"  # Q at US-a position
        assert LAYOUTS["FR"][0x1D][0] == "w"  # W at US-z position
