# -*- coding: utf-8 -*-
"""
Regression test for chessjson.get_score() / is_vur() on a one-sided game record.

Both methods branch on the presence of "<colour>Result" in the result dict:

    if color[0] + "Result" in result:
        res = result[color[0] + "Result"]
    elif result["black"] > 0:
        res = self.reverse[result[color[0] + "Result"]]   # same missing key -- KeyError

The elif is only reached when that exact key is already known to be absent, so the
old code read it anyway and crashed. This is reachable through public TRF parsing,
not just by poking the dict by hand: trf2json.parse_trf_game() builds a game record
from only one side's perspective at a time --

    if color == "b":
        game["bResult"] = points
    else:
        game["wResult"] = points

-- and append_result() only fills in the other side's key when a second, reciprocal
record for the same (round, white) pair shows up from the *other* player's own "001"
row. A player whose row ends early (e.g. they withdrew) leaves no such reciprocal
record, so a game where they were named as an opponent by someone else keeps only
that someone else's half. trf2json.parse_file() calls update_board_number() on every
individual tournament, which calls get_score() unconditionally for "white" on every
game -- so this crashes on ordinary parsing, not just on tie-break computation.

Reading the result through get_result_res() removed the crash, but its default is the
letter "Z", so a side with no result at all became a side that scored zero and the
reverse branch was never entered again. The tests at the end of this file measure the
score of the side that was never recorded, which is where that shows.
"""
import decimal

import pytest

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


def one_sided_round_two(round2="1", points="1.0"):
    # Player 1's row ends after round 1, as if they withdrew. Player 2's row
    # continues into round 2, playing black against player 1 -- who has no round-2
    # entry at all. Only one side of that round-2 game is ever recorded: white=1,
    # black=2, bResult set, no wResult.
    #
    # round2 is what player 2's round-2 column says and points the total their own "001"
    # record then declares. The two have to agree, or the reader cannot solve the score
    # system and the file fails for a reason that has nothing to do with this.
    lines = ["012 One-sided result test", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2000, "1.0", [(2, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, points, [(1, "b", "0"), (1, "b", round2)]))
    return lines


def test_parsing_a_one_sided_game_record_does_not_crash():
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(one_sided_round_two()), True)

    assert chessfile.get_status() == 0
    tournament = chessfile.get_tournament(1)
    games = {(game["round"], chessfile.get_result_cid(game, "white"), chessfile.get_result_cid(game, "black")): 
             game for game in tournament["gameList"]}

    round_two = games[(2, 1, 2)]
    assert round_two["black"]["result"] == "W"
    assert "result" not in round_two["white"]


def test_one_sided_game_still_reports_a_score_for_the_recorded_side():
    # get_score() itself, exercised through the public entry point: a competitor's
    # own points total must still come out right even though only their opponent's
    # half of the round-2 game was ever recorded.
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(one_sided_round_two()), True)
    tournament = chessfile.get_tournament(1)

    competitor_two = next(c for c in tournament["competitors"] if c["cid"] == 2)
    # Player 2 lost round 1 (0 points) then won round 2 (1 point) -- reported directly
    # off their own "001" row, unaffected by the one-sided game record.
    assert competitor_two["gamePoints"] == 1


@pytest.mark.parametrize(
    "round2, points, letter, whitescore",
    [
        ("1", "1.0", "W", "0.0"),   # black won        -> white lost
        ("0", "0.0", "L", "1.0"),   # black lost       -> white won
        ("=", "0.5", "D", "0.5"),   # black drew       -> white drew
        ("-", "0.0", "Z", "1.0"),   # black forfeited  -> white won the forfeit
    ],
    ids=["black-won", "black-lost", "draw", "black-forfeited"],
)
def test_the_unrecorded_side_scores_the_reverse_of_the_recorded_one(round2, points, letter,
                                                                   whitescore):
    """White's score on a one-sided record is Black's result reversed, not zero.

    This is the assertion the "Z" default silently took away. get_result_res() answers
    "Z" for a side that carries no result at all, so res was never None, the branch that
    reverses the opposite side's result was unreachable, and White's score came from the
    score system's entry for "Z" instead. Three of the four rows below then read 0.0:
    the player who won a game the loser never recorded, the player who drew one, and the
    player whose opponent forfeited all scored nothing.

    Only the first row, where Black won, is unaffected -- a loss and a zero are worth the
    same -- which is why it is here: it is the case that passes either way, and the other
    three are the ones that hold the reversal.
    """
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(one_sided_round_two(round2, points)), True)

    assert chessfile.get_status() == 0
    tournament = chessfile.get_tournament(1)
    round_two = next(g for g in tournament["gameList"] if g["round"] == 2)

    # The shape this is about: Black carries a result and White carries none.
    assert round_two["black"]["result"] == letter
    assert "result" not in round_two["white"]

    scoresystem = tournament["scoreSystem"]["game"]
    assert chessfile.get_score(scoresystem, round_two, "white") == decimal.Decimal(whitescore)


def test_a_forfeit_win_taken_from_the_other_side_is_not_an_unplayed_round():
    """is_vur() has to reverse the same way get_score() does.

    Player 2 forfeited round 2, so player 1 won it without playing. A forfeit win is not
    a VUR (C.07 art. 16.1 lists the categories, and a win is not among them), but with
    the "Z" default player 1's side of the record read as a zero-point bye and counted as
    one. It is the same dead branch, two lines further down the file.
    """
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(one_sided_round_two("-", "0.0")), True)
    tournament = chessfile.get_tournament(1)
    round_two = next(g for g in tournament["gameList"] if g["round"] == 2)

    assert round_two["played"] is False
    assert chessfile.is_vur(round_two, "white") is False
    # Player 2's own half is recorded, and a forfeit loss is a VUR.
    assert chessfile.is_vur(round_two, "black") is True
