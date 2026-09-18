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

from gacrux import gacruxexeptions
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


def team_line(cid, name, players, matchpoints="0.0", gamepoints="0.0"):
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
    line[54:60] = "%6s" % matchpoints
    line[61:67] = "%6s" % gamepoints
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


def teams(records, first=1):
    # Four teams of two players, two rounds played, a third round declared but not yet
    # played. Team 1 is players 1 and 2, team 2 is players 3 and 4, and so on -- so a
    # number like 6 names a player and no team at all. `first` is the start number of
    # the first player; the players are numbered consecutively from it.
    def p(number):
        return number + first - 1

    lines = ["012 Pairing numbers, teams", "042 2026-03-01", "XXR 3", "352 WB"]
    lines.append(team_line(1, "Team One", [p(1), p(2)], "2.0", "2.5"))
    lines.append(team_line(2, "Team Two", [p(3), p(4)], "2.0", "2.0"))
    lines.append(team_line(3, "Team Three", [p(5), p(6)], "0.0", "0.5"))
    lines.append(team_line(4, "Team Four", [p(7), p(8)], "4.0", "3.0"))
    lines.append(player_line(p(1), "One, Player", 2400, "1.5", [(p(5), "w", "1"), (p(7), "w", "=")]))
    lines.append(player_line(p(2), "Two, Player", 2300, "1.0", [(p(6), "b", "1"), (p(8), "b", "0")]))
    lines.append(player_line(p(3), "Three, Player", 2200, "0.5", [(p(7), "b", "0"), (p(5), "b", "=")]))
    lines.append(player_line(p(4), "Four, Player", 2100, "1.5", [(p(8), "w", "="), (p(6), "w", "1")]))
    lines.append(player_line(p(5), "Five, Player", 2000, "0.5", [(p(1), "b", "0"), (p(3), "w", "=")]))
    lines.append(player_line(p(6), "Six, Player", 1900, "0.0", [(p(2), "w", "0"), (p(4), "b", "0")]))
    lines.append(player_line(p(7), "Seven, Player", 1800, "1.5", [(p(3), "w", "1"), (p(1), "b", "=")]))
    lines.append(player_line(p(8), "Eight, Player", 1700, "1.5", [(p(4), "b", "="), (p(2), "w", "1")]))
    return lines + records


def parse(lines):
    chessfile = trf2json.trf2json()
    # verbose off: this is how a program that is handed a file reads it, and it is the
    # setting under which the reader used to swallow what it knew and crash later.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def test_240_naming_a_player_who_does_not_exist():
    # Four players, and a half-point-bye for number 6 in round three.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(individual(["240 H 003    6"]))

    message = str(excinfo.value)
    assert "240" in message      # the record it came from
    assert "6" in message        # the number that is wrong
    assert "1 - 4" in message    # the numbers that would have been right


def test_240_naming_a_player_who_exists_is_read():
    chessfile = parse(individual(["240 H 003    3"]))
    gameList = chessfile.get_tournament(1)["gameList"]
    
    byes = [game for game in gameList if game["round"] == 3]
    assert [(chessfile.get_result_cid(game, "white"), chessfile.get_result_cid(game, "black"), game["white"]["result"]) for game in byes] == [(3, 0, "D")]


def test_240_names_a_team_in_a_team_tournament():
    # In a team tournament the number is a team, and team 3 is a team the event has.
    chessfile = parse(teams(["240 H 003    3"]))
    matchList = chessfile.get_tournament(1)["matchList"]

    byes = [match for match in matchList if match["round"] == 3]
    assert [(chessfile.get_result_cid(match, "white"), chessfile.get_result_cid(match, "black"), match["white"]["result"]) for match in byes] == [(3, 0, "D")]


@pytest.mark.parametrize(
    "code, model",
    [
        ("FIDE_TEAM_TYPEA_MP_GP", "team_typea"),
        ("FIDE_TEAM_TYPEB_MP_GP", "team_typeb"),
        ("FIDE_TEAM_MP_GP", "nocolor"),
        ("FIDE_TEAM_BAKU", "team_typea"),
    ],
)
def test_record_192_selects_the_declared_team_colour_model(code, model):
    tournament = parse(teams(["192 " + code])).get_tournament(1)

    assert model in tournament["pairingSystem"]


def test_240_in_a_team_tournament_does_not_accept_a_player_number():
    # 6 is a player in this event, and no team. The bye goes to a team, so the number is
    # read against the teams -- checking it against the players would let this through
    # and hand the pairing a team that does not exist.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["240 H 003    6"]))

    message = str(excinfo.value)
    assert "240" in message
    assert "team 6" in message
    assert "1 - 4" in message


def test_320_naming_a_team_that_does_not_exist():
    # Record 320, the pairing-allocated bye: the team getting the PAB in each round.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["320  1.0  1.0 000 000 006"]))

    assert "320" in str(excinfo.value)
    assert "team 6" in str(excinfo.value)


