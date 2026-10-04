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
from copy import deepcopy

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
    tournament = read("\n".join(lines + ["352 WB"])).get_tournament(1)

    assert len(tournament["competitors"][0]["cplayers"]) == 3
    assert tournament["teamSize"] == 2


def test_a_sequence_written_before_the_team_section_is_read_the_same_way():
    """Physical record order does not change the parsed tournament."""
    lines = team_file().split("\n")
    first = read("\n".join(lines[:6] + ["352 WB"] + lines[6:])).get_tournament(1)
    last = read(team_file("352 WB")).get_tournament(1)

    assert first == last
    assert first["teamSequence"] == last["teamSequence"] == "WB"
    assert first["teamSize"] == last["teamSize"] == 2


@pytest.mark.parametrize("seq", ["BW", "BWWB", "B", "bwbw"])
def test_record_352_may_lead_with_black(seq):
    tournament = read(team_file("352 " + seq)).get_tournament(1)

    assert tournament["teamSequence"] == seq.upper()
    assert tournament["teamColor"] == "B"
    assert tournament["teamSize"] == len(seq)


@pytest.mark.parametrize("seq,white,black", [("BW", 1, 2), ("WB", 2, 1)])
def test_the_board_sequence_determines_the_match_colours(seq, white, black):
    lines = team_file("352 " + seq).splitlines()
    games = [(3, "b"), (4, "w"), (1, "w"), (2, "b")]
    for index, (opponent, colour) in enumerate(games, 6):
        line = lines[index]
        lines[index] = (line[:80] + " 0.5" + line[84:89]).ljust(91) + "%4d %s =" % (opponent, colour)
    for index in [10, 11]:
        line = lines[index]
        lines[index] = line[:54] + "   1.0" + line[60:61] + "   1.0" + line[67:]
    tournament = read("\n".join(lines)).get_tournament(1)

    match = tournament["matchList"][0]
    assert match["white"]["cid"] == white
    assert match["black"]["cid"] == black
    assert [(game["white"]["cid"], game["black"]["cid"]) for game in tournament["gameList"]] == [(3, 1), (2, 4)]
    engine = pairing_fideteam(tournament, 2, {"experimental": [], "verbose": 0})
    competitors, _ = engine.get_crosstable([], False, 0).init_engine(tournament, 2, 1, "w", "cid")
    assert competitors[white]["csq"].strip() == "w"
    assert competitors[black]["csq"].strip() == "b"
    assert competitors[white]["cod"] == 1
    assert competitors[black]["cod"] == -1


def test_a_team_event_with_no_results_has_no_board_count_without_record_352():
    """Record 310 lists a squad, reserves included, so it is not a board count."""
    tournament = read(team_file()).get_tournament(1)

    assert tournament["teamSize"] == 0
    assert len(tournament["competitors"]) == 2


@pytest.mark.parametrize("teams", [2, 3])
def test_pairing_round_one_without_record_352_goes_ahead(teams):
    lines = team_file().splitlines()
    if teams == 3:
        lines[1:4] = ["062 6", "072 6", "082 3"]
        lines[10:10] = [
            "001    5      Gamma Board1                     1800                             0.0    0",
            "001    6      Gamma Board2                     1700                             0.0    0",
        ]
        lines.append("310   3 Gamma                                    1800    0.0    0.0   3     5    6")
    tournament = read("\n".join(lines)).get_tournament(1)
    before = deepcopy(tournament)

    engine = pairing_fideteam(tournament, 1, {"experimental": [], "verbose": 0})
    pairs = [pair for bracket in engine.compute_pairing(False) for pair in bracket["pairs"]]

    assert len(pairs) == (teams + 1) // 2
    assert sum(pair["b"] == 0 for pair in pairs) == teams % 2
    assert sorted(cid for pair in pairs for cid in [pair["w"], pair["b"]] if cid) == list(range(1, teams + 1))
    assert tournament["scoreSystem"] == before["scoreSystem"]
    for competitor, original in zip(tournament["competitors"], before["competitors"]):
        assert {key: competitor[key] for key in original} == original
    assert tournament["teamSize"] == 0
    assert tournament["gameList"] == tournament["matchList"] == []


def test_pairing_later_rounds_still_requires_a_board_count():
    tournament = read(team_file()).get_tournament(1)

    with pytest.raises(gacruxexeptions.GacruxInputError, match="record 352"):
        pairing_fideteam(tournament, 2, {"experimental": [], "verbose": 0})


def test_pairing_round_one_still_rejects_a_negative_board_count():
    tournament = read(team_file()).get_tournament(1)
    tournament["teamSize"] = -1

    with pytest.raises(gacruxexeptions.GacruxInputError, match="record 352"):
        pairing_fideteam(tournament, 1, {"experimental": [], "verbose": 0})


def test_pairing_round_one_with_record_352_goes_ahead():
    tournament = read(team_file("352 WB")).get_tournament(1)

    engine = pairing_fideteam(tournament, 1, {"experimental": [], "verbose": 0})
    pairs = [pair for bracket in engine.compute_pairing(False) for pair in bracket["pairs"]]
    assert len(pairs) == 1


def test_a_team_event_with_matches_still_sizes_itself_from_them():
    """With matches and no record 352, the board count comes from the matches.

    The fixture is nine teams of two boards, seven rounds played, declared in
    record 310 and with no record 352.
    """
    with open("tests/fixtures/fideteam_nocolor.trf", encoding="latin1") as handle:
        tournament = read(handle.read()).get_tournament(1)

    assert tournament["teamSize"] == 2
    assert len(tournament["matchList"]) > 0


@pytest.mark.parametrize("section", ["310", "013"])
def test_board_count_is_available_before_reading_the_team_section(section):
    class Reader(trf2json.trf2json):
        def parse_trf_team(self, tournament, line):
            assert tournament["teamTournament"] is True
            assert tournament["teamSize"] == 2
            assert tournament["teamSequence"] == "WB"
            return super().parse_trf_team(tournament, line)

    text = team_file("352 WB")
    if section == "013":
        text = "\n".join(line for line in text.splitlines() if not line.startswith("310"))
        text += "\n013 " + "Alpha".ljust(32) + "    1    2"
        text += "\n013 " + "Beta".ljust(32) + "    3    4"
    reader = Reader()
    reader.parse_file(text, 1)
    assert reader.get_status() == 0
