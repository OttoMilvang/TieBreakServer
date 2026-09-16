# -*- coding: utf-8 -*-
"""
What the command line reports when a pairing or input fault reaches it.

``gacruxexeptions.py`` distinguishes three conditions -- a tournament state, a malformed
input, and an engine bug -- and the distinction is worth nothing unless it reaches the
status code the CLI reports.  The acceleration diagnostic is the concrete case: C.04.7
art. 1.4.4 forbids the Baku acceleration when game points are the primary score, and a
user who does that has to be told which article they violated, not that the program is
broken.

The team checker deliberately handles an incompletable C.04.6 round by producing the
largest legal matching and leaving each unmatched team opposite competitor zero. Those
article-3.3.3 policy results do not reach the command-line fault mapping; other callers
and the individual Dutch engine still can.
"""
import contextlib
import io
import sys

from gacrux import pairingchecker

# The circle-method round robin of four teams. Rounds 1-3 use up every pair; a declared
# round 4 can only repeat one of them.
SCHEDULE = {
    1: [(1, 4), (2, 3)],
    2: [(1, 3), (4, 2)],
    3: [(1, 2), (3, 4)],
    4: [(1, 4), (2, 3)],
}
TEAMS = 4
BOARDS = 2


def players(team):
    """The start numbers of one team's players, board order."""
    return [(team - 1) * BOARDS + board for board in range(1, BOARDS + 1)]


