# -*- coding: utf-8 -*-
"""Whether the number of rounds was declared, or only inferred from the rounds played.

Record 142 is the only TRF field that states the scheduled length of a tournament. A
file without one still yields a number, because the reader takes the highest round any
player record mentions, but that is a lower bound on the schedule and not the schedule:
a five-round event with two rounds played reads as a two-round event.

Three parts of C.04.6 ask which round is the last one rather than how many rounds have
happened - art. 1.7.2's last-round case for the type B colour preferences, and the "with
the exception of the last two rounds" of art. 2.3.4 [C7] and art. 2.3.7 [C10] - so the
two have to be told apart. numRoundsExplicit is what tells them apart, and -N sets it
too, because a count given on the command line is as much a declared schedule as a
record 142.
"""
import contextlib
import io
import sys

from gacrux import pairingchecker

BOARDS = 2
TEAMS = 4
SCHEDULE = {1: [(1, 4), (2, 3)], 2: [(1, 3), (4, 2)]}


def players(team):
    return [(team - 1) * BOARDS + board for board in range(1, BOARDS + 1)]


def player_line(startno, points, games):
    line = "001 "
    line += "%4d " % startno
    line += "m    "
    line += "%-33s " % ("T%dB%d, Player" % ((startno - 1) // BOARDS + 1, (startno - 1) % BOARDS + 1))
    line += "%4d " % (2200 - startno)
    line += "NOR "
    line += "%11d " % 0
    line += "1990/01/01 "
    line += "%4s " % points
    line += "%4d  " % startno
    return line + "  ".join(games)


def team_line(cid, matchpoints, gamepoints, played):
    line = "310 "
    line += "%3d " % cid
    line += "%-32s" % ("Team %d" % cid)
    line += " " * 7
    line += "%6d " % (2000 - cid)
    line += "%6s " % matchpoints
    line += "%6s " % gamepoints
    line += "%3d " % cid
    return line + "".join(" %4d" % startno for startno in played)


def team_file(declared_rounds):
    """Two played rounds of a four-team event. ``declared_rounds`` writes a record 142;
    None leaves it out, so the reader has only the rounds played to go on."""
    games = {startno: [] for startno in range(1, TEAMS * BOARDS + 1)}
    for rnd in (1, 2):
        for white, black in SCHEDULE[rnd]:
            for board in range(BOARDS):
                colour = "w" if board % 2 == 0 else "b"
                a, b = players(white)[board], players(black)[board]
                games[a].append("%4d %s %s" % (b, colour, "="))
                games[b].append("%4d %s %s" % (a, "b" if colour == "w" else "w", "="))
    lines = [
        "012 Four teams",
        "042 2026-03-01",
        "062 %d" % (TEAMS * BOARDS),
        "072 %d" % (TEAMS * BOARDS),
        "082 %d" % TEAMS,
    ]
    if declared_rounds is not None:
        lines.append("142 %d" % declared_rounds)
    lines += ["152 W", "192 FIDE_TEAM_MP_GP", "212 PTS"]
    for team in range(1, TEAMS + 1):
        for startno in players(team):
            lines.append(player_line(startno, "1.0", games[startno]))
    for team in range(1, TEAMS + 1):
        lines.append(team_line(team, "2.0", "2.0", players(team)))
    return "\n".join(lines) + "\n"


def read(tmp_path, trf, options=()):
    path = tmp_path / "teams.trf"
    path.write_text(trf, encoding="latin1")
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    sys.argv = ["pairingchecker", "-i", str(path), "-c"] + list(options)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return checker.chessfile.get_tournament(1)


def test_a_record_142_declares_the_round_count(tmp_path):
    """A file with a record 142 states its schedule, and the flag says so."""
    tournament = read(tmp_path, team_file(declared_rounds=5))
    assert tournament["numRounds"] == 5
    assert tournament["numRoundsExplicit"] is True


def test_without_a_record_142_the_count_is_only_inferred(tmp_path):
    """No record 142: the reader still reports a number, taken from the rounds played,
    and the flag says it was not declared. Two rounds were played, so the count is 2 -
    which is a lower bound on the schedule and says nothing about which round is last.
    """
    tournament = read(tmp_path, team_file(declared_rounds=None))
    assert tournament["numRounds"] == 2
    assert tournament["numRoundsExplicit"] is False


def test_a_declared_count_is_not_raised_by_the_rounds_played(tmp_path):
    """A record 142 declaring fewer rounds than the file goes on to play is still the
    declared schedule. The reader used to overwrite it with the higher number, which
    silently turned a contradictory file into a consistent-looking longer one; a declared
    count now stands, and the contradiction stays visible.
    """
    tournament = read(tmp_path, team_file(declared_rounds=1))
    assert tournament["numRounds"] == 1
    assert tournament["numRoundsExplicit"] is True


def test_the_command_line_count_declares_it_too(tmp_path):
    """-N is as much a declared schedule as a record 142."""
    tournament = read(tmp_path, team_file(declared_rounds=None), options=["-N", "7"])
    assert tournament["numRounds"] == 7
    assert tournament["numRoundsExplicit"] is True
