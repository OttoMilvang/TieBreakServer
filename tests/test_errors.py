# -*- coding: utf-8 -*-
"""
Regression tests for the errors the engine raises.

The one that matters is GacruxNoLegalPairing: a field can run out of legal pairings on
input that is valid in every respect, and the caller has to be able to recognise that
state (C.04.3 art. 1.9.3) rather than read it as a crash.
"""
import pytest

import errors
import trf2json
from pairingdutch import pairing_dutch


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
    with pytest.raises(errors.GacruxNoLegalPairing) as excinfo:
        pair_round(exhausted_round_robin(), 4)

    # Not "RuntimeError: No active exception to reraise", which is what a bare raise
    # outside an except block gives, and which says nothing about the tournament.
    assert "No active exception" not in str(excinfo.value)
    assert str(excinfo.value) != ""


def test_no_legal_pairing_is_catchable_as_a_gacrux_error():
    with pytest.raises(errors.GacruxError):
        pair_round(exhausted_round_robin(), 4)


def test_no_legal_pairing_is_not_an_invariant_violation():
    # A caller has to be able to tell a tournament state apart from a bug in the engine.
    assert not issubclass(errors.GacruxNoLegalPairing, errors.GacruxInvariantError)
    assert not issubclass(errors.GacruxNoLegalPairing, errors.GacruxInputError)
    for cls in [errors.GacruxNoLegalPairing, errors.GacruxInputError, errors.GacruxInvariantError]:
        assert issubclass(cls, errors.GacruxError)


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
