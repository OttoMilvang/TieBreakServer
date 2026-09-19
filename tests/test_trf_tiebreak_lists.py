# -*- coding: utf-8 -*-
"""
Records 202 and 212, the tie-break lists.

Neither record changes a score or a pairing. Both decide a rank: they name the tie-breaks,
in order, that turn a table of equal scores into a finishing order, and the standings a
tournament publishes are the standings these two records ask for. compute_tiebreaks()
takes the list from tournament["rankOrder"] whenever the caller has not supplied one of
its own, computes each named tie-break in turn, and ranks by them left to right.

The two records are read by one function with one flag:

    202  ->  parse_tiebreaks(tournament, line, False)
    212  ->  parse_tiebreaks(tournament, line, True)

and the whole of what that flag does is prepend the string "PTS":

    def parse_tiebreaks(self, tournament, line, has_pts):
        pts = "" if has_pts else "PTS "
        self.tiebreaks = (pts + line[4:]).replace(",", " ").split(" ")
        tournament["rankOrder"] = self.tiebreaks

That is the difference between the records and it is not a formatting detail. Record 202
is "the tie-breaks used to break ties", so the points come first by definition and the
record lists only what settles a tie among competitors already level on points. Record 212
is "the tie-breaks used to define standings", so it is the whole ordering and the points
are in it only if the file says so. A 212 record that does not name PTS asks for standings
that ignore the score, and the reader gives exactly that -- which is the sharpest way to
show what the flag is worth, and what the tests below do.

The reader takes the names as it finds them. It does not check that a name is a tie-break
it knows, does not remove a duplicate, and does not collapse a repeated separator, so a
record that names PTS itself under 202 gets it twice and a record written with two spaces
between two names gets an empty name between them. Those are pinned as they stand.

Not one of the 6,000 fixtures in tests/corpus carries a record 202, so the corpus cannot
reach this parser: 5,521 of them carry a 212 record and none a 202. Record 202 is
covered here and nowhere else.
"""
import decimal

import pytest

from gacrux import tiebreak
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


def buchholz_inverts_the_score(records):
    """Four players, two rounds, arranged so that Buchholz reverses the standings.

    Players 1 and 2 each beat players 4 and 3; players 3 and 4 lose both games. So the
    scores are 2.0, 2.0, 0.0, 0.0 and the two winners finish ahead of the two losers on
    points.

    Buchholz is the sum of a competitor's opponents' scores, and here every one of player
    1's and player 2's opponents scored 0.0 while every one of player 3's and player 4's
    scored 2.0. Buchholz is therefore 0.0, 0.0, 4.0, 4.0 -- the exact opposite order.

    A field this lopsided is not a tournament anybody would run, and that is the point: it
    makes "the points come first" and "the points are not in the list at all" produce
    different finishing orders on the same games, so a test can tell the two apart without
    depending on how ties among equals are broken.
    """
    lines = ["012 Buchholz reverses the standings", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2400, "2.0", [(4, "w", "1"), (3, "b", "1")]))
    lines.append(player_line(2, "Two, Player", 2300, "2.0", [(3, "w", "1"), (4, "w", "1")]))
    lines.append(player_line(3, "Three, Player", 2200, "0.0", [(2, "b", "0"), (1, "w", "0")]))
    lines.append(player_line(4, "Four, Player", 2100, "0.0", [(1, "b", "0"), (2, "b", "0")]))
    return lines + records


def parse(lines):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    return chessfile


def rank_order(records):
    # The list of names as the reader leaves it. compute_tiebreaks() replaces
    # tournament["rankOrder"] with the parsed tie-break definitions once it runs, so the
    # names have to be read before that.
    return parse(buchholz_inverts_the_score(records)).get_tournament(1)["rankOrder"]


def ranks(records):
    """Rank every competitor by whatever tie-break list the file declared.

    params["tiebreak"] is empty, which is how a caller says "use the tournament's own
    list": compute_tiebreaks() then takes tournament["rankOrder"], which is what record
    202 or 212 put there. Competitors that cannot be separated share a rank, so two
    players tied at the top are both rank 1 and the next two are rank 3.
    """
    tournament = parse(buchholz_inverts_the_score(records)).get_tournament(1)
    params = {"tiebreak": [], "check": False, "unrated": None}
    engine = tiebreak.tiebreak(tournament, -1, params)
    result = engine.compute_tiebreaks(tournament, params)
    return {cmp["cid"]: cmp["rank"] for cmp in result["competitors"]}


def test_202_puts_the_points_in_front_of_the_list_it_reads():
    """"Used to break ties" means the points are already understood, so the reader adds them.

    The record names two tie-breaks and the parsed order has three entries, PTS first.
    Nothing in the file says PTS; it is the "PTS " the False flag prepends, and it is what
    makes the record mean "among competitors level on points, order by Buchholz, then by
    Sonneborn-Berger" rather than "order by Buchholz".
    """
    assert rank_order(["202 BH SB"]) == ["PTS", "BH", "SB"]


@pytest.mark.parametrize(
    "record, expected",
    [
        ("212 BH SB", ["BH", "SB"]),
        ("212 PTS BH SB", ["PTS", "BH", "SB"]),
    ],
    ids=["without-pts", "with-pts"],
)
def test_212_takes_the_list_exactly_as_written(record, expected):
    """"Used to define standings" is the whole ordering, so the reader adds nothing.

    Both halves are needed. The first shows that no PTS appears when the file does not
    write one -- which is the flag doing its work, not the reader failing to find a name.
    The second shows that a file which does write PTS gets one PTS and not two, so the
    reader is passing the list through rather than happening to agree with record 202.
    """
    assert rank_order([record]) == expected


