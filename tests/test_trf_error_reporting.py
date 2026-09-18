# -*- coding: utf-8 -*-
"""How the reader reports a record it cannot parse.

read_all_lines() hands each line to the parser for its record. When a parser fails
without saying why, the reader records status 401 "Error in trf-file, line N, <line>"
and stops reading. The caller then has to be left with that status, and with nothing
else going wrong on the way out.

The error path used to return None, and parse_file() went straight on to look up
records in it, so the 401 ended as "TypeError: argument of type 'NoneType' is not
iterable".
"""
import contextlib
import io
import sys

import pytest

from gacrux import pairingchecker
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


def team_line(cid, name, players, matchpoints="0.0", gamepoints="0.0"):
    # Record 310: the team pairing number in columns 5-7, the name in 9-40, match
    # points in 55-60, game points in 62-67, rank in 69-71, players from 74 on.
    line = list(" " * 73)
    line[0:3] = "310"
    line[4:7] = "%3d" % cid
    line[8 : 8 + len(name)] = name
    line[54:60] = "%6s" % matchpoints
    line[61:67] = "%6s" % gamepoints
    line[68:71] = "%3d" % cid
    return "".join(line) + " ".join(["%4d" % player for player in players])


def teams(records):
    """Two teams of two players, two rounds played, plus the records a test adds."""
    lines = ["012 Error reporting, teams", "042 2026-03-01", "XXR 2", "352 WB"]
    lines.append(team_line(1, "Team One", [1, 2], "4.0", "3.0"))
    lines.append(team_line(2, "Team Two", [3, 4], "0.0", "1.0"))
    lines.append(player_line(1, "One, Player", 2400, "1.5", [(3, "w", "1"), (4, "w", "=")]))
    lines.append(player_line(2, "Two, Player", 2300, "1.5", [(4, "b", "="), (3, "b", "1")]))
    lines.append(player_line(3, "Three, Player", 2200, "0.5", [(1, "b", "0"), (2, "w", "=")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.5", [(2, "w", "="), (1, "b", "0")]))
    return lines + records


def parse(lines):
    chessfile = trf2json.trf2json()
    # verbose off, which is how a program that is handed a file reads it.
    chessfile.parse_file("\n".join(lines), 0)
    return chessfile


def test_an_unknown_forfeit_code_reports_the_line_number():
    """Record 330 has no forfeit code "XY", and the translation table raises KeyError.

    The reader names the line and stops. The 330 record is the 11th line of the file.
    """
    lines = teams(["330 XY   2   1   2"])
    assert lines[10] == "330 XY   2   1   2"

    chessfile = parse(lines)

    assert chessfile.get_status() == 401
    assert "Error in trf-file, line 11, 330 XY   2   1   2" in chessfile.chessjson["status"]["error"]


def test_an_unknown_forfeit_code_still_raises_when_verbose():
    with pytest.raises(KeyError):
        chessfile = trf2json.trf2json()
        chessfile.parse_file("\n".join(teams(["330 XY   2   1   2"])), True)


def test_a_file_with_no_bad_record_still_reads():
    assert parse(teams([])).get_status() == 0


def run(path, options):
    """Run the pairing checker's command line over one file, without -v."""
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    sys.argv = ["pairingchecker", "-i", path] + options
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return checker


def test_a_team_pairing_number_that_is_not_a_number_reports_401(tmp_path):
    """Record 310 with "  X" as its team pairing number.

    The parser fails on the record and the reader names the line with 401. Nothing
    after that may read the records again: the team pairing number check did, raised
    TypeError from outside the handler, and the command line reported 502 with the
    401 buried under it.
    """
    lines = [line[:4] + "  X" + line[7:] if line.startswith("310   2") else line
             for line in teams([])]
    path = tmp_path / "teams.trf"
    path.write_text("\n".join(lines) + "\n", encoding="latin1")

    checker = run(str(path), ["-p"])

    status = checker.resultjson.get("status", {})
    assert status.get("code") == 401
    messages = "\n".join(status.get("error", []))
    assert "Error in trf-file, line" in messages
    assert "Error when reading file" not in messages
