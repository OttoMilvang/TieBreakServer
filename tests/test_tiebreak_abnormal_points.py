# -*- coding: utf-8 -*-
"""
Record 299 reaching the tie-break engine.

TRF-2026 record 299 carries two things the tie-break has to read. A record with
a blank type is a penalty or a bonus: the points in the standings "are modified
by a positive or negative number (whatever the reason)", and for an individual
tournament that number is the points field in columns 14-17. A record with a
type names an unplayed-game outcome and writes it onto the game itself.

Both reached the tie-break as a fault rather than as a number, which is what
these pin: the engine may decide such a file is wrong and say so, but it may
not raise out of the middle of the computation.
"""
import decimal

from gacrux import tiebreak
from gacrux import trf2json


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


def abnormal_line(aat, matchpoints, gamepoints, rnd, competitors):
    # Record 299 at the columns TRF-2026 gives it: the type in column 5, the
    # match points in 8-11, the game points (or, for an individual, the points)
    # in 14-17, the round in 20-22 and the pairing numbers from 24-27 on.
    line = list(" " * 23)
    line[0:3] = "299"
    line[4] = aat
    line[7:11] = "%4s" % matchpoints
    line[13:17] = "%4s" % gamepoints
    line[19:22] = "%03d" % rnd
    return "".join(line) + " ".join(["%04d" % competitor for competitor in competitors])


def one_played_round(extra):
    """Two rated players, one game actually played, plus *extra* records."""
    return [
        "012 Abnormal assignment points",
        "042 2026/03/01",
        "062 2",
        "072 2",
        "102 1",
        player_line(1, "Player One", 2000, "1.0", [(2, "w", "1")]),
        player_line(2, "Player Two", 1900, "0.0", [(1, "b", "0")]),
    ] + extra


def compute(lines, tiebreaks):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": tiebreaks, "check": False, "unrated": None,
              "pre_determined": True, "swiss": False}
    engine = tiebreak.tiebreak(tournament, -1, params)
    result = engine.compute_tiebreaks(tournament, params)
    return dict([(cmp["cid"], str(cmp["tiebreakScore"][0])) for cmp in result["competitors"]])


def test_a_penalty_reaches_the_standings_of_an_individual_tournament():
    """A blank-type record 299 is read, and the points move by what it says.

    update_abnormal_list files the adjustment on the competitor under the keys
    "mpoints" and "gpoints", which are the team names for the two point types.
    It has already worked out the names this tournament uses -- an individual
    has one point type, "points" -- and the branch above it writes a game with
    exactly those names, but this branch spelled them out instead.
    compute_points then looked the adjustment up under the name the tournament
    does use and raised KeyError: 'points' before reaching any tie-break. So a
    penalty was not something the engine scored differently; it was a file the
    engine could not read at all.
    """
    assert compute(one_played_round([]), ["PTS"]) == {1: "1.0", 2: "0.0"}

    penalised = one_played_round([abnormal_line(" ", "", "-0.5", 1, [1])])

    assert compute(penalised, ["PTS"]) == {1: "0.5", 2: "0.0"}


def test_an_unplayed_result_the_rating_table_does_not_define_is_scored():
    """A result letter the rating table has no entry for is still a number.

    get_score walks its table until the letter resolves to a value. A letter
    the table does not carry at all skips the loop and is returned unchanged,
    so the caller is handed the letter "H" where it expects a score, and
    ComputeDeltaR raises TypeError: unsupported operand type(s) for -: 'str'
    and 'decimal.Decimal'.

    The table defines W, D, L and Z and maps the two unplayed results it knows,
    A and U, onto Z. It did not define the other three unplayed results, F, H
    and P, each of which record 299 can write onto a game.

    What such a record should do to the score itself is a separate question and
    this does not pin one; it pins only that the tournament is scored rather
    than raising from the middle of the computation.
    """
    lines = one_played_round([abnormal_line("H", "", " 0.5", 1, [1])])

    scores = compute(lines, ["PTS"])

    assert set(scores) == {1, 2}
    for value in scores.values():
        decimal.Decimal(value)          # a score, not a result letter
