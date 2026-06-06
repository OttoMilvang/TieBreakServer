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
from collections import defaultdict
import networkx as nx

# from networkx.algorithms import bipartite
from crosstable import crosstable
from crosstabledutch import crosstable_dutch, qdefs, flt
from pairing import pairing
import helpers


"""
Structre 

    Values: max players N=1000,  max rounds R=100, moved down players M, maxpsd P, maxbsn B, pairs S
    weight =
        positions               - value      
    c6 - c21
        1                       - 1 Start with 1 
        R**P                    - c6 100**psdlevel 
        R                       - c10
        R                       - c11
        N                       - c12
        N                       - c13
        R                       - c14
        R                       - c15
        R                       - c16
        R                       - c17
        R**P                    - c18 100**psdlevel 
        R**P                    - c19 100**psdlevel 
        R**P                    - c20 100**psdlevel 
        R**P                    - c21 100**psdlevel 
    HE1-HE2 hetrogenios
        R**M                    - R**(bsn mdp)
        R**M                    - R**(bsn mdp)*(bsn opponent)
    HO1-HO5 homogenious
        R                       - 1 if bsn > r else 0
        R*R                     - bsn
        10**S                   - 10**bsn if wsn <=r
        10**(B-S)               - 10**bsn if wsn >r
        10**(B-1)               - 10**(n-wbsn)*bbsn



"""


