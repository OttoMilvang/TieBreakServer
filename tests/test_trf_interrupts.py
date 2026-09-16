# -*- coding: utf-8 -*-
"""
An interrupt is not a malformed record, and neither the reader nor the command runner
may report it as one.

Two handlers used to be written as a bare ``except:``. Pass 2 of
trf2json.read_all_lines() turns a parser that failed without saying why into
"Error in trf-file, line N" and stops; commonmain.do_command() turns an exception
nobody foresaw into 510 "Program error". Both are right for an exception, and both
were wrong for KeyboardInterrupt and SystemExit, which are not Exceptions at all: a
user pressing Ctrl-C while a large file was being read got a status about the file
they had interrupted, and the run carried on to the next stage. The two handlers now
catch Exception and let everything else through.

The interrupt is raised by hand from inside a parser and from inside a command stage:
a real one cannot be timed from a test, and the point here is the routing.
"""
import sys

import pytest

from gacrux import pairingchecker
from gacrux import trf2json


LINES = "\n".join([
    "012 Interrupted",
    "042 2026-03-01",
    "XXR 1",
    "001    1 m    One, Player                       2400 NOR           0 1990/01/01  1.0     1     2 w 1",
    "001    2 m    Two, Player                       2300 NOR           0 1990/01/01  0.0     2     1 b 0",
])


def interrupt(*args, **kwargs):
    raise KeyboardInterrupt()


def test_an_interrupt_while_a_record_is_read_propagates(monkeypatch):
    monkeypatch.setattr(trf2json.trf2json, "parse_trf_player", interrupt)
    chessfile = trf2json.trf2json()

    with pytest.raises(KeyboardInterrupt):
        # verbose off: the non-verbose branch is the one that swallowed it.
        chessfile.parse_file(LINES, 0)

    assert chessfile.get_status() == 0, "an interrupt is not an error in the file"


def test_an_interrupt_in_a_command_stage_propagates(tmp_path, monkeypatch):
    path = tmp_path / "interrupted.trf"
    path.write_text(LINES + "\n", encoding="latin1")
    monkeypatch.setattr(trf2json.trf2json, "parse_file", interrupt)
    monkeypatch.setattr(sys, "argv", ["pairingchecker", "-i", str(path), "-c"])
    checker = pairingchecker.pairingchecker()

    with pytest.raises(KeyboardInterrupt):
        checker.common_main()

    assert checker.resultjson.get("status", {}).get("code", 0) != 510, \
        "an interrupt is not a defect of the engine"
