# -*- coding: utf-8 -*-
"""
The standing of a team tournament written with the older TRF record 013.

Record 013 is the team section of a file that predates TRF-2026: a team name and the
pairing numbers of its players, and nothing else. It has no score columns, so unlike
record 310 it declares no standing -- and the reader had none to put in its place.
``update_team_score()``, the function the reader calls for exactly this case, was::

    def update_team_score(self, tournament):
        for competitor in tournament["competitors"]:
            pass

so every team of a legacy team file was published on 0.0 match points and 0.0 game
points. The same tournament written with record 310 was published on the totals that
record declares, which the reader recomputes and checks. Two spellings of one event, two
different standings, no message either way.

Nothing inside the engine noticed, which is why this survived: the pairing and the
tie-breaks derive their own scores from the match list and the game list and never read
these fields. What reads them is whatever the reader hands the chessjson to, and a zero
there is indistinguishable from a team that has lost every match.

The totals written here are the ones ``validate_team_scores()`` recomputes a record 310
against, from the same function, so the two records agree by construction rather than by
coincidence. That is the property most of these tests assert: the standing the reader
publishes for a 013 file is the standing a 310 file would have had to declare to agree
with its own results.

Which rounds count towards a standing is a separate question, and it is not settled
here. ``team_score_totals()`` counts a match whose round the file has reached, plus a
pairing-allocated bye in any round, and that is the rule these tests were written
against -- not a rule they argue for.
"""
import decimal

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


def team_line_310(cid, name, players, matchpoints, gamepoints):
    # Record 310, at the columns TRF-2026 gives it: the pairing number in 5-7, the name
    # in 9-40, the match points in 55-60, the game points in 62-67, the rank in 69-71 and
    # the players from 74 on.
    line = list(" " * 73)
    line[0:3] = "310"
    line[4:7] = "%3d" % cid
    line[8 : 8 + len(name)] = name
    line[54:60] = "%6s" % matchpoints
    line[61:67] = "%6s" % gamepoints
    line[68:71] = "%3d" % cid
    return "".join(line) + " ".join(["%4d" % player for player in players])


def team_line_013(cid, name, players, matchpoints, gamepoints):
    # Record 013: the name in 5-36 and the players from 37 on. There is nowhere to put a
    # standing, so the totals this is handed are ignored -- which is the whole point. The
    # pairing number is not written either: a 013 team is numbered by the order the
    # records appear in, so the caller passes the numbers it expects them to be given.
    return "013 " + "%-32s" % name + "".join(["%4d " % player for player in players])


TEAM_LINE = {"013": team_line_013, "310": team_line_310}

VALUE = {"1": "1.0", "+": "1.0", "U": "1.0", "=": "0.5", "0": "0.0", "-": "0.0"}


def two_teams(record, rounds, matchpoints, gamepoints, byeround=False):
    """The two-team, two-board event of the record 310 tests, in either team record.

    Round 1 is team 1 as the white team and team 1 wins it 1.5 - 0.5; round 2 is team 2
    as the white team and team 1 wins it 1.5 - 0.5 again. A third round, with
    `byeround`, is one in which both teams sat out and every player recorded it.

    The totals are the standing after those rounds. Record 310 declares them and the
    reader checks them; record 013 cannot declare them and the reader now works them out.
    """
    games = [
        # player 1, team 1                 player 2, team 1
        [(3, "w", "1"), (3, "b", "=")],    [(4, "b", "="), (4, "w", "1")],
        # player 3, team 2                 player 4, team 2
        [(1, "b", "0"), (1, "w", "=")],    [(2, "w", "="), (2, "b", "0")],
    ]
    if rounds > 2 and byeround:
        # Nobody was paired at all: every player of both teams records "U", the TRF code
        # for a pairing-allocated bye, against no opponent.
        for game in games:
            game.append((0, "-", "U"))
    points = [sum((decimal.Decimal(VALUE[game[2]]) for game in game), decimal.Decimal("0.0"))
              for game in games]

    team_line = TEAM_LINE[record]
    lines = ["012 Legacy team totals", "042 2026-03-01", "XXR %d" % rounds, "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2], matchpoints[0], gamepoints[0]))
    lines.append(team_line(2, "Team Two", [3, 4], matchpoints[1], gamepoints[1]))
    for startno, name in enumerate(["One", "Two", "Three", "Four"]):
        lines.append(player_line(startno + 1, name + ", Player", 2400 - 100 * startno,
                                 "%.1f" % points[startno], games[startno]))
    return lines


def parse(lines):
    chessfile = trf2json.trf2json()
    # verbose off: this is how a program that is handed a file reads it.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def standing(chessfile):
    tournament = chessfile.get_tournament(1)
    return {competitor["cid"]: (competitor["matchPoints"], competitor["gamePoints"])
            for competitor in tournament["competitors"]}


def points(match, game):
    return (decimal.Decimal(match), decimal.Decimal(game))


def test_a_legacy_team_file_publishes_the_standing_its_results_give():
    """The regression. Two rounds, team 1 wins both 1.5 - 0.5, and it is 4.0 - 0.0.

    A win is worth two match points under the default team score system, so the match
    points are 4.0 and 0.0, and the game points are the totals the players' own 001
    records report: 3.0 and 1.0. Before the fix every one of those four numbers was 0.0.
    """
    chessfile = parse(two_teams("013", 2, ["4.0", "0.0"], ["3.0", "1.0"]))

    assert chessfile.get_status() == 0
    assert standing(chessfile) == {1: points("4.0", "3.0"), 2: points("0.0", "1.0")}


def test_the_two_team_records_publish_the_same_standing():
    """The property, rather than the numbers: one event, two spellings, one standing.

    The record 310 file declares the totals and is accepted, which is the reader saying
    those totals are the ones the results give. The record 013 file has no way to declare
    them and must arrive at the same place.
    """
    modern = parse(two_teams("310", 2, ["4.0", "0.0"], ["3.0", "1.0"]))
    legacy = parse(two_teams("013", 2, ["4.0", "0.0"], ["3.0", "1.0"]))

    assert modern.get_status() == 0 and legacy.get_status() == 0
    assert standing(legacy) == standing(modern)


def test_a_round_every_team_sat_out_is_in_the_standing():
    """Round 3 pairs nobody and every player writes "U" against no opponent.

    Each team's round 3 is a pairing-allocated bye worth one match point, so the standing
    is 5.0 and 1.0. The round has no match between two teams in it, so what says it
    happened is that the players recorded it.
    """
    legacy = parse(two_teams("013", 3, ["5.0", "1.0"], ["5.0", "3.0"], byeround=True))
    modern = parse(two_teams("310", 3, ["5.0", "1.0"], ["5.0", "3.0"], byeround=True))

    assert legacy.get_status() == 0 and modern.get_status() == 0
    assert standing(legacy) == {1: points("5.0", "5.0"), 2: points("1.0", "3.0")}
    assert standing(legacy) == standing(modern)


def test_a_declared_standing_is_still_the_declared_one():
    """The control: filling in a missing standing must not overwrite a declared one.

    Record 310 carries its own totals and the reader checks them against the results;
    it must not be handed computed ones instead, or the check would be comparing a
    number with itself and a file whose standings contradict its results would pass.
    """
    modern = parse(two_teams("310", 2, ["4.0", "0.0"], ["3.0", "1.0"]))

    assert standing(modern) == {1: points("4.0", "3.0"), 2: points("0.0", "1.0")}
