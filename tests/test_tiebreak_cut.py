# -*- coding: utf-8 -*-
"""
Regression tests for the cut modifiers /Cn and /Mn on Buchholz and Sonneborn-Berger.

The cut is limited by the number of rounds, not by the number of games the competitor
actually has. A competitor who withdrew, entered late or was given byes has fewer games
than that, so a cut can consume every game he has.

The second half of the file is about which element a cut takes when the competitor has
unplayed rounds. C.07 art. 14.1.1.d cuts the contribution of the lowest-scoring
opponent; art. 16.5.1 makes an exception of a participant with one or more VURs, and
art. 16.4 gives those VURs dummy scores that can differ from one another. Every test
here drives a whole tournament through the engine and reads the values and the cut
rounds back off the standings, so a change in how the cut chooses shows up as a changed
value or a changed round, not only as a changed helper.
"""
import contextlib
import io
import os
import sys
import tempfile

import pytest

from gacrux import tiebreak
from gacrux import tiebreakchecker
from gacrux import trf2json

PAB = (0, "-", "U")  # pairing-allocated bye
HPB = (0, "-", "H")  # half-point bye
ZPB = (0, "-", "Z")  # zero-point bye

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
REAL_SWISS = os.path.join(_FIXTURES, "swiss_with_many_unplayed_rounds.trf")
GOLDEN_BEFORE = os.path.join(_FIXTURES, "swiss_with_many_unplayed_rounds.2026-02-28.txt")
GOLDEN_ON = os.path.join(_FIXTURES, "swiss_with_many_unplayed_rounds.2026-03-01.txt")


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


