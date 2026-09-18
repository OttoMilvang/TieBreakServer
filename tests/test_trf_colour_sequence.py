# -*- coding: utf-8 -*-
"""TRF-2026 record 352, the board colour sequence of a team competition.

    352 WBWB

is one character per board, W or B, giving the colours the players of the team
the pairing designated White sit on. The reader takes the number of boards from
the length of the sequence and the team's colour from its first character, so a
record read wrongly here decides how many boards a match has and which way round
they are.

The record had no validation at all. An empty one reached seq[0] and faulted,
arbitrary characters were accepted as boards, an individual tournament accepted
it, and two of them silently left the last one standing.
"""
import pytest

from gacrux import gacruxexeptions
from gacrux import trf2json
from gacrux.pairingfideteam import pairing_fideteam


def team_file(*extra):
    """Two teams with two-player squads, no result, and caller-supplied records."""
    return "\n".join([
        "012 board colour sequence",
        "062 4",
        "072 4",
        "082 2",
        "142 3",
        "152 W",
        "001    1      Alpha Board1                     2000                             0.0    0",
        "001    2      Alpha Board2                     1900                             0.0    0",
        "001    3      Beta Board1                      1950                             0.0    0",
        "001    4      Beta Board2                      1850                             0.0    0",
        "310   1 Alpha                                    2000    0.0    0.0   1     1    2",
        "310   2 Beta                                     1900    0.0    0.0   2     3    4",
    ] + list(extra))


def read(text, verbose=0):
    chessfile = trf2json.trf2json()
    chessfile.parse_file(text, verbose)
    return chessfile


def test_a_declared_colour_sequence_is_read():
    """The control: the sequence supplies the size, the colours and the first colour."""
    tournament = read(team_file("352 WBBW")).get_tournament(1)

    assert tournament["teamSequence"] == "WBBW"
    assert tournament["teamColor"] == "W"
    assert tournament["teamSize"] == 4


def test_a_lower_case_sequence_is_read_as_the_same_boards():
    tournament = read(team_file("352 wb")).get_tournament(1)

    assert tournament["teamSequence"] == "WB"
    assert tournament["teamColor"] == "W"


@pytest.mark.parametrize("record", ["352", "352 WXB", "352 W B"], ids=["empty", "letter", "space"])
def test_record_352_requires_a_nonempty_board_colour_sequence(record):
    """Every character names one board and must therefore be White or Black.

    An empty sequence used to reach seq[0] and raise IndexError from the middle of
    the reader, and any other character was counted as a board and carried into the
    board order as a colour the pairing cannot read.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError, match="only W and B"):
        read(team_file(record))


def test_record_352_is_team_only():
    """TRF-2026 defines the board sequence for team competitions.

    In an individual tournament the record sets a board count and a board order for
    boards that do not exist, and nothing later contradicts it.
    """
    with open("tests/fixtures/no_colour_preference.trf", encoding="latin1") as handle:
        individual = handle.read() + "\n352 WB"

    with pytest.raises(gacruxexeptions.GacruxInputError, match="only valid in a team tournament"):
        read(individual)


def test_record_352_may_not_be_repeated():
    """Two board sequences leave both the team size and the board colours ambiguous.

    The second record used to overwrite the first without a word, so which of the two
    the event was read with depended on the order they were written in.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError, match="may occur only once"):
        read(team_file("352 WB", "352 BW"))


def test_record_352_wins_over_a_longer_roster():
    """Record 310 lists a squad, which may hold a reserve: the official TRF example
    has four boards and five players on a team. The sequence is the board count."""
    lines = team_file().split("\n")
    lines.insert(10, "001    5      Alpha Reserve                    1800                             0.0    0")
    lines[11] += "    5"
    tournament = read("\n".join(lines + ["352 WBWB"])).get_tournament(1)

    assert len(tournament["competitors"][0]["cplayers"]) == 3
    assert tournament["teamSize"] == 4


def test_a_sequence_written_before_the_team_section_is_read_the_same_way():
    """Where the record sits in the file does not decide whether it is accepted.

    The reader parses the records in its own order, not the file's, and record 352
    used to be read before either team-section record. The team-only check would then
    have refused every team file that declares its teams with a record 310 and
    nothing else, because nothing had yet said the tournament was a team event. The
    record is parsed after both team-section forms instead.
    """
    lines = team_file().split("\n")
    first = read("\n".join(lines[:6] + ["352 WB"] + lines[6:])).get_tournament(1)
    last = read(team_file("352 WB")).get_tournament(1)

    assert first["teamSequence"] == last["teamSequence"] == "WB"
    assert first["teamSize"] == last["teamSize"] == 2


@pytest.mark.parametrize("seq", ["BW", "BWWB", "B"])
def test_record_352_must_lead_with_white(seq):
    """C.04.6 art. 1.6.1 takes a team's colour from its first board.

    The sequence gives the colours of the team the pairing designates White, so
    it has to start with W for the two to agree. A file with 352 BW was read
    with every match colour reversed, and every colour difference with it.
    """
    with pytest.raises(gacruxexeptions.GacruxInputError, match="must lead with W"):
        read(team_file("352 " + seq))

    assert read(team_file("352 WB")).get_status() == 0


def test_a_team_event_with_no_results_has_no_board_count_without_record_352():
    """Record 310 lists a squad, reserves included, so it is not a board count."""
    tournament = read(team_file()).get_tournament(1)

    assert tournament["teamSize"] == 0
    assert len(tournament["competitors"]) == 2


def test_pairing_round_one_without_record_352_is_refused():
    """Before round one there are no matches to count the boards from.

    The pairing went ahead with teamSize 0, which gives a pairing-allocated bye no
    game points. It is now refused and asks for record 352, here with two teams
    and no bye to give.
    """
    tournament = read(team_file()).get_tournament(1)

    with pytest.raises(gacruxexeptions.GacruxInputError, match="record 352"):
        pairing_fideteam(tournament, 1, {"experimental": [], "verbose": 0})


def test_pairing_round_one_with_record_352_goes_ahead():
    tournament = read(team_file("352 WB")).get_tournament(1)

    engine = pairing_fideteam(tournament, 1, {"experimental": [], "verbose": 0})
    pairs = [pair for bracket in engine.compute_pairing(False) for pair in bracket["pairs"]]
    assert len(pairs) == 1
