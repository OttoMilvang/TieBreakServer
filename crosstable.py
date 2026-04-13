# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 07:39:55 2025
@author: Otto Milvang, sjakk@milvang.no

The main purpose of crosstable is to work on the structures
competitors - One-dimentional array of size [0..P+1] of competitor objects 
opponents - Two-dimentional array of size [0..P+1][0..P+1] of opponent objects 


"""

from decimal import Decimal
from tiebreak import tiebreak
from qdefs import qdefs
from itertools import combinations  

# Keywords from tiebreaks
PTS = 0
ACC = 1
RFP = 2
NUM = 3
RIP = 4
COD = 5
COP = 6
CSQ = 7
FLT = 8
TOP = 9

# Downfloat and upfloat bits
DF1 = 1
DF2 = 4
UF1 = 2
UF2 = 8

# Euality constants
QC6 = qdefs.QC6.name
QC7 = qdefs.QC7.name
QN8 = qdefs.QN8.name
QC8 = qdefs.QC8.name
QC9 = qdefs.QC9.name
QMM = qdefs.QMM.name
QC10 = qdefs.QC10.name
QC11 = qdefs.QC11.name
QC12 = qdefs.QC12.name
QC13 = qdefs.QC13.name
QC14 = qdefs.QC14.name
QC15 = qdefs.QC15.name
QC16 = qdefs.QC16.name
QC17 = qdefs.QC17.name
QC18 = qdefs.QC18.name
QC19 = qdefs.QC19.name
QC20 = qdefs.QC20.name
QC21 = qdefs.QC21.name
HE1 = qdefs.HE1.name
HE2 = qdefs.HE2.name
HO1 = qdefs.HO1.name
HO2 = qdefs.HO2.name
HO3 = qdefs.HO3.name
HO4 = qdefs.HO4.name
HO5 = qdefs.HO5.name
IW = qdefs.IW.name
QL = qdefs.QL.value
QC0 = qdefs.QC0.name
HE0 = qdefs.HE0.name
HO0 = qdefs.HO0.name
B0 = qdefs.B0.name
QS = qdefs.QS.value


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
            psd - The differnce in score between the palyers in 0.5p as char in base36, (or 'Z' for more than 17p).
        update_crosstable updates:
            For all pairs in a scorebracket
            c10 - c21 - The rules

    C = log10 (Max competitors) = 3
    R = log10 (Max rounds) = 2
    M = Number of moved down players
    P = Max point difference on downfloaters (in scorelevels)
    N = Number of moved down players + number of downfloaters
    B = Len of BSB
    S = Max pairs that can be paired


    """

    # constructor function
    def __init__(self, experimental, checkonly, verbose):
        self.verbose = verbose
        self.checkonly = checkonly
        self.experimental = {
            "XQC6": "XQC6" in experimental,
            "XQC7": "XQC7" in experimental,
            "XQC8": "XQC8" in experimental,
            "XQC9": "XQC9" in experimental,
            "XQC14": "XQC14" in experimental,
            "XQC14M1": "XQC14M1" in experimental,
            "XQC16": "XQC16" in experimental,
            "XQC16M1": "XQC16M1" in experimental,
            "XCTOPM1": "XTOPM1" in experimental,
        }
        self.scalars = [QC6, QN8, QC9, QC10, QC11, QC12, QC13, QC14, QC15, QC16, QC17, HO1, HO2, IW]

    def init_engine(self, tournament, rnd, maxmeets, topcolor, rank):
        self.rnd = rnd
        self.maxmeets = maxmeets
        self.topcolor = topcolor
        self.rank = rank
        cmps = self.compute_tiebreak(tournament, rnd)
        ncmps = len(cmps)
        self.C = 100  # digits
        if ncmps > 97:
            self.C = 1000
        if ncmps > 997:
            self.C = 10000
        self.R = 10  # digits
        if rnd > 9:
            self.R = 100
        if rnd > 99:
            self.R = 100
        self.Cbits = ncmps.bit_length()
        self.Rbits = rnd.bit_length()
        prohibited = tournament.get("prohibited", [])
        (competitors, opponents) = self.list_edges(cmps, maxmeets, topcolor, prohibited)
        return (competitors, opponents)

    def get_edge_quality(self, edge):
        if edge["qlevel"] != self.scorelevel or edge["cb"] == self.BLOB:
            self.update_edge(edge)
        return edge           

    def compute_tiebreak(self, tournament, rnd):
        tb = tiebreak(tournament, rnd - 1, None)
        tblist = ["PTS", "ACC", "RFP", "NUM", "RIP", "COD", "COP", "CSQ", "FLT", "TOP"]
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
                "rfp": tbval[RFP]["val"] != "" if tbval else False,
                "hst": tbval[RFP] if tbval else {},
                "num": tbval[NUM] if tbval else {},
                "rip": tbval[RIP]["val"] if tbval else 0,
                "cod": tbval[COD]["val"] if tbval else 0,
                "cop": tbval[COP]["val"] if tbval else "  ",
                "csq": " " + tbval[CSQ]["val"] if tbval else " ",
                "flt": tbval[FLT]["val"] if tbval else 0,
                "top": tbval[TOP]["val"] if tbval else False,
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
        # QC3 not-topscorers with absolute color preference cannot meet
        if self.checkonly:
            hb = b.get("hst", {}).get("val", "")
            canmeet = hb != "" and int(hb[0:-1]) == a["cid"]
        else:    
            canmeet = played < self.maxmeets and ca != cb and a["rfp"] and b["rfp"] or ca < self.BLOB and cb == self.BLOB
            for col in ["w", "b"]:
                col2 = col + "2"
                if a["cop"] == col2 and b["cop"] == col2 and (not a["top"]) and (not b["top"]):
                    canmeet = False
                if a["cod"] * b["cod"] >= 4 and (not a["top"]) and (not b["top"]):
                    canmeet = False
        # score diff
        c["canmeet"] = c["qc"] = canmeet
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
        self.pablevel = pablevel
        if update_maxpsd:
            maxpsd = max([node["scorelevel"] for node in nodes]) - scorelevel
            self.maxpsd = nodes[0]["scorelevel"] - scorelevel
            if maxpsd != self.maxpsd: breakpoint()
            self.mdp = [0] * self.maxpsd
            for node in nodes:
                psd = node["scorelevel"] - scorelevel
                if psd <= 0:
                    break
                self.mdp[self.maxpsd - psd] += 1
            self.init_cweights(scorelevel, nodes)
        self.L = self.maxpsd
        # print("Update scorelevel", scorelevel, len(nodes), len(edges), pablevel, update_maxpsd, self.maxpsd)
            
            
    def update_edge(self, edge):
        c = edge
        if c["qlevel"] == self.scorelevel and c["cb"] < self.BLOB:
            return
        c["qlevel"] = self.scorelevel
        c["quality"] = {q.name : None for q in qdefs if q.value < QL}
        coltrans = {"  ": "n", "w0": "w", "w1": "W", "w2": "W", "b0": "b", "b1": "B", "b2": "B"}
        maxpsd = self.maxpsd
        scorelevel = self.scorelevel
        if c["canmeet"]:
            a = self.competitors[c["ca"]]
            b = self.competitors[c["cb"]]
            weight = self.weight
            cweight = 0
            if a["scorelevel"] < b["scorelevel"]:
                (a, b) = (b, a)
            q = c["quality"]
            q[QC6] = 0
            q[QC7] = [0] * (maxpsd)
            q[QN8] = 0
            q[QC8] = [0] * (maxpsd + 1)
            q[QC9] = 0
            q[QMM] = [0] * (self.maxmeets-1)
            for elem in range(qdefs.QC10.value, qdefs.QC18.value):
                q[qdefs(elem).name] = 0
            for elem in range(qdefs.QC18.value, qdefs.QC21.value + 1):
                q[qdefs(elem).name] = [0] * maxpsd

            level = a["scorelevel"] - scorelevel

            c14 = c15 = c16 = c17 = 0
            if a["scorelevel"] >= scorelevel and b["scorelevel"] == scorelevel:
                if self.pablevel and b["scorelevel"] == 0:
                    q[QC9] = self.rnd - 1 - a["num"].get("val", 0)
                    cweight += weight[QC9] * q[QC9]

                if c["canmeet"] and c["played"] > 0 and self.maxmeets > 1:
                    q[QMM][c["played"]-1] = 1  

                # Topscorere

                if (a["top"] or b["top"]) and a["cid"] > 0 and b["cid"] > 0:
                    # if scorelevel == 9 and a["cid"] ==3 and b["cid"] == 9: breakpoint()

                    # c10 minimize the number of topscorers who get color diff > +2 or < -2
                    # print(c, a['cod'], b['cod'])
                    # apf = a["cod"] + 1 if a["cid"] == c["w"] else a["cod"] - 1
                    # bpf = b["cod"] + 1 if b["cid"] == c["w"] else b["cod"] - 1
                    # q[QC10] = 1 if abs(apf) > 2 and abs(bpf) >= 2 or abs(apf) >= 2 and abs(bpf) > 2 else 0

                    acod = a["cod"]
                    bcod = b["cod"]
                    if acod == bcod and abs(acod) >= 2:
                        q[QC10] = 1
                        cweight += weight[QC10]

                    # c11 minimize the number of topscorers who get same color three times in a row
                    # asq = a["csq"][-2:] + ("w" if a["cid"] == c["w"] else "b")
                    # bsq = b["csq"][-2:] + ("w" if b["cid"] == c["w"] else "b")
                    acop = a["cop"]
                    bcop = b["cop"]
                    opp = {"w": "bb", "b":"ww", " ":"  "}[acop[0]]

                    if acop[0] == bcop[0] == "w" or acop[0] == bcop[0] == "b":
                        opp = {"w": "bb", "b":"ww"}[acop[0]]
                        anp = int(acop[1])
                        bnp = int(bcop[1])

                        if a["csq"][-2:] == b["csq"][-2:] and (a["csq"][-2:] == "ww" or b["csq"][-2:] == "bb") or \
                           anp > bnp and b["csq"][-2:] == opp or bnp > anp and a["csq"][-2:] == opp or \
                           (anp == bnp == 2 and (abs(acod) > abs(bcod) and b["csq"][-2:] == opp or abs(bcod) > abs(acod) and a["csq"][-2:] == opp)):
                            q[QC11] = 1
                            cweight += weight[QC11]

                    if scorelevel == -1:
                         print(f"A: {a['cid']:2} {a['cod']:2} {a['csq'][-2:]} {a['cop']},   B: {b['cid']:2} {b['cod']:2} {b['csq'][-2:]} {b['cop']},  Q10: {q[QC10]} Q11: {q[QC11]}")


                # c12 minimize the number of players who do not get their color preference
                if a["cop"] != "  " and a["cop"][0].lower() == b["cop"][0].lower():
                    q[QC12] = 1
                    cweight += weight[QC12]

                # c13 minimize the number of players who do not get their strong color preference
                if q[QC12] == 1 and int(a["cop"][1]) > 0 and int(b["cop"][1]) > 0:
                    q[QC13] = 1
                    cweight += weight[QC13]

                c["colordiff"] = coltrans.get(a["cop"], a["cop"][0].upper()) + coltrans.get(b["cop"], b["cop"][0].upper())

                # c15 minimize the number of players who receive upfloft in the previous round
                c15 = 1 if (a["acc"] < b["acc"]) and (a["flt"] & UF1) or (a["acc"] > b["acc"]) and (b["flt"] & UF1) else 0
                if c15:
                    q[QC15] = 1
                    cweight += weight[QC15]

                # c17 minimize the number of players who receive upfloft two rounds before
                c17 = 1 if (a["acc"] < b["acc"]) and (a["flt"] & UF2) or (a["acc"] > b["acc"]) and (b["flt"] & UF2) else 0
                if c17:
                    q[QC17] = 1
                    cweight += weight[QC17]

            elif a["scorelevel"] >= scorelevel and b["scorelevel"] < scorelevel:
                q[QC6] = 1
                cweight += weight[QC6]
                if level > 0:
                    # q[QC7] = [1 if level == maxpsd - i else 0 for i in range(maxpsd)]
                    q[QC7][maxpsd - level] = 1
                    cweight += weight[QC7][maxpsd - level]

                if self.pablevel and b["scorelevel"] == 0:
                    q[QC9] = self.rnd - 1 - a["num"].get("val", 0)
                    cweight += weight[QC9] * q[QC9]

                # c14 minimize the number of players who receive downfloat in the previous round
                c14 = 1 if (a["flt"] & DF1) else 0
                if c14 and scorelevel == a["scorelevel"]:
                    q[QC14] = 1
                    cweight += weight[QC14]

                # c16 minimize the number of players who receive downfloat two rounds before
                c16 = 1 if a["flt"] & DF2 else 0
                if c16 and scorelevel == a["scorelevel"]:
                    q[QC16] = 1
                    cweight += weight[QC16]

            # c18-21 minimize the score difference of players who receive downfloat/upfloat in the previous round
            for cnn, val in enumerate([(level if cxx else 0) for cxx in [c14, c15, c16, c17]], start=qdefs.QC18.value):
                if val > 0:
                    q[qdefs(cnn).name][maxpsd - val] = 1
                    cweight += weight[qdefs(cnn).name][maxpsd - val]

            scorelevel2 = scorelevel - 1
            # print("QN8", scorelevel2, a['cid'], b['cid'], a['scorelevel'], b['scorelevel'], "            ", a['scorelevel'] >= scorelevel2 and b['scorelevel'] < scorelevel2)
            # if scorelevel == testlevel and update_maxpsd:
            #    breakpoint()
            if a["scorelevel"] >= scorelevel2 and b["scorelevel"] < scorelevel2:
                q[QN8] = 1
                cweight += weight[QN8]
                level = max(a["scorelevel"], b["scorelevel"]) - scorelevel2
                if level > 0:
                    # q[QC8] = [1 if level == maxpsd + 1 - i else 0 for i in range(maxpsd+1)]
                    q[QC8][maxpsd + 1 - level] = 1
                    cweight += weight[QC8][maxpsd + 1 - level]

            c["qc"] = (q[QC9] + sum(q[QMM]) + q[QC10] + q[QC11] + q[QC14] + q[QC15] + q[QC16]+ q[QC17] \
                    + sum(q[QC18]) + sum(q[QC19]) + sum(q[QC20]) + sum(q[QC21])) == 0
            c["qcweight"] = cweight

    def update_hetrogenious(self, scorelevel, nodes, edges, bsn):
        M = self.M = sum(self.mdp)
        self.ilen = 0
        elen = len(bsn) + 1
        weight = self.weight
        self.init_heweights(scorelevel, bsn)
        for c in edges:
            (ca, cb) = (c["ca"], c["cb"])
            q = self.get_edge_quality(c)["quality"]
            q[HE1] = [0] * M
            q[HE2] = [0] * M
            heweight = 0
            e1weight = sum(weight[HE1])

            ascl = self.competitors[ca]["scorelevel"]
            bscl = self.competitors[cb]["scorelevel"]
            absn = bsn.get(ca, elen)
            bbsn = bsn.get(cb, elen)
            if absn > bbsn:
                (absn, bbsn, ascl, bscl) = (bbsn, absn, bscl, ascl)
            # print(self.competitors[ca])
            if ascl > scorelevel and bscl <= scorelevel:
                e0 = absn
                e1 = 1 if bbsn == elen else 0
                e2 = bbsn - M if bbsn < elen else 0
                #if bscl < scorelevel: breakpoint()
                q[HE1][e0-1] = e1
                q[HE2][e0-1] = e2
                heweight += weight[HE1][e0 - 1] * e1
                heweight += weight[HE2][e0-1] * e2

            c["heweight"] = heweight

    def update_homogenious(self, scorelevel, edges, bsn, S):
        B = self.B = len(bsn)
        mdp = B - 2 * S
        B3 = self.B3 = S
        B4 = self.B4 = B - S
        B5 = self.B5 = B - 1
        self.ilen = 0
        # print ("BO:", B, S)
        weight = self.weight
        self.init_howeights(scorelevel, S, mdp)
        # print("CheckAnlyse", scorelevel, "M="+str(M), "P="+str(P), "N="+str(N), "S="+str(S), "B="+str(B) )
        # HO4weight = sum([weight[HO4][i] for i in range(B4)])
        HO4weight = sum(weight[HO4])
        for c in edges:
            c["howeight"] = 0
            (ca, cb) = (c["ca"], c["cb"])
            q = self.get_edge_quality(c)["quality"]
            q[HO1] = 0
            q[HO2] = 0
            q[HO3] = [0] * B3
            q[HO4] = [1] * B4
            q[HO5] = [0] * B5
            howeight = HO4weight
            ascl = self.competitors[ca]["scorelevel"]
            bscl = self.competitors[cb]["scorelevel"]
            if ascl == scorelevel and bscl == scorelevel:
                absn = bsn[ca]
                bbsn = bsn[cb]
                if absn > bbsn:
                    (absn, bbsn, ascl, bscl) = (bbsn, absn, bscl, ascl)

                if c["canmeet"]:
                    if absn > S:
                        q[HO1] = 1
                        howeight += weight[HO1]
                    q[HO2] = absn - 1
                    howeight += (absn - 1) * weight[HO2]
                    if absn <= S:
                        q[HO3][S - absn] = 1
                        howeight += weight[HO3][S - absn]
                    else:
                        q[HO4][absn - S - 1] = 0
                        howeight -= weight[HO4][absn - S - 1]
                    q[HO5][absn - 1] = bbsn - absn
                    howeight += weight[HO5][absn - 1] * (bbsn - absn)
                    # if c['quality'][HO5] != [bbsn if absn == i+1 else 0 for i in range(B)]: breakpoint()
            c["howeight"] = howeight

    def update_bipartite(self, scorelevel, pairs, bsn, HO2start, HO2stop):
        B = self.B = len(bsn)
        H = self.H = len(bsn) // 2
        M = self.M = sum(self.mdp)
       # print ("BO:", B, S, self.S)

        # print("CheckAnlyse", scorelevel, "M="+str(M), "P="+str(P), "N="+str(N), "S="+str(S), "B="+str(B) )
        self.init_bweights(scorelevel, H)
        weight = self.weight
        for pno, pair in enumerate(pairs):
            (ca, cb) = pair
            bweight = 0
            if HO2start <= ca <= HO2stop:
                (ca, cb) = (cb, ca)
            c = self.get_edge_quality(self.opponents[ca][cb])
            q = c["quality"]
            if q[HE1] is None or len(q[HE1]) != M:
                q[HE1] = [0] * M
                q[HE2] = [0] * M
            q[HO1] = 0
            q[HO2] = 0
            q[HO3] = 0
            q[HO4] = 0
            q[HO5] = [0] * H
            if pno >= mdp:
                absn = pno - mdp
                bbsn = bsn[cb]
                q[HO5][absn] = bbsn -absn
                bweight = weight[HO5][absn] * (bbsn - absn)
            c["biweight"] = bweight

    # Compute weight
    # mode 'E' - Hetrogenous
    # mode 'S' - Homogenous
    # mode 'B' - Bipartite
    # mode 'A' - Add S-part

    def cascade_weights(self, depth, start, stop):
        w = 1
        acc = {QC6: QC0, HE1: HE0, HO1: HO0}
        let = {QC6: "C", HE1: "HE", HO1: "HO"}
        # print("Deights", let[start], self.depth[start:stop+1])
        weight = self.weight
        for cval in range(stop.value, start.value-1, -1):
            nval = qdefs(cval).name
            if isinstance(depth[nval], int):
                (w, weight[nval], depth[nval]) = (w*depth[nval], w, len(str(depth[nval])))
            elif isinstance(depth[nval], list):
                weight[nval] = [0]*len(depth[nval])
                for eval in range(len(weight[nval])-1, -1, -1):
                    (w, weight[nval][eval], depth[nval][eval]) = (w*depth[nval][eval], w, len(str(weight[nval][eval])))
            else:
                raise
        # print("Weights", let[start], self.weight[acc[start]], self.weight[start:stop+1])
        return w



    def init_cweights(self, scorelevel, nodes):
        # print(f"Init cweight, scorelevel: {scorelevel}")
        cc = len(nodes) + 1
        c7len = len(self.mdp)
        c8len = c7len + 1
        mmlen = self.maxmeets -1
        self.weight = weight = {q.name : 0 for q in qdefs}
        self.depth  = depth  = {q.name : 0 for q in qdefs}
        scoregroup = [node for node in nodes if node["scorelevel"] >= scorelevel] 
        nscoregroup = [node for node in nodes if node["scorelevel"] >= scorelevel-1] 
        bsize = len(scoregroup)
        depth[QC6] = bsize +1
        depth[QC7] = [psd + 1 for psd in self.mdp ]
        depth[QN8] = len(nscoregroup) + 1
        depth[QC8] = [psd + 1 for psd in self.mdp ] + [bsize + 1 - sum(self.mdp) ] 
        depth[QC9] = bsize + 1 if scorelevel <= self.pablevel else 1
        depth[QMM] = [cc] * mmlen
        for i in range(mmlen):  
            depth[QMM][i] = cc
        depth[QC10] = len([node for node in nodes if node["scorelevel"] >= scorelevel and node["top"]]) +1
        depth[QC11] = depth[QC10]
        depth[QC12] = cc
        depth[QC13] = cc
        depth[QC14] = len([node for node in nodes if node["scorelevel"] >= scorelevel and (node["flt"] & DF1)]) +1
        depth[QC15] = len([node for node in nodes if node["scorelevel"] <= scorelevel and (node["flt"] & UF1)]) +1
        depth[QC16] = len([node for node in nodes if node["scorelevel"] >= scorelevel and (node["flt"] & DF2)]) +1
        depth[QC17] = len([node for node in nodes if node["scorelevel"] <= scorelevel and (node["flt"] & UF2)]) +1
        depth[QC18] = [psd + 1 for psd in self.mdp ]
        depth[QC19] = [psd + 1 for psd in self.mdp ]
        depth[QC20] = [psd + 1 for psd in self.mdp ]
        depth[QC21] = [psd + 1 for psd in self.mdp ]
        # print(scorelevel, depth)
        weight[QC0] = self.cascade_weights(depth, qdefs.QC6, qdefs.QC21)

        self.QCweight = (
            "C 1--"
            + "0"  # QC6
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # QC7
            + "-"
            + "0"  # QN8
            + "-"
            + str(["0" for v in [0] * c8len]).replace("'", "")  # QC8
            + "-"
            + "0"  # QC9
            + "-"
            + str(["0" for v in [0] * mmlen]).replace("'", "")  # QMM
            + "-"
            + "0"  # QC10
            + "-"
            + "0"  # QC11
            + "-"
            + "0"  # QC12
            + "-"
            + "0"  # QC13
            + "--"
            + "0"  # QC14
            + "-"
            + "0"  # QC15
            + "-"
            + "0"  # QC16
            + "-"
            + "0"  # QC17
            + "--"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # QC18
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # QC18
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # QC20
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")
        )  # QC21

 


    def init_heweights(self, scorelevel, bsn):
        # print(f"Init heweight, scorelevel: {scorelevel}")
        M = self.M
        elen = len(bsn) + 1 - M
        weight = self.weight
        depth = self.depth
        depth[HE1] = [2] * M
        depth[HE2] = [elen] * M
        weight[HE0] = self.cascade_weights(depth, qdefs.HE1, qdefs.HE2)
        self.HEweight = "E 1--" + str(["0" for v in [0] * M]).replace("'", "") + "-" + str(["0" for v in [0] * M]).replace("'", "")


    def init_howeights(self, scorelevel, S, mdp):
        # print(f"Init howeight, scorelevel: {scorelevel}")
        B = self.B # len of BSN
        B3 = self.B3
        B4 = self.B4
        B5 = self.B5
        weight = self.weight
        depth = self.depth

        depth[HO1] = S + 1
        depth[HO2] = sum(list(range(B-1, S, -2)[:S])) + 1 # B-1 + B-3 + ... + B-(2*S-1) + 1, first S odd numbers starting from B-1 
        depth[HO3] = [2] * B3
        depth[HO4] = [2] * B4
        depth[HO5] = list(range(B5, 0, -1))
        weight[HO0] = self.cascade_weights(depth, qdefs.HO1, qdefs.HO5)
 
        self.HOweight = (
            "S 1--"
            + "0"
            + "-"
            + "0"
            + "-"
            + str(["0" for v in [0] * B3]).replace("'", "")
            + "-"
            + str(["0" for v in [0] * B4]).replace("'", "")
            + "-"
            + str(["0" for v in [0] * B5]).replace("'", "")
        )




    def init_bweights(self, scorelevel, HO2nodes):
        #print(f"Init bweight, scorelevel: {scorelevel}")
        B = self.B
        C = self.C
        H = self.H = HO2nodes
        cc = str(C)[1:]
        weight = self.weight
        depth = self.depth
        depth[HO5] = [B + 1] * H
        weight[HO0] = self.cascade_weights(depth, qdefs.HO1, qdefs.HO5)
        self.Bweight = "B 1--" + str(["0" for v in [0] * H]).replace("'", "")

    def update_weight(self, mode, category, c):
        # match (mode):
        if mode == "QC":
                weight = c["qcweight"]
        elif mode == "HE":
                weight = c["qcweight"] * self.weight[HE0] + c["heweight"]
        elif mode == "HO":
                weight = c["qcweight"] * self.weight[HO0] + c["howeight"]
        elif mode == "BI":
                weight = c["qcweight"] * self.weight[B0] + c["biweight"]
        else:
            breakpoint()
        c["mode"] = mode
        c["levels"] = category
        c["weight"] = weight
        return weight

    def compute_weight(self, wpairs, bquality):

        quality = {q.name : None for q in qdefs if q.value < QL}
        quality[QN8] = 0

        # down =  [d[0] for d in downfloaters]
        for c in wpairs:
            # print(c['ca'], c['cb'], c['quality'][QN8])
            
            self.get_edge_quality(c)
            q = c["quality"]
            for elem in range(QL):
                nelem = qdefs(elem).name
                if elem < qdefs.HE1.value or (c.get("mode", "") == "HE" and elem < qdefs.HO1.value) or (c.get("mode", "") == "HO" and elem >= qdefs.HO1.value):
                    if q[nelem] is None:
                        pass
                    elif quality[nelem] is None:
                        quality[nelem] = q[nelem]
                    elif isinstance(quality[nelem], int):
                        quality[nelem] += q[nelem]
                    else:
                        for i in range(len(quality[nelem])):
                            quality[nelem][i] += q[nelem][i]

        return quality

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
            breakpoint()
            raise
        ptr = list(f)
        for i, c in enumerate(wres):
            ptr[index[i]] = str(c)
        return "".join(ptr)
    

    def format_weight(self, mode, w):
        weight = self.weight
        f = self.QCweight
        # match (mode):
        if mode == "HE":
                f += " " + self.HEweight
                cw = w // weight[HE0]
                ew = w % weight[HE0]
                return self.format_wpart(self.QCweight, cw, qdefs.QC6, qdefs.QC21) + " " + self.format_wpart(self.HEweight, ew, qdefs.HE1, qdefs.HE2)
        elif mode == "HO":
                f += " " + self.HOweight
                cw = w // weight[HO0]
                sw = w % weight[HO0]
                return self.format_wpart(self.QCweight, cw, qdefs.QC6, qdefs.QC21) + " " + self.format_wpart(self.HOweight, sw, qdefs.HO1, qdefs.HO5)
        elif mode == "BI":
                f += " " + self.Bweight
                cw = w // weight[B0]
                bw = w % weight[B0]
                return self.format_wpart(self.QCweight, cw, qdefs.QC6, qdefs.QC21) + " " + self.format_wpart(self.Bweight, bw, qdefs.HO5, qdefs.HO5)
        else:
                cw = w
                return self.format_wpart(self.QCweight, cw, qdefs.QC6, qdefs.QC21)


    def compute_pab_weight(self, edges):
        for edge in edges:
            edge["weight"] = edge["sb"] if edge["ca"] == 0 else 0

