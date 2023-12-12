# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 15:50:51 2023

@author: Otto Milvang, sjakk@milvang.no
"""

## 
## bergertables is the core of the round robin, 
## Se FIDE handbook
## C: General Rules and Technical Recommendations for Tournaments
## 05. General Regulations for Competitions / General Regulations for Competitions. 
## Annex 1: Details of Berger Table 
##
## n is he number of players, odd nubers are lifted to the first even number
## returns a 3-level dict  
##   1-dim - 1 .. n-1 is [round_number]
##   2-dim - 1 .. n/2 is [pair_number]
##   3-dim - {'white', 'black'} - players numbered 1 .. n 
## rr = bergertables(n)
## # In round 6, pair 2:
## white = rr[6][2]['white']
## black = rr[6][2]['black']


def bergertables(n):
    if (n % 2) == 1:
        n += 1
    nhalf = n//2
    bergertab = { 'players': n };
    pairing = {} 
    for pair in range(1, nhalf+1):
        pairing[pair] = { 'white': pair, 'black': n-pair+1 }
    bergertab[1] = pairing; # First round
    for round in range(2, n):
        newpairing = {}
        if (round%2) == 0:
            newpairing[1] = {
                'white': pairing[1]['black'],
                'black': pairing[nhalf]['black']
                }
        else:
            newpairing[1] = {
                'white': pairing[nhalf]['black'],
                'black': pairing[1]['white']
                }
        for pair in range(2, nhalf):
            newpairing[pair] = {
                'white': pairing[nhalf-pair+1]['black'], 
                'black': pairing[nhalf-pair+2]['white']
                }
        if (round%2) == 0:
            newpairing[nhalf] = {
                'white': pairing[1]['white'], 
                'black': pairing[2]['white']
                }
        else:
            newpairing[nhalf] = {
               'white': pairing[1]['black'], 
               'black': pairing[2]['white']
               }
        bergertab[round] = newpairing;
        pairing = newpairing;
    return bergertab;

## 
## lookupbergerpairing(bergertable, white, black) return round and board number, 
## bergertable is a structure returned by bergertables(n)
## white is the start number of the white-player
## black is the start number of the blcck-player
## returns a tuple [round, pair] 

def lookupbergerpairing(bergertable, white, black):
    n = bergertable['players']
    if not 'rnd' in bergertable:
        bergertable['rnd'] = [0] * n * n
        bergertable['pair'] = [0] * n * n
        for rnd in range(1, n):
            for pair in range(1, n//2 +1):
                w = bergertable[rnd][pair]['white']
                b = bergertable[rnd][pair]['black']
                bergertable['rnd'][(w-1)*n+b-1] = rnd
                bergertable['rnd'][(b-1)*n+w-1] = rnd + n - 1
                bergertable['pair'][(w-1)*n+b-1] = pair
                bergertable['pair'][(b-1)*n+w-1] = pair
    return [bergertable['rnd'][(white-1)*n+black-1], bergertable['pair'][(white-1)*n+black-1]]
        
#json.dump(roundrobinpairing(12), sys.stdout, indent=2)
          
          