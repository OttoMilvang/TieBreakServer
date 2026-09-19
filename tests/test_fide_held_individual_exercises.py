# -*- coding: utf-8 -*-
"""Worked examples 1-33 from Mario Held's FIDE C.07 exercise paper.

Source: IA Mario Held, *Exercises in Tie-Breaking*, Rev. 2403220900 /
C.07-2023, pp. 10-50.  ``/V1`` is used where the paper's 2023 adjustment
rules matter.  Separate tests below pin the values produced by the replacement
rules approved for 2026, so a changed definition cannot masquerade as a
regression in an older worked example.
"""
import os

import pytest

from gacrux import tiebreak
from gacrux import trf2json


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
SWISS_5 = os.path.join(FIXTURES, "held_swiss_5.trf")
SWISS_9 = os.path.join(FIXTURES, "held_swiss_9.trf")
ROUND_ROBIN = os.path.join(FIXTURES, "held_round_robin.trf")


def compute(path, code, *, pre_determined=False, ranks=False):
    chessfile = trf2json.trf2json()
    with open(path, encoding="utf-8") as source:
        chessfile.parse_file(source.read(), True)
    tournament = chessfile.get_tournament(1)
    codes = ["PTS", code] if ranks else [code]
    params = {
        "tiebreak": codes,
        "check": False,
        "unrated": None,
        "pre_determined": pre_determined,
        "swiss": not pre_determined,
    }
    result = tiebreak.tiebreak(tournament, -1, params).compute_tiebreaks(tournament, params)
    if ranks:
        return {competitor["cid"]: competitor["rank"] for competitor in result["competitors"]}
    return {
        competitor["cid"]: str(competitor["tiebreakScore"][0])
        for competitor in result["competitors"]
    }


BH = {1: "12.5", 2: "13.0", 3: "15.5", 4: "15.0", 5: "8.5", 6: "12.0",
      7: "14.5", 8: "13.5", 9: "9.0", 10: "13.0", 11: "13.5", 12: "11.5",
      13: "14.0", 14: "11.0", 15: "12.0", 16: "12.5"}
BH_C1 = {1: "11.0", 2: "12.0", 3: "13.0", 4: "11.5", 5: "7.5", 6: "11.0",
         7: "12.5", 8: "12.0", 9: "7.5", 10: "11.5", 11: "12.0", 12: "9.5",
         13: "12.0", 14: "9.0", 15: "11.0", 16: "11.0"}
AOB = {1: "12.60", 2: "13.60", 3: "13.40", 4: "13.38", 5: "13.40", 6: "13.25",
       7: "11.90", 8: "13.00", 9: "12.75", 10: "10.90", 11: "12.75", 12: "15.00",
       13: "12.10", 14: "13.17", 15: "12.20", 16: "13.30"}
FB = {1: "13.5", 2: "13.5", 3: "15.0", 4: "15.5", 5: "10.0", 6: "12.0",
      7: "13.5", 8: "12.5", 9: "9.5", 10: "12.5", 11: "12.5", 12: "11.5",
      13: "13.5", 14: "10.5", 15: "12.0", 16: "13.5"}
SB = {1: "8.00", 2: "9.50", 3: "10.50", 4: "9.75", 5: "4.25", 6: "6.50",
      7: "3.25", 8: "5.25", 9: "2.25", 10: "1.50", 11: "5.75", 12: "4.00",
      13: "4.25", 14: "4.50", 15: "3.50", 16: "7.25"}
SB_C1 = {1: "7.25", 2: "8.50", 3: "9.25", 4: "8.00", 5: "3.25", 6: "5.50",
         7: "1.25", 8: "3.75", 9: "2.25", 10: "0.00", 11: "4.25", 12: "4.00",
         13: "4.25", 14: "3.00", 15: "2.50", 16: "5.75"}
ARO = {1: "1820", 2: "1880", 3: "1940", 4: "1888", 5: "1690", 6: "1813",
       7: "1760", 8: "1730", 9: "1975", 10: "1880", 11: "1863", 12: "2050",
       13: "1930", 14: "1800", 15: "1860", 16: "1820"}
