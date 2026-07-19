# -*- coding: utf-8 -*-
"""
Regression tests for record 299, Abnormal Assignment points.

TRF-2026 gives record 299 five fields: the type of the assignment in column 5, the match
points in 8-11, the game points in 14-17, the round in 20-22, and the pairing numbers it
applies to in 24-27, 29-32, and so on. A record that leaves the round and the pairing
numbers out applies to every round and every competitor; that is the form the
specification writes out in its own note.
"""
import decimal

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


def abnormal_line(aat, matchpoints, gamepoints, rnd, competitors):
    # Record 299, written at the columns TRF-2026 gives it:
    #     1 - 3    record identifier
    #     5        type of abnormal assignment (AAT)
    #     8 - 11   match points
    #    14 - 17   game points (teams) or points (individuals)
    #    20 - 22   round number
    #    24 - 27   1st pairing number, then 29 - 32, 34 - 37, ...
    line = list(" " * 23)
    line[0:3] = "299"
    line[4] = aat
    line[7:11] = "%4s" % matchpoints
    line[13:17] = "%4s" % gamepoints
    line[19:22] = "%03d" % rnd
    return "".join(line) + " ".join(["%04d" % competitor for competitor in competitors])


def points_only_line(aat, matchpoints, gamepoints):
    # The form of record 299 the specification writes out in its own note. The record
    # stops after the game points: no round field and no pairing numbers, which means
    # every round and every competitor.
    #     ### T   MMMM     GGGG
    #     299 +    2.0      2.5
    line = list(" " * 17)
    line[0:3] = "299"
    line[4] = aat
    line[7:11] = "%4s" % matchpoints
    line[13:17] = "%4s" % gamepoints
    return "".join(line)


def two_rounds(abnormal):
    # Four players, two rounds, and whatever 299 records the test wants to add.
    lines = ["012 Abnormal assignment points", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(2, "w", "1"), (3, "b", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.5", [(1, "b", "0"), (4, "w", "=")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.5", [(4, "w", "1"), (1, "w", "=")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.5", [(3, "b", "0"), (2, "b", "=")]))
    return lines + abnormal


def parse(lines):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    return chessfile


def test_299_naming_competitors_is_read():
    # Forfeit wins in round two are worth 2 match points and 2.5 game points, and two
    # competitors got one. Reading the record must not raise.
    line = abnormal_line("+", "2.0", "2.5", 2, [2, 4])
    chessfile = parse(two_rounds([line]))

    assert chessfile.aatlist == [
        {
            "att": "+",
            "matchPoints": decimal.Decimal("2.0"),
            "gamePoints": decimal.Decimal("2.5"),
            "round": 2,
            "teams": [2, 4],
        }
    ]


def test_299_round_is_not_the_game_points_field():
    # Game points and the round are two different fields in two different places. Here
    # they are 3 and 2, and a reader that takes the round from the game points columns
    # reports round 3 without complaining about anything.
    line = abnormal_line("+", "2.0", "3", 2, [2, 4])
    chessfile = parse(two_rounds([line]))

    assert chessfile.aatlist[0]["round"] == 2
    assert chessfile.aatlist[0]["gamePoints"] == decimal.Decimal("3")


def test_299_for_all_rounds_and_all_competitors_sets_the_score_system():
    # No round and no pairing numbers: the points apply to the whole tournament, and go
    # to the score system rather than to the list of individual assignments. This is the
    # record the specification writes out in its note.
    lines = two_rounds([points_only_line("+", "2.0", "2.5"),
                        points_only_line("-", "0.0", "1.5")])
    chessfile = parse(lines)
    scoresystem = chessfile.get_tournament(1)["scoreSystem"]["match"]

    assert scoresystem["+"] == decimal.Decimal("2.0")   # forfeit win, match points
    assert scoresystem["+G"] == decimal.Decimal("2.5")  # forfeit win, game points
    assert scoresystem["-"] == decimal.Decimal("0.0")   # forfeit loss, match points
    assert scoresystem["-G"] == decimal.Decimal("1.5")  # forfeit loss, game points
    assert chessfile.aatlist == []


def test_299_for_all_rounds_of_a_named_competitor_is_read():
    # Round 000 means every round, but the record still names a competitor, so it is an
    # assignment and not a change to the score system.
    line = abnormal_line(" ", "0.0", "-1.0", 0, [3])
    chessfile = parse(two_rounds([line]))

    assert chessfile.aatlist == [
        {
            "att": " ",
            "matchPoints": decimal.Decimal("0.0"),
            "gamePoints": decimal.Decimal("-1.0"),
            "round": 0,
            "teams": [3],
        }
    ]