def withdrawal_after_round_1():
    # Round robin, five competitors, five rounds, Berger order. Player 5 withdraws after
    # round 1, so rounds 2-5 are a zero-point bye for him and a bye for each competitor
    # he was scheduled against. Games actually played: 1 has 3, 2 has 4, 3 has 3, 4 has 3
    # and 5 has 1.
    lines = ["012 Withdrawal in a round robin", "042 2026-03-01", "XXR 5"]
    lines.append(player_line(1, "One, Player", 2400, "4.5",
                             [PAB, (2, "w", "1"), (3, "b", "1"), (4, "w", "="), PAB]))
    lines.append(player_line(2, "Two, Player", 2300, "3.0",
                             [(5, "w", "1"), (1, "b", "0"), PAB, (3, "w", "1"), (4, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 2200, "2.5",
                             [(4, "w", "="), PAB, (1, "w", "0"), (2, "b", "0"), PAB]))
    lines.append(player_line(4, "Four, Player", 2100, "4.0",
                             [(3, "b", "="), PAB, PAB, (1, "b", "="), (2, "w", "1")]))
    lines.append(player_line(5, "Five, Player", 2000, "0.0",
                             [(2, "b", "0"), ZPB, ZPB, ZPB, ZPB]))
    return lines


def run(lines, tiebreaks, check=False, swiss=False):
    # swiss picks the unplayed-round rules of article 16 over the pre-determined pairing
    # rules, the way -s does on the command line.
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": tiebreaks, "check": check, "unrated": None,
              "pre_determined": not swiss, "swiss": swiss}
    tb = tiebreak.tiebreak(tournament, -1, params)
    return tb.compute_tiebreaks(tournament, params)


def compute(lines, tiebreaks, swiss=False):
    result = run(lines, tiebreaks, swiss=swiss)
    return dict([(cmp["cid"], str(cmp["tiebreakScore"][0])) for cmp in result["competitors"]])


def cut_rounds(lines, tiebreakname, startno, swiss=False):
    # The rounds a single cut modifier dropped, in the order it dropped them.
    result = run(lines, [tiebreakname], True, swiss=swiss)
    competitor = [cmp for cmp in result["competitors"] if cmp["cid"] == startno][0]
    return competitor["tiebreakDetails"][0]["cut"]


def test_buchholz_of_the_field():
    # Adjusted scores are 4.5, 3.0, 2.5, 4.0 and 0.0; unplayed rounds of a round robin do
    # not contribute an opponent. These are the sums the cuts below are taken from.
    assert compute(withdrawal_after_round_1(), ["BH"]) == {
        1: "9.5",    # 3.0 + 2.5 + 4.0
        2: "11.0",   # 0.0 + 4.5 + 2.5 + 4.0
        3: "11.5",   # 4.0 + 4.5 + 3.0
        4: "10.0",   # 2.5 + 4.5 + 3.0
        5: "3.0",    # 3.0
    }


def test_low_cut_larger_than_the_number_of_games():
    # BH/C2 drops the two lowest. Player 5 has one game, so everything he has is dropped
    # and his Buchholz is 0. Everybody else keeps the games the cut leaves.
    assert compute(withdrawal_after_round_1(), ["BH/C2"]) == {
        1: "4.0",    # 4.0                 (2.5 and 3.0 dropped)
        2: "8.5",    # 4.5 + 4.0           (0.0 and 2.5 dropped)
        3: "4.5",    # 4.5                 (3.0 and 4.0 dropped)
        4: "4.5",    # 4.5                 (2.5 and 3.0 dropped)
        5: "0",      # nothing left
    }


def test_high_cut_larger_than_the_number_of_games():
    # BH/M1 drops the lowest and then the highest. Player 5's single game goes with the
    # low cut, so the high cut has nothing left to drop.
    assert compute(withdrawal_after_round_1(), ["BH/M1"]) == {
        1: "3.0",    # 3.0                 (2.5 and 4.0 dropped)
        2: "6.5",    # 2.5 + 4.0           (0.0 and 4.5 dropped)
        3: "4.0",    # 4.0                 (3.0 and 4.5 dropped)
        4: "3.0",    # 3.0                 (2.5 and 4.5 dropped)
        5: "0",      # nothing left
    }


def test_sonneborn_berger_cuts():
    assert compute(withdrawal_after_round_1(), ["SB/C2"]) == {
        1: "2.00", 2: "0.00", 3: "0.00", 4: "2.25", 5: "0",
    }
    assert compute(withdrawal_after_round_1(), ["SB/M1"]) == {
        1: "3.00", 2: "2.50", 3: "2.00", 4: "3.00", 5: "0",
    }


@pytest.mark.parametrize("tb", ["BH/C5", "SB/C5"])
def test_cut_of_every_round(tb):
    # A cut of every round leaves nobody with a game, whatever he played.
    assert set(compute(withdrawal_after_round_1(), [tb]).values()) == set(["0"])


def test_cut_inside_the_number_of_games_is_unchanged():
    # A cut no competitor runs out of games on must keep the values it always had.
    assert compute(withdrawal_after_round_1(), ["BH/C1"]) == {
        1: "7.0",    # 3.0 + 4.0           (2.5 dropped)
        2: "11.0",   # 4.5 + 2.5 + 4.0     (0.0 dropped)
        3: "8.5",    # 4.5 + 4.0           (3.0 dropped)
        4: "7.5",    # 4.5 + 3.0           (2.5 dropped)
        5: "0",      # his one game dropped
    }


def swiss_with_absences(round3, startdate="2026-03-01"):
    # Swiss, five players, four rounds, dated by startdate. Player 2
    # takes a half-point bye in round 2 and plays his round 3 as round3 says: "-" is a
    # forfeit loss and gives him a second VUR (art. 16.1.2), "0" is an ordinary loss and
    # leaves him with one. Nothing else changes, every score included.
    #
    # Art. 16.4 caps the two VURs differently - the bye at the points for a draw times
    # the number of rounds, 0.5 * 4 = 2.0 (art. 16.4.2), the forfeit at the scheduled
    # opponent's adjusted score, 4.0, which leaves player 2's own 2.5 (art. 16.4.1). So
    # the bye is the VUR against the lower-scoring dummy while the forfeit is the VUR
    # with the lower contribution, and the two candidates come apart.
    #
    # Player 2's four elements, as opponent score x own result:
    #     round 1  0.5 x 1.0 = 0.50   played, opponent 5 scored 0.5
    #     round 2  2.0 x 0.5 = 1.00   VUR, half-point bye
    #     round 3  2.5 x 0.0 = 0.00   VUR when forfeited, opponent 1 scored 4.0 when not
    #     round 4  1.5 x 1.0 = 1.50   played, opponent 4 scored 1.5
    #
    # Rounds 2 and 3 are the two the caps touch, so a startdate before 2026-03-01
    # gives both of them player 2's own 2.5 instead. See the boundary test below.
    forfeited = round3 == "-"
    lines = ["012 Sonneborn-Berger cut with a requested absence", "022 Oslo", "032 NOR",
             "042 " + startdate, "052 2026-03-04", "062 5", "072 0", "092 Swiss System",
             "XXR 4"]
    lines.append(player_line(1, "Winner, Wanda", 2400, "4.0",
                             [(4, "w", "1"), (3, "b", "1"),
                              (2, "w", "+" if forfeited else "1"), (5, "b", "1")]))
    lines.append(player_line(2, "Cutcase, Cato", 2300, "2.5",
                             [(5, "w", "1"), HPB, (1, "b", round3), (4, "w", "1")]))
    lines.append(player_line(3, "Middle, Mons", 2200, "2.0",
                             [PAB, (1, "w", "0"), (5, "w", "1"), ZPB]))
    lines.append(player_line(4, "Lower, Lars", 2100, "1.5",
                             [(1, "b", "0"), (5, "b", "="), PAB, (2, "b", "0")]))
    lines.append(player_line(5, "Tailend, Tor", 2000, "0.5",
                             [(2, "b", "0"), (4, "w", "="), (3, "b", "0"), (1, "w", "0")]))
    return lines


def two_requested_absences():
    return swiss_with_absences("-")


def one_requested_absence():
    return swiss_with_absences("0")


def test_art_16_5_1_selects_the_vur_by_contribution_not_by_opponent_score():
    # Art. 16.5.1: "When a modifier calls for cutting the least significant value (see
    # Articles 14.1 to 14.4) of a participant with one or more VURs, the lowest
    # contribution coming from such rounds shall be cut, as long as such contribution is
    # not lower than the least significant value." The handbook spells the comparison
    # out for Sonneborn-Berger: determine the lowest contribution coming from a VUR and
    # the least significant value (art. 14.1.1.d), then "cut the higher of these two
    # values".
    #
    # For player 2 the lowest contribution coming from a VUR is round 3's 0.00, not
    # round 2's 1.00: art. 16.5.1 ranks the VURs by contribution, and the lower dummy
    # score behind round 2 does not make it the candidate. The least significant value
    # is round 1's 0.50, the contribution against the lowest-scoring opponent. The
    # higher of 0.00 and 0.50 is 0.50, so round 1 is cut and 2.50 is left.
    #
    # Ranking the VURs by their dummy score instead would take round 2, whose dummy is
    # capped at 2.0 against the other's 2.5, and leave 2.00.
    assert compute(two_requested_absences(), ["SB"], swiss=True)[2] == "3.00"
    assert compute(two_requested_absences(), ["SB/C1"], swiss=True)[2] == "2.50"
    assert cut_rounds(two_requested_absences(), "SB/C1", 2, swiss=True) == [1]


def test_art_16_5_2_reapplies_the_exception_to_the_remaining_elements():
    # Art. 16.5.2: "Rule 16.5.1 applies again to the remaining elements when the
    # modifier requires more cuts." Rounds 2, 3 and 4 remain after the first cut. The
    # lowest contribution coming from a VUR is still round 3's 0.00; the least
    # significant value is now round 4's 1.50, against the lowest-scoring opponent left.
    # The higher of the two is 1.50, so round 4 goes and 1.00 is left.
    assert compute(two_requested_absences(), ["SB/C2"], swiss=True)[2] == "1.00"
    assert cut_rounds(two_requested_absences(), "SB/C2", 2, swiss=True) == [1, 4]


def test_art_16_5_1_leaves_a_single_vur_cut_alone():
    # With one VUR there is nothing to rank, so the exception behaves as it always has.
    # The only contribution coming from a VUR is round 2's 1.00 and the least
    # significant value is round 1's 0.50; the higher is 1.00, so the VUR is cut. The
    # second cut has no VUR left and falls back to art. 14.1.1.d alone, taking round 1.
    assert compute(one_requested_absence(), ["SB"], swiss=True)[2] == "3.00"
    assert compute(one_requested_absence(), ["SB/C1"], swiss=True)[2] == "2.00"
    assert compute(one_requested_absence(), ["SB/C2"], swiss=True)[2] == "1.50"
    assert cut_rounds(one_requested_absence(), "SB/C1", 2, swiss=True) == [2]
    assert cut_rounds(one_requested_absence(), "SB/C2", 2, swiss=True) == [2, 1]


def test_art_16_4_caps_apply_from_the_start_date_of_the_2026_rules():
    # Art. 16.4: "To calculate the participant's own tie-break, each of their unplayed
    # rounds is evaluated as if the participant had played against a dummy [...] The
    # dummy's score for the tie-break calculation is the participant's own score.
    # However, it shall not exceed: 16.4.1 the scheduled opponent's adjusted score (see
    # Article 16.3), for unplayed rounds of categories 16.2.2 and 16.2.4 (forfeits);
    # 16.4.2 the points awarded for a draw multiplied by the number of rounds in the
    # tournament, for all other unplayed rounds".
    #
    # Those caps arrived with the rules of 2026-03-01, and find_tmversion picks the rule
    # set from the tournament's start date. The engine therefore has to give the same
    # file two different answers either side of that date, which is what this pins.
    #
    # Player 2 scores 2.5 and there are four rounds, so under the 2026 rules the bye is
    # capped at 0.5 * 4 = 2.0 and the forfeit keeps his own 2.5. Without the caps both
    # dummies take his own 2.5, and the bye contributes 2.5 * 0.5 = 1.25 rather than
    # 1.00. That is the whole of the difference: 3.25 against 3.00.
    before = swiss_with_absences("-", "2026-02-28")
    on_the_day = swiss_with_absences("-", "2026-03-01")

    assert compute(before, ["SB"], swiss=True)[2] == "3.25"
    assert compute(on_the_day, ["SB"], swiss=True)[2] == "3.00"

    # The cuts move with the caps. Before the caps the two VURs share one dummy score, so
    # the lowest-scoring VUR and the lowest-contribution VUR cannot come apart and the
    # ordinary art. 14.1.1.d candidate wins both cuts.
    assert compute(before, ["SB/C1"], swiss=True)[2] == "2.75"
    assert compute(before, ["SB/C2"], swiss=True)[2] == "1.25"
    assert cut_rounds(before, "SB/C1", 2, swiss=True) == [1]
    assert cut_rounds(before, "SB/C2", 2, swiss=True) == [1, 4]

    assert compute(on_the_day, ["SB/C1"], swiss=True)[2] == "2.50"
    assert compute(on_the_day, ["SB/C2"], swiss=True)[2] == "1.00"


def equal_vur_contribution():
    # Swiss, five players, four rounds, under the 2026 rules. Player 2 takes a half-point
    # bye in round 2 and plays the other three, and the field is scored so that his VUR
    # contributes exactly as much as his least significant played element - which is what
    # puts the "as long as such contribution is not lower" of art. 16.5.1 on the boundary.
    #
    # Player 2 scores 3.0 and there are four rounds, so art. 16.4.2 caps the bye's dummy
    # at 0.5 * 4 = 2.0. His four elements, as opponent score x own result:
    #
    #     round 1  1.0 x 1.0 = 1.00   played, opponent 5 adjusted to 1.0
    #     round 2  2.0 x 0.5 = 1.00   VUR, half-point bye     <- equal, and a VUR
    #     round 3  3.0 x 0.5 = 1.50   played, opponent 1 adjusted to 3.0
    #     round 4  2.0 x 1.0 = 2.00   played, opponent 3 adjusted to 2.0
    #
    # Round 1 is the least significant value under art. 14.1.1.d: its opponent's 1.0 is
    # the lowest score on the list. Its contribution is 1.00 and the VUR's is 1.00 too.
    lines = ["012 Sonneborn-Berger cut on the not-lower boundary", "022 Oslo", "032 NOR",
             "042 2026-03-01", "052 2026-03-04", "062 5", "072 0", "092 Swiss System",
             "XXR 4"]
    lines.append(player_line(1, "Toppen, Tore", 2400, "3.0",
                             [(4, "w", "1"), (3, "w", "1"), (2, "w", "="), (5, "b", "=")]))
    lines.append(player_line(2, "Boundary, Bodil", 2300, "3.0",
                             [(5, "w", "1"), HPB, (1, "b", "="), (3, "w", "1")]))
    lines.append(player_line(3, "Midten, Mari", 2200, "2.0",
                             [PAB, (1, "b", "0"), (4, "w", "1"), (2, "b", "0")]))
    lines.append(player_line(4, "Nede, Nils", 2100, "1.5",
                             [(1, "b", "0"), (5, "w", "="), (3, "b", "0"), PAB]))
    lines.append(player_line(5, "Sisten, Siri", 2000, "1.0",
                             [(2, "b", "0"), (4, "b", "="), ZPB, (1, "w", "=")]))
    return lines


def test_equal_vur_contribution_is_cut_as_not_lower():
    """Art. 16.5.1 cuts the VUR when its contribution equals the least significant value.

    The article cuts the lowest contribution coming from a VUR "as long as such
    contribution is not lower than the least significant value", so equality belongs to
    the VUR side of the comparison and the VUR is what goes.

    Player 2's VUR and his round 1 contribute the same 1.00, so the first cut removes
    1.00 whichever of the two it takes and SB/C1 is 4.50 either way. Only the round says
    which element went, which is why this test reads the cut rounds and not just the
    value: the engine has to report round 2.

    The second cut is the consequence. With the VUR gone the remaining elements are
    ordinary, art. 16.5.1 no longer applies, and round 1 - still the lowest-scoring
    opponent - is the one taken, in that order.
    """
    lines = equal_vur_contribution()

    assert compute(lines, ["SB"], swiss=True)[2] == "5.50"
    assert compute(lines, ["SB/C1"], swiss=True)[2] == "4.50"
    assert cut_rounds(lines, "SB/C1", 2, swiss=True) == [2]

    assert compute(lines, ["SB/C2"], swiss=True)[2] == "3.50"
    assert cut_rounds(lines, "SB/C2", 2, swiss=True) == [2, 1]


def checker_output(lines, tiebreaks):
    # Drive the real command-line checker in-process, the way tests/corpus/_harness.py
    # does, so a golden file is byte for byte what
    #     python -m gacrux.tiebreakchecker -i FILE -o OUT -c -dT -t PTS SB SB/C1 SB/C2
    # writes. Comparing whole outputs rather than a dict of values keeps the golden
    # reviewable in a diff and catches a change of rank or of the Check line too.
    workdir = tempfile.mkdtemp()
    source = os.path.join(workdir, "tournament.trf")
    output = os.path.join(workdir, "tiebreaks.txt")
    with open(source, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    saved_argv = sys.argv
    sys.argv = ["tiebreakchecker", "-i", source, "-o", output, "-c", "-dT", "-t"] + tiebreaks
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                tiebreakchecker.tiebreakchecker().common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved_argv
    with open(output, encoding="utf-8") as handle:
        return handle.read()


def golden(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def real_swiss(startdate=None):
    # Fifteen players, seven rounds, a real Swiss with names, federation, identifiers and
    # birth dates removed. It is thick with unplayed rounds - half-point byes, zero-point
    # byes, pairing-allocated byes and forfeits on both sides - which is what makes it
    # worth keeping: the article 16 paths are exercised on a real pairing history rather
    # than on a fixture built to reach them.
    #
    # The file is dated 2026-02-28, the last day before the March 2026 rules, so as it
    # stands it runs under the rules of 2024-08-01. startdate re-dates it in memory.
    lines = open(REAL_SWISS, encoding="utf-8").read().split("\n")
    if startdate is None:
        return lines
    return [("042 " + startdate) if line.startswith("042 ") else line for line in lines]


TIEBREAKS = ["PTS", "SB", "SB/C1", "SB/C2"]


def test_a_real_swiss_the_day_before_the_2026_rules():
    # 2026-02-28: no article 16.4 cap applies, so every VUR of a participant takes that
    # participant's own score as its dummy. Nothing here depends on how the VURs of one
    # participant are ranked against each other, because without the caps they all carry
    # the same dummy score and cannot be ranked apart.
    assert checker_output(real_swiss(), TIEBREAKS) == golden(GOLDEN_BEFORE)


def test_a_real_swiss_on_the_day_the_2026_rules_start():
    # 2026-03-01: the caps apply, so this is the same file measured under the other rule
    # set. Start number 4 is the row the art. 16.5.1 tie-break between equal VUR
    # contributions decides; his SB/C2 of 5.00 is derived element by element in
    # test_art_16_5_1_ties_among_equal_vur_contributions_go_to_the_lowest_opponent_score
    # below. Regenerate this golden only when a value change is intended, and say in the
    # commit message which cells moved.
    assert checker_output(real_swiss("2026-03-01"), TIEBREAKS) == golden(GOLDEN_ON)


def changed_rows(left, right):
    # The start numbers whose row differs between two checker outputs, plus any change to
    # the trailing Check line.
    lrows = left.rstrip("\n").split("\n")
    rrows = right.rstrip("\n").split("\n")
    assert len(lrows) == len(rrows), "outputs have different shapes"
    changed = set()
    for lrow, rrow in zip(lrows, rrows):
        if lrow != rrow:
            key = lrow.split("\t")[0]
            changed.add("Check" if key.startswith("Check") else key)
    return changed


def test_the_2026_caps_change_this_tournament():
    # What crossing 2026-03-01 does to one real tournament, so that the pair of goldens
    # is read as a pair and a regeneration that flattened the difference would be caught.
    assert changed_rows(golden(GOLDEN_BEFORE), golden(GOLDEN_ON)) == {
        "1", "3", "4", "5", "9", "10", "11", "12", "14", "Check",
    }
    assert golden(GOLDEN_BEFORE).endswith("Check: True\n")
    assert golden(GOLDEN_ON).endswith("Check: False\n")


def test_art_16_5_1_ties_among_equal_vur_contributions_go_to_the_lowest_opponent_score():
    """Art. 16.5.1 breaks a tie between equal VUR contributions by the opponent's score.

    Start number 4 of the real Swiss forfeited rounds 1, 2 and 3, so all three are VURs
    contributing 0.00, but art. 16.4.1 caps their dummy scores at the scheduled
    opponent's adjusted score and gives them 2.5, 1.5 and 2.5. His seven elements are:

        round 1  2.5 x 0.0 = 0.00   VUR, forfeit loss
        round 2  1.5 x 0.0 = 0.00   VUR, forfeit loss   <- least significant value
        round 3  2.5 x 0.0 = 0.00   VUR, forfeit loss
        round 4  2.5 x 1.0 = 2.50   pairing-allocated bye
        round 5  2.0 x 0.5 = 1.00   played
        round 6  2.5 x 0.5 = 1.25   played
        round 7  2.5 x 0.5 = 1.25   played

    Round 2 is the least significant value - its opponent's score, 1.5, is the lowest -
    and it is itself a VUR, so by art. 16.5.1's "they are the same element if the least
    significant value comes from a VUR" it is the element the first cut must take.

    Cut-1 removes 0.00 whichever of the three goes, so SB/C1 is 6.00 either way and the
    cut round is what says which element went. Cut-2 is where the value shows it: with
    round 2 gone the least significant value left is round 5's 1.00, and the lowest
    remaining VUR contribution, 0.00, is lower than that, so art. 16.5.1 does not apply
    and the ordinary candidate is cut, for 6.00 - 1.00 = 5.00. Taking round 1 first
    leaves round 2 in the pool and cuts another 0.00, for 6.00.
    """
    lines = real_swiss("2026-03-01")

    assert compute(lines, ["SB"], swiss=True)[4] == "6.00"
    assert compute(lines, ["SB/C1"], swiss=True)[4] == "6.00"
    assert cut_rounds(lines, "SB/C1", 4, swiss=True) == [2]

    assert compute(lines, ["SB/C2"], swiss=True)[4] == "5.00"
    assert cut_rounds(lines, "SB/C2", 4, swiss=True) == [2, 5]
