# -*- coding: utf-8 -*-
"""
Regression tests for the errors the engine raises.

The one that matters is GacruxNoLegalPairing: a field can run out of legal pairings on
input that is valid in every respect, and the caller has to be able to recognise that
state (C.04.3 art. 1.9.3) rather than read it as a crash.
"""
import pytest

from gacrux import gacruxexeptions
from gacrux import trf2json
from gacrux.pairingdutch import pairing_dutch


def player_line(startno, name, rating, points, games):
    line = "001 "
    line += "%4d " % startno                 # start number
    line += "m    "                          # sex + title
    line += "%-33s " % name                  # name
    line += "%4d " % rating                  # rating
    line += "NOR "                           # federation
    line += "%11d " % 0                      # fide id
    line += "1990/01/01 "                    # birth date
    line += "%4s " % points                  # points
    line += "%4d  " % startno                # rank
    return line + "  ".join(["%4d %s %s" % game for game in games])


def exhausted_round_robin():
    # Four competitors who have met each other once in three rounds. Round four cannot be
    # paired: every admissible opponent is used up.
    lines = ["012 Exhausted round robin", "042 2026-03-01", "XXR 4"]
    lines.append(player_line(1, "One, Player", 2400, "2.0",
                             [(2, "w", "1"), (3, "b", "0"), (4, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 2300, "1.0",
                             [(1, "b", "0"), (4, "w", "1"), (3, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "3.0",
                             [(4, "w", "1"), (1, "w", "1"), (2, "w", "1")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.0",
                             [(3, "b", "0"), (2, "b", "0"), (1, "b", "0")]))
    return lines


def pair_round(lines, rnd):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, rnd, params)
    return engine.compute_pairing(False, 0)


def test_no_legal_pairing_is_reported_as_such():
    with pytest.raises(gacruxexeptions.GacruxNoLegalPairing) as excinfo:
        pair_round(exhausted_round_robin(), 4)

    # Not "RuntimeError: No active exception to reraise", which is what a bare raise
    # outside an except block gives, and which says nothing about the tournament.
    assert "No active exception" not in str(excinfo.value)
    assert str(excinfo.value) != ""


def test_no_legal_pairing_is_catchable_as_a_gacrux_error():
    with pytest.raises(gacruxexeptions.GacruxError):
        pair_round(exhausted_round_robin(), 4)


def test_no_legal_pairing_is_not_an_invariant_violation():
    # A caller has to be able to tell a tournament state apart from a bug in the engine.
    assert not issubclass(gacruxexeptions.GacruxNoLegalPairing, gacruxexeptions.GacruxInvariantError)
    assert not issubclass(gacruxexeptions.GacruxNoLegalPairing, gacruxexeptions.GacruxInputError)
    for cls in [gacruxexeptions.GacruxNoLegalPairing, gacruxexeptions.GacruxInputError, gacruxexeptions.GacruxInvariantError]:
        assert issubclass(cls, gacruxexeptions.GacruxError)


def test_a_pairable_round_still_pairs():
    # The same field one round earlier is pairable, and must not raise.
    lines = ["012 Round robin, two rounds played", "042 2026-03-01", "XXR 4"]
    lines.append(player_line(1, "One, Player", 2400, "1.0", [(2, "w", "1"), (3, "b", "0")]))
    lines.append(player_line(2, "Two, Player", 2300, "1.0", [(1, "b", "0"), (4, "w", "1")]))
    lines.append(player_line(3, "Three, Player", 2200, "2.0", [(4, "w", "1"), (1, "w", "1")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.0", [(3, "b", "0"), (2, "b", "0")]))

    brackets = pair_round(lines, 3)
    pairs = []
    for bracket in brackets:
        for pair in bracket.get("pairs", []):
            pairs.append((pair["w"], pair["b"]))
    assert sorted([sorted(pair) for pair in pairs]) == [[1, 4], [2, 3]]


def three_leaders_who_have_met_every_lower_player():
    # Eight players, five rounds. Players 1, 2 and 3 have each beaten all of 4 to 8, so in
    # round six they can only meet each other -- three players, one pair, one over -- and
    # the even field allows no pairing-allocated bye (C.04.3 art. 1.9.1). The lower five
    # have edges among themselves, so the top of the field is not edgeless: the engine
    # gets past its first exit and has to recognise this state in the Hamilton remainder.
    lines = ["012 Three leaders who have met every lower player", "042 2026-03-01", "XXR 7"]
    lines.append(player_line(1, "One, Player", 2390, "5.0",
                             [(4, "b", "1"), (5, "w", "1"), (6, "b", "1"), (7, "w", "1"), (8, "b", "1")]))
    lines.append(player_line(2, "Two, Player", 2380, "5.0",
                             [(5, "w", "1"), (6, "b", "1"), (7, "w", "1"), (8, "b", "1"), (4, "w", "1")]))
    lines.append(player_line(3, "Three, Player", 2370, "5.0",
                             [(6, "b", "1"), (7, "w", "1"), (8, "b", "1"), (4, "w", "1"), (5, "b", "1")]))
    lines.append(player_line(4, "Four, Player", 2360, "1.0",
                             [(1, "w", "0"), (8, "b", "="), (5, "w", "="), (3, "b", "0"), (2, "b", "0")]))
    lines.append(player_line(5, "Five, Player", 2350, "1.0",
                             [(2, "b", "0"), (1, "b", "0"), (4, "b", "="), (6, "b", "="), (3, "w", "0")]))
    lines.append(player_line(6, "Six, Player", 2340, "1.0",
                             [(3, "w", "0"), (2, "w", "0"), (1, "w", "0"), (5, "w", "="), (7, "w", "=")]))
    lines.append(player_line(7, "Seven, Player", 2330, "1.0",
                             [(8, "w", "="), (3, "b", "0"), (2, "b", "0"), (1, "b", "0"), (6, "b", "=")]))
    lines.append(player_line(8, "Eight, Player", 2320, "1.0",
                             [(7, "b", "="), (4, "w", "="), (3, "w", "0"), (2, "w", "0"), (1, "w", "0")]))
    return lines


def test_art_1_9_3_a_top_bracket_that_cannot_be_completed_raises_before_find_pab():
    """The third exit of compute_pairing: a Hamilton remainder the top bracket cannot close.

    compute_pairing recognises an incompletable round (C.04.3 art. 1.9.3) in three places.
    The first two -- no edge at all at the top, and a last bracket that will not pair --
    raise GacruxNoLegalPairing. The third, a top-level remainder whose maximum matching
    leaves players over, returned an empty round-pairing, which no caller could tell from
    a round with nothing to pair.

    The second assertion documents that this fixture reaches that third exit and not one
    of the other two: the top level of the Hamilton table records players left unpaired.
    """
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(three_leaders_who_have_met_every_lower_player()), True)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, 6, params)

    with pytest.raises(gacruxexeptions.GacruxNoLegalPairing) as excinfo:
        engine.compute_pairing(False, 0)

    assert engine.hamilton[-1]["rem_unpaired"] != 0
    assert "1.9.3" in str(excinfo.value)
    assert "2 competitors" in str(excinfo.value)
