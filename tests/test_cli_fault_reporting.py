# -*- coding: utf-8 -*-
"""
What the command line reports when a pairing or input fault reaches it.

``gacruxexeptions.py`` distinguishes three conditions -- a tournament state, a malformed
input, and an engine bug -- and the distinction is worth nothing unless it reaches the
status code the CLI reports.  The acceleration diagnostic is the concrete case: C.04.7
art. 1.4.4 forbids the Baku acceleration when game points are the primary score, and a
user who does that has to be told which article they violated, not that the program is
broken.

A round that cannot be paired reaches the mapping like any other condition. C.04.6
art. 3.3.3 prescribes nothing for it and hands the round to the Chief Arbiter, so the
checker reports the state and stops rather than answering with a pairing of its own.
"""
import contextlib
import io
import sys

import pytest

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
# An impossible round is reported, not fabricated
# ---------------------------------------------------------------------------------


def test_pairing_an_impossible_round_reports_it_instead_of_giving_everyone_a_bye(tmp_path):
    """`-p` on an exhausted field must not answer with a bye for every unseated team.

    Three rounds of a four-team round robin use up every pair, so round four has no legal
    pairing at all. The engine says so with GacruxNoLegalPairing, and the only correct
    answer for the CLI is to report that condition (C.04.6 art. 3.3.3 leaves the decision
    to the Chief Arbiter). Four teams is an even field, so art. 1.4 -- "should the number
    of teams to be paired be odd, one team is not paired" -- allows no bye whatsoever
    here; a report naming competitor 0 as an opponent is therefore an invention, and four
    of them at once would break art. 1.4 even on an odd field, quite apart from art.
    2.1.2 [C2], which bars a team that has already had a bye from receiving another.

    The assertion is that no such pair is reported and that the run ends in a failure
    status rather than a successful-looking pairing.
    """
    path = write(tmp_path, round_robin(declared=3))

    (checker, _) = run(path, ["-p"])

    assert [pair for pair in reported_pairs(checker) if 0 in pair] == []
    assert status(checker) >= 400, "an unpairable round must not be reported as a pairing"


@pytest.mark.parametrize(
    "options",
    [
        pytest.param(["-c"], id="check"),
        pytest.param(["-c", "-p"], id="check-pairing"),
        pytest.param(["-c", "-a"], id="check-analysis"),
    ],
)
def test_checking_an_impossible_round_neither_fabricates_byes_nor_faults(tmp_path, options):
    """The three check invocations over a round that cannot be paired.

    The file declares a fourth round -- necessarily a repeat of round one, since every
    pair is used up -- and `-n 4` points each invocation at it. `-d T` asks for the text
    report, which is where the second half of this holds: the report renders a bracket by
    reading its "scorelevel", "competitors" and "downfloaters", so a bracket carrying only
    a "pairs" key makes write_text_details raise KeyError. common_main swallows that into
    status 503, "Error when writing file" -- a message about the output file for a fault
    that has nothing to do with it.

    `-c -a` is the control here: analysis reconstructs the pairing the file declares
    rather than computing one, and this file does declare a fourth round, so on this
    fixture that path never reaches the unpairable state and must keep reporting the
    declared round exactly as it always did. (It is reachable in general -- a declared
    round that cannot be reconstructed as a legal sequence of brackets raises from the
    analysis call too -- which is why both call sites have to leave the exception alone.)

    Two assertions, both of which hold whatever the invocation: on an even field of four
    teams art. 1.4 allows no pairing-allocated bye, so no reported pair may name
    competitor 0; and no run may end in 503, which here can only mean a malformed bracket
    reached the report.
    """
    path = write(tmp_path, round_robin(declared=4))

    (checker, _) = run(path, options + ["-n", "4", "-d", "T"])

    assert [pair for pair in reported_pairs(checker) if 0 in pair] == []
    assert status(checker) != 503, "the text report faulted on a bracket it cannot render"


def test_no_legal_pairing_has_its_own_status_code(tmp_path):
    """An exhausted field is not a program error, and the CLI must not call it one.

    ``gacruxexeptions.py``: "GacruxNoLegalPairing is a state of the tournament, not a
    defect of the engine ... A caller that pairs a small tournament is expected to catch
    this exception -- not to log it as a crash." Status 510 is literally "Program error",
    so reporting this condition as 510 tells the caller the opposite of the truth, and
    leaves it no way to tell the one exception that is not a bug apart from the ones that
    are.

    505 is the status for it -- the neighbour of 504, the other code that means the round
    asked for cannot be paired -- and the message the engine wrote has to survive with it,
    because a bare code cannot say which bracket ran out.
    """
    path = write(tmp_path, round_robin(declared=3))

    (checker, output) = run(path, ["-p", "-d", "T"])

    assert status(checker) != 510, "an unpairable round is not a defect of the engine"
    assert status(checker) == 505
    assert "cannot be paired" in messages(checker)
    assert "no legal pairing" in messages(checker)
    assert "Program error" not in messages(checker)
    # And it reaches the user, not just the JSON: write_error_file prints the status.
    assert "505" in output
    assert "no legal pairing" in output


