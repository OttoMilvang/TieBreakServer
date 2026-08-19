# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 16:26:22 2025

@author: Otto
"""
from decimal import Decimal
from gacrux.gacruxexeptions import GacruxInputError
from gacrux import scoresystem




class games2matches():

    
    def __init__(self, parent, tournament, options):
        self.parent = parent
        self.scores = parent.scores
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
        cteam[0] = 0
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
            wt = self.parent.get_result_cid(tmatch, "white")
            bt = self.parent.get_result_cid(tmatch, "black")
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
            wt = cteam[self.parent.get_result_cid(game, "white")] if "white" in game else 0
            bt = cteam[self.parent.get_result_cid(game, "black")] if "black" in game else 0
            if wt > bt:
                index = str(rnd) + "-" + str(wt) + "-" + str(bt)
            else:
                index = str(rnd) + "-" + str(bt) + "-" + str(wt)
            if wt > 0 and bt > 0:
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
                "white": {"cid": bye["competitor"]},
                "black": None,
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
                "white": {"cid": forfeited["white"]},
                "black": {"cid": forfeited["black"]},
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
                        "white": {"cid": int(p1)},
                        "black": None,
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
                (rnd, teama, teamb) = key.split("-")
                for teamx in [teama, teamb]:
                    tkey = rnd + "-" + teamx
                    teamno = int(teamx)
                    if teamno > 0:
                        tkey = rnd + "-" + teamx
                        tmatches[tkey] = {
                            "id": tmatch["id"], 
                            "games": [gameid for gameid in tmatch["games"] \
                                    if cteam.get(self.parent.get_result_cid(cgames[gameid], "white"), 0) == teamno \
                                    or cteam.get(self.parent.get_result_cid(cgames[gameid], "black"), 0) == teamno],
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
            (rnd, teama) = key.split("-")
            teamno = int(teama)
            a = str(tmatch["games"])
            # print("A", key, a)
            tmatch["games"] = [game["id"] for game in sorted([cgames[game] for game in tmatch["games"]], 
                    key=lambda game: (
                        game["black"] == 0 and game["wResult"] == "Z" or game["white"] == 0 and game["bResult"] == "Z" , 
                        (cplayer[self.parent.get_result_cid(game, "white")] if cteam[self.parent.get_result_cid(game, "white")] == teamno else cplayer[self.parent.get_result_cid(game, "black")]).get("order", 0))
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
            if key not in tmatches:
                err = f"Error in Out-of-order record (300), round {rnd}, team {team1}-{team2}, No such match found"
                self.parent.put_status(431, err)
                raise GacruxInputError(err)
            tmatch = tmatches[key]
            zgame = {'id': 0, 'round': rnd, 'white': {'cid': 0}, 'black': {'cid': 0}, 'played': False, 'rated': False, 'wResult': 'Z', 'bResult': 'Z', 'board': 0}
            games = [cgames[game] if game > 0 else zgame.copy() for game in tmatch["games"]]
            sortedgames = [None]*teamsize
            unsortedgames = []
            for i in range(teamsize):
                if i >= len(ooo["order"]):
                    err = f"Error in Out-of-order record (300), round {rnd}, {team1}-{team2} has only {len(ooo['order'])} players, but teamSize is {teamsize}"
                    self.parent.put_status(431, err)
                    raise GacruxInputError(err)
                player = ooo["order"][i]
                if player > 0:
                    playergames = [game for game in games if self.parent.get_result_cid(game, "white") == player or self.parent.get_result_cid(game, "black") == player]
                    if len(playergames) == 0:
                        err = f"Error in Out-of-order record (300), round {rnd}, team {team1} has no player {player}"
                        self.parent.put_status(431, err)
                        raise GacruxInputError(err)
                    playergames[0]["board"] = i + 1
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
            (rnd, teama, teamb) = key.split("-")
            if tmatch.get("black", -1) != 0 and int(teamb) != 0:
                games1 = tmatches[rnd + "-" + teama]["games"][:teamsize]
                games2 = tmatches[rnd + "-" + teamb]["games"][:teamsize]

                if "black" in tmatch:  # decide color
                    white = self.parent.get_result_cid(tmatch, "white")
                    black = self.parent.get_result_cid(tmatch, "black")
                else: 
                    for game in range(teamsize):  # Go through games2, find same game in game1
                        if games2[game] != 0 and games2[game] in games1: 
                            cgame = cgames[games2[game]]
                            wcol = self.tindex[seq[game % len(seq)]]  # Team with wcol is white 
                            bcol = "black" if wcol == "white" else "white"
                            white = cteam[self.parent.get_result_cid(cgame, wcol)]
                            black = cteam[self.parent.get_result_cid(cgame, bcol)]
                            tmatch.update({"white": {"cid": white}, "black": {"cid": black}})
                            break
                    else:
                        # unable to decide color
                        white = black = 0
                        tmatch.update({"white": {"cid": white}, "black": None})

                tmatch["games"] = []
                for game in range(teamsize): 
                    game2 = games2[0] if len(games2) else 0 
                    games2 = games2[1:]
                    if game2 != 0 and game2 in games1:
                        tmatch["games"].append(game2)
                        games1.remove(game2)
                    else:
                        gamelist = [game for game in games1 if game == 0 or game not in games2]
                        if len(gamelist) == 0:
                            err = f"Error in teams, round {rnd}, {teama}-{teamb} has only {len( tmatch['games'])} games, but teamSize is {teamsize}"
                            self.parent.put_status(431, err)
                            self.parent.put_status(431, "Add 300 Out-of-order records to solve this")
                            raise GacruxInputError(err + ". Add 300 Out-of-order records to solve this")
                        
                        game1 = gamelist[0]
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
                            # now we have two games, both White, find the correct white and update it with results from the other game
                            if cteam[self.parent.get_result_cid(wgame, "white")] != self.parent.get_result_cid(tmatch, wcol):
                                wgame, bgame = bgame, wgame
                            if wgame["black"] is None:
                                wgame["black"] = {"cid": self.parent.get_result_cid(bgame, "white")}
                            else:
                                wgame["black"].update({"cid": self.parent.get_result_cid(bgame, "white")})
                            wgame.update({"bResult": bgame["wResult"]}) 
                            tmatch["games"].append(wgame["id"])
                            self.tournament["gameList"].remove(bgame)
                for board, game in enumerate(tmatch["games"]): 
                    if game in cgames:
                        cgames[game]["board"] = board + 1 

            elif "white" not in tmatch:
                w0 = self.parent.get_result_cid(cgames[tmatch["games"][0]], "white")
                tmatch.update({"white": {"cid":  cteam[w0]}, "black": None, "played": False})
                # print("R", tmatch)
    # Decide score
        
    
    def decide_score(self):
        matches = self.matches 
        cgames = self.cgames
        cteam = self.cteam
        teamsize = self.tournament["teamSize"]
        seq = self.tournament.get("teamSequence", "WB")
        scores = self.scores

        for key, tmatch in matches.items():
            (rnd, teama, teamb) = key.split("-")
            arg = int(teama)
            games = [cgames[game] for game in tmatch["games"] if game in cgames]
            points = {"white": Decimal("0.0"), "black": Decimal("0.0")}
            if len(games) > 0:
                whitecid = self.parent.get_result_cid(tmatch, "white")
                blackcid = self.parent.get_result_cid(tmatch, "black")
                played = False
                ind = 0
                preres = None
                # print('GEO:', games)
                for game in range(teamsize):
                    ind += 1
                    if game >= len(games):
                        continue
                    cgame = games[game]
                    # wcol = self.tindex[seq[game % len(seq)]]  # Team with wcol is white (wrong) 
                    wcol = "white" if cteam[self.parent.get_result_cid(cgame, "white")] == whitecid else "black"
                    bcol = "black" if wcol == "white" else "white"
                    played = played or cgame["played"]
                    points[wcol] += scores.get_score(self.tournament, "game", cgame["wResult"])
                    points[bcol] += scores.get_score(self.tournament, "game", cgame.get("bResult", "Z"))
                tmatch["played"] = played
            if self.parent.get_result_cid(tmatch, "black") > 0:
                loss = "L" if played else "Z"
                if points["white"] > points["black"]:
                    tmatch.update({"wResult": "W", "bResult": loss})
                elif points["white"] < points["black"]:
                    tmatch.update({"wResult": loss, "bResult": "W"})
                elif points["white"] > 0 and points["black"] is not None:
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

        for key, tmatch in self.matches.items():
            if tmatch["round"] != rnd:
                rnd = tmatch["round"]
                board = 0
            board += 1
            tmatch["board"] = board
            self.append_result(self.tournament["matchList"], tmatch)
        # json_output('c:/temp/nmatches.json', tournament['matchList'])
        # json_output('c:/temp/ngames.json', tournament['gameList'])



