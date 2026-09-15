# -*- coding: utf-8 -*-
"""
Records 162 and 362, the game and the team match score system.

A TRF result is a letter, not a number. Record 162 says what those letters are worth in
game points and record 362 says what they are worth in team match points, and everything
downstream reads the answer: the totals the standings are ordered by, the score brackets
a Swiss pairing works in, and every points-based tie-break. A score system read one field
wrong is a tournament scored wrong, silently, from the first round.

Both records are parsed by the same function, parse_trf_scoresystem(), which reads the
line as a series of nine-character fields, the first of them beginning at the sixth
character of the line. The numbers below are the offsets the parser indexes with, counting
the "1" of "162" as offset 0:

    162  W 1.0    D 0.5    L 0.0    A 0.0    P 1.0    X 0.5
         ^        ^        ^        ^        ^        ^
         5        14       23       32       41       50

Each field is one letter, four characters of points, and four spaces. Only the letter at
the head of a field is looked at, only four characters of points are read, and a letter
that is not in the record's own table is passed over without a word.

The table is the part worth pinning, because it is crosswise:

    TRF letter   W    D    L    P    A    X
    score key    W    D    L    P    Z    A

The record's letters are TRF *result codes* and the keys are the reader's internal result
classes, and those two vocabularies do not line up. In self.results, the result code "A"
(absent) scores as class "Z" and the result code "X" scores as class "A", so field "A" of
record 162 sets key "Z" and field "X" sets key "A". output_trf_gamescore() writes the two
back out under the letters they came from, so the record round-trips; but read out of
context, "the A field sets Z and the X field sets A" is exactly the sort of thing a later
tidy-up silently straightens out, which is what the first two tests below are here to
prevent.

None of this shows in the fixtures: not one of the 6,000 files in tests/corpus carries a
record 162 or a record 362, so the corpus cannot reach either parser. Both are covered
here and nowhere else.
"""
import decimal
import os

import pytest

from gacrux import gacruxexeptions
from gacrux import trf2json


# The score system a file with no 162 record gets, from scoresystem.default_score["game"].
# The three played results are worth points; the five unplayed ones are held as the result
# they are worth, so that everything asking "what class of result is this" gets an answer
# rather than a number it has to recognise. F is a full-point bye, H a half-point bye, Z a
# zero-point bye, P a pairing-allocated bye and U an unknown result.
DEFAULT_GAME_SCORE_SYSTEM = {
    "W": decimal.Decimal("1.0"),
    "D": decimal.Decimal("0.5"),
    "L": decimal.Decimal("0.0"),
    "F": "W",
    "H": "D",
    "Z": decimal.Decimal("0.0"),
    "P": "W",
    "A": "D",
    "U": "Z",
}

# And the match system a team file with no 362 record gets, from default_score["match"].
# A match win is two points and a draw one. The four "G" keys are the game points of an
# unplayed match: "W*" means "a win in game points, once per board", which get_score()
# resolves against the team size.
DEFAULT_MATCH_SCORE_SYSTEM = {
    "W": decimal.Decimal("2.0"),
    "D": decimal.Decimal("1.0"),
    "L": decimal.Decimal("0.0"),
    "F": "W",
    "H": "D",
    "Z": decimal.Decimal("0.0"),
    "P": "D",
    "A": "D",
    "U": "Z",
    "FG": "W*",
    "HG": "D*",
    "ZG": "Z*",
    "PG": "P*",
}


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
    # Record 310, at the columns TRF-2026 gives it: the team pairing number in 5-7, the
    # name from 9, the match points in 55-60, the game points in 62-67, the rank in 69-71
    # and the player start numbers from 73 on.
    line = list(" " * 73)
    line[0:3] = "310"
    line[4:7] = "%3d" % cid
    line[8 : 8 + len(name)] = name
    line[54:60] = "%6s" % matchpoints
    line[61:67] = "%6s" % gamepoints
    line[68:71] = "%3d" % cid
    return "".join(line) + " ".join(["%4d" % player for player in players])


