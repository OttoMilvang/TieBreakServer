# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 07:39:55 2025

@author: Otto
"""

import sys
import math
from decimal import *
import helpers
import qdefs


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

# Quality constants 
C6  = qdefs.C6
C7  = qdefs.C7
N8  = qdefs.N8
C8  = qdefs.C8
C9  = qdefs.C9
C10 = qdefs.C10
C11 = qdefs.C11
C12 = qdefs.C12
C13 = qdefs.C13
C14 = qdefs.C14
C15 = qdefs.C15
C16 = qdefs.C16
C17 = qdefs.C17
C18 = qdefs.C18
C19 = qdefs.C19
C20 = qdefs.C20
C21 = qdefs.C21
Q1  = qdefs.Q1
Q2  = qdefs.Q2
Q3  = qdefs.Q3
Q4  = qdefs.Q4
Q5  = qdefs.Q5
Q6  = qdefs.Q6
Q7  = qdefs.Q7
IW  = qdefs.IW
QL  = qdefs.QL

class crosstable:

    """
    init_crosstable / update crosstable
        Update competitors first from cmps[i]['tiebreakDetails']
        THe crosstable is an virtual crosstable of opp[] elements.
        A game between player a and b is described in the crosstable elsement self.cmps[a]['opp'][b] === self.cmps[b]['opp'][a]
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
    def __init__(self, rnd, experimental, checkonly, verbose):
        self.rnd = rnd
        self.verbose = verbose
        self.checkonly = checkonly
        self.experimental = {
            'XC6' : 'XC6' in experimental,
            'XC7' : 'XC7' in experimental,
            'XC8' : 'XC8' in experimental,
            'XC9' : 'XC9' in experimental,
            'XC14' : 'XC14' in experimental,
            'XC14M1' : 'XC14M1' in experimental,
            'XC16' : 'XC16' in experimental,
            'XC16M1' : 'XC16M1' in experimental,
            'XCTOPM1' : 'XTOPM1' in experimental,
            }
        self.scalars = [C6, N8, C9, C10, C11, C12, C13, C14, C15, C16, C17, Q3, Q4, IW]


    def list_edges(self, cmps, maxmeet, topcolor, unpaired):
        self.cmps = cmps
        self.maxmeet = maxmeet
        self.size = len(cmps.keys()) + 1
        self.topcolor = topcolor
        self.ilen = 0
        self.score2level = None
        self.level2score = None
        checkonly = self.checkonly
        
        
        edges = []
        cmps = self.cmps
        size = self.size
        cr = self.crosstable = [None]*size
        self.numtop = 0
        for i in range(size):
            tbval = cmps[i]['tiebreakDetails'] if i in cmps else None
            cr[i] = {
               'cid': i,
               'pts': tbval[PTS]['val'] if tbval else Decimal('0.0'),
               'acc': tbval[ACC]['val'] if tbval else Decimal('-1.0'),
               'rfp': tbval[RFP]['val'] != '' if tbval and i not in unpaired else False,
               'pop': int(tbval[RFP]['val'][0:-1]) if tbval and len(tbval[RFP]['val'])> 1 else -1,
               'pco': tbval[RFP]['val'][-1:] if tbval and len(tbval[RFP]['val'])> 1 else "",
               'hst': tbval[RFP] if tbval else {},
               'num': tbval[NUM]['val'] if tbval else 0,
               'rip': tbval[RIP]['val'] if tbval else 0,
               'met': tbval[NUM] if tbval else {},
               'cod': tbval[COD]['val'] if tbval else 0,
               'cop': tbval[COP]['val'] if tbval else '  ',
               'csq': ' ' + tbval[CSQ]['val'] if tbval else ' ',
               'flt': tbval[FLT]['val'] if tbval else 0,
               'top' : tbval[TOP]['val'] if tbval else False,
               'mdp' : 0,
               'lmb' : -1,
               'opp': [None] * size,
                }
                
            cr[0]['rfp'] ^= cr[i]['rfp']
        self.level2score = acc = sorted(set([c['acc'] for c in cr if c['rfp'] or c['cid'] == 0]) )
        self.score2level = score2level = { acc[i] : i for i in range(len(acc)) } 

        # update tpn, give tps to players that have been paired at least once. 
        tpn = 0
        cr[0]['scorelevel'] = 0
        for i in range(1, size):
            cr[i]['scorelevel'] = score2level[cr[i]['acc']] if cr[i]['rfp'] else 0
            if cr[i]['rfp'] or cr[i]['rip']:
                tpn += 1
                cr[i]['tpn'] = tpn
            
        # Invariant c['ca'] < c['cb'] 
 
        for i in range(size):
            b = cr[i]
            for j in range(i+1):
                a = cr[j]
                c = a['opp'][i] = b['opp'][j] = {} 
                edges.append(c)
                c['ca'] = j
                c['cb'] = i
                c['sa'] = a['scorelevel']
                c['sb'] = b['scorelevel']

                # C1 and C2 meetmax = 1
                c['canmeet'] = i != j and a['rfp'] and b['rfp'] 
                c['played'] = 0
                # c['quality'] = [0 if elem in self.scalars else [] for elem in range(QL)]
                c['quality'] = [None]*QL
             
                
                # C3 nottopscorers with absolute color preference cannot meet
                for col in ['w', 'b']:
                    col2 = col + '2'
                    if a['cop'] == col2 and b['cop'] == col2 and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                    if a['cod'] * b['cod'] >= 4  and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                c['psd'] = abs(a['scorelevel'] -b['scorelevel'])
               
                
                
            for key, val in b['met'].items():
                if key != 'val' and val < i:
                    b['opp'][val]['played'] += 1
                    b['opp'][val]['canmeet'] = b['opp'][val]['canmeet'] and cr[i]['opp'][val]['played'] < self.maxmeet
                    #print('canmeet', i, val, a['opp'][val]['canmeet'])
        if checkonly:
            for i in range(size):
                a = cr[i]
                for j in range(size):
                    b = cr[j]
                    c = a['opp'][j]
                    if a['pop'] == j: 
                        c['canmeet'] = True
                        if a['pco'] == 'w' or b['pco'] == 'w':
                            c[a['pco']] = i
                            c[b['pco']] = j
                        # print(i, j, c['canmeet'], c['w'] if 'w' in c else '?', c['b'] if 'b' in c else '?' )
                    else:
                        c['canmeet'] = False
                
        return list(filter(lambda edge: edge['canmeet'], edges))
        
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

            
    def update_crosstable(self, scorelevel, nodes, edges, pab):
        experimental =  self.experimental
        # print ("CheckAnlyse --", scorelevel, pab)
        self.maxpsd = maxpsd = max([node['scorelevel'] for node in nodes])-scorelevel
        for node in nodes:
            node['mdp'] = node['scorelevel'] - scorelevel
        # print("Update scorelevel", scorelevel, "maxpsd", maxpsd)        
        for c in [c for c in edges if c['canmeet']]:
            a = ca = self.crosstable[c['ca']]
            b = cb = self.crosstable[c['cb']]
            if a['scorelevel'] < b['scorelevel']:
                (a, b) = (b,a)
            q = c['quality']
            q[C6] = 0 
            q[C7] = [0]*(maxpsd)
            q[N8] = 0
            q[C8] = [0]*(maxpsd+1)
            q[C9] = 0
            for elem in range(C9,C18):
                q[elem] = 0
            for elem in range(C18,C21+1):
                q[elem] = [0]*maxpsd 

            level =  a['scorelevel']-scorelevel

            if a['scorelevel'] >= scorelevel and b['scorelevel'] == scorelevel:
                # print(scorelevel, c['ca'], c['cb'], c['canmeet'], a['cid'] == 0, 'w' in c, a['mdp'],  b['mdp'])
                pair = self.color_allocation(a, b, c)
                if self.checkonly:
                    if not 'b' in c:
                        c['b'] = 0
                    (c['e-rule'], c['e-ok']) = (pair['e-rule'], c['w'] == pair['w'] and (c['b'] ==  pair['b']))
                else:
                    (c['w'], c['b'], c['e-rule'], c['e-ok']) = (pair['w'], pair['b'], pair['e-rule'], True)

                if pab and b['scorelevel'] == 0:
                    q[C9] = self.rnd -1 - a['num']
                    
                # Topscorere


                if (a['top'] or b['top']) and a['cid'] > 0 and b['cid'] > 0:

                    #c10 minimize the number of topscorers who get color diff > +2 or < -2
                    # print(c, a['cod'], b['cod'])
                    apf = a['cod'] + 1 if a['cid'] == c['w'] else a['cod'] - 1
                    bpf = b['cod'] + 1 if b['cid'] == c['w'] else b['cod'] - 1
                    # q[C10] = 1 if abs(apf) > 2 and abs(bpf) >= 2 or abs(apf) >= 2 and abs(bpf) > 2 else 0 

                    q[C10] = 1 if abs(apf) > 2 or abs(bpf) > 2 else 0 
                    
                    #c11 minimize the number of topscorers who get same color three times in a row
                    asq = a['csq'][-2:] + ('w' if a['cid'] == c['w'] else 'b')
                    bsq = b['csq'][-2:] + ('w' if b['cid'] == c['w'] else 'b')
                    q[C11] = 1 if asq == 'www' or bsq == 'www' or asq == 'bbb' or bsq == 'bbb' else 0 
                    # print(a['cid'], b['cid'], q[C11], asq, a['csq'][-2:], bsq, b['csq'][-2:])

                    
                #c12 minimize the number of players who do not get their color preference
                q[C12] = 1 if a['cop'] != '  ' and a['cop'][0].lower() ==  b['cop'][0].lower() else 0
                   
                #c13 minimize the number of players who do not get their strong color preference
                q[C13] = 1 if q[C12] == 1 and int(a['cop'][1]) > 0 and int(b['cop'][1]) > 0 else 0

                #c14 minimize the number of players who receive downfloat in the previous round
                c14 =  1 if (b['cid'] == 0) and (a['flt'] & DF1) else 0
                #print('Scorelevel', c14, scorelevel, a['scorelevel'], b['scorelevel'])
                q[C14] = c14 if scorelevel == b['scorelevel'] else 0


                #c15 minimize the number of players who receive upfloft in the previous round
                c15 = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF1) or (a['acc'] > b['acc']) and (b['flt'] & UF1)  else 0
                q[C15] = c15

                #c16 minimize the number of players who receive downfloat two rounds before
                c16 = 1 if (b['cid'] == 0) and (a['flt'] & DF2) else 0
                q[C16] = c16 if scorelevel == b['scorelevel'] else 0

                #c17 minimize the number of players who receive upfloft two rounds before
                c17 = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF2) or (a['acc'] > b['acc']) and (b['flt'] & UF2)  else 0
                q[C17] = c17

                #c18 minimize the score difference of players who receive downfloat in the previous round
                c18 = level if c14  else 0
                q[C18] = [1 if c18 == maxpsd-i else 0 for i in range(maxpsd)]
                #print('c18', c14, c18, c['psd'], level, q[C18])

                #c19 minimize the score difference of players who receive upfloft in the previous round
                c19 = level if c15  else 0
                q[C19] = [1 if c19 == maxpsd-i else 0 for i in range(maxpsd)]
                
                #c20 minimize the score difference of players who receive downfloat two rounds before
                c20 = level if c16  else 0
                q[C20] = [1 if c20 == maxpsd-i else 0 for i in range(maxpsd)]

                #c21 minimize the score difference of players who receive upfloft two rounds before
                c21 = level if c17  else 0
                q[C21] = [1 if c21 == maxpsd-i else 0 for i in range(maxpsd)]

            elif a['scorelevel'] >= scorelevel and b['scorelevel'] < scorelevel:
                q[C6] = 1          
                # print("N6", scorelevel, a['cid'], b['cid'], a['scorelevel'], b['scorelevel'], "            ", a['scorelevel'] >= scorelevel and b['scorelevel'] < scorelevel)
                #print("Level", level, maxpsd, maxpsd - level, scorelevel, a['scorelevel'], b['scorelevel'])
                if level > 0:
                    q[C7] = [1 if level == maxpsd - i else 0 for i in range(maxpsd)]
                    #q[C7][maxpsd-level] = 1   

                if pab and b['scorelevel'] == 0:
                    q[C9] = self.rnd - 1 - a['num']

                #c14 minimize the number of players who receive downfloat in the previous round
                c14 =  1 if (a['flt'] & DF1) else 0
                q[C14] = c14 if a['scorelevel'] == scorelevel  else 0

                #c16 minimize the number of players who receive downfloat two rounds before
                c16 = 1 if a['flt'] & DF2 else 0
                q[C16] = c16 if a['scorelevel'] == scorelevel else 0

                #c18 minimize the score difference of players who receive downfloat in the previous round
                c18 = level if c14  else 0
                q[C18] = [1 if c18 == maxpsd-i else 0 for i in range(maxpsd)]
                
                #c20 minimize the score difference of players who receive downfloat two rounds before
                c20 = level if c16  else 0
                q[C20] = [1 if c20 == maxpsd-i else 0 for i in range(maxpsd)]

            
            scorelevel2 = scorelevel - 1
            #print("N8", scorelevel2, a['cid'], b['cid'], a['scorelevel'], b['scorelevel'], "            ", a['scorelevel'] >= scorelevel2 and b['scorelevel'] < scorelevel2)
            if a['scorelevel'] >= scorelevel2 and b['scorelevel'] < scorelevel2:
                q[N8] = 1          
                level =  max(a['scorelevel'], b['scorelevel']) -scorelevel2
                if level > 0:
                    q[C8] = [1 if level == maxpsd + 1 - i else 0 for i in range(maxpsd+1)]

                #if c['ca'] == 46 and c['cb'] == 47 or c['ca'] == 47 and c['cb'] == 46:
                #    print(a['cod'], a['cop'], "\n", b['cod'], b['cop'],  "\n", c)
                #    raise
            
        self.C = 3 # digits
        self.R = 2 # digits
        self.L = maxpsd



    def update_hetrogenious(self, scorelevel, edges, bsn):
        C = self.C
        R = self.R
        M = self.M
        P = self.P
        N = self.N

        self.ilen = 0
                
        #print("All hetro", [c['cid'] for c in competitors])
        for c in edges:
            (ca, cb) = (c['ca'], c['cb'])
            q = c['quality']
            q[Q1] = q[Q2] = [0]*M

            ascl = self.crosstable[ca]['scorelevel']
            bscl = self.crosstable[cb]['scorelevel']
            #print(self.crosstable[ca])
            if  ascl > scorelevel and bscl == scorelevel or ascl == scorelevel and bscl > scorelevel:
                absn = bsn[ca] 
                bbsn = bsn[cb]
                if absn > bbsn:
                    (absn, bbsn, ascl, bscl) = (bbsn, absn, bscl, ascl)
                q1 = absn if absn <= M else 0
                q2 = bbsn if absn <= M else 0
                # print("H", wcid, bcid, wbsn, bbsn, q[Q1], q[Q2], N)
                q[Q1] = [0 if q1 == i+1 else 1 for i in range(M)] 
                q[Q2] = [q2 if q1 == i+1 else 0 for i in range(M)] 



    def update_homogenious(self, scorelevel, edges, bsn, S):
        C = self.C
        R = self.R
        M = self.M
        P = self.P
        N = self.N
        #S = self.S
        B = self.B 
        self.ilen = 0
        # print ("BO:", B, S, self.S)
        
        # print("CheckAnlyse", scorelevel, "M="+str(M), "P="+str(P), "N="+str(N), "S="+str(S), "B="+str(B) )

        for c in edges:
            (ca, cb) = (c['ca'], c['cb'])
            q = c['quality']
            q[Q1] = [0]*M
            q[Q2] = [0]*M
            q[Q3] = 0
            q[Q4] = 0
            q[Q5] = [0]*B
            q[Q6] = [0]*B
            q[Q7] = [0]*B
            ascl = self.crosstable[ca]['scorelevel']
            bscl = self.crosstable[cb]['scorelevel']
            if  ascl == scorelevel and bscl == scorelevel:
                absn = bsn[ca] 
                bbsn = bsn[cb]
                if absn > bbsn:
                    (absn, bbsn, ascl, bscl) = (bbsn, absn, bscl, ascl)

                weight = 0
                if 'tweight' in c and ' S ' not in c['tweight']:
                    #print()
                    #print('www', c['tweight'])
                    # self.weight(c, 'A')
                    pass
                #print("Test ", wcid, )
                if c['canmeet']:
                    q[Q1] = q[Q2] = [0]*M
                    q[Q3] = 1 if absn > S else 0
                    q[Q4] = absn-1
                    q[Q5] = [1 if (absn <= S) and (S - absn == i) else 0  for i in range(B)] 
                    # q[Q6] = [1 if (absn > S) and (B - absn == i) else B for i in range(B)] 
                    q[Q6] = [0 if (absn > S) and (absn - S - 1 == i) else 1 for i in range(B)] 
                    q[Q7] = [bbsn if absn == i+1 else 0 for i in range(B)]  
                    c['homogenious'] = weight
            #c = wcompetitor['opp'][0]
            #q[Q1] = q[Q2] = [0]*M
            #q[Q3] = q[Q4] = 0
            #q[Q5] = q[Q6] = q[Q7] = [0]*B


            

    # Compute weight
    # mode 'E' - Hetrogenous 
    # mode 'S' - Homogenous 
    # mode 'A' - Add S-part


    def init_weights(self, scorelevel, nodes, psd):
        
        bracketnodes = [node for node in nodes if node['scorelevel'] >= scorelevel]
        mdp = [node for node in bracketnodes if node['scorelevel'] > scorelevel]

        C = self.C
        R = self.R
        N = self.N = len(bracketnodes) 
        M = self.M = len(mdp)
        P = self.P = 0 #int(max(psd) if len(psd) > 0 else 0)
        S = self.S = (N-len(psd))//2
        B = self.B = 2*S + len(psd)
        #print ("BI:", B)
 
        
        self.Eweight = (' E ' + str([str(v).zfill(R) for v in [0]*M]).replace("'","")
                        + '-' + str([str(v).zfill(R) for v in [0]*M]).replace("'","")  )
        self.Sweight = ( ' S ' + "0".zfill(R) 
                               + '-' + "0".zfill(R+R)
                               + '-' + str([str(v).zfill(C) for v in [0]*B]).replace("'","")
                               + '-' + str([str(v).zfill(C+C) for v in [0]*B]).replace("'","")
                               + '-' + str([str(v).zfill(C) for v in [0]*B]).replace("'","")  )
        

    def weight(self, c, mode):
        C = self.C
        R = self.R 
        M = self.M
        P = self.P
        N = self.N
        S = self.S
        B = self.B
        L = self.L
        #print ("BW:", B)

        q = c['quality']
        c['mode'] = mode
        cweight = eweight = sweight = ""
        
        if mode == 'E' or mode == 'S' or mode == 'T':
            cweight = "C 1"      # Always start with C
            cweight = cweight + '-' + str(q[C6]).zfill(R)
            cweight = cweight + '-' + str([str(v).zfill(R) for v in q[C7]]).replace("'","")
            cweight = cweight + '-' + str(q[N8]).zfill(R)
            cweight = cweight + '-' + str([str(v).zfill(R) for v in q[C8]]).replace("'","")
            cweight = cweight + '-' + str(q[C9]).zfill(R)
            cweight = cweight + '-' + str(q[C10]).zfill(R)
            cweight = cweight + '-' +  str(q[C11]).zfill(R)
            cweight = cweight + '-' +  str(q[C12]).zfill(C)
            cweight = cweight + '-' +  str(q[C13]).zfill(C)
            cweight = cweight + '-'
            cweight = cweight + '-' +  str(q[C14]).zfill(R)
            cweight = cweight + '-' +  str(q[C15]).zfill(R)
            cweight = cweight + '-' +  str(q[C16]).zfill(R)
            cweight = cweight + '-' +  str(q[C17]).zfill(R)
            cweight = cweight + '-'
            cweight = cweight + '-' +  str([str(v).zfill(R) for v in q[C18]]).replace("'","")
            cweight = cweight + '-' +  str([str(v).zfill(R) for v in q[C19]]).replace("'","")
            cweight = cweight + '-' +  str([str(v).zfill(R) for v in q[C20]]).replace("'","")
            cweight = cweight + '-' +  str([str(v).zfill(R) for v in q[C21]]).replace("'","")
        if M > 0 and (mode == 'E' or mode == 'T'):
            eweight = eweight + ' E '
            eweight = eweight       + str([str(v).zfill(R) for v in q[Q1]]).replace("'","")
            eweight = eweight + '-' + str([str(v).zfill(R) for v in q[Q2]]).replace("'","")
