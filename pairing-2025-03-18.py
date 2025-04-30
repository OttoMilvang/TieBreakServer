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
import math
from decimal import *
from itertools import *
import math
import networkx as nx
from crosstable import crosstable

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
|         {
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
        self.pab = Decimal("-1.0")
        self.experimental = experimental
        self.verbose = verbose

    """
    init_crosstable / update crosstable
        Update competitors first from cmps[i]['tiebreakDetails']
        THe crosstable is an virtual crosstable of opp[] elements.
        A game between player a and b is described in the crosstable elsement self.cmps[a]['opp'][b] === self.cmps[b]['opp'][a]
        init_crosstable updates:
            For all pairs in the crosstable
            canmeet - True if they are alowd to meet, False othewise
            played - Number of times they have met
            psd - The differnce in scorelevels between the players (array)
        update_crosstable updates:
            For all pairs in a scorebracket
            c10 - c21 - The rules

        
    """
    



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
        self.crosstable = crosstable(self.cmps, self.maxmeet, self.topcolor, self.unpaired, self.experimental, self.checkonly, self.verbose)
        self.roundpairing = []
        s0 = self.list_competitors()
        if not self.is_complete(s0):
            if self.verbose:
                print('No legal pairing')
            return []
        
        if self.crosstable.crosstable[0]['rfp']:
            self.pab = self.find_score_for_pab(s0)
            if self.verbose > 1:
                print('PAB:', self.pab)

        num = len(s0)
        mdp = []
        remaining =  sorted(s0, key=lambda s: (-s['acc'], s['cid']))
        while len(remaining) > 0:
            self.bracket = None
            scorebracket = remaining[0]['acc']
            resident =  list(filter(lambda competitor: competitor['acc'] == scorebracket , remaining))
            remaining = remaining[len(resident):]
            mdp = self.pair_bracket(scorebracket, mdp, resident, remaining)
            if self.verbose > 1:
                print('Remaining', len(mdp), '+', len(remaining))
            #self.roundpairing.append(self.bracket)
        self.update_board(self.roundpairing)
        return self.roundpairing    

                    
    def list_competitors(self):
        competitors = []
        for competitor in self.crosstable.crosstable:
            if competitor['rfp']:
                competitors.append(competitor)
        return(competitors)


    def update_board(self, roundpairing):
        pairs = []
        for bracket in roundpairing:
            cids = { c['cid'] : c for c in bracket['competitors']}
            for pair in bracket['pairs']:
                (w, b) = (pair['w'], pair['b']) 
                (ws, bs) = (cids[w]['acc'], cids[b]['acc'])
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
                print(board, w, b, pair['ipab'], pair['maxs'], pair['sums'], pair['rank'], )
            npair['board'] = board 
            npairs.append(npair)
        return npairs

    """
    is_complete test if a set of players are complete (there are a legal paring)
    
    
    """

    def update_nummeet(self, s0, meet):
        mincanmeet = len(s0)
        for a in s0:
            nummeet = 0
            for b in s0:
                #print('num', a['cid'], b['cid'], a['opp'][b['cid']]['canmeet'])
                if a['opp'][b['cid']]['canmeet']:
                    nummeet += 1
            a[meet] = nummeet
            mincanmeet = min(mincanmeet, nummeet)
        return mincanmeet


    def is_complete_debug(self, s0, depth=0):   # Rename this to is_complete, and next to is_complete_debug
        comp = self.is_complete_debug(s0, depth)
        dfcids = sorted([c['cid'] for c in s0])
        print("Iscomplete", depth, dfcids, comp)
        return comp


        
    def is_complete(self, s0, depth=0):
        num = len(s0)
        if num == 0:
            return 1
        #print('Depth: ' + str(depth), num)
        num2 = num//2
        meet = 'meet' + str(depth)
        mincanmeet = self.update_nummeet(s0, meet)
        if mincanmeet == 0 or mincanmeet >= num//2:
            #print('ok', mincanmeet) 
            return mincanmeet
        w2 = sum(c['cop'] == 'w2' and not c['top'] for c in s0)
        b2 = sum(c['cop'] == 'b2' and not c['top'] for c in s0)
        if w2 > num2 or b2 > num2:
            return(0)
        s0sorted =  sorted(s0, key=lambda s: (s[meet]))
        shorttest = True
        for i in range(num2):
            if s0sorted[i][meet] <= i:
                shorttest = False
                break
        if shorttest:
            #print('st', mincanmeet) 
            return mincanmeet
        
        for i in range(1, num):
            if s0sorted[0]['opp'][s0sorted[i]['cid']]['canmeet']:
                (s0sorted[1], s0sorted[i]) = (s0sorted[i], s0sorted[1])
                #print(s0sorted[0]['cid'], s0sorted[1]['cid'])
                longtest = self.is_complete(s0sorted[2:], depth + 1)
                (s0sorted[1], s0sorted[i]) = (s0sorted[i], s0sorted[1])
                if longtest > 0:
                    #print('lt', mincanmeet) 
                    return(mincanmeet)
        #print('test', mincanmeet) 
        return 0

    """
    find_score_for_pab find lowest scroe that can meet PAB
    Just sort on score, and try the compeitors one by one if they can have a bye
    and the rest of the competitors are pairable.
    Only competitors with this score can have PAB, 
    set competitors with other score with canmeet = False
    
    """

    def find_score_for_pab(self, s0):
        num = len(s0)
        s0sorted =  sorted(s0, key=lambda s: (s['acc']))
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
    do_pairing
    Just sort on score, and try the compeitors one by one if they can have a bye
    and the rest of the competitors are pairable.
    Only competitors with this score can have PAB, 
    set competitors with other score with canmeet = False
    
    """
    

        
    def pair_bracket(self, scorebracket, mdp, resident, remaining):

        if self.verbose:
            print('================================================')
            print('Bracket:', scorebracket, 'bsn:', len(mdp), '+' ,len(resident))

        bracket = self.find_pairing_w(scorebracket, mdp, resident, remaining)
        return bracket['downfloaters'][:] + bracket['limbo']


    """
    find_downfloaters
    ameet will show how many each player can meet
    
    
    """

    def is_downfcomplete(self, downf, remaining, mincmeet):
        # TODO test
        return self.is_complete(downf + remaining)


    def compute_psd(self, scorebracket, competitors, add=''):
        psd = []
        scorelevel = self.crosstable.scorelevels[scorebracket]
        #print(down)
        for competitor in competitors:
            psd.append(competitor['scorelevel'] - scorelevel)
            #print('t', '|' +val+ '|')
            psd = sorted(psd, reverse=True )    
        return psd

    def compute_scoredownfloaters(self, scorelevel, competitors, add=''):
        return sorted([c['scorelevel'] for c in competitors], reverse=True)


    """
    enum_brackets(self, scorebracket, mdp, resident, remaining, listall):
    scorebracket - Score of bracket
    mdp - Moved down players
    resident - Resident players
    remaining - Remaining players
    listall - List all pairings, True: also unvalid, False: only valid

    Find all legal combinations of mdp + resident such that:
    Downfloaters + remaining is pairable
    Number of downfloater is as minimized

    limbo is the subset of mdp+resident that cannot be paired in the score bracket
    
    """
    
    def enum_brackets(self, scorebracket, mdp, resident, remaining, listall):
        if self.verbose > 1:
            print("Enum: ", scorebracket, "Mdp: ", [c['cid'] for c in mdp], "Resident: ", [c['cid'] for c in resident])

        # reorder mdp + resident + remaining => competitors + rest
        scorelevel = self.crosstable.scorelevels[scorebracket]

        candidates = mdp + resident
        minbmeet = self.update_nummeet(candidates, 'bmeet')
        limbo = list(filter(lambda competitor: competitor['bmeet'] == 0 , candidates))
        competitors = list(filter(lambda competitor: competitor['bmeet'] > 0 , candidates))
        rest = limbo + remaining
        numcompetitors = len(competitors)
        if len(mdp) + len(resident) + len(remaining) != len(competitors) + len(rest):
            raise
        
        # needdf is thhe number of downfloaters need to pair all players in rest
        # numdownf is the minimum number of downfloaters
 
        mincmeet = self.update_nummeet(rest, 'cmeet')
        needdf = len(list(filter(lambda competitor: competitor['cmeet'] == 0 , rest)))
        maxpairs = (numcompetitors-needdf) // 2 
        numdownf = numcompetitors - maxpairs * 2
        #print(minbmeet, len(limbo), len(competitors), need, maxpairs, numdownf )
 
        
        # Start with numdownf and increase by 2:
        # Expand all combination with competitors amd numfloat into pairs of comp + down 
        # Compute if comp is pairiable and down+rest is pairable, list both valid and invalid until no pairing is possible
        found = False
        brackets = []
        while not found and numdownf < numcompetitors:
            if self.verbose > 1:
                print('Combinations: ',  numcompetitors, numdownf)
            allcomp = list(combinations(competitors, numcompetitors - numdownf))     
            alldown = list(combinations(competitors, numdownf))
            alllen  = len(allcomp)
            if self.verbose > 1:
                print('Compnum: ', alllen)
            for i in range(alllen):
                comp = list(allcomp[i])
                down = list(alldown[alllen - i - 1])
                # print('Try', len(comp), len(down), len(limbo))
                if self.verbose > 1:
                    print('Comp/down', sorted([c['cid'] for c in comp]), sorted([c['cid'] for c in down]))
                c1 = self.is_complete(comp)
                #    print('Comp/down', sorted([c['cid'] for c in down + rest]), sorted([c['cid'] for c in down]))
                c2 = self.is_downfcomplete(down, rest, mincmeet)
                valid = c1 > 0 and c2 > 0
                # print("c1", c1, "c2", c2)
                if valid or listall:
                    psd = self.compute_psd(scorebracket, down + limbo)
                    if self.verbose > 1:
                        print('Psd', psd, self.compute_scoredownfloaters(scorebracket, down + limbo))
                    bracket = {
                        'scorebracket' : scorebracket,
                        'scorelevel' : scorelevel,
                        'competitors': sorted(comp, key=lambda s: (-s['acc'], s['cid'])),
                        'downfloaters': sorted(down, key=lambda s: (-s['acc'], s['cid'])),
                        'limbo': sorted(limbo, key=lambda s: (-s['acc'], s['cid'])),
                        'psd': psd, 
                        'sdf' : self.compute_scoredownfloaters(scorebracket, down + limbo),
                        'pairs': [],
                        'nextb': [],
                        'quality': { 'weight' : 0, **{'c'+str(i): None  for i in range(6,10)} },
                        'valid' : valid
                        }
                    brackets.append(bracket)
                found = found or valid
            numdownf += 2
        if len(brackets) == 0:
            psd = self.compute_psd(scorebracket, mdp + resident)
            if self.verbose > 1:
                print('None', scorebracket, psd)
            brackets.append({
                'scorebracket' : scorebracket,
                'scorelevel' : scorelevel,
                'competitors': [],
                'downfloaters': competitors,
                'limbo': limbo,
                'psd' : psd,
                'sdf' : self.compute_scoredownfloaters(scorebracket, mdp + resident),
                'pairs': [],
                'nextb': [],
                'quality': { 'weight' : 0, **{'c'+str(i): None  for i in range(6,10)} },
                'valid' : True
                })
        #print("Lenb", brackets[0]['quality'])
        return brackets                    


    def filter_valid(self, brackets):
        best = min([grp['psd'] for grp in brackets]) 
        brackets = list(filter(lambda grp: grp['valid'], brackets))
        return(brackets)            



    def filter_c7(self, seq):
        best = min([grp['psd'] for grp in seq]) 
        if self.verbose > 1:
            print("filter_c7", len(seq), "Min psd:", best)            
        self.c8 = best
        seq = list(filter(lambda grp: grp['psd'] == best, seq))
        if self.verbose > 1:
            print("filter_c7 returns ", len(seq), "Min psd:", best)            
        
        return(seq)            

    def filter_c8(self, seq, remaining):
        if len(seq) <= 1 or len(remaining) == 0:
            return(seq)
        if self.verbose > 1:
            print("filter_c8", len(seq))
        remaining =  sorted(remaining, key=lambda s: (-s['acc'], s['cid']))
        for bracket in seq:
            mdp = bracket['downfloaters'] + bracket['limbo']
            scorebracket = remaining[0]['acc']
            resident =  list(filter(lambda competitor: competitor['acc'] == scorebracket , remaining))
            sub_brackets = self.enum_brackets(scorebracket, mdp, resident, remaining[len(resident):], False) 
            best_brackets = self.filter_c7(sub_brackets)[0]
            #down = best_brackets['downfloaters'] + best_brackets['limbo']
            bracket['quality']['c8'] = best_brackets['psd'] 
            #bracket['quality']['c8'] = sorted([c['scorelevel'] for c in down ], reverse=True )
        sub_brackets =  sorted(seq, key=lambda c: c['quality']['c8'])
        bestpsd = sub_brackets[0]['quality']['c8']
        seq = list(filter(lambda grp: grp['quality']['c8'] == bestpsd, sub_brackets)) 
        return seq

        

    def filter_c9(self, scorebracket, seq, lenremaining):
        if scorebracket > self.pab:
            return(seq)
        if len(seq) == 1 or (lenremaining != 1 and len(seq[0]['downfloaters'])+ len(seq[0]['limbo']) > 1):
            return seq  # We are not in the lowest scorebracket with multiple candidates or only one candidate
        maxlen = 0
        for grp in seq:
            down = grp['downfloaters'] + grp['limbo']
            maxlen = max(maxlen, down[0]['num'])
        seq = list(filter(lambda grp: (grp['downfloaters'] + grp['limbo'])[0]['num'] == maxlen, seq))
        c9 = self.rnd - maxlen - 1
        for grp in seq:
            grp['quality']['c9'] = c9
        return(seq)            
        
    def count_downfloats(self, seq):
        size = len(self.cmps.keys()) + 1
        downfloaters = [0]*size
        groups = len(seq)
        for grp in seq:
            for player in grp['downfloaters']:
                downfloaters[player['cid']] += 1                
        for i in range(size):
            if downfloaters[i] == groups:
                downfloaters[i] = -groups
        return downfloaters

    
   
  
    """
    find_pairs - Build bracket from current pairing
    
    """
    



    def find_pairing_w(self, scorebracket, mdp, resident, remaining):
        if self.verbose > 1:
            print('Scorebracket = ',  scorebracket)
            print('Mdp        = ', [c['cid'] for c in mdp])
            print('Resident   = ', [c['cid'] for c in resident])
            if self.verbose > 2:
                print('Remaining  = ', [c['cid'] for c in remaining])
        scorelevel = self.crosstable.scorelevels[scorebracket]
        self.update_bsn(mdp + resident, 'bsn-' + str(scorelevel))

        self.crosstable.update_crosstable(scorebracket, mdp, resident, remaining)
        brackets = self.enum_brackets(scorebracket, mdp, resident, remaining, self.checkonly)
        allseqlen = len(brackets)
        if not self.checkonly:
            brackets = self.filter_valid(brackets)                # Valid
        validlen = len(brackets)
        if self.verbose > 1:
            print('Scorebracket = ',  scorebracket, allseqlen, validlen, len(brackets[0]['competitors']), len(brackets[0]['downfloaters']) )
            print('Valid = ',  validlen)
        brackets = self.filter_c7(brackets)                       # C7
        if self.verbose > 1:
            print('filter_c7 = ',  len(brackets))
        
        brackets = self.filter_c8(brackets, remaining)            # C8
        if self.verbose > 1:
            print('filter_c8 = ',  len(brackets))
            for b in brackets:
                print('Comp/down', sorted([c['cid'] for c in b['competitors']]), sorted([c['cid'] for c in b['downfloaters']]), sorted([c['cid'] for c in b['limbo']]))
        brackets = self.filter_c9(scorebracket, brackets, len(remaining))       # C9
        if self.verbose > 1:
            print('filter_c9 = ',  len(brackets))
        # self.filter_downfloats(brackets, mdp, scorebracket)
        downfloatcount = self.count_downfloats(brackets)
        
        tbracket = brackets[0].copy()
        tbracket['pairs'] = []
        tbracket['nextb'] = []
        tbracket['quality'] = { 'weight': 0, **{'c'+str(i): None  for i in range(6,10)}}
        
        bestbracket = None
        self.pair_weighted(tbracket, len(mdp), downfloatcount, False)
        
    
        down = sorted([c['ca'] for c in tbracket['nextb']]) #sorted([list(x)[1] for x in bracket if list(x)[0] == -1])
        for bracket in brackets:
            df = sorted([c['cid'] for c in bracket['downfloaters']])
            if down == df:
                if self.verbose > 1:
                    print("Simple")
                for elem in ['pairs', 'nextb', 'quality']:
                    bracket[elem] = tbracket[elem]
                bestbracket = bracket
                break
        if bestbracket == None:    
            if self.verbose > 1:
                print("Complex", len(brackets),"of", allseqlen)
            for bracket in brackets:
                self.pair_weighted(bracket, len(mdp), downfloatcount, True)
                if self.verbose > 1:
                    print('weight', bracket['quality']['weight'])
            if self.verbose > 1:
                print('Brackets: ', len(brackets))
            for bracket in brackets:
                #bracket['competitors'] = bracket['grp']['competitors']
                #bracket['downfloaters'] = sorted(bracket['grp']['downfloaters'], key=lambda c:  c['cid'])
                #self.analyze_bracket(bracket, mdp)
                bestbracket = bracket if self.compare_brackets(bracket, bestbracket) < 0 else bestbracket             
        if bestbracket:
            down = bestbracket['downfloaters'] + bestbracket['limbo']
            bestbracket['quality']['c6'] = len(down)
            bestbracket['quality']['c7'] = sorted([c['scorelevel'] for c in down], reverse=True) if len(down) else None
            #print(bestbracket['quality']['c7'] )
        if self.verbose and bestbracket:
            line = "best: "
            for key, val in  bestbracket.items():
                if key[0] == 'c' and (key[1] == '1' or key[1] == '2') or key[0] == 'e' or key[0] == 'h':
                    line += " " + key + ':' + str(val)
            if self.verbose >1:
                print(line)
            print('Pairs:')
            for c in bestbracket['pairs']:
                w = c['w']
                b = c['b']
                bsn = 'bsn-' + str(scorelevel)
                print('    ', w, '-', b, '  =>  ', 
                      min(self.crosstable.crosstable[w][bsn], 
                          self.crosstable.crosstable[b][bsn]), 
                      max(self.crosstable.crosstable[w][bsn], 
                          self.crosstable.crosstable[b][bsn]))
                #print('    ', c['w'], '-', c['b'])
            print('Down:  ', [c['cid'] for c in bestbracket['downfloaters']])
            print('Limbo: ', [c['cid'] for c in bestbracket['limbo']])
            if self.verbose > 1:
                for key, value in bracket['quality'].items():
                    print(key, value)
        self.roundpairing.append(bestbracket)    
        return  bestbracket


            
    def update_bsn(self, competitors, name):
        competitors = sorted(competitors, key=lambda c: (-c['acc'], c['cid']))
        lastcid = -1
        bsn = 0
        for i in range(len(competitors)):
            if competitors[i]['cid'] != lastcid:
                lastcid = competitors[i]['cid']
                bsn = bsn + 1
            competitors[i][name] = bsn
            # print(name, competitors[i]['cid'], "=", bsn )
        return bsn

    def add_pair(self, bracket, wpair, addnext):
        (a, b) = wpair

        appended = False
        if a>=0 and b>=0:
            c = self.crosstable.crosstable[a]['opp'][b]
            if addnext or c['psd'] != 0:
                bracket['pairs'].append(c)
                appended = True
                if self.verbose > 2:
                    (wh, bl) = wpair
                    print('E' if c['psd'] else 'O', wpair, self.crosstable.crosstable[wh]['rsn'] if wh > 0 and addnext else 0, self.crosstable.crosstable[bl]['rsn'] if bl > 0 and addnext else 0  )
        else:
            d = max(a,b)
            c = self.crosstable.crosstable[d]['opp'][0]
            if addnext:
                bracket['nextb'].append(c) 
                appended = True
                if self.verbose > 2:
                    (wh, bl) = wpair
                    print('O', wpair, self.crosstable.crosstable[wh]['rsn'] if wh > 0 else 0, self.crosstable.crosstable[bl]['rsn'] if bl > 0 else 0  )
                    #print('D', c['ca'])
        if appended:
            pass
            """
            if self.verbose > 1:
                print(c)
            q = bracket['quality']
            q['weight'] += c['weight']
            for i in range(10, 22):
                cx = "c"+str(i)
                q[cx] = q[cx] + c[cx] if cx in q else c[cx]
            if self.crosstable.M > 0:
                if 'q1' not in q:
                    q['q1'] = [0]*self.crosstable.M
                if c['q1'] > 0:
                    q['q1'][c['q1']-1]  = c['q2']
            if self.crosstable.S > 0:
                for i in range(3, 5):
                    qx = "q"+str(i)
                    q[qx] = q[qx] + c[qx] if qx in q else c[qx]
                if 'q5' not in q:
                    q['q5'] = [0]*self.crosstable.B
                    q['q7'] = [0]*self.crosstable.O
                if c['q5'] > 0:
                    q['q5'][c['q5']-1] = c['q6']
                if c['q7'] > 0:
                    q['q7'][c['q7']-1] = c['q8']
            """
            
    def pair_weighted_hetrogenious(self, competitors, downfloaters, numcomp, numdown, scorebracket, bracket, downfloatcount):
        scorelevel = self.crosstable.scorelevels[scorebracket]
        G = nx.Graph()
        edges = []
        self.update_bsn(competitors + downfloaters, 'bsn')
        #for c in competitors + downfloaters:
        #    print("HETRO: ", c['cid'], c['bsn'] if 'bsn' in c else "?")
        #self.update_bsn(competitors + downfloaters if fullscan else competitors)
        allcompetitors =  competitors + downfloaters if competitors != downfloaters else competitors
        #self.update_bsn(allcompetitors, 'bsn')
        self.crosstable.update_hetrogenious(allcompetitors)
        
        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['bsn']
                scor = wcompetitor['scorelevel'] == scorelevel or bcompetitor['scorelevel'] == scorelevel
                                
                c = wcompetitor['opp'][bcid]
                if wcid < bcid and c['canmeet'] and scor: # and downfloatcount[wcid] >= 0 and downfloatcount[bcid] >= 0:
                    weight = self.crosstable.weight(c, 'E')
                    if self.verbose > 2:
                        #print("EAdd", weight, wcid, bcid, [ c['c' + str(i)] for i in range(10,22)], [c['q' + str(i)] for i in range(1,3)] )
                        print("EAdd", c['tweight'], wcid, bcid)
                    edges.append((wcid, bcid, weight))
        
        for wcompetitor in downfloaters:
            wcid = wcompetitor['cid']
            c = wcompetitor['opp'][0]
            if downfloatcount[wcid] != 0 or True:
                #print("DD E Numdown", numdown)
                for downfloat in range(numdown):
                    bcid = -1 - downfloat
                    weight = self.crosstable.weight(c, 'E')
                    if self.verbose > 2:
                        print("EAdd", c['tweight'], wcid, bcid)
                        #print("EAdd", weight, wcid, bcid, [ c['c' + str(i)] for i in range(10,22)], [c['q' + str(i)] for i in range(1,3)] )
                    edges.append((wcid, bcid, weight))

        if self.verbose > 2:
            for edge in edges:
                (w,b,ww) = edge
                print((str(w) if w>10 else ' ' + str(w)), (str(b) if b>10 else ' ' + str(b)), ww )                
        G.add_weighted_edges_from(edges)
        wpairs = sorted(nx.min_weight_matching(G))
        for wpair in wpairs:
            self.add_pair(bracket, wpair, False)
        #helpers.json_output('c:/temp/comp.txt', competitors)
        #sys.exit(0)


    def pair_weighted_homogenious(self, competitors, downfloaters, numcomp, numdown, scorebracket, bracket, downfloatcount):
        scorelevel = self.crosstable.scorelevels[scorebracket]
        G = nx.Graph()
        edges = []
        totallen = self.update_bsn(competitors + downfloaters, 'rsn')
        S = numcomp//2 - len(bracket['pairs'])
        #for c in competitors + downfloaters:
        #    print("HOMO:  ", S, c['cid'],  c['bsn'] if 'bsn' in c else "?", c['rsn'])
        r = numcomp//2
        n = r*2 + numdown


        self.crosstable.update_homogenious(competitors + downfloaters, S)
        #for c in bracket['pairs']:
        #    self.crosstable.weight(c, 'A')
        if self.verbose > 2:
            print("pair_weighted_homogenious comp", [c['cid'] for c in competitors])
        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['rsn']
                bbsn = bcompetitor['rsn']
                scor = wcompetitor['scorelevel'] == scorelevel or bcompetitor['scorelevel'] == scorelevel
                c = wcompetitor['opp'][bcid]
                if wcid < bcid and c['canmeet'] and scor: # and downfloatcount[wcid] >= 0 and downfloatcount[bcid] >= 0:
                    #weight = wcompetitor['opp'][bcid]['weight'] + wcompetitor['opp'][bcid]['hetrogenious'] + wcompetitor['opp'][bcid]['homogenious']
                    weight = self.crosstable.weight(c, 'S')
                    #wcompetitor['opp'][bcid]['tweight'] = weight
                    if self.verbose > 2:
                        print("OAdd", c['tweight'], wcid, bcid)
                        #print("OAdd", weight, wcid, bcid, [ c['c' + str(i)] for i in range(10,22)], [c['q' + str(i)] for i in range(3,9)] )
                        
                    edges.append((wcid, bcid, weight))
        
        if self.verbose > 2:
            print("pair_weighted_homogenious down", [c['cid'] for c in competitors])
        for wcompetitor in downfloaters:
            wcid = wcompetitor['cid']
            c = wcompetitor['opp'][0]
            if downfloatcount[wcid] != 0 or True:
                #print("DD O Numdown", numdown)
                for downfloat in range(numdown):
                    bcid = -1 - downfloat
                    #weight = wcompetitor['opp'][0]['weight'] + wcompetitor['opp'][0]['hetrogenious'] + wcompetitor['opp'][0]['homogenious']
                    weight = self.crosstable.weight(c, 'S')
                    if self.verbose > 2:
                        print("OAdd", c['tweight'], wcid, bcid)
                       #      print("OAdd", weight, wcid, bcid, [ c['c' + str(i)] for i in range(10,22)], [c['q' + str(i)] for i in range(3,9)] )
                    edges.append((wcid, bcid, weight))
                
        G.add_weighted_edges_from(edges)
        wpairs = nx.min_weight_matching(G)
        for wpair in wpairs:
            self.add_pair(bracket, wpair, True)
            
        
    def pair_weighted(self, bracket, mdpcount, downfloatcount, single):
        competitors = sorted(bracket['competitors'] if single else bracket['competitors'] + bracket['downfloaters']  + bracket['limbo'], key=lambda s: (-s['acc'], s['cid']))
        downfloaters = sorted(bracket['downfloaters'] + bracket['limbo'] if single else bracket['competitors']  + bracket['downfloaters'] + bracket['limbo'], key=lambda s: (-s['acc'], s['cid']))
        limbo = []
        numdown = len(bracket['downfloaters'])
        numcomp = len(bracket['competitors']) + len(bracket['downfloaters']) - numdown
        totallen = len(bracket['competitors']) + len(bracket['downfloaters']) + len(bracket['limbo'])
        scorebracket = bracket['scorebracket']
        # hetrogenious = len(competitors) > 0 and competitors[0]['acc'] > scorebracket 
        if self.verbose > 1:
            print("hetrogenious")
            print('scorebracket   = ',  scorebracket)
            print('Comp           = ', [c['cid'] for c in competitors])
            print('Down           = ', [c['cid'] for c in downfloaters])
            print('Numcomp        = ', numcomp)
            print('Numdown        = ', numdown)
            print('Hetrogenious   = ', mdpcount)

        # print("PSD", bracket['psd'])
        self.crosstable.init_weights(totallen, mdpcount, bracket['psd'])
        if mdpcount > 0:
            self.pair_weighted_hetrogenious(competitors, downfloaters, numcomp, numdown, scorebracket, bracket, downfloatcount)
            paired = []
            for c in bracket['pairs']:
                paired.append(c['w'])
                paired.append(c['b'])
            competitors = list(filter(lambda competitor: competitor['cid'] not in paired and competitor['acc'] == scorebracket , competitors))
            limbo = list(filter(lambda downfloat: downfloat['cid'] not in paired and downfloat['acc'] != scorebracket , downfloaters))
            downfloaters = list(filter(lambda downfloat: downfloat['cid'] not in paired and downfloat['acc'] == scorebracket , downfloaters))
            
            #if not fullscan:
            #    downfloaters = list(filter(lambda competitor: competitor['cid'] not in paired, downfloaters))
        if self.verbose > 1:
            print("Homogenious")
            print('Scorebracket = ',  scorebracket)
            print('Comp         = ', [c['cid'] for c in competitors])
            print('Down         = ', [c['cid'] for c in downfloaters])
            print('limbo        = ', [c['cid'] for c in limbo])
            print('Numcomp      = ', numcomp)
            print('Numdown      = ', numdown)
        #bracket['quality']['weight'] = self.crosstable.adjust_hetrogenious(competitors, numcomp, numdown, bracket['quality']['weight'])
        self.pair_weighted_homogenious(competitors, downfloaters, numcomp, numdown, scorebracket, bracket, downfloatcount)
        paired = []
        for c in bracket['pairs']:
            paired.append(c['w'])
            paired.append(c['b'])
        downfloaters = list(filter(lambda downfloat: downfloat['cid'] not in paired, downfloaters))
        if self.verbose > 1:
            print("Computeweight")
            print('Scorebracket = ',  scorebracket)
            print('Pairs        = ', [(c['w'],c['b'])  for c in bracket['pairs']])
            print('Down         = ', [c['cid'] for c in downfloaters])
            print('limbo        = ', [c['cid'] for c in limbo])
            print('Numcomp      = ', numcomp)
            print('Numdown      = ', numdown)
        bracket['quality'] = self.crosstable.compute_weight(bracket['pairs'], downfloaters + limbo, bracket['quality'])
        return False
        

    def compare_brackets(self, a, b):
        if b == None: 
            return -1
        return a['quality']['weight'] - b['quality']['weight']

