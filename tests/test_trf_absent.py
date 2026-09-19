# -*- coding: utf-8 -*-
"""
Record XXZ, the competitors who are not there.

XXZ is one of the XX- extension records rather than one of the numbered records of
TRF-2026, and it decides a pairing. parse_trf_absent() clears the "present" flag of every
pairing number the record names, and that flag is what a pairing engine consults before it
seats anybody: crosstable.list_edges() turns it into "rfp" (ready for pairing), and a
competitor who is not ready for pairing is left out of the field for the round. The number
of boards changes, who meets whom changes, and if the record leaves an odd number of
players behind, somebody gets a bye who would not otherwise have had one.

So a record read wrongly here does not produce a wrong number in a table. It produces a
different round.

The record is a list of pairing numbers separated by spaces, commas or slashes, in any
mixture:

    XXZ 3 6
    XXZ 3,6
    XXZ 3/6

Two things are worth stating about the parser plainly, because the record's name suggests
otherwise. First, self.trfrecords describes XXZ as "Will not meet", which reads as a
statement about a pair of competitors -- that is record 260's job, prohibited pairings,
and it is not what this parser does. XXZ takes each number on its own and marks that
competitor absent, so it is not paired with anybody at all. Second, the flag it sets is on
the competitor dictionaries the tournament itself carries, not on a copy, so nothing
further has to be done for the pairing to see it.

The numbers are checked as they are read, by check_player(), so a number that names nobody
is a diagnostic naming the record and the number rather than a KeyError from further in.

Not one of the 6,000 fixtures in tests/corpus carries an XXZ record, so the corpus cannot
reach this parser. Nothing writes the record either -- its entry in self.trfrecords writes
with output_trf_noop -- so a file has to be written by hand to carry one, and these tests
are the only place one is.
"""
import os

import pytest

from gacrux import gacruxexeptions
from gacrux import trf2json
from gacrux.pairingdutch import pairing_dutch


# Eight players, two rounds played, round three to pair. The file is the fixture the
# no-colour-preference regression uses, so it is a position the engine is known to pair
# cleanly, which is what makes "and now it pairs differently" a statement about record XXZ
# rather than about the position.
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "no_colour_preference.trf")


def tournament_lines(records):
    with open(FIXTURE, encoding="utf-8") as handle:
        return handle.read().rstrip("\n").split("\n") + records


def parse(records):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(tournament_lines(records)), True)
    return chessfile


def presence(records):
    tournament = parse(records).get_tournament(1)
    return {competitor["cid"]: competitor["present"] for competitor in tournament["competitors"]}


ALL_EIGHT_PRESENT = {n: True for n in range(1, 9)}
WITHOUT_THREE_AND_SIX = {**ALL_EIGHT_PRESENT, 3: False, 6: False}


def test_a_tournament_with_no_xxz_record_has_everybody_present():
    """The starting point, so that every assertion below is a difference and not a default.

    parse_trf_player() sets "present" to True for every player it reads. Without this
    test, a record XXZ that did nothing at all would be indistinguishable from one that
    worked, in any test that only looked at the players it named.
    """
    assert presence([]) == ALL_EIGHT_PRESENT


@pytest.mark.parametrize(
    "record",
    [
        "XXZ 3 6",
        "XXZ 3,6",
        "XXZ 3/6",
        "XXZ 3, 6",
        "XXZ 3/6 ",
    ],
    ids=["spaces", "commas", "slashes", "comma-and-space", "trailing-space"],
)
def test_the_competitors_the_record_names_are_marked_absent(record):
    """All three separators mean the same thing, and so does any mixture of them.

    parse_trf_absent() replaces every comma and every slash with a space and then splits,
    so the three forms are the same list of numbers. Each is pinned separately because
    each is a separate line of the parser: drop the comma replacement and "3,6" becomes
    one unreadable token, drop the slash replacement and "3/6" does.

    The last two cases cover what the replacement leaves behind. A comma followed by a
    space becomes two spaces and an empty token between them, and a trailing separator
    leaves an empty token at the end; both are parsed as the number 0 and skipped, so a
    file written with either still names players 3 and 6 and nobody else.

    The assertion is on all eight competitors, not on the two named. A parser that marked
    everybody absent would satisfy any check confined to players 3 and 6.
    """
    assert presence([record]) == WITHOUT_THREE_AND_SIX


