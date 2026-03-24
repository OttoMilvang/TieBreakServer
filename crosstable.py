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
C6 = qdefs.C6.value
C7 = qdefs.C7.value
N8 = qdefs.N8.value
C8 = qdefs.C8.value
C9 = qdefs.C9.value
MM = qdefs.MM.value
C10 = qdefs.C10.value
C11 = qdefs.C11.value
C12 = qdefs.C12.value
C13 = qdefs.C13.value
C14 = qdefs.C14.value
C15 = qdefs.C15.value
C16 = qdefs.C16.value
C17 = qdefs.C17.value
C18 = qdefs.C18.value
C19 = qdefs.C19.value
C20 = qdefs.C20.value
C21 = qdefs.C21.value
E1 = qdefs.E1.value
E2 = qdefs.E2.value
S1 = qdefs.S1.value
S2 = qdefs.S2.value
S3 = qdefs.S3.value
S4 = qdefs.S4.value
S5 = qdefs.S5.value
IW = qdefs.IW.value
QL = qdefs.QL.value
C0 = qdefs.C0.value
E0 = qdefs.E0.value
S0 = qdefs.S0.value
B0 = qdefs.B0.value
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
            "XC6": "XC6" in experimental,
            "XC7": "XC7" in experimental,
            "XC8": "XC8" in experimental,
            "XC9": "XC9" in experimental,
            "XC14": "XC14" in experimental,
            "XC14M1": "XC14M1" in experimental,
            "XC16": "XC16" in experimental,
            "XC16M1": "XC16M1" in experimental,
            "XCTOPM1": "XTOPM1" in experimental,
        }
        self.scalars = [C6, N8, C9, C10, C11, C12, C13, C14, C15, C16, C17, S1, S2, IW]

    def init_engine(self, tournament, rnd, maxmeets, topcolor, unpaired, rank):
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
        (competitors, opponents) = self.list_edges(cmps, maxmeets, topcolor, unpaired, prohibited)
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
            tb.compute_tiebreak(mytb)
        return tb.cmps

    def list_edges(self, cmps, maxmeets, topcolor, unpaired, prohibited):
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
                "rfp": tbval[RFP]["val"] != "" if tbval and i not in unpaired else False,
                "pop": int(tbval[RFP]["val"][0:-1]) if tbval and len(tbval[RFP]["val"]) > 1 else -1,
                "pco": tbval[RFP]["val"][-1:] if tbval and len(tbval[RFP]["val"]) > 1 else "",
                "hst": tbval[RFP] if tbval else {},
                "num": tbval[NUM]["val"] if tbval else 0,
                "rip": tbval[RIP]["val"] if tbval else 0,
                "met": tbval[NUM] if tbval else {},
                "cod": tbval[COD]["val"] if tbval else 0,
                "cop": tbval[COP]["val"] if tbval else "  ",
                "csq": " " + tbval[CSQ]["val"] if tbval else " ",
                "flt": tbval[FLT]["val"] if tbval else 0,
                "top": tbval[TOP]["val"] if tbval else False,
            }
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
            bhasmet = [opp for (key, opp) in b["met"].items() if key != "val"]
            for j in range(i+1):
                a = competitors[j]
                opponents[j][i] = opponents[i][j] = self.create_edge(a, b, bhasmet)

        # Set c["w] and c["b"]
        if self.checkonly:
            for i in range(size):
                a = competitors[i]
                for j in range(size):
                    b = competitors[j]
                    c = opponents[i][j]
                    if a["pop"] == j:
                        c["canmeet"] = c["qc"] = True
                        if a["pco"] == "w" or b["pco"] == "w":
                            c[a["pco"]] = i
                            c[b["pco"]] = j
                        # print(i, j, c['canmeet'], c['w'] if 'w' in c else '?', c['b'] if 'b' in c else '?' )
                    else:
                        c["canmeet"] = c["qc"] = False
                        
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
            # C1 and C2 meetmax = 1
            "canmeet": False,
            "isblob": b["cid"] == self.BLOB,
            "played": played,
            "bun": self.rnd - 1 - b["num"], # Unplayd games by b, for c9-calculations
            "qlevel": -1, # quality was calulated for scorelevel ...
            "quality": None,
            "weight": 0,
            "cweight": 0,
            "eweight": 0,
            "sweight": 0,
            "iweight": 0,
            "colordiff": "  ",
            "qc": False,
        }
        # C3 not-topscorers with absolute color preference cannot meet
        canmeet = played < self.maxmeets and ca != cb and a["rfp"] and b["rfp"] or ca < self.BLOB and cb == self.BLOB
        for col in ["w", "b"]:
            col2 = col + "2"
            if a["cop"] == col2 and b["cop"] == col2 and (not a["top"]) and (not b["top"]):
                canmeet = False
            if a["cod"] * b["cod"] >= 4 and (not a["top"]) and (not b["top"]):
                canmeet = False
        # score diff
        c["psd"] = abs(sa - sb)
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
        c["quality"] = [None] * QL
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
            q[C6] = 0
            q[C7] = [0] * (maxpsd)
            q[N8] = 0
            q[C8] = [0] * (maxpsd + 1)
            q[C9] = 0
            q[MM] = [0] * (self.maxmeets-1)
            for elem in range(C10, C18):
                q[elem] = 0
            for elem in range(C18, C21 + 1):
                q[elem] = [0] * maxpsd

            level = a["scorelevel"] - scorelevel

            c14 = c15 = c16 = c17 = 0
            if a["scorelevel"] >= scorelevel and b["scorelevel"] == scorelevel:
                if self.pablevel and b["scorelevel"] == 0:
                    q[C9] = self.rnd - 1 - a["num"]
                    cweight += weight[C9] * q[C9]

                if c["canmeet"] and c["played"] > 0 and self.maxmeets > 1:
                    q[MM][c["played"]-1] = 1  

                # Topscorere

                if (a["top"] or b["top"]) and a["cid"] > 0 and b["cid"] > 0:
                    # if scorelevel == 9 and a["cid"] ==3 and b["cid"] == 9: breakpoint()

                    # c10 minimize the number of topscorers who get color diff > +2 or < -2
                    # print(c, a['cod'], b['cod'])
                    # apf = a["cod"] + 1 if a["cid"] == c["w"] else a["cod"] - 1
                    # bpf = b["cod"] + 1 if b["cid"] == c["w"] else b["cod"] - 1
                    # q[C10] = 1 if abs(apf) > 2 and abs(bpf) >= 2 or abs(apf) >= 2 and abs(bpf) > 2 else 0

                    acod = a["cod"]
                    bcod = b["cod"]
                    if acod == bcod and abs(acod) >= 2:
                        q[C10] = 1
                        cweight += weight[C10]

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
                            q[C11] = 1
                            cweight += weight[C11]

                    if scorelevel == -1:
                         print(f"A: {a['cid']:2} {a['cod']:2} {a['csq'][-2:]} {a['cop']},   B: {b['cid']:2} {b['cod']:2} {b['csq'][-2:]} {b['cop']},  Q10: {q[C10]} Q11: {q[C11]}")


                # c12 minimize the number of players who do not get their color preference
                if a["cop"] != "  " and a["cop"][0].lower() == b["cop"][0].lower():
                    q[C12] = 1
                    cweight += weight[C12]

                # c13 minimize the number of players who do not get their strong color preference
                if q[C12] == 1 and int(a["cop"][1]) > 0 and int(b["cop"][1]) > 0:
                    q[C13] = 1
                    cweight += weight[C13]

                c["colordiff"] = coltrans.get(a["cop"], a["cop"][0].upper()) + coltrans.get(b["cop"], b["cop"][0].upper())

                # c15 minimize the number of players who receive upfloft in the previous round
                c15 = 1 if (a["acc"] < b["acc"]) and (a["flt"] & UF1) or (a["acc"] > b["acc"]) and (b["flt"] & UF1) else 0
                if c15:
                    q[C15] = 1
                    cweight += weight[C15]

                # c17 minimize the number of players who receive upfloft two rounds before
                c17 = 1 if (a["acc"] < b["acc"]) and (a["flt"] & UF2) or (a["acc"] > b["acc"]) and (b["flt"] & UF2) else 0
                if c17:
                    q[C17] = 1
                    cweight += weight[C17]

            elif a["scorelevel"] >= scorelevel and b["scorelevel"] < scorelevel:
                q[C6] = 1
                cweight += weight[C6]
                if level > 0:
                    # q[C7] = [1 if level == maxpsd - i else 0 for i in range(maxpsd)]
                    q[C7][maxpsd - level] = 1
                    cweight += weight[C7][maxpsd - level]

                if self.pablevel and b["scorelevel"] == 0:
                    q[C9] = self.rnd - 1 - a["num"]
                    cweight += weight[C9] * q[C9]

                # c14 minimize the number of players who receive downfloat in the previous round
                c14 = 1 if (a["flt"] & DF1) else 0
                if c14 and scorelevel == a["scorelevel"]:
                    q[C14] = 1
                    cweight += weight[C14]

                # c16 minimize the number of players who receive downfloat two rounds before
                c16 = 1 if a["flt"] & DF2 else 0
                if c16 and scorelevel == a["scorelevel"]:
                    q[C16] = 1
                    cweight += weight[C16]

            # c18-21 minimize the score difference of players who receive downfloat/upfloat in the previous round
            for cnn, val in enumerate([(level if cxx else 0) for cxx in [c14, c15, c16, c17]], start=C18):
                if val > 0:
                    q[cnn][maxpsd - val] = 1
                    cweight += weight[cnn][maxpsd - val]

            scorelevel2 = scorelevel - 1
            # print("N8", scorelevel2, a['cid'], b['cid'], a['scorelevel'], b['scorelevel'], "            ", a['scorelevel'] >= scorelevel2 and b['scorelevel'] < scorelevel2)
            # if scorelevel == testlevel and update_maxpsd:
            #    breakpoint()
            if a["scorelevel"] >= scorelevel2 and b["scorelevel"] < scorelevel2:
                q[N8] = 1
                cweight += weight[N8]
                level = max(a["scorelevel"], b["scorelevel"]) - scorelevel2
                if level > 0:
                    # q[C8] = [1 if level == maxpsd + 1 - i else 0 for i in range(maxpsd+1)]
                    q[C8][maxpsd + 1 - level] = 1
                    cweight += weight[C8][maxpsd + 1 - level]

            c["qc"] = q[C9] + sum(q[MM]) + (sum(q[C10:C11 + 1]) + sum(q[C14:C17 + 1]) + sum(q[C18]) + sum(q[C19]) + sum(q[C20]) + sum(q[C21])) == 0
            c["cweight"] = cweight

    def update_hetrogenious(self, scorelevel, nodes, edges, bsn):
        M = self.M = sum(self.mdp)
        self.ilen = 0
        elen = len(bsn) + 1
        weight = self.weight
        self.init_eweights(scorelevel, bsn)
        for c in edges:
            (ca, cb) = (c["ca"], c["cb"])
            q = self.get_edge_quality(c)["quality"]
            q[E1] = [0] * M
            q[E2] = [0] * M
            eweight = 0
            e1weight = sum(weight[E1])

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
                q[E1][e0-1] = e1
                q[E2][e0-1] = e2
                eweight += weight[E1][e0 - 1] * e1
                eweight += weight[E2][e0-1] * e2

            c["eweight"] = eweight

    def update_homogenious(self, scorelevel, edges, bsn, S):
        B = self.B = len(bsn)
        mdp = B - 2 * S
        B3 = self.B3 = S
        B4 = self.B4 = B - S
        B5 = self.B5 = B - 1
        self.ilen = 0
        # print ("BO:", B, S)
        weight = self.weight
        self.init_sweights(scorelevel, S, mdp)
        # print("CheckAnlyse", scorelevel, "M="+str(M), "P="+str(P), "N="+str(N), "S="+str(S), "B="+str(B) )
        # s4weight = sum([weight[S4][i] for i in range(B4)])
        s4weight = sum(weight[S4])
        for c in edges:
            c["sweight"] = 0
            (ca, cb) = (c["ca"], c["cb"])
            q = self.get_edge_quality(c)["quality"]
            q[S1] = 0
            q[S2] = 0
            q[S3] = [0] * B3
            q[S4] = [1] * B4
            q[S5] = [0] * B5
            sweight = s4weight
            ascl = self.competitors[ca]["scorelevel"]
            bscl = self.competitors[cb]["scorelevel"]
            if ascl == scorelevel and bscl == scorelevel:
                absn = bsn[ca]
                bbsn = bsn[cb]
                if absn > bbsn:
                    (absn, bbsn, ascl, bscl) = (bbsn, absn, bscl, ascl)

                if c["canmeet"]:
                    if absn > S:
                        q[S1] = 1
                        sweight += weight[S1]
                    q[S2] = absn - 1
                    sweight += (absn - 1) * weight[S2]
                    if absn <= S:
                        q[S3][S - absn] = 1
                        sweight += weight[S3][S - absn]
                    else:
                        q[S4][absn - S - 1] = 0
                        sweight -= weight[S4][absn - S - 1]
                    q[S5][absn - 1] = bbsn - absn
                    sweight += weight[S5][absn - 1] * (bbsn - absn)
                    # if c['quality'][S5] != [bbsn if absn == i+1 else 0 for i in range(B)]: breakpoint()
            c["sweight"] = sweight

    def update_bipartite(self, scorelevel, pairs, bsn, s2start, s2stop):
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
            if s2start <= ca <= s2stop:
                (ca, cb) = (cb, ca)
            c = self.get_edge_quality(self.opponents[ca][cb])
            q = c["quality"]
            if q[E1] is None or len(q[E1]) != M:
                q[E1] = [0] * M
                q[E2] = [0] * M
            q[S1] = 0
            q[S2] = 0
            q[S3] = 0
            q[S4] = 0
            q[S5] = [0] * H
            if pno >= mdp:
                absn = pno - mdp
                bbsn = bsn[cb]
                q[S5][absn] = bbsn -absn
                bweight = weight[S5][absn] * (bbsn - absn)
            c["bweight"] = bweight

    # Compute weight
    # mode 'E' - Hetrogenous
    # mode 'S' - Homogenous
    # mode 'B' - Bipartite
    # mode 'A' - Add S-part

    def cascade_weights(self, depth, start, stop):
        w = 1
        weight = self.weight
        for cval in range(stop, start-1, -1):
            if isinstance(depth[cval], int):
                (w, weight[cval], depth[cval]) = (w*depth[cval], w, len(str(depth[cval])))
            elif isinstance(depth[cval], list):
                weight[cval] = [0]*len(depth[cval])
                for eval in range(len(weight[cval])-1, -1, -1):
                    (w, weight[cval][eval], depth[cval][eval]) = (w*depth[cval][eval], w, len(str(weight[cval][eval])))
            else:
                raise
        return w



    def init_cweights(self, scorelevel, nodes):
        # print(f"Init cweight, scorelevel: {scorelevel}")
        cc = len(nodes) + 1
        c7len = len(self.mdp)
        c8len = c7len + 1
        mmlen = self.maxmeets -1
        self.weight = weight = [0] * QS
        self.depth  = depth  = [0] * QS
        scoregroup = [node for node in nodes if node["scorelevel"] >= scorelevel] 
        nscoregroup = [node for node in nodes if node["scorelevel"] >= scorelevel-1] 
        bsize = len(scoregroup)
        depth[C6] = bsize +1
        depth[C7] = [psd + 1 for psd in self.mdp ]
        depth[N8] = len(nscoregroup) + 1
        depth[C8] = [psd + 1 for psd in self.mdp ] + [bsize + 1 - sum(self.mdp) ] 
        depth[C9] = bsize + 1 if scorelevel <= self.pablevel else 1
        depth[MM] = [cc] * mmlen
        for i in range(mmlen):  
            depth[MM][i] = cc
        depth[C10] = len([node for node in nodes if node["scorelevel"] >= scorelevel and node["top"]]) +1
        depth[C11] = depth[C10]
        depth[C12] = cc
        depth[C13] = cc
        depth[C14] = len([node for node in nodes if node["scorelevel"] >= scorelevel and (node["flt"] & DF1)]) +1
        depth[C15] = len([node for node in nodes if node["scorelevel"] <= scorelevel and (node["flt"] & UF1)]) +1
        depth[C16] = len([node for node in nodes if node["scorelevel"] >= scorelevel and (node["flt"] & DF2)]) +1
        depth[C17] = len([node for node in nodes if node["scorelevel"] <= scorelevel and (node["flt"] & UF2)]) +1
        depth[C18] = [psd + 1 for psd in self.mdp ]
        depth[C19] = [psd + 1 for psd in self.mdp ]
        depth[C20] = [psd + 1 for psd in self.mdp ]
        depth[C21] = [psd + 1 for psd in self.mdp ]
        # print(scorelevel, depth)
        weight[C0] = self.cascade_weights(depth, C6, C21)

        self.Cweight = (
            "C 1--"
            + "0"  # C6
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # C7
            + "-"
            + "0"  # N8
            + "-"
            + str(["0" for v in [0] * c8len]).replace("'", "")  # C8
            + "-"
            + "0"  # C9
            + "-"
            + str(["0" for v in [0] * mmlen]).replace("'", "")  # MM
            + "-"
            + "0"  # C10
            + "-"
            + "0"  # C11
            + "-"
            + "0"  # C12
            + "-"
            + "0"  # C13
            + "--"
            + "0"  # C14
            + "-"
            + "0"  # C15
            + "-"
            + "0"  # C16
            + "-"
            + "0"  # C17
            + "--"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # C18
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # C18
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")  # C20
            + "-"
            + str(["0" for v in [0] * c7len]).replace("'", "")
        )  # C21

 


    def init_eweights(self, scorelevel, bsn):
        # print(f"Init eweight, scorelevel: {scorelevel}")
        M = self.M
        elen = len(bsn) + 1 - M
        weight = self.weight
        depth = self.depth
        depth[E1] = [2] * M
        depth[E2] = [elen] * M
        weight[E0] = self.cascade_weights(depth, E1, E2)
        self.Eweight = "E 1--" + str(["0" for v in [0] * M]).replace("'", "") + "-" + str(["0" for v in [0] * M]).replace("'", "")


    def init_sweights(self, scorelevel, S, mdp):
        # print(f"Init sweight, scorelevel: {scorelevel}")
        B = self.B # len of BSN
        B3 = self.B3
        B4 = self.B4
        B5 = self.B5
        weight = self.weight
        depth = self.depth

        depth[S1] = S + 1
        depth[S2] = sum(list(range(B-1, S, -2)[:S])) + 1 # B-1 + B-3 + ... + B-(2*S-1) + 1, first S odd numbers starting from B-1 
        depth[S3] = [2] * B3
        depth[S4] = [2] * B4
        depth[S5] = list(range(B5, 0, -1))
        weight[S0] = self.cascade_weights(depth, S1, S5)
 
        self.Sweight = (
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




    def init_bweights(self, scorelevel, s2nodes):
        #print(f"Init bweight, scorelevel: {scorelevel}")
        B = self.B
        C = self.C
        H = self.H = s2nodes
        cc = str(C)[1:]
        weight = self.weight
        depth = self.depth
        depth[S5] = [B + 1] * H
        weight[S0] = self.cascade_weights(depth, S1, S5)
        self.Bweight = "B 1--" + str(["0" for v in [0] * H]).replace("'", "")

    def update_weight(self, mode, c):
        # print ("BW:", B)

        c["mode"] = mode

        # match (mode):
        if mode == "C":
                weight = c["cweight"]
        elif mode == "E":
                weight = c["cweight"] * self.weight[E0] + c["eweight"]
        elif mode == "S":
                weight = c["cweight"] * self.weight[S0] + c["sweight"]
        elif mode == "B":
                weight = c["cweight"] * self.weight[B0] + c["bweight"]
        c["weight"] = weight
        return weight

    def compute_weight(self, wpairs, bquality):

        quality = [None] * QL
        quality[N8] = 0

        # down =  [d[0] for d in downfloaters]
        for c in wpairs:
            # print(c['ca'], c['cb'], c['quality'][N8])
            
            self.get_edge_quality(c)
            q = c["quality"]
            for elem in range(QL):
                if elem < E1 or (c.get("mode", "") == "E" and elem < S1) or (c.get("mode", "") == "S" and elem >= S1):
                    if q[elem] is None:
                        pass
                    elif quality[elem] is None:
                        quality[elem] = q[elem]
                    elif isinstance(quality[elem], int):
                        quality[elem] += q[elem]
                    else:
                        for i in range(len(quality[elem])):
                            try:
                                quality[elem][i] += q[elem][i]
                            except:
                                breakpoint()

        return quality

    def format_wpart(self, f, wx, start, stop):
        weight = self.weight
        wres = []
        for welem in range(start, stop+1):
            warr = weight[welem]
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
        f = self.Cweight
        # match (mode):
        if mode == "E":
                cw = w // weight[E0]
                ew = w % weight[E0]
                return self.format_wpart(self.Cweight, cw, C6, C21) + " " + self.format_wpart(self.Eweight, ew, E1, E2)
        elif mode == "S":
                f += " " + self.Sweight
                cw = w // weight[S0]
                sw = w % weight[S0]
                return self.format_wpart(self.Cweight, cw, C6, C21) + " " + self.format_wpart(self.Sweight, sw, S1, S5)
        elif mode == "B":
                f += " " + self.Bweight
                cw = w // weight[B0]
                bw = w % weight[B0]
                return self.format_wpart(self.Cweight, cw, C6, C21) + " " + self.format_wpart(self.Bweight, bw, S5, S5)
        else:
                cw = w
                return self.format_wpart(self.Cweight, cw, C6, C21)


    def compute_pab_weight(self, edges):
        for edge in edges:
            edge["iweight"] = edge["sb"] if edge["ca"] == 0 else 0

