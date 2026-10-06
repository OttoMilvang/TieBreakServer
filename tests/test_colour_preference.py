# -*- coding: utf-8 -*-
"""
C.04.3 art. 1.7.1, the absolute colour preference.

    "An absolute colour preference occurs when a player's colour difference is greater than
     +1 or less than -1, or when a player had the same colour in the two latest rounds they
     played. The preference is for White when the colour difference is less than -1 or when
     the last two games were played with Black. The preference is for Black when the colour
     difference is greater than +1, or when the last two games were played with White."

The second clause of each sentence -- "when the last two games were played with Black" -- is
unconditional on the colour difference. Gating it at cod <= 0 (resp. cod >= 0) dropped the
|cod| == 1 cases, which then fell through to art. 1.7.2 and came back as a STRONG preference
for the OPPOSITE colour. That is what these tests hold the engine to.

There is one place where art. 1.7.1 asserts BOTH preferences at once -- a colour difference of
+2 or more together with two Blacks in the last two played rounds -- and the article does not
say which sentence wins. The engine resolves those by the colour difference. TestArticleConflict
pins that choice so it cannot drift silently, and does not claim it is the only reading.
"""
import pytest

from gacrux import trf2json
from gacrux.crosstabledutch import crosstable_dutch
from gacrux.pairingdutch import pairing_dutch

PAB = (0, "-", "U")  # pairing-allocated bye
HPB = (0, "-", "H")  # half-point bye
ZPB = (0, "-", "Z")  # zero-point bye


def preference(csq):
    """The engine's colour preference for a player whose played colours were *csq*."""
    cod = csq.count("w") - csq.count("b")
    return crosstable_dutch.color_preference(None, cod, csq)


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


def pair_round(lines, rnd):
    """Pair round *rnd* of the tournament in *lines*; return the engine and its brackets."""
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"}
    engine = pairing_dutch(tournament, rnd, params)
    return engine, engine.compute_pairing(False, 0)


def pair_of(brackets, startno):
    """The pair *startno* plays in, as the engine reports it ("w" and "b" keys)."""
    for bracket in brackets:
        for pair in bracket.get("pairs", []):
            if startno in (pair["w"], pair["b"]):
                return pair
    raise AssertionError("%d was not paired" % startno)


class TestTheLastTwoGamesClauseIsUnconditional:
    """art. 1.7.1, second clause: the cases a colour-difference gate used to drop."""

    def test_two_blacks_with_colour_difference_plus_one_is_absolute_white(self):
        # wwwbb: cod = +1, so "greater than +1" does NOT fire and the Black sentence is silent.
        # Only "the last two games were played with Black" applies -> absolute White.
        # Returned "b1" (a STRONG preference for BLACK -- the opposite colour) before the fix.
        assert preference("wwwbb") == "w2"

    def test_two_whites_with_colour_difference_minus_one_is_absolute_black(self):
        # bbbww: the mirror. cod = -1, so "less than -1" does not fire.
        assert preference("bbbww") == "b2"

    def test_two_blacks_with_a_balanced_colour_difference_is_absolute_white(self):
        assert preference("wwbb") == "w2"

    def test_two_whites_with_a_balanced_colour_difference_is_absolute_black(self):
        assert preference("bbww") == "b2"

    def test_two_blacks_with_colour_difference_minus_one_is_absolute_white(self):
        # Both sentences agree here; it is the case the old gate did handle.
        assert preference("wbbb") == "w2"


class TestTheColourDifferenceClauseIsUnaffected:
    """art. 1.7.1, first clause -- and arts. 1.7.2 to 1.7.4, which must not move."""

    @pytest.mark.parametrize("csq", ["wwwb", "wwwwbb"[:4]])
    def test_a_colour_difference_above_plus_one_is_absolute_black(self, csq):
        assert preference(csq) == "b2"

    def test_a_colour_difference_below_minus_one_is_absolute_white(self):
        assert preference("bbbw") == "w2"

    def test_a_colour_difference_of_plus_one_alone_is_a_strong_black_preference(self):
        # art. 1.7.2. wbw: cod = +1, last two are "bw" -- not the same colour, so 1.7.1 is silent.
        assert preference("wbw") == "b1"

    def test_a_colour_difference_of_minus_one_alone_is_a_strong_white_preference(self):
        assert preference("bwb") == "w1"

    def test_a_balanced_player_alternates(self):
        # art. 1.7.3, the mild preference.
        assert preference("wb") == "w0"
        assert preference("bw") == "b0"

    def test_a_player_who_has_not_played_has_no_preference(self):
        # art. 1.7.4.
        assert preference("") == "nc"


class TestArticleConflict:
    """art. 1.7.1 asserts both preferences at once here; the engine picks the colour difference.

    "The preference is for Black when the colour difference is greater than +1" AND "The
    preference is for White ... when the last two games were played with Black" both hold for
    a player on wwwwbb (cod = +2, last two Black). The article does not rank its own sentences.
    These tests pin the engine's choice -- the colour difference -- so that it is a decision on
    the record rather than an accident, and so a change to it cannot pass unnoticed.
    """

    def test_two_blacks_cannot_overturn_a_colour_difference_of_plus_two(self):
        assert preference("wwwwbb") == "b2"

    def test_two_whites_cannot_overturn_a_colour_difference_of_minus_two(self):
        assert preference("bbbbww") == "w2"


