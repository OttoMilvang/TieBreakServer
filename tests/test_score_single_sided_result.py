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
"""
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


def one_sided_round_two():
    # Player 1's row ends after round 1, as if they withdrew. Player 2's row
    # continues into round 2, playing black against player 1 -- who has no round-2
    # entry at all. Only one side of that round-2 game is ever recorded: white=1,
    # black=2, bResult set, no wResult.
    lines = ["012 One-sided result test", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2000, "1.0", [(2, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, "1.0", [(1, "b", "0"), (1, "b", "1")]))
    return lines


def test_parsing_a_one_sided_game_record_does_not_crash():
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(one_sided_round_two()), True)

    assert chessfile.get_status() == 0
    tournament = chessfile.get_tournament(1)
    games = {(game["round"], game["white"], game["black"]): game for game in tournament["gameList"]}

    round_two = games[(2, 1, 2)]
    assert round_two["bResult"] == "W"
    assert "wResult" not in round_two


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
