# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 07:39:55 2025

@author: Otto
"""

import sys
import math
from decimal import *
import helpers


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

DF1 = 1
DF2 = 4 
UF1 = 2
UF2 = 8


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
    def __init__(self, cmps, maxmeet, topcolor, unpaired, experimental, checkonly, verbose):
        self.cmps = cmps
        self.maxmeet = maxmeet
        self.verbose = verbose
        self.size = len(cmps.keys()) + 1
        self.topcolor = topcolor
        self.ilen = 0
        self.scorelevels = None
        
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
               'opp': [None] * size,
                }
                
            cr[0]['rfp'] ^= cr[i]['rfp']

        acc = sorted(set([c['acc'] for c in cr if c['rfp'] or c['cid'] == 0]) )
        self.scorelevels = scorelevels = { acc[i] : i for i in range(len(acc)) } 

        # update tpn, give tps to players that have been paired at least once. 
        tpn = 0
        for i in range(size):
            cr[i]['scorelevel'] = scorelevels[cr[i]['acc']]
            if cr[i]['rfp'] or cr[i]['rip']:
                tpn += 1
                cr[i]['tpn'] = tpn
            
        for i in range(size):
            a = cr[i]
            for j in range(i+1):
                b = cr[j]
                c = a['opp'][j] = b['opp'][i] = {} 
                c['ca'] = i
                c['cb'] = j

                # C1 and C2 meetmax = 1
                c['canmeet'] = i != j and a['rfp'] and b['rfp'] 
                c['played'] = 0

                for ci in range(10,22):
                    c["c" + str(ci)] = 0 
                
                
                # C3 nottopscorers with absolute color preference cannot meet
                for col in ['w', 'b']:
                    col2 = col + '2'
                    if a['cop'] == col2 and b['cop'] == col2 and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                    if a['cod'] * b['cod'] >= 4  and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                c['psd'] = abs(a['scorelevel'] -b['scorelevel'])
               
                
                
            for key, val in a['met'].items():
                if key != 'val' and val < i:
                    a['opp'][val]['played'] += 1
                    a['opp'][val]['canmeet'] = a['opp'][val]['canmeet'] and cr[i]['opp'][val]['played'] < self.maxmeet
                    #print('canmeet', i, val, a['opp'][val]['canmeet'])

        if checkonly:
            for i in range(size):
                a = cr[i]
                for j in range(size):
                    c = a['opp'][j]
                    c['canmeet'] = a['pop'] == j
                    #print(i, j, c['canmeet'] )
                


            
    def update_crosstable(self, scorebracket, mdp, resident, remaining):
        scorelevel = self.scorelevels[scorebracket]
        experimental =  self.experimental
        #print ("CheckAnlyse --", scorelevel)
        self.maxpsd = maxpsd = max([c['scorelevel'] for c in mdp])-scorelevel if len(mdp ) > 0 else 0
        for c in mdp:
            c['mdp'] = c['scorelevel'] - scorelevel
        # print("Update scorelevel", scorelevel, "maxpsd", maxpsd)        
        for a in ([self.crosstable[0]] + resident):
            for b in mdp + resident:
                c = a['opp'][b['cid']]
                if (c['canmeet'] or a['cid'] == 0) and (a['cid'] < b['cid'] or b['mdp'] > 0) :
                    # print(scorelevel, c['ca'], c['cb'], c['canmeet'], a['cid'] == 0, 'w' in c, a['mdp'],  b['mdp'])
                    #self.maxpsd = max(self.maxpsd, c['psd'])
                    (acol, bcol) = self.color_allocation(a, b, c)
                    pair = {acol: a['cid'], bcol: b['cid'] }
                    c['w'] = pair['w']
                    c['b'] = pair['b']
                    # print(scorelevel, c['w'], "-", c['b'])
                    cxx = 0


                    # PSD
                    c['c7'] = [0]*(maxpsd)
                    if a['cid'] == 0:
                        level =  b['scorelevel']-scorelevel
                        if level > 0:
                            c['c7'][maxpsd-level] = 1   

                    # Topscorere

                    c['c10'] = c['c11']  = 0
                    if (a['top'] or b['top']) and a['cid'] > 0:

                        #c10 minimize the number of topscorers who get color diff > +2 or < -2
                        #print(c, a['cod'], b['cod'])
                        apf = a['cod'] + 1 if a['cid'] == c['w'] else a['cod'] - 1
                        bpf = b['cod'] + 1 if b['cid'] == c['w'] else b['cod'] - 1
                        # c['c10'] = 1 if abs(apf) > 2 and abs(bpf) >= 2 or abs(apf) >= 2 and abs(bpf) > 2 else 0 
                        c['c10'] = 1 if abs(apf) > 2 or abs(bpf) > 2 else 0 
                    
                        #c11 minimize the number of topscorers who get same color three times in a row
                        asq = a['csq'][-2:] + ('w' if a['cid'] == c['w'] else 'b')
                        bsq = b['csq'][-2:] + ('w' if b['cid'] == c['w'] else 'b')
                        c['c11'] = 1 if asq == 'www' or bsq == 'www' or asq == 'bbb' or bsq == 'bbb' else 0 
                        # print(a['cid'], b['cid'], c['c11'], asq, a['csq'][-2:], bsq, b['csq'][-2:])

                    
                    #c12 minimize the number of players who do not get their color preference
                    c['c12'] = 1 if a['cop'] != '  ' and a['cop'][0].lower() ==  b['cop'][0].lower() else 0
                    
                    #c13 minimize the number of players who do not get their strong color preference
                    c['c13'] = 1 if c['c12'] == 1 and int(a['cop'][1]) > 0 and int(b['cop'][1]) > 0 else 0

                    #c14 minimize the number of players who receive downfloat in the previous round
                    c14 =  1 if (a['cid'] == 0) and (b['flt'] & DF1) else 0
                    c['c14'] = c14 if scorelevel == b['scorelevel'] else 0


                    #c15 minimize the number of players who receive upfloft in the previous round
                    c15 = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF1) or (a['acc'] > b['acc']) and (b['flt'] & UF1)  else 0
                    c['c15'] = c15

                    #c16 minimize the number of players who receive downfloat two rounds before
                    c16 = 1 if (a['cid'] == 0) and (b['flt'] & DF2) else 0
                    c['c16'] = c16 if scorelevel == b['scorelevel'] else 0

                    #c17 minimize the number of players who receive upfloft two rounds before
                    c17 = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF2) or (a['acc'] > b['acc']) and (b['flt'] & UF2)  else 0
                    c['c17'] = c17

                    #c18 minimize the score difference of players who receive downfloat in the previous round
                    c18 = level if c14  else 0
                    c['c18'] = [1 if c18 == maxpsd-i else 0 for i in range(maxpsd)]
                    #print('c18', c14, c18, c['psd'], level, c['c18'])

                    #c19 minimize the score difference of players who receive upfloft in the previous round
                    c19 = c['psd'] if c15  else 0
                    c['c19'] = [1 if c19 == maxpsd-i else 0 for i in range(maxpsd)]
                
                    #c20 minimize the score difference of players who receive downfloat two rounds before
                    c20 = level if c16  else 0
                    c['c20'] = [1 if c20 == maxpsd-i else 0 for i in range(maxpsd)]

                    #c21 minimize the score difference of players who receive upfloft two rounds before
                    c21 = c['psd'] if c17  else 0
                    c['c21'] = [1 if c21 == maxpsd-i else 0 for i in range(maxpsd)]

                    
                    c['q1'] = c['q2'] = c['q5'] = c['q6'] = c['q7'] = []
                    c['q3'] = c['q4'] = 0

                    #if c['ca'] == 46 and c['cb'] == 47 or c['ca'] == 47 and c['cb'] == 46:
                    #    print(a['cod'], a['cop'], "\n", b['cod'], b['cop'],  "\n", c)
                    #    raise
                        
        self.C = 3 # digits
        self.R = 2 # digits
        self.L = maxpsd



    def update_hetrogenious(self, competitors):
        C = self.C
        R = self.R
        M = self.M
        P = self.P
        N = self.N

        self.ilen = 0
                
        # print("All hetro", [c['cid'] for c in competitors])
        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['bsn'] 
                bbsn = bcompetitor['bsn']
                c = wcompetitor['opp'][bcid]
                if wbsn < bbsn and wcompetitor['opp'][bcid]['canmeet']:
                    q1 = wbsn if wbsn <= M else 0
                    q2 = bbsn if wbsn <= M else 0
                    # print("H", wcid, bcid, wbsn, bbsn, c['q1'], c['q2'], N)
                    c['q1'] = [0 if q1 == i+1 else 1 for i in range(M)] 
                    c['q2'] = [q2 if q1 == i+1 else 0 for i in range(M)] 
            c = wcompetitor['opp'][0]
            # print(c['ca'], c['cb'])
            c['q1'] = [0]*M
            c['q2'] = [0]*M



    def update_homogenious(self, competitors, S):
        C = self.C
        R = self.R
        M = self.M
        P = self.P
        N = self.N
        #S = self.S
        B = self.B 
        self.ilen = 0
        
        # print("CheckAnlyse", "M="+str(M), "P="+str(P), "N="+str(N), "S="+str(S), "B="+str(B) )

        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['rsn']
                bbsn = bcompetitor['rsn']
                weight = 0
                c = wcompetitor['opp'][bcid]
                if 'tweight' in c and ' S ' not in c['tweight']:
                    #print()
                    #print('www', c['tweight'])
                    # self.weight(c, 'A')
                    pass
                #print("Test ", wcid, )
                if wcid < bcid and wcompetitor['opp'][bcid]['canmeet']:
                    c['q1'] = c['q2'] = [0]*M
                    c['q3'] = 1 if wbsn > S else 0
                    c['q4'] = wbsn-1
                    c['q5'] = [1 if (wbsn <= S) and (S - wbsn == i) else 0  for i in range(B)] 
                    c['q6'] = [1 if (wbsn > S) and (B - wbsn -1 == i) else B for i in range(B)] 
                    c['q7'] = [bbsn if wbsn == i+1 else 0 for i in range(B)]  
                    # c['ho4'] = ho4 = [(-N+bbsn-1 if wbsn == i+1  else 0) for i in range(M)]
                    #weight = weight * R + (1 if wcid > r else 0)
                    #weight = weight * R*R + (wbsn-1)
                    #weight = weight * 10**n + (10**(n-wbsn) if wbsn <= r else 0)
                    ##weight = weight * 10**n + (10**(wbsn-1) if wbsn > r else 0)
                    #weight = weight * 10**(3*n) + 10*(n-wbsn)*(bbsn-1)
                    # print(weight)
                    wcompetitor['opp'][bcid]['homogenious'] = weight
            c = wcompetitor['opp'][0]
            c['q1'] = c['q2'] = [0]*M
            c['q3'] = c['q4'] = 0
            c['q5'] = c['q6'] = c['q7'] = [0]*B


            

    # Compute weight
    # mode 'E' - Hetrogenous 
    # mode 'S' - Homogenous 
    # mode 'A' - Add S-part


    def init_weights(self, total, nummdp, psd):
        C = self.C
        R = self.R
        N = self.N = total 
        M = self.M = nummdp
        P = self.P = int(max(psd) if len(psd) > 0 else 0)
        S = self.S = (N-len(psd))//2
        B = self.B = 2*S + len(psd)
        
        
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
        
        weight = ""
        if mode == 'D'  or mode == 'E' or mode == 'S' or mode == 'T':
            weight = "C 1"      # Always start with C
            weight = weight + '-' + str([str(v).zfill(R) for v in c['c7']]).replace("'","")
            weight = weight + '-' + str(c['c10']).zfill(R)
            weight = weight + '-' +  str(c['c11']).zfill(R)
            weight = weight + '-' +  str(c['c12']).zfill(C)
            weight = weight + '-' +  str(c['c13']).zfill(C)
            weight = weight + '-'
            weight = weight + '-' +  str(c['c14']).zfill(R)
            weight = weight + '-' +  str(c['c15']).zfill(R)
            weight = weight + '-' +  str(c['c16']).zfill(R)
            weight = weight + '-' +  str(c['c17']).zfill(R)
            weight = weight + '-'
            weight = weight + '-' +  str([str(v).zfill(R) for v in c['c18']]).replace("'","")
            weight = weight + '-' +  str([str(v).zfill(R) for v in c['c19']]).replace("'","")
            weight = weight + '-' +  str([str(v).zfill(R) for v in c['c20']]).replace("'","")
            weight = weight + '-' +  str([str(v).zfill(R) for v in c['c21']]).replace("'","")
        if M > 0 and (mode == 'E' or mode == 'T'):
            weight = weight + ' E '
            weight = weight       + str([str(v).zfill(R) for v in c['q1']]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(R) for v in c['q2']]).replace("'","")
        if M > 0 and mode == 'E':
            weight = weight + self.Sweight 
        if mode == 'S' or M == 0 and mode == 'T':
            weight = weight + self.Eweight 
        if mode == 'S' or mode == 'T':
            weight = weight + ' S '
            weight = weight       + str(c['q3']).zfill(R) 
            weight = weight + '-' + str(c['q4']).zfill(R+R)
            weight = weight + '-' + str([str(v).zfill(C) for v in c['q5']]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(C+C) for v in c['q6']]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(C) for v in c['q7']]).replace("'","")
        if mode == 'A':
            raise
            weight = c['tweight']
            if ' E ' not in weight:
                weight += self.Eweight
            if ' S ' not in weight:
                weight += self.Sweight
               
        c['tweight'] = weight
        c['weight'] = iweight = int(''.join(c for c in weight if c.isdigit()))
        ilen = self.ilen
        #print("WWW", c['ca'] if 'ca' in c else 0, c['cb'] if 'cb' in c else 0, ilen, weight)
        if ilen > 0 and len(weight) != ilen:
            print(len(weight), ilen)
            raise
        self.ilen = len(weight)
        
        return iweight

    def compute_weight(self, pairs, downfloaters, bquality):
        #C = self.C
        #R = self.R 
        M = self.M
        P = self.P
        #N = self.N
        #S = self.S
        B = self.B
        L = self.L

        quality = {
            'weight': 0,
            **{ 'c'+str(i): ([0]*L if i == 7 else bquality['c'+str(i)]) for i in range(6, 10)},
            #**{ 'c'+str(i): bracket['quality']['c'+str(i)] for i in range(6, 10)},
            **{ 'c'+str(i): ([0]*L if i == 7 or i >= 18 else 0) for i in range(10, 22)},
            'q1': [0]*M, 'q2': [0]*M,
            **{ 'q'+str(i): ([0]*B if i >= 5 else 0)  for i in range(3, 8) },
        }
        # print("computeWeight", bracket['scorebracket'], "c6", bracket['quality']['c6'], quality['c6'] )
        
        
        weight = 0
        down =  [d['opp'][0] for d in downfloaters]
        for c in  pairs  +  down:
            line = "C"
            #for elem in ['ca', 'cb', 'c7',  'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c19', 'c20', 'c21', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7']:
            #    line += " " + str(c[elem]) if elem in c else '--'
            #print(line)
            for elem in ['weight', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'q3', 'q4']:
                quality[elem] += c[elem]  if elem in c else 0
            for elem in ['c7', 'c18', 'c19', 'c20', 'c21', 'q1', 'q2', 'q5', 'q6', 'q7']:
                # print(elem, quality[elem], c[elem])
                for i in range(min(len(quality[elem]), len(c[elem]))):
                    quality[elem][i] += c[elem][i]  if elem in c else 0
                    # print(elem, i, c[elem][i], quality[elem][i] )

        #for d in []:
        #    c = c['opp'][0]
        ##    line = "C " + str(c['cid'])  + " "
        #    for elem in ['ca', 'cb', 'c7',  'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c19', 'c20', 'c21', 'q12', 'q3', 'q4', 'q5', 'q6', 'q7']:
        #        line += " " + (str(c['opp'][0][elem]) if elem in c['opp'][0] else '--')
        #    print(line)
        #    for elem in ['weight', 'c14', 'c16']:
        #        quality[elem] +=  c[elem] if elem in c else 0
        #    for elem in ['c7', 'c18', 'c20']:
        #        for i in range(min(len(quality[elem]),len(c['opp'][0][elem]))):
        #            quality[elem][i] += c['opp'][0][elem][i] if elem in c['opp'][0] else 0
        quality['c6'] = len(downfloaters)
        quality['iweight'] = quality['weight']
        self.weight(quality, 'T')
        if quality['weight'] != quality['iweight'] and False:
            print(quality['tweight'])
            print(quality['weight'])
            print(quality['iweight'])
            print(quality)
            raise
        # elem != 'q6' and c[elem][i] != O 
        quality['q6'] = [elem % B for elem in quality['q6']] 
        #print("c8 cw", quality['c8'])
        return quality


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
        (acp, acs) = list(a['cop'])
        (bcp, bcs) = list(b['cop'])
        acd = a['cod']
        bcd = b['cod']

        # PAB, always set player to white
        if c['ca'] == 0:
            return ('w', 'b')
        if c['cb'] == 0:
            return ('b', 'w')

        # E.1
        if acp == 'w' and bcp !='w':
            return ('w', 'b')
        if acp == 'b' and bcp !='b':
            return ('b', 'w')
        # E.2
        if (acp == 'w' and bcp == 'w' and acs > bcs) or (acp == 'b' and bcp == 'b' and acs < bcs):
            return('w', 'b')
        if (acp == 'b' and bcp == 'b' and acs > bcs) or (acp == 'w' and bcp == 'w' and acs < bcs):
            return ('b', 'w')
        if acd != bcd and acs == bcs: # both have absolute color preference, se if there are different color difference
            return ('w', 'b') if acd < bcd else ('b', 'w') 
        # E.3
        asq = a['csq']
        bsq = b['csq']
        for i in range (1, min(len(asq), len(bsq))):
            ac = asq[-i]
            bc = bsq[-i]
            if ac != bc:
                if ac == 'b' or bc == 'w':
                    return ('w', 'b')
                if ac == 'w' or bc == 'b':
                    return ('b', 'w')
        # E.4
        if a['tpn'] < b['tpn'] and (acp == 'w' or acp == 'b'):    
            return (acp, other[acp])
        if a['tpn'] > b['tpn'] and (acp == 'w' or acp == 'b'):        
            return (bcp, other[bcp])
        # E.5
        same = (a['tpn'] < b['tpn']) ^ (min(a['tpn'], b['tpn']) % 2 == 0)
        if same:
            return (self.topcolor, other[self.topcolor])
        else:        
            return (other[self.topcolor], self.topcolor)
                              


                        
