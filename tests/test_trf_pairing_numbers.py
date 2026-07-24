# -*- coding: utf-8 -*-
"""
Regression tests for the pairing numbers a TRF record names.

The reader indexes the competitors by pairing number, and it used to index them with
whatever number a record carried. A number that names nobody -- a typo, or a competitor
taken out of the player section and left behind in a later record -- came out of the
reader as an IndexError or a KeyError from somewhere far away from the record that
carried it.

Which competitors a number may name depends on the record and on the tournament.
TRF-2026 calls the field of records 240, 300, 320 and 330 a "(Team) Pairing Number": in
a team tournament it is a team, and the specification's own example of record 240 reads
"two teams (26 and 47) getting a HPB in the third round"; in an individual tournament it
is a player. The player ids that records 300 and 310 list within a team are players in
either kind of tournament.
"""
import pytest

import errors
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


def team_line(cid, name, players):
    # Record 310, written at the columns TRF-2026 gives it:
    #     1 - 3    record identifier 310
    #     5 - 7    team pairing number
    #     9 - 40   team name
    #    69 - 71   rank
    #    74 - 77   1st player id, then 79 - 82, ...
    line = list(" " * 73)
    line[0:3] = "310"
    line[4:7] = "%3d" % cid
    line[8 : 8 + len(name)] = name
    line[68:71] = "%3d" % cid
    return "".join(line) + " ".join(["%4d" % player for player in players])


def individual(records):
    # Four players, two rounds played, a third round declared but not yet played.
    lines = ["012 Pairing numbers", "042 2026-03-01", "XXR 3"]
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(2, "w", "1"), (3, "b", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.5", [(1, "b", "0"), (4, "w", "=")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.5", [(4, "w", "1"), (1, "w", "=")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.5", [(3, "b", "0"), (2, "b", "=")]))
    return lines + records


def teams(records):
    # Four teams of two players, two rounds played, a third round declared but not yet
    # played. Team 1 is players 1 and 2, team 2 is players 3 and 4, and so on -- so a
    # number like 6 names a player and no team at all.
    lines = ["012 Pairing numbers, teams", "042 2026-03-01", "XXR 3", "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2]))
    lines.append(team_line(2, "Team Two", [3, 4]))
    lines.append(team_line(3, "Team Three", [5, 6]))
    lines.append(team_line(4, "Team Four", [7, 8]))
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(5, "w", "1"), (7, "w", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "1.0", [(6, "b", "1"), (8, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "0.5", [(7, "b", "0"), (5, "b", "=")]))
    lines.append(player_line(4, "Four, Player", 2100, "1.5", [(8, "w", "="), (6, "w", "1")]))
    lines.append(player_line(5, "Five, Player", 2000, "0.5", [(1, "b", "0"), (3, "w", "=")]))
    lines.append(player_line(6, "Six, Player", 1900, "0.0", [(2, "w", "0"), (4, "b", "0")]))
    lines.append(player_line(7, "Seven, Player", 1800, "1.5", [(3, "w", "1"), (1, "b", "=")]))
    lines.append(player_line(8, "Eight, Player", 1700, "1.5", [(4, "b", "="), (2, "w", "1")]))
    return lines + records


def parse(lines):
    chessfile = trf2json.trf2json()
    # verbose off: this is how a program that is handed a file reads it, and it is the
    # setting under which the reader used to swallow what it knew and crash later.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def test_240_naming_a_player_who_does_not_exist():
    # Four players, and a half-point-bye for number 6 in round three.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(individual(["240 H 003    6"]))

    message = str(excinfo.value)
    assert "240" in message      # the record it came from
    assert "6" in message        # the number that is wrong
    assert "1 - 4" in message    # the numbers that would have been right


def test_240_naming_a_player_who_exists_is_read():
    chessfile = parse(individual(["240 H 003    3"]))
    gameList = chessfile.get_tournament(1)["gameList"]

    byes = [game for game in gameList if game["round"] == 3]
    assert [(game["white"], game["black"], game["wResult"]) for game in byes] == [(3, 0, "D")]


def test_240_names_a_team_in_a_team_tournament():
    # In a team tournament the number is a team, and team 3 is a team the event has.
    chessfile = parse(teams(["240 H 003    3"]))
    matchList = chessfile.get_tournament(1)["matchList"]

    byes = [match for match in matchList if match["round"] == 3]
    assert [(match["white"], match["black"], match["wResult"]) for match in byes] == [(3, 0, "D")]


def test_240_in_a_team_tournament_does_not_accept_a_player_number():
    # 6 is a player in this event, and no team. The bye goes to a team, so the number is
    # read against the teams -- checking it against the players would let this through
    # and hand the pairing a team that does not exist.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(teams(["240 H 003    6"]))

    message = str(excinfo.value)
    assert "240" in message
    assert "team 6" in message
    assert "1 - 4" in message


def test_320_naming_a_team_that_does_not_exist():
    # Record 320, the pairing-allocated bye: the team getting the PAB in each round.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(teams(["320  1.0  1.0 000 000 006"]))

    assert "320" in str(excinfo.value)
    assert "team 6" in str(excinfo.value)


def test_330_naming_a_team_that_does_not_exist():
    # Record 330, a forfeited match: the two teams scheduled to play it.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(teams(["330 +-   2   9   3"]))

    assert "330" in str(excinfo.value)
    assert "team 9" in str(excinfo.value)


def test_300_naming_a_team_that_does_not_exist():
    # Record 300, out of default order: the team playing OOdO and its opponent.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(teams(["300   2   7   4    3    4"]))

    assert "300" in str(excinfo.value)
    assert "team 7" in str(excinfo.value)


def test_300_naming_a_player_who_does_not_exist():
    # The same record then lists the players of the team, board by board. Those are
    # players, and 99 is not one.
    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(teams(["300   2   2   3   99    4"]))

    assert "300" in str(excinfo.value)
    assert "player 99" in str(excinfo.value)


def test_310_naming_a_player_who_does_not_exist():
    # A team made up of a player the player section does not have.
    lines = [team_line(1, "Team One", [1, 99]) if line.startswith("310   1") else line
             for line in teams([])]

    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(lines)

    assert "310" in str(excinfo.value)
    assert "player 99" in str(excinfo.value)


def test_001_naming_an_opponent_who_does_not_exist():
    # The opponent of a scheduled game is a pairing number as well, and it is the one an
    # arbiter is most likely to mistype. It cannot be checked while the record is read --
    # the opponent may be further down the file -- so it is checked once the player
    # section is complete.
    lines = ["012 Pairing numbers", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(2, "w", "1"), (6, "b", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.5", [(1, "b", "0"), (4, "w", "=")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.0", [(4, "w", "1"), (0, "-", "Z")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.5", [(3, "b", "0"), (2, "b", "=")]))

    with pytest.raises(errors.GacruxInputError) as excinfo:
        parse(lines)

    assert "001" in str(excinfo.value)
    assert "player 6" in str(excinfo.value)


def test_a_tournament_that_names_nobody_wrong_still_reads():
    # The check must not reject the records it is there to protect: every number below
    # names somebody, in an individual and in a team tournament.
    assert parse(individual(["240 H 003    3"])).get_status() == 0
    assert parse(teams(["240 H 003    3",
                        "300   2   2   3    3    4"])).get_status() == 0
