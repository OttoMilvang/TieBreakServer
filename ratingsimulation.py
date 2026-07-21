

import rating
from tournamentgenerator import tournamentgenerator  
import sys
import json
import os
import statistics
from helpers import *
from chessjson import chessjson
from trf2json import trf2json
from decimal import Decimal, ROUND_HALF_UP
from tiebreak import tiebreak
import version

# pip install matplotlib
# pip install numpy
# pip install scipy

import matplotlib.pyplot as plt
import numpy as np
import datetime
from scipy.stats import gaussian_kde
from matplotlib.ticker import MultipleLocator

KFACTOR40 = Decimal("40")
SIGMA40 = 64.0

KFACTOR20 = Decimal("20")
SIGMA20 = 42.0

class ratingsimulation:

    def __init__(self):
        self.tge = tournamentgenerator()
        self.tge.read_command_line()

    def run_simulations(self):
        self.find_range()
        self.create_data()
        params = self.tge.params
        generate = self.tge.parse_generate(params)
        experimental = params["experimental"] 
        newalg = int(experimental[0]) if len(experimental) > 0 else -1
        self.newfloor = int(experimental[1]) if len(experimental) > 1 else self.rfloor

        for fileno in range(*generate):
            if fileno > 0:
                self.tge.statistics.do_shuffle(self.player_list)
                playersintournament = 10 if "berger" in self.tge.params["method"] else 50
                for p in range(0, self.numplayers, playersintournament):
                    part_list = self.player_list[p:p+playersintournament]
                    rating_key = "rating"
                    chfile = self.rating_tournament(fileno, part_list, rating_key)
                    self.save_trf(chfile, "C:/temp/chfile.trf")
                    cmps = self.comute_tb(chfile["tournaments"][0])
                    for i, cmp in cmps.items():
                        self.update_rating(cmp, newalg >= 0 and fileno > newalg)
            self.output_players(self.player_list, params["output_file"], params["output_format"], fileno, fileno > newalg)


    ### rating_tournament(self, fileno, players) 
    ### Generate a tournament with players with ratings from rtop down to rtop - rstep*players and with a random sigma added to the rating. The tournament is generated according to the parameters in self.params and the results are generated according to the statistics in self.statistics. The tournament is run and the event is returned as a chessjson object.
    ### fileno is used to set the seed for the random number generator and to determine the top color. The tournament is generated with the method specified in self.params["method"] and with the acceleration specified in self.params["acceleration"]. The tournament is run with the number of rounds specified in self.params["number_of_rounds"] and with the current round specified in self.params["current_round"]. The tournament is generated with the number of players specified in self.params["players"] and with the number of team members specified in self.params["members"]. The tournament is generated with the game score specified in self.params["game_score"] and with the match score specified in self.params["match_score"]. The tournament is generated with the rating parameters specified in self.params["rating"] and with the statistics parameters specified in self.params["statistics"].
    ### player_list is an array of player objects with the following properties:
    ### - playerno: competitor id
    ### - rating: player FIDE rating
    ### - strength: player real strength, which is the initial rating plus

    def rating_tournament(self, fileno, player_list, rating_key="rating"):
        tge = self.tge
        params = tge.params
        ch = chessjson()
        today =  datetime.datetime.today().strftime('%Y-%m-%d')
        rounds = max(params["number_of_rounds"], params["current_round"])
        players = len(player_list)
        team_members = 1
        tournament = ch.add_tournament(1, False, rounds)
        if "game_score" in params and params["game_score"] is not None:
            tournament["scoreSystem"]["game"].update(params["game_score"])
        if "match_score" in params and params["match_score"] is not None:
            tournament["scoreSystem"]["match"].update(params["match_score"])   
        methodlist = params["methodlist"] = [item for sublist in [ s.lower().split("-") for s in params.get("method", ["dutch"])] for item in sublist]
        is_rr = "berger" in methodlist 
        exp = " ".join(params["experimental"])
        ch.get_event()["eventInfo"] = {
            "fullName": "tournamentgenerator ver." + version.version()["version"] + " " + exp,
            "site": "" ,
            "federation": "FID",
            "startDate": today,
            "endDate": today,
            "arbiters": {
                "chiefArbiter": ch.create_profile(1000, "ver 3.13", "Python", "u", "FID"),   
            }
        
        }
        tournament["topColor"] = "w" if fileno%2 == 0 else "b"
        tournament["accelerated"]= {"name" : params["acceleration"], "values": [] }
        tournament["pairingSystem"] = methodlist

        for p, player in enumerate(player_list):
            pno = player["playerno"]
            profile = ch.create_profile(player[rating_key], f"Player {pno:4}", "", "u", "FID") 
            tournament["competitors"].append({
                "cid": p+1,
                "profileId": profile,
                "present": True,
                "gamePoints": parse_float("0.0"),
                "orgrank": p+1,
                "rank": p+1,
                "realRating": player["strength"],
                "rating": player[rating_key],
                "random" : player["playerno"],
                }
            )
 
        tge.run_tournament(ch, tournament, rounds, is_rr)

        return ch.get_event()



    def is_junior(self, strength):
        return ((2000-strength)/1000)*0.9+0.05 > self.tge.statistics.get_random() 
    
    def find_range(self):
        rating = [int(r) for r in self.tge.params["rating"]]
        self.rmax = 1600
        self.rmin = 1200
        self.rfloor = 1400
        if len(rating) == 1:    
            self.rmax = rating[0]
        if len(rating) >= 2:    
            self.rmax = max(rating[0], rating[1])
            self.rmin = min(rating[0], rating[1])
        if len(rating) == 3:
            self.rfloor = rating[2]    
        self.numplayers = (self.rmax  - self.rmin) * 100
 
    def create_data(self):
        self.player_list = []
        self.player_ptr = {}
        rating = self.tge.params["rating"]

        self.tge.statistics.set_sigma(SIGMA20)        
        for p in range(1, self.numplayers + 1):
            strength = int(self.rmax - (self.rmax - self.rmin)*p/self.numplayers)
            rating = self.tge.statistics.add_sigma(strength)
            rating = rating if rating >= self.rfloor else 0
            junior = self.is_junior(strength)
            player = {
                "playerno": p,
                "rating": rating,
                "strength": strength,
                "junior" : junior,
                "kfactor" : KFACTOR40 if junior or rating == 0 else KFACTOR20,
                "ratedGames" : 30 if rating > 0 else 0,
                "game_list": []
            }
            self.player_list.append(player)
            self.player_ptr[player["playerno"]] = player


    def save_trf(self, chfile, filename):
        trf = trf2json()  
        txt = trf.output_file(chfile, 1, False)
        txt_output(filename, txt)

    def comute_tb(self, tournament):
        tb = tiebreak(tournament, 9, None)
        tblist = ["PTS", "ARO", "RND"]
        for pos in range(0, len(tblist)):
            mytb = tb.parse_tiebreak(pos + 1, tblist[pos])
            tb.compute_single_tiebreak(mytb)
        cmps = tb.cmps
        return cmps

    def update_rating(self, cmp, newalg):
        playerno = cmp["rnd"]
        ownrating = cmp["rating"]
        player = self.player_ptr[playerno]
        game_list = []
        mingames = 30 if newalg else 0
        for key, val in cmp["tiebreakDetails"][0].items():
            if isinstance(key, int):
                gamepoints =  cmp["tiebreakDetails"][0][key]
                opprating =  cmp["tiebreakDetails"][1].get(str(key), 0)
                opp =  cmp["tiebreakDetails"][2].get(str(key), 0)
                ratedgames = int(self.player_ptr[opp]["ratedGames"]) if opp > 0 else 0
                if opprating > 0 and ratedgames >= mingames:
                    expected = Decimal(rating.ComputeExpectedScore(ownrating, opprating)) if ownrating > 0 else Decimal("0.0")               
                    game_list.append({"points": gamepoints, "opprating": opprating, "expected": expected})
        if ownrating > 0:
            self.update_existing_rating(player, game_list, newalg)       
        else:
            self.update_new_rating(player, game_list, newalg)

    def update_existing_rating(self, player, game_list, newalg):
        # Implementation for updating existing player ratings
        rfloor = self.newfloor if newalg else self.rfloor
        points = sum(game["points"] for game in game_list)
        expected = sum(game["expected"] for game in game_list)
        delta = int(((points - expected) * player["kfactor"]).quantize(Decimal("0"), rounding="ROUND_HALF_UP"))
        old = player["rating"]
        player["rating"] = int(player["rating"] + delta)
        player["ratedGames"] += len(game_list)
        if player["rating"] < rfloor:
            player["rating"] = 0
            player["ratedGames"] = 0
            player["game_list"] = []
        elif player["ratedGames"] >=30 and not player["junior"]:
            player["kfactor"] = KFACTOR20

    def update_new_rating(self, player, game_list, newalg):
        # Implementation for updating new player ratings
        rfloor = self.newfloor if newalg else self.rfloor
        if len(game_list) == 0:
            return  # No games
        points = sum(game["points"] for game in game_list)
        if points == 0 and len(player["game_list"]) == 0:
            return  # Scored 0 in first game
        player["game_list"] += game_list
        player["game_list"] = player["game_list"][-36:] # Just 36 last games
        add2draw = [] if newalg else [{"points": Decimal("0.5"), "opprating": 1800}]*2
        game_list = player["game_list"] + add2draw
        points = sum(game["points"] for game in game_list)
        ratingperf = rating.ComputeTournamentPerformanceRating(points, [game["opprating"] for game in game_list])
        if ratingperf >= rfloor:
            player["rating"] = min(ratingperf, 2200)
            player["kfactor"] = KFACTOR40
            player["ratedGames"] = len(player["game_list"])
            player["game_list"] = []


    def output_players(self, player_list, filename, fileformat, fileno, newalg):
            if fileformat.lower() == "json":
                self.json_players(self.player_list, filename, fileno, fileno > newalg)
            else:
                self.plot_players(self.player_list, filename, fileno, fileno > newalg)

    def json_players(self, player_list, filename, fileno, newalg):
        file = filename.replace("%d", str(fileno).zfill(2))
        if len(directory := os.path.dirname(file)) > 0:
            os.makedirs(directory, exist_ok=True)    
        json_output(file, player_list)

    def plot_players(self, player_list, filename, fileno, newalg):
        ratings1 = [player["rating"] for player in player_list if player["rating"] > 0]
        strengths1 = [player["strength"] for player in player_list if player["rating"] > 0]    
        ratings2 = [player["rating"] for player in player_list if player["rating"] == 0]
        strengths2 = [player["strength"] for player in player_list if player["rating"] == 0]
        
        rfloor = self.newfloor if newalg else self.rfloor
        diff = max(0, min((self.rmin - rfloor) /2, 200))
        xmin = self.rmin
        xmax = self.rmax 
        ymin = max(rfloor, self.rmin - diff) 
        ymax = self.rmax + 400 - diff
        ymin = 1000
        ymax = 2000
        width = 8
        height = width/(xmax-xmin)*(ymax-ymin+100)

        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(width, height),  height_ratios=[(ymax-ymin)/100,0.9])
        fig.subplots_adjust(hspace=0.0)  # adjust space between Axes

        ax1.set_title(f"Rating floor = {rfloor}, iteration = {fileno: 2d}")
        ax1.set_xlabel('Strength')
        ax1.set_ylabel('Rating')
        diff = max(0, (self.rmin - rfloor) /2)
        ax1.axis([xmin, xmax, ymin, ymax]) 
        xy = np.vstack([strengths1, ratings1])
        z1 = gaussian_kde(xy)(xy)
        ax1.scatter(strengths1, ratings1, c=z1, s=30, alpha=0.6)
        ax1.plot([max(rfloor, self.rmin), self.rmax], [max(rfloor, self.rmin),self.rmax], color='red', linewidth=1.4)
        ax1.grid(True, color='grey', linewidth=1.4, linestyle='dotted')

        ax2.axis([self.rmin, self.rmax, 0, 105]) 
        ax2.invert_yaxis()
        ax2.set_xlabel('Playing strength')
        ax2.set_ylabel('Unrated')
        ax2.hist(strengths2,  color="maroon", bins=range(self.rmin, self.rmax))
        ticks = 100 if (xmax -xmin) <= 600 else 200
        ax2.xaxis.set_major_locator(MultipleLocator(ticks))
        ax2.xaxis.set_major_formatter('{x:.0f}')
        ax2.yaxis.set_major_locator(MultipleLocator(ticks))
        ax2.yaxis.set_major_formatter('{x:.0f}')
        # ax2.axis("equal")

        percent = len(ratings2)/len(self.player_list)*100
        ax2.text((self.rmin + self.rmax)/2 + 40, 80, f"{percent:4.1f}% unrated players", ha='left', va='bottom')
        ax2.grid(True, color='grey', linewidth=1.4, linestyle='dotted', axis = 'x')

        if filename == "-":
            plt.show()
        else:
            file = filename.replace("%d", str(fileno).zfill(2))
            if len(directory := os.path.dirname(file)) > 0:
                os.makedirs(directory, exist_ok=True)    
            plt.savefig(file, bbox_inches='tight')
        #breakpoint()
        plt.close()


# run program
if __name__ == "__main__":
    sys.set_int_max_str_digits(15000)
    rs = ratingsimulation()
    rs.run_simulations()

