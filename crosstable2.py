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

        
    """


    # constructor function    
    def __init__(self, cmps, maxmeet, topcolor, unpaired, checkonly, verbose):
        self.cmps = cmps
        self.maxmeet = maxmeet
        self.verbose = verbose
        self.size = len(cmps.keys()) + 1
        self.topcolor = topcolor
        
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

        # update tpn, give tps to players that have been paired at least once. 
        tpn = 0
        for i in range(size):
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
                    c["c" + str(ci)] = 0 if ci <18 else ''
                
                
                # C3 nottopscorers with absolute color preference cannot meet
                for col in ['w', 'b']:
                    col2 = col + '2'
                    if a['cop'] == col2 and b['cop'] == col2 and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                    if a['cod'] * b['cod'] >= 4  and (not a['top']) and (not b['top']):
                        c['canmeet'] = False
                
                c['psd'] = helpers.to_base36(a['acc'] -b['acc'])
               
                
                
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
                


            
    def update_crosstable(self, scorelevel, mdp, resident, remaining):
        maxpsd = max([c['scorelevel'] for c in mdp])-scorelevel if len(mdp ) > 0 else 0
        self.maxpsd = helpers.to_base36(maxpsd) 
        for c in mdp + resident:
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
                    cxx = 0


                    # PSD
                    c['c7'] = [0]*(maxpsd)
                    if a['cid'] == 0:
                        level =  b['mdp']
                        c['xpsd'] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[level] #  helpers.to_base36(level)
                        # print(c['ca'], c['cb'], level)
                        # print("PSDD", scorelevel, maxpsd, level, maxpsd - level)
                        if level > 0:
                            c['c7'][maxpsd-level] = 1   

                    # Topscorere

                    c['c10'] = c['c11']  = 0
                    if (a['top'] or b['top']) and a['cid'] > 0:

                        #c10 minimize the number of topscorers who get color diff > +2 or < -2
                        #print(c, a['cod'], b['cod'])
                        apf = a['cod'] + 1 if a['cid'] == c['w'] else a['cod'] - 1
                        bpf = b['cod'] + 1 if b['cid'] == c['w'] else b['cod'] - 1
                        c['c10'] = 1 if abs(apf) > 2 or abs(bpf) > 2 else 0 
                    
                        #c11 minimize the number of topscorers who get same color three times in a row
                        asq = a['csq'][-2:] + ('w' if a['cid'] == c['w'] else 'b')
                        bsq = b['csq'][-2:] + ('w' if b['cid'] == c['w'] else 'b')
                        c['c11'] = 1 if asq == 'www' or bsq == 'www' or asq == 'bbb' or bsq == 'bbb' else 0 

                    cxx = 10 if cxx == 0 and c['c10'] > 0 else 0
                    cxx = 11 if cxx == 0 and c['c11'] > 0 else 0
                    
                    #c12 minimize the number of players who do not get their color preference
                    c['c12'] = 1 if a['cop'] != '  ' and a['cop'][0].lower() ==  b['cop'][0].lower() else 0
                    #cxx = 12 if cxx == 0 and c['c12'] > 0
                    
                    #c13 minimize the number of players who do not get their strong color preference
                    c['c13'] = 1 if  a['cod'] * b['cod'] >= 1 else 0
                    cxx = 13 if cxx == 0 and c['c13'] > 0 else 0

                    #c14 minimize the number of players who receive downfloat in the previous round
                    c['c14'] = 1 if (a['cid'] == 0) and (b['flt'] & DF1) else 0
                    #cxx = 14 if cxx == 0 and c['c14'] > 0 else 0

                    #c15 minimize the number of players who receive upfloft in the previous round
                    c['c15'] = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF1) or (a['acc'] > b['acc']) and (b['flt'] & UF1)  else 0
                    cxx = 15 if cxx == 0 and c['c15'] > 0 else 0

                    #c16 minimize the number of players who receive downfloat two rounds before
                    c['c16'] = 1 if (a['cid'] == 0) and (b['flt'] & DF2) else 0
                    #cxx = 16 if cxx == 0 and c['c16'] > 0 else 0

                    #c17 minimize the number of players who receive upfloft two rounds before
                    c['c17'] = 1 if (a['acc'] < b['acc']) and (a['flt'] & UF2) or (a['acc'] > b['acc']) and (b['flt'] & UF2)  else 0
                    cxx = 17 if cxx == 0 and c['c17'] > 0 else 0

                    #c18 minimize the score difference of players who receive downfloat in the previous round
                    #c['c18'] = psd =  helpers.to_base36(competitor['acc'] - scorelevel + 1) if c['c14']  else ''
                    #print('xpsd', c['ca'], c['cb'], scorelevel, c['xpsd'] if  c['c14'] and 'xpsd' in c else '0')
                    c['c18'] = c['xpsd'] if c['c14'] and 'xpsd' in c else '0'
                    c['c18'] = [1 if helpers.from_base36(c['c18']) == maxpsd-i else 0 for i in range(maxpsd)]
                    cxx = 18 if cxx == 0 and c['c18'] != '' else 0

                    #c19 minimize the score difference of players who receive upfloft in the previous round
                    c['c19'] = c['xpsd'] if c['c15'] and 'xpsd' in c else '' 
                    c['c19'] = [1 if helpers.from_base36(c['c19']) == maxpsd-i else 0 for i in range(maxpsd)]
                    cxx = 19 if cxx == 0 and c['c19'] != '' else 0
                
                    #c20 minimize the score difference of players who receive downfloat two rounds before
                    #c['c20'] = psd =  helpers.to_base36(competitor['acc'] - scorelevel + 1) if c['c16']  else ''
                    c['c20'] = c['xpsd'] if c['c16'] and 'xpsd' in c else ''
                    c['c20'] = [1 if helpers.from_base36(c['c20']) == maxpsd-i else 0 for i in range(maxpsd)]
                    cxx = 20 if cxx == 0 and c['c20'] != '' else 0

                    #c21 minimize the score difference of players who receive upfloft two rounds before
                    c['c21'] = c['xpsd'] if c['c17'] and 'xpsd' in c else ''
                    c['c21'] = [1 if helpers.from_base36(c['c21']) == maxpsd-i else 0 for i in range(maxpsd)]
                    cxx = 21 if cxx == 0 and c['c21'] != '' else 0

                    c['cxx'] = cxx
                    
                    if c['c10'] > 0 or c['c11'] > 0:
                        self.numtop += 1

                    c['q1'] = c['q2'] = c['q3'] = c['q4'] = 0
                    c['q12'] = c['q5'] = c['q6'] = c['q7'] = []


        self.N = 3 # digits
        self.R = 2 # digits
        self.M = len(mdp)
        self.P = maxpsd
        self.B = len(mdp) + len(resident)
        self.S = 0
        self.O = 0



    def update_hetrogenious(self, competitors):
        N = self.N
        R = self.R
        M = self.M
        P = self.P
        B = self.B

                
        # print("All hetro", [c['cid'] for c in competitors])
        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['bsn'] 
                bbsn = bcompetitor['bsn']
                c = wcompetitor['opp'][bcid]
                if wbsn < bbsn and wcompetitor['opp'][bcid]['canmeet']:
                    c['q1'] = wbsn if wbsn <= M else 0
                    c['q2'] = bbsn if wbsn <= M else 0
                    # print("H", wcid, bcid, wbsn, bbsn, c['q1'], c['q2'], B)
                    c['q12'] = [c['q2'] if c['q1'] == i+1 else B+1 for i in range(M)] 
            c = wcompetitor['opp'][0]
            # print(c['ca'], c['cb'])
            c['q1'] = c['q2'] = 0
            c['q12'] = [0]*M



    def update_homogenious(self, competitors, numcomp, numdown):
        N = self.N
        R = self.R
        M = self.M
        P = self.P
        B = self.B
        self.S = S = r = numcomp//2
        self.D = numdown
        self.O = O = r*2 + numdown
        
        for wcompetitor in competitors:
            for bcompetitor in competitors:
                wcid = wcompetitor['cid']
                bcid = bcompetitor['cid']
                wbsn = wcompetitor['bsn']
                bbsn = bcompetitor['bsn']
                weight = 0
                c = wcompetitor['opp'][bcid]
                #print("Test ", wcid, )
                if wcid < bcid and wcompetitor['opp'][bcid]['canmeet']:
                    c['q3'] = 1 if wbsn > S else 0
                    c['q4'] = wbsn-1
                    c['q5'] = [1 if (wbsn <= S) and (S - wbsn == i) else 0  for i in range(O)] 
                    c['q6'] = [1 if (wbsn > S) and (O - wbsn -1 == i) else O for i in range(O)] 
                    c['q7'] = [bbsn if wbsn == i+1 else 0 for i in range(O)]  
                    # c['ho4'] = ho4 = [(-B+bbsn-1 if wbsn == i+1  else 0) for i in range(M)]
                    #weight = weight * R + (1 if wcid > r else 0)
                    #weight = weight * R*R + (wbsn-1)
                    #weight = weight * 10**n + (10**(n-wbsn) if wbsn <= r else 0)
                    ##weight = weight * 10**n + (10**(wbsn-1) if wbsn > r else 0)
                    #weight = weight * 10**(3*n) + 10*(n-wbsn)*(bbsn-1)
                    # print(weight)
                    wcompetitor['opp'][bcid]['homogenious'] = weight
            c = wcompetitor['opp'][0]
            c['q1'] = c['q2'] = c['q3'] = c['q4'] = 0
            c['q5'] = c['q6'] = c['q7'] = [0]*O


    def e10(self, n):
        return 10**n if n>= 0 else 0
            

    # Compute weight
    # mode 'E' - Hetrogenous 
    # mode 'S' - Homogenous 
    # mode 'A' - Add S-part

    def weight(self, c, mode):
        N = self.N
        R = self.R 
        M = self.M
        P = self.P
        B = self.B
        S = self.S
        O = self.O
        
        weight = ""
        if mode == 'E' or mode == 'S' or mode == 'T':
            weight = "C "      # Always start with C
            weight = weight + '-' + str([str(v).zfill(R) for v in c['c7']]).replace("'","")
            weight = weight + '-' + str(c['c10']).zfill(R)
            weight = weight + '-' +  str(c['c11']).zfill(R)
            weight = weight + '-' +  str(c['c12']).zfill(N)
            weight = weight + '-' +  str(c['c13']).zfill(N)
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
            weight = weight + str([str(v).zfill(N) for v in c['q12']]).replace("'","")
        if S > 0 and (mode == 'S' or mode == 'T'):
            if 'mode' == 'S':
                weight = weight + ' E '
                weight = weight + str([str(v).zfill(N) for v in [0]*M]).replace("'","")
            weight = weight + ' S '
            weight = weight       + str(c['q3']).zfill(R) 
            weight = weight + '-' + str(c['q4']).zfill(R+R)
            weight = weight + '-' + str([str(v).zfill(R) for v in c['q5']]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(R) for v in c['q6']]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(R) for v in c['q7']]).replace("'","")
        if mode == 'A' and ' S ' not in c['tweight']:
            weight = c['tweight']
            weight = weight + ' S '
            weight = weight       + "0".zfill(R) 
            weight = weight + '-' + "0".zfill(R+R)
            weight = weight + '-' + str([str(v).zfill(R) for v in [0]*O]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(R) for v in [0]*O]).replace("'","")
            weight = weight + '-' + str([str(v).zfill(R) for v in [0]*O]).replace("'","")
        c['tweight'] = weight
        c['weight'] = iweight = int(''.join(c for c in weight if c.isdigit()))
       
        return iweight




    def adjust_hetrogenious(self, competitors, numcomp, numdown, weight):
        R = self.R
        self.S = S = numcomp//2
        self.D = D = numdown
        self.O = O = S*2 + numdown
        
        if S > 0:
            weight = weight * R * R * R
            weight = weight * R**(3*O)
        return weight
    
    def compute_weight2(self, bracket):
        N = self.N
        R = self.R
        M = self.M
        P = self.P
        B = self.B
        S = self.S
        O = self.O

        quality = {
            'weight': 0,
            **{ 'c'+str(i): ([0]*P if i == 7 or i >= 18 else 0)   for i in range(6, 22)},
            'q12' :[0]*M,
            **{ 'q'+str(i): ([0]*O if i >= 5 else 0)  for i in range(3, 8) },
        }
        
        
        weight = 0
        for c in bracket['pairs']:
            line = "C"
            for elem in ['ca', 'cb', 'c7',  'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c19', 'c20', 'c21', 'q12', 'q3', 'q4', 'q5', 'q6', 'q7']:
                line += " " + str(c[elem]) if elem in c else '--'
            print(line)
            for elem in ['weight', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'q3', 'q4']:
                quality[elem] += c[elem]
            for elem in ['c7', 'c18', 'c19', 'c20', 'c21', 'q12', 'q5', 'q6', 'q7']:
                for i in range(min(len(quality[elem]), len(c[elem]))):
                    quality[elem][i] += c[elem][i]
                    print(elem, i, c[elem][i], quality[elem][i] )

        for c in bracket['downfloaters']:
            line = "C"
            for elem in ['ca', 'cb', 'c7',  'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c19', 'c20', 'c21', 'q12', 'q3', 'q4', 'q5', 'q6', 'q7']:
                line += " " + (str(c['opp'][0][elem]) if elem in c['opp'][0] else '--')
            print(line)
            for elem in ['weight', 'c14', 'c18']:
                quality[elem] +=  c['opp'][0][elem] if elem in c['opp'][0] else 0
            for elem in ['c7', 'c18', 'c20']:
                for i in range(min(len(quality[elem]),len(c['opp'][0][elem]))):
                    quality[elem][i] += c['opp'][0][elem][i] if elem in c['opp'][0] else 0
        quality['c6'] = len(bracket['downfloaters']) + len(bracket['limbo'])
        quality['iweight'] = quality['weight']
        self.weight(quality, 'T')
        if quality['weight'] != quality['iweight'] and False:
            print(quality['tweight'])
            print(quality['weight'])
            print(quality['iweight'])
            print(quality)
            raise
        # elem != 'q6' and c[elem][i] != O 
        return quality
    
    def compute_weight(self, bracket):
        quality = self.compute_weight2(bracket)
        weight = 0
        for c in bracket['pairs']:
            #print(c['weight'])
            weight += c['weight']
        for c in bracket['downfloaters']:
            #print(c['cid'], c['opp'][0]['weight'] if 'weight' in c['opp'][0] else 0)
            weight += c['opp'][0]['weight'] if 'weight' in c['opp'][0] else 0
        quality['weight'] = weight
        print(quality)
        if quality['weight'] != quality['iweight']:
            print(quality['tweight'])
            print(quality['weight'])
            print(quality['iweight'])

        return bracket['quality']
    


                                       
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
                              


                        