def player_line(startno, points, games):
    line = "001 "
    line += "%4d " % startno                     # start number
    line += "m    "                              # sex + title
    line += "%-33s " % ("T%dB%d, Player" % ((startno - 1) // BOARDS + 1, (startno - 1) % BOARDS + 1))
    line += "%4d " % (2200 - startno)            # rating
    line += "NOR "                               # federation
    line += "%11d " % 0                          # fide id
    line += "1990/01/01 "                        # birth date
    line += "%4s " % points                      # points
    line += "%4d  " % startno                    # rank
    return line + "  ".join(games)


def team_line(cid, matchpoints, gamepoints, played):
    line = "310 "
    line += "%3d " % cid                         # team number
    line += "%-32s" % ("Team %d" % cid)          # team name
    line += " " * 7
    line += "%6d " % (2000 - cid)                # team strength
    line += "%6s " % matchpoints                 # match points
    line += "%6s " % gamepoints                  # game points
    line += "%3d " % cid                         # rank
    return line + "".join(" %4d" % startno for startno in played)


def round_robin(declared, numrounds=4, typeoftournament="FIDE_TEAM_MP_GP", extra=()):
    """A four-team team tournament with ``declared`` of its rounds played out.

    Every match is drawn on both boards, so all four teams stay level on match points and
    on game points and the file needs no ranking argument to be internally consistent.
    """
    games = {startno: [] for startno in range(1, TEAMS * BOARDS + 1)}
    for rnd in range(1, declared + 1):
        for white, black in SCHEDULE[rnd]:
            for board in range(BOARDS):
                # Board 1 of the white team has White, board 2 has Black (art. 4 has no
                # say here: record 192 selects the model with no colour preferences).
                colour = "w" if board % 2 == 0 else "b"
                a, b = players(white)[board], players(black)[board]
                games[a].append("%4d %s %s" % (b, colour, "="))
                games[b].append("%4d %s %s" % (a, "b" if colour == "w" else "w", "="))

    lines = [
        "012 Four teams, exhausted round robin",
        "042 2026-03-01",
        "062 %d" % (TEAMS * BOARDS),
        "072 %d" % (TEAMS * BOARDS),
        "082 %d" % TEAMS,
        "142 %d" % numrounds,
        "152 W",
        "192 " + typeoftournament,
        "212 PTS",
    ]
    lines.extend(extra)
    for team in range(1, TEAMS + 1):
        for startno in players(team):
            lines.append(player_line(startno, "%.1f" % (0.5 * declared), games[startno]))
    for team in range(1, TEAMS + 1):
        # Every match drawn: one match point and one game point per round, per team.
        lines.append(team_line(team, "%.1f" % declared, "%.1f" % declared, players(team)))
    return "\n".join(lines) + "\n"


def write(tmp_path, trf, name="teams.trf"):
    path = tmp_path / name
    path.write_text(trf, encoding="latin1")
    return str(path)


def run(path, options):
    """Drive the real command line over one file; return the checker and what it printed.

    The status the caller sees is ``resultjson["status"]``, which is what chessserver
    hands back and what the corpus harness reads. Nothing here passes ``-v``: the verbose
    path of ``do_command`` re-raises, and the non-verbose path is the one users get.
    """
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    written = io.StringIO()
    sys.argv = ["pairingchecker", "-i", path] + options
    try:
        with contextlib.redirect_stdout(written), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return (checker, written.getvalue())


def status(checker):
    return checker.resultjson.get("status", {}).get("code")


def messages(checker):
    """The status text the run reports, as one string."""
    return "\n".join(checker.resultjson.get("status", {}).get("error", []))


def reported_pairs(checker):
    """Every pair the run reports, from whichever shape of result it produced."""
    result = getattr(checker.chessfile, "result", None) or {}
    pairs = list(result.get("pairs") or [])
    for rndpairing in result.get("roundpairing", []):
        for key in ("pairs", "current"):
            pairs.extend(rndpairing.get(key) or [])
    return [tuple(pair) for pair in pairs]


# ---------------------------------------------------------------------------------
# Fault classes retain distinct status codes
# ---------------------------------------------------------------------------------


# C.04.7 art. 1.4.4 -- record 250 gives the Baku virtual points, and record 192 makes game
# points the primary score. The two together are the combination the article forbids.
ACCELERATION = "250 " + "%4s " % "2.0" + "%4s " % "1.0" + "%3d " % 1 + "%3d " % 1 + "%4d " % 1 + "%4d" % 2


def test_cli_preserves_acceleration_input_diagnostic(tmp_path):
    """A file that breaks C.04.7 art. 1.4.4 must be told which article it breaks.

    ``pairing_fideteam.__init__`` refuses an accelerated tournament whose primary score is
    game points and says why, in a sentence written for the person who wrote the file.
    That is a ``GacruxInputError`` -- "the tournament handed to the engine is malformed"
    (gacruxexeptions.py) -- and funnelling it into 510 "Program error" throws the
    sentence away and accuses the engine of a bug the user committed.

    The input-error band is 4xx, and 401 is the code trf2json already records beside every
    GacruxInputError it raises, so a caller sees one code for one meaning wherever the
    malformation is found. The assertion that matters most is the last one: the article
    number reaches the output the user actually reads.
    """
    trf = round_robin(declared=3, typeoftournament="FIDE_TEAM_GP_MP", extra=[ACCELERATION])
    path = write(tmp_path, trf)

    (checker, output) = run(path, ["-p", "-d", "T"])

    assert status(checker) != 510, "a malformed tournament is not a defect of the engine"
    assert status(checker) == 401
    assert "C.04.7 art. 1.4.4" in messages(checker)
    assert "Program error" not in messages(checker)
    assert "C.04.7 art. 1.4.4" in output


def test_an_engine_invariant_violation_is_still_a_program_error(tmp_path, monkeypatch):
    """510 keeps the meaning it has, so that it stays worth reporting.

    ``gacruxexeptions.py``: "GacruxInvariantError means an internal consistency check of
    the engine failed. This is a bug in the engine." That -- and an exception nobody anticipated at
    all -- is what 510 "Program error" is for. Splitting the other two conditions out of
    510 is only worth doing if what is left behind still means what it says, so this pins
    the third arm of the mapping rather than leaving it to follow by implication.

    The invariant is raised by hand: a genuine one cannot be provoked from a file without
    a bug to provoke it with, and the point here is the routing, not the invariant.
    """
    from gacrux import gacruxexeptions
    from gacrux.pairingfideteam import pairing_fideteam

    def broken(self, checkonly, reportlevel=0):
        raise gacruxexeptions.GacruxInvariantError("the engine contradicted itself")

    monkeypatch.setattr(pairing_fideteam, "compute_pairing", broken)
    path = write(tmp_path, round_robin(declared=2))

    (checker, _) = run(path, ["-p"])

    assert status(checker) == 510
    assert "Program error" in messages(checker)
