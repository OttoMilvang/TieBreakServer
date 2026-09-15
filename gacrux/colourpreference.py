# -*- coding: utf-8 -*-
"""
The colour preference of C.04.3 art. 1.7, for an individual Swiss tournament.

One function, shared by the pairing engine (crosstable_dutch.color_preference, which the
Dutch pairing reads for every competitor) and the tie-break listing (the COP column of
tiebreak.compute_score). The two used to have an implementation each and disagreed: a
player on wwwbb was "w2" to the engine and "b2" to the listing. A tie-break listing that
contradicts the pairing engine about the same player is wrong in one of the two places,
so there is now one place.

The return is the colour, then the strength:
    "w2" / "b2" - an absolute colour preference, art. 1.7.1
    "w1" / "b1" - a strong colour preference, art. 1.7.2
    "w0" / "b0" - a mild colour preference, art. 1.7.3
    "nc"        - no colour preference, art. 1.7.4

The colour difference (cod) is C.04.3 art. 1.6, games played with White minus games played
with Black; the colour sequence (csq) is the colours of the games played, in order. Only
played games count in either (C.04.2 art. 3.4), and that is the caller's business: both
callers build cod and csq from played games with an opponent before asking.

The definitions are tested in the order the article writes them, so the first one that
fits a player is the one that holds.
"""


def color_preference(cod, csq):
    """The colour preference of a player with colour difference *cod* and history *csq*."""
    # C.04.3 art. 1.7.1: "The preference is for White when the colour difference is less
    # than -1 OR when the last two games were played with Black." The second clause is
    # unconditional on the colour difference. Gating it at cod <= 0 (resp. cod >= 0) drops
    # the |cod| == 1 cases, which then fall through to art. 1.7.2 and come back as a STRONG
    # preference for the OPPOSITE colour -- e.g. a player with the colour history wwwbb
    # (cod = +1, last two Black) has an absolute preference for White by 1.7.1, but was
    # returned "b1". Widening to cod <= 1 / cod >= -1 covers them.
    #
    # cod >= +2 with the last two games Black (and its mirror) is left resolving by the
    # colour difference, as before: there art. 1.7.1 asserts BOTH preferences, and the
    # article does not say which wins.
    if cod <= -2 or cod <= 1 and csq[-2:] == "bb":
        return "w2"
    elif cod >= 2 or cod >= -1 and csq[-2:] == "ww":
        return "b2"
    elif cod == -1:
        return "w1"
    elif cod == 1:
        return "b1"
    elif csq[-1:] == "b":
        return "w0"
    elif csq[-1:] == "w":
        return "b0"
    return "nc"
