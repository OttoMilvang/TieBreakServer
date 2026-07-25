# -*- coding: utf-8 -*-
"""
Regression tests for the colour tie-breaks COD / COP / CSQ.

A competitor who gets the same colour in every game accumulates a colour difference
outside the range of the colour-preference table used by tiebreak.compute_score().
That must not crash the score preparation.
"""
import pytest

import tiebreak
import trf2json


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


def compute(lines, tiebreaks):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": tiebreaks, "check": False, "unrated": None}
    tb = tiebreak.tiebreak(tournament, -1, params)
    result = tb.compute_tiebreaks(tournament, params)
    return dict([(cmp["cid"], cmp["tiebreakScore"]) for cmp in result["competitors"]])


def one_colour_all_the_way(rounds):
    # Player 1 is white against player 2 in every round, player 3 is white against
    # player 4 in every round. 1 and 3 end on +rounds, 2 and 4 on -rounds.
    lines = ["012 Same colour every round", "042 2026-03-01", "XXR %d" % rounds]
    lines.append(player_line(1, "One, Player", 2000, "%.1f" % rounds, [(2, "w", "1")] * rounds))
    lines.append(player_line(2, "Two, Player", 1900, "0.0", [(1, "b", "0")] * rounds))
    lines.append(player_line(3, "Three, Player", 1800, "%.1f" % rounds, [(4, "w", "1")] * rounds))
    lines.append(player_line(4, "Four, Player", 1700, "0.0", [(3, "b", "0")] * rounds))
    return lines


@pytest.mark.parametrize("rounds", [9, 10, 15])
def test_same_colour_in_every_game(rounds):
    # COD is the colour difference (white games minus black games) and CSQ the colour
    # sequence; both are well defined however lopsided the colours are. COP is derived
    # from COD and must saturate rather than run off the end of its table.
    scores = compute(one_colour_all_the_way(rounds), ["COD", "COP", "CSQ"])

    assert scores[1][0] == rounds
    assert scores[2][0] == -rounds
    assert scores[1][2] == "w" * rounds
    assert scores[2][2] == "b" * rounds
    assert scores[1][1][0] in "wb"
    assert scores[2][1][0] in "wb"


def test_normal_colours_are_unchanged():
    # Colour differences inside the table must keep the values they always had.
    lines = ["012 Normal colours", "042 2026-03-01", "XXR 3"]
    lines.append(player_line(1, "One, Player", 2000, "2.0", [(2, "w", "1"), (3, "b", "0"), (4, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, "1.0", [(1, "b", "0"), (4, "w", "1"), (3, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 1800, "2.0", [(4, "w", "0"), (1, "w", "1"), (2, "w", "1")]))
    lines.append(player_line(4, "Four, Player", 1700, "1.0", [(3, "b", "1"), (2, "b", "0"), (1, "b", "0")]))
    scores = compute(lines, ["COD", "COP", "CSQ"])

    assert scores[1] == [1, "b1", "wbw"]
    assert scores[2] == [-1, "w1", "bwb"]
    assert scores[3] == [3, "b2", "www"]
    assert scores[4] == [-3, "w2", "bbb"]
