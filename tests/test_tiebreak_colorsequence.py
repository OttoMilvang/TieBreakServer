# -*- coding: utf-8 -*-
"""
Regression tests for the colour tie-breaks COD / COP / CSQ.

A competitor who gets the same colour in every game accumulates a colour difference
outside the range of the colour-preference table tiebreak.compute_score() keeps for
team tournaments. That must not crash the score preparation. For an individual
tournament the listed COP is the colour preference of C.04.3 art. 1.7 exactly as the
pairing engine computes it (colourpreference.color_preference), and the last two tests
hold the listing to that.
"""
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


def compute(lines, tiebreaks):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": tiebreaks, "check": False, "unrated": None}
    tb = tiebreak.tiebreak(tournament, -1, params)
    result = tb.compute_tiebreaks(tournament, params)
    return dict([(cmp["cid"], cmp["tiebreakScore"]) for cmp in result["competitors"]])


def one_colour_all_the_way(rounds):
    # Player 1 is white against player 2 in every round, player 3 is white against
    # player 4 in every round. 1 and 3 end on +rounds, 2 and 4 on -rounds.
    lines = ["012 Same colour every round", "042 2026-03-01", "XXR %d" % rounds]
    lines.append(player_line(1, "One, Player", 2000, "%.1f" % rounds, [(2, "w", "1")] * rounds))
    lines.append(player_line(2, "Two, Player", 1900, "0.0", [(1, "b", "0")] * rounds))
    lines.append(player_line(3, "Three, Player", 1800, "%.1f" % rounds, [(4, "w", "1")] * rounds))
    lines.append(player_line(4, "Four, Player", 1700, "0.0", [(3, "b", "0")] * rounds))
    return lines


@pytest.mark.parametrize("rounds", [9, 10, 15])
def test_same_colour_in_every_game(rounds):
    """COD, COP and CSQ all stay well defined when every game had the same colour.

    COD is the colour difference (white games minus black games) and CSQ the colour
    sequence; both are well defined however lopsided the colours are. COP is derived
    from COD and must saturate rather than run off the end of its table.

    The COP assertions name the exact value rather than merely checking that the first
    character is a colour. A weaker check ("scores[1][1][0] in 'wb'") accepts the
    *inverted* answer -- it passes just as happily when a player who has had nothing but
    White is told to prefer White again -- so it cannot hold the saturation direction.
    A player on nothing but White has an absolute preference for Black ("b2"), and the
    all-Black player the mirror ("w2"); see
    test_long_colour_sequence_saturates_in_correct_direction for the table derivation.
    """
    scores = compute(one_colour_all_the_way(rounds), ["COD", "COP", "CSQ"])

    assert scores[1][0] == rounds
    assert scores[2][0] == -rounds
    assert scores[1][2] == "w" * rounds
    assert scores[2][2] == "b" * rounds
    assert scores[1][1] == "b2"
    assert scores[2][1] == "w2"


@pytest.mark.parametrize("rounds", [5, 6, 9, 10, 15])
def test_long_colour_sequence_saturates_in_correct_direction(rounds):
    """A saturated colour preference must point AWAY from the colour already had.

    For an individual tournament COP is now colourpreference.color_preference, whose
    colour-difference branch ("greater than +1" / "less than -1", art. 1.7.1) saturates
    by construction, so a run of one colour cannot point the wrong way however long it
    is. This test keeps holding that direction. The account below is of the lookup
    table the listing used to read for everybody and still reads for team tournaments,
    where the clamp it describes is what stops the table inverting.

    That table is a nine-character string built in tiebreak.compute_score():

        colpref = other[ocol] + "bbbbwwww"

    indexed by the running colour difference ``pf`` (white games minus black games).
    For a competitor whose last game was White (``ocol == "w"``,
    ``other[ocol] == "b"``) the table is

        index:   0    1    2    3    4     5    6    7    8
                                                (also -4  -3   -2   -1)
        letter: "b"  "b"  "b"  "b"  "b"   "w"  "w"  "w"  "w"

    Index 0 is the "alternate" entry -- the opposite of the colour just played.
    Indices +1..+4 are the four ``b`` characters, reached by a competitor who has had
    more White than Black, and who is therefore due Black. Indices -1..-4 are the same
    four ``w`` characters counted from the END of the string (positions 8, 7, 6, 5),
    reached by one who has had more Black than White and is due White. The table is
    therefore a map for ``pf`` in [-4, +4] and for nothing else.

    Beyond that range the two halves collide. ``pf = +5`` on a competitor who has had
    five Whites indexes position 5 -- the FIRST character of the negative half -- and
    yields "w": an absolute preference for White for a competitor who has had nothing
    but White. ``pf = -5`` wraps to position 4, the last character of the positive
    half, and yields "b" for the all-Black one. Clamping to the length of the string
    ([-9, +8]) lands inside the opposite half rather than on its own end, so it does
    not rescue this; the clamp has to be to the range the table is a map for, [-4, +4].

    5 and 6 rounds catch the positive-half collision on both competitors. 9, 10 and 15
    rounds catch it on the all-White one, where a length-based clamp masks it for the
    all-Black one by accident: -9 and below saturate onto index 0, which happens to be
    "w" for a competitor whose last game was Black.

    The value is the full COP string, not just its colour, so that an inverted answer
    cannot pass. The trailing "2" is the absolute-preference strength of C.04.3 art.
    1.7.1: from round 2 on, this competitor's last two games were the same colour.
    """
    scores = compute(one_colour_all_the_way(rounds), ["COD", "COP"])

    # Player 1 had White in every round: colour difference +rounds, due Black.
    assert scores[1][0] == rounds
    assert scores[1][1] == "b2"
    # Player 2 had Black in every round: colour difference -rounds, due White.
    assert scores[2][0] == -rounds
    assert scores[2][1] == "w2"