def test_a_declared_round_with_no_legal_pairing_is_not_accepted(tmp_path):
    """A file may not check out on a round the rules prescribe no pairing for.

    This is the corpus class the change turns over. Eighteen team records of
    tests/corpus reach a round whose field is exhausted, and they were accepted --
    marked valid, no disagreement -- because the checker computed the same maximum
    matching for them that had been written into the file. Neither side of that
    comparison came from C.04.6: art. 3.3.3 prescribes nothing at all for a round that
    cannot be completed, it hands the round to the Chief Arbiter, so agreeing with the
    file proves nothing about the file.

    The verdict for such a round is therefore not "check passed" and not "check failed"
    but "there is no pairing to compare against", which is what 505 says.
    """
    path = write(tmp_path, round_robin(declared=4))

    (checker, _) = run(path, ["-c"])

    assert status(checker) == 505
    assert status(checker) not in (0, 1), "a round the rules do not prescribe has no verdict"


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


# ---------------------------------------------------------------------------------
# 3.3 -- the individual engine reports an incompletable round, it does not return nothing
# ---------------------------------------------------------------------------------


def individual_line(startno, points, games):
    line = "001 "
    line += "%4d " % startno                     # start number
    line += "m    "                              # sex + title
    line += "%-33s " % ("Player %d, One" % startno)
    line += "%4d " % (2400 - 10 * startno)       # rating
    line += "NOR "                               # federation
    line += "%11d " % 0                          # fide id
    line += "1990/01/01 "                        # birth date
    line += "%4s " % points                      # points
    line += "%4d  " % startno                    # rank
    return line + "  ".join("%4d %s %s" % game for game in games)


def three_leaders_who_have_met_every_lower_player():
    """Eight players, five rounds played, and a sixth round that cannot be completed.

    Players 1, 2 and 3 have each beaten every one of players 4 to 8, so in round six each
    of them can only meet one of the other two -- three players, one pair, one left over.
    The field is even, so C.04.3 art. 1.9.1 allows no pairing-allocated bye, and the lower
    five, who have met only some of each other, cannot absorb the third leader either:
    the round-pairing cannot be completed on any reading of art. 1.9.
    """
    lower = [4, 5, 6, 7, 8]
    games = {startno: [] for startno in range(1, 9)}
    points = {startno: 0.0 for startno in range(1, 9)}
    for rnd in range(5):
        pairs = []
        used = set()
        for offset, leader in enumerate((1, 2, 3)):
            opponent = lower[(rnd + offset) % 5]
            pairs.append((leader, opponent))
            used.add(opponent)
        rest = [startno for startno in lower if startno not in used]
        pairs.append((rest[0], rest[1]))
        for index, (a, b) in enumerate(pairs):
            # Colours alternate so no colour preference decides anything here.
            (ca, cb) = ("w", "b") if (rnd + index) % 2 == 0 else ("b", "w")
            if a <= 3:
                (ra, rb) = ("1", "0")
                points[a] += 1
            else:
                (ra, rb) = ("=", "=")
                points[a] += 0.5
                points[b] += 0.5
            games[a].append((b, ca, ra))
            games[b].append((a, cb, rb))
    lines = ["012 Three leaders who have met every lower player", "042 2026-03-01", "XXR 7"]
    for startno in range(1, 9):
        lines.append(individual_line(startno, "%.1f" % points[startno], games[startno]))
    return "\n".join(lines) + "\n"


def test_art_1_9_3_an_incompletable_dutch_round_is_reported_not_returned_empty(tmp_path):
    """`-p` on a Dutch round that cannot be completed must say so, not report no pairs.

    C.04.3 art. 1.9.1 says the round-pairing is complete only when every player but at
    most one has been paired, and art. 1.9.3 hands an incompletable round to the Chief
    Arbiter. The individual engine has three exits for that state: the top score bracket
    with no edge at all, the last bracket that cannot be paired -- both already raise
    ``GacruxNoLegalPairing`` -- and a top-bracket remainder that a maximum matching cannot
    complete, which returned an empty round-pairing instead. The command line then
    reported status 0 with ``pairs: []``: a successful-looking pairing of nobody.

    The status has to be 505, the code for an unhandled incompletable round, and the
    message has to cite the article that says whose decision this now is.
    """
    path = write(tmp_path, three_leaders_who_have_met_every_lower_player(), "eight.trf")

    (checker, output) = run(path, ["-p"])

    assert status(checker) == 505, "an incompletable round is not a pairing of nobody"
    assert "1.9.3" in messages(checker)
    assert "2 competitors" in messages(checker)
    assert reported_pairs(checker) == []
    assert "505" in output
