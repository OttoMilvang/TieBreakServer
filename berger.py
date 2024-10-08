# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
## # In round 6, board 2:
## white = rr['parining'][6][2]['white']
## black = rr['parining'][6][2]['black']


def bergertables(nplayers):
    nplayers += (nplayers % 2)
    pairs = nplayers//2
    bergertable = { 'players': nplayers, 'parining': {} }
    bergertable['parining'][1] = pairing =  { boardno: {'white': boardno, 'black': nplayers - boardno + 1} for boardno in range(1, pairs + 1) } # First round
    (wp, wc, bp, bc) = (1, 'white', pairs, 'black')
    for rnd in range(2, nplayers):
        bergertable['parining'][rnd] = newpairing = {}
        newpairing[1] = { 'white': pairing[wp]['black'], 'black': pairing[bp][bc] }
        for board in range(2, pairs):
            newpairing[board] = {'white': pairing[pairs-board+1]['black'], 'black': pairing[pairs-board+2]['white']}
        newpairing[pairs] = {'white': pairing[1][wc], 'black': pairing[2]['white'] }
        pairing = newpairing
        (wp, wc, bp, bc) = (bp, bc, wp, wc)
    return bergertable



"""
The generic BergerTable follows the description in the paper "Berger explained". 
Its made generic,  so its should be easy to translate it into other programming languages.
https://www.milvang.no/berger/BergerExplained.pdf
"""

def bergertablesGeneric(nplayers):
    # Let N be the number of players (or number of players + 1 if the number of players are odd)
    # The players are assigned a pairing number 1 to N. The number of boards is B = N/2. 
    nplayers += (nplayers % 2)
    pairs = nplayers//2
    bergertable = { 'players': nplayers, 'parining': {} }
    
    # In the first round the lowest half will have white and the highest half black. 
    # In general, on board b, where b is in the range 1 ... B,  player m shall have white against player N-m+1.  
    pairing =  {}
    for board in range(1, pairs + 1):
        pairing[board] = {'white': board, 'black': nplayers - board + 1}
    bergertable['parining'][1] = pairing
    
    # nplayeriswhite is a flag to alternate color for player N
    nplayeriswhite = False
    for rnd in range(2, nplayers):
        # Step 1: 
        # Sort the players 1 … N-1 according to their pair number in the 
        # previous round and then white before black. 
        playerlist = []
        for board in range(1, pairs+1):
            for color in ['white', 'black']:
                if pairing[board][color] < nplayers:
                    playerlist.append(pairing[board][color])
        # We dont need longer need pairing for the previous round. Resuse for this round                    
        pairing = {}
        # On the first board player N shall meet the last player in sorted list. 
        # Remove this player from the list and pair him against player N. 
        # Player N shall alternate color. This other player will be white if 
        # his pairing number is in the range 1 … B, and black otherwise.  
        firstboard = playerlist.pop()
        if nplayeriswhite:
            pairing[1] = {'white': firstboard, 'black': nplayers}
        else:
            pairing[1] = {'white': nplayers, 'black': firstboard}
        nplayeriswhite = not nplayeriswhite
        # From the end of the list, make a pair with white as the penultimate 
        # player in the list, and black as the last player in the list and 
        # remove these players from the list.  Repeat this until the list is empty.  
        for board in range(2, pairs+1):
            black = playerlist.pop()
            white = playerlist.pop()
            pairing[board] = {'white': white, 'black': black}
        bergertable['parining'][rnd] = pairing
        # Repeat from step 1 until all rounds are paired. 
    return bergertable




## 
## bergerpairing(bergertable, round, board) return round and board number, 
## bergertable is a structure returned by bergertables(n)
## rnd is the current round
## board is current board
## returns a tuple { 'white': white, 'black': black } 

def bergerpairing(bergertable, rnd, board):
    if rnd in bergertable['parining'] and board in bergertable['parining'][rnd]:
        return bergertable['parining'][rnd][board]
    return None


## 
## bergerlookup(bergertable, white, black) return round and board number, 
## bergertable is a structure returned by bergertables(n)
## white is the start number of the white-player
## black is the start number of the blcck-player
## returns a tuple { 'round': round, 'board': board } 

def bergercrosstables(bergertable):
    nplayers = bergertable['players']
    pairs = nplayers//2
    bergertable['crosstable'] = crosstable = { wplayer : {} for wplayer in range(1, nplayers + 1)  }
    for rnd in range(1, nplayers):
        for board in range(1, pairs +1):
            w = bergertable['parining'][rnd][board]['white']
            b = bergertable['parining'][rnd][board]['black']
            crosstable[w][b] = {'round': rnd, 'board': board }
            crosstable[b][w] = {'round': rnd + nplayers - 1, 'board': board }
    return bergertable


def bergerlookup(bergertable, white, black):
    if 'crosstable' not in bergertable:
        bergercrosstables(bergertable)
    if white in bergertable['crosstable'] and black in bergertable['crosstable'][white]:
        return bergertable['crosstable'][white][black]
    return None


def print_bergertable(n):
    roundrobin = bergertables(n)
    n = roundrobin['players']
    pairs = n//2
    print(str(n-1) + ' and ' + str(n) + ' players:')
    for rnd in range (1, n):
        txt = 'Rd ' + str(rnd) + ': '
        for board in range(1, pairs+1):
            pair =  bergerpairing(roundrobin, rnd, board)
            white = str(pair['white'])
            black = str(pair['black'])
            txt += '  ' + white +' - ' + black
        print(txt) 

#### Module test ####

def module_test():
    for n in  [6, 10, 25]:
        print_bergertable(n)
        print()
          
          