def test_a_pairing_number_of_zero_names_nobody():
    """0 is skipped rather than looked up, which is what makes an empty token harmless.

    The parser tests "if num > 0" before it does anything with a number, and parse_int()
    turns an empty string into 0. So a record's padding, its separators and an explicit 0
    all take the same path out. There is no competitor 0 to mark -- the pairing engine
    uses cid 0 for the dummy opponent that gives somebody a bye -- so a reader that looked
    it up would fail on the ordinary well-formed record rather than on a malformed one.
    """
    assert presence(["XXZ 0 3"]) == {**ALL_EIGHT_PRESENT, 3: False}


def test_an_unknown_pairing_number_is_reported_as_an_input_error():
    """9 names nobody in an eight-player event, and the reader says so and stops.

    parse_trf_absent() calls check_player() before it touches the competitor, so the
    number is resolved against the players the file actually declared. Without that call
    the next line indexes self.pcompetitors with it and the user gets "KeyError: 9" out of
    the middle of the reader, naming neither the record nor the numbers that would have
    been right.

    The message is the one every other record's pairing numbers get from
    check_pairing_number(), so record XXZ is not a second dialect of the same complaint,
    and status 401 is set as well as the exception raised, so a caller that catches the
    error still sees the file marked unread.
    """
    chessfile = trf2json.trf2json()

    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        chessfile.parse_file("\n".join(tournament_lines(["XXZ 9"])), True)

    assert str(excinfo.value) == "Record XXZ names player 9, the tournament has 8 players (1 - 8)"
    assert chessfile.get_status() == 401


def pair_round_three(records):
    """Pair round three of the fixture, with whatever records the test added.

    The parameters are the ones tests/test_no_colour_preference_crash.py uses on the same
    file: white on top, no experimental options, and a real pairing rather than a check.
    """
    tournament = parse(records).get_tournament(1)
    tournament["topColor"] = "w"
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    brackets = pairing_dutch(tournament, 3, params).compute_pairing(False, 0)
    pairs = [pair for bracket in brackets if bracket and "pairs" in bracket for pair in bracket["pairs"]]
    return [(pair["w"], pair["b"]) for pair in pairs]


def test_an_absent_competitor_is_left_out_of_the_pairing():
    """What the flag is for: two competitors marked absent, and round three loses a board.

    Eight players pair into four boards with nobody left over. Mark players 3 and 6 absent
    and six players remain, so the round is three boards, and neither 3 nor 6 appears on
    any of them. The other six are all still paired, so the record removed two competitors
    and did not disturb the rest of the field.

    This is the assertion that makes the "present" flag more than a value in a dictionary.
    Everything above tests that the reader sets it; this tests that setting it is what
    keeps a competitor out of a round, which is the whole reason the record exists.
    """
    before = pair_round_three([])
    after = pair_round_three(["XXZ 3 6"])

    assert sorted(cid for pair in before for cid in pair) == list(range(1, 9))
    assert len(before) == 4

    assert len(after) == 3
    seated = sorted(cid for pair in after for cid in pair)
    assert seated == [1, 2, 4, 5, 7, 8]


def test_leaving_an_odd_number_of_competitors_gives_somebody_a_bye():
    """One competitor absent, seven left, and the engine has to seat one of them alone.

    A pairing engine handed an odd field pairs the last competitor against the dummy
    competitor cid 0, which is how a bye is expressed. So record XXZ does not only remove
    the competitor it names: it decides whether anybody else gets a bye at all, and in
    this position that is player 8.

    It is worth a test of its own because it is the consequence a file writer is least
    likely to expect from a record that reads like a note about who is not coming, and
    because it fails differently from the test above -- a reader that ignored the record
    entirely would pair four full boards here and no bye.
    """
    after = pair_round_three(["XXZ 3"])

    assert len(after) == 4
    assert sorted(cid for pair in after for cid in pair) == [0, 1, 2, 4, 5, 6, 7, 8]
    assert (8, 0) in after   # player 8 is the one left over, paired against the dummy
