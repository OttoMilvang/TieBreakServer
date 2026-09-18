# -*- coding: utf-8 -*-
"""A team tournament is not paired, or checked, within two rounds of an end that was
only inferred.

Three parts of C.04.6 ask where the end of the event is. Two of them apply under every
colour model:

    2.3.4  [C7]  With the exception of the LAST TWO ROUNDS, minimise the number of
                 upfloaters that were floaters in the previous round.
    2.3.7  [C10] With the exception of the LAST TWO ROUNDS, minimise the number of
                 upfloaters' opponents that were floaters in the previous round.

and the third is art. 1.7.2, the type B colour preferences, which withholds the mild
preference at a colour difference of zero "if it is not the last round" and gives none
at all "when its CD is zero when pairing for the last round".

Only record 142 states the scheduled length (C.04.1 art. 1: the number of rounds "is
declared beforehand"). Without it trf2json takes the last round played and marks the
count as not explicit, so every round the engine is asked for is within two of that
end. The round is refused instead, naming record 142 and -N. Rounds further from the
inferred end are paired and checked as before.
"""
import contextlib
import io
import os
import sys

import pytest

from gacrux import pairingchecker
from gacrux import trf2json
from gacrux.gacruxexeptions import GacruxInputError
from gacrux.pairingfideteam import pairing_fideteam

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "fideteam_nocolor.trf")


def team_file(code, *, rounds="142 7"):
    """The nine-team, seven-round fixture, re-coded and optionally without its record 142."""
    with open(FIXTURE, encoding="latin1") as handle:
        lines = handle.read().rstrip("\n").split("\n")
    out = []
    for line in lines:
        if line.startswith("192"):
            out.append("192 " + code)
        elif line.startswith("142"):
            if rounds:
                out.append(rounds)
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def tournament_of(text):
    chessfile = trf2json.trf2json()
    chessfile.parse_file(text, 0)
    return chessfile.chessjson["event"]["tournaments"][0]


def engine(text, rnd):
    return pairing_fideteam(tournament_of(text), rnd, {"experimental": [], "verbose": 0})


def check(tmp_path, text, argv=()):
    """Run pairingchecker -c over the file."""
    trf = tmp_path / "team.trf"
    trf.write_text(text, encoding="latin1")
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    sys.argv = ["pairingchecker", "-i", str(trf), "-c"] + list(argv)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return checker


def rounds_checked(checker):
    return [item["round"] for item in checker.chessfile.result["roundpairing"]]


def test_type_b_without_a_round_count_is_refused():
    """Round 8 of a type B file that accounts for seven rounds and has no record 142."""
    with pytest.raises(GacruxInputError) as excinfo:
        engine(team_file("FIDE_TEAM_TYPEB_MP_GP", rounds=""), 8)
    message = str(excinfo.value)
    assert "142" in message
    assert "-N" in message
    assert "1.7.2" in message
    assert "2.3.4" in message


def test_type_b_with_a_round_count_is_paired():
    """The same file with its record 142, pairing its last round."""
    assert engine(team_file("FIDE_TEAM_TYPEB_MP_GP"), 7).typeb is True


def test_type_b_paired_past_the_declared_end_is_refused_too():
    """A file that declares seven rounds cannot say whether round 8 is the last one."""
    with pytest.raises(GacruxInputError) as excinfo:
        engine(team_file("FIDE_TEAM_TYPEB_MP_GP"), 8)
    assert "-N" in str(excinfo.value)


def test_type_a_without_a_round_count_is_refused():
    """Art. 1.7.1 never asks which round is the last, but [C7] and [C10] do, under type
    A as under any other model. The message names the criteria and not art. 1.7.2."""
    with pytest.raises(GacruxInputError) as excinfo:
        engine(team_file("FIDE_TEAM_TYPEA_MP_GP", rounds=""), 8)
    message = str(excinfo.value)
    assert "142" in message
    assert "2.3.4" in message
    assert "2.3.7" in message
    assert "1.7.2" not in message


def test_type_a_without_a_round_count_is_paired_further_from_the_end():
    """Round 5 is not within two of the inferred seven, so [C7] and [C10] apply to it
    whatever the true length of the event is."""
    built = engine(team_file("FIDE_TEAM_TYPEA_MP_GP", rounds=""), 5)
    assert built.typeb is False
    assert built.lasttworounds is False


def test_no_colour_preferences_without_a_round_count_is_refused():
    """[C7] and [C10] are not colour criteria, so a competition without colour
    preferences is refused like the others."""
    with pytest.raises(GacruxInputError) as excinfo:
        engine(team_file("FIDE_TEAM_MP_GP", rounds=""), 8)
    assert "2.3.7" in str(excinfo.value)


def test_no_colour_preferences_without_a_round_count_is_paired_further_from_the_end():
    built = engine(team_file("FIDE_TEAM_MP_GP", rounds=""), 5)
    assert built.usecolor is False
    assert built.lasttworounds is False


def test_check_mode_stops_two_rounds_before_an_inferred_end(tmp_path):
    """Seven rounds played and no record 142: rounds 1 to 5 are checked and round 6 is
    refused. With -N 9 round 7 is not within two of the end and all seven are checked."""
    text = team_file("FIDE_TEAM_TYPEA_MP_GP", rounds="")
    checker = check(tmp_path, text)
    tournament = checker.chessfile.get_tournament(1)
    assert tournament["numRounds"] == 7
    assert tournament["numRoundsExplicit"] is False
    assert rounds_checked(checker) == [1, 2, 3, 4, 5]
    assert checker.resultjson["status"]["code"] >= 400
    # -v lets the engine's own error through: it is round 6, and it names record 142
    with pytest.raises(GacruxInputError, match="^round 6 .*record 142"):
        check(tmp_path, text, ["-v"])

    checker = check(tmp_path, text, ["-N", "9"])
    assert checker.chessfile.get_tournament(1)["numRoundsExplicit"] is True
    assert rounds_checked(checker) == [1, 2, 3, 4, 5, 6, 7]
    assert checker.resultjson["status"]["code"] in (0, 1)


def test_type_b_check_mode_stops_two_rounds_before_an_inferred_end_as_well(tmp_path):
    text = team_file("FIDE_TEAM_TYPEB_MP_GP", rounds="")
    checker = check(tmp_path, text)
    assert rounds_checked(checker) == [1, 2, 3, 4, 5]
    assert checker.resultjson["status"]["code"] >= 400
    with pytest.raises(GacruxInputError, match="^round 6 .*record 142"):
        check(tmp_path, text, ["-v"])
