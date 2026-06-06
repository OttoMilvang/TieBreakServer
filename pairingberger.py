"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Fri Aug  11 11:43:23 2023
@author: Otto Milvang, sjakk@milvang.no
"""

import json
import sys
import time
from decimal import Decimal
from crosstable import crosstable
from collections import defaultdict
import berger

from pairing import pairing
from enum import Enum
import helpers



class bergerdefs(Enum):
    IW = 0


class pairing_berger(pairing):

    BERGER_RULES = {
        0 : "2022-01-01",
        } 

    # constructor function
    def __init__(self, tournament, rnd, params):
        # helpers.json_output(sys.stdout, cmps[12]['tiebreakDetails'])
        super().__init__(tournament, rnd, params)
        self.rules = self.BERGER_RULES[0]
        competitors = self.numcompetitors
        self.cycle = competitors + competitors % 2 -1
        self.fide = "fide" in tournament.get("pairingSystem", [])
        self.gacrux = "gacrux" in tournament.get("pairingSystem", [])
        self.reverse = "reverse" in tournament.get("pairingSystem", [])

        self.maxmeets = tournament.get("maxMeets", 1)
        ## print("Max meets = ", self.maxmeets, ", numcompetitors = ", self.numcompetitors, ", cycle = ", self.cycle)
        if ((rnd-1)//self.cycle) % 2 == 0:
            self.trans = {"white": "white", "black": "black"}
        else:
            self.trans = {"white": "black", "black": "white"}

    def get_crosstable(self, experimental, checkonly, verbose):
        return crosstable(experimental, checkonly, verbose)

    def qdefs_enum(self):
        return bergerdefs

    def pair_bracket(self, scorelevel, nodes, edges, testpab):
        if scorelevel !=0:
            return (None, nodes, edges, testpab)

        bracket = {
            "scorelevel": scorelevel,
            "competitors": [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel],
            "pairs": [],
            "downfloaters": [],
            "remaining": [],
            "quality": [],
        }
 
        showtime = self.showtime
        self.crosstable.set_scorelevel(scorelevel)
        t0 = time.time()
   
        if self.reportlevel >= 2 and scorelevel < len(self.crosstable.levels()):
            print("================================================")
            print("Scorelevel: ", scorelevel,  ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Bracket       = ", self.crosstable.levels()[scorelevel])
        elif self.verbose:
            print("Scorelevel: ", scorelevel, ",  nodes: ", len(nodes), ", edges: ", len(edges))

        self.crosstable.update_crosstable(scorelevel, nodes, edges, 0)
        t1 = time.time()
        if showtime and self.reportlevel >= 2 and scorelevel < len(self.crosstable.levels()):
            print("Time          = ", t1 - t0)

        # print(nodes[0])

        # print("Cat", self.checkonly, scorelevel, category)
        numpairs = 0  # Number of homogenious pairs
        wpairs = []
        bt = berger.bergertables(self.numcompetitors)
        if self.checkonly:
            bracket["pairs"] = edges
            for board in range(len(edges)):
                c = edges[board]
                c["board"] = board + 1
                ca = self.competitors[c["ca"]]
                cb = self.competitors[c["cb"]]
                if ca["cid"] == 0:
                    p =  {"w": cb["cid"], "b": 0}
                else: # ca["hst"]["val"][-1] == 0:
                   p =  {ca["hst"]["val"][-1]: ca["cid"], cb["hst"]["val"][-1]: cb["cid"]}
                c.update(p)
                node = berger.bergerlookup(bt, c["w"], c["b"])
                if node:
                    c["board"] = node["board"]
        else:   
            rnd = self.rnd
            if self.fide and self.maxmeets == 2 and (rnd == self.cycle or rnd == self.cycle - 1):
                rnd = 2*self.cycle - rnd - 1  
            elif self.gacrux and rnd > self.cycle:
                rnd -= 1
                cycle = rnd //self.cycle
                rnd = (rnd % self.cycle + self.cycle - cycle) % self.cycle + 1
            elif self.reverse and rnd > self.cycle:
                rnd -= 1
                cycle = rnd //self.cycle
                #rnd = (rnd % self.cycle + self.cycle - cycle) % self.cycle + 1
                if cycle % 2 == 1:
                    rnd = self.cycle - rnd
                else:
                    rnd += 1
            rnd = (rnd-1) % self.cycle + 1
            trans = self.trans
            for board, pair in bt["pairing"][rnd].items():
                w = pair[trans["white"]]
                b = pair[trans["black"]]
                w = w if w <= self.numcompetitors else 0
                b = b if b <= self.numcompetitors else 0
                if w == 0:
                    (w, b) = (b, w)
                c = self.opponents[w][b]
                c["w"] = w
                c["b"] = b
                c["board"] = board
                bracket["pairs"].append(c)            

        (nodes, edges, npaired) = self.remove_pairs(nodes, edges, bracket["pairs"])

        bracket["remaining"] = [c["cid"] for c in nodes if c["scorelevel"] < scorelevel]
        bracket["downfloaters"] = [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel]
        return (bracket, nodes, edges, testpab)

    def update_board(self, roundpairing):
        pairs = []
        return pairs

    def find_pab(self, nodes, edges):
        return (None, 0, nodes, edges)