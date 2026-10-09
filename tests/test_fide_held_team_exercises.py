# -*- coding: utf-8 -*-
"""Worked team examples 34-49 from Mario Held's FIDE C.07 exercise paper.

Source: IA Mario Held, *Exercises in Tie-Breaking*, Rev. 2403220900 /
C.07-2023, pp. 52-69.  The compact crosstable below is transcribed from page
6.  It is expanded into the same competitor/match/game structure produced by
the TRF reader, including the board results needed by exercises 46-48.
"""
from decimal import Decimal

import pytest

from gacrux import tiebreak


GAME_SCORE = {
    "W": Decimal("1"), "D": Decimal("0.5"), "L": Decimal("0"),
    "F": "W", "H": "D", "Z": Decimal("0"), "P": "W", "A": "D", "U": "Z",
}
MATCH_SCORE = {
    "W": Decimal("2"), "D": Decimal("1"), "L": Decimal("0"),
    "F": "W", "H": "D", "Z": Decimal("0"), "P": "D", "A": "D", "U": "Z",
    "FG": "W*", "HG": "D*", "ZG": "Z*", "PG": "D*",
}
REVERSE = {"W": "L", "D": "D", "L": "W"}

# opponent, team colour and game points; the five symbolic entries are unplayed matches.
TEAM_ROWS = {
    1: ["8w2.5", "4b1.5", "7w3", "2b2.5", "5w1.5", "+F", "3b2.5"],
    2: ["9b3", "3w4", "5b0", "1w1.5", "13w3", "4b2.5", "10b3"],
    3: ["10w2.5", "2b0", "9w3", "6b2.5", "4w3", "5b3.5", "1w1.5"],
    4: ["11b3", "1w2.5", "13b3", "5w3.5", "3b1", "2w1.5", "9b2.5"],
    5: ["12w4", "6b3", "2w4", "4b0.5", "1b2.5", "3w0.5", "13b3.5"],
    6: ["13b2", "5w1", "8b3", "3w1.5", "11b2.5", "-F", "12w2.5"],
    7: ["14w2", "8b2", "1b1", "10w2.5", "9b2", "13w2", "ZPB"],
    8: ["1b1.5", "7w2", "6w1", "12b3.5", "10b2", "9w2", "11w3"],
    9: ["2w1", "12b4", "3b1", "14w3", "7w2", "8b2", "4w1.5"],
    10: ["3b1.5", "11w1.5", "12b2.5", "7b1.5", "8w2", "14b3", "2w1"],
    11: ["4w1", "10b2.5", "14w2", "13b1.5", "6w1.5", "12w2", "8b1"],
    12: ["5b0", "9w0", "10w1.5", "8w0.5", "PAB", "11b2", "6b1.5"],
    13: ["6w2", "14b2.5", "4w1", "11w2.5", "2b1", "7b2", "5w0.5"],
    14: ["7b2", "13w1.5", "11b2", "9b1", "HPB", "10w1", "PAB"],
}


def board_results(game_points):
    results = []
    while game_points >= 1:
        results.append("W")
        game_points -= 1
    if game_points:
        results.append("D")
    return results + ["L"] * (4 - len(results))


