# -*- coding: utf-8 -*-
"""The standing TRF-2026 record 310 declares, against the results of the file.

Record 310 columns 55-60 and 62-67 carry a team's match points and its game points.
validate_team_scores() recomputes both -- the match points from what each of the
team's matches was worth, the game points from the totals the team's players report
in columns 81-84 of their own 001 records -- and compares.

What it does with a disagreement is the question these tests answer. A standing that
differs from the results is the ordinary shape of a file carrying an arbiter's
decision: a team docked for not appearing, a penalty, a fine. TRF-2026 has record
299, Abnormal Assignment points, for exactly that. So the reader keeps the standing
the arbiter published, keeps reading the event, and says what it noticed on the
status "info" channel -- the non-fatal half of the status block the reader hands
out, beside the "error" list that everything fatal goes into.

Before this, the comparison was made and then thrown away: the raise that was to
report it stood behind "if badteams and False", so a file whose declared standing
contradicted its own results was read with status 0 and not one word about it.
"""
from decimal import Decimal

import pytest

from gacrux import gacruxexeptions
from gacrux import trf2json

# Four teams of two players, two rounds played, a third round declared but not played.
# Team 1 is players 1 and 2, team 2 is players 3 and 4, and so on. The declared record
# 310 totals are the ones the results give, so the file agrees with itself.
TEAMS = {
    1: ("Team One", [1, 2], "2.0", "2.5"),
    2: ("Team Two", [3, 4], "2.0", "2.0"),
    3: ("Team Three", [5, 6], "0.0", "0.5"),
    4: ("Team Four", [7, 8], "4.0", "3.0"),
}
PLAYERS = [
    (1, "One, Player", 2400, "1.5", [(5, "w", "1"), (7, "w", "=")]),
    (2, "Two, Player", 2300, "1.0", [(6, "b", "1"), (8, "b", "0")]),
    (3, "Three, Player", 2200, "0.5", [(7, "b", "0"), (5, "b", "=")]),
    (4, "Four, Player", 2100, "1.5", [(8, "w", "="), (6, "w", "1")]),
    (5, "Five, Player", 2000, "0.5", [(1, "b", "0"), (3, "w", "=")]),
    (6, "Six, Player", 1900, "0.0", [(2, "w", "0"), (4, "b", "0")]),
    (7, "Seven, Player", 1800, "1.5", [(3, "w", "1"), (1, "b", "=")]),
    (8, "Eight, Player", 1700, "1.5", [(4, "b", "="), (2, "w", "1")]),
]


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


def team_line(cid, name, players, matchpoints, gamepoints):
    # Record 310, written at the columns TRF-2026 gives it:
    #     1 - 3    record identifier 310
    #     5 - 7    team pairing number
    #     9 - 40   team name
    #    55 - 60   match points
    #    62 - 67   game points
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


def team_file(declared=None):
    """The fixture, with some teams' declared record 310 totals replaced.

    `declared` maps a team's number to the (match points, game points) the record is
    to declare instead of the ones the results give.
    """
    declared = declared or {}
    lines = ["012 Team standings", "042 2026-03-01", "XXR 3", "352 WB"]
    for cid, (name, players, matchpoints, gamepoints) in TEAMS.items():
        matchpoints, gamepoints = declared.get(cid, (matchpoints, gamepoints))
        lines.append(team_line(cid, name, players, matchpoints, gamepoints))
    lines.extend(player_line(*player) for player in PLAYERS)
    return lines


def parse(lines):
    chessfile = trf2json.trf2json()
    # verbose off: this is how a program that is handed a file reads it.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def test_a_standing_that_agrees_with_the_results_says_nothing():
    """The starting point, so that every assertion below is a difference.

    The fixture declares the totals its own results give, so there is nothing to
    report and no "info" channel is created at all.
    """
    chessfile = parse(team_file())

    assert chessfile.get_status() == 0
    assert "info" not in chessfile.chessjson["status"]


def test_a_declared_standing_that_disagrees_is_reported():
    """Team 1 declares one match point too few, team 3 one game point too many.

    Nothing else in the file moves, so the message is about those two teams and the
    two different things the two totals are checked against.
    """
    chessfile = parse(team_file({1: ("1.0", "2.5"), 3: ("0.0", "1.5")}))

    message = chessfile.chessjson["status"]["info"]
    assert isinstance(message, str)
    assert "310" in message                                   # the record it is about
    assert "team 1 declares 1.0 match points" in message      # declared
    assert "the matches give 2.0" in message                  # recomputed
    assert "team 3 declares 1.5 game points" in message
    assert "give 0.5" in message
    assert "299" in message           # where a deliberate difference is declared
    assert "team 2" not in message and "team 4" not in message