def test_normal_colours_are_unchanged():
    # Colour differences inside the table must keep the values they always had.
    lines = ["012 Normal colours", "042 2026-03-01", "XXR 3"]
    lines.append(player_line(1, "One, Player", 2000, "2.0", [(2, "w", "1"), (3, "b", "0"), (4, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, "1.0", [(1, "b", "0"), (4, "w", "1"), (3, "b", "0")]))
    lines.append(player_line(3, "Three, Player", 1800, "2.0", [(4, "w", "0"), (1, "w", "1"), (2, "w", "1")]))
    lines.append(player_line(4, "Four, Player", 1700, "1.0", [(3, "b", "1"), (2, "b", "0"), (1, "b", "0")]))
    scores = compute(lines, ["COD", "COP", "CSQ"])

    assert scores[1] == [1, "b1", "wbw"]
    assert scores[2] == [-1, "w1", "bwb"]
    assert scores[3] == [3, "b2", "www"]
    assert scores[4] == [-3, "w2", "bbb"]


def all_draws_with_player_1_on(csq):
    # Six players, one round per character of csq, every game drawn. Player 1 meets
    # player 2 every round and has the colours csq spells out; player 2 has the mirror.
    # Players 3 to 6 alternate colours against each other and never carry a preference
    # that matters here. Nothing pairs this tournament, so the repeated opponents are
    # harmless: the point is what the listing says about player 1's colour history.
    rounds = len(csq)
    other = {"w": "b", "b": "w"}
    lines = ["012 Colour history %s" % csq, "042 2026-03-01", "XXR %d" % rounds]
    half = "%.1f" % (rounds / 2.0)
    lines.append(player_line(1, "One, Player", 2000, half, [(2, c, "=") for c in csq]))
    lines.append(player_line(2, "Two, Player", 1900, half, [(1, other[c], "=") for c in csq]))
    alternating = ["w" if rnd % 2 == 0 else "b" for rnd in range(rounds)]
    lines.append(player_line(3, "Three, Player", 1800, half, [(4, c, "=") for c in alternating]))
    lines.append(player_line(4, "Four, Player", 1700, half, [(3, other[c], "=") for c in alternating]))
    lines.append(player_line(5, "Five, Player", 1600, half, [(6, c, "=") for c in alternating]))
    lines.append(player_line(6, "Six, Player", 1500, half, [(5, other[c], "=") for c in alternating]))
    return lines


def test_art_1_7_1_two_blacks_at_colour_difference_plus_one_list_as_absolute_white():
    """The listed COP is the colour preference of C.04.3 art. 1.7, as the engine reads it.

    A player on wwwbb has a colour difference of +1 and had Black in the two latest
    rounds. Art. 1.7.1: "The preference is for White when the colour difference is less
    than -1 or when the last two games were played with Black" -- the second clause is
    unconditional on the colour difference, so this is an ABSOLUTE preference for White,
    "w2", and it is what crosstable_dutch.color_preference gives the pairing engine.

    The listing computed its own answer from the colour difference alone and reported
    "b2": the opposite colour. A tie-break listing that contradicts the pairing engine
    about the same player is wrong in one of the two places, and the engine is the one
    that was held to the article.
    """
    scores = compute(all_draws_with_player_1_on("wwwbb"), ["COD", "COP", "CSQ"])

    assert scores[1] == [1, "w2", "wwwbb"]


@pytest.mark.parametrize("csq", ["wwwbb", "bbbww", "wwbb", "wbw", "wwwwb"])
def test_the_listed_colour_preference_is_the_engines(csq):
    """COP as listed equals crosstable_dutch.color_preference for the same history.

    One implementation, not two that can drift: the listing used to keep a lookup table
    of its own that read the strength off the last two colours rather than off art. 1.7,
    so besides the +/-1 cases it also emitted strengths the article does not define
    ("b3" for wwwwb). The histories here cover an absolute preference by the last two
    games at a colour difference of +1 and -1 (art. 1.7.1), one at a difference of zero,
    a strong preference (art. 1.7.2), and a history whose old listing was "b3".
    """
    from gacrux.crosstabledutch import crosstable_dutch

    cod = csq.count("w") - csq.count("b")
    scores = compute(all_draws_with_player_1_on(csq), ["COD", "COP", "CSQ"])

    assert scores[1] == [cod, crosstable_dutch.color_preference(None, cod, csq), csq]
