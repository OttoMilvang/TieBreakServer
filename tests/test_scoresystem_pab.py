# -*- coding: utf-8 -*-
"""
Regression tests for the value of an unplayed game in the score system.

Record 162 states the score system in points: the points of a win, of a draw, of a loss,
and the points of the unplayed games -- among them P, the pairing-allocated bye. The
scoring points system is a decision of the organiser, and the value of the PAB is
another one; TRF-2026 lets record 162 state both, and neither constrains the other.

The reader holds an unplayed game as the result it is worth -- "P": "W" says a PAB is
worth what a win is worth -- and reads the points of record 162 back into a result to do
so. A PAB whose points are the points of no result cannot be read back that way, and is
held as its points.
"""
import decimal

import trf2json
from tiebreak import tiebreak


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


def three_one_zero(pab):
    # Five players and two rounds, scored 3 / 1 / 0, with the pairing-allocated bye worth
    # what the caller says. The odd player out gets the bye in both rounds, and reports
    # twice the value of the bye in his 001 record.
    points = decimal.Decimal(pab) * 2
    lines = ["012 Three one zero", "042 2026-03-01", "XXR 2",
             "162  W 3.0    D 1.0    L 0.0    P%4s" % pab]
    lines.append(player_line(1, "One, Player", 2400, "6.0", [(2, "w", "1"), (3, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.0", [(1, "b", "0"), (4, "w", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "3.0", [(4, "b", "1"), (1, "b", "0")]))
    lines.append(player_line(4, "Four, Player", 2100, "3.0", [(3, "w", "0"), (2, "b", "1")]))
    lines.append(player_line(5, "Five, Player", 2000, "%.1f" % points, [(0, "-", "U"), (0, "-", "U")]))
    return lines


def parse(lines):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def points_of(chessfile):
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    result = tiebreak(tournament, 2, params).compute_tiebreaks(tournament, params)
    return {competitor["cid"]: competitor["tiebreakScore"][0] for competitor in result["competitors"]}


def test_pab_worth_half_a_point_in_a_three_one_zero_system():
    # A win is 3, a draw is 1, a loss is 0 -- and the bye is half a point, which is the
    # value of no result at all. Reading the points back into a result is what cannot be
    # done here, and it used to raise "KeyError: Decimal('0.5')" from the score system.
    chessfile = parse(three_one_zero("0.5"))
    scoresystem = chessfile.get_tournament(1)["scoreSystem"]["game"]

    assert chessfile.get_status() == 0
    assert scoresystem["P"] == decimal.Decimal("0.5")
    # The score system resolves, and the player who sat out both rounds has the two byes
    # the file says he has -- not a win, and not a draw.
    assert points_of(chessfile)[5] == decimal.Decimal("1.0")


def test_pab_worth_a_win_is_still_held_as_a_win():
    # The bye is worth 3.0, which is what a win is worth, so it is a win: the value the
    # record states is read back into the result, as it always was.
    chessfile = parse(three_one_zero("3.0"))
    scoresystem = chessfile.get_tournament(1)["scoreSystem"]["game"]

    assert chessfile.get_status() == 0
    assert scoresystem["P"] == "W"
    assert points_of(chessfile)[5] == decimal.Decimal("6.0")