def test_202_and_212_rank_the_same_tournament_in_opposite_orders():
    """The flag decides the standings, and here it decides them completely.

    The two records name the same tie-break over the same games. Under 202 the reader puts
    PTS first, so the two players on 2.0 finish ahead of the two on 0.0 and Buchholz only
    separates equals -- which here it cannot, both pairs being level on it too, so the
    ranks are 1, 1, 3, 3. Under 212 the list is Buchholz alone: the score is not consulted
    at all, and the two players who lost every game, having played the two who won every
    game, finish first on a Buchholz of 4.0 against 0.0.

    A complete inversion is the strongest available evidence that the flag is doing
    something and not merely decorating a list. It is also what a file writer risks by
    reaching for record 212 when they meant record 202.
    """
    assert ranks(["202 BH"]) == {1: 1, 2: 1, 3: 3, 4: 3}
    assert ranks(["212 BH"]) == {1: 3, 2: 3, 3: 1, 4: 1}


def test_202_names_the_tie_break_the_engine_then_computes():
    """The list is not just stored: each name becomes a computed column, in order.

    Two entries in the record, two numbers per competitor, in the order the record wrote
    them. The values are the ones derived in buchholz_inverts_the_score(): 2.0 points and
    0.0 Buchholz for the two who won everything, 0.0 points and 4.0 Buchholz for the two
    who lost everything. Asserting the values rather than the length is what distinguishes
    "the list reached the tie-break engine" from "the list reached the tie-break engine in
    the right order" -- reversed, this tournament would report 0.0 and 2.0.
    """
    tournament = parse(buchholz_inverts_the_score(["202 BH"])).get_tournament(1)
    params = {"tiebreak": [], "check": False, "unrated": None}
    result = tiebreak.tiebreak(tournament, -1, params).compute_tiebreaks(tournament, params)

    assert {cmp["cid"]: cmp["tiebreakScore"] for cmp in result["competitors"]} == {
        1: [decimal.Decimal("2.0"), decimal.Decimal("0.0")],
        2: [decimal.Decimal("2.0"), decimal.Decimal("0.0")],
        3: [decimal.Decimal("0.0"), decimal.Decimal("4.0")],
        4: [decimal.Decimal("0.0"), decimal.Decimal("4.0")],
    }


@pytest.mark.parametrize(
    "record, expected",
    [
        ("202 BH,SB", ["PTS", "BH", "SB"]),
        ("212 BH,SB", ["BH", "SB"]),
    ],
    ids=["202", "212"],
)
def test_a_comma_separates_two_names_the_way_a_space_does(record, expected):
    """Commas are accepted, because files in the wild write the list either way.

    parse_tiebreaks() replaces every comma with a space before splitting, so "BH,SB" is
    two names and not one name spelt oddly. Without that, the list would hold the single
    unknown name "BH,SB", which no tie-break answers to.
    """
    assert rank_order([record]) == expected


def test_a_202_record_that_names_pts_itself_gets_it_twice():
    """The reader prepends PTS without looking, so a file that writes it gets two.

    Record 202 is defined as the tie-breaks used to break a tie, so a file has no reason
    to name PTS in it -- but files do, and this is what happens: "PTS " goes on the front
    and the file's own PTS stays where it was. The second one is harmless in practice,
    since ordering by points twice orders by points, but it is a duplicated column in
    every published standings table.

    It is pinned rather than fixed because removing it is a decision about what the reader
    should do with a record that contradicts its own definition, and because a fix would
    have to choose between dropping the file's PTS and dropping the reader's -- which are
    the same result here and different results for a file that writes PTS second.
    """
    assert rank_order(["202 PTS BH"]) == ["PTS", "PTS", "BH"]


def test_two_spaces_between_two_names_leave_an_empty_name_between_them():
    """The split is on a single space, so a repeated separator produces an empty entry.

    line[4:] is split with .split(" ") rather than .split(), which means every run of n
    spaces yields n - 1 empty strings. A record lined up in columns, or one written with a
    stray double space, therefore hands the tie-break engine a name that is the empty
    string. The reader does not reject it and does not drop it.

    This is a fragility of the reader worth having on record: the empty name is not a
    tie-break, and it is carried into the rank order alongside the real ones. It is left
    as it is here rather than quietly changed to .split(), because that would also change
    what a leading or trailing space in an existing file produces.
    """
    assert rank_order(["202 BH  SB"]) == ["PTS", "BH", "", "SB"]


@pytest.mark.parametrize(
    "records",
    [
        ["202 BH", "212 SB"],
        ["212 SB", "202 BH"],
    ],
    ids=["202-first", "212-first"],
)
def test_212_wins_over_202_whichever_order_the_file_writes_them_in(records):
    """A file with both records keeps the 212 list, because of the reader's own order.

    parse_file() does not read the file top to bottom. It reads pass 1 into a dictionary
    keyed by record identifier and then walks self.trfrecords, which lists 202 before 212,
    so 212 is always parsed second and its assignment to tournament["rankOrder"] is the
    one that survives. Both records write the whole list, not a part of it, so the first
    one read is discarded entirely -- the "BH" of the 202 record does not appear.

    Pinning both file orders is the point of the test. A reader that happened to process
    the file in the order it was written would agree with this test in one case and
    disagree in the other, and a file with contradictory records would then be scored
    differently depending on which line its author typed first.
    """
    assert rank_order(records) == ["SB"]
