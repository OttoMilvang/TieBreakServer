# -*- coding: utf-8 -*-
"""The file's answer to C.04.6 art. 1.2.1 survives a primary score named on the
command line.

Art. 1.2.1 asks the rules of the competition two questions: which score is the
primary one, and whether the other is used for colour allocation (art. 4.2.2).
A record 192 code answers both at once - FIDE_TEAM_TYPEA_MP_GP says the
secondary score is used, FIDE_TEAM_TYPEA_MP says it is not - and trf2json
records the second answer as scoreSystem["secondaryUsed"].

"-m fideteam-mp" names the primary score only. commonmain writes that token
into the score system as the primary score, over the one the file named, so
the engine cannot tell the two sources apart by looking at "primary" alone;
without the recorded answer it would fall back to art. 1.2.2 and use game
points for the colours of a file that said not to.
"""
import contextlib
import io
import os
import sys

from gacrux import pairingchecker
from gacrux.pairingfideteam import SECONDARY_USED, pairing_fideteam

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "fideteam_nocolor.trf")


def team_file(code):
    """The shipped nine-team fixture, re-coded."""
    with open(FIXTURE, encoding="latin1") as handle:
        lines = handle.read().rstrip("\n").split("\n")
    return "\n".join("192 " + code if line.startswith("192") else line for line in lines)


def engines_built_by(monkeypatch, tmp_path, code, argv):
    """Run pairingchecker over the re-coded fixture and return the engines it built,
    one per round it checked."""
    path = tmp_path / "team.trf"
    path.write_text(team_file(code), encoding="latin1")
    built = []
    original = pairing_fideteam.__init__

    def record(self, tournament, rnd, params):
        original(self, tournament, rnd, params)
        built.append(self)

    monkeypatch.setattr(pairing_fideteam, "__init__", record)
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    sys.argv = ["pairingchecker", "-i", str(path), "-c"] + argv
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    assert len(built) == 7
    return built


def test_art_1_2_1_the_file_alone_still_answers(monkeypatch, tmp_path):
    """FIDE_TEAM_TYPEA_MP with no -m at all: the file said the secondary score is not
    used, and nothing on the command line says otherwise."""
    for engine in engines_built_by(monkeypatch, tmp_path, "FIDE_TEAM_TYPEA_MP", []):
        assert engine.secondary is False


def test_art_1_2_1_naming_both_scores_on_the_command_line_overrides_the_file(monkeypatch, tmp_path):
    """-m fideteam-mp-gp states that the secondary score is used, whatever the file said."""
    for engine in engines_built_by(monkeypatch, tmp_path, "FIDE_TEAM_TYPEA_MP", ["-m", "fideteam-mp-gp"]):
        assert engine.secondaryscore == SECONDARY_USED
        assert engine.secondary is True


def test_art_1_2_1_a_file_that_uses_the_secondary_score_keeps_it_under_a_command_line_primary(monkeypatch, tmp_path):
    """FIDE_TEAM_TYPEA_MP_GP read with -m fideteam-mp: the file said the secondary score
    is used, and the command line does not say otherwise."""
    for engine in engines_built_by(monkeypatch, tmp_path, "FIDE_TEAM_TYPEA_MP_GP", ["-m", "fideteam-mp"]):
        assert engine.tournament["scoreSystem"]["secondaryUsed"] is True
        assert engine.secondary is True


def test_art_1_2_1_a_file_that_does_not_use_the_secondary_score_keeps_that_under_a_command_line_primary(monkeypatch, tmp_path):
    """FIDE_TEAM_TYPEA_MP read with -m fideteam-mp: the file said the secondary score is
    not used, and the command line does not say otherwise."""
    for engine in engines_built_by(monkeypatch, tmp_path, "FIDE_TEAM_TYPEA_MP", ["-m", "fideteam-mp"]):
        assert engine.secondary is False