def test_a_disagreement_does_not_refuse_the_event():
    """A remark is not a fault, so the status code stays 0 and "error" stays empty.

    A caller that tests the code before it uses the event must still get the event:
    refusing would throw away every team, every game and every tie-break in it over a
    file with nothing wrong with it.
    """
    chessfile = parse(team_file({1: ("1.0", "2.5")}))

    assert chessfile.get_status() == 0
    assert not chessfile.chessjson["status"]["error"]
    assert chessfile.chessjson["status"]["info"]


def test_multiple_information_messages_remain_schema_strings():
    chessfile = trf2json.trf2json()

    chessfile.report_info("first observation")
    chessfile.report_info("second observation")

    assert chessfile.chessjson["status"]["info"] == (
        "first observation\nsecond observation"
    )


def test_the_declared_standing_is_the_one_kept():
    """The arbiter published 1.0, so the team is published on 1.0 and not on 2.0."""
    tournament = parse(team_file({1: ("1.0", "2.5")})).get_tournament(1)

    declared = {team["cid"]: team["matchPoints"] for team in tournament["competitors"]}
    assert declared[1] == Decimal("1.0")
    assert declared[2] == Decimal("2.0")


VALUE = {"1": "1.0", "+": "1.0", "U": "1.0", "=": "0.5", "0": "0.0", "-": "0.0"}