ARO_C1 = {1: "1900", 2: "1988", 3: "2000", 4: "1983", 5: "1738", 6: "1900",
          7: "1838", 8: "1800", 9: "2200", 10: "1975", 11: "2000", 12: "None",
          13: "2025", 14: "1900", 15: "1963", 16: "1900"}
TPR = {1: "1969", 2: "2120", 3: "2089", 4: "2081", 5: "1690", 6: "1813",
       7: "1611", 8: "1730", 9: "1175", 10: "1640", 11: "1776", 12: "1250",
       13: "1781", 14: "1925", 15: "1788", 16: "1969"}
WIN = {1: "2", 2: "3", 3: "2", 4: "2", 5: "2", 6: "3", 7: "1", 8: "2",
       9: "1", 10: "1", 11: "2", 12: "2", 13: "1", 14: "2", 15: "2", 16: "3"}
WON = {1: "2", 2: "3", 3: "2", 4: "2", 5: "2", 6: "2", 7: "1", 8: "2",
       9: "0", 10: "1", 11: "1", 12: "0", 13: "1", 14: "2", 15: "2", 16: "3"}
BPG = {1: "2", 2: "3", 3: "2", 4: "2", 5: "2", 6: "2", 7: "3", 8: "2",
       9: "1", 10: "3", 11: "2", 12: "0", 13: "3", 14: "2", 15: "3", 16: "2"}
BWG = {1: "1", 2: "1", 3: "1", 4: "1", 5: "0", 6: "1", 7: "0", 8: "0",
       9: "0", 10: "1", 11: "0", 12: "0", 13: "1", 14: "1", 15: "1", 16: "1"}
GE = {1: "5", 2: "5", 3: "5", 4: "4", 5: "5", 6: "5", 7: "5", 8: "5",
      9: "3", 10: "5", 11: "5", 12: "3", 13: "5", 14: "3", 15: "5", 16: "5"}
PS = {1: "11.0", 2: "13.0", 3: "11.0", 4: "11.5", 5: "5.0", 6: "6.0",
      7: "6.0", 8: "8.5", 9: "2.5", 10: "4.0", 11: "5.5", 12: "7.0",
      13: "7.0", 14: "6.0", 15: "7.0", 16: "10.5"}
PS_C1 = {1: "10.0", 2: "12.0", 3: "10.5", 4: "10.5", 5: "5.0", 6: "6.0",
         7: "5.0", 8: "8.0", 9: "2.5", 10: "4.0", 11: "5.0", 12: "7.0",
         13: "6.0", 14: "5.0", 15: "7.0", 16: "10.0"}


def only(values, *players):
    return {player: values[player] for player in players}


