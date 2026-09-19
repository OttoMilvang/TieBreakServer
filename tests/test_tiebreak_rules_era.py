# -*- coding: utf-8 -*-
"""
Which tie-break rule set a tournament is scored under is decided by its START DATE.

tiebreak.TIEBREAK_RULES maps a rule-set number to the date that set came into force, and
find_tmversion() picks the set by comparing the tournament's start date to the 2026 entry:
a tournament that started before 2026-03-01 is scored under the earlier rules, one that
started on or after it under the 2026 rules approved by the FIDE Council on 02/02/2026.

The date therefore has to be READ. It used to be MEASURED instead --

    if len(startdate) != 10:
        startdate = str(datetime.now())[0:10]
    if startdate < self.TIEBREAK_RULES[2]:

-- which made two different things go wrong at once. Any start date that was not exactly
ten characters long was treated as absent and replaced with today's local date, so a TRF
line carrying trailing padding or a time of day (``042 2026-02-28   ``, ``042 2026-02-28
10:00``) selected a different rule set from the same line without them. Trailing padding is
ordinary in a fixed-width TRF, so the same tournament could be scored two different ways
depending on whitespace nobody can see. And the substitute was ``datetime.now()``, the naive
local clock, so an undated file's tie-breaks changed across local midnight and differed
between machines in different time zones.

These tests pin the rule set selected for each shape of start date. Every case names the
date it means and the rule set that date is entitled to, so a wrong answer is visible as a
wrong rule set rather than as an accepted string.
"""
import pytest

from gacrux import tiebreak
from gacrux import trf2json


# The rule sets, by the name find_tmversion() selects them under. Spelled out here so the
# assertions below read as "this date gets the 2026 rules", not as "this date gets a 2".
RULES_2024 = 1
RULES_2026 = 2
CUTOFF = "2026-03-01"

assert tiebreak.tiebreak.TIEBREAK_RULES[RULES_2026] == CUTOFF
assert max(tiebreak.tiebreak.TIEBREAK_RULES) == RULES_2026


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


def tournament_dated(dateline):
    """A minimal one-round tournament, with *dateline* as its whole 042 record, or none."""
    lines = ["012 Rule era test"]
    if dateline is not None:
        lines.append(dateline)
    lines += ["XXR 1",
              player_line(1, "One, Player", 2000, "1.0", [(2, "w", "1")]),
              player_line(2, "Two, Player", 1900, "0.0", [(1, "b", "0")])]
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    return chessfile.get_tournament(1)


def selected_rules(tournament):
    """The rule set the engine scores *tournament* under, through the public entry point."""
    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    engine = tiebreak.tiebreak(tournament, -1, params)
    engine.compute_tiebreaks(tournament, params)
    return engine.rulesversion


@pytest.mark.parametrize(
    "dateline, expected",
    [
        # The plain ISO date on each side of the cut-off: the baseline both padded forms
        # below have to agree with.
        pytest.param("042 2026-02-28", RULES_2024, id="iso-before-cutoff"),
        pytest.param("042 2026-03-01", RULES_2026, id="iso-on-cutoff"),
        # Trailing padding. A fixed-width TRF pads its fields as a matter of course, and
        # 2026-02-28 is 2026-02-28 whether or not spaces follow it. Selected the 2026 rules
        # before the fix, because 13 != 10 meant "no date, use today", and today is past the
        # cut-off. The pair is what makes this discriminating: a padded date on each side of
        # the cut-off must give a DIFFERENT answer, which "always use today" cannot do.
        pytest.param("042 2026-02-28   ", RULES_2024, id="padded-before-cutoff"),
        pytest.param("042 2026-03-15   ", RULES_2026, id="padded-after-cutoff"),
        # A time of day after the date, likewise. The tournament started on 28 February
        # whatever o'clock it was; 16 != 10 meant "use today" before the fix.
        pytest.param("042 2026-02-28 10:00", RULES_2024, id="timestamped-before-cutoff"),
        pytest.param("042 2026-03-15 10:00", RULES_2026, id="timestamped-after-cutoff"),
        # Slash-separated, four-digit year. helpers.parse_date() normalises the separators,
        # so what reaches find_tmversion() is an ordinary ISO date and 15 March is after the
        # cut-off.
        pytest.param("042 2026/03/15", RULES_2026, id="slash-four-digit-year"),
        # No 042 record at all. The fallback: an undated tournament is scored under the
        # NEWEST rules -- a fixed choice, so that the answer does not depend on the clock of
        # the machine that happens to run the calculation, or on which side of local midnight
        # it runs. See find_tmversion() for why it is not an error.
        pytest.param(None, RULES_2026, id="no-042-record"),
    ],
)
def test_start_date_is_read_not_measured(dateline, expected):
    assert selected_rules(tournament_dated(dateline)) == expected


def test_a_null_start_date_selects_the_fallback_rather_than_raising():
    """startDate present but JSON null -- ``len(None)`` used to raise TypeError.

    A TRF cannot express this, but the engine also reads tournaments straight from JSON,
    where a "startDate": null is an ordinary way to say the date is not known. It is the
    same state as an absent record and takes the same documented fallback, the newest rules.
    """
    tournament = tournament_dated("042 2026-02-28")
    tournament["tournamentInfo"]["startDate"] = None

    assert selected_rules(tournament) == RULES_2026


def test_the_fallback_does_not_depend_on_the_clock():
    """An undated tournament must get the same rule set on every machine, on every day.

    The fallback is the newest rule set by construction, not by comparing today against the
    cut-off -- so this asserts the identity, which no local clock can change, rather than
    the number 2, which a future rule set would move.
    """
    assert selected_rules(tournament_dated(None)) == max(tiebreak.tiebreak.TIEBREAK_RULES)


def test_a_two_digit_year_is_expanded_upstream_and_the_era_follows_it():
    """``042 01/03/26`` selects the pre-2026 rules, because it arrives as the year 2001.

    This pins a limitation that is NOT find_tmversion's to fix, so that it is recorded
    rather than mistaken for correct behaviour. helpers.parse_date() expands a two-digit
    year by prefixing "20" to the FIRST component of the date --

        return "20" + date.replace("/", "-")        # helpers.py

    -- so "01/03/26" becomes "2001-03-26" before find_tmversion() ever sees it, and the
    day/month/year reading that produced it (1 March 2026) is unrecoverable by then.
    find_tmversion() does the right thing with the date it is handed: 2001-03-26 is long
    before the cut-off and is entitled to the earlier rules. The defect is the expansion,
    in helpers.parse_date(), and it is where the fix belongs.

    If parse_date() is corrected to read the year last, this test fails and should be
    changed to expect RULES_2026 -- which is the point of asserting the era here rather
    than asserting the string.
    """
    assert selected_rules(tournament_dated("042 01/03/26")) == RULES_2024