def held_team_tournament():
    tournament = {
        "tournamentNo": 1,
        "tournamentType": "Team-Swiss",
        "numRounds": 7,
        "currentRound": 7,
        "teamTournament": True,
        "teamSize": 4,
        "rankOrder": ["PTS"],
        "scoreSystem": {
            "game": dict(GAME_SCORE),
            "match": dict(MATCH_SCORE),
            "primary": "match",
            "secondary": "game",
        },
        "competitors": [],
        "gameList": [],
        "matchList": [],
    }
    for team in TEAM_ROWS:
        tournament["competitors"].append({
            "cid": team,
            "rank": team,
            "teamId": team,
            "present": True,
            "random": team,
            "cplayers": [{"cid": team * 10 + board, "teamId": team} for board in range(1, 5)],
        })

    game_id = 0
    match_id = 1000
    for team, rounds in TEAM_ROWS.items():
        for round_number, entry in enumerate(rounds, start=1):
            if entry[-1].isdigit():
                colour = "w" if "w" in entry else "b"
                opponent_text, game_points_text = entry.split(colour, 1)
                opponent = int(opponent_text)
                game_points = Decimal(game_points_text)
                if colour != "w":
                    continue  # the match is emitted from its white team's row
                results = board_results(game_points)
                if team == 11 and opponent == 14:
                    results = ["W", "D", "D", "L"]
                games = []
                for board, result in enumerate(results, start=1):
                    game_id += 1
                    games.append(game_id)
                    if board % 2:
                        white_player, black_player, white_result = team * 10 + board, opponent * 10 + board, result
                    else:
                        white_player, black_player, white_result = opponent * 10 + board, team * 10 + board, REVERSE[result]
                    tournament["gameList"].append({
                        "id": game_id,
                        "round": round_number,
                        "board": board,
                        "white": {"cid": white_player, "result": white_result},
                        "black": {"cid": black_player, "result": REVERSE[white_result]},
                        "played": True,
                        "rated": True,
                    })
                black_points = Decimal("4") - game_points
                result = "W" if game_points > black_points else ("D" if game_points == black_points else "L")
                match_id += 1
                tournament["matchList"].append({
                    "id": match_id,
                    "round": round_number,
                    "white": {"cid": team, "result": result, "gpoints": game_points},
                    "black": {"cid": opponent, "result": REVERSE[result], "gpoints": black_points},
                    "played": True,
                    "rated": False,
                    "games": games,
                })
            else:
                result, played = {
                    "+F": ("W", False), "-F": ("Z", False), "ZPB": ("Z", False),
                    "PAB": ("P", True), "HPB": ("H", False),
                }[entry]
                match_id += 1
                tournament["matchList"].append({
                    "id": match_id,
                    "round": round_number,
                    "white": {"cid": team, "result": result},
                    "black": None,
                    "played": played,
                    "rated": False,
                    "games": [],
                })
    return tournament


def compute(codes):
    tournament = held_team_tournament()
    params = {"tiebreak": codes, "check": False, "unrated": None, "swiss": True, "pre_determined": False}
    result = tiebreak.tiebreak(tournament, -1, params).compute_tiebreaks(tournament, params)
    return (
        {competitor["cid"]: [str(value) for value in competitor["tiebreakScore"]] for competitor in result["competitors"]},
        {competitor["cid"]: competitor["rank"] for competitor in result["competitors"]},
    )


MP = {1: "10", 2: "10", 3: "10", 4: "10", 5: "10", 6: "7", 7: "6", 8: "7", 9: "6", 10: "5", 11: "4", 12: "2", 13: "6", 14: "4"}
GP = {1: "17.5", 2: "17.0", 3: "16.0", 4: "17.0", 5: "18.0", 6: "12.5", 7: "11.5", 8: "15.0", 9: "14.5", 10: "13.0", 11: "11.5", 12: "7.5", 13: "11.5", 14: "11.5"}
BH_MP = {1: "64", 2: "57", 3: "58", 4: "56", 5: "55", 6: "46", 7: "44", 8: "41", 9: "50", 10: "44", 11: "41", 12: "41", 13: "52", 14: "36"}
BH_C1_MP = {1: "57", 2: "52", 3: "53", 4: "52", 5: "53", 6: "39", 7: "38", 8: "39", 9: "48", 10: "42", 11: "39", 12: "39", 13: "48", 14: "32"}
BH_GP = {1: "114.0", 2: "107.5", 3: "109.5", 4: "106.0", 5: "99.0", 6: "92.0", 7: "94.5", 8: "90.0", 9: "97.5", 10: "92.0", 11: "88.0", 12: "92.0", 13: "101.0", 14: "87.0"}
BH_C1_GP = {1: "100.5", 2: "96.0", 3: "97.0", 4: "94.5", 5: "91.5", 6: "79.5", 7: "83.0", 8: "82.5", 9: "90.0", 10: "84.5", 11: "80.5", 12: "84.5", 13: "89.5", 14: "75.5"}


def test_exercise_34_match_points_then_game_points():
    values, _ = compute(["PTS", "GPTS"])
    order = sorted(values, key=lambda team: (-Decimal(values[team][0]), -Decimal(values[team][1]), team))
    assert order == [5, 1, 2, 4, 3, 8, 6, 9, 7, 13, 10, 11, 14, 12]


