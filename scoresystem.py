# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 13:57:55 2023
@author: Otto Milvang, sjakk@milvang.no
"""

from decimal import Decimal
import helpers

# ==============================
#
#  Scoresystem


class scoresystem:

    #                "W": {},
    #                "D": {},
    #                "L": {},
    #                "F": {},
    #                "H": {},
    #                "Z": {},
    #                "P": {},
    #                "A": {},
    #                "U": {},

    def __init__(self):
        self.name = ""
        self.score = {  # used to calculate scoresystem
            "game": {},
            "match": {},
        }

        self.default_score = {
            "game": {
                "W": Decimal("1.0"),
                "D": Decimal("0.5"),
                "L": Decimal("0.0"),
                "F": "W",
                "H": "D",
                "Z": Decimal("0.0"),
                "P": "W",
                "A": "D",
                "U": "Z",
            },
            "match": {
                "W": Decimal("2.0"),
                "D": Decimal("1.0"),
                "L": Decimal("0.0"),
                "F": "W",
                "H": "D",
                "Z": Decimal("0.0"),
                "P": "D",
                "A": "D",
                "U": "Z",
                "FG": "W*",
                "HG": "D*",
                "ZG": "Z*",
                "PG": "P*",
            },
        }

    def add_scoresystem(self, scoretype, scoresystem):
        score = self.score
        for key, value in scoresystem.items():
            score[scoretype][key] = value

    def add_unplayed(self, key, matchPoints, gamePoints):
        score = self.score
        score["match"][key] = matchPoints
        score["match"][key + "G"] = gamePoints

    # ths calculates score

    def parse_trf_pab(self, tournament, line):
        matchPoints = helpers.parse_float(line[4:8])
        gamePoints = helpers.parse_float(line[9:13])
        self.scores.add_unplayed("P", matchPoints, gamePoints)
        rnd = 1
        for i in range(17, len(line) + 1, 4):
            competitor = helpers.parse_int(line[i - 3 : i])
            if competitor > 0:
                gameResults = []
                totalPoints = gamePoints
                gamesleft = tournament["teamSize"]
                for i in range(gamesleft, 0, -1):
                    if totalPoints > i * self.gamescore["D"]:
                        gameResult = "W"
                    elif totalPoints < i * self.gamescore["L"]:
                        gameResult = "L"
                    else:
                        gameResult = "D"
                    gameResults.append(gameResult)
                    totalPoints -= self.gamescore[gameResult]
                for result in ["W", "D", "L", "Z"]:
                    if matchPoints == self.teamscore[result]:
                        matchResult = result
                self.byelist.append(
                    {
                        "type": "P",
                        "competitor": competitor,
                        "round": rnd,
                        "matchPoints": matchPoints,
                        "gamePoints": gamePoints,
                        "matchResult": matchResult,
                        "gameResults": gameResults,
                    }
                )
            rnd += 1

    #
    # Solve point system
    # Input array of equations:
    # sum = w * W + d * D + l * L + p * P + u * U + z * Z
    # Solve w, d, l, p, u, z for variables where W, D, L, P, U and Z present in equautins
    #

    def solve_scoresystem_p(self, equations, pab):
        # print(equations)
        score = {"sum": Decimal("0.0"), "W": 0, "D": 0, "L": 0, "P": 0, "U": 0, "Z": 0}
        # print ('PAB:', pab)
        res = {}
        for loss in [Decimal("0.0"), Decimal("0.5"), Decimal("1.0")]:
            res["L"] = loss
            for draw in [loss + Decimal("0.5"), loss + Decimal("1.0"), loss + Decimal("1.5"), loss + Decimal("2.0")]:
                res["D"] = draw
                for win in [
                    draw + draw - loss,
                    draw + draw - loss + 1,
                    draw + draw - loss + Decimal("0.5"),
                    draw + draw - loss + Decimal("1.0"),
                    draw + draw - loss + Decimal("1.5"),
                    draw + draw - loss + Decimal("2.0"),
                ]:
                    res["W"] = win
                    for unknown in ["D", "L", "W"]:
                        res["U"] = res[unknown]
                        ok = True
                        # if loss != 0.0 or draw != 0.5 or win != 1.0 or unknown != 'D':
                        #    continue
                        for result in equations:
                            tsum = 0
                            tsum += result["W"] * win
                            tsum += result["D"] * draw
                            tsum += result["L"] * loss
                            tsum += result["U"] * res[unknown]
                            res["U"] = unknown
                            res["Z"] = Decimal("0.0")
                            for key, value in result.items():
                                if key != "pab" and key != "pres":
                                    score[key] += value
                            pok = False
                            if result["P"] > 0:
                                for p in pab:
                                    # print(tsum, result['P'], res[p],  tsum + result['P'] * res[p], result['sum'])
                                    if tsum + result["P"] * res[p] == result["sum"]:
                                        # print('TRUE', result['sum'])
                                        pok = True
                                        result["pres"] = p
                                        res["P"] = res[p]
                            else:
                                # print(tsum, result['P'], result['sum'])
                                pok = tsum == result["sum"]
                            ok = ok and pok

                        if ok:
                            ret = {key: value for key, value in res.items() if score[key] != 0}
                            for key in ["X", "U"]:
                                if key in ret and res[key] in ["W", "D", "L", "Z"] and ret[key] not in ret:
                                    ret[res[key]] = res[res[key]]

                            for eq in equations:
                                # print(eq)
                                if "pab" in eq:
                                    # print(eq)
                                    eq["pab"]["wResult"] = eq["pres"]
                                    res.pop("P", None)

                            # print(equations)
                            # print('Score:', score)
                            # print('Ret = ',  ret)
                            return ret
        # print('none')
        # return None

    def solve_scoresystem(self, equations):
        res = False
        res = res or self.solve_scoresystem_p(equations, ["W"])
        res = res or self.solve_scoresystem_p(equations, ["D"])
        res = res or self.solve_scoresystem_p(equations, ["L"])
        res = res or self.solve_scoresystem_p(equations, ["W", "D"])
        res = res or self.solve_scoresystem_p(equations, ["D", "L"])
        res = res or self.solve_scoresystem_p(equations, ["W", "D", "L"])

        return res
        # print(equations)

    def fill_default_scoresystem(self, stype):
        score = {key: value for (key, value) in self.score[stype].items()}
        defscore = self.default_score[stype].copy()
        defscore.update(score)
        return defscore

        defscore = self.defualt_score["game"].copy()
        defscore.update(score)
        trans = {}
        for result in ["W", "D", "L", "Z"]:
            trans[defscore[result]] = result
        for result in ["F", "H", "P", "A", "U"]:
            if isinstance(defscore[result], Decimal):
                defscore[result] = trans[defscore[result]]
        self.score["game"] = defscore
        return defscore

    def update_gamescore(self, tournament, equations, istrf25):
        # score = helpers.solve_scoresystem(equations)  -- added record 162 to solve this
        score = self.fill_default_scoresystem("game")
        trans = {}
        for result in ["W", "D", "L", "Z"]:
            trans[score[result]] = result
        for result in ["F", "H", "P", "A", "U"]:
            if isinstance(score[result], Decimal):
                score[result] = trans[score[result]]
        self.score["game"] = score
        eqok = False
        for version in ["TRF25", "TRF16"]:
            # print("+EQOK", eqok, version, "162" in self.all_lines,  not eqok and ("162" not in self.all_lines or version == "TRF25"))
            if not eqok and (not istrf25 or version == "TRF25"):
                eqok = True
                score = self.fill_default_scoresystem("game") if version == "TRF25" else self.solve_scoresystem(equations)
                # print(version, score)
                for eq in equations:
                    if eq["sum"] == Decimal("0.0"):
                        continue
                    # print(eq)
                    # if "pab" in eq and version == "TRF25":
                    #    eq["pab"]["wResult"] = score["P"]
                    checksum = Decimal("0.0")
                    for elem in ["W", "D", "L", "Z", "P", "U"]:
                        if elem in score:
                            num = eq[elem]
                            val = elem
                            while not isinstance(val, Decimal):
                                val = score[val]
                            checksum += num * val
                    # print(eq)
                    if eq["sum"] != checksum:
                        eqok = False
                # print("-EQOK", eqok, version, "162" in self.all_lines)
        if not eqok:
            raise
        if "Z" not in score:
            score["Z"] = Decimal("0.0")
        self.score["game"] = score
        return score

    def update_teamscore(self, tournament, equations, istrf25):

        eqok = False
        score = self.fill_default_scoresystem("match")
        self.score["match"] = score
        return score

    def get_score(self, tournament, scorename, scoretype):
        score = self.score[scorename]

        points = score[scoretype]
        if isinstance(points, Decimal):
            pass
        elif len(points) == 2 and points[1] == "*":
            points = self.get_score(tournament, "game", points[0]) * tournament["teamSize"]
        else:
            points = self.get_score(tournament, scorename, points)
        # print(scorename, scoretype, points)
        return points

    def get_result(self, tournament, scoresystem, points):
        score = tournament.get("scoresystem", {}).get(scoresystem, {})

        if points == score.get("W", helpers.parse_float("1.0")):
            return "W"
        if points == score.get("D", helpers.parse_float("0.5")):
            return "D"
        if points == score.get("Z", helpers.parse_float("0.0")):
            return "Z"
        if points == score.get("L", helpers.parse_float("0.0")):
            return "L"
        return "Z"