def four_players(records):
    """Four players, two rounds, every game played to a decisive result or a draw.

    Nothing here is worth a bye, a forfeit or an absence, so no result of class Z, P or A
    is ever scored. That matters: update_gamescore() checks every player's reported total
    against the declared score system and refuses the file if none of them adds up, so a
    test that gives the Z, P or A keys an unusual value needs a tournament in which no
    result of that class occurs. Player 1 and player 3 finish on 1.5, players 2 and 4 on
    0.5, which is what a win plus a draw and a loss plus a draw are worth in the ordinary
    1 / 0.5 / 0 system.
    """
    lines = ["012 Game score system", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(2, "w", "1"), (3, "b", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "0.5", [(1, "b", "0"), (4, "w", "=")]))
    lines.append(player_line(3, "Three, Player", 2200, "1.5", [(4, "w", "1"), (1, "w", "=")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.5", [(3, "b", "0"), (2, "b", "=")]))
    return lines + records


def four_teams(records, matchpoints=("2.0", "2.0", "0.0", "4.0")):
    """Four teams of two, two rounds, and whatever match points record 310 should declare.

    Round 1 is team 1 against team 3 and team 2 against team 4; round 2 is team 1 against
    team 4 and team 2 against team 3. Team 1 wins its first match 2-0 and loses its second
    0.5-1.5; team 2 loses 0.5-1.5 and wins 1.5-0.5; team 4 wins both. So the matches are
    two wins for team 4, one each for teams 1 and 2, and none for team 3, and the game
    points are 2.5, 2.0, 0.5 and 3.0 whatever a match is worth.

    The match points are a parameter because they are what record 362 decides. Under the
    default 2 / 1 / 0 they are 2.0, 2.0, 0.0 and 4.0; under a 3 / 1 / 0 system they are
    3.0, 3.0, 0.0 and 6.0. validate_team_scores() checks record 310 against the matches
    it can see, so declaring one set of match points and the other score system is a file
    the reader refuses.
    """
    lines = ["012 Team match score system", "042 2026-03-01", "XXR 2", "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2], matchpoints[0], "2.5"))
    lines.append(team_line(2, "Team Two", [3, 4], matchpoints[1], "2.0"))
    lines.append(team_line(3, "Team Three", [5, 6], matchpoints[2], "0.5"))
    lines.append(team_line(4, "Team Four", [7, 8], matchpoints[3], "3.0"))
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
    chessfile.parse_file("\n".join(lines), True)
    return chessfile


def test_162_maps_its_letters_crosswise_onto_the_score_system_keys():
    """The A field sets key Z and the X field sets key A. That is not a typo.

    The three values are chosen so that none of them is the value of any other key: 0.3,
    0.7 and 0.9 are not 1.0, not 0.5 and not 0.0. That is deliberate. update_gamescore()
    reads a P or an A worth exactly what a win, a draw, a loss or a zero-point bye is
    worth back into that result, so a record written with the ordinary values -- which is
    what the shipped fixture tests/fixtures/no_colour_preference.trf has -- comes out of
    the reader with P and A holding letters, and the crosswise mapping leaves no trace to
    check. A later test covers that case; this one keeps the three values distinct so the
    mapping is visible in the parsed structure:

        field A 0.3  ->  key Z = 0.3     what a TRF result code "A" (absent) is worth
        field P 0.7  ->  key P = 0.7     what a pairing-allocated bye is worth
        field X 0.9  ->  key A = 0.9     what a TRF result code "X" is worth

    The rest of the dictionary is the default: W, D and L are the same values the defaults
    already hold, and F, H and U cannot be set by record 162 at all.
    """
    chessfile = parse(four_players(["162  W 1.0    D 0.5    L 0.0    A 0.3    P 0.7    X 0.9"]))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == {
        **DEFAULT_GAME_SCORE_SYSTEM,
        "Z": decimal.Decimal("0.3"),
        "P": decimal.Decimal("0.7"),
        "A": decimal.Decimal("0.9"),
    }


def test_162_is_written_back_out_under_the_letters_it_was_read_from():
    """The crosswise mapping round-trips, which is the reason to believe it is deliberate.

    output_trf_gamescore() writes key Z into the A field and key A into the X field, the
    exact inverse of what the reader did. So a file read and written again comes back
    byte for byte, and a change to either half alone loses the value of a result on the
    way through. Pinning the pair together says that neither half may be "corrected" on
    its own.

    The line below is also the column layout, stated once as a value rather than as a
    comment: the letters land on offsets 5, 14, 23, 32, 41 and 50, and each carries four
    characters of points.
    """
    line = "162  W 1.0    D 0.5    L 0.0    A 0.3    P 0.7    X 0.9"
    chessfile = parse(four_players([line]))

    written = chessfile.output_trf_gamescore(chessfile.get_tournament(1), "162")

    assert written == line + "\n"


def test_162_keeps_a_value_that_is_already_the_value_of_a_result_as_that_result():
    """The record the shipped fixture carries, and why the mapping is invisible in it.

    tests/fixtures/no_colour_preference.trf ends with exactly this line. Every value in
    it is a value some other key already has: A 0.0 is what a loss is worth, P 1.0 what a
    win is worth, X 0.5 what a draw is worth. update_gamescore() reads such a value back
    into the result rather than keeping the number, so that anything asking what class of
    result an unplayed game is gets a letter, and anything asking what it is worth follows
    the letter to a number.

    Key Z keeps its 0.0 as a number: it is one of the four results the read-back table is
    built from, not one of the five it rewrites. Key P becomes "W" and key A becomes "D".
    So the parsed system is indistinguishable from the default, and the whole of the
    crosswise mapping in this file is the 0.0 that reached Z from the A field.
    """
    chessfile = parse(four_players(["162  W 1.0    D 0.5    L 0.0    A 0.0    P 1.0    X 0.5"]))

    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == DEFAULT_GAME_SCORE_SYSTEM


def test_162_passes_over_a_letter_that_is_not_in_its_table():
    """F, H and Z are keys of the score system but not fields of record 162.

    The reader's table has six entries, W D L P A X, and any other letter at the head of a
    field is skipped without a status code and without a message. That is worth a test in
    both directions. A file writer who reasons from the score system rather than from the
    record -- "there is an H key, so I will write an H field" -- gets the default value of
    a half-point bye and no warning that the line was ignored; and the letter "Z" is the
    trap in the middle of it, because record 162 sets key Z from its A field and ignores
    a field actually written Z.

    The three values below are as loud as the fields allow, so nothing here could be
    mistaken for the default it is being compared against.
    """
    chessfile = parse(four_players(["162  W 1.0    D 0.5    L 0.0    F 9.9    H 8.8    Z 7.7"]))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == DEFAULT_GAME_SCORE_SYSTEM


def test_162_only_sees_a_letter_that_starts_a_nine_character_field():
    """The record is read by column, not by whitespace, and a field one short is lost.

    The line below is the same record as the others with one space missing before the P,
    so the P sits at offset 31 rather than 32 -- close enough to read at a glance, and the
    reader does not see it at all: it looks at offsets 5, 14, 23 and 32, finds a space at
    32, and skips it. The pairing-allocated bye is then worth what a win is worth, by
    default, and nothing says the file asked for anything else.

    The value is 0.7, which no other key holds, so the assertion below distinguishes "the
    field was not read" from "the field was read": a P key of 0.7 would be the value the
    line asks for and a P key of "W" is the default it actually gets.
    """
    chessfile = parse(four_players(["162  W 1.0    D 0.5    L 0.0   P 0.7"]))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == DEFAULT_GAME_SCORE_SYSTEM


def test_162_reads_exactly_four_characters_of_points():
    """A fifth character of points is not read, and the value is quietly cut short.

    The points of a field are the four characters after the letter, which is what the
    writer's "%4.1f" produces and what leaves room for "10.0". A file that writes 0.79 in
    a field puts the "9" in the first column of the next field's padding, and the reader
    takes " 0.79"[:4] -- 0.7.

    The digit does not come back later. fill_default_scoresystem() rounds every value to
    the number of decimals W, D and L are written to, which here is one, so a reader that
    took all five characters would score the pairing-allocated bye at 0.8. Neither is what
    the file wrote, and neither raises a status code, so the two-decimal value has simply
    no way to reach the tournament. The behaviour is pinned rather than changed, because
    widening the field would change what every existing record 162 means in the column
    after the one it declares.
    """
    chessfile = parse(four_players(["162  W 1.0    D 0.5    L 0.0    P 0.79"]))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == {
        **DEFAULT_GAME_SCORE_SYSTEM,
        "P": decimal.Decimal("0.7"),
    }


def test_362_declares_what_a_team_match_is_worth():
    """A 3 / 1 / 0 match system, and the file only reads at all because 362 says so.

    Teams 1 and 2 win one match each, team 3 none and team 4 both. Under the default
    2 / 1 / 0 that is 2.0, 2.0, 0.0 and 4.0 match points; the record 310 lines below
    declare 3.0, 3.0, 0.0 and 6.0 instead, which is the same standings scored 3 / 1 / 0.
    validate_team_scores() compares the two, so the declared match points are only
    consistent with the matches when record 362 has changed what a win is worth -- which
    makes this the shortest statement of what the record is for. A reader that dropped
    record 362 could not read this file at all.

    Only W and D are declared. L keeps the default 0.0, and the five keys record 362
    cannot set keep the defaults as well.
    """
    chessfile = parse(four_teams(["362  W 3.0    D 1.0    L 0.0"],
                                 matchpoints=("3.0", "3.0", "0.0", "6.0")))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["match"] == {
        **DEFAULT_MATCH_SCORE_SYSTEM,
        "W": decimal.Decimal("3.0"),
        "D": decimal.Decimal("1.0"),
    }


def test_362_leaves_the_game_score_system_alone():
    """The same file, and the game system is untouched by the record next to it.

    Record 362 and record 162 are one function apart -- parse_trf_matchscore() and
    parse_trf_gamescore() differ only in the string they pass -- so the way this goes
    wrong is that a team file's match points reach the game score system, or the other way
    about. In this tournament that would be visible immediately: a match win is 3.0 here
    and a game win must still be 1.0, because the individual results the eight players
    report are ordinary wins, draws and losses adding up to 1.5, 1.0, 0.5 and so on.
    """
    chessfile = parse(four_teams(["362  W 3.0    D 1.0    L 0.0"],
                                 matchpoints=("3.0", "3.0", "0.0", "6.0")))

    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == DEFAULT_GAME_SCORE_SYSTEM


def test_the_same_team_file_without_362_is_refused():
    """The other half of the test above: drop the record and the file no longer reads.

    Without record 362 the reader scores the matches 2 / 1 / 0, gets 2.0, 2.0, 0.0 and 4.0
    match points, and finds record 310 claiming 3.0, 3.0, 0.0 and 6.0. It says so. This is
    here so that the file used above is known to depend on record 362 for its result,
    rather than being a file that would have parsed either way -- which is the difference
    between a test of record 362 and a test of nothing at all.

    The reader reports the disagreement instead of refusing the event, because it cannot
    tell a missing score system from a standing an arbiter changed on purpose. Either way
    the totals move, which is what this test is here to detect.
    """
    chessfile = parse(four_teams([], matchpoints=("3.0", "3.0", "0.0", "6.0")))

    message = "; ".join(chessfile.chessjson["status"]["info"])
    assert "310" in message                                # the record that disagrees
    assert "team 1 declares 3.0 match points" in message   # what the file said
    assert "the matches give 2.0" in message               # what 2 / 1 / 0 makes of it


def test_362_maps_its_letters_the_same_crosswise_way():
    """Record 362 shares the translation table, so its A field sets Z and its X sets A.

    Same three distinct values as the game-score test, for the same reason, and the same
    conclusion: field A 0.3 is key Z, field P 0.7 is key P, field X 0.9 is key A. W, D and
    L are left at the defaults here so that the record 310 match points of four_teams()
    stay consistent and the file reads.

    The match system keeps all three as numbers. Nothing reads a match P or A back into a
    result the way update_gamescore() does for the game system, so 0.3 and 0.9 survive
    even though they are not the value of any other key -- which is the one place the two
    records behave differently, and the reason this is a test of its own rather than a
    parameter of the first one.
    """
    chessfile = parse(four_teams(["362  W 2.0    D 1.0    L 0.0    A 0.3    P 0.7    X 0.9"]))

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["match"] == {
        **DEFAULT_MATCH_SCORE_SYSTEM,
        "Z": decimal.Decimal("0.3"),
        "P": decimal.Decimal("0.7"),
        "A": decimal.Decimal("0.9"),
    }


def test_the_shipped_fixture_round_trips_its_own_162_record():
    """The one 162 record checked into the repository, read and written back unchanged.

    Everything above builds its own tournament, which is the only way to reach the fields
    the corpus never writes. This reads the file as it stands, so the column layout the
    other tests assume is known to be the layout a real file uses rather than one invented
    here.

    The round-trip is the assertion that carries the weight. Every value in this record is
    an ordinary one, so the parsed system on its own cannot tell a reader that mapped the
    A field to key Z from one that mapped it to key A -- both end up looking like the
    default. Writing it out again can: key Z holds 0.0 and key A resolves to 0.5, so the
    line comes back with "A 0.0" and "X 0.5" only if both halves of the crosswise mapping
    are the way round they are, and comes back with them swapped if either is turned over.
    """
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "no_colour_preference.trf")
    with open(fixture, encoding="utf-8") as handle:
        text = handle.read().rstrip("\n")
    chessfile = parse(text.split("\n"))

    record = [line for line in text.split("\n") if line.startswith("162")]

    assert chessfile.get_status() == 0
    assert chessfile.get_tournament(1)["scoreSystem"]["game"] == DEFAULT_GAME_SCORE_SYSTEM
    assert record == ["162  W 1.0    D 0.5    L 0.0    A 0.0    P 1.0    X 0.5"]
    assert chessfile.output_trf_gamescore(chessfile.get_tournament(1), "162") == record[0] + "\n"
