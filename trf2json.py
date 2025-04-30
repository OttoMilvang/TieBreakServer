# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
import time
from decimal import Decimal

import berger
import chessjson
import helpers


class trf2json(chessjson.chessjson):

    # Read trf into a JSON for Chess data structure
    
    trfrecords = [ 
        {'id': '###', 'desc': 'Comments' },
        {'id': '012', 'desc': 'Tournament Name' },
        {'id': '022', 'desc': 'City' },
        {'id': '032', 'desc': 'Federation' },
        {'id': '042', 'desc': 'Date of start' },
        {'id': '052', 'desc': 'Date of end' },
        {'id': '062', 'desc': 'Number of players' },
        {'id': '072', 'desc': 'Number of rated players' },
        {'id': '082', 'desc': 'Number of teams' },
        {'id': '092', 'desc': 'Type of tournament' },
        {'id': '102', 'desc': 'Chief Arbiter' },
        {'id': '112', 'desc': 'Deputy Chief Arbiter' },
        {'id': '122', 'desc': 'Allotted times per moves/game' },
        {'id': '132', 'desc': 'Dates of the round' },
        {'id': '142', 'desc': 'Number of rounds' },
        {'id': '152', 'desc': 'Initial-colour' },
        {'id': '162', 'desc': 'Scoring point system for individuals' },
        {'id': '172', 'desc': 'Encoded Starting Rank Method' },
        {'id': '192', 'desc': 'Encoded Type Of Tournament' },
        {'id': '202', 'desc': 'FIDE Tie-Breaks used to break ties' },
        {'id': '212', 'desc': 'FIDE Tie-Breaks used to define standings' },
        {'id': '222', 'desc': 'Encoded Time Control' },
        {'id': '352', 'desc': 'Colour sequence (W or B) for boards in team competitions' },
        {'id': '362', 'desc': 'Scoring point system for teams' },
        {'id': '001', 'desc': 'Player section' },
        {'id': 'FID', 'desc': 'National Rating Support' },
        {'id': '310', 'desc': 'Team section' },
        {'id': '013', 'desc': 'Team section' },
        {'id': '250', 'desc': 'Accelerated Round' },
        {'id': '260', 'desc': 'Prohibited pairings' },
        {'id': '240', 'desc': 'Bye section HPB and FPB' },
        {'id': '320', 'desc': 'Bye section PAB' },
        {'id': '330', 'desc': 'Forfeited matches' },
        {'id': '300', 'desc': 'Out of order' },
        {'id': '299', 'desc': 'Abnormal Assignment points' },
        {'id': '801', 'desc': 'Informative records for teams' },
        {'id': '802', 'desc': 'Informative records for teams' },
        {'id': 'XXR', 'desc': 'Nuber of rounds' },
        {'id': 'XXZ', 'desc': 'Will not meet' },
    ]


    

    # constructor function
    def __init__(self):
        super().__init__()
        self.chessjson["origin"] = "trf2json ver. 1.03"
        self.event["ratingLists"] = [{"listName": "TRF"}]
        self.cteam = {}  # pointer from cid-player to cid-team
        self.cboard = {}
        self.p001 = {}
        self.byelist = []
        self.forfeitedlist = []
        self.ooolist = []
        self.o001 = {}
        self.pcompetitors = {}  # pointer to player section competitors
        self.bcompetitors = {}  # pointer to team competitors, index id 1st board player cid
        self.tcompetitors = {}  # pointer to team section competitors, index is team cid
        self.cteam[0] = 0
        self.cboard[0] = 0
        self.gamescore = {
            "W": Decimal("1.0"), 
            "D": Decimal("0.5"),
            "L": Decimal("0.0"),
            "Z": Decimal("0.0"),
            "P": "W",
            "A": "D",
            "U": "Z",
            } 
        self.teamscore = {
            "W": Decimal("2.0"), 
            "D": Decimal("1.0"),
            "L": Decimal("0.0"),
            "Z": Decimal("0.0"),
            "P": "D",
            "A": "D",
            "U": "Z",
            } 
        self.national = {
            "federation": "FID",
            "mode": "FIDE",
            "func": helpers.rating_fide
        }

    # ==============================
    #
    # Read TRF file


    def parse_file(self, alines, verbose):
        now = time.time()
        #
        # Set up the structure
        #
        self.event["published"] = time.strftime("%Y-%m %d %H:%M:%S", time.localtime(now))
        self.event["tournaments"].append(
            {
                "tournamentNo": 1,
                "tournamentType": "Tournament",
                "ratingList": "TRF",
                "numRounds": 0,
                "currentRound": 0,
                "teamTournament": False,
                "rankOrder": ["PTS"],
                "competitors": [],
                "teamSize": 0,
                "gameScoreSystem": "game",
                "matchScoreSystem": "match",
                "gameList": [],
                "matchList": [],
                "timeControl": {"description" : "", "encoded": "" },
            }
        )
        #self.gamescore = {}
        #self.teamscore = {}
        self.gamescores = []  # used to calculate scoresystem
        self.teamscores = []  # used to calculate scoresystem
        lines = alines.replace("\r", "\n").split("\n")
        tournament = self.get_tournament(1)
        #
        # Pass 1
        # Read all lines into a structure sorted by trfid
        #        
        self.all_lines = {}
        lineno = 0
        for line in lines:
            # print(line)
            lineno += 1
            if len(line) >= 3:
                trfkey = line[0:3]
                if trfkey not in self.all_lines:
                    self.all_lines[trfkey] = []
                self.all_lines[trfkey].append({'no': lineno, 'txt': line})                            

        #
        # Update team tournament
        #        
        tournament["teamTournament"] = ('013' in self.all_lines or '310' in self.all_lines)
  
        #
        # Pass 2
        # Parse all lines in a spesific order
        #        
                
        for record in self.trfrecords:
            trfid = record["id"]
            if trfid in self.all_lines:
                for trfline in self.all_lines[trfid]:
                    lineno = trfline["no"]
                    line =  trfline["txt"]
                    try:
                        self.parse_line(tournament, record["id"], line)
                    except:
                        if verbose:
                            raise
                        self.put_status(401, "Error in trf-file, line " + str(lineno) + ", " + line)
                        return
                self.all_lines.pop(trfid)
            self.post_parse_line(tournament, trfid)

        for key, item in self.all_lines.items():
            #print('Line 179', key)
            #raise
            pass

        tournament["gameScoreSystem"] = self.update_gamescore(tournament, self.gamescores, "game")
        if tournament["teamTournament"]:
            # print(self.pcompetitors)
            # print(self.bcompetitors)
            # print(self.tcompetitors)
            if len(self.tcompetitors) == 0:
                self.prepare_team_section_013(tournament)
            else:
                self.prepare_team_section_310(tournament)
            # self.update_board_number(tournament, tournament['teamSection'], True)
            if tournament["teamSize"] == 0:
                tournament["teamSize"] = round(len(tournament["gameList"]) / len(tournament["matchList"]))
        else:
            self.prepare_player_section(tournament)
            self.update_board_number(tournament, "game", False)
        # helpers.json_output('-', self.byelist)
        self.update_bye_list(tournament)
        self.update_forfeited_list(tournament)
        # for m in sorted(tournament['matchList'], key=lambda match: (match['round'], match['white'])):
        #    print(m['round'], m['white'], m['black'], m['wResult'], m['played'])
        return

    def parse_line(self, tournament, trfkey, line):
                trfvalue = line[4:]
                match trfkey:  # noqa
                    case "###":
                        pass
                    case "001":
                        self.parse_trf_player(tournament, line)
                    case "012":
                        self.parse_trf_info("fullName", trfvalue)
                    case "013":
                        self.parse_trf_team(tournament, line, False)
                        tournament["teamTournament"] = True
                    case "022":
                        self.parse_trf_info("site", trfvalue)
                    case "032":
                        self.parse_trf_info("federation", trfvalue)
                    case "042":
                        self.parse_trf_info("startDate", helpers.parse_date(trfvalue))
                    case "052":
                        self.parse_trf_info("endDate", helpers.parse_date(trfvalue))
                    case "062":
                        # numplayers = int(trfvalue.split()[0])
                        pass
                    case "072":
                        # numrated = int(trfvalue)
                        pass
                    case "082":
                        # numteams = int(trfvalue)
                        pass
                    case "092":
                        tournament["tournamentType"] = trfvalue
                    case "102":
                        self.parse_trf_arbiter(True, line)
                    case "112":
                        self.parse_trf_arbiter(False, line)
                    case "122":
                        tournament["timeControl"]["description"] = trfvalue
                    case "132":
                        self.parse_trf_dates(tournament, line)
                    case "142":
                        self.parse_trf_numbrounds(tournament, line)
                    case "152":
                        self.parse_trf_initialcolor(tournament, line)
                    case "162":
                        self.parse_trf_scoresystem(tournament, line, False)
                    case "172":
                        self.parse_trf_nationalsupport(tournament, line)
                    case "192":
                        self.parse_trf_info("typeOfTournament", trfvalue)
                    case "202":
                        self.parse_tiebreaks(tournament, line, False)
                    case "212":
                        self.parse_tiebreaks(tournament, line, True)
                    case "222":
                        tournament["timeControl"]["encoded"] = trfvalue
                    case "240":
                        self.parse_trf_bye(tournament, line, 4)
                    case "250":
                        self.parse_trf_accellerated(tournament, line)
                    case "260":
                        self.parse_trf_prohibited(tournament, line)
                    case "300":
                        self.parse_trf_outoforder(tournament, line)
                    case "310":
                        self.parse_trf_team(tournament, line, True)
                        tournament["teamTournament"] = True
                    case "320":
                        self.parse_trf_pab(tournament, line)
                    case "330":
                        self.parse_forfeited(tournament, line)
                    case "352":
                        self.parse_colorsequence(tournament, line)
                    case "362":
                        self.parse_trf_scoresystem(tournament, line, True)
                    case "FID":
                        self.parse_trf_nationalrating(tournament, line)


                    case "XXR":
                        self.parse_trf_numbrounds(tournament, line)
                    case "XXZ":
                        self.parse_trf_absent(tournament, line)
                    case "XXS":
                        self.parse_trf_points(tournament, line)
                    case "XXC":
                        self.parse_trf_configuration(tournament, line)
                    case "XXA":
                        self.parse_trf_accelleratedv4(tournament, line)
                        # tt = tournament["tournamentType"].upper()
                    # Roberto
                    case "ACC":
                        self.parse_trf_acc(tournament, line)
                    case "TSE":
                        self.parse_trf_tse(tournament, line)
                    case "xxBBB":
                        tournament["teamSection"]["competitors"] = sorted(
                            tournament["teamSection"]["competitors"], key=lambda x: x["cid"]
                        )
                        self.tcompetitors = {elem["cid"]: elem for key, elem in self.tcompetitors.items()}
                        (self.cplayers, self.cteam) = self.build_tournament_teamcompetitors(tournament)
                    case "PAB":
                        self.parse_trf_npg(tournament, line, "P", Decimal("0.5"))
                    case "FPB":
                        self.parse_trf_npg(tournament, line, "F", Decimal("1.0"))
                    case "HPB":
                        self.parse_trf_npg(tournament, line, "H", Decimal("0.5"))
                    case "ZPB":
                        self.parse_trf_npg(tournament, line, "Z", Decimal("0.0"))
                    case "MFO":
                        self.parse_trf_forfeit(tournament, line, "W", "Z")
                    case "DFM":
                        self.parse_trf_forfeit(tournament, line, "Z", "Z")
                    # case 'OOO':
                    #    self.parse_trf_ooo(tournament, line)
                    # case 'XXX':
                    #    self.parse_test_xxx(tournament, line)
                    case "FFF":
                        # sys.exit(0)
                        pass

    def post_parse_line(self, tournament, trfkey):
        match trfkey:  # noqa
           case "001":
                self.pids = self.all_pids()
           case "172":
                trfid = self.national["federation"]
           case "013":
               teamsize = tournament["teamSize"]
               if tournament["teamTournament"] and (teamsize == 0):
                   countgames = [{} for i in range(tournament['currentRound'])]
                   teamsize = 0
                   for game in tournament['gameList']:
                       if game['played'] and 'white' in game and 'black' in game and game['white'] > 0 and game['black'] > 0:
                           rnd = game['round'] - 1
                           for col in ['white', 'black']:
                               player = game[col]
                               teamid = self.pcompetitors[game[col]]['teamId']
                               countgames[rnd][teamid] = countgames[rnd][teamid] + 1 if teamid in countgames[rnd] else 1
                               teamsize = max(teamsize, countgames[rnd][teamid])
                   # print(teamsize)
                   tournament["teamSize"] = teamsize

                                   
                                   
                                   
    def update_gamescore(self, tournament, equations, name):
        # score = helpers.solve_scoresystem(equations)  -- added record 162 to solve this
        
        eqok = False
        for version in ["TRF25", "TRF16"]:
            # print("+EQOK", eqok, version, "162" in self.all_lines,  not eqok and ("162" not in self.all_lines or version == "TRF25"))
            if not eqok and ("162" not in self.all_lines or version == "TRF25"):
                eqok = True
                score = self.gamescore if version == "TRF25" else helpers.solve_scoresystem(equations)
                # print(score)
                for eq in equations:
                    # print(eq)
                    if "pab" in eq and version == "TRF25":
                        eq["pab"]["wResult"] = score["P"]
                    checksum = Decimal("0.0")
                    for elem in ["W", "D", "L", "Z", "P", "U"]:
                        if elem in score:
                            num = eq[elem]
                            val = elem
                            while not isinstance(val, Decimal):
                                val = score[val]
                            checksum += (num * val)                    
                    # print(eq)
                    if eq['sum'] != checksum:
                       eqok = False
                # print("-EQOK", eqok, version, "162" in self.all_lines)
        if not eqok:
            raise

        self.gamescore = score
        scorename = None
        for name, scoreList in self.scoreLists.items():
            if all(key not in score or score[key] == scoreList[key] for key in ["W", "D", "L", "Z"]):
                scorename = name
                break
            if scorename is None:
                scorename = (
                    "my"
                    + "-"
                    + (str(score["W"]) if "W" in score else Decimal("0.0"))
                    + "-"
                    + (str(score["D"]) if "D" in score else Decimal("0.0"))
                    + "-"
                    + (str(score["L"]) if "L" in score else Decimal("0.0"))
                    + "-"
                    + (str(score["Z"] if "Z" in score else 0.0))
                )
                newlist = {"listName": scorename, "scoreSystem": score}
                self.event["scoreLists"].append(newlist)

        if scorename in self.scoreLists:
            # scoresystem = self.scoreLists[scorename]
            pass
        else:
            # scorelist = list(filter(lambda ss: ss["listName"] == scorename, self.event["scoreLists"]))
            pass
            # scoresystem = scorelist[0]["scoreSystem"]

        # if score != None and 'P' in score :
        #    pval = score['P']
        # elif 'P' in scoresystem:
        #   pval = scoresystem['P']
        # elif self.is_rr(tournament):
        #    pval = 'L'
        # else:
        #    pval = 'D' if isteam else 'W'

        if score is not None and "U" in score:
            uval = score["U"]
        else:
            uval = "D"

        for result in tournament[name + "List"]:
            # if result['wResult'] == 'P':
            #    result['wResult'] = pval
            if result["wResult"] == "U":
                result["wResult"] = uval
        return scorename

    def is_rr(self, tournament):
        if "rr" not in self.__dict__:
            tt = tournament["tournamentType"].upper()
            numcomp = len(tournament["competitors"])
            numrounds = tournament["numRounds"]
            rr = False
            if tt.find("SWISS") >= 0:
                rr = False
            elif tt.find("RR") >= 0 or tt.find("ROBIN") >= 0 or tt.find("BERGER") >= 0:
                rr = True
            elif numcomp == numrounds + 1 or numcomp == numrounds:
                rr = True
            elif numcomp == (numrounds + 1) * 2 or numcomp == numrounds * 2:
                rr = True
            self.rr = rr
        return self.rr

    def update_board_number(self, tournament, name, isteam):
        # is the tournament RR?
        scorename = tournament[name + "ScoreSystem"]

        results = {}

        for result in tournament[name + "List"]:
            rnd = result["round"]
            if rnd not in results:
                results[rnd] = []
            results[rnd].append(result)

        numcomp = len(tournament["competitors"])
        points = [Decimal("0.0")] * (numcomp + 1)

        # update each round
        for rnd, roundresults in results.items():
            if self.is_rr(tournament):
                self.update_rr_board_number(roundresults, numcomp, points)
            else:
                self.update_swiss_board_number(roundresults, numcomp, points)
            for result in roundresults:
                wScore = self.get_score(scorename, result, "white")
                bScore = 0
                points[result["white"]] += wScore
                if "bResult" in result:
                    bScore = self.get_score(scorename, result, "black")
                    points[result["black"]] += bScore

    def update_rr_board_number(self, roundresults, numcomp, points):
        rr = berger.bergertables(numcomp)
        n = rr["players"]
        cround = 0
        for result in roundresults:
            w = result["white"]
            b = result["black"] if "black" in result and result["black"] > 0 else n
            blku = berger.bergerlookup(rr, w, b)
            rnd = blku["round"] if blku["round"] < n else blku["round"] - n + 1
            if cround > 0 and cround != rnd:
                return self.update_swiss_board_number(roundresults, numcomp, points)  # not rr
            cround = rnd
            result["board"] = blku["board"]
        return

    def update_swiss_board_number(self, roundresults, numcomp, points):
        for result in roundresults:
            w = result["white"]
            b = result["black"] if "black" in result and result["black"] > 0 else 0
            c = 2 if b > 0 else 1
            result["rank"] = {"c": c, "w": points[w], "b": points[b], "r": min(w, b) if b > 0 else w}

        roundresults = sorted(
            roundresults,
            key=lambda result: (-result["rank"]["c"], -result["rank"]["w"], -result["rank"]["b"], result["rank"]["r"]),
        )
        for i in range(0, len(roundresults)):
            roundresults[i]["board"] = i + 1
            roundresults[i].pop("rank")

    def update_bye_list(self, tournament):
        # helpers.json_output('-', tournament['gameList'])
        trans = {"F": "W", "H": "D", "P": "D", "W": "W", "D": "D", "L": "L", "U": "U", "Z": "Z"}
        for bye in self.byelist:
            elemlist = list(
                filter(
                    lambda match: bye["round"] == match["round"] and match["white"] == bye["competitor"],
                    tournament["matchList"],
                )
            )
            if len(elemlist) == 0:
                raise
            elem = elemlist[0]
            elem["played"] = bye["type"] == "P"
            elem["wResult"] = trans[bye["type"]]
            if bye["matchPoints"] is not None:
                elem["wResult"] = self.points2score(tournament, True, bye["matchPoints"])
            games = list(
                filter(
                    lambda game: bye["round"] == game["round"] and bye["competitor"] == self.cteam[game["white"]],
                    tournament["gameList"],
                )
            )
            # if bye['round'] == 1 and bye['competitor'] == 3:
            #    print(bye, games)

            teamsize = min(tournament["teamSize"], len(games))
            gamePoints = bye["gamePoints"]
            if gamePoints is not None:
                gpab = ["D"] * teamsize
                scoresystem = self.scoreLists[tournament["gameScoreSystem"]]

                gp = scoresystem["D"] * tournament["teamSize"]
                for i in range(tournament["teamSize"]):
                    if gamePoints > gp:
                        gpab[i] = "W"
                        gp += scoresystem["W"] - scoresystem["D"]
                    if gamePoints < gp:
                        gpab[teamsize - i - 1] = "Z"
                        gp += scoresystem["Z"] - scoresystem["D"]
            else:
                gpab = [bye["type"]] * teamsize
            for game in games:
                if "board" in game and game["board"] > 0:
                    game["played"] = bye["type"] == "P"
                    game["wResult"] = trans[gpab[game["board"] - 1]]
            # if bye['round'] == 1 and bye['competitor'] == 3:
            #    print(bye, games)

    #    forfeited
    #    {
    #        'type': ftype,  'WZ'/'ZZ'/'ZW'
    #        'round': rnd,
    #        'white': whiteteam,
    #        'black': blackteam,
    #    }

    def update_forfeited_list(self, tournament):
        # helpers.json_output('-', tournament['gameList'])
        # trans = {"F": "W", "H": "D", "P": "D", "W": "W", "D": "D", "L": "L", "U": "U", "Z": "Z"}
        for forfeited in self.forfeitedlist:
            # print(forfeited)
            white = list(
                filter(
                    lambda match: forfeited["round"] == match["round"]
                    and (match["white"] == forfeited["white"] or match["black"] == forfeited["white"]),
                    tournament["matchList"],
                )
            )
            black = list(
                filter(
                    lambda match: forfeited["round"] == match["round"]
                    and (match["white"] == forfeited["black"] or match["black"] == forfeited["black"]),
                    tournament["matchList"],
                )
            )
            # print('White', white, 'Black', black)
            white = white[0]
            black = black[0]
            if white != black:
                white["black"] = max(black["white"], black["black"])
                white["wResult"] = forfeited["type"][0]
                white["bResult"] = forfeited["type"][1]
                tournament["matchList"] = list(
                    filter(lambda match: match["id"] != black["id"], tournament["matchList"])
                )
                # print(white)
            # print(len(tournament['matchList']))

            # "elem['played'] = bye['type'] == 'P'
            # elem['wResult'] = trans[bye['type']]
            # if bye['matchPoints'] is not None:
            #    elem['wGameResult'] = self.points2score(tournament, True, bye['matchPoints'])
            # games = list(filter(lambda game: bye['round']  == game['round' ] and bye['competitor'] == self.cteam[
            # game['white']]  ,tournament['gameList']))
            # if bye['round'] == 1 and bye['competitor'] == 3:
            #    print(bye, games)

            # teamsize = min(tournament['teamSize'], len(games))
            # gamePoints = bye['gamePoints']
            # if gamePoints is not None:
            #    gpab = ['D']*teamsize
            #    scoresystem = self.scoreLists[tournament['gameScoreSystem']]

            #    gp = scoresystem['D'] * tournament['teamSize']
            #    for i in range(tournament['teamSize']):
            #        if gamePoints > gp:
            #            gpab[i] = 'W'
            #            gp += scoresystem['W'] - scoresystem['D']
            #        if gamePoints < gp:
            #            gpab[teamsize - i - 1] = 'Z'
            #            gp += scoresystem['Z'] - scoresystem['D']
            # else:
            #    gpab = [bye['type']]*teamsize
            # for game in games:
            #    if 'board' in game and game['board'] > 0:
            #        game['played'] = bye['type'] == 'P'
            #        game['wResult'] = trans[gpab[game['board'] -1]]

    # ==============================
    #
    # Read TRF line

    def parse_trf_game(self, tournament, startno, currentround, sgame, score):
        if len(sgame.strip()) == 0:
            return None
        opponent = helpers.parse_int(sgame[0:4])
        color = sgame[5].lower()
        if color != "w" and color != "b" and color != "-" and color != " ":
            color = " "
        result = sgame[7].upper()
        points = "U"
        played = False
        rated = False
        match result:  # noqa
            case "1":
                points = "W"
                played = True
                rated = True
            case "=":
                points = "D"
                played = opponent > 0
                rated = opponent > 0
            case "0":
                points = "L"
                played = True
                rated = True
            case "U":
                points = "P"
                played = True
                rated = False
            case "W":
                points = "W"
                played = True
                rated = False
            case "D":
                points = "D"
                played = True
                rated = False
            case "L":
                points = "L"
                played = True
                rated = False
            case "?":
                points = "U"
                played = True
                rated = False
            case "+" | "F":
                points = "W"
                played = False
                rated = False
            case "H":
                points = "D"
                played = False
                rated = False
            case "-" | "Z" | " ":
                points = "Z"
                played = False
                rated = False

        if color == "b":
            white = opponent
            black = startno
        else:
            white = startno
            black = opponent
        # game = None
        # for item in section['results']:
        #    if item['round'] == currentround and item['white'] == white and item['black'] == black:
        #       game = item
        # if game == None:
        # self.numResults += 1
        score[points] = (score[points] if points in score else 0) + 1
        game = {"id": 0, "round": currentround, "white": white, "black": black, "played": played, "rated": rated}
        # section['results'].append(game)
        if color == "b":
            game["bResult"] = points
        else:
            game["wResult"] = points
        if result == "U":
            score["pab"] = game
        self.append_result(tournament["gameList"], game)
        return game

    def parse_trf_player(self, tournament, line):
        #    print('parse')
        fideName = line[14:47].rstrip()
        names = fideName.split(",")
        while len(names) < 2:
            names.append("")
        ftitle = title = line[10:13].strip()
        match title:  # noqa
            case "g":
                ftitle = "GM"
            case "m":
                ftitle = "IM"
            case "f":
                ftitle = "FM"
            case "c":
                ftitle = "CM"
            case "wg":
                ftitle = "WGM"
            case "wm":
                ftitle = "WIM"
            case "wf":
                ftitle = "WFM"
            case "wc":
                ftitle = "WCM"

        profile = {
            "id": 0,
            "lastName": names[0].strip(),
            "firstName": names[1].strip(),
            "sex": line[9:10],
            "birth": helpers.parse_date(line[69:79]),
            "federation": line[53:56].strip(),
            "fideId": helpers.parse_int(line[57:68]),
            "fideName": fideName,
            "rating": [helpers.parse_int(line[48:52])],
            "fideTitle": ftitle,
        }
        self.append_profile(profile)

        startno = helpers.parse_int(line[4:8])
        self.o001[startno] = line
        self.p001[startno] = line
        gamePoints = helpers.parse_float(line[80:84])
        # score accumulates number of wins, draws and losses and will compare it to sum in order to guess score system
        competitor = {
            "cid": startno,
            "profileId": self.numProfiles,
            "present": startno > 0,
            "gamePoints": gamePoints,
            "rank": helpers.parse_int(line[85:89]),
            "rating": helpers.parse_int(line[48:52]),
        }
        score = {"sum": gamePoints, "W": 0, "D": 0, "L": 0, "P": 0, "U": 0, "Z": 0}
        self.gamescores.append(score)
        # section['competitors'].append(competitor)
        self.pcompetitors[competitor["cid"]] = competitor
        linelen = len(line)
        currentround = 0
        lastplayed = 0
        lastpaired = 0
        for i in range(99, linelen + 1, 10):
            currentround += 1
            game = self.parse_trf_game(tournament, startno, currentround, line[i - 8 : i], score)
            # if startno == 31:
            #    print(currentround, game)
            if game is not None:
                if game["played"] and currentround > lastplayed:
                    lastplayed = currentround
                    if game["white"] > 0 and game["black"] > 0 and currentround > lastpaired:
                        lastpaired = currentround
        if lastplayed > tournament["numRounds"]:
            tournament["numRounds"] = lastplayed
        if lastpaired > tournament["currentRound"]:
            tournament["currentRound"] = lastpaired
        return 1

    def parse_trf_team(self, tournament, line, ext):
        linelen = len(line)
        cid = helpers.parse_int(line[4:7]) if ext else len(self.bcompetitors) + 1
        teamname = (line[8:40] if ext else line[4:36]).rstrip()
        # nickname = line[41:46].rstrip() if ext else ""
        # strength = helpers.parse_int(line[47:53]) if ext else 0
        matchPoints = helpers.parse_float(line[54:60]) if ext else Decimal("0.0")
        gamePoints = helpers.parse_float(line[61:67]) if ext else Decimal("0.0")
        rank = helpers.parse_int(line[68:71]) if ext else 0
        team = {"id": 0, "teamName": teamname, "players": []}
        teamid = self.append_team(team, 0)
        # players = []

        competitor = {
            "cid": cid,
            "teamId": teamid,
            "rank": rank,
            "present": True,
            "matchPoints": matchPoints,
            "gamePoints": gamePoints,
            "tieBreakScore": [],
            "cplayers": [],
        }
        # cplayers = tournament['playerSection']['competitors']
        # section['competitors'].append(competitor)
        board = 0
        for i in range(77 if ext else 40, linelen + 1, 5):
            board += 1
            pid = helpers.parse_int(line[i - 4 : i])
            if pid == 0:
                continue
            if ext:
                competitor["cplayers"].append(self.pcompetitors[pid])
            else:
                competitor["cplayers"].append(pid)
            # players.append(cplayers[pid-1]['profileId'])
            self.pcompetitors[pid]["teamId"] = teamid
            self.cboard[pid] = board
            # self.cteam[pid] = competitor['cid']
        if ext:
            self.tcompetitors[cid] = competitor
        else:
            self.bcompetitors[competitor["cplayers"][0]] = competitor

    def parse_trf_info(self, info, value):
        self.event["eventInfo"][info] = value
        return 1

    def parse_trf_dates(self, tournament, line):
        linelen = len(line)

        tournament["rounds"] = []
        currentround = 0
        for j in range(99, linelen + 1, 10):
            currentround += 1
            date = line[j - 8 : j]
            tournament["rounds"].append({"roundNo": currentround, "startTime": helpers.parse_date(date)})
        return

    def parse_trf_arbiter(self, is_ca, line):
        linelen = len(line.rstrip())
        if linelen == 3:
            return
        fideid = 0
        if linelen == 48:
            fideid = int(line[37:48])
            line = line[4:37].rstrip()
        else:
            line = line[4:].rstrip()
        nameparts = line.split(" ")
        sname = 0
        otitle = ""
        ename = len(nameparts) - 1
        if nameparts[0] == "IA" or nameparts[0] == "FA":
            sname = 1
            otitle = nameparts[0]
        lastname = nameparts[ename]
        firstname = " ".join(nameparts[sname:ename])
        profile = {
            "id": 0,
            "fideId": fideid,
            "firstName": firstname,
            "lastName": lastname,
            "sex": "u",
            "federation": "",
            "fideName": lastname + ", " + firstname,
            "fideOTitle": otitle,
        }
        pid = self.append_profile(profile)
        if "arbiters" not in self.event["eventInfo"]:
            self.event["eventInfo"]["arbiters"] = {"chiefArbiter": 0, "arbiters": []}
        if is_ca:
            self.event["eventInfo"]["arbiters"]["chiefArbiter"] = pid
        else:
            self.event["eventInfo"]["arbiters"]["arbiters"].append(pid)
        return

    def parse_tiebreaks(self, tournament, line, has_pts):
        pts = "" if has_pts else "PTS "
        self.tiebreaks = (pts + line[4:]).replace(",", " ").split(" ")
        tournament["rankOrder"] = self.tiebreaks

    def parse_colorsequence(self, tournament, line):
        seq = line[4:].strip()
        tournament["teamSize"] = len(seq)
        tournament["teamColor"] = seq[0].upper()
        tournament["teamSequence"] = seq.upper()

    def parse_trf_numbrounds(self, tournament, line):
        tournament["numRounds"] = helpers.parse_int(line[4:].rstrip())

    def parse_trf_initialcolor(self, tournament, line):
        tournament["topColor"] = line[4:].rstrip().upper()

    def parse_trf_scoresystem(self, tournament, line, isteam):
        scoresystem = self.teamscore if isteam else self.gamescore
        trans = {
            "W": "W",
            "D": "D",
            "L": "L",
            "P": "P",
            "A": "Z",
            "X": "A",
            }
        for pos in range(5, len(line)-1, 9):
            sym = line[pos].upper()
            pts = helpers.parse_float(line[pos+1:pos+5])
            if sym in trans:
                scoresystem[trans[sym]] =  pts
                # print(trans[sym], pts)
        p = list(filter(lambda result: scoresystem[result] == scoresystem['P'], ['W','D','L']))
        if len(p) > 0:
            scoresystem['P'] = p[0]
        u = list(filter(lambda result: scoresystem[result] == scoresystem['P'], ['W','D','L']))
        if len(u) > 0:
            scoresystem['U'] = u[0]
                
                

    def parse_trf_nationalsupport(self, tournament, line):
        national = self.national
        national["federation"] = line[4:7].strip()
        national["mode"] = line[8:13].strip()
        match national["mode"]:
            case "FIDE":
                national["func"] = helpers.rating_fide
            case "NRO":
                national["func"] = helpers.rating_nro
            case "FIDON":
                national["func"] = helpers.rating_fidon
            case "NIDOF":
                national["func"] = helpers.rating_nidof
            case "HBFN":
                national["func"] = helpers.rating_hbfn
            case "LBFN":
                national["func"] = helpers.rating_lbfn
            case "OTHER":
                national["func"] = helpers.rating_other
            case _:
                self.print_warning("parse_trf_nationalsupport: " + national["mode"] + " not matched")
        self.event["ratingLists"].append({"listName": national["federation"]})               

    def parse_trf_nationalrating(self, tournament, line):
        startno = helpers.parse_int(line[4:8])
        rating = helpers.parse_int(line[48:52])
        
        fideName = line[14:47].rstrip()
        names = fideName.split(",")
        while len(names) < 2:
            names.append("")
        title = line[10:13].strip()
        competitor = self.pcompetitors[startno]
        profile = self.pids[competitor["profileId"]]
        profile["lastName"] = names[0].strip()
        profile["lfirstName"] = names[1].strip()
        profile["sex"] = line[9:10]
        profile["rating"].append(rating)
        competitor["rating"] = self.national["func"](competitor["rating"], rating) 
        return 1



        
    def parse_trf_absent(self, tournament, line):
        for elem in line[4:].replace(",", " ").replace("/", " ").split(" "):
            num = helpers.parse_int(elem)
            if num > 0:
                self.pcompetitors[num]["present"] = False
        return

    def parse_trf_points(self, tournament, line):
        # TODO
        return

    def parse_trf_configuration(self, tournament, line):
        # TODO+4
        return

    def parse_trf_accellerated(self, tournament, line):
        if "acceleration" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["acceleration"] = acc
        matchPoints = helpers.parse_float(line[4:8])
        gamePoints = helpers.parse_float(line[9:13])
        firstround = helpers.parse_int(line[14:17])
        lastround = helpers.parse_int(line[18:21])
        if lastround == 0:
            lastround = firstround
        firstcompetitor = helpers.parse_int(line[22:26])
        lastcompetitor = helpers.parse_int(line[27:31]) if len(line) >= 31 else 0
        if lastcompetitor == 0:
            lastcompetitor = firstcompetitor
        matchScore = self.points2score(tournament, True, matchPoints)
        gameScore = self.points2score(tournament, False, gamePoints)

        value = {
            "matchScore": matchScore,
            "gameScore": gameScore,
            "firstRound": firstround,
            "lastRound": lastround,
            "firstCompetitor": firstcompetitor,
            "lastCompetitor": lastcompetitor,
        }
        tournament["acceleration"]["values"].append(value)
        return

    def parse_trf_prohibited(self, tournament, line):
        linelen = len(line)
        if "prohibited" not in tournament:
            pro = {"name": "Pro", "values": []}
            tournament["prohibited"] = pro
        firstround = helpers.parse_int(line[4:7])
        lastround = helpers.parse_int(line[8:11])
        if lastround == 0:
            lastround = firstround
            
        competitors = []
        for i in range(16, len(line) + 1, 5):
            competitor = helpers.parse_int(line[i - 4 : i])
            competitors.append(competitor)
            
        value = {
            "firstRound": firstround,
            "lastRound": lastround,
            "competitors": competitors,
        }
        tournament["prohibited"]["values"].append(value)
        return


    def parse_trf_outoforder(self, tournament, line):
        order = []
        rnd = helpers.parse_int(line[4:7])
        oooteam = helpers.parse_int(line[8:11])
        otherteam = helpers.parse_int(line[12:15])
        for i in range(20, len(line) + 1, 5):
            order.append(helpers.parse_int(line[i - 4 : i]))
        ooo = {"round": rnd, "oooteam": oooteam, "otherteam": otherteam, "order": order}
        self.ooolist.append(ooo)
        # print(ooo)

    def parse_trf_accelleratedv4(self, tournament, line):
        linelen = len(line)
        if "acceleration" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["acceleration"] = acc
        scorename = tournament["matchScoreSystem"] if tournament["teamTournament"] else tournament["gameScoreSystem"]
        scoresystem = self.scoreLists[scorename]
        competitor = helpers.parse_int(line[4:8])
        groups = {"W": [], "D": [], "L": [], "Z": []}
        currentround = 0
        # lastplayed = 0
        # lastpaired = 0
        for i in range(9, linelen - 3, 5):
            currentround += 1
            points = helpers.parse_float(line[i : i + 4])
            score = "Z"
            for s in groups.keys():
                if scoresystem[s] == points:
                    score = s
            groups[score].append(currentround)
        for s in ["W", "D", "L"]:
            start = 0
            cgroup = groups[s]
            c_len = len(cgroup)
            while start < c_len:
                stop = start
                while stop < c_len and cgroup[stop] - cgroup[start] == stop - start:
                    stop += 1
                value = {
                    "matchScore": s,
                    "gameScore": s,
                    "firstRound": cgroup[start],
                    "lastRound": cgroup[stop - 1],
                    "firstCompetitor": competitor,
                    "lastCompetitor": competitor,
                }
                tournament["acceleration"]["values"].append(value)
                start = stop
        return

    def parse_trf_pab(self, tournament, line):
        matchPoints = helpers.parse_float(line[4:8])
        gamePoints = helpers.parse_float(line[9:13])

        rnd = 1
        for i in range(17, len(line) + 1, 4):
            competitor = helpers.parse_int(line[i - 3 : i])
            if competitor > 0:
                gameResults = []
                totalPoints = gamePoints
                gamesleft = tournament['teamSize']
                for i in range(gamesleft, 0, -1):
                    if totalPoints > i * self.gamescore['D']:
                        gameResult = 'W'
                    elif totalPoints < i * self.gamescore['L']:
                        gameResult = 'L'
                    else:
                        gameResult = 'D'
                    gameResults.append(gameResult)
                    totalPoints -= self.gamescore[gameResult]                        
                for result in ['W', 'D', 'L', 'Z']:
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

    
    def parse_trf_bye(self, tournament, line, idsize):  
        # for 240 record idsize=4, for 330 record idsize=3
        trans = {"Z": "Z", "H": "D", "F": "W"}
        bye = line[4].upper()
        score = trans[bye]
        rnd = helpers.parse_int(line[6:9])
        for i in range(10+idsize, len(line) + 1, idsize+1):
            competitor = helpers.parse_int(line[i - idsize : i])
            if competitor > 0:
                self.byelist.append(
                    {
                        "type": bye,
                        "competitor": competitor,
                        "round": rnd,
                        "matchPoints": self.teamscore[score],
                        "matchScore" : score,
                        "gamePoints": self.gamescore[score] * tournament['teamSize'],
                        "gameResults": [score] * tournament['teamSize'],
                    }
                )

    def parse_forfeited(self, tournament, line):
        forfeit = line[4:6].upper()
        rnd = helpers.parse_int(line[7:10])
        whiteteam = helpers.parse_int(line[11:14])
        blackteam = helpers.parse_int(line[15:18])
        match forfeit:
            case "10" | "WL" | "WZ" | "+-":
                ftype = "WZ"
            case "00" | "LL" | "ZZ" | "--":
                ftype = "ZZ"
            case "01" | "LW" | "ZW" | "-+":
                ftype = "ZW"
        self.forfeitedlist.append(
            {
                "type": ftype,
                "round": rnd,
                "white": whiteteam,
                "black": blackteam,
            }
        )

    # Experimental

    def trf_update_game(self, tournament, game, trans):
        rnd = game["round"]
        score = {
            "-": Decimal("0.0"),
            "+": Decimal("1.0"),
            "Z": Decimal("0.0"),
            "H": Decimal("0.5"),
            "F": Decimal("1.0"),
            "U": Decimal("0.5"),
        }
        for player in ["white", "black"]:
            sno = game[player]
            if sno > 0:
                line = self.p001[sno]
                gp = helpers.parse_float(line[80:84])
                other = game["white"] if player == "black" else game["black"]
                # tno = self.cteam[sno]
                # if tno == 3:
                # print(line)
                col = player[0] if game["black"] > 0 else "-"
                oldres = line[88 + 10 * rnd]
                newres = trans[game[col + "Result"]] if col != "-" else trans[game["wResult"]]
                opp = "{0:4}".format(other) if other > 0 else "0000"
                line = line[: 81 + 10 * rnd] + opp + " " + col + " " + newres + line[89 + 10 * rnd :]
                if oldres != newres:
                    gp = gp - score[oldres] + score[newres]
                    line = line[:80] + "{0:4.1f}".format(gp) + line[84:]
                self.p001[game[player]] = line
                # if tno == 3:
                # print(line)
                # tno = self.cteam[sno]
                # team = self.tcompetitors[tno]
                # print(team)
                # sys.exit(0)

    def parse_trf_acc(self, tournament, line):
        if "acceleration" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["acceleration"] = acc
        points = helpers.parse_float(line[4:8])
        firstround = helpers.parse_int(line[9:12])
        lastround = helpers.parse_int(line[13:16])
        firstcompetitor = helpers.parse_int(line[17:21])
        lastcompetitor = helpers.parse_int(line[22:26])
        score = self.points2score(tournament, tournament["teamTournament"], points)
        value = {
            "matchScore": score,
            "gameScore": score,
            "firstRound": firstround,
            "lastRound": lastround,
            "firstCompetitor": firstcompetitor,
            "lastCompetitor": lastcompetitor,
        }
        tournament["acceleration"]["values"].append(value)

    def parse_trf_tse(self, tournament, line):
        # print(line)
        # linelen = len(line)
        tpn = helpers.parse_int(line[4:7])
        tp = helpers.parse_int(line[8:12])
        # nickname = line[13:18]
        # strength = helpers.parse_int(line[19:25])
        rank = helpers.parse_int(line[26:29])
        matchPoints = helpers.parse_int(line[30:34])
        gamePoints = helpers.parse_float(line[35:41])
        # team = self.tcompetitors[cid]
        competitor = {
            "cid": tpn,
            "teamId": 0,
            "rank": rank,
            "present": True,
            "matchPoints": matchPoints,
            "gamePoints": gamePoints,
            "tieBreakScore": [],
            "cplayers": [],
            "topPlayer": tp,
        }
        self.tcompetitors[tpn] = competitor

    def parse_trf_ooo(self, tournament, line):
        linelen = len(line)
        debug = line[0:27] == "?OOO   1   14    0   29   39"

        rnd = helpers.parse_int(line[4:7])
        nulls = 0
        pnums = []
        snums = []
        pteam = steam = 0
        trans = {"W": "+", "L": "-", "Z": "-"}
        for i in range(12, linelen + 1, 5):
            num = helpers.parse_int(line[i - 4 : i])
            pnums.append(num)
            if num > 0:
                nteam = self.cteam[num]
                if pteam == 0 or pteam == nteam:
                    pteam = nteam
                else:
                    steam = nteam
            else:
                nulls += 1
        pgames = []
        sgames = []
        glen = len(pnums) // 2
        if steam == 0:
            glen = len(pnums)
            for game in tournament["playerSection"]["results"]:
                if game["round"] == rnd:
                    wteam = self.cteam[game["white"]]
                    bteam = self.cteam[game["black"]]
                    if pteam in [wteam, bteam] and wteam > 0 and bteam > 0:

                        steam = wteam + bteam - pteam
        else:
            snums = pnums[len(pnums) // 2 :]
            pnums = pnums[: len(pnums) // 2]
        presults = tournament["playerSection"]["results"]
        for game in presults:
            if game["round"] == rnd:
                wteam = self.cteam[game["white"]]
                bteam = self.cteam[game["black"]]
                if pteam in [wteam, bteam]:
                    pgames.append(game)
                if steam in [wteam, bteam]:
                    sgames.append(game)
        if len(snums) == 0:
            cplayers = self.tcompetitors[steam]["cplayers"]
            for player in cplayers:
                game = list(filter(lambda game: game["white"] == player or game["black"] == player, sgames))[0]
                sgames.append(game)
            p = s = 0
            lastc = "b"
            for i in range(0, len(pnums)):
                c = pnums[i]
                if c > 0:
                    while pgames[p]["white"] != c and pgames[p]["black"] != c:
                        p = (p + 1) % len(pgames)
                    game = pgames[p]
                    lastc = "w" if game["white"] == c else "b"
                    while sgames[s % len(sgames)]["id"] != game["id"] and s < len(sgames) * (p + 1):
                        s += 1
                    if sgames[s % len(sgames)]["id"] == game["id"]:
                        snums.append(game["white"] + game["black"] - c)
                        s += 1
                    p = (p + 1) % len(pgames)
                else:
                    while pgames[p]["wResult"] != "Z" or pgames[p]["black"] != 0:
                        p = (p + 1) % len(pgames)

                    while sgames[s]["wResult"] != "W" or sgames[s]["black"] != 0:
                        s += 1
                    pplayer = pgames[p]["white"]
                    splayer = sgames[s]["white"]
                    game = {
                        "id": 0,
                        "round": rnd,
                        "white": splayer if lastc == "w" else pplayer,
                        "black": pplayer if lastc == "w" else splayer,
                        "played": False,
                        "rated": False,
                    }
                    presults.remove(pgames[p])
                    presults.remove(sgames[s])
                    pgames[p] = game
                    sgames[s] = game
                    # section['results'].append(game)
                    game["wResult"] = "W" if game["white"] == splayer else "L"
                    game["bResult"] = "W" if game["black"] == splayer else "L"
                    self.append_result(tournament["gameList"], game)
                    self.trf_update_game(tournament, game, trans)

        if debug:
            json.dump(pgames, sys.stdout, indent=2)
            json.dump(sgames, sys.stdout, indent=2)
        # print('OOQ ' + '{0:3}'.format(rnd)+ '{0:4}'.format(pteam) + ' ' + line[7:])
        for i in range(0, glen):
            num = pnums[i]
            game = list(filter(lambda game: game["white"] == num or game["black"] == num, pgames))
        return

    def parse_trf_npg(self, tournament, line, letter, points):
        linelen = len(line)
        trans = {"U": "U", "Z": "-", "H": "H", "F": "F", "-": "-"}
        trres = {"U": "D", "Z": "Z", "H": "D", "F": "W", "-": "L"}
        rnd = 0
        for i in range(7, linelen + 1, 4):
            rnd += 1
            num = helpers.parse_int(line[i - 3 : i])
            if num > 0:
                games = list(
                    filter(
                        lambda game: game["round"] == rnd and self.cteam[game["white"]] == num,
                        tournament["playerSection"]["results"],
                    )
                )
                nzgames = list(filter(lambda game: game["wResult"] != "Z", games))

                pteam = self.tcompetitors[num]
                ind = 0
                myletter = letter
                for cplayer in pteam["cplayers"]:
                    lgame1 = list(filter(lambda game: game["white"] == cplayer, nzgames))
                    lgame2 = list(filter(lambda game: game["white"] == cplayer, games))
                    game = lgame2[0] if len(lgame1) == 0 else lgame1[0]
                    if ind >= 4:
                        myletter = "-"
                    game["wResult"] = myletter
                    game["played"] = myletter == "U"
                    game["rated"] = False

                    self.trf_update_game(tournament, game, trans)
                    game["wResult"] = trres[myletter]
                    ind += 1

    def parse_trf_forfeit(self, tournament, line, wletter, lletter):
        # linelen = len(line)
        trans = {"W": "+", "L": "-", "Z": "-"}
        rnd = helpers.parse_int(line[4:7])
        win = helpers.parse_int(line[8:11])
        los = helpers.parse_int(line[12:15])
        # print('FF', rnd, win, los, wletter, lletter)
        wpteam = self.tcompetitors[win]
        lpteam = self.tcompetitors[los]
        ind = 0
        for i in range(0, len(wpteam["cplayers"])):
            # if ind == 4:
            #    break
            wp = wpteam["cplayers"][i]
            lp = lpteam["cplayers"][ind]
            game = {
                "id": 0,
                "round": rnd,
                "white": wp if i in [0, 2] else lp,
                "black": lp if i in [0, 2] else wp,
                "wResult": wletter if i in [0, 2] else lletter,
                "bResult": lletter if i in [0, 2] else wletter,
                "played": False,
                "rated": False,
            }
            presults = tournament["playerSection"]["results"]
            games = list(
                filter(lambda game: game["round"] == rnd and (game["white"] == wp or game["white"] == lp), presults)
            )
            # nzgames = list(filter(lambda game: game['wResult'] != 'Z', games))

            if len(games) == 2 and (games[0]["wResult"] == wletter or games[1]["wResult"] == wletter):
                for rgame in games:
                    presults.remove(rgame)
                self.append_result(presults, game)
                self.trf_update_game(tournament, game, trans)
                ind += 1
            games = list(
                filter(lambda game: game["round"] == rnd and (game["white"] == wp or game["white"] == lp), presults)
            )
            # print(games)

    def parse_test_xxx(self, tournament, line):
        gp = {}
        for key, line in self.p001.items():
            cid = self.cteam[helpers.parse_int(line[4:8])]
            gp2 = helpers.parse_float(line[80:84])

            gp[cid] = (gp[cid] + gp2) if cid in gp else gp2

        sum1 = sum2 = 0
        for key, competitor in self.tcompetitors.items():
            cid = competitor["cid"]
            gp1 = competitor["gamePoints"]
            gp2 = gp[cid]
            sum1 += gp1
            sum2 += gp2
        # if gp1 != gp2:
        #        print(cid, gp1, gp2)
        # print(sum1, sum2)

    # More

    def export_trf(self, params):
        # print(self.event)
        with open(params["output_file"], "w") as f:
            json.dump(self.event, f, indent=2)

    def prepare_player_section(self, tournament):
        tournament["competitors"] = sorted(list(self.pcompetitors.values()), key=lambda g: (g["cid"]))

    def prepare_team_section_013(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.bcompetitors.items():
            cplayers = competitor["cplayers"]
            competitor["cplayers"] = []
            for pcid in cplayers:
                cplayer = self.pcompetitors[pcid]
                competitor["cplayers"].append(cplayer)
                tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])

            self.tcompetitors[competitor["cid"]] = competitor
        # print(self.tcompetitors)
        self.prepare_team_section(tournament, False)

    def prepare_team_section_310(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.tcompetitors.items():
            if "topPlayer" in competitor:
                pcid = competitor["topPlayer"]
                competitor.pop("topPlayer")
                bcompetitor = self.bcompetitors[pcid]
                competitor["teamId"] = bcompetitor["teamId"]
                for pcid in bcompetitor["cplayers"]:
                    cplayer = self.pcompetitors[pcid]
                    competitor["cplayers"].append(cplayer)
                    tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])
            else:
                bcompetitor = competitor
                for pcid in competitor["cplayers"]:
                    # print(type(pcid))
                    cplayer = self.pcompetitors[pcid if isinstance(pcid, int) else pcid["cid"]]
                    tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])

                # print(self.pcompetitors[pcid])
        # print('TSE')
        self.prepare_team_section(tournament, True)

    def prepare_team_section_tse(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.tcompetitors.items():
            pcid = competitor["topPlayer"]
            competitor.pop("topPlayer")
            bcompetitor = self.bcompetitors[pcid]
            competitor["teamId"] = bcompetitor["teamId"]
            for pcid in bcompetitor["cplayers"]:
                cplayer = self.pcompetitors[pcid]
                competitor["cplayers"].append(cplayer)
                tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])
                # print(self.pcompetitors[pcid])
        # print('TSE')
        # print(self.tcompetitors)
        self.prepare_team_section(tournament, True)

    def prepare_team_section(self, tournament, haspointsupdated):
        # update players in teams

        cteam = self.cteam
        for cid, team in self.tcompetitors.items():
            for player in team["cplayers"]:
                cteam[player["cid"]] = cid

        self.merge_matches(tournament)

        tournament["matchScoreSystem"] = "match"
        # tournament['matchList'] = sorted(list(matches.values()), key=lambda g: (g['id']))
        tournament["competitors"] = sorted(list(self.tcompetitors.values()), key=lambda g: (g["cid"]))
        if not haspointsupdated:
            self.update_team_score(tournament)

    # merge matches build a match list based on a games list.
    #
    # Step 1. For each game, create a match identification, and add the game to a list.
    # Step 2. Find the board order and calculate the result.
    # Step 3. Add games to match list.

    def merge_matches(self, tournament):
        matchid = 0
        numboards = 0
        games = sorted(tournament["gameList"][:], key=lambda g: (g["round"]))
        matches = {}
        byes = {}
        cteam = self.cteam
        tindex = {"W": "white", "B": "black"}
        tother = {"W": "B", "B": "W"}
        # helpers.json_output('-', cplayer[1])

        cplayer = self.tcompetitors
        # Step 1
        # Create the identification,
        #     a game in round 3 between team 4 and 8 is identified by 3-8-4 regardless of white and black
        #     a game in round 6 with team 12 and no opponent is identified by 6-12-0

        for game in games:
            game["board"] = 0
            rnd = game["round"]
            wt = cteam[game["white"]]
            bt = cteam[game["black"]] if "black" in game and game["black"] > 0 else 0
            if wt > bt:
                index = str(rnd) + "-" + str(wt) + "-" + str(bt)
            else:
                index = str(rnd) + "-" + str(bt) + "-" + str(wt)
            if bt > 0:
                if not (index in matches):
                    matchid += 1
                    matches[index] = {"id": matchid, "games": []}
                matches[index]["games"].append(game)
                if len(matches[index]["games"]) > numboards:
                    numboards = len(matches[index]["games"])
            else:
                if not index in byes:
                    matchid += 1
                    byes[index] = {"id": matchid, "games": []}
                byes[index]["games"].append(game)

        #    json.dump(byes, f, indent=2)
        # helpers.json_output('c:/temp/matched.json', matches)
        # helpers.json_output('c:/temp/byes.json', byes)

        # Step 2
        # Calculate the team size
        # Normally this is already set

        teamsize = tournament["teamSize"]
        if teamsize == 0:
            for key, tmatch in matches.items():
                teamsize = max(teamsize, len(tmatch["games"]))
            tournament["teamSize"] = teamsize
        seq = (
            tournament["teamSequence"]
            if "teamSequence" in tournament
            else "".join(["WB"] * ((teamsize + 1) // 2))[0:teamsize]
        )
        # bseq =''.join([tother[elem] for elem in list(seq)])
        wcol = seq[0]

        # Step 3
        # Add Forfeited matches to the list
        # If outOfOrder records gives information, so use it
        # This is both for out of order games and for spare players

        for bye in self.byelist:
            key = (
                str(bye["round"])
                + "-"
                + str(bye["competitor"])
                + "-0"
            )
            if key not in matches:
                matchid += 1
                games = []
                gamescore = bye["gamePoints"]
                tcompetitor = self.tcompetitors[bye["competitor"]]
                for gameno in range(tournament["teamSize"]):
                    game = {"id": self.next_game(), 
                            "round": bye["round"], 
                            "white": tcompetitor["cplayers"][gameno]["cid"], 
                            "black": 0, 
                            "played": bye["type"] == "P", 
                            "rated": False, 
                            "wResult": bye["gameResults"][gameno], 
                            "board": gameno + 1
                            }
                    tournament["gameList"].append(game)
                    games.append(game)
                matches[key] = {"id": matchid, "white": bye["competitor"], "black": 0, "games": games}
            else:
                #TODO
                raise

        for forfeited in self.forfeitedlist:
            key = (
                str(forfeited["round"])
                + "-"
                + str(max(forfeited["white"], forfeited["black"]))
                + "-"
                + str(min(forfeited["white"], forfeited["black"]))
            )
            if key not in matches:
                matchid += 1
                for gameno in range(tournament["teamSize"]):
                    game = {"id": self.next_game(), "round": bye["round"], "white": 0, "black": 0, "played": True, "rated": False, "wResult": "D", "board": gameno + 1}
                    games.append(game)
                #matches[key] = {"id": matchid, "white": forfeited["white"], "black": forfeited["black"], "games": games}

        for ooo in self.ooolist:
            key = (
                str(ooo["round"])
                + "-"
                + str(max(ooo["oooteam"], ooo["otherteam"]))
                + "-"
                + str(min(ooo["oooteam"], ooo["otherteam"]))
            )
            if key not in matches:
                matchid += 1
                matches[key] = {"id": matchid, "games": []}

        # Step 4
        # Merge games from bye list into match list
        # Example
        # Before:
        # matches: 8-17-4 contains 3 games, byes: 8-17-0 contains two Z-byes, 8-4-0 contains one forfeited win and
        # one Z-bye
        # After:
        # matches: 8-17-4 contains 7 games, byes: none

        for key, value in matches.items():
            (rnd, p1, p2) = key.split("-")
            arg = int(p1)
            b1 = rnd + "-" + p1 + "-" + "0"
            b2 = rnd + "-" + p2 + "-" + "0"
            if b1 in byes:
                value["games"].extend(byes.pop(b1)["games"])
            if b2 in byes:
                value["games"].extend(byes.pop(b2)["games"])

        # with open('c:/temp/byes.json', 'w') as f:
        #    json.dump(byes, f, indent=2)

        """
        for key, tmatch in byes.items():
            nmatch = {
                'id': byes[key]['id'],
                'games': []
                }
            zero = []

            for game in tmatch['games']:
                if game['wResult'] == 'Z':
                    zero.append(game)
                else:
                    nmatch['games'].append(game)
            for i in range(0, len(zero)-1):
                for j in range(i+1, len(zero)):
                    if self.cboard[zero[j]['white']] < self.cboard[zero[i]['white']]:
                        (zero[i], zero[j]) = (zero[j], zero[i])
            while len(nmatch['games']) < teamsize:
                if len(zero) > 0:
                    game = zero[0]
                    zero.pop(0)
                else:
                    game = {
                         'id': chessjson.next_game(),
                         'round': rnd,
                         'white': 0,
                         'black': 0,
                         'played': false,
                         'rated': false,
                         'wResult': 'Z'
                         }
                nmatch['games'].append(game)
            matches[key] = nmatch
       """

        # Step 5
        # Add byes to match list

        for key in byes.keys():
            matches[key] = byes[key]

        # Step 6
        # Create a pointer dict tmatches such that this is an index for round and team
        # 8-17-4 got two pointers 8-17 and 8-4

        tmatches = {}
        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            tkey = rnd + "-" + p1
            tmatches[tkey] = tmatch
            if int(p2) > 0:
                tkey = rnd + "-" + p2
                tmatches[tkey] = tmatch

        # Step 7
        # Update out of order

        for ooo in self.ooolist:
            tmatch = tmatches[str(ooo["round"]) + "-" + str(ooo["oooteam"])]
            for i in range(teamsize):
                player = ooo["order"][i]
                if player > 0:
                    list(filter(lambda game: game["white"] == player or game["black"] == player, tmatch["games"]))[0][
                        "board"
                    ] = (i + 1)
                    # helpers.json_output('-', tmatch['games'])

        # Step 8
        # Sort games according to strength and previous ooo-list

        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            arg = int(p1)
            teams = {}
            for game in tmatch["games"]:
                for col in ["white", "black"]:
                    if game[col] > 0:
                        tcol = self.cteam[game[col]]
                        if tcol not in teams:
                            teams[tcol] = []
                        teams[tcol].append(game)
            # if int(rnd) == 12 and arg == 30:
            #    print('Teams', teams)
            for key, games in teams.items():
                # if int(rnd) == 12 and arg == 30:
                #    print('GamesA', games)
                # games = sorted(games, key=lambda game: (game['round'] == 0, game['round'], game['black'] == 0,
                # game['black'] == 0 and game['wResult'] == 'Z' )  )
                games = sorted(
                    games,
                    key=lambda game: (
                        game["board"] == 0,
                        game["board"],
                        game["black"] == 0 and game["wResult"] == "Z",
                        self.cboard[game["white"]] if self.cteam[game["white"]] == arg else self.cboard[game["black"]],
                    ),
                )

                # if arg == 11:
                #    for game in games:
                #        print('GamesB', rnd, game['white'], game['black'], game['board'] == 0, game['board'],
                #        game['black'] == 0 and game['wResult'] == 'Z', self.cboard[game['white']] if self.cteam[
                #        game['white']] == arg else self.cboard[game['black']] )

                for i in range(teamsize):
                    sg = list(filter(lambda game: game["board"] == i + 1 or game["board"] == 0, games))
                    # if int(rnd) == 12 and arg == 30:
                    #    print('TSg', sg)
                    sg[0]["board"] = i + 1
            # if int(rnd) == 12 and arg == 30:
            #    print('Teams', teams)

            if len(teams) == 2:
                (team1, team2) = teams.keys()
                forfeitedlist = list(
                    filter(
                        lambda forfeited: int(rnd) == forfeited["round"]
                        and (team1 == forfeited["white"] or team2 == forfeited["white"]),
                        self.forfeitedlist,
                    )
                )
                # print('Test', rnd, team1, team2)
                # if (False and team1 == 33 and team2 ==23):
                # print(forfeitedlist, self.forfeitedlist[0])
                #    pp = True

                if len(forfeitedlist) > 0:
                    forfeited = forfeitedlist[0]
                    if team2 == forfeited[tindex[wcol]]:
                        (team2, team1) = (team1, team2)
                else:
                    for i in range(teamsize):
                        col = seq[i]
                        pair = list(filter(lambda game: game["board"] == i + 1, tmatch["games"]))
                        if len(pair) < 2:
                            continue
                        (pairw, pairb) = pair
                        if pairw["id"] == pairb["id"]:
                            teamw = self.cteam(pairw["white"])
                            # teamb = self.cteam(pairb["black"])
                            if (wcol == "W") ^ (wcol == col) ^ (teamw == team1):
                                (team2, team1) = (team1, team2)
                                break

                for i in range(teamsize):
                    col = seq[i]
                    pair = list(filter(lambda game: game["board"] == i + 1, tmatch["games"]))
                    if len(pair) < 2:
                        continue
                    (pairw, pairb) = pair
                    if pairw["id"] != pairb["id"]:
                        teamw = self.cteam[pairw["white"]]
                        # teamb = self.cteam[pairb['black']]
                        if (wcol == "W") ^ (wcol == col) ^ (teamw == team1):
                            (pairb, pairw) = (pairw, pairb)
                        pairw["black"] = pairb["white"]
                        pairw["bResult"] = pairb["wResult"]
                        pairb["id"] = 0
                    # if self.cteam(pairw['white']) == team2
            tmatch["games"] = list(filter(lambda game: game["id"] != 0, tmatch["games"]))
        tournament["gameList"] = list(filter(lambda game: game["id"] != 0, tournament["gameList"]))

        # Step 9
        # Decide score

        # print('------------------')
        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            arg = int(p1)
            games = sorted(tmatch["games"], key=lambda game: (game["board"] == 0, game["board"]))
            # if int(rnd) == 12 and (arg == 28 or arg == 30):
            #    print ("Debug sorted", arg, games)
            scorename = tournament["gameScoreSystem"]
            scoresystem = self.scoreLists[scorename]
            if "P" not in scoresystem:
                scoresystem["P"] = "D"
            # helpers.json_output('-', games)
            white = self.cteam[games[0]["white"]]
            black = self.cteam[games[0]["black"]]
            tmatch["round"] = games[0]["round"]
            tmatch["white"] = white
            tmatch["black"] = black
            played = False
            wscore = 0
            bscore = 0
            # if (len(games) < numboards):
            #    print(numboards, key, tmatch, len(games))
            ind = 0
            preres = None
            # print('GEO:', games)
            for i in range(0, teamsize):
                ind += 1
                game = None
                g0 = list(filter(lambda game: "board" in game and game["board"] == ind, games))
                # if len(g0) ==  0:
                game = g0[0]
                # else:
                #    g1 =  list(filter(lambda game: game['black'] > 0 or game['wResult'] != 'L' or game['played'] ,
                #    games))
                #    if len(g1) > 0:
                #        game = g1[0]
                #    else:
                #        game = games[0]
                # game['board'] = ind
                if preres is None:
                    preres = game["wResult"]
                played = played or game["played"]
                # print('Sel', game)
                ws = self.get_score(scorename, game, "white")
                bs = self.get_score(scorename, game, "black") if "bResult" in game else 0
                if self.cteam[game["white"]] == white:
                    wscore += ws
                    bscore += bs
                else:
                    wscore += bs
                    bscore += ws
                games.remove(game)
                # if ind == 4:
                #    break
            tmatch["played"] = played

            wResult = wcol.lower() + "Result"
            bResult = tother[wcol].lower() + "Result"
            if black > 0:
                if wscore > bscore:
                    tmatch[wResult] = "W"
                    tmatch[bResult] = "L"
                elif bscore > wscore:
                    tmatch[wResult] = "L"
                    tmatch[bResult] = "W"
                elif wscore > 0 and bscore > 0:
                    tmatch[wResult] = "D"
                    tmatch[bResult] = "D"
                else:
                    tmatch[wResult] = "L"
                    tmatch[bResult] = "L"
            else:
                tmatch["wResult"] = preres

        # with open('c:/temp/matches.json', 'w') as f:
        #    json.dump(matches, f, indent=2)

        rnd = 0
        board = 0

        for key, tmatch in matches.items():
            if tmatch["round"] != rnd:
                rnd = tmatch["round"]
                board = 0
            board += 1
            tmatch["board"] = board
            tmatch.pop("games")
            self.append_result(tournament["matchList"], tmatch)
        # helpers.json_output('c:/temp/matches.json', tournament['matchList'])
        # helpers.json_output('c:/temp/games.json', tournament['gameList'])

    def update_team_score(self, tournament):
        for competitor in tournament["competitors"]:
            pass

    # Module test

    def dumpresults(self):
        cmps = self.event["status"]["competitors"]
        print(cmps)
        tcmps = {elem["startno"]: elem for elem in cmps}
        competitors = self.event["tournaments"][0]["teamSection"]["competitors"]
        for competitor in competitors:
            cid = competitor["cid"]
            sgp = 0
            for player in competitor["cplayers"]:
                trf = self.p001[player]
                country = trf[53:56]
                gp = helpers.parse_float(trf[80:84])
                sgp += gp

            print("{0:2}".format(cid) + "  - " + country)
            eq = (
                competitor["matchPoints"] == tcmps[cid]["tiebreakDetails"][0]["val"]
                and competitor["gamePoints"] == tcmps[cid]["calculations"][1]["val"]
            )
            print("TSE:", "{0:4.1f}".format(competitor["matchPoints"]), "{0:5.1f}".format(competitor["gamePoints"]))
            print("001:", "{0:4}".format(" "), "{0:5.1f}".format(sgp))
            print(
                "TBS:",
                "{0:4.1f}".format(tcmps[cid]["tiebreakDetails"][0]["val"]),
                "{0:5.1f}".format(tcmps[cid]["calculations"][1]["val"]),
                "" if eq else "*****",
            )
            print("Org:")
            for player in competitor["cplayers"]:
                trf = self.o001[player]
                print(trf)
            print("Mod:")
            for player in competitor["cplayers"]:
                trf = self.p001[player]
                print(trf)
            currentround = 0
            linelen = len(trf)
            line = "{0:89}".format(" ")
            for i in range(99, linelen + 1, 10):
                currentround += 1
                line += "{0:10.1f}".format(tcmps[cid]["tiebreakDetails"][0][currentround])
            print(line)
            currentround = 0
            line = "{0:89}".format(" ")
            for i in range(99, linelen + 1, 10):
                currentround += 1
                line += "{0:10.1f}".format(tcmps[cid]["tiebreakDetails"][1][currentround])
            print(line)

        print()
        for key, trf in self.p001.items():
            print(trf)


# ============== Module test ================


def dotest(name, details):
    print("==== " + name + " ====")
    root = "..\\..\\..\\..\\Nordstrandsjakk\\Turneringsservice\\"

    with open(root + name + "\\" + name + details + ".txt") as f:
        lines = f.read()

    tournament = trf2json()
    tournament.parse_file(lines, True)
    with open(root + name + "\\" + name + details + ".json", "w") as f:
        json.dump(tournament.event, f, indent=2)


def module_test():
    # dotest('escc2018')
    # dotest('h2023')
    dotest("lyn23", "-Rating-A-Lyn-FIDE")
    dotest("ngpl23", "-A-Langsjakk-FIDE")
    dotest("ngpl23", "-B-Langsjakk-FIDE")
    dotest("ngpl23", "-C-Langsjakk-FIDE")
    dotest("elite19-20", "-FIDE")
    dotest("Team-Example", "-013")
    dotest("Team-Example", "-TSE")
    dotest("nm_lag_19", "-Langsjakk-FIDE")
    dotest("test-half-point", "-Langsjakk-FIDE")
    dotest("test-half-point2", "-Langsjakk-FIDE")
