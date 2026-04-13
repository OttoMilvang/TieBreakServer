# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 16:51:48 2025

@author: otto
"""

"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import argparse
import json
import io
import sys
import os
import datetime
import codecs
import version
from helpers import *
from chessjson import chessjson
from commonmain import commonmain
from trf2json import trf2json
from ts2json import ts2json
from tiebreak import tiebreak
from crosstable import crosstable
from pairing import pairing
from drawresult import drawresult
#from generator import generator

# ==============================

"""
Syntax:
    python pairingchecker.py [options]
        -i input-file        # config
        -o output-file       # default is stdout %d is replaced by tournament number
        -b ascii | utf8 | latin1 
        -t a | r | w | b          # alternate / random / white /black
        -u [list of illagal pairings]
        -n <no>              # Number of rounds 
        -m <method>          # dutch | berger
        -T team_size         # Team tournment with <team_size> players/team 
        -X exclude           # Exclude some pairs
        -d @ | T | J         # Print result in result format, text format or JSON formet (default)
        

"""


class tournamentgenerator(commonmain):

    def __init__(self):
        super().__init__()
        ver = version.version()
        self.origin = "tournamentgenerator ver. " + ver["version"]

 

    def read_command_line(self):
        self.helptxt.update({
            "-a": "Baku accelleration",
            "-R": "Rating, -r <highest rating> <rating step> [<sigma>]",
            "-S": "statistics, -s <rate zpb> <rate hpb> <rate forfeited>",
            "-m": "dutch | berger",
            })
        
        self.parser.add_argument("-a", "--acceleration", required=False, action="store_true", default=False, help=self.helptxt["-a"])
        self.parser.add_argument("-g", "--generate", required=False, nargs="*", default=["0", "1000"],
                            help="Generate 'g' tournaments")
        self.parser.add_argument("-p", "--players", required=False, default="40",
                            help="Do pairing")
        self.parser.add_argument("-T", "--members", required=False, default="1",
                            help="Team members")
        self.parser.add_argument("-R", "--rating", required=False, nargs="*", default=[], help=self.helptxt["-R"])
        self.parser.add_argument("-S", "--statistics", required=False, nargs="*", default=["0.01", "0.05", "0.02"], help=self.helptxt["-S"])
        self.parser.add_argument("-m", "--method", required=False, default="dutch", help=self.helptxt["-m"])
        self.parser.add_argument("-M", "--maxmeets", required=False, default="0", help="The maximum number of meets")
        self.parser.add_argument("-t", "--top-color", required=False,
            default=' ',
            help="Color on top board" )
        self.parser.add_argument(
            "-u",
            "--unpaired",
            required=False,
            nargs="*",
            default=[] )
        self.read_common_command_line(self.origin, True)


    def process_tournaments(self):
        params = self.params
        generate = ([0] + [int(g) for g in params["generate"]])[-2:]
        seed = generate[0] * 10000 + 4711
        self.statistics = drawresult(seed)
        self.statistics.set_params(0.01, 0.05, 0.02)
        self.statistics.set_sigma(50.0)
        self.statistics.set_team(1)
        for fileno in range(*generate):
            event = self.gen_tournament(fileno)
            trf = trf2json()  
            txt = trf.output_file(event, 1, self.params["verbose"])
            file = params["output_file"].replace("%d", str(fileno).zfill(4))
            if len(directory := os.path.dirname(file)) > 0:
                os.makedirs(directory, exist_ok=True)    
            txt_output(file, txt)
                
    def gen_tournament(self, fileno):
        params = self.params
        ch = chessjson()
        today =  datetime.datetime.today().strftime('%Y-%m-%d')
        rounds = max(self.params["number_of_rounds"], self.params["current_round"])
        players = int(self.params["players"])
        members = int(self.params["members"])
        tournament = ch.add_tournament(1, False, rounds)
        rating = params["rating"]
        if players < 65:
            rtop = 2200
            rstep = 10
            sigma = 50.0
        elif players < 85:
            rtop = 2200 + 10 * (players-64)
            rstep = 10
            sigma = 50.0
        elif players < 700:
            rtop = 2400
            rstep = 600.0/players
            sigma = 100.0
        else:
            rtop = 2000
            rstep = 0
            sigma = 200.0

        rtop = rtop if len(rating) < 1 else parse_int(rating[0])
        rstep = rstep if len(rating) < 2 else parse_int(rating[1])
        sigma = sigma if len(rating) < 3 else float(parse_float(rating[2]))

        stat = params["statistics"]
        zpb = 0.01 if len(stat) < 1 else float(stat[0])
        hpb = 0.05 if len(stat) < 2 else float(stat[1])
        forfeited = 0.02 if len(stat) < 3 else float(stat[2])
        self.statistics.set_params(zpb, hpb, forfeited) 
        self.statistics.set_sigma(sigma) 
        self.statistics.set_team(members)
        exp = " ".join(self.params["experimental"])
        ch.get_event()["eventInfo"] = {
            "fullName": "tournamentgenerator ver." + version.version()["version"] + " " + exp,
            "site": f"rating={rtop}, step={rstep:4.1f}, sigma={sigma:4.1f}, zpb={zpb:4.2f}, hpb={hpb:4.2f}, forfeited={forfeited:4.2f}" ,
            "federation": "FID",
            "startDate": today,
            "endDate": today,
            "arbiters": {
                "chiefArbiter": ch.create_profile(1000, "ver 3.13", "Python", "u", "FID"),   
            }
        
        }
        tournament["topColor"] = "w" if fileno%2 == 0 else "b"
        tournament["accelerated"]= {"name" : params["acceleration"], "values": [] }


        for player in range(1, players + 1):
            rating = int(rtop - rstep*player)
            profile = ch.create_profile(rating, f"Player {player:4}", "", "u", "FID") 
            tournament["competitors"].append({
                "cid": player,
                "profileId": profile,
                "present": True,
                "gamePoints": parse_float("0.0"),
                "orgrank": player,
                "rank": player,
                "realRating": rating,
                "rating": self.statistics.add_sigma(rating),
                "random" : self.statistics.get_random(),
                }
            )
        # ch.update_tournament_random(tournament, False)        
        tournament["competitors"] = sorted(tournament["competitors"],  key=lambda comp: (-comp["rating"], comp["random"]))
        cid = 0
        for competitor in tournament["competitors"]:
            cid += 1
            competitor["cid"] = cid
        for rnd in range(1, rounds + 1):
            if rnd == 4:
                self.statistics.set_hpb(0.0)
            self.do_pairing(ch, tournament, rnd)

        return ch.get_event()

    def do_pairing(self, ch, tournament, rnd):
        tr = {"Z": "Z", "H": "D", "+": "W", "-": "Z" }
        rounds = int(self.params["number_of_rounds"])
        maxmeets = int(self.params["maxmeets"])
        self.params['is_rr'] = False
        self.docheck = False
        self.doanalysis = False
        self.dopairing = True  
        tournament["currentRound"] =  rnd
        if maxmeets > 0:
            tournament["maxMeets"] =  maxmeets
        pcompetitors = {c["cid"] : c for c in tournament["competitors"] }
        numcompetitors = 0
        for competitor in tournament["competitors"]:
            has_bye = self.statistics.has_bye()
            competitor["present"] = len(has_bye) == 0
            if competitor["present"]: numcompetitors += 1 
            if len(has_bye):
                game = {
                    "id": 0,
                    "round": rnd,
                    "white": competitor["cid"],
                    "black": 0,
                    "played": False,
                    "rated": False,
                    "wResult": tr[has_bye],
                    }
                ch.append_result(tournament["gameList"], game)
                if has_bye == "H":
                    competitor["gamePoints"] += tournament["scoreSystem"]["game"]["D"]
        if tournament["accelerated"]["name"] and rnd == 1:
            present = [competitor["cid"] for competitor in tournament["competitors"] if competitor["present"]]
            q = ((len(present)+3) // 4) * 2 # From handbook
            rounds = max(self.params["number_of_rounds"], self.params["current_round"])
            accrounds = [0, (rounds+3)//4, (rounds+1)//2 ]
            gscrounds = ["Z", "W", "D" ]
            for acc in [1,2]: 
                value = {
                "matchResult": gscrounds[acc],
                "gameResult": gscrounds[acc],
                "firstRound": accrounds[acc-1] + 1,
                "lastRound": accrounds[acc],
                "firstCompetitor": 1,
                "lastCompetitor": present[q-1],
                }
                tournament["accelerated"]["values"].append(value)
        
        cpairing  = pairing(tournament, rnd, 
                            tournament["topColor"], 
                            "fakerank" not in self.params["experimental"] and self.params['rank'],
                            self.params['experimental'], 
                            self.params['verbose'])
        result = self.compute_pairing(cpairing, self.params) 
        for level in result['checker']:
            for pair in level['pairs']:
                w = pcompetitors[pair["w"]]
                if pair["b"] > 0:
                    b = pcompetitors[pair["b"]]
                    res = self.statistics.result(w["realRating"], b["realRating"])
                    played = res == "W" or res == "D" or res == "B"
                    wResult ={"W": "W", "D":"D", "B": "L", "+": "W", "-": "Z"}[res]
                    bResult ={"W": "L", "D":"D", "B": "W", "+": "Z", "-": "W"}[res]
                    b["gamePoints"] += tournament["scoreSystem"]["game"][bResult]
                else:
                    wResult = "W"
                    bResult = None
                    played = True
                w["gamePoints"] += tournament["scoreSystem"]["game"][wResult]
                game = {
                    "id": 0,
                    "round": rnd,
                    "white": pair["w"],
                    "black": pair["b"] ,
                    "played": played,
                    "rated": played,
                    "wResult": wResult,
                    "bResult": bResult,
                    }
                ch.append_result(tournament["gameList"], game)

    def fakerank(self, tm, trans, pairing):
        for competitor in tm["competitors"]:
            competitor["cid"] = trans[competitor["cid"]]
        for game in tm["gameList"]:
            game["white"] = trans[game["white"]]
            game["black"] = trans[game["black"]]
        tm["competitors"] = sorted(tm["competitors"], key=lambda c: c["cid"])
        for cpairing in pairing:
            for pair in cpairing["pairs"]:
                pair["w"] = trans[pair["w"]]
                pair["b"] = trans[pair["b"]] if pair["b"] > 0 else 0
                pair["ca"] = trans[pair["ca"]]
                pair["cb"] = trans[pair["cb"]] if pair["cb"] > 0 else 0 

    def compute_pairing(self, pairingengine, params):
        #print('PARAMS', params)
        self.pairingengine = pairingengine
        tm = pairingengine.tournament
        analysis = pairing = [] 
        if "fakerank" in params["experimental"]:
            fwd = [0]*(len(tm["competitors"])+1)
            inv = [0]*(len(tm["competitors"])+1)
            for i, c in enumerate(tm["competitors"]):
                fwd[c["cid"]] = c["rank"]
                inv[c["rank"]] = c["cid"]
            self.fakerank(tm, fwd, pairing)
        acompetitors = pcompetitors = {} 
        if self.doanalysis or (self.docheck and not self.doanalysis and not self.dopairing):
            analysis = pairingengine.compute_pairing(True)
            acompetitors = sorted([{key: value for (key, value) in c.items() if key != 'opp'} for c in pairingengine.crosstable.crosstable], key=lambda c: (c['cid']))  
                     
        if self.dopairing or (self.docheck and not self.doanalysis and not self.dopairing):
            pairing = pairingengine.compute_pairing(False)
            pcompetitors = sorted(pairingengine.crosstable.competitors, key=lambda c: (c['cid']))                         
        if "fakerank" in params["experimental"]:
            self.fakerank(tm, inv, pairing)
        result = {
            'round' : pairingengine.rnd,
            'check': self.docheck,
            'analysis' : analysis,
            'checker': pairing, 
            'competitors' : pcompetitors if len(pcompetitors) >= len(acompetitors) else acompetitors,
            'level2score' : pairingengine.crosstable.level2score,
        }
        #chessfile.chessjson["status"]["code"] = 1
        return result



sys.set_int_max_str_digits(15000)
tge = tournamentgenerator()
code = tge.read_command_line()
tge.process_tournaments()
sys.exit(code)