def two_teams(rounds, matchpoints, gamepoints):
    """Two teams of two boards, with the record 310 totals the caller gives.

    Team 1 wins rounds 1 and 2 by 1.5 - 0.5. Round 3, when there is one, is awarded to
    team 1 by forfeit under record 330: every board "+" or "-" against no opponent.
    """
    games = [
        [(3, "w", "1"), (3, "b", "=")],    [(4, "b", "="), (4, "w", "1")],
        [(1, "b", "0"), (1, "w", "=")],    [(2, "w", "="), (2, "b", "0")],
    ]
    if rounds > 2:
        for player, result in enumerate(["+", "+", "-", "-"]):
            games[player].append((0, "-", result))
    totals = [sum((Decimal(VALUE[game[2]]) for game in played), Decimal("0.0"))
              for played in games]

    lines = ["012 Team score totals", "042 2026-03-01", "XXR %d" % rounds, "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2], matchpoints[0], gamepoints[0]))
    lines.append(team_line(2, "Team Two", [3, 4], matchpoints[1], gamepoints[1]))
    for startno, name in enumerate(["One", "Two", "Three", "Four"]):
        lines.append(player_line(startno + 1, name + ", Player", 2400 - 100 * startno,
                                 "%.1f" % totals[startno], games[startno]))
    if rounds > 2:
        lines.append("330 +-   3   1   2")
    return lines


def three_teams_with_an_announced_bye(matchpoints, gamepoints, byes):
    """Three teams, rounds 1 and 2 played, and record 320 naming round 3's bye too.

    A bye is worth one match point and two game points. The third number of record 320
    is the bye of a round that has been paired and not played.
    """
    lines = ["012 Announced bye", "042 2026-03-01", "XXR 3", "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2], matchpoints[0], gamepoints[0]))
    lines.append(team_line(2, "Team Two", [3, 4], matchpoints[1], gamepoints[1]))
    lines.append(team_line(3, "Team Three", [5, 6], matchpoints[2], gamepoints[2]))
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(3, "w", "1"), (5, "b", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "1.0", [(4, "b", "="), (6, "w", "=")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.0", [(1, "b", "0"), (0, "-", "U")]))
    lines.append(player_line(4, "Four, Player", 2100, "1.5", [(2, "w", "="), (0, "-", "U")]))
    lines.append(player_line(5, "Five, Player", 2000, "1.5", [(0, "-", "U"), (1, "w", "=")]))
    lines.append(player_line(6, "Six, Player", 1900, "1.5", [(0, "-", "U"), (2, "b", "=")]))
    lines.append("320  1.0  2.0 " + " ".join("%03d" % bye for bye in byes))
    return lines


def test_a_last_round_decided_by_forfeit_agrees_with_record_310():
    """Round 3 is one match, awarded to team 1 under record 330.

    No game of it was played against an opponent, so currentRound stays at 2, and the
    round was left out of the check: "team 1 declares 6.0 match points, the matches give
    4.0", about a file that agrees with itself.
    """
    chessfile = parse(two_teams(3, ["6.0", "0.0"], ["5.0", "1.0"]))

    assert chessfile.get_status() == 0
    assert "info" not in chessfile.chessjson["status"]
    tournament = chessfile.get_tournament(1)
    assert tournament["currentRound"] == 2
    forfeited = [match for match in tournament["matchList"] if match["round"] == 3]
    assert [(chessfile.get_result_cid(match, "white"), chessfile.get_result_cid(match, "black"),
             match["white"]["result"], match["black"]["result"]) for match in forfeited] == [(1, 2, "W", "Z")]


def test_a_bye_announced_for_a_future_round_agrees_with_record_310():
    """Record 320 names team 1's bye for a round 3 nobody has played.

    Record 310 is the standing after round 2, so that bye is not in it. It was counted,
    and the check reported "team 1 declares 3.0 match points, the matches give 4.0".
    """
    chessfile = parse(three_teams_with_an_announced_bye(
        ["3.0", "1.0", "2.0"], ["2.5", "2.5", "3.0"], [3, 2, 1]))

    assert chessfile.get_status() == 0
    assert "info" not in chessfile.chessjson["status"]


def test_a_disagreement_names_the_rounds_counted_and_both_figures():
    """Team 1 declares 5.0 match points for three wins, team 2 2.0 game points for 1.0.

    The remark says which rounds were counted, and the figure for team 1 is 6.0, with
    the forfeited round in it.
    """
    chessfile = parse(two_teams(3, ["5.0", "0.0"], ["5.0", "2.0"]))

    assert chessfile.get_status() == 0
    message = chessfile.chessjson["status"]["info"]
    assert "310" in message
    assert "rounds 1 - 3" in message
    assert "team 1 declares 5.0 match points" in message
    assert "the matches give 6.0" in message
    assert "team 2 declares 2.0 game points" in message
    assert "give 1.0" in message


def test_a_match_naming_a_team_record_310_does_not_declare_is_a_typed_error():
    """The totals are kept by the team numbers record 310 declares.

    Every record naming a team is checked as it is read, so a match can only name an
    undeclared team if something built the match list by hand; that used to be a bare
    KeyError from inside the reader.
    """
    chessfile = parse(two_teams(2, ["4.0", "0.0"], ["3.0", "1.0"]))
    tournament = chessfile.get_tournament(1)
    tournament["matchList"].append({
        "id": 0, "round": 2, "played": True,
        "white": {"cid": 9, "result": "W"}, "black": {"cid": 1, "result": "L"},
    })

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        chessfile.validate_team_scores(tournament)

    message = str(excinfo.value)
    assert "team 9" in message
    assert "310" in message
    assert "round 2" in message
    assert "1 - 2" in message


def test_a_bye_whose_game_points_are_only_in_record_320_agrees_with_record_310():
    """TRF-2026 leaves a pairing-allocated bye out of a team event's 001 points.

    Columns 81-84 of the 001 record hold what the player scored over the board or by
    forfeit, so team 1's player writes 0.0 for a round-one bye, record 320 says the bye
    is worth 1.0 game points, and record 310 declares 1.0. Files that add the bye to the
    001 points as well are accepted too. Each team is read with the standing record 310
    declares.
    """
    lines = ["012 Bye in record 320 only", "042 2026-03-01", "XXR 1", "352 W"]
    lines.append(team_line(1, "Team One", [1], "1.0", "1.0"))
    lines.append(team_line(2, "Team Two", [2], "0.0", "0.0"))
    lines.append(team_line(3, "Team Three", [3], "2.0", "1.0"))
    lines.append(player_line(1, "One, Player", 2400, "0.0", [(0, "-", "U")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.0", [(3, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.0", [(2, "w", "1")]))
    lines.append("320  1.0  1.0 001")

    chessfile = parse(lines)

    assert chessfile.get_status() == 0
    assert "info" not in chessfile.chessjson["status"]
    tournament = chessfile.get_tournament(1)
    assert {competitor["cid"]: (competitor["matchPoints"], competitor["gamePoints"])
            for competitor in tournament["competitors"]} == {
        1: (Decimal("1.0"), Decimal("1.0")),
        2: (Decimal("0.0"), Decimal("0.0")),
        3: (Decimal("2.0"), Decimal("1.0")),
    }

    # The same file with the bye in the 001 points too still agrees.
    lines[7] = player_line(1, "One, Player", 2400, "1.0", [(0, "-", "U")])
    chessfile = parse(lines)
    assert chessfile.get_status() == 0
    assert "info" not in chessfile.chessjson["status"]


def test_a_correct_record_310_still_reads():
    """Two team files whose record 310 totals are the ones their results give.

    The second names no bye for round 3 in record 320, which is a 000 in that
    round's field.
    """
    for lines in [
        two_teams(2, ["4.0", "0.0"], ["3.0", "1.0"]),
        three_teams_with_an_announced_bye(["3.0", "1.0", "2.0"], ["2.5", "2.5", "3.0"], [3, 2, 0]),
    ]:
        chessfile = parse(lines)
        assert chessfile.get_status() == 0
        assert "info" not in chessfile.chessjson["status"]