def test_a_second_record_320_is_refused():
    """TRF-2026: record 320 is "one record per tournament".

    The record carries the value of a pairing-allocated bye and one team per round, so
    a second one is either a repeat or a contradiction, and the reader used to let the
    second silently replace what the first had put into the score system and add its
    byes on top of the first's. Neither reading is the file's, so the file is refused
    and the message says which record and which rule.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["320  1.0  1.0 000 000 003", "320  1.0  1.0 000 000 003"]))

    message = str(excinfo.value)
    assert "320" in message
    assert "one record per tournament" in message


def test_a_second_record_240_of_the_same_type_and_round_is_refused():
    """TRF-2026: record 240 is "at most one record per type per round".

    Every team or player getting a half-point bye in round 3 is listed on the one "H"
    record for round 3, so a second "H 003" record is a repeat or a contradiction, and
    the reader used to append its byes to the first's without a word. A record of a
    different type in the same round, or of the same type in another round, is what
    the specification allows, and the control below keeps it readable.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["240 H 003    3", "240 H 003    4"]))

    message = str(excinfo.value)
    assert "240" in message
    assert "per type per round" in message
    assert "H" in message and "round 3" in message

    # Control: a different type in the same round, and the same type in another round.
    assert parse(teams(["240 H 003    3", "240 F 003    4"])).get_status() == 0


def test_330_naming_a_team_that_does_not_exist():
    # Record 330, a forfeited match: the two teams scheduled to play it.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["330 +-   2   9   3"]))

    assert "330" in str(excinfo.value) or "Error in teams" in str(excinfo.value)
    assert "team 9" in str(excinfo.value) or "Error in teams" in str(excinfo.value)


def test_300_naming_a_team_that_does_not_exist():
    # Record 300, out of default order: the team playing OOdO and its opponent.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["300   2   7   4    3    4"]))

    assert "300" in str(excinfo.value) or "Out-of-order" in str(excinfo.value)
    assert "team 7" in str(excinfo.value) 


def test_300_naming_a_player_who_does_not_exist():
    # The same record then lists the players of the team, board by board. Those are
    # players, and 99 is not one.
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(teams(["300   2   2   3   99    4"]))

    assert "300" in str(excinfo.value)
    assert "player 99" in str(excinfo.value)


def test_310_naming_a_player_who_does_not_exist():
    # A team made up of a player the player section does not have.
    lines = [team_line(1, "Team One", [1, 99]) if line.startswith("310   1") else line
             for line in teams([])]

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(lines)

    assert "310" in str(excinfo.value)
    assert "player 99" in str(excinfo.value)


def renumbered(records, old, new):
    """The team fixture with team `old`'s pairing number (columns 5-7) changed to `new`."""
    return [
        line[:4] + "%3d" % new + line[7:] if line.startswith("310" + "%4d" % old) else line
        for line in teams(records)
    ]


@pytest.mark.parametrize(
    "old, new, found",
    [
        (4, 3, "1, 2, 3, 3"),       # duplicate
        (4, 5, "1, 2, 3, 5"),       # gap
        (1, 0, "0, 2, 3, 4"),       # zero
    ],
    ids=["duplicate", "gap", "zero"],
)
def test_record_310_requires_team_pairing_numbers_1_to_n(old, new, found):
    """C.04.6 art. 1.1.1: each team has a different TPN, from 1 to the number of teams.

    A duplicate used to replace one team with the other and read on with status 0, a
    zero was read as team 0, and a gap ran off the end of the board-number list with
    an IndexError.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(renumbered([], old, new))

    message = str(excinfo.value)
    assert "Record 310" in message
    assert found in message
    assert "expected 1, 2, 3, 4" in message


def test_record_310_accepts_the_complete_team_pairing_number_range():
    assert parse(teams([])).get_status() == 0


def test_team_pairing_numbers_1_to_n_is_a_fide_team_swiss_rule():
    """Art. 1.1.1 is an article of the Swiss team system and nothing else.

    TRF-2026 record 310 only asks for a number "From 1 to 999", and record 192 lists
    team events that are not C.04.6 at all. A Berger round robin with teams 1, 2, 3
    and 5 is read. Two teams with one number are refused whatever the system, since
    the reader keeps the teams by that number.
    """
    assert parse(renumbered(["192 BERGER_TEAM_ROUNDROBIN"], 4, 5)).get_status() == 0

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(renumbered(["192 FIDE_TEAM_MP_GP"], 4, 5))
    assert "Record 310" in str(excinfo.value)
    assert "expected 1, 2, 3, 4" in str(excinfo.value)

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(renumbered(["192 BERGER_TEAM_ROUNDROBIN"], 4, 3))
    assert "Record 310" in str(excinfo.value)
    assert "1, 2, 3, 3" in str(excinfo.value)


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

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        parse(lines)

    assert "001" in str(excinfo.value)
    assert "player 6" in str(excinfo.value)


def test_a_tournament_that_names_nobody_wrong_still_reads():
    # The check must not reject the records it is there to protect: every number below
    # names somebody, in an individual and in a team tournament.
    assert parse(individual(["240 H 003    3"])).get_status() == 0
    assert parse(teams(["240 H 003    3",
                        "300   2   2   3    3    4"])).get_status() == 0


def test_a_four_digit_player_id_on_record_310_is_read():
    """A player id of 1000 or more in record 310 is data, not misalignment.

    TRF-2026 gives record 310 its rank in columns 69-71 and its first player in columns
    74-77; the player ids of record 001 run "from 1 to 9999". The misalignment check
    read line[71:74], which is columns 72-74, and column 74 is the first digit of the
    first player id -- blank for an id below 1000, and a digit for 1000 and above. So a
    team whose first player was numbered 1000 or more was reported as "misaligned
    data, may be bad character encoding", status 467, for a record that is correct.
    """
    chessfile = parse(teams([], first=1001))

    assert chessfile.get_status() == 0
    tournament = chessfile.get_tournament(1)
    teamone = next(team for team in tournament["competitors"] if team["cid"] == 1)
    assert [player["cid"] for player in teamone["cplayers"]] == [1001, 1002]
