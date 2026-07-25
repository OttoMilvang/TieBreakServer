# -*- coding: utf-8 -*-
"""
Regression tests for the cut modifiers /Cn and /Mn on Buchholz and Sonneborn-Berger.

The cut is limited by the number of rounds, not by the number of games the competitor
actually has. A competitor who withdrew, entered late or was given byes has fewer games
than that, so a cut can consume every game he has.
"""
from decimal import Decimal

import pytest

import tiebreak
import trf2json

PAB = (0, "-", "U")  # pairing-allocated bye
ZPB = (0, "-", "Z")  # zero-point bye


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


def withdrawal_after_round_1():
    # Round robin, five competitors, five rounds, Berger order. Player 5 withdraws after
    # round 1, so rounds 2-5 are a zero-point bye for him and a bye for each competitor
    # he was scheduled against. Games actually played: 1 has 3, 2 has 4, 3 has 3, 4 has 3
    # and 5 has 1.
    lines = ["012 Withdrawal in a round robin", "042 2026-03-01", "XXR 5"]
    lines.append(player_line(1, "One, Player", 2400, "4.5",
                             [PAB, (2, "w", "1"), (3, "b", "1"), (4, "w", "="), PAB]))
    lines.append(player_line(2, "Two, Player", 2300, "3.0",
                             [(5, "w", "1"), (1, "b", "0"), PAB, (3, "w", "1"), (4, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "2.5",
                             [(4, "w", "="), PAB, (1, "w", "0"), (2, "b", "0"), PAB]))
    lines.append(player_line(4, "Four, Player", 2100, "4.0",
                             [(3, "b", "="), PAB, PAB, (1, "b", "="), (2, "w", "1")]))
    lines.append(player_line(5, "Five, Player", 2000, "0.0",
                             [(2, "b", "0"), ZPB, ZPB, ZPB, ZPB]))
    return lines


def compute(lines, tiebreaks):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": tiebreaks, "check": False, "unrated": None, "pre_determined": True}
    tb = tiebreak.tiebreak(tournament, -1, params)
    result = tb.compute_tiebreaks(tournament, params)
    return dict([(cmp["cid"], str(cmp["tiebreakScore"][0])) for cmp in result["competitors"]])


def test_buchholz_of_the_field():
    # Adjusted scores are 4.5, 3.0, 2.5, 4.0 and 0.0; unplayed rounds of a round robin do
    # not contribute an opponent. These are the sums the cuts below are taken from.
    assert compute(withdrawal_after_round_1(), ["BH"]) == {
        1: "9.5",    # 3.0 + 2.5 + 4.0
        2: "11.0",   # 0.0 + 4.5 + 2.5 + 4.0
        3: "11.5",   # 4.0 + 4.5 + 3.0
        4: "10.0",   # 2.5 + 4.5 + 3.0
        5: "3.0",    # 3.0
    }


def test_low_cut_larger_than_the_number_of_games():
    # BH/C2 drops the two lowest. Player 5 has one game, so everything he has is dropped
    # and his Buchholz is 0. Everybody else keeps the games the cut leaves.
    assert compute(withdrawal_after_round_1(), ["BH/C2"]) == {
        1: "4.0",    # 4.0                 (2.5 and 3.0 dropped)
        2: "8.5",    # 4.5 + 4.0           (0.0 and 2.5 dropped)
        3: "4.5",    # 4.5                 (3.0 and 4.0 dropped)
        4: "4.5",    # 4.5                 (2.5 and 3.0 dropped)
        5: "0",      # nothing left
    }


def test_high_cut_larger_than_the_number_of_games():
    # BH/M1 drops the lowest and then the highest. Player 5's single game goes with the
    # low cut, so the high cut has nothing left to drop.
    assert compute(withdrawal_after_round_1(), ["BH/M1"]) == {
        1: "3.0",    # 3.0                 (2.5 and 4.0 dropped)
        2: "6.5",    # 2.5 + 4.0           (0.0 and 4.5 dropped)
        3: "4.0",    # 4.0                 (3.0 and 4.5 dropped)
        4: "3.0",    # 3.0                 (2.5 and 4.5 dropped)
        5: "0",      # nothing left
    }


def test_sonneborn_berger_cuts():
    assert compute(withdrawal_after_round_1(), ["SB/C2"]) == {
        1: "2.00", 2: "0.00", 3: "0.00", 4: "2.25", 5: "0",
    }
    assert compute(withdrawal_after_round_1(), ["SB/M1"]) == {
        1: "3.00", 2: "2.50", 3: "2.00", 4: "3.00", 5: "0",
    }


def test_sonneborn_berger_vur_candidate_is_selected_by_contribution():
    # C.07 articles 14.1.1.d and 16.5 require two different candidates:
    #
    # * the ordinary candidate is the contribution associated with the opponent
    #   having the lowest score (round 10 here: 2.50), and
    # * the VUR candidate is the lowest contribution from a VUR (round 4: 0.00),
    #   regardless of the dummy scores attached to those VURs.
    #
    # The March 2026 caps can give VURs different dummy scores. Selecting a VUR by
    # dummy score would wrongly choose round 1 (2.75) and produce 31.25. Article
    # 16.5 instead compares 0.00 with 2.50 and cuts the latter, producing 31.50.
    games = [
        {"vur": True, "score": Decimal("5.50"), "tbvalue": Decimal("2.75"), "rnd": 1},
        {"vur": True, "score": Decimal("6.00"), "tbvalue": Decimal("0.00"), "rnd": 4},
        {"vur": False, "score": Decimal("2.50"), "tbvalue": Decimal("2.50"), "rnd": 10},
        {"vur": False, "score": Decimal("5.00"), "tbvalue": Decimal("5.00"), "rnd": 2},
        {"vur": False, "score": Decimal("4.50"), "tbvalue": Decimal("4.50"), "rnd": 3},
        {"vur": False, "score": Decimal("3.50"), "tbvalue": Decimal("3.50"), "rnd": 5},
        {"vur": False, "score": Decimal("4.00"), "tbvalue": Decimal("4.00"), "rnd": 6},
        {"vur": False, "score": Decimal("3.50"), "tbvalue": Decimal("3.50"), "rnd": 7},
        {"vur": False, "score": Decimal("3.00"), "tbvalue": Decimal("3.00"), "rnd": 8},
        {"vur": False, "score": Decimal("2.75"), "tbvalue": Decimal("2.75"), "rnd": 9},
        {"vur": False, "score": Decimal("2.75"), "tbvalue": Decimal("2.50"), "rnd": 11},
    ]

    cut_game = tiebreak._select_low_cut_game(games)

    assert cut_game["rnd"] == 10
    assert sum(game["tbvalue"] for game in games if game is not cut_game) == Decimal("31.50")


def test_equal_vur_contribution_is_cut_as_not_lower():
    # Article 16.5 says the VUR is cut when its contribution is "not lower" than
    # the ordinary candidate, so equality belongs to the VUR side of the comparison.
    ordinary = {"vur": False, "score": Decimal("1.00"), "tbvalue": Decimal("1.00"), "rnd": 1}
    vur = {"vur": True, "score": Decimal("4.00"), "tbvalue": Decimal("1.00"), "rnd": 2}

    assert tiebreak._select_low_cut_game([ordinary, vur]) is vur


@pytest.mark.parametrize("tb", ["BH/C5", "SB/C5"])
def test_cut_of_every_round(tb):
    # A cut of every round leaves nobody with a game, whatever he played.
    assert set(compute(withdrawal_after_round_1(), [tb]).values()) == set(["0"])


def test_cut_inside_the_number_of_games_is_unchanged():
    # A cut no competitor runs out of games on must keep the values it always had.
    assert compute(withdrawal_after_round_1(), ["BH/C1"]) == {
        1: "7.0",    # 3.0 + 4.0           (2.5 dropped)
        2: "11.0",   # 4.5 + 2.5 + 4.0     (0.0 dropped)
        3: "8.5",    # 4.5 + 4.0           (3.0 dropped)
        4: "7.5",    # 4.5 + 3.0           (2.5 dropped)
        5: "0",      # his one game dropped
    }