class pairing_dutch(pairing):

    DUTCH_RULES = {
        0 : "2022-01-01",
        1 : "2026-02-01",   # Approved by FIDE Council on 01/02/2026
        } 

    # constructor function
    def __init__(self, tournament, rnd, params):
        # helpers.json_output(sys.stdout, cmps[12]['tiebreakDetails'])
        super().__init__(tournament, rnd, params)
        self.rules = self.DUTCH_RULES[1]
 
    def get_crosstable(self, experimental, checkonly, verbose):
        return crosstable_dutch(experimental, checkonly, verbose)

    def qdefs_enum(self):
        return qdefs

    def pair_bracket(self, scorelevel, nodes, edges, testpab):
        bracket = {
            "scorelevel": scorelevel,
            "competitors": [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel],
            "pairs": [],
            "downfloaters": [],
            "remaining": [],
            "quality": {q.name : None for q in qdefs },
            "bsne": self.update_bsn(scorelevel, nodes),
            "bsno": {},
            "pab": scorelevel == self.pablevel,
        }

        showtime = self.showtime
        self.crosstable.set_scorelevel(scorelevel)
        pabbracket = self.apply_c9(scorelevel, nodes, edges, testpab)
        t0 = time.time()
        category = self.get_category(scorelevel, nodes, edges)

        if self.reportlevel >= 2 and scorelevel < len(self.crosstable.levels()):
            print("================================================")
            print("Scorelevel: ", scorelevel, ", bsn: ", len(bracket["bsne"]), ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Bracket       = ", self.crosstable.levels()[scorelevel])
            print("Pabbracket    = ", pabbracket, "PAB" if scorelevel == self.pablevel else "")
            print("Category      = ", category)
        elif self.verbose:
            print("Scorelevel: ", scorelevel, ", bsn: ", len(bracket["bsne"]), ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Category      = ", category)

        self.crosstable.update_crosstable(scorelevel, nodes, edges, pabbracket)
        t1 = time.time()
        if showtime and self.reportlevel >= 2 and scorelevel < len(self.crosstable.levels()):
            print("Time          = ", t1 - t0)

        # print(nodes[0])

        # print("Cat", self.checkonly, scorelevel, category)
        testpab = category == 0 or category > 1
        numpairs = 0  # Number of homogenious pairs
        wpairs = []
        if category == -1 and not self.checkonly:
            (_, bracket["downfloaters"]) = (bracket["downfloaters"], bracket["competitors"].copy())
            (_, bracket["remaining"]) = (bracket["remaining"], [c["cid"] for c in nodes if c["scorelevel"] < scorelevel])
            return (bracket, nodes, edges, testpab)

        if self.reportlevel:
            bcompetitors = [c for c in bracket["competitors"]]

        for pairingmode in ["BI", "HE", "HO"]:  # B = bipartite, E = hetrogenious, T = homogenious
            t0 = time.time()
            if pairingmode == "BI":
                (weighted, pairsleft, pairs) = self.pair_simple_round(bracket, nodes, edges, pairingmode, numpairs, category)
            else:
                (weighted, pairsleft, pairs) = self.pair_round(bracket, nodes, edges, pairingmode, numpairs, category)

            t1 = time.time() - t0
            self.timer[pairingmode] = t1 if not self.timer.get(pairingmode) else self.timer[pairingmode] + t1

            if self.verbose:
                npairs = len(pairs) if pairs else 0
                print(f"{'Check ' if self.checkonly else 'Pair  '} round: {self.rnd}, Scorelevel: {scorelevel:2}, Pairs: {pairingmode} - {npairs:2}, {t1:.2f}s")

            if pairs is None:
                continue
            paired = []
            # if scorelevel ==1 and category > 0:breakpoint()

            bipartite = pairingmode == "BI"
            hetro = pairingmode == "HE"
            for a, b in pairs:
                c = self.opponents[a][b]
                (alevel, blevel) = (c["sa"], c["sb"]) if c["sa"] >= c["sb"] else (c["sb"], c["sa"])
                if hetro and alevel > scorelevel and blevel == scorelevel or not hetro:
                    wpairs.append(c)
                if bipartite or (hetro and alevel > scorelevel or not hetro and alevel == scorelevel) and blevel == scorelevel:
                    paired.append(c)
                elif hetro and alevel == scorelevel and blevel <= scorelevel:
                    numpairs += 1 if alevel == scorelevel and blevel == scorelevel else 0
                # elif hetrogenious and alevel > scorelevel and blevel < scorelevel:
                #    self.competitors[a if c["sa"] > scorelevel else b]['lmb'] = scorelevel

            if not weighted:
                numpairs = pairsleft

            if len(paired) > 0:
                bracket["pairs"] += paired
                (nodes, edges, npaired) = self.remove_pairs(nodes, edges, paired)
            else:
                npaired = []

            for pair in bracket["pairs"]:
                self.update_color(pair)

            if self.reportlevel > 1 and scorelevel < len(self.crosstable.levels()):
                print("-Mode", pairingmode)
                print("Competitors   = ", bcompetitors)
                print("Pairs         = ", [(c["w"], c["b"]) for c in bracket["pairs"]])
                if pairingmode == "HO":
                    print("Down          = ", [c for c in bracket["downfloaters"]])
                bcompetitors = [c for c in bracket["competitors"] if c not in npaired]
            if pairingmode == "BI" and pairsleft == 0:
                break
        bracket["remaining"] = [c["cid"] for c in nodes if c["scorelevel"] < scorelevel]
        bracket["downfloaters"] = [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel]
        if len(bracket["pairs"]): #  and pairingmode != "BI":
            bracket["quality"] = self.crosstable.compute_weight(wpairs, bracket["quality"]) 
        else:
            testpab = False
        return (bracket, nodes, edges, testpab)

    def update_board(self, roundpairing):
        pairs = []
        cmp = self.competitors
        for bracket in roundpairing:
            for pair in bracket["pairs"]:
                #self.update_color(pair)
                (w, b) = (pair["w"], pair["b"])
                (ws, bs) = (cmp[w]["acc"], cmp[b]["acc"])
                ipab = w == 0 or b == 0
                maxs = max(ws, bs)
                sums = ws + bs
                rank = w if w < b else b
                pairs.append(
                    {
                        "pair": pair,
                        "ipab": ipab,
                        "maxs": maxs,
                        "sums": sums,
                        "rank": rank,
                    }
                )
                board = 0
        npairs = []
        for pair in sorted(pairs, key=lambda c: (c["ipab"], -c["maxs"], -c["sums"], c["rank"])):
            npair = pair["pair"]
            (w, b) = (npair["w"], npair["b"])
            board += 1
            if self.reportlevel > 2:
                print(
                    "Board: ",
                    board,
                    w,
                    b,
                    pair["ipab"],
                    pair["maxs"],
                    pair["sums"],
                    pair["rank"],
                )
            npair["board"] = board
            npairs.append(npair)
        return npairs

    """
    update_bsn
    Competitors are sorted on score_level and then on TPN

    """

    def update_bsn(self, scorelevel, competitors):
        bsn = {}
        for i in range(len(competitors)):
            if competitors[i]["scorelevel"] < scorelevel:
                return bsn
            bsn[competitors[i]["cid"]] = i + 1
        return bsn

    """
    apply_c9
    Determine if c9 shall be used
    Minimise the number of unplayed games of the assignee of the pairing-allocated-bye.
    Apply to brackets that downfloat exactly one player, 
    who will end up receiving the pairing-allocated bye
    """

    def apply_c9(self, scorelevel, nodes, edges, testpab):
        if scorelevel > self.pablevel:
            return False
        # print("Testpab-I",  scorelevel, testpab, self.roundpairing[-1]["quality"][QN8] if testpab else -1)
        if scorelevel <= 1:
            return True
        if not self.optimize and testpab and len(self.roundpairing) > 0:
            #    print("Testpab-N", scorelevel, self.roundpairing[-1]["quality"][QN8])
            return self.roundpairing[-1]["quality"][qdefs.QN8.name] == 1
        c9_nodes = [node for node in nodes if node["scorelevel"] >= scorelevel or node["cid"] == 0]
        # print("Testpab-F",  scorelevel, len(c9_nodes), [node["scorelevel"] for node in c9_nodes])
        if len(c9_nodes) % 2 == 1:
            return False
        c9_edges = self.get_edges(c9_nodes, edges)
        rest_nodes = list(filter(lambda node: node["scorelevel"] < scorelevel and node["cid"] != 0, nodes))
        rest_edges = self.get_edges(rest_nodes, edges)
        (_, c9_rest, _) = self.is_complete(c9_nodes, c9_edges)
        (_, c9_rest, _) = self.is_complete(rest_nodes, rest_edges) if c9_rest == 0 else (0, c9_rest, 0)
        # print("Testpab-Y",  scorelevel, len(c9_nodes), c9_rest == 0)
        return c9_rest == 0

    """
    General pairing 
    Weighthed pairing will always be correct, but the number of edges is 
    in the order P**2 where P is the number of players. For more than 500 players
    the weighted method is slow, and may stop due to high memory consumtion. 

    Therfore if no switches say otherwise the program will first try a simple
    algorithm, and then the weighted.    
   
    pair_pab(nodes, edges)

    """

    """
    category - level of simplifications

        Check if this scorelevel is pairable by itself
        # If so we replace all nodes lower than scorelevel with BLOB
        # Category -1 => None can meet
        # Category 0 => Full scan needed
        # Category 1 => current scorelevel and next scorelevel is pairable with max 1 df
        # Category >1 =>The remaining before and after next "category" scorelevel is pairable with max 1 df

    """

    def get_category(self, scorelevel, nodes, edges):
        testlevel = -1
        # breakpoint()
        if not self.optimize:
            return 0
        if scorelevel < self.pablevel:
            return 0

        # thislevel = sum([1 for node in nodes if node["scorelevel"] >= scorelevel])
        cat1 = False
        hamilton = self.hamilton
        if scorelevel == testlevel:
            breakpoint()
        if len(edges) == 0:
            raise  
        if edges[0]["sa"] < scorelevel or edges[0]["sb"] < scorelevel:
            return -1  # There are no pairing for this scorebracket
        if edges[0]["sa"] == 1 and edges[0]["sb"] == 1:
            return 1  # Last scoregroup is always pairable
        if hamilton[scorelevel].get("rem_unpaired", 2) > 1 or scorelevel < self.pablevel:
            return 0

        shamilton = hamilton[scorelevel]
        if scorelevel == 1:
            return 1 if shamilton["rem_hamilton"] > 0 else 0
        top_nodes = bot_nodes = nodes
        top_edges = bot_edges = edges
        for level in range(scorelevel, 0, -1):
            # if level == 1 or level <= self.pablevel: return 0
            if scorelevel == testlevel:
                breakpoint()
            (top_nodes, top_edges) = self.select_nodes_and_edges(nodes, edges, level, self.levels)
            lhamilton = hamilton[level]
            (shamilton["this_pairs"], shamilton["this_rest"], shamilton["this_hamilton"]) = self.is_complete(
                top_nodes, top_edges
            )
            rhamilton = hamilton[level - 1]
            if level == scorelevel and shamilton["this_rest"] == 0:
                if rhamilton.get("rem_hamilton", -1) <= 0:
                    (bot_nodes, bot_edges) = self.select_nodes_and_edges(bot_nodes, bot_edges, 0, level - 1)
                    (shamilton["mod_pairs"], shamilton["mod_unpaired"], _) = self.is_complete(bot_nodes, bot_edges)
                    if shamilton["mod_unpaired"] > 0:
                        return 0  # Remaining can not be paired
                if rhamilton.get("rem_hamilton", -1) > 0:
                    if len(top_nodes) % 2:
                        raise
                    return 1
            tmeet = (
                shamilton.get("this_hamilton", -1) > 0
                and lhamilton.get("cur_hamilton", -1) > 0
                and lhamilton.get("cross_hamilton", -1) >= 0
                and lhamilton.get("rem_hamilton", -1) > 0
            )
            if scorelevel == testlevel:
                print(
                    "Tmeet",
                    level,
                    tmeet,
                    shamilton.get("this_hamilton", -1),
                    lhamilton.get("cur_hamilton", -1),
                    lhamilton.get("cross_hamilton", -1),
                    lhamilton.get("rem_hamilton", -1),
                )
            cat1 = cat1 and tmeet
            if shamilton.get("rem_hamilton", -1) <= 0:
                return 1 if cat1 else 0  # Dont wait time to see if rest is complete
            if tmeet:
                category = scorelevel - level + 1
                ok = category > 1 or level > self.pablevel and len(top_nodes) % 2 == 0
                if scorelevel == testlevel:
                    print("Cat x", ok)
                if ok and category == 2 and cat1:
                    category = 1
                # if thislevel > 1 and thislevel%2==1 and category == 1: breakpoint()
                if scorelevel == testlevel and ok:
                    print("Cat r", category)
                if ok:
                    return category
                cat1 = True
        if scorelevel == testlevel:
            print("Cat r", 0)
        return 0

    def modify_edges(self, S1nodes, S2nodes, edges, scorelevel, category, condition):
        testlevel = -1
        if category == 0:
            return (S1nodes, edges)
        new_edges = []
        add_edges = []
        cmp = self.competitors
        orgS2nodes = S2nodes

        opponents = self.opponents
        lim = scorelevel - category + 1
        nodeid1 = [node["cid"] for node in S1nodes if node["scorelevel"] >= lim]
        if S2nodes is None:
            (S2nodes, nodeid2) = (S1nodes, nodeid1)
            addblob = len(nodeid1) % 2 == 1
        else:
            nodeid2 = [node["cid"] for node in S2nodes if node["scorelevel"] >= lim]
            addblob = len(nodeid1) < len(nodeid2)
        new_edges = self.get_modifiededges(nodeid1, nodeid2, edges)
        if testlevel == scorelevel:
            breakpoint()
        if addblob:
            blob = 0 if self.pablevel >= scorelevel else self.crosstable.BLOB
            nodeid1.append(blob)
            S2nodesid = [node["cid"] for node in S2nodes if node["scorelevel"] == lim]

            if blob == 0:
                for node_id in S2nodesid:
                    new_edge = opponents[node_id][0]
                    if new_edge[condition]:
                        add_edges.append(new_edge)
            else:
                mid = self.edgeBinarySearch(edges, lim - 1)
                for edge in edges[mid:]:
                    if edge["ca"] in S2nodesid:
                        node_id = edge["ca"]
                    elif edge["cb"] in S2nodesid:
                        node_id = edge["cb"]
                    else:
                        continue
                    new_edge = self.crosstable.create_edge(cmp[node_id], cmp[blob])
                    if cmp[node_id]["flt"] & (flt.DF1.value + flt.DF2.value) > 0:
                        new_edge["qc"] = False
                    if new_edge[condition]:
                        add_edges.append(new_edge)
                        S2nodesid.remove(node_id)
                        if len(S2nodesid) == 0:
                            break
                # breakpoint()

            for edge in add_edges:
                node_id = edge["ca"] if edge["ca"] > 0 and edge["ca"] < blob else edge["cb"]
                if cmp[node_id]["flt"] & (flt.DF1.value + flt.DF2.value) > 0:
                    new_edge["qc"] = False

            new_edges += add_edges
            if len(add_edges) == 0:
                return (S1nodes, edges)
            new_nodes = [node for node in S1nodes if node["cid"] in nodeid1]
            new_nodes.append(cmp[blob])
            self.crosstable.update_crosstable(scorelevel, new_nodes, add_edges, self.pablevel, False)
        else:
            snodes = S1nodes + S2nodes if orgS2nodes is not None else S1nodes
            new_nodes = [node for node in snodes if node["cid"] in nodeid1]
        new_nodes = sorted(new_nodes, key=lambda s: (-s["scorelevel"], s[self.rank]))
        return (new_nodes, new_edges)

    def find_pab(self, nodes, edges):
        """
        Parameters
        ----------
        nodes : array of nodes
        edges : array of edges,

        Returns
        -------
        pab : scorelevel on pab

        """
        pab = self.pablevel
        cmp = self.competitors
        hamilton = self.hamilton
        if self.optimize and pab == -1 and len(edges) > 0 and len(hamilton) > 0 and hamilton[-1]["rem_hamilton"] >= 0:
            # Note that edges are sorted on "ca" and then on "cb"
            # in the order scorelevel on a, scorelevel on b, cid
            pab = cmp[edges[-1]["cb"]]["scorelevel"] if cmp[0]["rfp"] else 0
        if pab == -1 and len(edges) > 0:
            (_, _, pab) = self.find_weighted_pab(nodes, edges)
        if pab == -1 and self.verbose:
            print("No legal pairing")

        self.pablevel = pab
        edges = [edge for edge in edges if edge["ca"] != 0 or edge["sb"] == pab]
        return (None, pab, nodes, edges)


    def pair_round(self, bracket, nodes, edges, pairingmode, numpairs, category):
        """
        pair_round - find the best pairing of a set nodes.
        Parameters:
            bracket - the current scorebracket
            nodes - the competitors to be paired
            edges - the legal pair candidates
            pairingmode - hetrogenious pairing = "HE", homogenious pairing = "HO"
            numpairs - Number of paires that can be made in bracket
            pdp - moved down players
            category - Number of scorelevels that must be used in the algorithm
        Returns:
            sorted array of pairs, lowest value in pair first
        """
        scorelevel = bracket["scorelevel"]
        cmp = self.competitors
        pairs = None
        full = False
        pairsleft = 0
        if self.optimize and pairingmode == "HE" and nodes[0]["scorelevel"] == scorelevel:
            pairs = []
            pairsleft = (
                len([node for node in nodes if node["scorelevel"] == scorelevel])
                - self.hamilton[scorelevel - 1].get("rem_unpaired", 0)
            ) // 2
        if pairs is None:
            while not full:  # Number of pairs must be correct in homogenious, otherwise rerun
                pairs = self.pair_weighted_round(bracket, nodes, edges, pairingmode, numpairs, category)
                if pairingmode == "HO":
                    paired = len(
                        [
                            (a, b)
                            for (a, b) in pairs
                            if cmp[a]["rfp"] and cmp[a]["rfp"] and cmp[a]["scorelevel"] == scorelevel and cmp[b]["scorelevel"] == scorelevel
                        ]
                    )
                    if paired != numpairs:
                        # print("Rerun round", self.rnd, paired, numpairs)
                        numpairs = paired
                        continue
                full = True
        return (full, pairsleft, [((a, b) if a < b else (b, a)) for (a, b) in pairs])

    """
    Weighted pairing 
    Weighthed pairing will always be correct, but the number of edges is 
    in the order P**2 where P is the number of players. For more than 500 players
    the weighted method is slow, and may stop due to high memory consumtion. 

    Therfore if no switches say otherwise the program will first try a simple
    algorithm, and then the weighted.    

    """

    # find_weighted_pab
    # Competitors are sorted on score_level and then on TPN
    # The higher scorelevel on pab, the higher weight
    # If round is not pairable return empty set of edges
    # return (edges, pab)

    def weighted_match(self, nodes, edges):
        G = nx.Graph()
        nx_edges = [(edge["ca"], edge["cb"], 0) for edge in edges]
        G.add_weighted_edges_from(nx_edges)
        matching = nx.min_weight_matching(G)
        return len(nodes) - 2 * len(matching)

    def find_weighted_pab(self, nodes, edges):
        pablevel = 0
        G = nx.Graph()
        self.crosstable.compute_pab_weight(edges)
        nx_edges = [(edge["ca"], edge["cb"], edge["weight"]) for edge in edges]
        G.add_weighted_edges_from(nx_edges)
        wpairs = sorted([((a, b) if a < b else (b, a)) for (a, b) in nx.min_weight_matching(G)])
        if len(wpairs) < len(nodes) // 2:
            return (len(wpairs), len(wpairs) * 2 - len(nodes), -1)  # No legal pairing
        (w, pab) = wpairs[0]
        if w == 0:  # We have PAB
            pablevel = self.competitors[pab]["scorelevel"]
        return (len(wpairs), 0, pablevel)

    def pair_simple_round(self, bracket, nodes, edges, hetrogenious, numpairs, category):

        testlevel = -1

        scorelevel = bracket["scorelevel"]
        hthis = self.hamilton[scorelevel]
        hnext = self.hamilton[scorelevel-1] if scorelevel > 0  else {}

        # Don't run if not optimizez, or rest can not be paired
        if category == 0 or (not self.optimize) or hnext.get("rem_unpaired",1) > 1:
            return (False, 1, None)

        # Don't bother try this with less than 20 players
        if hthis.get("cur_pairs", 0) < 10:
            return (False, 1, None)
        pairs = []

        # order nodes in scorelevels
        levels = self.levels
        nodeptr = [-1] * (levels + 1)
        lastn = levels + 1
        for i, node in enumerate(nodes):
            if (firstn := node["scorelevel"]) < lastn:
                nodeptr[firstn] = i
                lastn = firstn
        if nodeptr[0] == -1:
            nodeptr[0] = len(nodes)

        HO1len = nodeptr[scorelevel]
        HO2len = nodeptr[scorelevel - 1]
        slen = HO2len
        if scorelevel <= self.pablevel:
            slen -= 1
        if slen % 2 == 1 and hnext.get("cur_hamilton", -1) < 2:
            return (False, 2, None)

        colordiff = self.analysis_colordiff(nodes[:HO2len])
        c12 = colordiff["c12"]
        c13 = colordiff["c13"]

        # hetrogenious pairing
        hetro = []
        SHE1 = [node["cid"] for node in nodes[:HO1len]]
        SHE2 = SER = [node["cid"] for node in nodes[HO1len:HO2len]]
        if len(SHE1):
            hetro = self.simple_permute(scorelevel, nodes, edges, SHE1, SHE2, colordiff, False)
            if len(hetro) == 0:
                return (False, 3, None)
            SER = [node for node in SHE2 if node not in hetro]

        # homogenious pairing
        homo = []
        slen = len(SER)
        if scorelevel <= self.pablevel:
            slen -= 1
        SHO1 = SER[: slen // 2]
        SHO2 = SER[slen //2:]
        if len(SHO2) - len(SHO1) > 1:
            return (False, 4, None)
        if len(SHO1):
            # rpos = nodeptr[max(0, scorelevel - 2)]
            homo = self.simple_permute(scorelevel, nodes, edges, SHO1, SHO2, colordiff, True)
            if len(homo) == 0:
                return (False, 5, None)
            # SHO2 = [node for node in SHO2 if node not in homo]
            # SHO2 = list(set(SHO2)-set(homo))
        # breakpoint()
        pairs = [(SHE1[a], b) for (a, b) in enumerate(hetro)] + [(SHO1[a], b) for (a, b) in enumerate(homo[0:len(SHO1)])]
        tc12 = tc13 = 0
        self.crosstable.B = slen
        self.crosstable.init_bweights(scorelevel, len(SHO2))
        epairs = []
        spairs = []
        for a, b in pairs:
            edge = self.get_edge_quality(self.opponents[a][b])
            if a in SHE1:
                epairs.append(edge)
            else:
                spairs.append(edge)
            tc12 += edge["quality"][qdefs.QC12.name]
            tc13 += edge["quality"][qdefs.QC13.name]

        bracket["bsno"] = self.update_bsn(scorelevel, [node for node in nodes if node["cid"] in SER])
        # self.crosstable.update_hetrogenious(scorelevel, epairs, bracket["bsne"])
        # self.crosstable.update_bipartite(scorelevel, pairs, bracket["bsno"], SHO2[0], SHO2[-1]
        # self.crosstable.update_homogenious(scorelevel, spairs, bracket["bsne"], len(spairs))


        if c12 != tc12 or c13 != tc13: # We never end here if recursion is corrrect
            if self.verbose:
               print("## Err in color alloc", c12, tc12, c13, tc13)
            return (False, 6, None)
        return (False, 0, pairs)

    # Non-Recursion

    def simple_permute(self, scorelevel, nodes, edges, S1, S2, colordiff, checkdf):
        testlevel = -1
        MAXSUB = 40320 # 8! permutations
        numsub = 0
        if S2 is None or len(S2) == 0:
            return []
        permutation = []
        stack = [-1]
        while slen := len(stack):
            index = stack.pop()
            if slen <= len(S1) and index >= 0:
                self.cannotbepared(S1[slen - 1], S2[index], colordiff, permutation)
                numsub += 1
                if numsub >= MAXSUB:
                    break
            index += 1
            plen = len(permutation)
            while index < len(S2):
                #if scorelevel == testlevel:
                #    breakpoint()
                if (
                    (S2[index] not in permutation)
                    and numsub < MAXSUB
                    and (plen >= len(S1) or self.canbepared(S1[plen], S2[index], colordiff, permutation))
                ):
                    break
                index += 1
            else:
                if plen := len(permutation):
                    permutation.pop()
                continue
            stack.append(index)
            stack.append(-1)
            permutation.append(S2[index])
            if scorelevel == testlevel:
                print("====>", permutation)
            if len(permutation) == (len(S2) if checkdf else len(S1)):
                if not checkdf or self.canbecompleted(scorelevel, nodes, edges, S1, S2, permutation):
                    if self.verbose > 1:
                        print("Permute", numsub, "Pairs:", len(permutation) )
                    return permutation
        if self.verbose:
            print("Max permute", numsub)
        return []

    def canbepared(self, S1, S2, colordiff, depth):
        edge = self.opponents[S1][S2]
        self.get_edge_quality(edge)
        if edge["qc"] and self.try_and_update_colordiff(edge, colordiff):
            return True
        return False

    def cannotbepared(self, S1, S2, colordiff, depth):
        edge = self.opponents[S1][S2]
        self.get_edge_quality(edge)
        if S1 == 0:
            raise
            # breakpoint()
        self.free_and_update_colordiff(edge, colordiff)
        return True

    # After a perfect match of simple pairing, is it possible to pair the remaining nodes ?

    def tcanbecompleted(self, scorelevel, nodes, edges, S1, S2, permutations):
        t0 = time.time()
        comp = self.canbecompleted(scorelevel, nodes, edges, S1, S2, permutations)
        t1 = time.time()
        if self.verbose:
            print(f"Can be compleeted: {t1 - t0:.3} s", comp)
        return comp


    def canbecompleted(self, scorelevel, nodes, edges, S1, S2, permutations):
        # restnodes = S2[len(permutations):]
        restnodes = permutations[len(S1) :]
        if len(restnodes) == 0:
            return True
        if any([self.competitors[rest]["flt"] & (flt.DF1.value + flt.DF2.value) for rest in restnodes]):
            # print("FLT return", False)
            return False
        if scorelevel <= self.pablevel:
            min_c9 = min([edge["unplayed"] for edge in edges if edge["ca"] == 0 and edge["canmeet"]])
        for rest in restnodes:
            if scorelevel <= self.pablevel:
                redge = self.opponents[rest][0]
                if redge["canmeet"]:
                    if redge["unplayed"] != min_c9:
                        return
                    mod_nodes = [node for node in nodes if node["cid"] != rest and node["cid"] != 0]
                    mod_nodes = [node for node in mod_nodes if node["cid"] not in S1 and node["cid"] not in permutations[: len(S1)]]
                    mod_edges = self.get_edges(mod_nodes, edges)
                    (_, unpaired, _) = self.is_complete(mod_nodes, mod_edges)
                    # print("PAB return", unpaired, unpaired == 0)
                    return unpaired == 0
            else:
                rest_nodes = [node for node in nodes if node["cid"] not in S1 and node["cid"] not in permutations[: len(S1)]]
                for edge in self.opponents[rest]:
                    if edge["canmeet"] and (edge["sa"] == scorelevel - 1 or edge["sb"] == scorelevel - 1):
                        opp = edge["ca"] + edge["cb"] - rest
                        mod_nodes = [node for node in rest_nodes if node["cid"] != rest and node["cid"] != opp]
                        # mod_nodes = [node for node in _nodes if node['cid'] not in S1 and node['cid'] not in permutations[:len(S1)]]
                        mod_edges = self.get_edges(mod_nodes, edges)
                        (_, unpaired, _) = self.is_complete(mod_nodes, mod_edges)
                        if unpaired == 0:
                            # print("RES return", unpaired == 0)
                            return True
                # print("RES return", False)
                return False


    def pair_weighted_round(self, bracket, nodes, edges, pairingmode, numpairs, category):
        # print("Pair", len(edges))
        scorelevel = bracket["scorelevel"]
        G = nx.Graph()
        nx_edges = []
        (modified_nodes, modified_edges) = self.modify_edges(nodes, None, edges, scorelevel, category, "canmeet")
        if len(modified_nodes) == 0:
            return []
        #  match (pairingmode):
        if pairingmode == "HE":
            self.crosstable.update_hetrogenious(scorelevel, modified_nodes, modified_edges, bracket["bsne"])
        elif pairingmode == "HO":
            # bracket['bsno'] = self.update_bsn(scorelevel, [node for node in modified_nodes if node['scorelevel'] <= scorelevel and node['lmb'] != scorelevel])
            bracket["bsno"] = self.update_bsn(scorelevel, [node for node in modified_nodes if node["scorelevel"] <= scorelevel])
            self.crosstable.update_homogenious(scorelevel, modified_edges, bracket["bsno"], numpairs)
        elif pairingmode == "BI":
            bracket["bsnb"] = {node["cid"]: i + 1 for i, node in enumerate(modified_nodes)}
            self.crosstable.update_hetrogenious(scorelevel, modified_nodes, modified_edges, bracket["bsnb"])
            self.crosstable.update_bipartite(
                scorelevel, modified_edges, bracket["bsnb"], nodes[len(nodes) // 2]["cid"], nodes[-1]["cid"]
            )
        if self.reportlevel > 2:
            print("pair_weighted(" + pairingmode + "," + str(numpairs) + ") comp:", [c["cid"] for c in modified_nodes])
            print("edges", [(c["ca"], c["cb"]) for c in modified_edges])
        # category =0
        for c in [edge for edge in modified_edges]:
            (wcid, bcid) = (c["ca"], c["cb"])
            weight = self.crosstable.update_weight(pairingmode, category, c)
            if self.reportlevel > 3:
                print(pairingmode + "-Edge:", f"{wcid:3} {bcid:3} ", self.crosstable.format_weight(pairingmode, weight)) #, c["weight"], c["qcweight"], c["heweight"], c["howeight"])
            nx_edges.append((wcid, bcid, weight))


        t0 = time.time()
        if self.checkonly and len(nodes) ==  2 * len(edges):
            wpairs = [(a,b) for (a,b,c) in nx_edges]
        else:
            G.add_weighted_edges_from(nx_edges)
            wpairs = nx.min_weight_matching(G)
            if self.reportlevel > 3:
                print("-------------------------")
                for pair in wpairs:
                    c = self.opponents[pair[0]][pair[1]]
                    (wcid, bcid) = (c["ca"], c["cb"])
                    print(pairingmode + "-Minw:", f"{wcid:3} {bcid:3} ", self.crosstable.format_weight(pairingmode, c["weight"])) #, c["weight"], c["qcweight"], c["heweight"], c["howeight"])
        t1 = time.time() 
        # print("Time:", t1 - t0)
        return wpairs

    """
    Optimized pairing 
    When the number of players are much higher then the number of rounds
    we can try an pairing without exchanges and c12.


    """

    """
    is_copmplete(self, nodes, edges, offset=0, weight= True, hist=None)
        nodes - node list
        edges - edge list, consider to use get_edges from a commection of edges
        offset - For test on hamilton_path only this must be (len(nodes)+1)//2
        weight - use weightrd algoritm if first test fails
        hist - use precalculated histogram 
    returns:
        (pairs, unpaired, hamilton)
        pairs - number of pairs that can be paired 
        unpaired - number of unpaired
        hamilton - difference between sorthist[0] - limit
 
        -1: No pairs can be formed
         0: pairing is not complete
         1: odd number of nodes that can be paired with (len(nodes)-1)/2 pairs
         2: even number of nodes that can be paired with len(nodes)/2 pairs
         3: odd number of nodes that forms a hamilton path
         4: even number of nodes that forms a hamilton path
    """

    def is_complete(self, nodes, edges, offset=-1, weight=True, hist=None, pab=False):
        numnodes = len(nodes)
        limit = (numnodes + 1) // 2
        if pab:
            limit += 1
            self.pablevel = -1
        if hist is None:
            hist = self.compute_whohasmet_histogram(nodes, edges)
        sorthist = sorted(hist)
        #  This attemt lead to wrong result for 1 of 100000 tournaments, and is not worth the risk of a wrong pairing
        # if len(sorthist) > len(nodes):
        #    sorthist = sorthist[-len(nodes):]  
        if len(sorthist) == 0 or sorthist[-1] == 0:
            return (0, numnodes, -1)  # None can meet
        if not pab and nodes[0]["cid"] == 0 and hist[0] > 1 and sorthist[1] >= limit:
            return (numnodes // 2, numnodes % 2, sorthist[1] - limit - 1) 
        if sorthist[0] >= limit:
            return (numnodes // 2, numnodes % 2, sorthist[0] - limit)
        if offset == -1:
            offset = 1 - numnodes % 2 if weight and not pab else limit
        # if len(nodes) == -1:
        #     breakpoint()
        if len(nodes) != len(hist) and not weight:
            return (0, 0, sorthist[0] - limit)
        if all([min(i + offset, limit) <= sorthist[i] for i in range(min(numnodes, limit + 1))]):
            return (numnodes // 2, numnodes % 2, sorthist[0] - limit)
        if weight:
            # print("Complete weighted")
            if pab:
                (pairs, unpaired, rpab) = self.find_weighted_pab(nodes, edges)
                self.pablevel = rpab
                return (pairs, unpaired, sorthist[0] - limit)
            else:
                rest = self.weighted_match(nodes, edges)
                return ((numnodes - rest) // 2, rest, sorthist[0] - limit)
        return (0, numnodes, sorthist[0] - limit)

    def compute_whohasmet_histogram(self, nodes, edges):
        numnodes = len(nodes)
        node_id = {node["cid"]: i for i, node in enumerate(nodes)}
        hist = [0] * numnodes
        for edge in edges:
            hist[node_id[edge["ca"]]] += 1
            hist[node_id[edge["cb"]]] += 1
        return hist

    # analysis_colordiff
    # nodes - list of nodes, all with a color preference "w2", "b2, "w1", "b1", "w0", "b0" of "nc"
    # treat w2 + w1 as w1 and b2 + b1 as b1
    # Now pair as many of w1 vs b1
    # then b1 vs w0 and w1 vs b0
    # if we have players without colorpreference subtract frp w2/b2 and then w1/b1
    # The lowest theoretical value of c12 is max(0, abs(wc - bc) - nc) // 2
    # The lowest theoretical value of c13 is max(0, c12 - w0) if (w0+w1) > (b0+b1) else max(0, c12- b0)

    def calculate_c12_c13_pref(self, c):
        (nc, w0, wc, b0, bc) = c
        if wc > bc:
            c12 = max(0, wc - bc - nc) // 2
            c13 = max(0, c12 - w0)
        else:
            c12 = max(0, bc - wc - nc) // 2
            c13 = max(0, c12 - b0)
        if wc > bc + nc:
            pref = "w"
        elif bc > wc + nc:
            pref = "b"
        else:
            pref = "n"

        return (c12, c13, pref)

    def analysis_colordiff(self, nodes):
        # Always even number
        # if (len(nodes)%2) == 1:
        #    breakpoint()
        col = defaultdict(int)
        for node in nodes:
            cop = node["cop"]
            col[cop] += 1
        for c in ["w", "b"]:
            col[c + "c"] = col[c + "0"] + col[c + "1"] + col[c + "2"]

        col["nc"] += (col["wc"] + col["bc"] + col["nc"]) % 2  # if PAB
        (col["c12"], col["c13"], col["pref"]) = self.calculate_c12_c13_pref(col[c] for c in ["nc", "w0", "wc", "b0", "bc"])

        return col

    def try_and_update_colordiff(self, edge, colordiff):
        (nc, w0, wc, b0, bc) = (colordiff[c] for c in ["nc", "w0", "wc", "b0", "bc"])
        for c in edge["colordiff"]:
            # match (c):
            if c == "n":
                nc -= 1
            elif c == "w":
                w0 -= 1
                wc -= 1
            elif c == "W":
                wc -= 1
            elif c == "b":
                b0 -= 1
                bc -= 1
            elif c == "B":
                bc -= 1
        # Start with QC12 and QC13, it the pair increases the minimum QC12/QC13,
        # adjust with th QC12 / QC13 contrebution of current pair
        (c12, c13, pref) = self.calculate_c12_c13_pref((nc, w0, wc, b0, bc))
        cd12 = 1 if edge["colordiff"].lower() in ["ww", "bb"] else 0
        cd13 = 1 if edge["colordiff"] in ["WW", "BB"] else 0
        if c12 + cd12 > colordiff["c12"] or c13 + cd13 > colordiff["c13"]:
            return False
        colordiff.update({"nc": nc, "w0": w0, "wc": wc, "b0": b0, "bc": bc, "c12": c12, "c13": c13, "pref": pref})
        # print("Add edge ", edge["ca"], edge["cb"])
        return True

    def free_and_update_colordiff(self, edge, colordiff):
        # print("Sub edge", edge["ca"], edge["cb"])
        (nc, w0, wc, b0, bc) = (colordiff[c] for c in ["nc", "w0", "wc", "b0", "bc"])
        for c in edge["colordiff"]:
            # match (c):
            if c == "n":
                nc += 1
            elif c == "w":
                w0 += 1
                wc += 1
            elif c == "W":
                wc += 1
            elif c == "b":
                b0 += 1
                bc += 1
            elif c == "B":
                bc += 1
        # Start with QC12 and QC13, it the pair increases the minimum QC12/QC13,
        # adjust with th QC12 / QC13 contrebution of current pair
        (c12, c13, pref) = self.calculate_c12_c13_pref((nc, w0, wc, b0, bc))
        # cd12 = 1 if edge["colordiff"].lower() in ["ww", "bb"] else 0
        # cd13 = 1 if edge["colordiff"] in ["WW", "BB"] else 0
        # if c12 + cd12 > colordiff['c12'] or c13 + cd13> colordiff['c13']:
        #    return False
        colordiff.update({"nc": nc, "w0": w0, "wc": wc, "b0": b0, "bc": bc, "c12": c12, "c13": c13, "pref": pref})
        return True

    def analysis_downfloat(self, scorelevel, S1nodes, S2nodes, edges, colordiff):
        if S1nodes[-1]["scorelevel"] != scorelevel:
            return 0

    """
    color_allocation(a, b, c)
    Implement section E
    a - competitor a
    b - competitor b
    c - opponents element


    """

    def update_color(self, c):
        ca = self.competitors[c["ca"]]
        cb = self.competitors[c["cb"]]
        colres = self.color_allocation(ca, cb)
        if self.checkonly:
            if ca["cid"] == 0:
                p =  {"w": cb["cid"], "b": 0}
            else: # ca["hst"]["val"][-1] == 0:
               p =  {ca["hst"]["val"][-1]: ca["cid"], cb["hst"]["val"][-1]: cb["cid"]}
            c.update(p)
            c["colorrule"] = colres["colorrule"]
        else:
            (c["w"], c["b"], c["colorrule"]) = (colres["w"], colres["b"], colres["colorrule"])


    def color_allocation(self, a, b):
        rank = self.rank  # "cid" or "rnk"
        other = {"w": "b", "b": "w", " ": " "}
        (acid, bcid) = (a["cid"], b["cid"])
        (arank, brank) = (a[rank], b[rank])
        (acp, acs) = list(a["cop"])
        (bcp, bcs) = list(b["cop"])
        acd = a["cod"]
        bcd = b["cod"]
        #if acid == 1 and bcid == 6 or acid == 6 and bcid == 1:
        #    breakpoint()

        # PAB, always set player to white
        if arank == 0:
            return {"w": bcid, "b": acid, "colorrule": "pab"}  # ('b', 'w', 'pab')
        if brank == 0:
            return {"w": acid, "b": bcid, "colorrule": "pab"}  # ('w', 'b', 'pab')

        # E.1

        if acp == "w" and bcp != "w" or acp != "b" and bcp == "b":
            return {"w": acid, "b": bcid, "colorrule": "E.1"}  # ('w', 'b', 'E.1')
        if acp == "b" and bcp != "b" or acp != "w" and bcp == "w":
            return {"w": bcid, "b": acid, "colorrule": "E.1"}  # ('b', 'w', 'E.1')
        # E.2
        if (acp == "w" and bcp == "w" and acs > bcs) or (acp == "b" and bcp == "b" and acs < bcs):
            return {"w": acid, "b": bcid, "colorrule": "E.2"}  # ('w', 'b', 'E.2')
        if (acp == "b" and bcp == "b" and acs > bcs) or (acp == "w" and bcp == "w" and acs < bcs):
            return {"w": bcid, "b": acid, "colorrule": "E.2"}  # ('b', 'w', 'E.2')
        if acd != bcd and acs == bcs:  # both have absolute color preference, se if there are different color difference
            return {"w": acid, "b": bcid, "colorrule": "E.2"} if acd < bcd else {"w": bcid, "b": acid, "colorrule": "E.2"}
            # return ('w', 'b', 'E.2') if acd < bcd else ('b', 'w', 'E.2')
        # E.3
        asq = a["csq"]
        bsq = b["csq"]
        for i in range(1, min(len(asq), len(bsq))):
            ac = asq[-i]
            bc = bsq[-i]
            if ac != bc:
                if ac == "b" or bc == "w":
                    return {"w": acid, "b": bcid, "colorrule": "E.3"}  # ('w', 'b', 'E.3')
                if ac == "w" or bc == "b":
                    return {"w": bcid, "b": acid, "colorrule": "E.3"}  # ('b', 'w', 'E.3')
        # E.4
        (atpn, btpn) = (a["tpn"], b["tpn"])
        (highcid, hightpn) = (
            (acid, atpn)
            if a["scorelevel"] > b["scorelevel"] or a["scorelevel"] == b["scorelevel"] and atpn < btpn
            else (bcid, btpn)
        )
        lowcid = acid + bcid - highcid
        if acp == "w" or acp == "b":
            # print("S2", acp, min(acid, bcid), max(acid, bcid), {acp : min(acid, bcid), other[acp] : max(acid, bcid) , "colorrule": 'E.4'})
            return {acp: highcid, other[acp]: lowcid, "colorrule": "E.4"}  # (acp, other[acp], 'E.4')
        # if a['tpn'] > b['tpn'] and (acp == 'w' or acp == 'b'):
        #    return (other[acp], acp, 'E.4')
        # E.5
        tc = self.topcolor
        rev = hightpn % 2 == 0
        return {tc: (lowcid if rev else highcid), other[tc]: (highcid if rev else lowcid), "colorrule": "E.5"}
