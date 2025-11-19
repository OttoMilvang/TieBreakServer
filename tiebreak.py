# -*- coding: utf-8 -*-
"""
Created on Fri Aug  11 11:43:23 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import math
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import rating as rating

"""
Structure

+--- tiebreaks: [  - added in compute-tiebreak
|         {
|             order: priority of tiebreak
|             name: Acronym from regulations
|             pointtype: mpoints (match points) gpoints (game points) or points
|             modifiers: { low / high / lim / urd / p4f / fmo / rev / ver / vuv / rev }
|         },
|         ...
|
|       ]
+--- isteam: True/False
+--- currentRound: Standings after round 'currentround'
+--- rounds: Total number of rounds
+--- rr: RoundRobin (True/False)
+--- scoresystem: {
|        game: { W:1.0, D:0.5, L:0.0, Z:0.0, P:1.0, A:0.5, U: 0.0 }
|        team: { W:1.0, D:1.0, L:0.0, Z:0.0, P:1.0, A:1.0, U: 0.0 }
|                 }
+--- players/teams:  {
|              1: {
|                    cid: startno
|                    rating: rating
|                    kfactor: k
|                    rating: rating
|                    rrst: {  - results, games for players, matches for teams
|                        1: {  - round
|                              points - points for game / match
|                              rpoints - for games, points with score system 1.0 / 0.5 / 0.0
|                              color - w / b
|                              played  - boolean
|                              rated - boolean
|                              opponent - id of opponent
|                              opprating - rating of opponent
|                              deltaR - for rating change
|                            }
|                        2: {  - round 2 }
|                           ...
|                           }
|                   tbval: {  - intermediate results from tb calculations }
|     ---- output for each player / team
|                   score: [ array of tie-breaks values, same order and length as 'tiebreaks'
|                   rank: final rank of player / team
|                 },
|              2: { ... },
|                  ...
|         }
+--- rankorder: [ array of rankorder,  players/teams ]
|

"""


class tiebreak:

    # CURRENT_RULES = 1  => First implementation
    # CURRENT_RULES = 2  => 2026-02-01,  §16, max value  
    
    TIEBREAK_RULES = {
        1 : "2024-08-01",
        2 : "2026-02-01",
        } 

    # constructor function
    def __init__(self, chessevent, tournamentno, currentround, params):
        self.tiebreaklist = {
            "NUL":   {"func": self.get_nul,                             "rev": False, "desc": "Null"},
            "PTS":   {"func": self.get_builtin,                         "rev": True , "desc": "Points (default)"},
            "MPTS":  {"func": self.get_builtin,                         "rev": True , "desc": "Match Points"},
            "GPTS":  {"func": self.get_builtin,                         "rev": True , "desc": "Game Points"},
            "SNO":   {"func": self.get_builtin,                         "rev": False, "desc": "Start number"},
            "RANK":  {"func": self.get_builtin,                         "rev": False, "desc": "Original rank in tournament file"},
            "RND":   {"func": self.get_builtin,                         "rev": False, "desc": "Unique random number"},
            "WIN":   {"func": self.get_builtin,                         "rev": True , "desc": "Number of Wins"},
            "WON":   {"func": self.get_builtin,                         "rev": True , "desc": "Number of Games Won"},
            "BPG":   {"func": self.get_builtin,                         "rev": True , "desc": "Number of Games Played with Black"},
            "BWG":   {"func": self.get_builtin,                         "rev": True , "desc": "Number of Games Won with Black"},
            "GE":    {"func": self.get_builtin,                         "rev": True , "desc": "Same as REP"},
            "REP":   {"func": self.get_builtin,                         "rev": True , "desc": "Rounds one Elected to Play"},
            "RIP":   {"func": self.get_builtin,                         "rev": True , "desc": "number of rounds paired (for TPN assignment)"},
            "VUR":   {"func": self.get_builtin,                         "rev": True , "desc": "Voluntary unplayed rounds"},
            "NUM":   {"func": self.get_builtin,                         "rev": True , "desc": "Number of played games"},
            "COP":   {"func": self.get_builtin,                         "rev": True , "desc": "Color preference"},
            "COD":   {"func": self.get_builtin,                         "rev": True , "desc": "Color difference"},
            "CSQ":   {"func": self.get_builtin,                         "rev": True , "desc": "Color sequence"},
            "RTG":   {"func": self.get_builtin,                         "rev": True , "desc": "Start number"},
            "MPVGP": {"func": self.reverse_pointtype,                   "rev": True , "desc": "Match Points or Game Points"},
            "DE":    {"func": self.compute_direct_encounter,            "rev": False, "desc": "Direct Encounter"},
            "EDE":   {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "EDEC":  {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "EDET":  {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "EDEB":  {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "EDEBT": {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "EDEBB": {"func": self.compute_ext_direct_encounter,        "rev": False, "desc": "Direct Encounter"},
            "PS":    {"func": self.compute_progressive_score,           "rev": True , "desc": "Progressive Scores"},
            "KS":    {"func": self.compute_koya,                        "rev": True , "desc": "Koya system"},
            "BH":    {"func": self.compute_buchholz_sonneborn_berger,   "rev": True , "desc": "Bochholz"},
            "FB":    {"func": self.compute_buchholz_sonneborn_berger,   "rev": True , "desc": "Fore Bochholz"},
            "SB":    {"func": self.compute_buchholz_sonneborn_berger,   "rev": True , "desc": "Sonneborn Berger"},
            "ABH":   {"func": self.compute_buchholz_sonneborn_berger,   "rev": True , "desc": "Adjusted score for Buchholz"},
            "AFB":   {"func": self.compute_buchholz_sonneborn_berger,   "rev": True , "desc": "Adjusted score for Fore Buchholz"},
            "AOB":   {"func": self.compute_average_of_buchholz,         "rev": True , "desc": "Average of Buchholz"},
            "ARO":   {"func": self.compute_ratingperformance,           "rev": True , "desc": "Average Rating of opponents"},
            "TPR":   {"func": self.compute_ratingperformance,           "rev": True , "desc": "Tournament Rating Performance"},
            "PTP":   {"func": self.compute_ratingperformance,           "rev": True , "desc": "Perfect Rating Performance"},
            "APRO":  {"func": self.compute_average_rating_performance,  "rev": True , "desc": "Average of Rating Performance"},
            "APPO":  {"func": self.compute_average_perfect_performance, "rev": True , "desc": "Average of Perfect Performance"},
            "ESB":   {"func": self.compute_ext_sonneborn_berger,        "rev": True , "desc": "Extended Sonneborn Berger" },
            "EMMSB": {"func": self.compute_ext_sonneborn_berger,        "rev": True , "desc": "Extended Sonneborn Berger" },
            "EMGSB": {"func": self.compute_ext_sonneborn_berger,        "rev": True , "desc": "Extended Sonneborn Berger" },
            "EGMSB": {"func": self.compute_ext_sonneborn_berger,        "rev": True , "desc": "Extended Sonneborn Berger" },
            "EGGSB": {"func": self.compute_ext_sonneborn_berger,        "rev": True , "desc": "Extended Sonneborn Berger" },
            "BC":    {"func": self.compute_boardcount,                  "rev": False, "desc": "Board count"},
            "TBR":   {"func": self.compute_top_bottom_board,            "rev": False, "desc": "Board count"},
            "BBE":   {"func": self.compute_top_bottom_board,            "rev": False, "desc": "Board count"},
            "SSSC":  {"func": self.compute_score_strength_combination,  "rev": True , "desc": "Score strength combination"},
            "STD":   {"func": self.compute_std,                         "rev": True , "desc": "Stanard score system"},
            "ACC":   {"func": self.compute_acc,                         "rev": True , "desc": "	Points + accellerated points"},
            "FLT":   {"func": self.compute_flt,                         "rev": True , "desc": "Float (8=df 4=uf in prev round, 2=df 1=uf in 2 rounds before)"},
            "RFP":   {"func": self.compute_rfp,                         "rev": True , "desc": "Registered for round"},
            "TOP":   {"func": self.compute_top,                         "rev": True , "desc": "	Is player a top-scorer in last round"},
            }
            
        self.tournament = tournament = chessevent.get_tournament(tournamentno)
        self.tiebreaks = []
        if tournament is None:
            return
        self.isteam = self.isteam = tournament["teamTournament"] if "teamTournament" in tournament else False
        self.teamsize = tournament["teamSize"] if "teamSize" in tournament else 1
        chessevent.update_tournament_random(tournament, self.isteam)
        self.rounds = tournament["numRounds"]
        self.currentround = currentround if currentround >= 0 else self.rounds
        self.get_score = chessevent.get_score
        self.is_vur = chessevent.is_vur
        self.maxboard = 0
        self.lastplayedround = 0
        self.primaryscore = None  # use default
        self.acceleration = tournament["acceleration"] if "acceleration" in tournament else None
        self.rating = {"W": Decimal("1.0"), "D": Decimal("0.5"), "L": "Z", "Z": Decimal("0.0"), "A": "Z", "U": "Z"}

        if self.isteam:
            self.scoresystem = tournament["scoreSystem"]
            self.matchscore = tournament["scoreSystem"]["match"]
            self.gamescore = tournament["scoreSystem"]["game"]
            [self.cplayers, self.cteam] = chessevent.build_tournament_teamcompetitors(tournament)
            self.allgames = chessevent.build_all_games(tournament, self.cteam, False)
            self.teams = self.prepare_competitors(tournament, "match")
            self.compute_score(self.teams, "match", "mpoints", self.matchscore, self.currentround)
            self.compute_score(self.teams, "game", "gpoints", self.gamescore, self.currentround)
        else:
            self.matchscore = tournament["scoreSystem"]["game"]
            self.gamescore = tournament["scoreSystem"]["game"]
            self.players = self.prepare_competitors(tournament, "game")
            self.compute_score(self.players, "game", "points", self.gamescore, self.currentround)
        self.cmps = self.teams if self.isteam else self.players
        numcomp = len(self.cmps)
        self.rankorder = list(self.cmps.values())

        # find tournament type
        tt = tournament["tournamentType"].upper()
        self.rr = params["is_rr"] if params is not None and "is_rr" in params else False
        if self.rr is None:
            if tt.find("SWISS") >= 0:
                self.rr = False
            elif tt.find("RR") >= 0 or tt.find("ROBIN") >= 0 or tt.find("BERGER") >= 0:
                self.rr = True
            elif numcomp == self.rounds + 1 or numcomp == self.rounds:
                self.rr = True
            elif numcomp * 2 == (self.rounds + 1) or numcomp * 2 == self.rounds:
                self.rr = True
        self.unrated = int(params["unrated"]) if params is not None and "unrated" in params else 0
        self. rulesversion = max(self.TIEBREAK_RULES.keys())

    def find_tmversion(self, tm):
        startdate = tm.get("tournamentInfo", {}).get("startDate", "")
        if len(startdate) != 10:
            startdate = str(datetime.now())[0:10]
        if startdate < self.TIEBREAK_RULES[2]:
            self.rulesversion = 1
        

    """
    compute_tiebreaks(self, chessfile, tournamentno, params)
    chessfile - Chessfile structure
    tournamentno - which tournament to calculate
    params - Parameters from core
    """

    def compute_tiebreaks(self, chessfile, tournamentno, params):
        # run tiebreak
        if chessfile.get_status() == 0:
            tm = chessfile.get_tournament(tournamentno)
            self.find_tmversion(tm)
            tblist = params["tie_break"]
            if len(tblist) == 0 and "rankOrder" in tm:
                tblist = tm["rankOrder"]
                params["tie_break"] = tblist
            for pos in range(0, len(tblist)):
                mytb = self.parse_tiebreak(pos + 1, tblist[pos])
                self.compute_tiebreak(mytb)
        if chessfile.get_status() == 0:
            tm["rankOrder"] = self.tiebreaks
            jsoncmps = tm["competitors"]
            correct = True
            competitors = []
            for cmp in jsoncmps:
                competitor = {}
                competitor["cid"] = startno = cmp["cid"]
                correct = correct and cmp["rank"] == self.cmps[startno]["rank"]
                competitor["rank"] = cmp["rank"] = self.cmps[startno]["rank"]
                if self.isteam:
                    competitor["boardPoints"] = self.cmps[startno]["tbval"]["gpoints_" + "bp"]
                competitor["tiebreakDetails"] = self.cmps[startno]["tiebreakDetails"]
                competitor["tiebreakScore"] = cmp["tiebreakScore"] = self.cmps[startno]["tiebreakScore"]
                competitors.append(competitor)
            chessfile.result = {
                "check": correct, 
                "rules": self.TIEBREAK_RULES[self.rulesversion],
                "tiebreaks": self.tiebreaks, 
                "competitors": competitors
            }
        

    def prepare_competitors(self, tournament, scorename):
        rounds = self.currentround
        # for rst in competition['results']:
        #    rounds = max(rounds, rst['round'])
        # self.rounds = rounds
        ptype = "mpoints" if self.isteam else "points"
        # scoresystem = self.scoresystem['match']
        # Fill competition structure, replaze unplayed games with played=Fales, points=0.0
        cmps = {}
        for competitor in tournament["competitors"]:
            rnd = competitor["random"] if "random" in competitor else 0
            cmp = {
                "cid": competitor["cid"],
                "rsts": {},
                "orgrank": competitor["rank"] if "rank" in competitor else 0,
                "rank": 1,
                "rating": (competitor["rating"] if "rating" in competitor else 0),
                "present": competitor["present"] if "present" in competitor else True,
                "tiebreakScore": [],
                "tiebreakDetails": [],
                "rnd": rnd,
                "tbval": {},
            }
            # Be sure that missing results are replaced by zero
            zero = Decimal("0.0")
            for rnd in range(1, rounds + 1):
                cmp["rsts"][rnd] = {
                    ptype: zero,
                    "rpoints": zero,
                    "res": "Z",
                    "color": "w",
                    "played": False,
                    "vur": True,
                    "rated": False,
                    "opponent": 0,
                    "opprating": 0,
                    "board": 0,
                    "deltaR": 0,
                }
            cmps[competitor["cid"]] = cmp
        for rst in tournament[scorename + "List"]:
            if rst["round"] <= self.currentround or True:
                self.prepare_result(cmps, rst, self.matchscore)
                if self.isteam:
                    self.prepare_teamgames(cmps, rst, self.scoresystem)

        # helpers.json_output('c:\\temp\\mc02.txt', cmps)

        return cmps

    def solve_score(self, tournament, score, scorename, scoretype):
        points = score[scorename][scoretype]
        if isinstance(points, Decimal):
            return points
        if len(points) == 2 and points[1] == "*":
            return self.solve_score(tournament, score, "game", points[0]) * tournament["teamSize"]
        return self.solve_score(tournament, score, scorename, points)

    def prepare_result(self, cmps, rst, scoresystem):
        ptype = "mpoints" if self.isteam else "points"
        scoresystem = self.matchscore if self.isteam else self.gamescore
        rnd = rst["round"]
        white = rst["white"]
        wPoints = self.get_score(scoresystem, rst, "white")
        wrPoints = self.get_score(self.rating, rst, "white")
        wVur = self.is_vur(rst, "white")
        wrating = 0
        brating = 0
        expscore = None
        if "black" in rst:
            black = rst["black"]
        else:
            black = 0
        if black > 0:
            if "bResult" not in rst:
                rst["bResult"] = self.scoreLists["_reverse"][rst["wResult"]]
            bPoints = self.get_score(scoresystem, rst, "black")
            brPoints = self.get_score(self.rating, rst, "black")
            bVur = self.is_vur(rst, "black")
            if rst["played"]:
                if white in cmps and "rating" in cmps[white] and cmps[white]["rating"] > 0:
                    wrating = cmps[white]["rating"]
                if black in cmps and "rating" in cmps[black] and cmps[black]["rating"] > 0:
                    brating = cmps[black]["rating"]
                expscore = rating.ComputeExpectedScore(wrating, brating)
        board = rst["board"] if "board" in rst else 0
        if white > 0:
            cmps[white]["rsts"][rnd] = {
                ptype: wPoints,
                "rpoints": wrPoints,
                "res": rst["wResult"],
                "color": "w",
                "played": rst["played"],
                "vur": wVur,
                "rated": rst["rated"] if "rated" in rst else (rst["played"] and black > 0),
                "opponent": black,
                "opprating": brating,
                "board": board,
                "deltaR": (rating.ComputeDeltaR(expscore, wrPoints) if expscore is not None else None),
            }
        if black > 0:
            self.lastplayedround = max(self.lastplayedround, rnd)
            cmps[black]["rsts"][rnd] = {
                ptype: bPoints,
                "rpoints": brPoints,
                "res": rst["bResult"],
                "color": "b",
                "played": rst["played"],
                "vur": bVur,
                "rated": rst["rated"] if "rated" in rst else (rst["played"] and white > 0),
                "opponent": white,
                "opprating": wrating,
                "board": board,
                "deltaR": (rating.ComputeDeltaR(Decimal(1.0) - expscore, brPoints) if expscore is not None else None),
            }
        return

    def prepare_teamgames(self, cmps, rst, score):
        maxboard = 0
        rnd = rst["round"]
        for col in ["white", "black"]:
            if col in rst and rst[col] > 0:
                gpoints = 0
                competitor = rst[col]
                games = []
                cmp = cmps[competitor]["rsts"][rnd]
                if competitor in self.allgames[rnd]:
                    for game in self.allgames[rnd][competitor]:
                        white = game["white"]
                        black = game["black"] if "black" in game else 0
                        board = game["board"] if "board" in game else 0
                        maxboard = max(maxboard, board)
                        wVur = self.is_vur(game, "white")
                        if self.cteam[white] == competitor and board > 0:
                            points = self.get_score(self.gamescore, game, "white")
                            gpoints += points
                            games.append(
                                {
                                    "points": points,
                                    "rpoints": self.get_score(self.rating, game, "white"),
                                    "color": "w",
                                    "vur": wVur,
                                    "played": game["played"],
                                    "rated": game["rated"] if "rated" in rst else (game["played"] and black > 0),
                                    "player": white,
                                    "opponent": black,
                                    "board": board,
                                }
                            )
                        if black > 0 and board > 0 and self.cteam[black] == competitor:
                            points = self.get_score(self.gamescore, game, "black")
                            bVur = self.is_vur(game, "black")
                            gpoints += points
                            games.append(
                                {
                                    "points": points,
                                    "rpoints": self.get_score(self.rating, game, "black"),
                                    "color": "b",
                                    "vur": bVur,
                                    "played": game["played"],
                                    "rated": game["rated"] if "rated" in rst else (game["played"] and black > 0),
                                    "player": black,
                                    "opponent": white,
                                    "board": board,
                                }
                            )
                    cmp["gpoints"] = gpoints
                    cmp["games"] = games
                else:
                    if cmp["opponent"] == 0 and cmp["played"]:
                        cmp["gpoints"] = self.solve_score(self.tournament, score, "match", "PG")
                    else:
                        trans = {"W": "F", "D": "H", "L": "Z"}
                        res = trans[cmp["res"]] if cmp["res"] in trans else cmp["res"]
                        cmp["gpoints"] = self.solve_score(self.tournament, score, "match", res + "G")
                    cmp["games"] = []
        self.maxboard = max(self.maxboard, maxboard)

    def addtbval(self, obj, rnd, val):
        rnd = str(rnd)
        if rnd in obj:
            if isinstance(val, str):
                obj[rnd] = obj[rnd] + val
            else:
                obj[rnd] = obj[rnd] + val
        else:
            obj[rnd] = val

    def compute_score(self, cmps, scorename, pointtype, scoretype, norounds):
        prefix = pointtype + "_"
        other = {"w": "b", "b": "w", " ": " "}
        pointsfordraw = scoretype["D"] * (self.teamsize if scorename[0] == "g" else 1)
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            tbscore[prefix + "nul"] = {"val": 0}
            tbscore[prefix + "sno"] = {"val": startno}
            tbscore[prefix + "rank"] = {"val": cmp["orgrank"]}
            tbscore[prefix + "rnd"] = {"val": cmp["rnd"]}
            tbscore[prefix + "rtg"] = {"val": cmp["rating"]}
            tbscore[prefix + "cnt"] = {"val": 0}  # count number of elements (why)
            tbscore[prefix + "points"] = {"val": Decimal("0.0")}  # total points
            tbscore[prefix + "win"] = {"val": 0}  # number of wins (played and unplayed)
            tbscore[prefix + "won"] = {"val": 0}  # number of won games over the board
            tbscore[prefix + "bpg"] = {"val": 0}  # number of black games played
            tbscore[prefix + "bwg"] = {"val": 0}  # number of games won with black
            tbscore[prefix + "ge"] = {"val": 0}  # number of games played + PAB
            tbscore[prefix + "rep"] = {"val": 0}  # number of rounds elected to play (same as GE)
            tbscore[prefix + "rip"] = {"val": 0}  # number of rounds paired (for TPN assignment)
            tbscore[prefix + "vur"] = {"val": 0}  # number of vurs (check algorithm)
            tbscore[prefix + "cop"] = {"val": "  "}  # color preference (for pairing)
            tbscore[prefix + "cod"] = {"val": 0}  # color difference (for pairing)
            tbscore[prefix + "csq"] = {"val": ""}  # color sequence (for pairing)
            tbscore[prefix + "num"] = {"val": 0}  # number of games played (for pairing)
            tbscore[prefix + "lp"] = 0  # last round played
            tbscore[prefix + "lo"] = 0  # last round without vur
            tbscore[prefix + "lp"] = 0  # last round paired
            tbscore[prefix + "pfp"] = 0  # points from played games
            tbscore[prefix + "lg"] = 0  # self.scoreLists[scoretype]['D'] # Result of last game
            tbscore[prefix + "bp"] = {}  # Boardpoints
            # cmpr = sorted(cmp, key=lambda p: (p['rank'], p['tbval'][prefix + name]['val'], p['cid']))
            pcol = " "  # Previous color
            csq = ""
            for rnd in range(1, norounds + 1):
                if rnd in cmp["rsts"]:
                    rst = cmp["rsts"][rnd]
                    # total score
                    points = rst[pointtype] if pointtype in rst else 0
                    tbscore[prefix + "points"][rnd] = points
                    tbscore[prefix + "points"]["val"] += points
                    # number of games
                    if self.isteam and scorename == "game":
                        if rst["played"] and rst["opponent"] > 0:
                            gamelist = rst["games"] 
                        else:
                            gamelist =  []
                            points = self.gamescore[rst["res"]]
                            while isinstance(points, str):
                                points = self.gamescore[points]
                            for board in range(self.teamsize):
                                gamelist.append({"points": points, 
                                                  "rpoints": Decimal('0.0'), 
                                                  "color": "w", 
                                                  "vur": rst["vur"], 
                                                  "played": rst["played"], 
                                                  "rated": False,
                                                  "player": 0, 
                                                  "opponent": 0,
                                                  "board": board+1}) 
                    else:
                        gamelist = [rst]
                    for game in gamelist:
                        if self.isteam and scorename == "game":
                            points = game["points"]
                            if game["played"] and game["opponent"] <= 0:  # PAB
                                points = self.gamescore["W"]
                            board = game["board"]
                            tbscore[prefix + "bp"][board] = (
                                tbscore[prefix + "bp"][board] + points if board in tbscore[prefix + "bp"] else points
                            )
                            # tbscore[prefix + 'bp']['val'] += tbscore[prefix + 'bp'][board]

                        self.addtbval(tbscore[prefix + "cnt"], rnd, 1)
                        self.addtbval(tbscore[prefix + "cnt"], "val", 1)

                        # result in last game
                        if rnd == self.rounds and game["opponent"] > 0:
                            tbscore[prefix + "lg"] += points

                        # points from played games
                        if game["played"]:
                            self.addtbval(tbscore[prefix + "num"], rnd, game["opponent"])
                            if game["opponent"] > 0:
                                self.addtbval(tbscore[prefix + "num"], "val", 1)
                                tbscore[prefix + "pfp"] += points
                                ocol = ncol = game["color"]
                                pf = 1 if ocol == "w" else -1
                                self.addtbval(tbscore[prefix + "cod"], rnd, pf)
                                self.addtbval(tbscore[prefix + "cod"], "val", pf)
                                pf = tbscore[prefix + "cod"]["val"]
                                ncol = (other[ocol] + "bbbbwwww")[pf]
                                ncol += str(abs(pf)) if ocol != pcol else "2"
                                # if ocod > -2 and ocod < 2:
                                #    ncol = 'w' if ocol == 'b' else 'b'
                                #    ncol = ncol.upper() if ncol.upper() == tbscore[prefix + 'cop']['val'].upper()
                                #    else ncol

                                csq += ocol
                                pcol = ocol
                                self.addtbval(tbscore[prefix + "csq"], rnd, ocol)
                                self.addtbval(tbscore[prefix + "csq"], "val", ocol)

                                self.addtbval(tbscore[prefix + "cop"], rnd, ncol)
                                tbscore[prefix + "cop"]["val"] = ncol

                            # last played game (or PAB)
                            if rnd > tbscore[prefix + "lp"]:
                                tbscore[prefix + "lp"] = rnd
                        elif "points" in game and game["points"] == scoretype["W"]:
                            self.addtbval(tbscore[prefix + "num"], rnd, 0)

                        # number of win
                        win = 1 if points == scoretype["W"] else 0
                        self.addtbval(tbscore[prefix + "win"], rnd, win)
                        self.addtbval(tbscore[prefix + "win"], "val", win)

                        # number of win played over the board
                        won = 1 if points == scoretype["W"] and game["played"] and game["opponent"] > 0 else 0
                        self.addtbval(tbscore[prefix + "won"], rnd, won)
                        self.addtbval(tbscore[prefix + "won"], "val", won)

                        # number of games played with black
                        bpg = 1 if game["color"] == "b" and game["played"] else 0
                        self.addtbval(tbscore[prefix + "bpg"], rnd, bpg)
                        self.addtbval(tbscore[prefix + "bpg"], "val", bpg)

                        # number of win played with black
                        bwg = 1 if game["color"] == "b" and game["played"] and points == scoretype["W"] else 0
                        self.addtbval(tbscore[prefix + "bwg"], rnd, bwg)
                        self.addtbval(tbscore[prefix + "bwg"], "val", bwg)

                        # number of games elected to play
                        # ge = 1 if game['played'] or (game['opponent'] > 0 and points == self.scoreLists[scoretype][
                        # 'W']) else 0
                        ge = 1 if game["played"] or (points == scoretype["W"]) else 0
                        self.addtbval(tbscore[prefix + "ge"], rnd, ge)
                        self.addtbval(tbscore[prefix + "ge"], "val", ge)
                        self.addtbval(tbscore[prefix + "rep"], rnd, ge)
                        self.addtbval(tbscore[prefix + "rep"], "val", ge)

                        # number of gamesin pairing
                        rip = 1 if game["played"] or game["opponent"] > 0 else 0
                        self.addtbval(tbscore[prefix + "rip"], rnd, rip)
                        self.addtbval(tbscore[prefix + "rip"], "val", rip)

                        vur = 1 if game["vur"] else 0
                        self.addtbval(tbscore[prefix + "vur"], rnd, vur)
                        self.addtbval(tbscore[prefix + "vur"], "val", vur)

                        # last round with opponent, pab or fpb (16.2.1, 16.2.2, 16.2.3 and 16.2.4)
                        if rnd > tbscore[prefix + "lo"] and (vur == 0):
                            tbscore[prefix + "lo"] = rnd
                        if rnd > tbscore[prefix + "lp"] and (game["opponent"] > 0):
                            tbscore[prefix + "lp"] = rnd

    """
    compute_recursive_if_tied is used for DE, EDE, EDEBT, EDEBB, EDET, EDEB, TBR and BBE
    Foreach loop see if last run untied any more. If not sort all records
    In loopcount 0 initializee all structures
    In loopcount 1 .. n run different parts for example for EDE alternate Primary scoro, secondary score  
    When subrange is empty clean up. We have finished all subranges and will report more_to_do

    """

    def compute_recursive_if_tied(self, tb, cmps, rounds, compute_singlerun):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        name = tb["name"].lower()
        ro = self.rankorder
        for player in ro:
            player["tbval"][prefix + name] = {}
            player["tbval"][prefix + name]["val"] = player["rank"]  # rank value initial value = rank
            player["tbval"]["moreloops"] = True  # As long as True we have more to check
        # part 1, run recursive until no more are tied
        loopcount = 0
        moretodo = compute_singlerun(tb, cmps, rounds, ro, loopcount)
        while moretodo:
            moretodo = False
            loopcount += 1
            start = 0
            while start < len(ro):
                currentrank = ro[start]["tbval"][prefix + name]["val"]
                for stop in range(start + 1, len(ro) + 1):
                    if stop == len(ro) or currentrank != ro[stop]["tbval"][prefix + name]["val"]:
                        break
                # we have a range start .. stop-1 to check for top board result
                if ro[start]["tbval"]["moreloops"]:
                    if stop - start == 1:
                        moreloops = False
                        ro[start]["tbval"]["moreloops"] = moreloops
                    else:
                        subro = ro[start:stop]  # subarray of rankorder
                        moreloops = compute_singlerun(tb, cmps, rounds, subro, loopcount)
                        for player in subro:
                            player["tbval"]["moreloops"] = moreloops  # 'de' rank value initial value = rank
                        moretodo = moretodo or moreloops
                start = stop
            # json.dump(ro, sys.stdout, indent=2)
            moreloops = compute_singlerun(tb, cmps, rounds, [], loopcount)
            moretodo = moretodo or moreloops
            ro = sorted(ro, key=lambda p: (p["rank"], p["tbval"][prefix + name]["val"], p["cid"]))
        # part 2, Reorder rank
        start = 0
        while start < len(ro):
            currentrank = ro[start]["rank"]
            for stop in range(start, len(ro) + 1):
                if stop == len(ro) or currentrank != ro[stop]["rank"]:
                    break
                # we have a range start .. stop-1 to check for direct encounter
            offset = ro[start]["tbval"][prefix + name]["val"]
            if ro[start]["tbval"][prefix + name]["val"] != ro[stop - 1]["tbval"][prefix + name]["val"]:
                offset -= 1
            for p in range(start, stop):
                ro[p]["tbval"][prefix + name]["val"] -= offset
            start = stop
        return name

    # -----------------
    # Direct encounter
    #
    
    def compute_direct_encounter(self, tb, cmps, rounds):
        func = self.compute_singlerun_direct_encounter
        return self.compute_recursive_if_tied(tb, cmps, rounds, func)
 
    def compute_ext_direct_encounter(self, tb, cmps, rounds):
        if tb["name"] in ["EDEC", "EDEBT", "EDEBB"]:
            self.compute_boardcount(tb, cmps, self.currentround)
        func = self.compute_singlerun_ext_direct_encounter
        return self.compute_recursive_if_tied(tb, cmps, rounds, func)


    def compute_basic_direct_encounter(self, tb, cmps, rounds, subro, loopcount, points, scorename, scoretype, prefix):
        name = tb["name"].lower()
        (xscorename, xpoints, xscoretype, prefix) = self.get_scoreinfo(tb, True)
        changes = 0
        rpos = loopcount - tb["modifiers"]["swap"]  # Report pos
        postfix = " " + scorename[0] if tb["name"] == "EDE" else ""
        currentrank = subro[0]["tbval"][prefix + name]["val"]
        metall = True  # Met all opponents on same range
        metmax = len(subro) - 1  # Max number of opponents
        for player in range(0, len(subro)):
            de = subro[player]["tbval"]
            de["denum"] = 0  # number of opponens
            de["deval"] = 0  # sum score against of opponens
            de["demax"] = 0  # sum score against of opponens, unplayed = win
            de["delist"] = {}  # list of results numgames, score, maxscore
            for rnd, rst in subro[player]["rsts"].items():
                if rnd <= rounds:
                    opponent = rst["opponent"]
                    if opponent > 0:
                        played = True if tb["modifiers"]["p4f"] else rst["played"]
                        if played and cmps[opponent]["tbval"][prefix + name]["val"] == currentrank:
                            # 6.1.2 compute average score
                            if opponent in de["delist"]:
                                score = de["delist"][opponent]["score"]
                                num = de["delist"][opponent]["cnt"]
                                sumscore = score * num
                                de["deval"] -= score
                                num += 1
                                sumscore += rst[points]
                                score = sumscore / num
                                de["denum"] = 1
                                de["deval"] += score
                                de["delist"][opponent]["cnt"] = 1
                                de["delist"][opponent]["score"] = score
                            else:
                                de["denum"] += 1
                                de["deval"] += rst[points]
                                de["delist"][opponent] = {"cnt": 1, "score": rst[points]}
            # if not tb['modifiers']['p4f'] and de['denum'] < metmax:
            # if (not tb['modifiers']['p4f'] and de['denum'] < metmax) or tb['modifiers']['sws']:
            if (not self.rr and de["denum"] < metmax) or tb["modifiers"]["sws"]:
                metall = False
                de["demax"] = de["deval"] + (metmax - de["denum"]) * scoretype["W"] * (self.teamsize if points == "gpoints" else 1)
            else:
                de["demax"] = de["deval"]
        if metall:  # 6.2 All players have met
            # print("T")
            subro = sorted(subro, key=lambda p: (-p["tbval"]["deval"], p["cid"]))
            crank = rank = subro[0]["tbval"][prefix + name]["val"]
            val = subro[0]["tbval"]["deval"]
            sprefix = "\t" if rpos in subro[0]["tbval"][prefix + name] else ""
            self.addtbval(subro[0]["tbval"][prefix + name], rpos, sprefix + str(val) + postfix)
            for i in range(1, len(subro)):
                rank += 1
                de = subro[i]["tbval"]
                if val != de["deval"]:
                    crank = de[prefix + name]["val"] = rank
                    val = de["deval"]
                    changes += 1
                else:
                    de[prefix + name]["val"] = crank
                sprefix = "\t" if rpos in de[prefix + name] else ""
                self.addtbval(de[prefix + name], rpos, sprefix + str(val) + postfix)
        else:  # 6.2 swiss tournament
            # print("F")
            subro = sorted(subro, key=lambda p: (-p["tbval"]["deval"], -p["tbval"]["demax"], p["cid"]))
            crank = rank = subro[0]["tbval"][prefix + name]["val"]
            val = subro[0]["tbval"]["deval"]
            maxval = subro[0]["tbval"]["demax"]
            sprefix = "\t" if rpos in subro[0]["tbval"][prefix + name] else ""
            self.addtbval(subro[0]["tbval"][prefix + name], rpos, sprefix + str(val) + "/" + str(maxval) + postfix)
            unique = True
            for i in range(1, len(subro)):
                rank += 1
                tbmax = max(subro[i:], key=lambda tbval: tbval["tbval"]["demax"])
                de = subro[i]["tbval"]
                if unique and val > tbmax["tbval"]["demax"]:
                    crank = de[prefix + name]["val"] = rank
                    val = de["deval"]
                    maxval = de["demax"]
                    changes += 1
                else:
                    val = de["deval"]
                    maxval = de["demax"]
                    de[prefix + name]["val"] = crank
                    unique = False
                sprefix = "\t" if rpos in de[prefix + name] else ""
                self.addtbval(de[prefix + name], rpos, sprefix + str(val) + "/" + str(maxval) + postfix)
                # self.addtbval(de[prefix + name], rpos,  str(val) + '/' + str(maxval) + postfix)
        return changes

    def compute_singlerun_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        tb["modifiers"]["swap"] = 0
        changes = 1 if loopcount == 0 else 0
        if loopcount > 0 and len(subro) > 0:
            changes = self.compute_basic_direct_encounter(tb, cmps, rounds, subro, loopcount, points, scorename, scoretype, prefix)
        return changes

    """
    EDE - Primary Score - Secondary score
    EDEC - Primary Score - Secondary score - BC
    EDET - Primary Score - Secondary score - TBR
    EDEB - Primary Score - Secondary score - BBE
    EDEBT - Primary Score - Secondary score - BC -TBR
    EDEBB - Primary Score - Secondary score - BC - BBE
    Does not work ...
    """

    def xxcompute_singlerun_ext_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        # name = tb["name"].lower()
        # print("compute_singlerun_ext_direct_encounter", loopcount, points, scoretype, prefix, subro[0]['rank'] if len(subro)> 0 else 0 , len(subro))
        changes = 0
        if loopcount == 0:
            functype = {
                "EDE": "PS", 
                "EDEC": "PSC", 
                "EDET": "PST", 
                "EDEB": "PSB", 
                "EDEBT": "PSCT", 
                "EDEBB": "PSCB"
            }
            tb["modifiers"]["functions"] = functions = functype[tb["name"]]
            tb["modifiers"]["loopcount"] = 0
            tb["modifiers"]["edechanges"] = [True] * len(functions)
            tb["modifiers"]["swap"] = 0
            return True
        if tb["modifiers"]["loopcount"] != loopcount:
            tb["modifiers"]["loopcount"] = loopcount
            tb["modifiers"]["changes"] = 0
        if len(subro) == 0:
            if tb["modifiers"]["changes"] == 0:
                tb["modifiers"]["primary"] = not tb["modifiers"]["primary"]
                tb["modifiers"]["edechanges"][scorename] = 0
                swap = tb["modifiers"]["swap"]
                tb["modifiers"]["edechanges"][swap] = True
                tb["modifiers"]["swap"] = (swap + 1) % len(tb["modifiers"]["functions"])
                ro = self.rankorder
                for player in ro:
                    player["tbval"]["moreloops"] = True  # 'de' rank value initial value = rank
            else:
                tb["modifiers"]["edechanges"] = [True for _ in tb["modifiers"]["edechanges"]]
            return any(tb["modifiers"]["edechanges"]) and loopcount < 30
        changes = 0
        swap = tb["modifiers"]["functions"][tb["modifiers"]["swap"]]
        if swap == "P":
                (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
                while (
                    ch := self.compute_basic_direct_encounter(
                        tb, cmps, rounds, subro, loopcount, points, scorename, scoretype, prefix
                    )
                ) > 0:
                    changes += ch
        if swap == "S":
                (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, False)
                while (
                    ch := self.compute_basic_direct_encounter(
                        tb, cmps, rounds, subro, loopcount, points, scorename, scoretype, prefix
                    )
                ) > 0:
                    changes += ch
        if swap == "B":
                (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, False)
                while (ch := self.compute_basic_direct_encounter(tb, cmps, rounds, subro, loopcount, "bc", "bc", "bc", prefix)) > 0:
                    changes += ch

        tb["modifiers"]["changes"] += changes
        return changes > 0 and loopcount < 30

    def compute_singlerun_ext_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        name = tb['name'].lower()
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, loopcount == 0 or tb['modifiers']['primary'])
        #(points, scoretype, prefix) = self.get_scoreinfo(tb, loopcount == 0 or tb['modifiers']['primary'])
        changes = 0
        if loopcount == 0:
            tb['modifiers']['primary'] = True
            tb['modifiers']['points'] = points
            (secondary, _, _, _) = self.get_scoreinfo(tb, False)
            tb['modifiers']['loopcount'] = 0
            tb['modifiers']['edechanges'] = {scorename: 0, secondary: 1 }
            tb['modifiers']['swap'] = 0
            return True
        if tb['modifiers']['loopcount'] != loopcount:
            tb['modifiers']['loopcount'] = loopcount
            tb['modifiers']['changes'] = 0
        if len(subro) == 0: 
            if tb['modifiers']['changes'] == 0:
                tb['modifiers']['primary'] = not tb['modifiers']['primary']
                tb['modifiers']['edechanges'][scorename] = 0
                tb['modifiers']['swap'] += 1
                ro = self.rankorder
                for player in ro:
                    player['tbval']['moreloops'] = True  # 'de' rank value initial value = rank
            else:
                (secondary, _, _, _) = self.get_scoreinfo(tb, not tb['modifiers']['primary'])
                tb['modifiers']['edechanges'][secondary] = 1
            retsum = tb['modifiers']['edechanges']['match'] + tb['modifiers']['edechanges']['game']
            #print('E', loopcount, tb['modifiers']['changes'], retsum, tb['modifiers']['edechanges'])
            return retsum > 0  and loopcount < 30
        changes = self.compute_basic_direct_encounter(tb, cmps, rounds, subro, loopcount, points, scorename, scoretype, prefix)
        tb['modifiers']['changes'] += changes
        return changes > 0 and loopcount < 30



    def compute_progressive_score(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        low = tb["modifiers"]["low"]
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            ps = 0
            ssf = 0  # Sum so far
            tbscore[prefix + "ps"] = {"val": ps, "cut": []}
            for rnd in range(1, rounds + 1):
                p = cmp["rsts"][rnd][points] if rnd in cmp["rsts"] and points in cmp["rsts"][rnd] else Decimal("0.0")
                ssf += p
                # p = p * (rounds+1-rnd)
                tbscore[prefix + "ps"][rnd] = ssf
                if rnd <= low:
                    tbscore[prefix + "ps"]["cut"].append(rnd)
                else:
                    ps += ssf
            tbscore[prefix + "ps"]["val"] = ps
        return "ps"

    def compute_koya(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        plim = tb["modifiers"]["plim"]
        nlim = tb["modifiers"]["nlim"]
        lim = plim * scoretype["W"] * rounds * (self.teamsize if points == "gpoints" else 1) / Decimal("100.0") + nlim
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            ks = 0
            tbscore[prefix + "ks"] = {"val": ks, "cut": []}
            for rnd, rst in cmp["rsts"].items():
                if rnd <= rounds:
                    opponent = rst["opponent"]
                    if opponent > 0:
                        oppscore = cmps[opponent]["tbval"][prefix + "points"]["val"]
                        ownscore = cmp["tbval"][prefix + "points"][rnd]
                        tbscore[prefix + "ks"][rnd] = ownscore
                        if oppscore >= lim:
                            ks += ownscore
                        else:
                            tbscore[prefix + "ks"]["cut"].append(rnd)
            tbscore[prefix + "ks"]["val"] = ks
        return "ks"

    def compute_buchholz_sonneborn_berger(self, tb, cmps, rounds):
        version = self.rulesversion
        if tb["modifiers"]["ver"]:
            version = max(self.TIEBREAK_RULES.keys())
        tbname = self.compute_buchholz_sonneborn_berger_ver(tb, cmps, rounds, version)
        return tbname
        
    def compute_ext_sonneborn_berger(self, tb, cmps, rounds):
        if len(tb["name"]) == 5:
            tb["pointtype"] = tb["name"][1:3].lower() + "points"
        tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
        return tbname


    def compute_buchholz_sonneborn_berger_ver(self, tb, cmps, rounds, version):
        name = tb["name"].lower()
        isfb = name == "fb" or name == "afb" or tb["modifiers"]["fmo"]
        (oscorename, opoints, oscoretype, oprefix) = self.get_scoreinfo(tb, True)
        (sscorename, spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, name == "sb")
        opointsfordraw = oscoretype["D"] * (self.teamsize if opoints == "gpoints" else 1)
        spointsfordraw = sscoretype["D"] * (self.teamsize if spoints == "gpoints" else 1)
        # print("Pointsfordraw",  oprefix, opointsfordraw, sprefix, spointsfordraw)
        name = tb["name"].lower()
        if name == "aob":
            name = "bh"
        is_sb = name == "sb" or name == "esb" or (len(name) == 5 and name[0] == "e" and name[3:5] == "sb")
        if name == "esb" or (len(name) == 5 and name[0] == "e" and name[3:5] == "sb"):
            (sscorename, spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, False)
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            tbscore[oprefix + "abh"] = {"val": 0}  # Adjusted score for BH (check algorithm)
            # 16.3.2    Unplayed rounds of category 16.2.5 are evaluated as draws.
            isfore = isfb and tbscore[oprefix + "lp"] == self.rounds  # do we need to adjust for Fore
            adjustfore = False
            for rnd, rst in cmp["rsts"].items():
                if rnd <= rounds:
                    points_no_opp = Decimal(0.0) if self.rr else opointsfordraw
                    hasopponent = rnd <= tbscore[oprefix + "lo"] or rst["opponent"] > 0
                    adjustfore = adjustfore or (isfore and rnd == rounds and rst["opponent"] > 0)
                    tbval = rst[opoints] if hasopponent else points_no_opp
                    tbscore[oprefix + "abh"][rnd] = tbval
                    tbscore[oprefix + "abh"]["val"] += tbval
            fbscore = tbscore[oprefix + "points"]["val"]
            if adjustfore:
                adjust = opointsfordraw - tbscore[oprefix + "lg"]
                tbscore[oprefix + "abh"][self.rounds] += adjust
                tbscore[oprefix + "abh"]["val"] += adjust
                fbscore += adjust
            tbscore[oprefix + "ownscore"] = fbscore
            #if version == 2:
            #    tbscore[oprefix + "abh"] = max(tbscore[oprefix + "abh"], opointsfordraw * rounds)
                
        if name == "abh" or name == "afb":
            return "abh"

        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            bhvalue = []
            for rnd, rst in cmp["rsts"].items():
                if rnd <= rounds:
                    opponent = rst["opponent"]
                    vur = rst["vur"]
                    played = True if tb["modifiers"]["p4f"] or (isfb and rnd == self.rounds) else rst["played"]
                    if played and opponent > 0:
                        vur = False
                        score = cmps[opponent]["tbval"][oprefix + "abh"]["val"]
                    elif not self.rr:
                        score = cmps[startno]["tbval"][oprefix + "ownscore"]
                        if tb["modifiers"]["ver"] == 2: # 2026-02-01
                            if opponent > 0:  # 16.4.1
                                score = min(score, cmps[opponent]["tbval"][oprefix + "abh"]["val"])
                            else:             # 16.4.2
                                score = min(score, opointsfordraw * rounds)
                    else:
                        score = 0
                    if tb["modifiers"]["urd"] and not self.rr:
                        sres = spointsfordraw
                    else:
                        sres = rst[spoints] if spoints in rst else Decimal("0.0")
                    tbvalue = score * sres if is_sb else score
                    # if  opponent >  0 or not tb['modifiers']['p4f'] :
                    if opponent > 0 or not self.rr:
                        bhvalue.append({"vur": vur, "tbvalue": tbvalue, "score": score, "rnd": rnd})
            tbscore = cmp["tbval"]
            tbscore[oprefix + name] = {"val": 0, "cut": []}
            for game in bhvalue:
                self.addtbval(tbscore[oprefix + name], game["rnd"], game["tbvalue"])

            low = tb["modifiers"]["low"]
            if low > rounds:
                low = rounds
            high = tb["modifiers"]["high"]
            if low + high > rounds:
                high = rounds - low
            while low > 0:
                sortall = sorted(bhvalue, key=lambda game: (game["score"], game["tbvalue"]))
                sortexp = sorted(bhvalue, key=lambda game: (-game["vur"], game["score"], game["tbvalue"]))
                if tb["modifiers"]["vun"] or sortall[0]["tbvalue"] > sortexp[0]["tbvalue"]:
                    bhvalue = sortall[1:]
                    tbscore[oprefix + name]["cut"].append(sortall[0]["rnd"])
                else:
                    bhvalue = sortexp[1:]
                    tbscore[oprefix + name]["cut"].append(sortexp[0]["rnd"])
                low -= 1

            while high > 0:
                sortall = sorted(bhvalue, key=lambda game: (-game["score"], -game["tbvalue"]))
                # sortexp = sorted(bhvalue, key=lambda game: (-game['vur'], -game['score'], -game['tbvalue'])) // No
                # exception on high
                sortexp = sorted(bhvalue, key=lambda game: (-game["score"], -game["tbvalue"]))
                if tb["modifiers"]["vun"]:
                    bhvalue = sortall[1:]
                    tbscore[oprefix + name]["cut"].append(sortall[0]["rnd"])
                else:
                    bhvalue = sortexp[1:]
                    tbscore[oprefix + name]["cut"].append(sortexp[0]["rnd"])
                high -= 1

            #            if high > 0:
            #                if tb['modifiers']['vun']:
            #                    bhvalue = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))[high:]
            #                else:
            #                    bhvalue = sorted(bhvalue, key=lambda game: (game['played'], -game['score'],
            #                    -game['tbvalue']))[high:]

            for game in bhvalue:
                self.addtbval(tbscore[oprefix + name], "val", game["tbvalue"])
        return name


        
    def compute_ratingperformance(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        name = tb["name"].lower()
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            tbscore[prefix + "aro"] = {"val": 0, "cut": []}
            tbscore[prefix + "tpr"] = {"val": 0, "cut": []}
            tbscore[prefix + "ptp"] = {"val": 0, "cut": []}
            ratingopp = []
            trounds = 0
            for rnd, rst in cmp["rsts"].items():
                if rnd <= rounds and rst["played"] and rst["opponent"] > 0:
                    trounds += 1
                    if rst["opprating"] > 0 or tb["modifiers"]["unr"] > 0:
                        rst["rnd"] = rnd
                        rst["adjrating"] = rtng = rst["opprating"] if rst["opprating"] > 0 else tb["modifiers"]["unr"]
                        ratingopp.append(rst)
                        self.addtbval(cmp["tbval"][prefix + "aro"], rnd, rtng)
                        self.addtbval(cmp["tbval"][prefix + "tpr"], rnd, rtng)
                        self.addtbval(cmp["tbval"][prefix + "ptp"], rnd, rtng)
            # trounds = rounds  // This is correct only if unplayed gmes are cut.
            low = tb["modifiers"]["low"]
            if low > rounds:
                low = rounds
            high = tb["modifiers"]["high"]
            if low + high > rounds:
                high = rounds - low
            while low > 0:
                if trounds == len(ratingopp):
                    newopp = sorted(ratingopp, key=lambda p: (p["adjrating"]))
                    if len(newopp) > 0:
                        tbscore[prefix + name]["cut"].append(newopp[0]["rnd"])
                    ratingopp = newopp[1:]
                trounds -= 1
                low -= 1
            while high > 0:
                if trounds == len(ratingopp):
                    newopp = sorted(ratingopp, key=lambda p: (p["adjrating"]))
                    if len(newopp) > 0:
                        tbscore[prefix + name]["cut"].append(newopp[-1]["rnd"])
                    ratingopp = newopp[:-1]
                trounds -= 1
                high -= 1
            rscore = 0
            ratings = []
            for p in ratingopp:
                rscore += p["rpoints"]
                ratings.append(p["adjrating"])

            tbscore[prefix + "aro"]["val"] = rating.ComputeAverageRatingOpponents(ratings)
            tbscore[prefix + "tpr"]["val"] = rating.ComputeTournamentPerformanceRating(rscore, ratings)
            tbscore[prefix + "ptp"]["val"] = rating.ComputePerfectTournamentPerformance(rscore, ratings)
        return tb["name"].lower()

    def compute_boardcount(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            bc = 0
            tbscore[prefix + "bc"] = {"val": bc}
            for val, points in tbscore["gpoints_" + "bp"].items():
                bc += val * points
                self.addtbval(tbscore[prefix + "bc"], val, val * points)
            tbscore[prefix + "bc"]["val"] = bc
        return "bc"

    def compute_top_bottom_board(self, tb, cmps, rounds):
        tbname = self.compute_recursive_if_tied(tb, cmps, rounds, self.compute_singlerun_topbottomboardresult)
        return tbname

    def compute_singlerun_topbottomboardresult(self, tb, cmps, rounds, ro, loopcount):
        name = tb["name"].lower()
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        if loopcount == 0:
            for player in ro:
                player["tbval"]["tbrval"] = Decimal("0.0")
                player["tbval"]["bbeval"] = Decimal("0.0")
                for val, points in player["tbval"]["gpoints_" + "bp"].items():
                    player["tbval"]["bbeval"] += points
            return True
        if len(ro) == 0:
            return False
        for player in range(0, len(ro)):
            ro[player]["tbval"]["tbrval"] = ro[player]["tbval"]["gpoints_" + "bp"][loopcount]
            ro[player]["tbval"]["bbeval"] -= ro[player]["tbval"]["gpoints_" + "bp"][self.maxboard - loopcount + 1]
        subro = sorted(ro, key=lambda p: (-p["tbval"][name + "val"], p["cid"]))
        count = currentrank = ro[0]["tbval"][prefix + name]["val"]
        for player in range(0, len(subro)):
            if subro[player]["tbval"][name + "val"] != subro[player - 1]["tbval"][name + "val"]:
                currentrank = count
            subro[player]["tbval"][prefix + name]["val"] = currentrank
            self.addtbval(subro[player]["tbval"][prefix + name], loopcount, subro[player]["tbval"][name + "val"])
            count += 1
        return loopcount < self.maxboard

    def compute_score_strength_combination(self, tb, cmps, currentround):
        self.compute_buchholz_sonneborn_berger(tb, cmps, currentround)
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            dividend = cmp["tbval"][prefix + "sssc"]["val"]
            divisor = 1
            key = points[0]
            if key == "m":
                score = cmp["tbval"]["gpoints_" + "points"]["val"]
                divisor = math.floor(scoretype["W"] * currentround / self.gamescore["W"] / self.maxboard)
            elif key == "g":
                score = cmp["tbval"]["mpoints_" + "points"]["val"]
                divisor = math.floor(scoretype["W"] * currentround * self.maxboard / self.matchscore["W"])
            if tb["modifiers"]["nlim"] > 0:
                divisor = tb["modifiers"]["nlim"]
            val = (score + dividend / divisor).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            cmp["tbval"][prefix + "sssc"] = {"val": val}
        return "sssc"

    def get_accelerated(self, prefix, rnd, startno):
        acc = "Z"
        if self.acceleration is None:
            return acc
        for val in self.acceleration["values"]:
            if (
                rnd >= val["firstRound"]
                and rnd <= val["lastRound"]
                and startno >= val["firstCompetitor"]
                and startno <= val["lastCompetitor"]
            ):
                acc = val["gameResult"] if prefix == "points_" else val["matchResult"]
        return acc

    # STD: 1.0/ 0.5 /0.0 point system

    def compute_std(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        pointsfordraw = scoretype["D"]
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            tbscore[prefix + "std"] = {"val": Decimal("0.0"), 0: Decimal("0.0")}
            for rnd in range(1, rounds + 1):
                #breakpoint()                
                if scorename == "match" or self.teamsize <= 1:
                    p = cmp["rsts"][rnd][points] if rnd in cmp["rsts"] and points in cmp["rsts"][rnd] else Decimal("0.0")
                    # std from 2026 rules, does not work for 
                    if p > pointsfordraw:
                        std = Decimal("1.0")
                    elif p == pointsfordraw:
                        std = Decimal("0.5")
                    else:
                        std = Decimal("0.0")
                elif cmp["rsts"][rnd]["played"] and cmp["rsts"][rnd]["opponent"] > 0:
                    std = Decimal("0.0")
                    for game in cmp["rsts"][rnd]['games']:
                        p = game["points"]
                        if p > pointsfordraw:
                            std += Decimal("1.0")
                        elif p == pointsfordraw:
                            std += Decimal("0.5")
                else:
                    pointsfordraw = self.gamescore["D"]                  
                    p = self.gamescore[cmp["rsts"][rnd]["res"]]
                    while isinstance(p, str):
                        p = self.gamescore[p]
                    if p > pointsfordraw:
                        std = Decimal("1.0")
                    elif p == pointsfordraw:
                        std = Decimal("0.5")
                    else:
                        std = Decimal("0.0")
                    std = std * self.teamsize
                tbscore[prefix + "std"][rnd] = std
                tbscore[prefix + "std"]["val"] += std
                #print(pointsfordraw, p, std, tbscore[prefix + "std"]["val"])
                #breakpoint()
        return "std"

    def compute_acc(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        if prefix + "acc" in cmps[1]["tbval"]:
            return "acc"

        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            acc = self.get_accelerated(prefix, 1, startno)
            val = scoretype[acc]
            tbscore[prefix + "acc"] = {"val": val, 0: val}
            spoints = 0  # Points so far
            for rnd in range(1, rounds + 1):
                p = cmp["rsts"][rnd][points] if rnd in cmp["rsts"] and points in cmp["rsts"][rnd] else Decimal("0.0")
                spoints += p
                acc = self.get_accelerated(prefix, rnd + 1, startno)  # Round 0 shall have the value of 1 and so on
                val = spoints + scoretype[acc]
                tbscore[prefix + "acc"][rnd] = val
            tbscore[prefix + "acc"]["val"] = val
        return "acc"

    def compute_flt(self, tb, cmps, rounds):
        self.compute_acc(tb, cmps, rounds)
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            tbscore[prefix + "flt"] = {"val": 0}
            nfloat = 0  # Float so far as numeric
            sfloat = ""  # Float so far as string
            for rnd in range(1, rounds + 1):
                nfloat *= 4
                p = cmp["rsts"][rnd][points] if rnd in cmp["rsts"] and points in cmp["rsts"][rnd] else Decimal("0.0")
                opp = cmp["rsts"][rnd]["opponent"] if rnd in cmp["rsts"] and "opponent" in cmp["rsts"][rnd] else 0
                # ownacc = own points + accellerated
                # oppacc = opponent points + accellerated
                if opp > 0 and cmp["rsts"][rnd]["played"]:
                    ownacc = cmp["tbval"][prefix + "acc"][rnd - 1]
                    oppacc = cmps[opp]["tbval"][prefix + "acc"][rnd - 1]
                elif p > scoretype["L"] or cmp["rsts"][rnd]["played"]:  # Have points without playing, more than points for loss
                    ownacc = 1
                    oppacc = 0
                else:
                    ownacc = 0
                    oppacc = 0
                if ownacc > oppacc:
                    cfloat = "d"
                    ifloat = 1
                elif ownacc < oppacc:
                    cfloat = "u"
                    ifloat = 2
                else:
                    cfloat = "-"
                    ifloat = 0
                if rnd == 1 and cfloat == "u":
                    pass
                self.addtbval(tbscore[prefix + "flt"], rnd, cfloat)
                nfloat += ifloat
                sfloat += cfloat
            tbscore[prefix + "flt"]["val"] = (sfloat if tb["modifiers"]["sws"] else nfloat) % 16
        return "flt"

    def compute_rfp(self, tb, cmps, rounds):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            val = True
            tbscore[prefix + "rfp"] = {"val": val}
            for rnd in range(1, rounds + 2):
                val = True
                if rnd in cmp["rsts"]:
                    if cmp["rsts"][rnd]["opponent"] == 0:
                        clr = "w"
                    elif startno == 0:
                        clr = "b"
                    else:
                        clr = cmp["rsts"][rnd]["color"]
                    val = (
                        str(cmp["rsts"][rnd]["opponent"]) + clr
                        if cmp["rsts"][rnd]["played"] or (cmp["rsts"][rnd]["opponent"] > 0)
                        else ""
                    )
                elif rnd > self.lastplayedround:
                    val = "Y" if cmp["present"] else ""
                else:
                    val = ""
                if rnd <= rounds:
                    val = "pab" if val == "0w" else val
                    if not cmp["rsts"][rnd]["played"]:
                        res = cmp["rsts"][rnd]["res"]
                        if cmp["rsts"][rnd]["opponent"]:
                            val = {"W": "+", "D": "=", "L": "-", "P": "pab", "U": "=", "Z": "-"}[res]
                        else:
                            val = {"W": "F", "D": "H", "L": "Z", "P": "pab", "U": "=", "Z": "Z"}[res]
                    tbscore[prefix + "rfp"][rnd] = val
            tbscore[prefix + "rfp"]["val"] = val
        return "rfp"

    def compute_top(self, tb, cmps, rounds):
        self.compute_acc(tb, cmps, rounds)
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        last = self.rounds - 1
        lim = scoretype["W"] * last * (self.teamsize if points == "gpoints" else 1) / Decimal("2.0")
        for startno, cmp in cmps.items():
            tbscore = cmp["tbval"]
            val = (rounds >= last) and tbscore[prefix + "acc"][last] > lim
            tbscore[prefix + "top"] = {"val": val}
        return "top"

    def get_nul(self, tb, cmps, rounds):
        return "nul"

    def get_builtin(self, tb, cmps, rounds):
        tbname = tb["name"]
        if tbname == "PTS" or tbname == "MPTS" or tbname == "GPTS":
            return "points"
        return tbname.lower()

    def reverse_pointtype(self, tb, cmps, rounds):
        txt = self.primaryscore
        trans = {
            "mpoints": "gpoints",
            "gpoints": "mpoints",
            "mmpoints": "ggpoints",
            "mgpoints": "gmpoints",
            "gmpoints": "mgpoints",
            "ggpoints":"mmgpoints"
        }
        tb["pointtype"] = trans.get(txt, txt)
        return "points"

    def parse_tiebreak(self, order, txt):
        # BH@23:IP/C1-P4F
        pointtrans = {
            "MP": "mpoints",
            "GP": "gpoints",
            "MM": "mmpoints",
            "MG": "mgpoints",
            "GM": "gmpoints",
            "GG": "ggpoints",
        }
        txt = txt.upper()
        comp = txt.replace("!", "/").replace("#", "/").split("/", 2)
        # if len(comp) == 1:
        #    comp = txt.split('-')
        nameparts = comp[0].split(":")
        nameyear = nameparts[0].split("@")
        nameyear.append("24")
        name = nameyear[0]
        year = int(nameyear[1])
        if self.primaryscore is not None:
            pointtype = self.primaryscore
        elif self.isteam:
            pointtype = "mpoints"
        else:
            pointtype = "points"
        if name == "MPTS":
            pointtype = "mpoints"
        if name == "GPTS":
            pointtype = "gpoints"

        if len(nameparts) == 2:
            pointtype = pointtrans[nameparts[1].upper()]
        if self.primaryscore is None and (name == "PTS" or name == "MPTS" or name == "GPTS"):
            self.primaryscore = pointtype
        # if name == 'MPVGP':
        #    name = 'PTS'
        #        pointtype = self.reverse_pointtype(self.primaryscore)

        tb = {
            "order": order,
            "name": name,
            "year": year,
            "pointtype": pointtype,
            "modifiers": {
                "low": 0,                   # cut low
                "high": 0,                  # cut high
                "plim": Decimal("50.0"),    # KS lim in percentage
                "nlim": Decimal("0.0"),     # KS lim in score
                "unr": self.unrated,        # Set unrated = <val> 
                "urd": False,               # D All unplayed is draw (not published) 
                "p4f": False,               # Treat all unplayed games as played
                "sws": False,               # Treat as Swiss tournament
                "fmo": False,               # Fore mode
                "rev": False,               # Reverse default order
                "ver": self.rulesversion,   # Set rule version, 1=2024, 2=2026
                "vun": False,               # Proposal of Roberto (not published)
            },
        }
        for mf in comp[1:]:
            mf = mf.upper()
            for index in range(0, len(mf)):
                if mf[index] == "C":
                        if mf[1:].isdigit():
                            tb["modifiers"]["low"] = int(mf[1:])
                elif mf[index] == "M":
                        if mf[1:].isdigit():
                            tb["modifiers"]["low"] = int(mf[1:])
                            tb["modifiers"]["high"] = int(mf[1:])
                elif mf[index] == "L":
                        scale = Decimal("1.0") if "." in mf else Decimal(0.5)
                        numbers = mf.replace(".", "")
                        if mf[1:].isdigit():
                            tb["modifiers"]["plim"] = Decimal(mf[1:])
                        elif mf[1] == "+" and numbers[2:].isdigit():
                            tb["modifiers"]["nlim"] = Decimal(mf[2:]) * scale
                        elif mf[1] == "-" and numbers[2:].isdigit():
                            tb["modifiers"]["nlim"] = -Decimal(mf[2:]) * scale
                elif mf[index] == "K":
                        if mf[1:].isdigit():
                            tb["modifiers"]["nlim"] = Decimal(mf[1:])
                elif mf[index] == "D":
                        tb["modifiers"]["urd"] = True
                elif mf[index] == "U":
                        tb["modifiers"]["unr"] = int(mf[1:])
                elif mf[index] == "P":
                        tb["modifiers"]["p4f"] = True
                elif mf[index] == "F":
                        tb["modifiers"]["fmo"] = True
                elif mf[index] == "R":
                        tb["modifiers"]["rev"] = True
                elif mf[index] == "S":
                        tb["modifiers"]["sws"] = True
                elif mf[index] == "V":
                        ver = int(mf[1:]) if len(mf[1:]) else max(self.TIEBREAK_RULES.keys()) 
                        if ver > 2000:
                            ver = 2 if ver == 2026 else 1
                        else:
                            ver = 1 if ver == 1 else 2 
                        tb["modifiers"]["ver"] = ver
                elif mf[index] == "N":
                        tb["modifiers"]["vun"] = True
        if self.rr and not tb["modifiers"]["sws"]:  # Default for RR is to treat unplayed games as played
            tb["modifiers"]["p4f"] = True
        return tb

    def addval(self, cmps, tb, value):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        precision = 0
        for startno, cmp in cmps.items():
            cmp["tiebreakScore"].append(cmp["tbval"][prefix + value]["val"])
            cmp["tiebreakDetails"].append(cmp["tbval"][prefix + value])
            if isinstance(cmp["tbval"][prefix + value]["val"], Decimal):
                (s, n, e) = cmp["tbval"][prefix + value]["val"].as_tuple()
                precision = min(precision, e)
        tb["precision"] = -precision

    # -------------------------------
    # Average
    
    def compute_average_of_buchholz(self, tb, cmps, rounds):
        tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, rounds)
        tbname = self.compute_average(tb, "bh", cmps, rounds, True, "0.01")  # 0.01 => two decimals
        return tbname

    def compute_average_rating_performance(self, tb, cmps, rounds):
        tbname = self.compute_ratingperformance(tb, cmps, rounds)
        tbname = self.compute_average(tb, "tpr", cmps, rounds, True, "1.") # 1.0 => no decimals
        return tbname

    def compute_average_perfect_performance(self, tb, cmps, rounds):
        tbname = self.compute_ratingperformance(tb, cmps, rounds)
        tbname = self.compute_average(tb, "ptp", cmps, self.currentround, True, "1.") # 1.0 => no decimals
        return tbname



    def compute_average(self, tb, name, cmps, rounds, ignorezero, norm):
        (scorename, points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        tbname = tb["name"].lower()
        for startno, cmp in cmps.items():
            cmp["tbval"][prefix + tbname] = {"val": 0, "cut": []}
            sum = Decimal(0.0)
            num = 0
            for rnd, rst in cmp["rsts"].items():
                if rst["played"] and rst["opponent"] > 0 and rnd <= rounds:
                    opponent = rst["opponent"]
                    value = cmps[opponent]["tbval"][prefix + name]["val"]
                    if not ignorezero or value > 0:
                        num += 1
                        sum += value
                        self.addtbval(cmp["tbval"][prefix + tbname], rnd, value)
            val = sum / Decimal(num) if num > 0 else Decimal("0.0")
            cmp["tbval"][prefix + tbname]["val"] = val.quantize(Decimal(norm), rounding=ROUND_HALF_UP)
        return tbname

    # get_scoreinfo(self, tb, primary)
    # tb - tie break
    # primary or secondary score

    def get_scoreinfo(self, tb, primary):
        pos = 0 if primary else 1
        key = tb["pointtype"][pos]
        if not primary and (key != "g" and key != "m"):
            key = tb["pointtype"][0]
            if key == "g":
                key = "m"
            elif key == "m":
                key = "g"
        if key == "g":
                return ["game", "gpoints", self.gamescore, "gpoints_"]
        elif key == "m":
                return ["match", "mpoints", self.matchscore, "mpoints_"]
        else:
                return ["game", "points", self.gamescore, "points_"]

    def compute_tiebreak(self, tb):
        cmps = self.cmps
        tbname = tb["name"] 
        tiebreak = self.tiebreaklist[tbname] if tbname in self.tiebreaklist else self.tiebreaklist["NUL"]        
        tb["modifiers"]["rev"] = tb["modifiers"]["rev"] ^ tiebreak["rev"]
        tbname = tiebreak["func"](tb, cmps, self.currentround)
        
        """
        match tb["name"]:
            case "PTS" | "MPTS" | "GPTS":
                tbname = self.get_builtin(tb, cmps, self.currentround)
            case "MPVGP":
                tbname = self.reverse_pointtype(tb, cmps, self.currentround)
            case "SNO" | "RANK" | "RND":
                tb["modifiers"]["reverse"] = False
                tbname = self.get_builtin(tb, cmps, self.currentround)
            case "DF": 
                tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
            case "DE":
                tb["modifiers"]["reverse"] = False
                tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
            case "EDE" | "EDEC" | "EDET" | "EDEB" | "EDEBT" | "EDEBB":
                tb["modifiers"]["reverse"] = False
                tbname = self.compute_ext_direct_encounter(tb, cmps, self.currentround)
            case "WIN" | "WON" | "BPG" | "BWG" | "GE" | "REP" | "RIP" | "VUR" | "NUM" | "COP" | "COD" | "CSQ" | "RTG":
                tbname = self.get_builtin(tb, cmps, self.currentround)
            case "PS":
                tbname = self.compute_progressive_score(tb, cmps, self.currentround)
            case "KS":
                tbname = self.compute_koya(tb, cmps, self.currentround)
            case "BH" | "FB" | "SB" | "ABH" | "AFB":
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
            case "AOB":
                tbname = self.compute_average_of_buchholz(tb, cmps, self.currentround)
            case "ARO" | "TPR" | "PTP":
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
            case "APRO":
                tbname = self.compute_average_rating_performance(tb, cmps, self.currentround)
            case "APPO":
                tbname = self.compute_average_perfect_performance(tb, cmps, self.currentround)
            case "ESB" | "EMMSB" | "EMGSB" | "EGMSB" | "EGGSB":
                tbname = self.compute_ext_sonneborn_berger(tb, cmps, self.currentround)
            case "BC":
                tb["modifiers"]["reverse"] = False
                tbname = self.compute_boardcount(tb, cmps, self.currentround)
            case "TBR" | "BBE":
                tb["modifiers"]["reverse"] = False
                tbname = self.compute_top_bottom_board(tb, cmps, self.currentround)
            case "SSSC":
                tbname = self.compute_score_strength_combination(tb, cmps, self.currentround)
            case "STD":
                tbname = self.compute_std(tb, cmps, self.currentround)
            case "ACC":
                tbname = self.compute_acc(tb, cmps, self.currentround)
            case "FLT":
                tbname = self.compute_flt(tb, cmps, self.currentround)
            case "RFP":
                tbname = self.compute_rfp(tb, cmps, self.currentround)
            case "TOP":
                tbname = self.compute_top(tb, cmps, self.currentround)
            case _:
                tbname = None
                return
        """
        
        self.tiebreaks.append(tb)
        index = len(self.tiebreaks) - 1
        self.addval(cmps, tb, tbname)
        reverse = 1 if "rev" in tb["modifiers"] and not tb["modifiers"]["rev"] else -1
        self.rankorder = sorted(self.rankorder, key=lambda cmp: (cmp["rank"], cmp["tiebreakScore"][index] * reverse, cmp["cid"]))
        rank = 1
        val = self.rankorder[0]["tiebreakScore"][index]
        for i in range(1, len(self.rankorder)):
            rank += 1
            if self.rankorder[i]["rank"] == rank or self.rankorder[i]["tiebreakScore"][index] != val:
                self.rankorder[i]["rank"] = rank
                val = self.rankorder[i]["tiebreakScore"][index]
            else:
                self.rankorder[i]["rank"] = self.rankorder[i - 1]["rank"]
