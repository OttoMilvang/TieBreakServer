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
from qdefs import qdefs, flt
import helpers


"""
Structre 

+--- competitor
|         {
            'cid': 9, 
            'pts': Decimal('0.5'), 
            'acc': Decimal('0.5'), 
            'rfp': True / False,
            'pop': -1,
            'pco': ""
            'hst': { "val": "Y", "1": "23b"},
            'num': 2, 
            'rip': 1,
            'met': {'val': 2, 1: 1, 2: 10}, 
            'cod': 0, 
            'cop': 'b0', 
            'csq': ' bw', 
            'flt': 2, 
            'top': False,
            'mdp': 0,
            'scorelevel'
          }
+--- crosstable: [  
|         {
            'ca': 5,          # lowest cid in pair
            'cb': 17,         # highest cid in pair
            'sa': 3,          # scorelevel a
            'sb': 3,          # scorelevel b
            'canmeet': True,  # players can meet
            'isblob': False,  # true if node represent a collection of players
            'played': 0,      # Number of games played
            'psd': 0,         # abs(sa-sb)
            'w': '3',         # cid of white 
            'b': '17',        # cid of black, 0 if no opponent
            'quality': [...]  # array of quality variables
            '?weight': 0,     # Weight used in weighted pairing
            'qc': True,       # true if 'canmeet' and C9-C11 == 0 and C14-C21 == 0
            'colordff': 'BB', # color difference for pair. 
            'e-rule': 'E.4',  # rules used to decide color
            'mode': "S",      # selected from hetrogenios "E" of homogenios "S" pairs
            'board': 19       # board number in pairing 
|         }, 
|         ...
|    
|       ]
+--- seq: [  Array of possible brackets containing competitors/downfloats
          {
           'scorelevel': <points> ,     # Bracket points
           'competitors': [],           # Array of competitor objects   
           'downfloaters':  []          # Array of downfloated competitors
           'limbo': limbo []            # Array of nonpairable downfloats
           'pairs': []                  # Array of crosstable elements
           'mdp' []                     # Array of moveddown crosstable elements
           'psd' : lval,                # scorelevels of psd's value
           'valid' : True
          },
           ...
    ]



+--- Return object ---
         {
             'round': 4
             'check': True/False
             'analyze': [       # Array of score brackets, anaalyze existing pairing
                {
                    'scorelevel': <level> ,     # Bracket level 
                    'competitors': [],          # Array of competitor objects   
                    'pairs': []                 # Pairs
                    'downfloaters':  [5, 11]    # Array of downfloated competitors
                    'remaining':  [23, 0]       # Array of remaining competitors
                    'quality': [...]            # array C6-C21, E1-E2, S1-S5
                    'pab': False,               # true if this is PAB scorelevel
                    'valid': True,              # True if pairing is valid
                },
                .... more brackets                    
                ],
            'checker': [       # Array of score brackets, same structure as analyze
                        ...
                        ]
            }

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
    E1-E2 hetrogenios
        R**M                    - R**(bsn mdp)
        R**M                    - R**(bsn mdp)*(bsn opponent)
    S1-S5 homogenious
        R                       - 1 if bsn > r else 0
        R*R                     - bsn
        10**S                   - 10**bsn if wsn <=r
        10**(B-S)               - 10**bsn if wsn >r
        10**(B-1)               - 10**(n-wbsn)*bbsn



"""