def test_exercise_34_game_points_then_match_points():
    values, _ = compute(["GPTS", "MPTS"])
    order = sorted(values, key=lambda team: (-Decimal(values[team][0]), -Decimal(values[team][1]), team))
    assert order == [5, 1, 2, 4, 3, 8, 9, 10, 6, 7, 13, 11, 14, 12]


@pytest.mark.parametrize(
    "exercise,codes,expected",
    [
        (35, ["BH/V1"], BH_MP),
        (36, ["BH/C1/V1"], BH_C1_MP),
        (37, ["BH/X/V1", "BH/C1/X/V1"], {team: [BH_GP[team], BH_C1_GP[team]] for team in MP}),
        (38, ["EMMSB/C1/V1"], {1: "74", 2: "64", 3: "66", 4: "64", 5: "66"}),
        (39, ["EGMSB/V1"], {1: "158.0", 2: "144.0", 3: "150.0", 4: "146.0", 5: "132.0"}),
        (40, ["EMGSB/V1"], {7: "68.5", 9: "83.0", 13: "73.0"}),
        (41, ["EGGSB/V1"], {6: "157.50", 8: "181.50"}),
    ],
    ids=lambda value: "exercise-%s" % value if isinstance(value, int) else None,
)
def test_held_team_calculation(exercise, codes, expected):
    values, _ = compute(codes)
    actual = {team: values[team] if isinstance(wanted, list) else values[team][0] for team, wanted in expected.items()}
    assert actual == expected


def test_exercises_42_and_44_leave_incomplete_direct_encounters_tied():
    _, ranks = compute(["PTS", "EDE"])
    assert ranks[11] == ranks[14]  # Exercise 42
    assert ranks[7] == ranks[9] == ranks[13]  # Exercise 44


def test_exercise_43_direct_encounter_breaks_the_seven_point_tie():
    _, ranks = compute(["PTS", "EDE"])
    assert ranks[6] < ranks[8]


def test_exercise_45_extended_direct_encounter_orders_the_leaders():
    _, ranks = compute(["PTS", "EDE"])
    assert sorted(range(1, 6), key=ranks.get) == [4, 2, 1, 3, 5]


@pytest.mark.parametrize(
    "exercise,code",
    [(46, "EDEBT"), (47, "EDET"), (48, "EDEB")],
)
def test_held_board_tiebreak(exercise, code):
    _, ranks = compute(["PTS", code])
    assert ranks[11] < ranks[14]


def test_exercise_49_score_and_schedule_strength_combination():
    values, _ = compute(["SSSC/V1"])
    # Held prints one decimal; the engine retains the hundredths used to round it.
    expected = {1: "38.83", 2: "36.00", 3: "35.33", 4: "35.67", 5: "36.33", 6: "27.83", 7: "26.17", 8: "28.67", 9: "31.17", 10: "27.67", 11: "25.17", 12: "21.17", 13: "28.83", 14: "23.50"}
    assert {team: values[team][0] for team in expected} == expected


# Team 1's round-six forfeit win is the only result in this tournament affected by
# the 2026 Art. 16.4 cap.  Team 2 is included to prove that ordinary played rounds
# retain the Held value while the capped dummy contribution changes team 1.
@pytest.mark.parametrize(
    "exercise,code,expected",
    [
        (35, "BH/V2", {1: "61", 2: "57"}),
        (36, "BH/C1/V2", {1: "54", 2: "52"}),
        (37, "BH/X/V2", {1: "110.5", 2: "107.5"}),
        (38, "EMMSB/C1/V2", {1: "68", 2: "64"}),
        (39, "EGMSB/V2", {1: "151.0", 2: "144.0"}),
        (40, "EMGSB/V2", {1: "146.5", 2: "131.0"}),
        (41, "EGGSB/V2", {1: "269.00", 2: "249.75"}),
        (49, "SSSC/V2", {1: "37.83", 2: "36.00"}),
    ],
)
def test_held_team_exercise_under_2026_adjustment_rules(exercise, code, expected):
    values, _ = compute([code])
    assert {team: values[team][0] for team in expected} == expected
