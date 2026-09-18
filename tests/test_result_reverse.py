# -*- coding: utf-8 -*-
"""
The reverse table of chessjson gives the result of the other side of a game.

A game record can carry any letter of the score system, and a JSON event may use any
of them, so every letter of default_score needs an entry. A letter added to the score
system later then fails here and not as a KeyError inside a tie-break.
"""
from gacrux import trf2json


def test_reverse_is_defined_for_every_result_letter():
    reader = trf2json.trf2json()

    assert set(reader.default_score["game"]) <= set(reader.reverse)
    # FG, HG, ZG and PG are game points for an unplayed match, not result letters.
    assert set(reader.default_score["match"]) - {"FG", "HG", "ZG", "PG"} <= set(reader.reverse)

    # The opponent of a forfeit win forfeited, as "Z" -> "W" the other way round.
    assert reader.reverse["F"] == "Z"
    # A half-point bye is half a point unplayed on both sides.
    assert reader.reverse["H"] == "H"
    # A pairing-allocated bye has no opponent. One named anyway played nothing.
    assert reader.reverse["P"] == "Z"
