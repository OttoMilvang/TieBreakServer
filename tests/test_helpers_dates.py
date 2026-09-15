# -*- coding: utf-8 -*-
"""
helpers.parse_date - the date formats the readers accept, and what they mean.

parse_date normalises the several ways a date reaches the readers into the
"YYYY-MM-DD" the JSON event carries, keeping any time of day that came with it.
ts2json feeds it the start and end of the event, the start of a round, the
enrolment deadline and a competitor's date of birth, so a round's startTime and
an enrolment deadline lose their meaning if the time is dropped.

The two separated formats do not read their fields in the same order, and that
is what most of these tests are here to record:

    01.03.2026   dotted, day first    -> 2026-03-01
    26/03/01     slashed, year first  -> 2026-03-01

Both are pinned below. The slashed form is year-first because the TRF
specification says so: TRF-2026 and TRF-2016 give record 132, the dates of the
rounds, the format YY/MM/DD, and records 042 and 052 and the birth date of
record 001 the format YYYY/MM/DD. The year comes first in every slashed date a
TRF carries, with two figures in 132 and four elsewhere.
"""
import pytest

from gacrux import helpers


@pytest.mark.parametrize(
    "text, expected",
    [
        # Already normalised: passed through untouched.
        ("2026-03-01", "2026-03-01"),
        ("2026-03-01 10:00", "2026-03-01 10:00"),
        # Dotted with a four-figure year first: separators swapped, nothing else.
        ("2026.03.01", "2026-03-01"),
        # Dotted, day first - the ordinary continental form.
        ("01.03.2026", "2026-03-01"),
        ("31.12.2025", "2025-12-31"),
        # Slashed. The century is supplied and the fields are NOT reordered, so
        # the first field is the year: 26/03/01 is the first of March 2026.
        ("26/03/01", "2026-03-01"),
        ("2026/03/01", "2026-03-01"),
    ],
)
def test_parse_date_normalises_the_accepted_forms(text, expected):
    assert helpers.parse_date(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2026-03-01 10:00", "2026-03-01 10:00"),
        ("2026.03.01 10:00", "2026-03-01 10:00"),
        ("01.03.2026 10:00", "2026-03-01 10:00"),
        ("26/03/01 10:00", "2026-03-01 10:00"),
    ],
)
def test_parse_date_keeps_the_time_of_day(text, expected):
    """A time given with the date survives, whichever form the date is in.

    Three of the four forms already kept it. The day-first dotted form did not:
    its branch tested len(dateparts) == 2 while standing inside a branch that
    had already established len(dateparts) == 3, so the line that re-attached
    the time could never run and the time was dropped. ts2json reads a round's
    startTime and the enrolment deadline through here, so that silently turned
    a deadline into midnight.
    """
    assert helpers.parse_date(text) == expected


def test_a_slashed_two_figure_year_is_read_as_the_year_and_not_as_the_day():
    """01/03/26 is 26 March 2001, not 1 March 2026.

    The slashed branch prefixes the century and leaves the field order alone, so
    the first field is the year - the opposite of the dotted branch, where the
    first field is the day. This test exists so that the difference is a
    recorded decision rather than a surprise: a file that means 1 March 2026 has
    to write 26/03/01, and one that writes 01/03/26 gets 2001.

    That is what the specification prescribes, not a guess about the files:
    TRF-2026 and TRF-2016 both give record 132 (dates of the rounds) the format
    YY/MM/DD, so 26/03/01 in a 132 record is 1 March 2026 by definition, and
    the four-figure YYYY/MM/DD of records 042, 052 and the birth date puts the
    year first as well.
    """
    assert helpers.parse_date("01/03/26") == "2001-03-26"
    assert helpers.parse_date("26/03/01") == "2026-03-01"
