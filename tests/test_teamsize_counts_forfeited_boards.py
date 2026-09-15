# -*- coding: utf-8 -*-
"""The number of boards of a team event whose matches contain a forfeited board.

A team file need not say how many boards a match has. Record 352 states it as the length
of its colour sequence, and where that record is absent the reader infers it, in
``post_parse_line()``'s record 013 branch, as the largest number of games any one team
had in any one round.

It counted only the games it considered *played*::

    if game["played"] and self.get_result_cid(game, "white") > 0 and ...

A board decided by forfeit is not played. It is still a board: the two players are
paired at it, they are named as each other's opponents, and TRF records the result as
"+" and "-" in their own 001 records. So an event in which every team had a forfeit in
every round was measured one board short, and nothing about the file was malformed --
this is what a round with an absentee looks like.

One board short is not a cosmetic figure. ``teamSize`` is what ``update_board_number()``
numbers the boards with, so the last board of every match was given board number 0;
``build_tmatches()`` then carried teamSize games per match and dropped it; the team's
game points were the sum of the boards that survived, short by whatever was scored on
the last one; and a pairing-allocated bye is worth ``teamSize`` times the game-point
value of a draw-or-better, so the bye was short a board too. A reader that also checks
record 310 against the 001 records then rejects the file it has just miscounted.

The event below is the smallest one that shows it: two teams, three boards, one round,
board 2 forfeited on both sides, and no record 352 to state the board count outright.
"""
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


def team_line_013(name, players):
    # Record 013: the name in 5-36, the players from 37 on, and no score columns.
    return "013 " + "%-32s" % name + "".join(["%4d " % player for player in players])


def three_board_event(forfeited_board):
    """Two teams of three, one round. ``forfeited_board`` is decided "+"/"-".

    Deliberately no record 352: this is the file that makes the reader infer the board
    count rather than read it.
    """
    results = ["1", "=", "="]
    results[forfeited_board - 1] = "+"
    mirrored = {"1": "0", "=": "=", "+": "-"}
    value = {"1": "1.0", "=": "0.5", "+": "1.0", "0": "0.0", "-": "0.0"}

    lines = ["012 Forfeited board", "042 2026-03-01", "XXR 1"]
    lines.append(team_line_013("Team One", [1, 2, 3]))
    lines.append(team_line_013("Team Two", [4, 5, 6]))
    for board in range(3):
        # Team One's player is startno 1+board, Team Two's is 4+board; they are each
        # other's opponents, on this board, whether or not the game was played.
        ours, theirs = results[board], mirrored[results[board]]
        lines.append(player_line(1 + board, "One%d, Player" % board, 2400,
                                 value[ours], [(4 + board, "w", ours)]))
        lines.append(player_line(4 + board, "Two%d, Player" % board, 2300,
                                 value[theirs], [(1 + board, "b", theirs)]))
    return lines


def read(lines):
    chessfile = trf2json.trf2json()
    # verbose off: this is how a program that is handed a file reads it.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile.get_tournament(1)


def test_a_forfeited_board_still_counts_towards_the_board_count():
    tournament = read(three_board_event(forfeited_board=2))
    assert tournament["teamSize"] == 3


def test_every_board_of_the_match_is_numbered():
    """Board 0 is what a board past ``teamSize`` is given, so it is the visible symptom.

    One entry per board, so a three-board match is boards 1, 2 and 3 -- not a 0 among them.
    """
    tournament = read(three_board_event(forfeited_board=2))
    boards = sorted(game["board"] for game in tournament["gameList"])
    assert boards == [1, 2, 3], boards


def test_the_match_carries_every_board():
    tournament = read(three_board_event(forfeited_board=2))
    assert [len(match["games"]) for match in tournament["matchList"]] == [3]


def test_a_fully_played_round_was_never_affected():
    """The control: with nothing forfeited the old counting already gave 3."""
    lines = ["012 Nothing forfeited", "042 2026-03-01", "XXR 1",
             team_line_013("Team One", [1, 2, 3]), team_line_013("Team Two", [4, 5, 6])]
    for board in range(3):
        lines.append(player_line(1 + board, "One%d, Player" % board, 2400, "0.5",
                                 [(4 + board, "w", "=")]))
        lines.append(player_line(4 + board, "Two%d, Player" % board, 2300, "0.5",
                                 [(1 + board, "b", "=")]))
    assert read(lines)["teamSize"] == 3