# One named case per exercise keeps the document's numbering visible in pytest output.
HELD_EXERCISES = [
    (1, SWISS_5, "BH/V1", only(BH, 2), False, False),
    (2, SWISS_5, "BH/V1", only(BH, 1, 3), False, False),
    (3, SWISS_5, "BH/V1", only(BH, 5, 8, 11), False, False),
    (4, SWISS_5, "BH/V1", only(BH, 1, 3, 4, 16), False, False),
    (5, SWISS_5, "BH/C1/V1", only(BH_C1, 5, 8, 11), False, False),
    (6, SWISS_5, "BH/C1/V1", only(BH_C1, 7, 9, 13), False, False),
    (7, SWISS_5, "BH/C1/V1", only(BH_C1, 1, 3, 4, 16), False, False),
    (8, SWISS_5, "BH/C1/V1", only(BH_C1, 12, 14, 15), False, False),
    (9, SWISS_5, "AOB/V1", AOB, False, False),
    (10, SWISS_5, "FB/V1", FB, False, False),
    (11, SWISS_5, "SB/V1", only(SB, 1, 3, 4, 16), False, False),
    (12, SWISS_5, "SB/V1", SB, False, False),
    (13, SWISS_5, "SB/C1/V1", SB_C1, False, False),
    (14, ROUND_ROBIN, "SB/V1", {1: "9.25", 2: "6.25", 3: "6.25", 4: "4.25", 5: "3.25", 6: "2.25"}, True, False),
    (15, ROUND_ROBIN, "SB/C1/V1", {1: "9.25", 2: "4.75", 3: "4.75", 4: "4.25", 5: "3.25", 6: "1.50"}, True, False),
    (16, ROUND_ROBIN, "KS", {1: "2.0", 2: "0.5", 3: "0.5", 4: "1.0", 5: "0.5", 6: "0.0"}, True, False),
    (17, SWISS_5, "ARO/V1", ARO, False, False),
    (18, SWISS_5, "ARO/C1/V1", ARO_C1, False, False),
    (19, SWISS_5, "TPR/V1", only(TPR, 2, 6, 12), False, False),
    (20, SWISS_5, "TPR/V1", TPR, False, False),
    (21, SWISS_5, "APRO/V1", {1: "1789", 3: "1904", 4: "1772", 16: "1805"}, False, False),
    (22, SWISS_5, "PTP/V1", {3: "2112"}, False, False),
    (23, SWISS_5, "DE", {1: 2, 3: 2, 4: 2, 16: 2}, False, True),
    (24, SWISS_5, "DE", {5: 7, 8: 7, 11: 7}, False, True),
    (25, SWISS_9, "DE", {1: 3, 2: 5, 3: 1, 4: 3, 5: 9, 6: 2, 7: 6, 8: 6, 9: 14, 10: 9, 11: 13, 12: 14, 13: 16, 14: 9, 15: 9, 16: 6}, False, True),
    (26, ROUND_ROBIN, "DE", {1: 1, 2: 2, 3: 2, 4: 6, 5: 5, 6: 4}, True, True),
    (27, SWISS_5, "WIN", WIN, False, False),
    (28, SWISS_5, "WON", WON, False, False),
    (29, SWISS_5, "BPG", BPG, False, False),
    (30, SWISS_5, "BWG", BWG, False, False),
    (31, SWISS_5, "GE", GE, False, False),
    (32, SWISS_5, "PS", PS, False, False),
    (33, SWISS_5, "PS/C1", PS_C1, False, False),
]


@pytest.mark.parametrize(
    "exercise,path,code,expected,pre_determined,ranks",
    HELD_EXERCISES,
    ids=["exercise-%02d" % case[0] for case in HELD_EXERCISES],
)
def test_held_individual_exercise(exercise, path, code, expected, pre_determined, ranks):
    actual = compute(path, code, pre_determined=pre_determined, ranks=ranks)
    assert {player: actual[player] for player in expected} == expected


def changed(values, **replacements):
    result = dict(values)
    result.update({int(player): value for player, value in replacements.items()})
    return result


# The 2026 Art. 16.4 cap changes only these worked examples.  The old expectations
# above remain Held's published answers; these are the corresponding /V2 answers.
POST_2026 = [
    (3, "BH/V2", only(changed(BH, **{"11": "12.5"}), 5, 8, 11)),
    (4, "BH/V2", only(changed(BH, **{"4": "14.0"}), 1, 3, 4, 16)),
    (5, "BH/C1/V2", only(changed(BH_C1, **{"11": "11.0"}), 5, 8, 11)),
    (9, "AOB/V2", changed(AOB, **{"1": "12.40", "3": "12.90", "5": "13.20", "7": "11.70", "8": "12.90", "10": "10.80", "12": "14.00", "13": "11.90", "14": "13.00", "16": "13.10"})),
    (10, "FB/V2", changed(FB, **{"4": "14.5", "11": "12.0", "12": "11.0"})),
    (11, "SB/V2", only(changed(SB, **{"4": "9.25"}), 1, 3, 4, 16)),
    (12, "SB/V2", changed(SB, **{"4": "9.25", "6": "6.00", "11": "4.75"})),
    (13, "SB/C1/V2", changed(SB_C1, **{"4": "7.75", "6": "5.00", "11": "3.25"})),
]


@pytest.mark.parametrize(
    "exercise,code,expected",
    POST_2026,
    ids=["exercise-%02d-2026" % case[0] for case in POST_2026],
)
def test_held_exercise_under_2026_adjustment_rules(exercise, code, expected):
    actual = compute(SWISS_5, code)
    assert {player: actual[player] for player in expected} == expected
