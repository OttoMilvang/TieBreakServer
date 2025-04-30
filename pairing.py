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
from decimal import *
from itertools import *
import math
import networkx as nx
from crosstable import crosstable
import qdefs

N8  = qdefs.N8

"""
Structre 

+--- competitor
|         {
            'cid': 9, 
            'pts': Decimal('0.5'), 
            'acc': Decimal('0.5'), 
            'rfp': True / False
            'num': 2, 
            'met': {'val': 2, 1: 1, 2: 10}, 
            'cod': 0, 
            'cop': 'b0', 
            'csq': ' bw', 
            'flt': 2, 
            'top': False,
            'opp': array of Pointers into crosstable
            'bsn' : internal order ov bracket sequence number 
            '?meet?': intermediate results 
          }
+--- crosstable: [  
|         {
            'canmeet': True, 
            'played': 0, 
            'psd': [2, 1], 
            'w': '3', 
            'b': '17', 
            'c10': 0, 
            'c11': 0, 
            'c12': 0, 
            'c13': 0, 
            'c14': 0, 
            'c15': 0, 
            'c16': 0, 
            'c17': 1, 
            'c18': '', 
            'c19': '', 
            'c20': '', 
            'c21': '1',
|             cdiff: color difference 
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
            'check': True/False
            'analyze': [       # Array of score brackets, anaalyze existing pairing
                {
                    'scorebracket': <points> ,  # Bracket points
                    'competitors': [],          # Array of competitor objects   
                    'pairs': []                 # Pairs
                    'downfloaters':  [5, 11]    # Array of downfloated competitors
                    'psd': [3, 0]               # Pairing scorelevel difference
                    'c10': 0                    # C10
                    'c11': 0                    # C11
                    'c12': 0                    # C12
                    'c13': 0                    # C13
                    'c14': 1                    # C14
                    'c15': 0                    # C15
                    'c16': 0                    # C16
                    'c17': 0                    # C17
                    'c18': '3'                  # C18 Pairing score difference*2 for C13, base36 sorted in string 
                    'c19': '0'                  # C19 
                    'c20': '0'                  # C20
                    'c21': '0'                  # C21
                    'heblen': 2,                # Len of s1 in  heterogeneous bracket
                    'hebpno' : 17,              # Perrmutation number in heterogeneous bracket
                    'hebmax': 24,               # Max possible perrmutations in heterogeneous bracket
                    'hoblen': 2,                # Len of s1 in  homoogeneous bracket
                    'hpbpno' : 17,              # Perrmutation number in homogeneous bracket
                    'hobmax': 24,               # Max possible perrmutations in homogeneous bracket
                    'exchb1' : [5 , 7],         # BSN moved from S1 to S2
                    'exchb2' : [8 , 9],         # BSN moved from S2 to S1
                    'exclen' : 2,               # nuber of exchanged BSNs
                    'exclen' : 2,               # nuber of exchanged BSNs
                    'excdif'' : 5,              # Sum of BSM in exchb2 and exchb1
                    'excdi1': 2,                # Max diff of BSN in exchb1
                    'excdi2': 1,                # Max diff of BSN in exchb2
                },
                .... more brackets                    
                ],
            'pairing': [       # Array of score brackets, same structure as analyze
                        ...
                        ]
            }

    Values: max players N=1000,  max rounds R=100, moved down players M, maxpsd P, maxbsn B
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
    hetrogenios
        R**M                    - R**(bsn mdp)
        R**M                    - R**(bsn mdp)*(bsn opponent)
    homogenious
        R                       - 1 if bsn > r else 0
        R*R                     - bsn
        10**B                   - 10**bsn if wsn <=r
        10**B                   - 10**bsn if wsn >r
        10**3B                  - 10**(3*n) + 10*(n-wbsn)*bbsn
  

                      
"""

import sys;
import helpers;


