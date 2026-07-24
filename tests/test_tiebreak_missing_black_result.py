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

import errors
import tiebreak
import trf2json


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
    # "bResult" not in result, so nothing crashes until tie-breaks are computed.
    round_two = next(g for g in tournament["gameList"] if g["round"] == 2)
    assert "bResult" not in round_two

    params = {"tiebreak": ["PTS"], "check": False, "unrated": None}
    with pytest.raises(errors.GacruxInputError) as excinfo:
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
