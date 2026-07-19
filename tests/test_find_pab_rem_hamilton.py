# -*- coding: utf-8 -*-
"""
Regression test for find_pab() reading hamilton[-1]["rem_hamilton"] directly.

compute_hamilton() builds one dict per score level and only fills in "rem_hamilton"
(among other keys) for levels it actually visits while walking the sorted edge list.
If the highest score level has no edge touching it at all -- every competitor there
already has zero legal opponents anywhere in the field -- the loop never reaches that
level before it hits the levels-sentinel and breaks, so hamilton[-1] is left as the
empty dict `{}` from initialisation. find_pab() read
``hamilton[-1]["rem_hamilton"] >= 0`` directly, a guaranteed KeyError, where every
other reference to "rem_hamilton" in this file uses ``.get("rem_hamilton", -1)``.

The fixture: six players, "A" plays and beats a different one of the other five
(B..F) in each of five rounds, so entering round six A has met every other
competitor in the field and has zero legal opponents left -- A is alone at the top
score bracket with no edge reaching it. B..F never play each other, so C(5,2) = 10
edges remain among them; find_pab()'s ``len(edges) > 0`` guard is satisfied by those,
so it does reach the buggy line. This is a legal, if unfortunate, tournament state
(FIDE C.04.3 art. 1.9.3): A genuinely cannot be paired, which the fixed engine now
reports as GacruxNoLegalPairing instead of crashing on an internal KeyError.
"""
import pytest

import errors
import trf2json
from pairingdutch import pairing_dutch


def header(startno, name, rating, points):
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
    return line


def player_line_sparse(startno, name, rating, points, games_by_round, maxround):
    # Unlike the fixed-width helper used elsewhere in this suite, this one can leave
    # a round column blank (8 spaces) for a round the competitor did not play at all,
    # rather than omitting trailing rounds wholesale -- needed here because A plays
    # every round but B..F each play only one specific round out of five.
    line = header(startno, name, rating, points)
    parts = []
    for round_no in range(1, maxround + 1):
        if round_no in games_by_round:
            parts.append("%4d %s %s" % games_by_round[round_no])
        else:
            parts.append(" " * 8)
    return line + "  ".join(parts)


def isolated_leader(maxround=5):
    names = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F"}
    lines = ["012 Isolated leader test", "042 2026-03-01", "XXR 6"]

    a_games = {r: (r + 1, "w", "1") for r in range(1, maxround + 1)}
    lines.append(player_line_sparse(1, "A, Player", 2000, "5.0", a_games, maxround))

    for opponent in range(2, 7):
        round_no = opponent - 1
        games = {round_no: (1, "b", "0")}
        lines.append(player_line_sparse(opponent, f"{names[opponent]}, Player", 1900, "0.0", games, maxround))

    return lines


def pair_round(lines, rnd):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, rnd, params)
    return engine.compute_pairing(False, 0)


def test_isolated_leader_fixture_has_edges_but_none_reach_the_top_level():
    # Sanity-check the fixture itself: A has genuinely played everyone (five games,
    # one per round, one per opponent), so no edge in the round-6 field can touch A.
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(isolated_leader()), True)
    tournament = chessfile.get_tournament(1)
    a_games = [g for g in tournament["gameList"] if g["white"] == 1 or g["black"] == 1]
    assert len(a_games) == 5
    assert {g["white"] + g["black"] - 1 for g in a_games} == {2, 3, 4, 5, 6}


def test_isolated_leader_is_reported_as_no_legal_pairing_not_a_keyerror():
    with pytest.raises(errors.GacruxNoLegalPairing) as excinfo:
        pair_round(isolated_leader(), 6)

    # Not "KeyError: 'rem_hamilton'", which is what the direct (unguarded) dict read
    # gives when the top score level's hamilton entry was never populated.
    assert "rem_hamilton" not in str(excinfo.value)
