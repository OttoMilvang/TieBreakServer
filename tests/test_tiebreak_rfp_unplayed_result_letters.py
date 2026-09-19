# -*- coding: utf-8 -*-
"""
compute_rfp (tiebreak code "RFP", registered-for-round) raised KeyError on an
ordinary, valid result letter it had simply never enumerated.

Its two lookup tables translate an unplayed game's scoreSystem result letter --
W, D, L, F, H, Z, P, A or U, the full vocabulary scoresystem.py's default_score
defines, and the same one record 299 (Abnormal Assignment) writes directly onto
a game (see test_tiebreak_abnormal_points.py) -- into a display code for the
pairing list. Both tables only ever named a subset of that vocabulary, and both
used a bare subscript, so a competitor whose game that round recorded a letter
neither table names raised KeyError out of the middle of the tie-break
computation instead of being scored.

compute_score, a few lines above compute_rfp in the same file, already has to
solve exactly this problem (translate a result letter, or leave it alone if the
table does not name it) and does it with a lookup-with-fallback (its `trans`
dict). This pins compute_rfp taking the same fallback, for both of its tables --
confirmed against the pre-fix tree to actually raise for the case below, in the
table used when the game recorded an opponent. The sibling table (no opponent
recorded -- the ordinary bye case) has the identical structural gap and the fix
covers it the same way, but a minimal file exercising *that* branch specifically
with an un-enumerated letter was not found, so it is fixed defensively rather
than pinned by a second test here.
"""
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


def compute_rfp(lines):
    chessfile = trf2json.trf2json()
    chessfile.parse_file("\n".join(lines), True)
    tournament = chessfile.get_tournament(1)
    params = {"tiebreak": ["RFP"], "check": False, "unrated": None,
              "pre_determined": True, "swiss": False}
    engine = tiebreak.tiebreak(tournament, -1, params)
    result = engine.compute_tiebreaks(tournament, params)
    return dict([(cmp["cid"], cmp["tiebreakScore"][0]) for cmp in result["competitors"]])


def test_record_299_writing_h_onto_a_game_with_an_opponent_does_not_crash_rfp():
    """Record 299 (res != blank, a round and pairing numbers given) overwrites an
    *existing* game's result -- see parse_trf_abnormal -- so "H" (half-point bye)
    can reach compute_rfp's opponent-present branch on a player who has a real
    opponent recorded that round but did not play them. Confirmed to raise
    KeyError: 'H' on the pre-fix tree.
    """
    lines = [
        "012 record 299 writes H onto a game with a recorded opponent",
        "062 2",
        "072 1",
        "142 3",
        "152 W",
        player_line(1, "Player One", 2000, "0.5", [(2, "w", "-")]),
        player_line(2, "Player Two", 1900, "0.5", [(1, "b", "-")]),
        "299 H         0.5    1    1",
    ]

    scores = compute_rfp(lines)

    assert set(scores) == {1, 2}