#        if M > 0 and mode == 'E':
#            weight = weight + self.Sweight 
#        if mode == 'S' or M == 0 and mode == 'T':
#            weight = weight + self.Eweight 
        if mode == 'S' or mode == 'T':
            sweight = sweight + ' S '
            sweight = sweight       + str(q[Q3]).zfill(R) 
            sweight = sweight + '-' + str(q[Q4]).zfill(R+R)
            sweight = sweight + '-' + str([str(v).zfill(C) for v in q[Q5]]).replace("'","")
            sweight = sweight + '-' + str([str(v).zfill(C+C) for v in q[Q6]]).replace("'","")
            sweight = sweight + '-' + str([str(v).zfill(C) for v in q[Q7]]).replace("'","")
        c['cweight'] = cweight
        c['eweight'] = eweight
        c['sweight'] = sweight
        c['tweight'] = tweight = cweight + eweight + sweight
        c['weight'] = iweight = int(''.join(c for c in tweight if c.isdigit()))
        ilen = self.ilen
        #print("WWW", c['ca'] if 'ca' in c else 0, c['cb'] if 'cb' in c else 0, ilen, weight)
        if ilen > 0 and len(tweight) != ilen:
            #print("Weight: ", len(tweight), ilen)
            #raise
            pass
        self.ilen = len(tweight)
        
        return iweight

    def compute_weight(self, wpairs, bquality):
        #C = self.C
        #R = self.R 
        M = self.M
        P = self.P
        #N = self.N
        #S = self.S
        B = self.B
        L = self.L

        quality = [None]*QL
        quality[N8] = 0
        
        
        
        weight = 0
        #down =  [d['opp'][0] for d in downfloaters]
        for c in  wpairs:
            #print(c['ca'], c['cb'], c['quality'][N8])
            q = c['quality']
            line = "C"
            for elem in range(QL):
                if elem < Q1 or (c['mode'] == 'E' and elem < Q3) or (c['mode'] == 'S' and elem >= Q3):
                    if q[elem] == None:
                        pass
                    elif quality[elem] == None:
                        quality[elem] = q[elem]
                    elif isinstance(quality[elem], int):
                        quality[elem] += q[elem]
                    else:
                        for i in range(len(quality[elem])):
                            #print(elem, i)
                            #print(quality)
                            #print(q)
                            quality[elem][i] += q[elem][i]

        #self.weight(quality, 'T')
        if False: # or quality['weight'] != quality['iweight'] and False:
            print(quality['tweight'])
            print(quality['weight'])
            print(quality['iweight'])
            print(quality)
            raise
        # elem != 'q6' and c[elem][i] != O 
        #quality[Q6] = [elem % B for elem in quality[Q6]] if quality[Q6] is not None else None
        #print("c8 cw", quality[Q6])
        return quality

    def compute_pab_weight(self, edges):
        for edge in edges:
            edge['iweight'] = edge['sb'] if edge['ca'] == 0 else 0


    def compute_weightx(self, bracket):
        weight = 0
        for c in bracket['pairs']:
            #print(c['weight'])
            weight += c['weight']
        for c in bracket['downfloaters']:
            #print(c['cid'], c['opp'][0]['weight'] if 'weight' in c['opp'][0] else 0)
            weight += c['opp'][0]['weight'] if 'weight' in c['opp'][0] else 0
        quality = {'weight': weight}
        return quality
    


                                       
    """
    color_allocation(a, b, c)
    Implement section E
    a - competitor a
    b - competitor b
    c - crosstable element
    
    
    """
        
    def color_allocation(self, a, b, c):
        other ={'w': 'b', 'b': 'w', ' ': ' ' }  
        (acid, bcid) = (a['cid'], b['cid'])
        (acp, acs) = list(a['cop'])
        (bcp, bcs) = list(b['cop'])
        acd = a['cod']
        bcd = b['cod']

        # PAB, always set player to white
        if acid == 0:
            return {"w": bcid, "b": acid, "e-rule": "pab" } # ('b', 'w', 'pab')
        if bcid == 0:
            return {"w": acid, "b": bcid, "e-rule": "pab" } # ('w', 'b', 'pab')

        # E.1
 
        if acp == 'w' and bcp !='w' or acp != 'b' and bcp =='b':
            return {"w": acid, "b": bcid, "e-rule": "E.1" } # ('w', 'b', 'E.1')
        if acp == 'b' and bcp !='b'  or acp != 'w' and bcp =='w':
            return {"w": bcid, "b": acid, "e-rule": "E.1" } # ('b', 'w', 'E.1')
        # E.2
        if (acp == 'w' and bcp == 'w' and acs > bcs) or (acp == 'b' and bcp == 'b' and acs < bcs):
            return {"w": acid, "b": bcid, "e-rule": "E.2" } # ('w', 'b', 'E.2')
        if (acp == 'b' and bcp == 'b' and acs > bcs) or (acp == 'w' and bcp == 'w' and acs < bcs):
            return {"w": bcid, "b": acid, "e-rule": "E.2" } # ('b', 'w', 'E.2')
        if acd != bcd and acs == bcs: # both have absolute color preference, se if there are different color difference
            return {"w": acid, "b": bcid, "e-rule": "E.2" } if acd < bcd else {"w": bcid, "b": acid, "e-rule": "E.2" } 
            # return ('w', 'b', 'E.2') if acd < bcd else ('b', 'w', 'E.2') 
        # E.3
        asq = a['csq']
        bsq = b['csq']
        for i in range (1, min(len(asq), len(bsq))):
            ac = asq[-i]
            bc = bsq[-i]
            if ac != bc:
                if ac == 'b' or bc == 'w':
                    return {"w": acid, "b": bcid, "e-rule": "E.3" } #('w', 'b', 'E.3')
                if ac == 'w' or bc == 'b':
                    return {"w": bcid, "b": acid, "e-rule": "E.3" } # ('b', 'w', 'E.3')
        # E.4
        (atpn, btpn) = (a['tpn'], b['tpn'])
        (highcid, hightpn) = (acid, atpn) if a['scorelevel'] > b['scorelevel'] or a['scorelevel'] == b['scorelevel'] and atpn < btpn else (bcid, btpn)
        lowcid = acid + bcid - highcid
        if acp == 'w' or acp == 'b':
            #print("E4", acp, min(acid, bcid), max(acid, bcid), {acp : min(acid, bcid), other[acp] : max(acid, bcid) , "e-rule": 'E.4'})
            return {acp : highcid, other[acp] : lowcid , "e-rule": 'E.4'}   # (acp, other[acp], 'E.4')
        #if a['tpn'] > b['tpn'] and (acp == 'w' or acp == 'b'):        
        #    return (other[acp], acp, 'E.4')
        # E.5
        tc = self.topcolor
        rev = hightpn % 2 == 0
        return {tc : (lowcid if rev else highcid), other[tc] : (highcid if rev else lowcid), "e-rule": 'E.5'}

        #same = (a['tpn'] < b['tpn']) ^ (min(a['tpn'], b['tpn']) % 2 == 0)
        #if same:
        #    return (self.topcolor, other[self.topcolor], 'E.5')
        #else:        
        #    return (other[self.topcolor], self.topcolor, 'E.5')
                              


                        
