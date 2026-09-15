# -*- coding: utf-8 -*-
"""TRF-2026 record 250, the accelerated rounds section.

    250  1.0  1.0   1   1    1    4

reads as "for round 1, competitors 1 to 4 carry 1.0 match points and 1.0 game
points on top of what they have scored". The two fields are point values, and
parse_trf_accelerated reads them into the accelerated value under matchPoints
and gamePoints. tiebreak.get_accelerated adds the same two fields to a
competitor's score, so the record decides a scoregroup and therefore a pairing.

The writer has to put back what the reader took in, because that is the only
thing that makes a file readable again by whoever is handed it.
"""
from decimal import Decimal

from gacrux import trf2json

RECORD_250 = "250  1.0  1.0   1   1    1    4"


def read(extra_lines):
    with open("tests/fixtures/no_colour_preference.trf", encoding="latin1") as handle:
        lines = handle.read().rstrip("\n").split("\n")
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines + extra_lines), 0)
    return chessfile


def written_250_lines(chessfile):
    written = chessfile.output_file(chessfile.chessjson["event"], 1, 1)
    return [line for line in written.split("\n") if line.startswith("250")]


def test_record_250_is_read_as_point_values():
    values = read([RECORD_250]).get_tournament(1)["accelerated"]["values"]

    assert len(values) == 1
    assert values[0]["matchPoints"] == Decimal("1.0")
    assert values[0]["gamePoints"] == Decimal("1.0")
    assert values[0]["firstRound"] == 1 and values[0]["lastRound"] == 1
    assert values[0]["firstCompetitor"] == 1 and values[0]["lastCompetitor"] == 4


def test_a_record_250_survives_being_written_back_out():
    """The written record used to state an acceleration of zero.

    The writer looked the two point values up in the score system, which is keyed
    by result letter -- "W", "D", "L" -- so a Decimal point value matched no key
    and the 0.0 default was written in its place. Every accelerated value came
    out of the writer as "250  0.0  0.0 ...", which is not an acceleration at
    all, and the file then paired its first round differently from the one it was
    written from.
    """
    chessfile = read([RECORD_250])

    assert written_250_lines(chessfile) == [RECORD_250]


def test_a_tournament_without_a_record_250_writes_none():
    assert written_250_lines(read([])) == []
