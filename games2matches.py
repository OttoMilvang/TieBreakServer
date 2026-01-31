# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 16:26:22 2025

@author: Otto
"""
from decimal import Decimal
import scoresystem




class games2matches():

    
    def __init__(self, score, tournament, options):
        self.score = score
        self.tournament = tournament
        self.cteam = {}
        self.cplayer = {0: {}}
        self.cgames = {}
        self.matchid = options.get("current_id", 0)
        self.numboards = tournament["teamSize"]
        self.games = sorted(tournament["gameList"][:], key=lambda g: (g["round"]))
        self.matches = {}
        self.byes = {}
        self.byelist = options.get("byelist", [])
        self.forfeitedlist = options.get("forfeitedlist", [])
        self.ooolist = options.get("ooolist", [])


    def merge_matches(self):
        self.tindex = {"W": "white", "B": "black"}
        self.tother = {"W": "B", "B": "W"}
        self.build_cpointers()
        self.sort_matches_to_matches_and_byes()
        self.sort_games_to_matches_and_byes()
        self.find_teamsize()
        self.add_byes()
        self.add_forfeited()
        self.add_ooo()
        self.merge_byes_into_matches()
        self.find_zpb()
        self.build_tmatches()
        self.sort_tmatches()
        self.sort_ooo()
        self.merge_tmatches()
        self.decide_score()
        return self.matches
        
    def get_current_id(self):
       return self.matchid
        
        # json_output('-', cplayer[1])

    # Build pointer

    def build_cpointers(self):
        tournament = self.tournament
        cteam = self.cteam
        cplayer = self.cplayer
        
        self.cgames = {game["id"]: game for game in tournament["gameList"]  }
        
        for team in tournament["competitors"]:
            for player in team["cplayers"]:
                cteam[player["cid"]] = team["cid"]
                cplayer[player["cid"]] = player



    # Create the identification,
    #   Matches are identified by "rnd-high-low" means that if team 4 meet team 8 in round 3
    #   all games will be sorted to "3-8-4", "3-8-0" and "3-4-0" regardless of white and black
    #   played games in matches["3-8-4"], and byes in byes["3-8-0"] and byes["3-4-0"]

    def sort_matches_to_matches_and_byes(self):
        matchList = self.tournament["matchList"]
        matches = self.matches
        byes = self.byes
        
        for tmatch in matchList:
            tmatch["board"] = 0
            tmatch["games"] = []
            rnd = tmatch["round"]
            wt = tmatch["white"]
            bt = tmatch["black"] if "black" in tmatch and tmatch["black"] > 0 else 0
            if wt > bt:
                index = str(rnd) + "-" + str(wt) + "-" + str(bt)
            else:
                index = str(rnd) + "-" + str(bt) + "-" + str(wt)
            if not (index in matches):
                if bt > 0:
                    matches[index] = tmatch
                else:
                    byes[index] = tmatch



    # Create the identification,
    #   Matches are identified by "rnd-high-low" means that if team 4 meet team 8 in round 3
    #   all games will be sorted to "3-8-4", "3-8-0" and "3-4-0" regardless of white and black
    #   played games in matches["3-8-4"], and byes in byes["3-8-0"] and byes["3-4-0"]

    def sort_games_to_matches_and_byes(self):
        matches = self.matches
        byes = self.byes
        cteam = self.cteam
        
        for game in self.games:
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
                    self.matchid += 1
                    matches[index] = {"id": self.matchid, 
                                      "round": rnd, 
                                      "games": []}
                matches[index]["games"].append(game["id"])
                self.numboards = max(self.numboards, len(matches[index]["games"]))
            else:
                if not index in byes:
                    self.matchid += 1
                    byes[index] = {"id": self.matchid, 
                                   "round": rnd, 
                                   "games": []}
                byes[index]["games"].append(game["id"])

   # Calculate the team size
   #    Normally this is already set

    def find_teamsize(self):
        tournament = self.tournament
        matches = self.matches
        teamsize = tournament["teamSize"]
        if teamsize == 0:
            for key, tmatch in matches.items():
                teamsize = max(teamsize, len(tmatch["games"]))
            tournament["teamSize"] = teamsize
        seq = tournament["teamSequence"] if "teamSequence" in tournament else "".join(["WB"] * ((teamsize + 1) // 2))[0:teamsize]
        # bseq =''.join([tother[elem] for elem in list(seq)])
        wcol = seq[0]
        tournament["teamSize"] = teamsize
 

    # Add byes to the byes list
 
    def add_byes(self):
        for bye in self.byelist:
            key = str(bye["round"]) + "-" + str(bye["competitor"]) + "-0"
            wres = bye["wResult"] if "wResult" in bye else "Z"
            byetrans = {"Z": "Z", "H": "D", "F": "W", "P": "P"  }
            wres = byetrans[bye["type"]]
            if key not in self.byes:
                self.matchid += 1
                # gamescore = self.scores.get_score(tournament, "match", bye["type"] + "G")

                self.byes[key] = {
                    "id": self.matchid, 
                    "games": [], 
                    "round": bye["round"], 
                }
                # print("Match", matches[key] )
            self.byes[key].update({
                "white": bye["competitor"], 
                "black": 0, 
                "played": bye["type"] == "P", 
                "wResult": wres,
                })

 

    # Add Forfeited matches to the list
    
    def add_forfeited(self):
        for forfeited in self.forfeitedlist:
            key = str(forfeited["round"]) + "-" + str(max(forfeited["white"], forfeited["black"])) + "-" + str(min(forfeited["white"], forfeited["black"]))
            if key not in self.matches:
                self.matchid += 1
                self.matches[key] = {"id": self.matchid, 
                                     "round": forfeited["round"], 
                                     "games": []}
            self.matches[key].update({
                "white": forfeited["white"], 
                "black": forfeited["black"], 
                "played": False, 
                "wResult": forfeited["type"][0],
                "bResult": forfeited["type"][1],
                })
    # If outOfOrder records gives information, so use it

    def add_ooo(self):
        for ooo in self.ooolist:
            key = str(ooo["round"]) + "-" + str(max(ooo["oooteam"], ooo["otherteam"])) + "-" + str(min(ooo["oooteam"], ooo["otherteam"]))
            if key not in self.matches:
                self.matchid += 1
                self.matches[key] = {"id": self.matchid, 
                                     "round": ooo["round"],
                                     "games": []}



    # Merge games from bye list into match list
    #   Example
    #   Before:
    #   matches: 8-17-4 contains 3 games, byes: 8-17-0 contains two Z-byes, 8-4-0 contains one forfeited win and
    #   one Z-bye
    #   After:
    #   matches: 8-17-4 contains 5 games, byes: none
    #   At the end move unhandled byse into matches

    def merge_byes_into_matches(self):
        matches = self.matches 
        byes = self.byes
        teamsize = self.tournament["teamSize"]
        for key, match in matches.items():
            (rnd, p1, p2) = key.split("-")
            bye1 = rnd + "-" + p1 + "-" + "0"
            bye2 = rnd + "-" + p2 + "-" + "0"

            games1 = byes.pop(bye1,{"games": []})["games"]
            games2 = byes.pop(bye2,{"games": []})["games"]
            #if  len(match["games"]) != teamsize:
            match["games"].extend(games1)
            match["games"].extend(games2)
        for key in byes.keys():
            matches[key] = byes[key]
         

    # Identify ZPB not listed in 
    #   8-17-4 got two pointers 8-17 and 8-4

    def find_zpb(self):
        matches = self.matches
        cteam = self.cteam
        cgames = self.cgames
        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            if len([game for game in tmatch["games"] if cgames[game]["black"] != 0 or cgames[game]["wResult"] != "Z"]) == 0:
                if "wResult" not in tmatch:
                    tmatch.update({
                        "white": int(p1), 
                        "black": 0, 
                        "played": False, 
                        "wResult": "Z",
                        })
            


    # Create a pointer dict tmatches such that this is an index for round and team
    #   8-17-4 got two pointers 8-17 and 8-4
    
    def build_tmatches(self):
        self.tmatches = tmatches = {}
        matches = self.matches
        cteam = self.cteam
        cgames = self.cgames
        for key, tmatch in matches.items():
            if tmatch.get("black", -1) != 0:
                (rnd, p1, p2) = key.split("-")
                for px in [p1, p2]:
                    tkey = rnd + "-" + px
                    ipx = int(px)
                    if ipx > 0:
                        tkey = rnd + "-" + px
                        tmatches[tkey] = {
                            "id": tmatch["id"], 
                            "games": [game for game in tmatch["games"] if cteam.get(cgames[game]["white"], 0) == ipx or cteam.get(cgames[game]["black"], 0) == ipx],
                        }                        
            else:
                tmatch["games"] = []
        
    # Sort tmatches
    #   For each tmatch sort games on scheduled game and then order in team

    def sort_tmatches(self):
        tmatches = self.tmatches 
        cgames = self.cgames
        cteam = self.cteam
        cplayer = self.cplayer
        for key, tmatch in tmatches.items():
            (rnd, p1) = key.split("-")
            p1 = int(p1)
            a = str(tmatch["games"])
            # print("A", key, a)
            tmatch["games"] = [game["id"] for game in sorted([cgames[game] for game in tmatch["games"]], 
                    key=lambda game: (
                        game["black"] == 0 and game["wResult"] == "Z", 
                        (cplayer[game.get("white", 0)] if cteam[game.get("white",0)] == p1 else cplayer[game.get("black", 0)]).get("order", 0))
                    )]
            b = str(tmatch["games"])
            # if (a!= b): print(a, b)

    # Sort_ooo
        # Add out ot order records

    def sort_ooo(self):
        tmatches = self.tmatches 
        teamsize = self.tournament["teamSize"]
        cgames = self.cgames
        for ooo in self.ooolist:
            rnd = ooo["round"]
            team1 = ooo["oooteam"]
            team2 = ooo["otherteam"]
            key = str(rnd) + "-" + str(team1)
            tmatch = tmatches[key]
            games = [cgames[game] for game in tmatch["games"]]
            sortedgames = [None]*teamsize
            unsortedgames = []
            for i in range(teamsize):
                player = ooo["order"][i]
                if player > 0:
                    [game for game in games if game["white"] == player or game["black"] == player][0]["board"] = i + 1
            for game in games:
                board = game['board']
                if board > 0:
                    sortedgames[board-1] = game 
                else:
                    unsortedgames.append(game)
            # for game in sortedgames: print('S', game)
            # for game in unsortedgames: print('U', game)
            for i in range(teamsize):
                if sortedgames[i] is None:
                    sortedgames[i] = unsortedgames[0] if len(unsortedgames) else {}
                    unsortedgames = unsortedgames[1:]
            tmatch["games"] = [game.get("id", 0) for game in sortedgames + unsortedgames]
            # for game in tmatch["games"]: print('E', cgames[game])

    # Merge_tmatches
        # For each tmatch, we now have two elements in tmatches, with white games, and black games.
        # Find correct pairs and save to matches

    def merge_tmatches(self):
        matches = self.matches 
        tmatches = self.tmatches 
        cgames = self.cgames
        cteam = self.cteam
        cplayer = self.cplayer
        teamsize = self.tournament["teamSize"]
        seq = self.tournament.get("teamSequence", "WB")
        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            if tmatch.get("black", -1) != 0 and int(p2) != 0:
                games1 = tmatches[rnd + "-" + p1]["games"][:teamsize]
                games2 = tmatches[rnd + "-" + p2]["games"][:teamsize]
                
                if "black" in tmatch:  # decide color
                    white = tmatch["white"]
                    black = tmatch["black"]
                else: 
                    for game in range(teamsize):  # Go through games2, find same game in game1
                        if games2[game] != 0 and games2[game] in games1: 
                            cgame = cgames[games2[game]]
                            wcol = self.tindex[seq[game % len(seq)]]  # Team with wcol is white 
                            bcol = "black" if wcol == "white" else "white"
                            white = cteam[cgame[wcol]]
                            black = cteam[cgame[bcol]]
                            tmatch.update({"white": white, "black": black})
                            break
                    else:
                        # unable to decide color
                        white = black = 0
                        tmatch.update({"white": white, "black": black})

                tmatch["games"] = []
                for game in range(teamsize): 
                    game2 = games2[0] if len(games2) else 0 
                    games2 = games2[1:]
                    if game2 != 0 and game2 in games1:
                        tmatch["games"].append(game2)
                        games1.remove(game2)
                    else:
                        game1 = [game for game in games1 if game == 0 or game not in games2][0]
                        games1.remove(game1)
                        wcol = self.tindex[seq[game % len(seq)]]  # Team with wcol is white 
                        bcol = "black" if wcol == "white" else "white"
                        if game1 == 0:
                            tmatch["games"].append(game2)
                        elif game2 == 0:
                            tmatch["games"].append(game1)
                        else:
                            wgame = cgames[game1]
                            bgame = cgames[game2]
                            if cteam[wgame["white"]] != tmatch[wcol]:
                                wgame, bgame = bgame, wgame
                            wgame.update({"black": bgame["white"], "bResult": bgame["wResult"]}) 
                            tmatch["games"].append(wgame["id"])
                            self.tournament["gameList"].remove(bgame)
                for board, game in enumerate(tmatch["games"]): 
                    cgames[game]["board"] = board + 1 
            elif "white" not in tmatch:
                w0 = cgames[tmatch["games"][0]]["white"]
                tmatch.update({"white": cteam[w0], "black": 0, "played": False})
                # print("R", tmatch)
    # Decide score
        
    
    def decide_score(self):
        matches = self.matches 
        cgames = self.cgames
        cteam = self.cteam
        teamsize = self.tournament["teamSize"]
        seq = self.tournament.get("teamSequence", "WB")
        score = self.score

        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split("-")
            arg = int(p1)
            games = [cgames[game] for game in tmatch["games"]]
            points = {"white": Decimal("0.0"), "black": Decimal("0.0")}
            if len(games) > 0:
                white = tmatch["white"]
                black = tmatch["black"]
                played = False
                ind = 0
                preres = None
                # print('GEO:', games)
                for game in range(teamsize):
                    ind += 1
                    cgame = games[game]
                    # wcol = self.tindex[seq[game % len(seq)]]  # Team with wcol is white (wrong) 
                    wcol = "white" if cteam[cgame["white"]] == white else "black"
                    bcol = "black" if wcol == "white" else "white"
                    played = played or cgame["played"]
                    points[wcol] += score.get_score(self.tournament, "game", cgame["wResult"])
                    points[bcol] += score.get_score(self.tournament, "game", cgame.get("bResult", "Z"))
                tmatch["played"] = played
            if tmatch["black"] > 0:
                loss = "L" if played else "Z"
                if points["white"] > points["black"]:
                    tmatch.update({"wResult": "W", "bResult": loss})
                elif points["white"] < points["black"]:
                    tmatch.update({"wResult": loss, "bResult": "W"})
                elif points["white"] > 0 and points["black"] > 0:
                    tmatch.update({"wResult": "D", "bResult": "D"})
                else:
                    tmatch.update({"wResult": loss, "bResult": loss})
            else:
                if "wResult" not in tmatch:
                    wr = cgames[tmatch["games"][0]]["wResult"]
                    tmatch["wResult"] = cgames[tmatch["games"][0]]["wResult"]
        # with open('c:/temp/matches.json', 'w') as f:
        #    json.dump(matches, f, indent=2)




    def p(self, game):
        print("g", game)

    def remaining(self):
        rnd = 0
        board = 0

        for key, tmatch in matches.items():
            if tmatch["round"] != rnd:
                rnd = tmatch["round"]
                board = 0
            board += 1
            tmatch["board"] = board
            self.append_result(tournament["matchList"], tmatch)
        # json_output('c:/temp/nmatches.json', tournament['matchList'])
        # json_output('c:/temp/ngames.json', tournament['gameList'])



