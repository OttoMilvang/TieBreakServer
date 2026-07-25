# -*- coding: utf-8 -*-
"""
Regression test for the bare ``raise`` on an unpairable position in get_category().

get_category() ends with ``if len(edges) == 0: raise`` -- a bare raise outside any
except block, which does not re-raise anything: it raises "RuntimeError: No active
exception to reraise", discarding whatever the real condition was. This is reachable
on a legal but degenerate tournament: a near-round-robin tail where a score bracket
has run out of legal opponents entirely (FIDE C.04.3 art. 1.9.3). Through
pairingchecker this used to surface as the opaque status 510 "Program error".

The fixture here is a fresh six-player full round robin, five rounds played, so by
round six every pair in the field has already met -- deliberately a different shape
from the four-player fixture in test_errors.py, so this test does not just repeat
that one under a new name; it independently pins the same commit's fix.
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


# Circle-method round robin schedule for six players, rounds 1-5 -- every pair meets
# exactly once, so round 6 has no legal pairing left for anyone.
SCHEDULE = {
    1: [(1, 6), (2, 5), (3, 4)],
    2: [(1, 5), (6, 4), (2, 3)],
    3: [(1, 4), (5, 3), (6, 2)],
    4: [(1, 3), (4, 2), (5, 6)],
    5: [(1, 2), (3, 6), (4, 5)],
}


def full_round_robin_of_six():
    games = {i: [] for i in range(1, 7)}
    points = {i: 0 for i in range(1, 7)}
    for rnd, pairs in SCHEDULE.items():
        for index, (a, b) in enumerate(pairs):
            (white_colour, black_colour) = ("w", "b") if (rnd + index) % 2 == 0 else ("b", "w")
            (result_a, result_b) = ("1", "0") if a < b else ("0", "1")
            games[a].append((b, white_colour, result_a))
            games[b].append((a, black_colour, result_b))
            points[a if result_a == "1" else b] += 1

    lines = ["012 Full round robin, six players, exhausted", "042 2026-03-01", "XXR 6"]
    for i in range(1, 7):
        lines.append(player_line(i, f"Player {i}, One", 2400 - 10 * i, f"{points[i]}.0", games[i]))
    return lines


def pair_round(lines, rnd):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, rnd, params)
    return engine.compute_pairing(False, 0)


def test_round_six_of_an_exhausted_round_robin_is_reported_cleanly():
    with pytest.raises(errors.GacruxNoLegalPairing) as excinfo:
        pair_round(full_round_robin_of_six(), 6)

    # Not "RuntimeError: No active exception to reraise", which is what the bare
    # raise gave and which says nothing about the tournament being unpairable.
    assert "No active exception" not in str(excinfo.value)
    assert str(excinfo.value) != ""


def test_round_one_of_the_same_field_still_pairs():
    # Before any games are played the same six players are trivially pairable, and
    # must not raise -- this fixture's exhaustion is specific to round six, not an
    # artifact of the fixture shape itself.
    lines = ["012 Full round robin, no rounds played yet", "042 2026-03-01", "XXR 6"]
    for i in range(1, 7):
        lines.append(player_line(i, f"Player {i}, One", 2400 - 10 * i, "0.0", []))

    brackets = pair_round(lines, 1)
    pairs = [(pair["w"], pair["b"]) for bracket in brackets for pair in bracket.get("pairs", [])]
    assert len(pairs) == 3
    seated = [cid for pair in pairs for cid in pair]
    assert sorted(seated) == list(range(1, 7))
