# -*- coding: utf-8 -*-
"""
Created on Sun Sep 22 12:59:02 2024

@author: Otto
"""

import berger
import sys
import json

for i in range(10, 12, 2):
    bt = berger.bergertablesGeneric(i)
    #bt = berger.bergertables(i)
    json.dump(bt, sys.stdout, indent=2)
    
    ## rr = bergertables(n)
    ## # In round 6, pair 2:
    white = bt['parining'][6][2]['white']
    black = bt['parining'][6][2]['black']
    print(white, black)
    j = i//2
    for r in range (1, i):
        for b in range(1, j+1):
            print('F', r, b, berger.bergerpairing(bt, r, b))
    for w in range(1, i+1):            
            for b in range(1, i+1):
                if w != b:
                    print('R', w, b, berger.bergerlookup(bt, w, b))

    for r in range (1, i):
        txt = 'Rd ' + str(r) + ': '
        for b in range(1, j+1):
            p =  berger.bergerpairing(bt, r, b)
            w = str(p['white'])
            b = str(p['black'])
            txt += '  ' + w +' - ' + b
        print(txt) 
                  