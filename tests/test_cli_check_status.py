# -*- coding: utf-8 -*-
"""
The status code `pairingchecker -c` reports, and what each of its four modes compares.

`-c` answers one question: is the pairing the file declares the pairing the engine would
have made? `-a` and `-p` say which side of that comparison to compute and show -- `-a`
reconstructs the declared pairing, `-p` computes the engine's own -- and `-c` on its own
computes both. So only two of the four combinations have two sides to compare:

    -c          both sides computed  -> the verdict is meaningful
    -c -a -p    both sides computed  -> the verdict is meaningful
    -c -a       only the declared side; the engine's side is empty
    -c -p       only the engine's side; the declared side is empty

In the one-sided modes the comparison is between a pairing and nothing, which is never
equal, so the verdict has to be suppressed rather than reported as a difference. The text
report already knows this and prints its "Check:" line only when the two flags agree
(`(self.dopairing > 0) == (self.doanalysis > 0)`, write_text_file). apply_result meant to
say the same thing with the opposite sense and instead wrote

    ok = ok or (self.dopairing > 0 ^ self. doanalysis > 0)

`^` binds tighter than a comparison operator, so `0 ^ self.doanalysis` is evaluated first
and what is left is a *chained* comparison, which Python reads as

    (self.dopairing > (0 ^ self.doanalysis)) and ((0 ^ self.doanalysis) > 0)

that is, `dopairing > doanalysis and doanalysis > 0`. Over the four combinations of the
two counts -- (0,0), (1,0), (0,1) and (1,1) -- that is False, False, False and False: the
term never fires, so it never suppresses anything, and `-c -p` and `-c -a` report status 1
on every run, including runs where the file is right in every particular.

The fixture is the eight-player FIDE_DUTCH_2025 tournament of tests/fixtures, whose two
played rounds are both exactly what the engine pairs; `-c` over it is the repository's
standard example of a file that checks out.
"""
import contextlib
import io
import os
import sys

import pytest

from gacrux import pairingchecker

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "no_colour_preference.trf")

# The four ways of asking `-c` for a verdict. The first two compare two computed sides;
# the last two have only one side and therefore no difference to report.
MODES = [
    pytest.param([], id="check"),
    pytest.param(["-p", "-a"], id="check-pairing-analysis"),
    pytest.param(["-p"], id="check-pairing"),
    pytest.param(["-a"], id="check-analysis"),
]

TWO_SIDED = [
    pytest.param([], id="check"),
    pytest.param(["-p", "-a"], id="check-pairing-analysis"),
]


def check(options, path=FIXTURE):
    """Run the real checker in check mode and return the status code it reports."""
    checker = pairingchecker.pairingchecker()
    saved = sys.argv
    sys.argv = ["pairingchecker", "-i", path, "-c"] + options
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                checker.common_main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
    return checker.resultjson.get("status", {}).get("code")


@pytest.mark.parametrize("options", MODES)
def test_check_with_pairing_exits_zero_on_a_matching_round(options):
    """Every mode of `-c` reports success on a file whose rounds all match.

    Status 1 is reserved for "the declared pairing differs from the prescribed one", and
    this file has no such difference: `-c` alone, which compares both computed sides,
    reports 0 on it. `-c -p` and `-c -a` look at the same file and the same rounds and can
    discover nothing `-c` did not, so any status they report other than 0 is manufactured
    by the checker rather than found in the tournament -- and 1 in particular tells a
    script driving the checker that a correct file is wrong.
    """
    assert check(options) == 0


def a_round_two_the_engine_pairs_the_other_way_round(tmp_path):
    """The fixture with the colours of one round-two pair the wrong way round.

    Players 1 and 4 drew in round two, 1 with White. Declaring the same game as 4-1
    leaves every result, every score and every board untouched, so the file still reads
    and still ranks the same way, but the pairing it declares is no longer the pairing
    the engine prescribes: the comparison has a real difference in it.
    """
    with open(FIXTURE, encoding="latin1") as handle:
        trf = handle.read()
    trf = trf \
        .replace("1.5    0     5 b 1     4 w =", "1.5    0     5 b 1     4 b =") \
        .replace("1.5    0     8 w 1     1 b =", "1.5    0     8 w 1     1 w =")
    path = tmp_path / "swapped.trf"
    path.write_text(trf, encoding="latin1")
    return str(path)


@pytest.mark.parametrize("options", TWO_SIDED)
def test_a_round_that_does_not_match_is_still_reported_as_a_difference(options, tmp_path):
    """The two-sided modes must still be able to say no.

    Suppressing the verdict where there is nothing to compare is only correct if it does
    not also suppress it where there is, so both modes that compute both sides have to
    keep reporting status 1 for a round that really does differ. The one-sided modes are
    deliberately not exercised here: after the fix they report 0 for this file too,
    because a one-sided run compares a pairing against nothing and cannot tell a
    corrupted round from a correct one.
    """
    path = a_round_two_the_engine_pairs_the_other_way_round(tmp_path)

    assert check(options + ["-n", "2"], path) == 1


@pytest.mark.parametrize("options", TWO_SIDED)
def test_an_exchanged_round_is_reported_as_a_difference(options):
    """`-T` rewrites the declared pairs of the round being checked.

    Round two of the fixture is 1-4 and 3-2. `-T 1-2 3-4` declares it as 1-2 and 3-4
    instead, the same four players with other opponents, which is not the pairing the
    engine prescribes. Both two-sided modes have to apply the exchange and report the
    round as a difference (status 1), not refuse the exchange as malformed (status 410).
    """
    assert check(options + ["-n", "2", "-T", "1-2", "3-4"]) == 1


@pytest.mark.parametrize("options", TWO_SIDED)
def test_an_exchange_that_undoes_a_swap_is_reported_as_a_match(options, tmp_path):
    """The reverse case: round two of the swapped file declares 4-1, and `-T 1-4` puts
    the pair back the way the engine prescribes it, so the round matches (status 0)."""
    path = a_round_two_the_engine_pairs_the_other_way_round(tmp_path)

    assert check(options + ["-n", "2", "-T", "1-4"], path) == 0
