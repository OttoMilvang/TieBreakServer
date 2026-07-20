# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 07:39:55 2025
@author: Otto Milvang, sjakk@milvang.no

The main purpose of crosstable is to work on the structures
competitors - One-dimentional array of size [0..P+1] of competitor objects 
opponents - Two-dimentional array of size [0..P+1][0..P+1] of opponent objects 


"""

from decimal import Decimal
from gacrux.tiebreak import tiebreak
from itertools import combinations  
from enum import Enum

# Keywords from tiebreaks
PTS = 0
ACC = 1
ACX = 2
RFP = 3
NUM = 4
RIP = 5
COD = 6
CSQ = 7
FLT = 8
TOP = 9

class flt(Enum):
    DF1 = 1
    UF1 = 2
    DF2 = 4
    UF2 = 8




class crosstable:
    """
    init_crosstable / update crosstable
        Update competitors first from cmps[i]['tiebreakDetails']
        The crosstable is an virtual crosstable of  elements.
        A game between player a and b is described in the crosstable elsement self.cmps[a][b] === self.cmps[b][a]
        init_crosstable updates:
            For all pairs in the crosstable
            canmeet - True if they are alowd to meet, False othewise
            played - Number of times they have met
        update_crosstable updates:



    """

    # constructor function
    def __init__(self, experimental, checkonly, verbose):
        self.verbose = verbose
        self.checkonly = checkonly
        self.experimental = {
        }

    def init_engine(self, tournament, rnd, maxmeets, topcolor, rank):
        self.rnd = rnd
        self.maxmeets = maxmeets
        self.topcolor = topcolor
        self.rank = rank
        self.numrounds = tournament["numRounds"]
        cmps = self.compute_tiebreak(tournament, rnd)
        prohibited = tournament.get("prohibited", [])
        (competitors, opponents) = self.list_edges(cmps, maxmeets, topcolor, prohibited)
        return (competitors, opponents)

    def floatrule(self):
        return "FLT"

    def maxquality(self):
        return 0

    def color_preference(self, cod, csq):
        return "nc"

    def get_edge_quality(self, edge):
        if edge["qlevel"] != self.scorelevel or edge["cb"] == self.BLOB:
            self.update_edge(edge)
        return edge           

    def compute_tiebreak(self, tournament, rnd):
        tb = tiebreak(tournament, rnd - 1, None)
        if tournament["teamTournament"] and "primary" in tournament["scoreSystem"]:
            tb.set_primaryscore(tournament["scoreSystem"]["primary"])
        tblist = ["PTS", "ACC", "ACC/X", "RFP", "NUM", "RIP", "COD", "CSQ", self.floatrule(), "TOP"]
        for pos in range(0, len(tblist)):
            mytb = tb.parse_tiebreak(pos + 1, tblist[pos])
            tb.compute_single_tiebreak(mytb)
        return tb.cmps

    def list_edges(self, cmps, maxmeets, topcolor, prohibited):
        self.cmps = cmps
        self.size = self.BLOB = len(cmps.keys()) + 1
        self.ilen = 0
        self.score2level = None
        self.level2score = None
        checkonly = self.checkonly

        cmps = self.cmps
        size = self.size
        opponents = self.opponents = [None] * (size + 1)
        competitors = self.competitors = [None] * (size + 1)
        self.numtop = 0
        for i in range(size + 1):
            tbval = cmps[i]["tiebreakDetails"] if i in cmps else None
            competitors[i] = {
                "cid": i,
                "rnk": cmps[i]["orgrank"] if i in cmps else i,
                "pts": tbval[PTS]["val"] if tbval else Decimal("0.0"),
                "acc": tbval[ACC]["val"] if tbval else Decimal("-1.0"),
                "acx": tbval[ACX]["val"] if tbval else Decimal("-1.0"),
                "rfp": tbval[RFP]["val"] != "" if tbval else False,
                "hst": tbval[RFP] if tbval else {},
                "num": tbval[NUM] if tbval else {},
                "rip": tbval[RIP]["val"] if tbval else 0,
                "cod": tbval[COD]["val"] if tbval else 0,
                "csq": " " + tbval[CSQ]["val"] if tbval else " ",
                "flt": tbval[FLT]["val"] if tbval else 0,
                "top": tbval[TOP]["val"] if tbval else False,
                "cop": self.color_preference(tbval[COD]["val"], tbval[CSQ]["val"]) if tbval else "  ",
            }
            if i in cmps and not cmps[i]["present"] and not self.checkonly:
                competitors[i]["rfp"] = False
            opponents[i] = [None] * (size + 1)

            competitors[0]["rfp"] ^= competitors[i]["rfp"]
        self.level2score = acc = sorted(set([c["acc"] for c in competitors if c["rfp"] or c["cid"] == 0]))
        self.score2level = score2level = {acc[i]: i for i in range(len(acc))}


        # update scorelevel
        competitors[0]["scorelevel"] = 0
        for i in range(1, size):
            competitors[i]["scorelevel"] = score2level[competitors[i]["acc"]] if competitors[i]["rfp"] else 0
        competitors[size]["scorelevel"] = -1

        # update tpn, give tps to players that have been paired at least once.
        tpn = 0
        rr = sorted(competitors, key=lambda s: (s[self.rank]))
        for i in range(1, size):
            if rr[i]["rfp"] or rr[i]["rip"]:
                tpn += 1
                rr[i]["tpn"] = tpn



        # Invariant c['ca'] < c['cb']
        for i in range(size + 1):
            b = competitors[i]
            bhasmet = [opp for (key, opp) in b["num"].items() if key != "val"]
            for j in range(i+1):
                a = competitors[j]
                opponents[j][i] = opponents[i][j] = self.create_edge(a, b, bhasmet)

        for elem in prohibited:
            if  elem["firstRound"] <= self.rnd <= elem["lastRound"]:
                for c1, c2 in list(combinations(elem["competitors"], 2)):
                    opponent = opponents[c1][c2]
                    opponent["canmeet"] = opponent["qc"] = False
                    
                        
        return (competitors, opponents)

    def levels(self):
        return self.level2score

    def create_edge(self, nodea, nodeb, bhasmet = None):
        (a, b) = (nodea, nodeb) if nodea["cid"] <= nodeb["cid"] else (nodeb, nodea)
        played = bhasmet.count(a["cid"]) if bhasmet is not None else 0
        ca = a["cid"]
        cb = b["cid"]
        sa = a["scorelevel"]
        sb = b["scorelevel"]
        c = {
            "ca": ca,
            "cb": cb,
            "sa": sa,
            "sb": sb,
            # QC1 and QC2 meetmax = 1
            "canmeet": False,
            "isblob": b["cid"] == self.BLOB,
            "played": played,
            "unplayed": self.rnd - 1 - b["num"].get("val", 0), # Unplayd games by b, for c9-calculations
            "qlevel": -1, # quality was calulated for scorelevel ...
            "quality": None,
            "weight": 0,
            "qcweight": 0,
            "heweight": 0,
            "howeight": 0,
            "colordiff": "  ",
            "qc": False,
        }
        c["canmeet"] = c["qc"] = self.update_canmeet(c, a, b, bhasmet)
 
        return c

    """
    update crosstable
        Update competitors first from cmps[i]['tiebreakDetails']
        update_crosstable updates:
            For all pairs in a scorebracket
            c10 - c21 - The rules


    """
    def set_scorelevel(self, scorelevel):
        self.scorelevel = scorelevel


    def update_crosstable(self, scorelevel, nodes, edges, pablevel, update_maxpsd=True):
        pass
            
    def update_canmeet(self, edge, a, b, bhasmet):
        played = bhasmet.count(a["cid"]) if bhasmet is not None else 0
        ca = a["cid"]
        cb = b["cid"]
        if self.checkonly:
            hb = b.get("hst", {}).get("val", "")
            if hb == "":
                hb = "0w"
            canmeet = hb != "" and int(hb[0:-1]) == a["cid"]
        else:    
           canmeet = played < self.maxmeets and ca != cb and a["rfp"] and b["rfp"] or ca < self.BLOB and cb == self.BLOB
        return canmeet

 



    def format_wpart(self, f, wx, start, stop):
        weight = self.weight
        wres = []
        for welem in range(start.value, stop.value+1):
            warr = weight[qdefs(welem).name]
            if isinstance(warr, int):
                warr = [warr]
            for wfac in warr:
                we = wx // wfac
                wx = wx % wfac
                wres.append(we)
    
        index = [i for i, c in enumerate(f) if c == "0"]
        if len(wres) != len(index):
            raise
        ptr = list(f)
        for i, c in enumerate(wres):
            ptr[index[i]] = str(c)
        return "".join(ptr)
    

    def compute_pab_weight(self, edges):
        for edge in edges:
            edge["weight"] = edge["sb"] if edge["ca"] == 0 else 0

