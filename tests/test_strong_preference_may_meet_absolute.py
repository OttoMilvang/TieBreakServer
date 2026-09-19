# -*- coding: utf-8 -*-
"""A strong colour preference is not an absolute one, in update_canmeet().

crosstabledutch.py's update_canmeet() carried a second colour-based
restriction beyond FIDE C.04.3 art. 2.1.3 [C3] (two players who both hold an
ABSOLUTE same-colour preference, art. 1.7.1, may not be paired together):

    if a["cod"] * b["cod"] >= 4 and (not a["top"]) and (not b["top"]):
        canmeet = False

"cod" is the colour difference of C.04.3 art. 1.6, "the number of games played
with White minus the number of games played with Black"; a value of +-1 is
only a STRONG preference (art. 1.7.2), not an absolute one. The removed test
forbade a pairing whenever the *product* of two players' colour differences
reached 4 or worse -- which a strong preference (|cod| = 1) paired against a
large one (|cod| = 4) satisfies just as well as two absolute preferences would
(|cod| = 2 each). That treated the strong side as if its preference were
absolute, which art. 1.7.2 does not say, and could delete the only legal edge
a bracket had.

The fixture below has 87 players and round 11 to pair, a position where
this specific pair of colour differences is what decides the
round: players 83 (cod -1, strong White preference) and 84 (cod -4, absolute
White preference) must be allowed to meet, because 83's preference is not
absolute. With the extra test in place the engine pairs 73-83 and downfloats
84 onto 79 instead -- leaving the bracket's own moved-down player (79, a full
scorelevel above the rest of the bracket) to carry the downfloat rather than
83, a same-level resident. That is a worse choice by the engine's own
criterion, art. 2.4.2 [C7] (minimise the scores, taken in descending order,
of the downfloaters): downfloating 83 costs 0 scorelevels, downfloating 79
costs 1.

The round has no pairing-allocated bye; what is under test is update_canmeet()
alone, hence the file's name.
"""
import os

from gacrux import trf2json
from gacrux.pairingdutch import pairing_dutch

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "absolute_vs_strong_colour_preference.trf"
)


def pair_round_11():
    with open(FIXTURE, encoding="latin1") as handle:
        chessfile = trf2json.trf2json()
        chessfile.parse_file(handle.read(), False)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, 11, params)
    brackets = engine.compute_pairing(False, 0)
    pairs = set()
    for bracket in brackets:
        for pair in bracket["pairs"]:
            pairs.add(frozenset((pair["w"], pair["b"])))
    return pairs


def test_a_strong_colour_preference_may_meet_an_absolute_one():
    """Players 83 (strong White, cod -1) and 84 (absolute White, cod -4) must
    be a legal pair: art. 2.1.3 [C3] only forbids two ABSOLUTE preferences."""
    pairs = pair_round_11()
    assert frozenset((83, 84)) in pairs


def test_the_brackets_own_moved_down_player_is_not_forced_to_downfloat_instead():
    """The consequence: with 83-84 forbidden by the product test, the engine
    downfloats 79 (the bracket's own moved-down player, a full scorelevel
    above its residents) rather than 83 (a same-level resident) -- the
    opposite of what art. 2.4.2 [C7] prefers between two otherwise-tied
    candidates."""
    pairs = pair_round_11()
    assert frozenset((73, 79)) in pairs
    assert frozenset((73, 83)) not in pairs