def a_player_who_has_not_played_level_with_one_due_white():
    # Player 1 takes a half-point bye in each of the first four rounds, so he is on 2.0
    # and has played no game: by C.04.3 art. 1.7.4 he has no colour preference. Players
    # 2 to 8 play the four rounds with one pairing-allocated bye a round. Player 8 is the
    # only one of them on 2.0, with Black, White, White, Black: colour difference 0 and
    # Black last, a mild preference for White (art. 1.7.3).
    schedule = [
        [(4, 8, "=", "="), (3, 7, "1", "0"), (6, 5, "=", "=")],   # 2 has the bye
        [(4, 6, "=", "="), (8, 3, "1", "0"), (7, 2, "0", "1")],   # 5 has the bye
        [(4, 2, "0", "1"), (5, 7, "1", "0"), (8, 6, "0", "1")],   # 3 has the bye
        [(2, 5, "0", "1"), (3, 4, "=", "="), (7, 8, "=", "=")],   # 6 has the bye
    ]
    byes = [2, 5, 3, 6]
    value = {"1": 1.0, "=": 0.5, "0": 0.0}
    games = {startno: [] for startno in range(1, 9)}
    points = {startno: 0.0 for startno in range(1, 9)}
    for rnd, pairs in enumerate(schedule):
        for white, black, rw, rb in pairs:
            games[white].append((black, "w", rw))
            games[black].append((white, "b", rb))
            points[white] += value[rw]
            points[black] += value[rb]
        games[byes[rnd]].append(PAB)
        points[byes[rnd]] += 1.0
        games[1].append(HPB)
        points[1] += 0.5
    lines = ["012 A player who has not played yet", "042 2026-03-01", "XXR 7"]
    for startno in range(1, 9):
        lines.append(player_line(startno, "P%d, X" % startno, 2400 - 10 * startno,
                                 "%.1f" % points[startno], games[startno]))
    return lines


def test_art_1_7_4_the_opponent_of_a_player_with_no_preference_is_granted_theirs():
    """art. 1.7.4: "Players who did not play any games have no colour preference (the
    preference of their opponents is granted)."

    In round 5 players 1 and 8, both on 2.0, are paired. Player 8 has a mild preference
    for White. Player 1 is the higher ranked, so with a preference for White of his own he
    would get White (art. 5.2.2, or 5.2.4 if both were mild). He has played no game, so
    he has none, and player 8's preference is granted.
    """
    engine, brackets = pair_round(a_player_who_has_not_played_level_with_one_due_white(), 5)

    assert engine.competitors[1]["cop"] == "nc"
    assert engine.competitors[8]["cop"] == "w0"
    pair = pair_of(brackets, 1)
    assert (pair["w"], pair["b"]) == (8, 1)


def eight_players_with_a_forfeit_and_a_bye():
    # Eight players, four rounds. Player 1 wins over the board in round 1 (White), is
    # awarded a forfeit win in round 2 (recorded with White, "+"), takes a half-point bye
    # in round 3 and wins over the board in round 4 (White). Player 6 loses over the board
    # in round 1 (Black), forfeits round 2 (recorded with Black, "-"), then plays rounds 3
    # (White) and 4 (Black). Player 8 is absent in round 3 so the field stays even.
    schedule = [
        [(1, 5, "1", "0"), (2, 6, "1", "0"), (3, 7, "=", "="), (4, 8, "0", "1")],
        [(1, 6, "+", "-"), (5, 2, "1", "0"), (7, 4, "=", "="), (3, 8, "1", "0")],
        [(2, 3, "1", "0"), (4, 5, "=", "="), (6, 7, "0", "1")],
        [(1, 8, "1", "0"), (2, 4, "1", "0"), (3, 6, "=", "="), (5, 7, "1", "0")],
    ]
    value = {"1": 1.0, "=": 0.5, "0": 0.0, "+": 1.0, "-": 0.0}
    games = {startno: [] for startno in range(1, 9)}
    points = {startno: 0.0 for startno in range(1, 9)}
    for pairs in schedule:
        seated = set()
        for white, black, rw, rb in pairs:
            games[white].append((black, "w", rw))
            games[black].append((white, "b", rb))
            points[white] += value[rw]
            points[black] += value[rb]
            seated |= {white, black}
        for startno in range(1, 9):
            if startno not in seated:
                games[startno].append(HPB if startno == 1 else ZPB)
                points[startno] += 0.5 if startno == 1 else 0.0
    lines = ["012 Only played games count", "042 2026-03-01", "XXR 7"]
    for startno in range(1, 9):
        lines.append(player_line(startno, "P%d, X" % startno, 2400 - 10 * startno,
                                 "%.1f" % points[startno], games[startno]))
    return lines


def test_art_3_4_only_played_games_count_in_the_colour_history():
    """C.04.2 art. 3.4: "Only played games or matches count in situations where the
    colour sequence is meaningful. So, for instance, a participant with a colour history
    of BWBuW ('u' for unplayed, i.e. no valid game or match in round-4) will be treated
    as if their colour history was uBWBW."

    The guard is tiebreak.compute_score's "comp['played'] and comp['opponent'] > 0"
    before anything is added to COD or CSQ. The forfeit win and the bye of player 1 are
    unplayed rounds even though the forfeit carries a colour in the file, so his history
    is WuuW, read as uuWW: colour difference +2, sequence "ww", absolute Black. Had the
    forfeit counted he would be on +3 and "www". Player 6 is the sharper case: with his
    forfeit loss counted his colour difference would be -2 and his preference ABSOLUTE
    White; without it he is on -1 with a history "bwb", a STRONG preference for White.

    The crosstable prefixes the sequence with one space for the round before the first.
    This is green today; it pins the guard so it cannot be lost.
    """
    engine, _ = pair_round(eight_players_with_a_forfeit_and_a_bye(), 5)

    assert (engine.competitors[1]["cod"], engine.competitors[1]["csq"],
            engine.competitors[1]["cop"]) == (2, " ww", "b2")
    assert (engine.competitors[6]["cod"], engine.competitors[6]["csq"],
            engine.competitors[6]["cop"]) == (-1, " bwb", "w1")