class pairing:

    # constructor function
    def __init__(self, chessfile, tournamentno, rnd, topcolor, unpaired, maxmeet, experimental, verbose):

        # helpers.json_output(sys.stdout, cmps[12]['tiebreakDetails'])
        self.chessfile = chessfile
        self.tournamentno = tournamentno
        self.rnd = rnd
        self.topcolor = topcolor
        self.unpaired = [helpers.parse_int(u) for u in unpaired]
        self.maxmeet = maxmeet
        self.experimental = experimental
        self.verbose = verbose
        self.optimize = "weighted" not in experimental

    """
    compute_pairing 
        find a list of present competitors, if number of competitors are odd, add a dummy competitor (cid = 0)
        check if pairing is complete (possible)
        find lowest possible score for PAB
        start with empty mdp (moved doen players) and all competitors in remaining   
        loop over remaining
            find score bracket point
            make a pairing bracket and from mdp, resident and remaining, do bracket pairing
        
    """

    def compute_pairing(self, checkonly, reportlevel=0):
        if self.verbose:
            print("Round:", self.rnd, "Check:", "Yes" if checkonly else "No")
        self.checkonly = checkonly
        self.reportlevel = reportlevel
        self.optimize = "weighted" not in self.experimental and not checkonly
        self.crosstable = crosstable(self.experimental, self.checkonly, self.verbose)
        t0 = time.time()
        (nodes, edges) = self.crosstable.init_engine(
            self.chessfile, self.tournamentno, self.rnd, self.maxmeet, self.topcolor, self.unpaired
        )
        t1 = time.time()
        if self.verbose:
            print("Init engine:", t1 - t0, "s")
        # edges = self.crosstable.list_edges(self.cmps, self.maxmeet, self.topcolor, self.unpaired)
        self.levels = levels = len(self.crosstable.levels())

        (competitors, edges) = self.list_competitors(self.crosstable.crosstable, edges)
        self.competitors = {c["cid"]: c for c in competitors}
        nodes = competitors[:]

        self.hammilton = self.compute_hammilton(nodes, edges)
        if self.hammilton[levels - 1].get("rem_unpaired", 0) != 0:
            return []

        pab = self.find_pab(nodes, edges)

        edges = self.filter_pab(edges, pab)
        if self.verbose:
            print("PAB:", pab, "edges:", len(edges))

        scorelevel = nodes[0]["scorelevel"] if len(nodes) > 0 else -1

        self.roundpairing = []
        testpab = False
        mdp = 0
        while len(nodes) > 0 and scorelevel >= 0:
            self.bracket = None
            if self.verbose > 1:
                print("Roundpairing, scorelevel ", self.rnd, ", Nodes = ", len(nodes), ", edges = ", len(edges))
            (bracket, nodes, edges, testpab) = self.pair_bracket(scorelevel, nodes, edges, mdp, testpab)
            self.roundpairing.append(bracket)
            mdp = len(bracket["downfloaters"])
            scorelevel -= 1
        self.update_board(self.roundpairing)
        return self.roundpairing

    def select_nodes_and_edges(self, nodes, edges, from_scorelevel, to_scorelevel, condition=None):
        mod_nodes = [node for node in nodes if node["scorelevel"] >= from_scorelevel and node["scorelevel"] <= to_scorelevel]
        mod_edges = self.get_edges(mod_nodes, edges, condition)
        return (mod_nodes, mod_edges)

    def remove_pairs(self, nodes, edges, paired):
        npaired = [edge["ca"] for edge in paired] + [edge["cb"] for edge in paired]
        mod_nodes = [node for node in nodes if node["cid"] not in npaired]
        mod_edges = self.get_edges(mod_nodes, edges)
        return (mod_nodes, mod_edges, npaired)

    def get_nodeid(self, nodes, cid="cid"):
        return [node[cid] for node in nodes]

    def get_edgeid(self, edges, ca="ca", cb="cb"):
        return [(edge[ca], edge[cb]) for edge in edges]

    def edgeBinarySearch(self, edges, scorelevel):
        """
        edgeBinarySearch - find first element with min(scorelevel) >= target

        Parameters
        ----------
        egdes : array of edges
        target : scorelevel

        Returns
        -------
        Pointer to first element with min(scorelevel) >= target

        """
        left = 0
        right = len(edges) - 1
        while left <= right:
            mid = (left + right) // 2
            c0mid = min(edges[mid]["sa"], edges[mid]["sb"])
            if c0mid == scorelevel:
                if mid == 0:
                    return mid
                c1mid = min(edges[mid - 1]["sa"], edges[mid - 1]["sb"])
                if c1mid == scorelevel + 1:
                    return mid
                elif c1mid > scorelevel + 1:
                    left = mid + 1
                else:
                    right = mid - 1
            elif c0mid > scorelevel:
                left = mid + 1
            else:
                right = mid - 1
        return len(edges) + 1

    def get_edges(self, nodes, edges, condition=None):
        """
        get_edges - Optimized version to extract edges with both vertices in "nodes"

        Parameters
        ----------
        nodes : Array of nodes
        edges : Array of edges
        condition : optional condition ("canmeet" / "qc" / other)

        Returns
        -------
        new_edges : array of edges

        """

        if len(nodes) == 0 or len(edges) == 0:
            return []
        msl = nodes[-1]["scorelevel"] - 1

        # Note that both nodes and edges are sorted on scorelevel
        # Edges on min(scorelevel), then max(scorelevel)
        if min(edges[0]["sa"], edges[0]["sb"]) < msl:
            return []
        if min(edges[-1]["sa"], edges[-1]["sb"]) <= msl and msl >= 0:
            mid = self.edgeBinarySearch(edges, msl)
            if mid < len(edges):
                edges = edges[0:mid]

        cmps = [False] * (self.crosstable.BLOB + 1)
        for node in nodes:
            cmps[node["cid"]] = True
        if condition:
            new_edges = [edge for edge in edges if cmps[edge["ca"]] and cmps[edge["cb"]] and edge[condition]]
        else:
            new_edges = [edge for edge in edges if cmps[edge["ca"]] and cmps[edge["cb"]]]
        return new_edges

    def get_modifiededges(self, nodeid1, nodeid2, edges, condition=None):
        cmps1 = [False] * (self.crosstable.BLOB + 1)
        cmps2 = [False] * (self.crosstable.BLOB + 1)
        for node in nodeid1:
            cmps1[node] = True
        for node in nodeid2:
            cmps2[node] = True
        new_edges = [edge for edge in edges if cmps1[edge["ca"]] and cmps2[edge["cb"]]]
        return new_edges

    def list_competitors(self, nodes, edges):
        mod_nodes = sorted([node for node in nodes if node["rfp"]], key=lambda s: (-s["scorelevel"], s["cid"]))
        mod_edges = self.get_edges(mod_nodes, edges)
        mod_edges = sorted(
            mod_edges, key=lambda edge: (-min(edge["sa"], edge["sb"]), -max(edge["sa"], edge["sb"]), edge["ca"], edge["cb"])
        )
        return (mod_nodes, mod_edges)

    # compute_hammilton
    # for each scorelevel, compute the number of paired unpaired players
    # Returns an array of length levels, and for each level:
    # "rem_pairs" : total pairs that can be made from this scorelevel and below
    # "rem_unpaired" : total unpaired for this scorelevel and below
    # "rem_hammilton" : >= 0 if an hammilton path exists,
    # "cur_pairs" : number of pairs than maximum can be formed in this scorelevel
    # "cur_unpaired" : number of minimum unpaired players in this scorelevel
    # "cur_hammilton" : >= 0 if an hammilton path exists for this scorelevel
    # "cross_hammilton" : >= 0 if there are safe to downfloat one player

    def compute_hammilton(self, nodes, edges):
        levels = self.levels
        hammilton = [{} for _ in range(levels)]
        self.pab = -1
        if self.checkonly:
            return hammilton
        # rest_nodes = nodes[::-1] if self.pab == 0 else nodes[-2::-1]
        rest_nodes = nodes[::-1]
        numnodes = len(rest_nodes)
        numedges = len(edges)
        # while numedges > 0 and edges[numedges-1]["ca"] == 0: numedges -= 1
        rest_edges = sorted(edges[:numedges], key=lambda edge: (max(edge["sa"], edge["sb"]), min(edge["sa"], edge["sb"])))
        bp = False

        # nodeptr point to first element lower than scorelevel
        # rest_nodes[nodeptr[level]:] selects all nodes with scorelevel < level

        nodeptr = [0] * (levels + 1)
        lastn = 0
        for i, node in enumerate(rest_nodes + [{"scorelevel": levels}]):
            if (firstn := node["scorelevel"]) > lastn:
                nodeptr[lastn + 1] = i
                lastn = firstn
        node_id = {node["cid"]: i for i, node in enumerate(rest_nodes)}

        hist = [0] * numnodes
        laste = 0
        ll_nodes = []   # Just to keep code checkers happy
        ff_nodes = []
        ll_hist = []
        fl_hist = []
        lf_hist = []

        for i, edge in enumerate(rest_edges + [{"sa": levels, "sb": levels}]):
            if (firste := max(edge["sa"], edge["sb"])) > laste:
                # update each scorelevel - hammilton
                rest = hammilton[laste]
                if laste > 0:
                    (rest["cur_pairs"], rest["cur_unpaired"], rest["cur_hammilton"]) = self.is_complete(
                        ll_nodes, None, weight=False, hist=ll_hist
                    )
                    (_, _, fh) = self.is_complete(ll_nodes, None, weight=False, hist=fl_hist)
                    (_, _, lh) = self.is_complete(ff_nodes, None, weight=False, hist=lf_hist)
                    rest["cross_hammilton"] = min(fh, lh)
                # more to do?
                # find if remaining is pairable. This in marked on lasteventlevel+1
                # rest = hammilton[laste+1]
                test_nodes = rest_nodes[: nodeptr[laste + 1]]  # if laste >= self.pab else rest_nodes[nodeptr[firste]:-1]
                (rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hammilton"]) = self.is_complete(
                    test_nodes, rest_edges[:i], hist=hist[: nodeptr[laste + 1]], pab=firste == levels
                )
                # print(laste, len(test_nodes), rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hammilton"])
                (rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hammilton"]) = self.is_complete(
                    test_nodes, rest_edges[:i], hist=hist[: nodeptr[laste + 1]], pab=firste == levels
                )
                if edge["sa"] == levels and edge["sb"] == levels:
                    break
                laste = firste
                ff_nodes = rest_nodes[nodeptr[laste - 1] : nodeptr[laste]] if laste > 0 else []
                ff_id = {node["cid"]: j for j, node in enumerate(ff_nodes)}
                ll_nodes = rest_nodes[nodeptr[laste] : nodeptr[laste + 1]]
                ll_id = {node["cid"]: j for j, node in enumerate(ll_nodes)}
                ll_hist = [0] * len(ll_nodes)
                fl_hist = [0] * len(ff_nodes)
                lf_hist = [0] * len(ll_nodes)
            hist[node_id[edge["ca"]]] += 1
            hist[node_id[edge["cb"]]] += 1
            if edge["sa"] == edge["sb"]:
                # breakpoint()
                ll_hist[ll_id[edge["ca"]]] += 1
                ll_hist[ll_id[edge["cb"]]] += 1
            if abs(edge["sa"] - edge["sb"]) == 1:
                fl_hist[ff_id[edge["ca"] if edge["sa"] < edge["sb"] else edge["cb"]]] += 1
                lf_hist[ll_id[edge["cb"] if edge["sa"] < edge["sb"] else edge["ca"]]] += 1

        # laste += 1
        if bp:
            breakpoint()
        return hammilton

    def pair_bracket(self, scorelevel, nodes, edges, mdp, testpab):
        bracket = {
            "scorelevel": scorelevel,
            "competitors": [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel],
            "pairs": [],
            "downfloaters": [],
            "remaining": [],
            "quality": [None] * qdefs.QL.value,
            "bsne": self.update_bsn(scorelevel, nodes),
            "bsno": {},
            "pab": scorelevel == self.pab,
            "valid": True,
        }

        pabbracket = self.apply_c9(scorelevel, nodes, edges, testpab)
        t0 = time.time()
        category = self.get_category(scorelevel, nodes, edges)
        self.crosstable.update_crosstable(scorelevel, nodes, edges, pabbracket)

        # Why is this wrong?
        # mid = self.edgeBinarySearch(edges, scorelevel- (1 if category == 1 else 2))
        # self.crosstable.update_crosstable(scorelevel, nodes, edges[0:mid], pabbracket)
        t1 = time.time()

        if self.reportlevel >= 2 and scorelevel < len(self.crosstable.levels()):
            print("================================================")
            print("Scorelevel: ", scorelevel, ", bsn: ", len(bracket["bsne"]), ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Bracket       = ", self.crosstable.levels()[scorelevel])
            print("Pabbracket    = ", pabbracket, "PAB" if scorelevel == self.pab else "")
            print("Category      = ", category)
            print("Time          = ", t1 - t0)
        elif self.verbose:
            print("Scorelevel: ", scorelevel, ", bsn: ", len(bracket["bsne"]), ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Category      = ", category)

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

        for pairingmode in ["B", "E", "S"]:  # B = bipartite, E = hetrogenious, S = homogenious
            t0 = time.time()

            if pairingmode == "B":
                if self.optimize:
                    (weighted, pairsleft, pairs) = self.pair_simple_round(
                        bracket, nodes, edges, pairingmode, numpairs, mdp, category
                    )
                    # print("Simple ", self.rnd, scorelevel, pairsleft)
                if not self.optimize or pairs is None:
                    continue
            else:
                (weighted, pairsleft, pairs) = self.pair_round(bracket, nodes, edges, pairingmode, numpairs, mdp, category)
            t1 = time.time()
            if self.verbose:
                print("Pair round", self.rnd, "Scorelevel:", scorelevel, pairingmode, f"{t1-t0:.2f}")
            paired = []
            # if scorelevel ==1 and category > 0:breakpoint()

            bipartite = pairingmode == "B"
            hetro = pairingmode == "E"
            for a, b in pairs:
                c = self.competitors[a]["opp"][b]
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
            if self.reportlevel > 1 and scorelevel < len(self.crosstable.levels()):
                print("-Mode", pairingmode)
                print("Competitors   = ", bcompetitors)
                print("Pairs         = ", [(c["w"], c["b"]) for c in bracket["pairs"]])
                if pairingmode == "S":
                    print("Down          = ", [c for c in bracket["downfloaters"]])
                bcompetitors = [c for c in bracket["competitors"] if c not in npaired]
            if pairingmode == "B" and pairsleft == 0:
                break
        bracket["remaining"] = [c["cid"] for c in nodes if c["scorelevel"] < scorelevel]
        bracket["downfloaters"] = [c["cid"] for c in nodes if c["scorelevel"] >= scorelevel]
        if len(bracket["pairs"]):
            bracket["quality"] = self.crosstable.compute_weight(wpairs, bracket["quality"])
        else:
            testpab = False
        return (bracket, nodes, edges, testpab)

    def update_board(self, roundpairing):
        pairs = []
        for bracket in roundpairing:
            for pair in bracket["pairs"]:
                (w, b) = (pair["w"], pair["b"])
                (ws, bs) = (self.competitors[w]["acc"], self.competitors[b]["acc"])
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
        if scorelevel > self.pab:
            return False
        # print("Testpab-I",  scorelevel, testpab, self.roundpairing[-1]["quality"][N8] if testpab else -1)
        if scorelevel <= 1:
            return True
        if not self.optimize and testpab and len(self.roundpairing) > 0:
            #    print("Testpab-N", scorelevel, self.roundpairing[-1]["quality"][N8])
            return self.roundpairing[-1]["quality"][qdefs.N8.value] == 1
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
        if scorelevel < self.pab:
            return 0

        # thislevel = sum([1 for node in nodes if node["scorelevel"] >= scorelevel])
        cat1 = False
        hammilton = self.hammilton
        if scorelevel == testlevel:
            breakpoint()
        if len(edges) == 0:
            raise  
        if edges[0]["sa"] < scorelevel or edges[0]["sb"] < scorelevel:
            return -1  # There are no pairing for this scorebracket
        if edges[0]["sa"] == 1 and edges[0]["sb"] == 1:
            return 1  # Last scoregroup is always pairable
        if hammilton[scorelevel].get("rem_unpaired", 2) > 1 or scorelevel < self.pab:
            return 0

        shammilton = hammilton[scorelevel]
        if scorelevel == 1:
            return 1 if shammilton["rem_hammilton"] > 0 else 0
        top_nodes = bot_nodes = nodes
        top_edges = bot_edges = edges
        for level in range(scorelevel, 0, -1):
            # if level == 1 or level <= self.pab: return 0
            (top_nodes, top_edges) = self.select_nodes_and_edges(top_nodes, top_edges, level, self.levels)
            lhammilton = hammilton[level]
            (shammilton["this_pairs"], shammilton["this_rest"], shammilton["this_hammilton"]) = self.is_complete(
                top_nodes, top_edges
            )
            rhammilton = hammilton[level - 1]
            if level == scorelevel and shammilton["this_rest"] == 0:
                if rhammilton.get("rem_hammilton", -1) <= 0:
                    (bot_nodes, bot_edges) = self.select_nodes_and_edges(bot_nodes, bot_edges, 0, level - 1)
                    (shammilton["mod_pairs"], shammilton["mod_unpaired"], _) = self.is_complete(bot_nodes, bot_edges)
                    if shammilton["mod_unpaired"] > 0:
                        return 0  # Remaining can not be paired
                if rhammilton.get("rem_hammilton", -1) > 0:
                    if len(top_nodes) % 2:
                        raise
                    return 1
            tmeet = (
                shammilton.get("this_hammilton", -1) > 0
                and lhammilton.get("cur_hammilton", -1) > 0
                and lhammilton.get("cross_hammilton", -1) >= 0
                and lhammilton.get("rem_hammilton", -1) > 0
            )
            if scorelevel == testlevel:
                print(
                    "Tmeet",
                    level,
                    tmeet,
                    shammilton.get("this_hammilton", -1),
                    lhammilton.get("cur_hammilton", -1),
                    lhammilton.get("cross_hammilton", -1),
                    lhammilton.get("rem_hammilton", -1),
                )
            cat1 = cat1 and tmeet
            if shammilton.get("rem_hammilton", -1) <= 0:
                return 1 if cat1 else 0  # Dont wait time to see if rest is complete
            if tmeet:
                category = scorelevel - level + 1
                ok = category > 1 or level > self.pab and len(top_nodes) % 2 == 0
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

    def modify_edges(self, s1nodes, s2nodes, edges, scorelevel, category, condition):
        testlevel = -1
        if category == 0:
            return (s1nodes, edges)
        new_edges = []
        add_edges = []

        cr = self.crosstable.crosstable
        lim = scorelevel - category + 1
        nodeid1 = [node["cid"] for node in s1nodes if node["scorelevel"] >= lim]
        if s2nodes is None:
            (s2nodes, nodeid2) = (s1nodes, nodeid1)
            addblob = len(nodeid1) % 2 == 1
        else:
            nodeid2 = [node["cid"] for node in s2nodes if node["scorelevel"] >= lim]
            addblob = len(nodeid1) < len(nodeid2)
        new_edges = self.get_modifiededges(nodeid1, nodeid2, edges)
        if testlevel == scorelevel:
            breakpoint()
        if addblob:
            blob = 0 if self.pab >= scorelevel else self.crosstable.BLOB
            nodeid1.append(blob)
            s2nodesid = [node["cid"] for node in s2nodes if node["scorelevel"] == lim]

            if blob == 0:
                for node_id in s2nodesid:
                    new_edge = cr[node_id]["opp"][0]
                    if new_edge[condition]:
                        add_edges.append(new_edge)
            else:
                mid = self.edgeBinarySearch(edges, lim - 1)
                for edge in edges[mid:]:
                    if edge["ca"] in s2nodesid:
                        node_id = edge["ca"]
                    elif edge["cb"] in s2nodesid:
                        node_id = edge["cb"]
                    else:
                        continue
                    new_edge = self.crosstable.create_edge(cr[node_id], cr[blob])
                    if cr[node_id]["flt"] & (flt.DF1.value + flt.DF2.value) > 0:
                        new_edge["qc"] = False
                    if new_edge[condition]:
                        add_edges.append(new_edge)
                        s2nodesid.remove(node_id)
                        if len(s2nodesid) == 0:
                            break
                # breakpoint()

            for edge in add_edges:
                node_id = edge["ca"] if edge["ca"] > 0 and edge["ca"] < blob else edge["cb"]
                if cr[node_id]["flt"] & (flt.DF1.value + flt.DF2.value) > 0:
                    new_edge["qc"] = False

            new_edges += add_edges
            if len(add_edges) == 0:
                return (s1nodes, edges)
            new_nodes = [node for node in s1nodes if node["cid"] in nodeid1]
            new_nodes.append(self.crosstable.crosstable[blob])
            self.crosstable.update_crosstable(scorelevel, new_nodes, add_edges, self.pab, False)
        else:
            new_nodes = [node for i, node in self.competitors.items() if i in nodeid1]
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
        pab = self.pab
        hammilton = self.hammilton
        if self.optimize and pab == -1 and len(edges) > 0 and len(hammilton) > 0 and hammilton[-1]["rem_hammilton"] >= 0:
            # Note that edges are sorted on "ca" and then on "cb"
            # in the order scorelevel on a, scorelevel on b, cid
            pab = self.competitors[edges[-1]["cb"]]["scorelevel"] if 0 in self.competitors else 0
        if pab == -1 and len(edges) > 0:
            (_, _, pab) = self.find_weighted_pab(nodes, edges)
        if pab == -1 and self.verbose:
            print("No legal pairing")

        self.pab = pab
        return pab

    def filter_pab(self, edges, pab):
        return list(filter(lambda edge: edge["ca"] != 0 or edge["sb"] == pab, edges))

    def pair_round(self, bracket, nodes, edges, pairingmode, numpairs, mdp, category):
        """
        pair_round - find the best pairing of a set nodes.
        Parameters:
            bracket - the current scorebracket
            nodes - the competitors to be paired
            edges - the legal pair candidates
            pairingmode - hetrogenious pairing = "E", homogenious pairing = "S"
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
        if self.optimize and pairingmode == "E" and nodes[0]["scorelevel"] == scorelevel:
            pairs = []
            pairsleft = (
                len([node for node in nodes if node["scorelevel"] == scorelevel])
                - self.hammilton[scorelevel - 1].get("rem_unpaired", 0)
            ) // 2
        if pairs is None:
            while not full:  # Number of pairs must be correct in homogenious, otherwise rerun
                pairs = self.pair_weighted_round(bracket, nodes, edges, pairingmode, numpairs, mdp, category)
                if pairingmode == "S":
                    paired = len(
                        [
                            (a, b)
                            for (a, b) in pairs
                            if a in cmp and b in cmp and cmp[a]["scorelevel"] == scorelevel and cmp[b]["scorelevel"] == scorelevel
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
        # print("W826",len(nodes) - 2*len(matching))
        return len(nodes) - 2 * len(matching)

    def find_weighted_pab(self, nodes, edges):
        pablevel = 0
        G = nx.Graph()
        self.crosstable.compute_pab_weight(edges)
        nx_edges = [(edge["ca"], edge["cb"], edge["iweight"]) for edge in edges]
        G.add_weighted_edges_from(nx_edges)
        wpairs = sorted([((a, b) if a < b else (b, a)) for (a, b) in nx.min_weight_matching(G)])
        if len(wpairs) < len(nodes) // 2:
            return (len(wpairs), len(wpairs) * 2 - len(nodes), -1)  # No legal pairing
        (w, pab) = wpairs[0]
        if w == 0:  # We have PAB
            pablevel = self.competitors[pab]["scorelevel"]
        return (len(wpairs), 0, pablevel)

    def pair_simple_round(self, bracket, nodes, edges, hetrogenious, numpairs, mdp, category):
        testlevel = -1
        scorelevel = bracket["scorelevel"]
        h = self.hammilton[scorelevel]
        # Don't bother try this with less than 20 players
        # print("Category", category, "Simple? ", "E" if hetrogenious else "O", h.get("cur_pairs"), h.get("this_hammilton"))
        if h.get("cur_pairs", 0) < 10:
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

        s1len = nodeptr[scorelevel]
        s2len = nodeptr[scorelevel - 1]
        slen = s2len
        if scorelevel <= self.pab:
            slen -= 1
        if slen % 2 == 1 and self.hammilton[scorelevel - 1].get("cur_hammilton", -1) < 2:
            return (False, 2, None)

        colordiff = self.analyze_colordiff(nodes[:s2len])
        c12 = colordiff["c12"]
        c13 = colordiff["c13"]

        # hetrogenious pairing
        hetro = []
        SE1 = [node["cid"] for node in nodes[:s1len]]
        SE2 = SER = [node["cid"] for node in nodes[s1len:s2len]]
        if len(SE1):
            hetro = self.simple_permute(scorelevel, nodes, edges, SE1, SE2, colordiff, False)
            if len(hetro) == 0:
                return (False, 3, None)
            SER = [node for node in SE2 if node not in hetro]

        # homogenious pairing
        homo = []
        slen = len(SER)
        if scorelevel <= self.pab:
            slen -= 1
        SS1 = SER[: slen // 2]
        SS2 = SER[slen //2:]
        if len(SS2) - len(SS1) > 1:
            return (False, 4, None)
        if len(SS1):
            # rpos = nodeptr[max(0, scorelevel - 2)]
            homo = self.simple_permute(scorelevel, nodes, edges, SS1, SS2, colordiff, True)
            if len(homo) == 0:
                return (False, 5, None)
            # SS2 = [node for node in SS2 if node not in homo]
            # SS2 = list(set(SS2)-set(homo))
        # breakpoint()
        pairs = [(SE1[a], b) for (a, b) in enumerate(hetro)] + [(SS1[a], b) for (a, b) in enumerate(homo[0:len(SS1)])]
        tc12 = tc13 = 0
        self.crosstable.init_bweights(scorelevel, len(SS2))
        epairs = []
        spairs = []
        for a, b in pairs:
            edge = self.competitors[a]["opp"][b]
            if a in SE1:
                epairs.append(edge)
            else:
                spairs.append(edge)
            tc12 += edge["quality"][qdefs.C12.value]
            tc13 += edge["quality"][qdefs.C13.value]

        bracket["bsno"] = self.update_bsn(scorelevel, [node for node in nodes if node["cid"] in SER])
        self.crosstable.update_hetrogenious(scorelevel, epairs, mdp, bracket["bsne"])
        self.crosstable.update_homogenious(scorelevel, spairs, bracket["bsne"], len(spairs))

        if c12 != tc12 or c13 != tc13: # We never end here if recursion is corrrect
            # breakpoint()
            return (False, 6, None)
        return (False, 0, pairs)

    # Non-Recursion

    def simple_permute(self, scorelevel, nodes, edges, S1, S2, colordiff, checkdf):
        testlevel = -1
        MAXSUB = 100000
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
                if scorelevel == testlevel:
                    breakpoint()
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
                    return permutation
        if self.verbose:
            print("Max permute", numsub)
        return []

    def canbepared(self, s1, s2, colordiff, depth):
        edge = self.competitors[s1]["opp"][s2]
        if edge["qc"] and self.try_and_update_colordiff(edge, colordiff):
            return True
        return False

    def cannotbepared(self, s1, s2, colordiff, depth):
        edge = self.competitors[s1]["opp"][s2]
        if s1 == 0:
            raise
            # breakpoint()
        self.free_and_update_colordiff(edge, colordiff)
        return True

    def canbecompleted(self, scorelevel, nodes, edges, s1, s2, permutations):
        # restnodes = s2[len(permutations):]
        restnodes = permutations[len(s1) :]
        if len(restnodes) == 0:
            return True
        if any([self.competitors[rest]["flt"] & (flt.DF1.value + flt.DF2.value) for rest in restnodes]):
            return False
        for rest in restnodes:
            if scorelevel <= self.pab:
                redge = self.competitors[rest]["opp"][0]
                if self.competitors[rest]["opp"][0]["canmeet"]:
                    min_c9 = min([edge["quality"][qdefs.C9.value] for edge in edges if edge["ca"] == 0 and edge["canmeet"]])
                    if redge["quality"][qdefs.C9.value] != min_c9:
                        return False
                    mod_nodes = [node for node in nodes if node["cid"] != rest and node["cid"] != 0]
                    mod_nodes = [node for node in mod_nodes if node["cid"] not in s1 and node["cid"] not in permutations[: len(s1)]]
                    mod_edges = self.get_edges(mod_nodes, edges)
                    (_, unpaired, _) = self.is_complete(mod_nodes, mod_edges)
                    # print("PAB return", unpaired == 0)
                    return unpaired == 0
            else:
                rest_nodes = [node for node in nodes if node["cid"] not in s1 and node["cid"] not in permutations[: len(s1)]]
                for edge in self.competitors[rest]["opp"]:
                    if edge["canmeet"] and (edge["sa"] == scorelevel - 1 or edge["sb"] == scorelevel - 1):
                        opp = edge["ca"] + edge["cb"] - rest
                        mod_nodes = [node for node in rest_nodes if node["cid"] != rest and node["cid"] != opp]
                        # mod_nodes = [node for node in _nodes if node['cid'] not in s1 and node['cid'] not in permutations[:len(s1)]]
                        mod_edges = self.get_edges(mod_nodes, edges)
                        (_, unpaired, _) = self.is_complete(mod_nodes, mod_edges)
                        if unpaired == 0:
                            # print("RES return", unpaired == 0)
                            return True
                # print("RES return", False)
                return False

    def xxpair_simple_round(self, bracket, nodes, edges, hetrogenious, numpairs, mdp, category):
        testlevel = -1
        scorelevel = bracket["scorelevel"]
        h = self.hammilton[scorelevel]
        # Don't bother try this with less than 20 players
        if h.get("cur_pairs", 0) < 10:
            return (None, 0)
        pairs = []
        if hetrogenious:
            if scorelevel > 1 and self.hammilton[scorelevel].get("this_hammilton", -1) <= mdp + 1:
                return (None, 1)
            # if scorelevel == 5: breakpoint()
            (mod_nodes, mod_edges) = self.select_nodes_and_edges(nodes, edges, scorelevel, self.levels)
            self.crosstable.update_hetrogenious(scorelevel, mod_edges, mdp, bracket["bsne"])
            s1len = 0
            while len(mod_nodes) and mod_nodes[s1len]["scorelevel"] > scorelevel:
                s1len += 1
            colordiff = self.analyze_colordiff(mod_nodes)
            while len(mod_nodes) and mod_nodes[0]["scorelevel"] > scorelevel:
                cid = mod_nodes[0]["cid"]
                for edge in mod_edges:
                    if (edge["ca"] == cid or edge["cb"] == cid) and edge["qc"] and self.try_and_update_colordiff(edge, colordiff):
                        pairs.append((edge["ca"], edge["cb"]))
                        mod_nodes = [node for node in mod_nodes if node["cid"] != edge["ca"] and node["cid"] != edge["cb"]]
                        # weight = self.crosstable.update_weight("E", edge)
                        break
                else:
                    return (None, 2)
            rempairs = len(mod_nodes) // 2
            return (pairs, rempairs)
        else:
            mod_nodes = [node for node in nodes if node["scorelevel"] >= scorelevel]
            if (slen := len(mod_nodes)) == 0:
                return ([], 6)
            # if self.pab >= scorelevel: slen -=1
            if scorelevel == testlevel:
                breakpoint()
            s1nodes = mod_nodes[: (slen) // 2]
            s2nodes = mod_nodes[(slen) // 2:]
            s1len = len(s1nodes)
            s2len = len(s2nodes)
            (s1nodes, bipartite_edges) = self.modify_edges(s1nodes, s2nodes, edges, scorelevel, category, "qc")
            # print("S2", len(s1nodes), len(s2nodes), s1nodes[-1]["cid"])
            if len(s1nodes) != len(s2nodes):
                return (None, 7)
            blob = 0 if s1len == s2len else s1nodes[-1]["cid"]

            slen = len(s1nodes) + len(s2nodes)
            bsnnodes = s1nodes + s2nodes
            bsno = {node["cid"]: i + 1 for i, node in enumerate(bsnnodes)}
            bracket["bsno"] = bsno

            colordiff = self.analyze_colordiff(s1nodes + s2nodes)
            # numdf = self.analyze_downfloat(scorelevel, s1nodes, s2nodes, edges, colordiff)
            c12 = colordiff["c12"]
            c13 = colordiff["c13"]
            histx = [0] * slen
            histc = [0] * slen
            for edge in bipartite_edges:
                if edge["qc"]:
                    if edge.get("colordiff", "").lower() in ["ww", "bb"]:
                        histx[bsno[edge["ca"]] - 1] += 1
                        histx[bsno[edge["cb"]] - 1] += 1
                    else:
                        histc[bsno[edge["ca"]] - 1] += 1
                        histc[bsno[edge["cb"]] - 1] += 1
            hist = [(a + b) for (a, b) in list(zip(histc, histx))]
            lim = min(hist) - 3 if min(histc) > 3 else 0
            if self.verbose:
                print(
                    "Rnd",
                    self.rnd,
                    "Scorelevel",
                    scorelevel,
                    "Len",
                    len(mod_nodes),
                    "Lim:",
                    lim,
                    "Ham",
                    self.hammilton[scorelevel]["cur_hammilton"],
                )
            if lim < 1:
                return (None, 8)
            if scorelevel == testlevel:
                breakpoint()
            for pairno in range(lim):
                cid = s1nodes[pairno]["cid"]
                for nodeno, node in enumerate(s2nodes[pairno:], start=pairno):
                    edge = self.competitors[cid]["opp"][node["cid"]]
                    if edge["qc"] and self.try_and_update_colordiff(edge, colordiff):
                        pairs.append((edge["ca"], edge["cb"]))
                        s2nodes = s2nodes[0:pairno] + [s2nodes[nodeno]] + s2nodes[pairno:nodeno] + s2nodes[nodeno + 1:]
                        self.crosstable.update_weight("S", edge)
                        break
                else:
                    if pairno <= 0:
                        return (None, 9)
                    pairs = pairs[:-1]
                    break
            numpairs = len(pairs)
            while numpairs > 0:
                restnodes = s1nodes[numpairs:] + s2nodes[numpairs:]
                restcid = self.get_nodeid(restnodes)
                restedges = [edge for edge in bipartite_edges if edge["ca"] in restcid and edge["cb"] in restcid]
                wpairs = sorted(self.pair_weighted_round(bracket, bsnnodes, restedges, "B", len(restcid) // 2, mdp, 0))
                tpairs = wpairs + pairs
                nc12 = sum(
                    filter(
                        None,
                        [
                            self.competitors[ca]["opp"][cb]["quality"][qdefs.C12.value]
                            for (ca, cb) in tpairs
                            if ca != blob and cb != blob
                        ],
                    )
                )
                nc13 = sum(
                    filter(
                        None,
                        [
                            self.competitors[ca]["opp"][cb]["quality"][qdefs.C13.value]
                            for (ca, cb) in tpairs
                            if ca != blob and cb != blob
                        ],
                    )
                )
                if self.verbose:
                    print("Simple pairs=", len(pairs), "Weighted pairs=", len(wpairs))

                if len(tpairs) * 2 == slen and nc12 == c12 and nc13 == c13:
                    break
                numpairs -= 1
                if numpairs > 0:
                    pairs = pairs[:-1]
            else:
                return (None, 10)
            return (tpairs, 0)

    def pair_weighted_round(self, bracket, nodes, edges, pairingmode, numpairs, mdp, category):
        scorelevel = bracket["scorelevel"]
        G = nx.Graph()
        nx_edges = []
        (modified_nodes, modified_edges) = self.modify_edges(nodes, None, edges, scorelevel, category, "canmeet")
        if len(modified_nodes) == 0:
            return []
        #  match (pairingmode):
        if pairingmode == "E":
            self.crosstable.update_hetrogenious(scorelevel, modified_edges, mdp, bracket["bsne"])
        elif pairingmode == "S":
            # bracket['bsno'] = self.update_bsn(scorelevel, [node for node in modified_nodes if node['scorelevel'] <= scorelevel and node['lmb'] != scorelevel])
            bracket["bsno"] = self.update_bsn(scorelevel, [node for node in modified_nodes if node["scorelevel"] <= scorelevel])
            self.crosstable.update_homogenious(scorelevel, modified_edges, bracket["bsno"], numpairs)
        elif pairingmode == "B":
            bracket["bsnb"] = {node["cid"]: i + 1 for i, node in enumerate(modified_nodes)}
            self.crosstable.update_bipartite(
                scorelevel, modified_edges, bracket["bsnb"], nodes[len(nodes) // 2]["cid"], nodes[-1]["cid"]
            )
        if self.reportlevel > 2:
            print("pair_weighted(" + pairingmode + "," + str(numpairs) + ") comp:", [c["cid"] for c in modified_nodes])
            print("edges", [(c["ca"], c["cb"]) for c in modified_edges])
        # category =0
        for c in [edge for edge in modified_edges]:
            (wcid, bcid) = (c["ca"], c["cb"])
            weight = self.crosstable.update_weight(pairingmode, c)
            if self.reportlevel > 3:
                print(pairingmode + "-Edge:", f"{wcid:3} {bcid:3} ", self.crosstable.format_weight(pairingmode, weight))
            nx_edges.append((wcid, bcid, weight))

        # t0 = time.time()
        G.add_weighted_edges_from(nx_edges)
        wpairs = nx.min_weight_matching(G)
        # t1 = time.time()
        return wpairs

    """
    Optimized pairing 
    When the number of players are much higher then the number of rounds
    we can try an pairing without exchanges and c12.

    update_nummeet(self, s0, key, offset=1)
    Returns 0 if we cannot garateee that pairing is possible
    othewise returns the minimum number of opponents you can meet
    Offset 1 since we add one downloaded player

    """

    """
    is_copmplete(self, nodes, edges, offset=0, weight= True, hist=None)
        nodes - node list
        edges - edge list, consider to use get_edges from a commection of edges
        offset - For test on hammilton_path only this must be (len(nodes)+1)//2
        weight - use weightrd algoritm if first test fails
        hist - use precalculated histogram 
    returns:
        (pairs, unpaired, hammilton)
        pairs - number of pairs that can be paired 
        unpaired - number of unpaired
        hammilton - difference between sorthist[0] - limit
 
        -1: No pairs can be formed
         0: pairing is not complete
         1: odd number of nodes that can be paired with (len(nodes)-1)/2 pairs
         2: even number of nodes that can be paired with len(nodes)/2 pairs
         3: odd number of nodes that forms a hammilton path
         4: even number of nodes that forms a hammilton path
    """

    def is_complete(self, nodes, edges, offset=-1, weight=True, hist=None, pab=False):
        numnodes = len(nodes)
        limit = (numnodes + 1) // 2
        if pab:
            limit += 1
            self.pab = -1
        if hist is None:
            hist = self.compute_whohasmet_histogram(nodes, edges)
        sorthist = sorted(hist)
        if len(sorthist) == 0 or sorthist[-1] == 0:
            return (0, numnodes, -1)  # None can meet
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
                self.pab = rpab
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

    # analyze_colordiff
    # nodes - list of nodes, all with a color preference "w2", "b2, "w1", "b1", "w0", "b0" of "  "
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

    def analyze_colordiff(self, nodes):
        # Always even number
        # if (len(nodes)%2) == 1:
        #    breakpoint()
        col = defaultdict(int)
        for node in nodes:
            cop = node["cop"].replace("  ", "nc")
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
        # Start with C12 and C13, it the pair increases the minimum C12/C13,
        # adjust with th C12 / C13 contrebution of current pair
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
        # Start with C12 and C13, it the pair increases the minimum C12/C13,
        # adjust with th C12 / C13 contrebution of current pair
        (c12, c13, pref) = self.calculate_c12_c13_pref((nc, w0, wc, b0, bc))
        # cd12 = 1 if edge["colordiff"].lower() in ["ww", "bb"] else 0
        # cd13 = 1 if edge["colordiff"] in ["WW", "BB"] else 0
        # if c12 + cd12 > colordiff['c12'] or c13 + cd13> colordiff['c13']:
        #    return False
        colordiff.update({"nc": nc, "w0": w0, "wc": wc, "b0": b0, "bc": bc, "c12": c12, "c13": c13, "pref": pref})
        return True

    def analyze_downfloat(self, scorelevel, s1nodes, s2nodes, edges, colordiff):
        if s1nodes[-1]["scorelevel"] != scorelevel:
            return 0
