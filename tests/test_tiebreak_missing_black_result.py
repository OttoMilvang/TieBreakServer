# -*- coding: utf-8 -*-
"""
Regression test for tiebreak.prepare_result() on a game with no black result at all.

prepare_result() already guarded the case where a real black player (black > 0) has
no "bResult" key -- but reported it by calling ``self.chessevent.put_status(451, err)``
followed by a bare ``raise``. tiebreak has no ``chessevent`` attribute (that belongs to
chessjson), so the put_status() call itself raised AttributeError before the intended
message was ever produced; and even if it had reached the bare ``raise``, that raises
"RuntimeError: No active exception to reraise" outside an except block. Either way the
diagnostic describing what was actually wrong with the input was destroyed.

Reached through the public entry point: constructing tiebreak.tiebreak() on a
non-team tournament calls prepare_competitors() -> prepare_result() for every game in
gameList, so a tournament with an incomplete game record crashes the moment tie-breaks
are computed for it, not from poking prepare_result() directly.
"""
import pytest

from gacrux import gacruxexeptions
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


def missing_black_result_round_two():
    # Player 2's row ends after round 1, as if they withdrew. Player 1's row
    # continues into round 2, playing white against player 2 -- who has no round-2
    # entry at all. Only one side of that round-2 game is ever recorded: white=1,
    # black=2, wResult set, no bResult.
    lines = ["012 Missing black result test", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2000, "2.0", [(2, "w", "1"), (2, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, "0.0", [(1, "b", "0")]))
    return lines


def build_tournament():
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(missing_black_result_round_two()), True)
    return chessfile.get_tournament(1)


def test_computing_tiebreaks_reports_the_missing_result_cleanly():
    tournament = build_tournament()
    # trf2json itself parses this fine -- get_score("black") is never called because
    # "black" "result" not in result, so nothing crashes until tie-breaks are computed.
    round_two = next(g for g in tournament["gameList"] if g["round"] == 2)
    assert "black" in round_two and "result" not in round_two["black"]

    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    with pytest.raises(gacruxexeptions.GacruxInputError) as excinfo:
        tiebreak.tiebreak(tournament, -1, params)

    # Not AttributeError ("'tiebreak' object has no attribute 'chessevent'") and not
    # "RuntimeError: No active exception to reraise" -- a message that actually
    # describes the malformed record.
    assert "No active exception" not in str(excinfo.value)
    assert "chessevent" not in str(excinfo.value)
    assert "black" in str(excinfo.value)
    assert "round 2" in str(excinfo.value)


def test_a_complete_game_record_still_computes_tiebreaks():
    lines = ["012 Complete game, control", "042 2026-03-01", "XXR 1"]
    lines.append(player_line(1, "One, Player", 2000, "1.0", [(2, "w", "1")]))
    lines.append(player_line(2, "Two, Player", 1900, "0.0", [(1, "b", "0")]))
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)

    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    tb = tiebreak.tiebreak(tournament, -1, params)
    result = tb.compute_tiebreaks(tournament, params)
    scores = {cmp["cid"]: cmp["tiebreakScore"] for cmp in result["competitors"]}
    assert scores[1][0] == 1
    assert scores[2][0] == 0


def bresult_only_round_two():
    """The mirror of missing_black_result_round_two(): player 1 withdraws instead.

    Player 1's row ends after round 1. Player 2's row runs on into round 2, playing
    Black against player 1 -- who has no round-2 entry of their own. The resulting
    round-2 record carries a result for Black and none at all for White.

    Black LOSES that round 2, which is what makes the case measurable: White's half is
    then worth a win, a point that has to be derived from Black's letter. Had Black won
    it, White's half would be a loss and worth the same nothing as no result at all, and
    the test could not tell the two apart.
    """
    lines = ["012 One-sided result test", "042 2026-03-01", "XXR 2"]
    lines.append(player_line(1, "One, Player", 2000, "0.0", [(2, "w", "0")]))
    lines.append(player_line(2, "Two, Player", 1900, "1.0", [(1, "b", "1"), (1, "b", "0")]))
    return lines


def test_pts_handles_a_record_with_no_white_result():
    """PTS must complete, and be right, on a game recorded only from Black's side.

    The GacruxInputError guard above cannot help here: it tests for a missing result on
    Black, and here Black's is the half that is present. White's score has to come from
    reversing Black's result, and a tie-break engine that read the absent side as the
    letter "Z" would score the round for nobody.

    The points are derived, not read from the "001" totals: prepare_result() builds each
    competitor's per-round record from the game list, so player 1's round-2 score comes
    from the reversal.

      round 1: 2 (Black) beats 1   -> 1 scores 0.0, 2 scores 1.0
      round 2: 2 (Black) loses to 1 -> recorded for Black only; White's half is the
                                      reverse of "L", a win, 1.0
      totals:  player 1 = 1.0, player 2 = 1.0

    Player 1's own "001" record declares 0.0, the one game his row carries, so the point
    in his PTS can only have come from the game the other row describes.
    """
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(bresult_only_round_two()), True)
    tournament = chessfile.get_tournament(1)

    round_two = next(g for g in tournament["gameList"] if g["round"] == 2)
    assert round_two["black"]["result"] == "L"
    assert "result" not in round_two["white"]

    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    tb = tiebreak.tiebreak(tournament, -1, params)
    result = tb.compute_tiebreaks(tournament, params)

    scores = {cmp["cid"]: cmp["tiebreakScore"] for cmp in result["competitors"]}
    ranks = {cmp["cid"]: cmp["rank"] for cmp in result["competitors"]}
    # The standings are complete: every competitor got a score and a rank.
    assert sorted(scores) == [1, 2]
    assert scores[1][0] == 1
    assert scores[2][0] == 1
    assert sorted(ranks.values()) == [1, 1]


def test_the_two_one_sided_records_are_treated_differently_on_purpose():
    """This pins an asymmetry, so that it is on the record rather than accidental.

    A record with no result for White is recovered by reversing Black's, above. A record
    with no result for Black is refused by the GacruxInputError guard in
    prepare_result(), because the competitor entry for Black is built from that result
    further down. Both records come from the same cause -- a withdrawn player leaving
    half a game behind -- so which one the engine accepts depends only on the colour the
    withdrawing player had.

    If the asymmetry is resolved in favour of recovering both halves, this is the test to
    change, and the assertion above says what a reader would be giving up.
    """
    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    with pytest.raises(gacruxexeptions.GacruxInputError):
        tiebreak.tiebreak(build_tournament(), -1, params)
