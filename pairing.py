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
from crosstable import crosstable, flt
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
            'qc': True,       # true if 'canmeet' and QC9-QC11 == 0 and QC14-QC21 == 0
            'colordff': 'BB', # color difference for pair. 
            'colorrule': 'E.4',  # rules used to decide color
            'mode': "HO",      # selected from hetrogenios "HE" of homogenios "S" pairs
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
          },
           ...
    ]



+--- Return object ---
         {
             'round': 4
             'check': True/False
             'analysis': [       # Array of score brackets, anaalyze existing pairing
                {
                    'scorelevel': <level> ,     # Bracket level 
                    'competitors': [],          # Array of competitor objects   
                    'pairs': []                 # Pairs
                    'downfloaters':  [5, 11]    # Array of downfloated competitors
                    'remaining':  [23, 0]       # Array of remaining competitors
                    'quality': [...]            # array QC6-QC21, HE1-HE2, HO1-HO5
                    'pab': False,               # true if this is PAB scorelevel
                },
                .... more brackets                    
                ],
            'checker': [       # Array of score brackets, same structure as analysis
                        ...
                        ]
            }


"""



class pairing:

    # constructor function
    def __init__(self, tournament, rnd, params):
        # helpers.json_output(sys.stdout, cmps[12]['tiebreakDetails'])
        self.tournament = tournament
        self.rnd = rnd
        self.numcompetitors = len(tournament["competitors"])
        self.topcolor = self.get_topcolor(tournament, params.get("top_color", ""))
        self.experimental = params.get("experimental", None)
        self.verbose = params.get("verbose", None)
        self.nummeets = int((rnd-1) * tournament.get("maxMeets", 1) / tournament["numRounds"]) + 1
        rank = "experimental" in params and "fakerank" not in params["experimental"] and params.get('rank', False)
        self.rank = "rnk" if rank else "cid"
        self.rules = "2022-01-01"
        self.optimize = "weighted" not in self.experimental
        self.showtime = "time" in self.experimental

    def get_topcolor(self, tournament, defcolor):
        if "topColor" in tournament:
            # print("Topcolor if", tournament["topColor"].lower())
            return tournament["topColor"].lower()
        mlist = tournament["matchList"]
        glist = tournament["gameList"]
        clist = mlist if "matchList" in tournament and len(mlist) > 0 else glist
        if len(clist) > 0:
            clist = sorted(clist, key=lambda p: (p["round"], (p["black"] == 0), min(p["white"], p["black"])))
            topcolor = "w" if clist[0]["white"] < clist[0]["black"] else "b"
            return topcolor.lower()
        if defcolor in ["w", "b", "W", "B"]:
            return defcolor.lower()
        return "w" if random.random() < 0.5 else "b"

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
        self.reportlevel = reportlevel * self.verbose
        self.optimize = "weighted" not in self.experimental and not checkonly
        self.crosstable = self.get_crosstable(self.experimental, self.checkonly, self.verbose)
        self.get_edge_quality = self.crosstable.get_edge_quality
        t0 = time.time()
        (competitors, opponents) = self.crosstable.init_engine(
            self.tournament, self.rnd, self.nummeets, self.topcolor, self.rank 
        )
        self.competitors = competitors
        self.opponents = opponents

        t1 = time.time()
        if self.verbose > 1:
            print("Init engine:", f"{t1 - t0:.3f} s")
        self.levels = levels = len(self.crosstable.levels())

        t0 = time.time()
        nodes = self.list_nodes(competitors)
        edges = self.list_edges(opponents)
        t1 = time.time()
        if self.verbose > 1:
            print("Init nodes and edges:", f"{t1 - t0:.3f} s")

        t0 = time.time()
        self.hamilton = self.compute_hamilton(nodes, edges)
        if self.hamilton[levels - 1].get("rem_unpaired", 0) != 0:
            return []
        t1 = time.time()
        if self.verbose > 1:
            print("Init Hamilton:", f"{t1 - t0:3f} s")

        t0 = time.time()

        (pabbracket, pablevel, nodes, edges) = self.find_pab(nodes, edges)

        t1 = time.time()
        if self.verbose > 1:
            print("PAB:", pablevel, "edges:", len(edges), f"{t1 - t0:.3} s")

        scorelevel = nodes[0]["scorelevel"] if len(nodes) > 0 else -1

        self.roundpairing = []
        testpab = False
        self.timer = {}
        self.time = 0.0
        self.stime = 0.0

        while len(nodes) > 0 and scorelevel >= 0:
            self.bracket = None
            if self.verbose > 1:
                print("Roundpairing, scorelevel ", scorelevel, ", Nodes = ", len(nodes), ", edges = ", len(edges))
            (bracket, nodes, edges, testpab) = self.pair_bracket(scorelevel, nodes, edges, testpab)
            if bracket:
                self.roundpairing.append(bracket)
            scorelevel -= 1
        if len(nodes) > 0:
            breakpoint()
            raise            
        if pabbracket:
            self.roundpairing.append(pabbracket)
        self.update_board(self.roundpairing)
        if self.showtime and self.verbose > 1:
            print(f"Round {self.rnd}, {'check' if self.checkonly else 'pairing'}:") 
            for key, value in self.timer.items():
                print(f"--- {key} time {value:.3f} s ---")

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
        cmpHO1 = [False] * (self.crosstable.BLOB + 1)
        cmpHO2 = [False] * (self.crosstable.BLOB + 1)
        for node in nodeid1:
            cmpHO1[node] = True
        for node in nodeid2:
            cmpHO2[node] = True
        new_edges = [edge for edge in edges if cmpHO1[edge["ca"]] and cmpHO2[edge["cb"]]]
        return new_edges

    def list_nodes(self, competitors):
        mod_nodes = sorted([node for node in competitors if node["rfp"]], key=lambda s: (-s["scorelevel"], s[self.rank]))
        return mod_nodes
    
    def list_edges(self, opponents):
        edges = []
        for i, line in enumerate(opponents):
            edges +=  [edge for edge in line[i+1:-1] if edge["canmeet"] ]
        mod_edges = sorted(edges, key=lambda edge: (-min(edge["sa"], edge["sb"]), -max(edge["sa"], edge["sb"]), edge["ca"], edge["cb"]))
        return mod_edges

    # compute_hamilton
    # for each scorelevel, compute the number of paired unpaired players
    # Returns an array of length levels, and for each level:
    # "rem_pairs" : total pairs that can be made from this scorelevel and below
    # "rem_unpaired" : total unpaired for this scorelevel and below
    # "rem_hamilton" : >= 0 if an hamilton path exists for this scorelevel and below
    # "cur_pairs" : number of pairs than maximum can be formed in this scorelevel
    # "cur_unpaired" : number of minimum unpaired players in this scorelevel
    # "cur_hamilton" : >= 0 if an hamilton path exists for this scorelevel
    # "cross_hamilton" : >= 0 if there are safe to downfloat one player

    def compute_hamilton(self, nodes, edges):
        levels = self.levels
        hamilton = [{} for _ in range(levels)]
        self.pablevel = -1
        if self.checkonly:
            return hamilton
        # rest_nodes = nodes[::-1] if self.pablevel == 0 else nodes[-2::-1]
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
                # update each scorelevel - hamilton
                rest = hamilton[laste]
                if laste > 0:
                    (rest["cur_pairs"], rest["cur_unpaired"], rest["cur_hamilton"]) = self.is_complete(
                        ll_nodes, None, weight=False, hist=ll_hist
                    )
                    (_, _, fh) = self.is_complete(ll_nodes, None, weight=False, hist=fl_hist)
                    (_, _, lh) = self.is_complete(ff_nodes, None, weight=False, hist=lf_hist)
                    rest["cross_hamilton"] = min(fh, lh)
                # more to do?
                # find if remaining is pairable. This in marked on lasteventlevel+1
                # rest = hamilton[laste+1]
                test_nodes = rest_nodes[: nodeptr[laste + 1]]  # if laste >= self.pablevel else rest_nodes[nodeptr[firste]:-1]
                (rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hamilton"]) = \
                    self.is_complete(test_nodes, rest_edges[:i], hist=hist[: nodeptr[laste + 1]], pab = firste == levels)
                # print(laste, len(test_nodes), rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hamilton"])
                #(rest["rem_pairs"], rest["rem_unpaired"], rest["rem_hamilton"]) = \
                #    self.is_complete(test_nodes, rest_edges[:i], hist=hist[: nodeptr[laste + 1]], pab = firste == levels)
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
                ll_hist[ll_id[edge["ca"]]] += 1
                ll_hist[ll_id[edge["cb"]]] += 1
            if abs(edge["sa"] - edge["sb"]) == 1:
                fl_hist[ff_id[edge["ca"] if edge["sa"] < edge["sb"] else edge["cb"]]] += 1
                lf_hist[ll_id[edge["cb"] if edge["sa"] < edge["sb"] else edge["ca"]]] += 1

        # laste += 1
        if bp:
            breakpoint()
        return hamilton

    def is_complete(self, nodes, edges, weight=False, hist=None, pab=False):
        num_pairs = len(nodes) // 2
        num_unpaired = len(nodes) - 2 * num_pairs
        is_hamilton = num_unpaired == 0
        return (num_pairs, num_unpaired, is_hamilton)