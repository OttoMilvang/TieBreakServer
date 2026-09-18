# -*- coding: utf-8 -*-
"""TRF-2026 record 320, the pairing-allocated-bye section, in a file with no teams.

The bye section of TRF-2026 reads: full-, half- and zero-point byes are recorded
"for both individuals and teams (240); pairing-allocated-bye (320) just for
teams". Record 320 sits under the "Teams" heading, and its identifier fields are
each named "Team Pairing Number", so a file with no 013 or 310 record gives them
nothing to name.

Read in such a file the record used to reach update_individualbye_list, which
takes the result letter off each bye-list entry under ``score``. parse_trf_bye
writes that key for records 240 and 330; parse_trf_pab wrote the point values
without it, so the lookup raised KeyError('score'). That is raised from
parse_file after read_all_lines has returned, outside the handler that turns an
unreadable record into "Error in trf-file, line N", so it arrived as status 510
rather than as a report about the record.

The record is now refused as 401, alongside the two other conditions
parse_trf_pab already reports that way, so the bye list never carries a
pairing-allocated bye for an individual competitor at all.
"""
import pytest

from gacrux import trf2json
from gacrux.gacruxexeptions import GacruxInputError

# Record 320 (parse_trf_pab): match points in columns 5-8, game points in 10-13,
# then team pairing numbers three wide from column 15, one per round in turn.
RECORD_320_FOR_NUMBER_1 = "320 1.0  1.0    1"


def fixture_lines():
    """The eight-player, two-round individual tournament used by the reader tests.

    Every player has a game in both rounds and the declared totals reconcile, so
    the record under test is the only thing wrong with the file.
    """
    with open("tests/fixtures/no_colour_preference.trf", encoding="latin1") as handle:
        return handle.read().rstrip("\n").split("\n")


def read(extra_lines):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(fixture_lines() + extra_lines), 0)
    return chessfile


def test_a_record_320_without_a_team_section_is_refused():
    """Status 401 and a message naming the record, not a KeyError from the bye list."""
    with pytest.raises(GacruxInputError) as excinfo:
        read([RECORD_320_FOR_NUMBER_1])

    message = str(excinfo.value)
    assert "320" in message
    assert "team tournaments only" in message


def test_the_points_half_of_a_record_320_is_refused_on_its_own():
    """The refusal is on the record, not on the competitors it happens to name.

    The loop that reads the pairing numbers starts past the two point fields, so
    this record names nobody. It still declares what a PAB is worth, and a value
    for a bye no individual competitor can be given is as wrong as the bye.
    """
    with pytest.raises(GacruxInputError) as excinfo:
        read(["320 1.0  1.0"])

    assert "320" in str(excinfo.value)


def test_no_pairing_allocated_bye_reaches_the_individual_bye_list():
    """The record is refused before it can write to the list.

    update_individualbye_list returns early for a team tournament, so an entry of
    type "P" is only ever read back in an individual one. Refusing the record
    keeps that combination from arising, which is why the entry needs no result
    letter of its own.
    """
    chessfile = trf2json.trf2json()
    with pytest.raises(GacruxInputError):
        chessfile.parse_file("\n".join(fixture_lines() + [RECORD_320_FOR_NUMBER_1]), 0)

    assert [bye for bye in chessfile.byelist if bye["type"] == "P"] == []


def test_a_record_240_still_reaches_the_individual_bye_list():
    """The refusal is specific to record 320.

    Record 240 is declared for individuals as well as teams, so it keeps working,
    and it is what supplies the ``score`` key that record 320 lacked. A record 240
    of type "H" is worth a draw, which is "D".
    """
    byelist = read(["240 H   1    2"]).byelist

    assert len(byelist) == 1
    assert byelist[0]["type"] == "H"
    assert byelist[0]["score"] == "D"
    assert byelist[0]["round"] == 1
    assert byelist[0]["competitor"] == 2


def test_a_record_240_that_contradicts_a_game_played_as_black_is_reported():
    """Player 1 is Black in round 1 against player 5 and won.

    A record 240 giving player 1 a half-point bye in that round contradicts
    the game. It was only compared with the White side of each game, so the
    game was missed, a second round-1 entry was added for player 1 and the
    score went from 1.5 to 1.0.
    """
    chessfile = read(["240 H   1    1"])

    status = chessfile.chessjson["status"]
    assert status["code"] == 405
    assert any("competitor 1" in message for message in status["error"])
    tournament = chessfile.get_tournament(1)
    roundone = [game for game in tournament["gameList"] if game["round"] == 1
                and 1 in (chessfile.get_result_cid(game, "white"), chessfile.get_result_cid(game, "black"))]
    assert len(roundone) == 1


def read_team(extra_lines):
    """Nine teams of two boards, seven rounds, declared in record 310 and with no 320."""
    with open("tests/fixtures/fideteam_nocolor.trf", encoding="latin1") as handle:
        chessfile = trf2json.trf2json()
        chessfile.parse_file(handle.read() + "\n" + "\n".join(extra_lines), 0)
    return chessfile


def test_a_record_320_naming_nobody_adds_no_bye():
    """The points half of the record without a competitor half, in a team file.

    The loop that reads the pairing numbers starts past the two point fields, so
    a record that stops after them names no competitor and there is no bye to
    add. It still declares what a PAB is worth, so it is not an error.
    """
    chessfile = read_team(["320 1.0  1.0"])

    assert chessfile.byelist == []
    assert chessfile.get_status() == 0
