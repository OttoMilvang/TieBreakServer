# -*- coding: utf-8 -*-
"""Team PTS follows the primary score declared by TRF record 192."""
from decimal import Decimal

import pytest

import tiebreak


def team_tournament(primary):
    game = {
        "W": Decimal("1.0"), "D": Decimal("0.5"), "L": Decimal("0.0"),
        "F": "W", "H": "D", "Z": Decimal("0.0"), "P": "W", "A": "D", "U": "Z",
    }
    match = {
        "W": Decimal("2.0"), "D": Decimal("1.0"), "L": Decimal("0.0"),
        "F": "W", "H": "D", "Z": Decimal("0.0"), "P": "D", "A": "D", "U": "Z",
        "FG": "W*", "HG": "D*", "ZG": "Z*", "PG": "P*",
    }
    return {
        "teamTournament": True,
        "teamSize": 2,
        "tournamentType": "SWISS",
        "numRounds": 0,
        "competitors": [],
        "gameList": [],
        "matchList": [],
        "scoreSystem": {"game": game, "match": match, "primary": primary},
        "accelerated": {"firstRound": 0, "lastRound": 0, "values": []},
    }


@pytest.mark.parametrize(
    "primary, expected",
    [(None, "mpoints"), ("match", "mpoints"), ("game", "gpoints")],
)
def test_pts_uses_the_declared_team_primary_score(primary, expected):
    params = {"tiebreak": [], "check": False, "unrated": None}
    calculator = tiebreak.tiebreak(team_tournament(primary), -1, params)

    assert calculator.parse_tiebreak(1, "PTS")["pointtype"] == expected