class pairing:

    

    # constructor function    
    def __init__(self, rnd, cmps, topcolor, unpaired, maxmeet, experimental, verbose):
        
        #helpers.json_output(sys.stdout, cmps[12]['tiebreakDetails'])
        self.rnd = rnd
        self.cmps = cmps
        self.topcolor = topcolor
        self.unpaired = [helpers.parse_int(u) for u in unpaired]
        self.maxmeet = maxmeet
        self.experimental = experimental
        self.verbose = verbose


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
                    
    def compute_pairing(self, checkonly):
        self.checkonly = checkonly
        self.crosstable = crosstable(self.rnd, self.experimental, self.checkonly, self.verbose)
        edges = self.crosstable.list_edges(self.cmps, self.maxmeet, self.topcolor, self.unpaired)

        (competitors, edges) = self.list_competitors(self.crosstable.crosstable, edges)
        self.competitors = { c['cid']: c for c in competitors}
        nodes = competitors[:]
        
        
        pab = self.find_pab(nodes, edges)
        if pab == -1:
            if self.verbose:
                print('No legal pairing')
            return []

        if self.verbose:
            print('PAB:', pab, 'edges:', len(edges))

        edges = self.filter_pab(edges, pab) 
        scorelevel = nodes[0]['scorelevel'] + (1 if nodes[0]['scorelevel'] == pab else 0)

        self.roundpairing = []
        ispab = False
        while len(nodes) > 0 and scorelevel >= 0:
            self.bracket = None
            if self.verbose > 1:
                print("Roundpairing, scorelevel ", scorelevel, ", Nodes = ", len(nodes), ", edges = ", len(edges) )
            (bracket, nodes, edges) = self.pair_bracket(scorelevel, nodes, edges, ispab)
            self.roundpairing.append(bracket)
            scorelevel -= 1
            ispab = scorelevel <= pab and bracket['quality'][N8] <= 1
            if self.verbose > 1:
                print("Pab:",scorelevel, ispab, bracket['quality'][N8])
        self.update_board(self.roundpairing)
        return self.roundpairing    


                    
    def list_competitors(self, crosstable, edges):
        competitors = sorted([competitor for competitor in crosstable if competitor['rfp']], key=lambda s: (-s['scorelevel'], s['cid']))
        cids = [competitor['cid'] for competitor in competitors]
        edges = [edge for edge in edges if edge['ca'] in cids and edge['cb'] in cids]
        return(competitors, edges)


    def pair_bracket(self, scorelevel, nodes, edges, pab):
        bracket = {
            'scorelevel' : scorelevel,
            'competitors': [c['cid'] for c in nodes if c['scorelevel'] >= scorelevel],
            'pairs': [],
            'downfloaters': [],
            'remaining' : [],
            'quality': [None]*qdefs.QL,
            'bsne' : self.update_bsn(scorelevel, nodes),
            'bsno' : {},
            'valid' : True
            }

        #prefix = 'a' if self.checkonly else 'p'
        if self.verbose and scorelevel < len(self.crosstable.level2score):
            print('================================================')
            print('Bracket: ', self.crosstable.level2score[scorelevel], ', bsn: ', len(bracket['bsne']), ", nodes: ", len(nodes), ", edges: ", len(edges))
        #print(nodes[0])
        self.crosstable.update_crosstable(scorelevel, nodes, edges, pab)
        
        S = 0 # Number of homogenious pairs
        wpairs = []

        if self.verbose:
            bcompetitors = [c for c in bracket['competitors']] 
        for hetrogenious in [True, False]:
            self.crosstable.init_weights(scorelevel, nodes, bracket['downfloaters'])
            pairs = self.pair_round(bracket, nodes, edges, hetrogenious, S)
            paired = []

            for (a, b) in pairs:
                alevel = self.competitors[a]['scorelevel'] 
                blevel = self.competitors[b]['scorelevel'] 
                c = self.competitors[a]['opp'][b]
                if hetrogenious:
                    if alevel > scorelevel and blevel == scorelevel or alevel == scorelevel and blevel > scorelevel:
                        wpairs.append(c)
                        paired.append(a)
                        paired.append(b)
                        bracket['pairs'].append(c) 
                        #vprint("Hetro pair:", c['w'], c['b'])
                    elif alevel <= scorelevel and blevel == scorelevel or alevel == scorelevel and blevel <= scorelevel:
                        S += (1 if alevel == scorelevel and blevel == scorelevel else 0) 
                    elif alevel < scorelevel and blevel > scorelevel or alevel > scorelevel and blevel < scorelevel:
                        self.competitors[a if alevel > scorelevel else b]['lmb'] = scorelevel
                else:
                    wpairs.append(c)
                    if alevel == scorelevel and blevel == scorelevel:
                        paired.append(a)
                        paired.append(b)
                        bracket['pairs'].append(c) 
                        # print("Homo pair:", a, b)
                    elif alevel >= scorelevel and blevel < scorelevel or alevel < scorelevel and blevel >= scorelevel:
                        c['down-' + str(scorelevel)] = a if alevel == scorelevel else b
                        bracket['downfloaters'].append(a if alevel >= scorelevel else b) 
                        bracket['remaining'].append(a if alevel < scorelevel else b) 
                        # print("Down pair:", a, b)
                    else:
                        bracket['remaining'].append(a)
                        bracket['remaining'].append(b)
                        # print("Rem pair:", a, b)

            nodes = [node for node in nodes if node['cid'] not in paired]
            edges = [c for c in edges if c['ca'] not in paired and c['cb'] not in paired]

            if self.verbose and scorelevel < len(self.crosstable.level2score):
                print("-Hetrogenious" if hetrogenious else "-Homogenious")
                print('Scorelevel    = ',  scorelevel)
                print('Competitors   = ', bcompetitors)
                print('Pairs         = ', [(c['w'], c['b'])  for c in bracket['pairs']])
                if not hetrogenious:
                    print('Down          = ', [c for c in bracket['downfloaters']])
                bcompetitors = [c for c in bracket['competitors'] if c not in  paired] 
        bracket['quality'] = self.crosstable.compute_weight(wpairs, bracket['quality'])
        return (bracket, nodes, edges)
        




    def update_board(self, roundpairing):
        pairs = []
        for bracket in roundpairing:
            cids = bracket['competitors']
            for pair in bracket['pairs']:
                (w, b) = (pair['w'], pair['b']) 
                (ws, bs) = (self.competitors[w]['acc'], self.competitors[b]['acc'])
                ipab = w == 0 or b == 0
                maxs = max(ws,bs)
                sums = ws + bs
                rank = w if w < b else b                
                pairs.append({
                    'pair' : pair,
                    'ipab' : ipab,
                    'maxs' : maxs,
                    'sums' : sums, 
                    'rank' : rank,
                    })
                board = 0
        npairs = []
        for pair in  sorted(pairs, key=lambda c: (c['ipab'],  -c['maxs'], -c['sums'], c['rank'])):
            npair = pair['pair']
            (w, b) = (npair['w'], npair['b']) 
            board += 1 
            if self.verbose > 1:
                print("Board: ", board, w, b, pair['ipab'], pair['maxs'], pair['sums'], pair['rank'], )
            npair['board'] = board 
            npairs.append(npair)
        return npairs



    """
    find_score_for_pab find lowest scroe that can meet PAB
    Just sort on score, and try the compeitors one by one if they can have a bye
    and the rest of the competitors are pairable.
    Only competitors with this score can have PAB, 
    set competitors with other score with canmeet = False
    
    """

    def find_score_for_pab(self, s0, edges):
        num = len(s0)
        s0sorted =  sorted(s0, key=lambda s: (s["acc"]))
        for i in range(1, num):
            if s0sorted[i]['opp'][0]['canmeet']:
                (s0sorted[1], s0sorted[i]) = (s0sorted[i], s0sorted[1])
                canmeet = self.is_complete(s0sorted[2:])  
                (s0sorted[1], s0sorted[i]) = (s0sorted[i], s0sorted[1])
                if canmeet > 0:
                    pab = s0sorted[i]['acc']
                    break
        # updete PAB
        for i in range(1, num):
            if s0sorted[i]['acc'] != pab:
                s0sorted[i]['opp'][0]['canmeet'] = False
        return pab     
    
    
    """
    update_bsn
    Competitors are sorted on score_level and then on TPN
    
    """
 

            
    def update_bsn_old(self, scorelevel, competitors, name):
        for i in range(len(competitors)):
            if competitors[i]['scorelevel'] < scorelevel:
                return i
            competitors[i][name] = i+1
        return len(competitors)

    def update_bsn(self, scorelevel, competitors):
        bsn = {}
        for i in range(len(competitors)):
            if competitors[i]['scorelevel'] < scorelevel:
                return bsn
            bsn[competitors[i]['cid']] = i+1
        return bsn




    """
    General pairing 
    Weighthed pairing will always be correct, but the number of edges is 
    in the order P**2 where P is the number of players. For more than 500 players
    the weighted method is slow, and may stop due to high memory consumtion. 

    Therfore if no switches say otherwise the program will first try a simple
    algorithm, and then the weighted.    
   
    pair_pab(nodes, edges)

    

   
    """

    def find_pab(self, nodes, edges):
        return self.find_weighted_pab(nodes, edges)

    def filter_pab(self, edges, pab):
        return list(filter(lambda edge: edge['ca'] != 0 or edge['sb'] == pab, edges))


    def pair_round(self, bracket, nodes, edges, hetrogenious, S):
        return self.pair_weighted_round(bracket, nodes, edges, hetrogenious, S)



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
     
    

    def find_weighted_pab(self, nodes, edges):
        pab = 0
        G = nx.Graph()
        self.crosstable.compute_pab_weight(edges)
        nx_edges = [(edge['ca'], edge['cb'], edge['iweight']) for edge in edges]
        G.add_weighted_edges_from(nx_edges)
        matching =  sorted(nx.min_weight_matching(G))
        pabpairs = list(filter(lambda nx_edge: list(nx_edge)[0] == 0 or list(nx_edge)[1] == 0, matching))
        if len(matching) < len(nodes)//2:
            return -1 # No legal pairing
        if len(pabpairs) > 0:  # We have PAB
            (w, b) = pabpairs[0]
            pabnode = list(filter(lambda node: node['cid'] == max(w,b), nodes))[0]
            pab = pabnode['scorelevel']
        return pab
        


    def pair_weighted_round(self, bracket, nodes, edges, hetrogenious,S):
        scorelevel = bracket['scorelevel']
        G = nx.Graph()
        nx_edges = []
        bracket['bsno'] = self.update_bsn(scorelevel, [node for node in nodes if node['scorelevel'] <= scorelevel and node['lmb'] != scorelevel])
        if hetrogenious:
            self.crosstable.update_hetrogenious(scorelevel, edges, bracket['bsne'])
            option = "E"
        else:
            self.crosstable.update_homogenious(scorelevel, edges, bracket['bsno'], S)
            option = "S"
        if self.verbose > 1:
            print("pair_weighted(" + str(hetrogenious) + "," + str(S) + ") comp:", [c['cid'] for c in nodes])
        for c in [edge for edge in edges]:
                (wcid, bcid) = (c["ca"], c["cb"]) 
                if c['canmeet']: # and downfloatcount[wcid] >= 0 and downfloatcount[bcid] >= 0:
                    weight = self.crosstable.weight(c, option)
                    if self.verbose > 2:
                        print(option + "Add", c['tweight'], wcid, bcid)
                    nx_edges.append((wcid, bcid, weight))
        if self.verbose > 2:
            for (w,b,ww) in nx_edges:
                print("Egde: ", (str(w) if w>10 else ' ' + str(w)), (str(b) if b>10 else ' ' + str(b)), ww )                
                
        G.add_weighted_edges_from(nx_edges)
        wpairs = sorted(nx.min_weight_matching(G))
        # print("Homo ", scorelevel, wpairs, len(wpairs))
        return wpairs
            
        

    """
    Optimized pairing 
    When the number of players are much higher then the number of rounds
    it is easy to optimize the pairing.
    
    
    """
    def pair_round_1(self, bracket, nodes, edges, hetrogenious,S):
        return