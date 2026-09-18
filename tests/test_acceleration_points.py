# -*- coding: utf-8 -*-
"""Regression tests for the point-valued acceleration representation."""
from decimal import Decimal

from gacrux import chessjson
from gacrux import ts2json
from gacrux.tiebreak import tiebreak
from gacrux.tournamentgenerator import tournamentgenerator


def test_ts2json_acceleration_uses_points():
    reader = ts2json.ts2json()
    tournament = {
        "numRounds": 9,
        "scoreSystem": {
            "match": {"W": Decimal("3.0"), "D": Decimal("1.0")},
            "game": {"W": Decimal("1.0"), "D": Decimal("0.5")},
        },
        "accelerated": {"name": "BAKU2016", "bakuGa": 20, "values": []},
    }

    reader.add_accelerated(tournament)

    assert tournament["accelerated"]["values"][0] == {
        "matchPoints": Decimal("3.0"),
        "gamePoints": Decimal("1.0"),
        "firstRound": 1,
        "lastRound": 3,
        "firstCompetitor": 1,
        "lastCompetitor": 20,
    }


def test_do_pairing_stores_acceleration_as_points(monkeypatch):
    runner = tournamentgenerator()
    runner.params = {
        "number_of_rounds": 9,
        "current_round": 0,
        "maxmeets": 0,
        "method": ["dutch"],
        "experimental": [],
    }
    runner.method["dutch"] = lambda tournament, rnd, params: None
    monkeypatch.setattr(runner, "compute_pairing", lambda engine, params: {"checker": []})
    monkeypatch.setattr(runner.statistics, "has_bye", lambda: "")
    tournament = chessjson.chessjson().add_tournament(1, False, 9)
    tournament["accelerated"] = {"name": "BAKU2016", "values": []}
    tournament["competitors"] = [
        {"cid": cid, "present": True, "gamePoints": Decimal("0.0")}
        for cid in range(1, 5)
    ]

    runner.do_pairing(chessjson.chessjson(), tournament, 1)

    assert tournament["accelerated"]["values"][0]["matchPoints"] == Decimal("2.0")
    assert tournament["accelerated"]["values"][0]["gamePoints"] == Decimal("1.0")
    assert "matchResult" not in tournament["accelerated"]["values"][0]


def test_team_secondary_acceleration_uses_game_points():
    """ACC/X uses the point value belonging to the exchanged score.

    With match points primary and game points secondary, ACC/X reaches
    ``get_accelerated`` as ``gpoints_``. That prefix must select the one virtual game
    point, not the two virtual match points.
    """
    engine = object.__new__(tiebreak)
    engine.accelerated = {
        "values": [
            {
                "matchPoints": Decimal("2.0"),
                "gamePoints": Decimal("1.0"),
                "firstRound": 1,
                "lastRound": 3,
                "firstCompetitor": 1,
                "lastCompetitor": 2,
            }
        ]
    }

    assert engine.get_accelerated("mpoints_", 1, 1) == Decimal("2.0")
    assert engine.get_accelerated("gpoints_", 1, 1) == Decimal("1.0")
    assert engine.get_accelerated("points_", 1, 1) == Decimal("1.0")
