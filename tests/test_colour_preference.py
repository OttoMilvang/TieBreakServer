# -*- coding: utf-8 -*-
"""
C.04.3 art. 1.7.1, the absolute colour preference.

    "An absolute colour preference occurs when a player's colour difference is greater than
     +1 or less than -1, or when a player had the same colour in the two latest rounds they
     played. The preference is for White when the colour difference is less than -1 or when
     the last two games were played with Black. The preference is for Black when the colour
     difference is greater than +1, or when the last two games were played with White."

The second clause of each sentence -- "when the last two games were played with Black" -- is
unconditional on the colour difference. Gating it at cod <= 0 (resp. cod >= 0) dropped the
|cod| == 1 cases, which then fell through to art. 1.7.2 and came back as a STRONG preference
for the OPPOSITE colour. That is what these tests hold the engine to.

There is one place where art. 1.7.1 asserts BOTH preferences at once -- a colour difference of
+2 or more together with two Blacks in the last two played rounds -- and the article does not
say which sentence wins. The engine resolves those by the colour difference. TestArticleConflict
pins that choice so it cannot drift silently, and does not claim it is the only reading.
"""
import pytest
from gacrux.crosstabledutch import crosstable_dutch


def preference(csq):
    """The engine's colour preference for a player whose played colours were *csq*."""
    cod = csq.count("w") - csq.count("b")
    return crosstable_dutch.color_preference(None, cod, csq)


class TestTheLastTwoGamesClauseIsUnconditional:
    """art. 1.7.1, second clause: the cases a colour-difference gate used to drop."""

    def test_two_blacks_with_colour_difference_plus_one_is_absolute_white(self):
        # wwwbb: cod = +1, so "greater than +1" does NOT fire and the Black sentence is silent.
        # Only "the last two games were played with Black" applies -> absolute White.
        # Returned "b1" (a STRONG preference for BLACK -- the opposite colour) before the fix.
        assert preference("wwwbb") == "w2"

    def test_two_whites_with_colour_difference_minus_one_is_absolute_black(self):
        # bbbww: the mirror. cod = -1, so "less than -1" does not fire.
        assert preference("bbbww") == "b2"

    def test_two_blacks_with_a_balanced_colour_difference_is_absolute_white(self):
        assert preference("wwbb") == "w2"

    def test_two_whites_with_a_balanced_colour_difference_is_absolute_black(self):
        assert preference("bbww") == "b2"

    def test_two_blacks_with_colour_difference_minus_one_is_absolute_white(self):
        # Both sentences agree here; it is the case the old gate did handle.
        assert preference("wbbb") == "w2"


class TestTheColourDifferenceClauseIsUnaffected:
    """art. 1.7.1, first clause -- and arts. 1.7.2 to 1.7.4, which must not move."""

    @pytest.mark.parametrize("csq", ["wwwb", "wwwwbb"[:4]])
    def test_a_colour_difference_above_plus_one_is_absolute_black(self, csq):
        assert preference(csq) == "b2"

    def test_a_colour_difference_below_minus_one_is_absolute_white(self):
        assert preference("bbbw") == "w2"

    def test_a_colour_difference_of_plus_one_alone_is_a_strong_black_preference(self):
        # art. 1.7.2. wbw: cod = +1, last two are "bw" -- not the same colour, so 1.7.1 is silent.
        assert preference("wbw") == "b1"

    def test_a_colour_difference_of_minus_one_alone_is_a_strong_white_preference(self):
        assert preference("bwb") == "w1"

    def test_a_balanced_player_alternates(self):
        # art. 1.7.3, the mild preference.
        assert preference("wb") == "w0"
        assert preference("bw") == "b0"

    def test_a_player_who_has_not_played_has_no_preference(self):
        # art. 1.7.4.
        assert preference("") == "nc"


class TestArticleConflict:
    """art. 1.7.1 asserts both preferences at once here; the engine picks the colour difference.

    "The preference is for Black when the colour difference is greater than +1" AND "The
    preference is for White ... when the last two games were played with Black" both hold for
    a player on wwwwbb (cod = +2, last two Black). The article does not rank its own sentences.
    These tests pin the engine's choice -- the colour difference -- so that it is a decision on
    the record rather than an accident, and so a change to it cannot pass unnoticed.
    """

    def test_two_blacks_cannot_overturn_a_colour_difference_of_plus_two(self):
        assert preference("wwwwbb") == "b2"

    def test_two_whites_cannot_overturn_a_colour_difference_of_minus_two(self):
        assert preference("bbbbww") == "w2"
