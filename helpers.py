# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Tue Oct 31 13:57:55 2023
@author: Otto Milvang, sjakk@milvang.no
"""

import math
import sys
import json
from decimal import *


# ==============================
#
#  Helpers

def parse_date(date):
    datetime = date.split(' ', 1)
    dateparts = datetime[0].split('.')
    if len(dateparts) == 3:
        if len(dateparts[0]) == 4:
            return date.replace('.', '-')
        if len(dateparts) == 2:
            return dateparts[2] + '-' + dateparts[1] + '-' + dateparts[0] + " " + datetime[1]
        return dateparts[2] + '-' + dateparts[1] + '-' + dateparts[0]
    dateparts = datetime[0].split('/')
    if len(dateparts) == 3:
        if len(dateparts[0]) == 4:
            return date.replace('/', '-')
        return '20' + date.replace('/', '-')
    return(date)
    
    
def parse_minutes(time):
    hms = time.split(':')
    if len(hms) != 3:
        return 0
    return int(hms[0]) * 60 + int(hms[1]) 
    
def parse_seconds(time):
    hms = time.split(':')
    if len(hms) != 3:
        return 0
    return int(hms[0]) * 3600 + int(hms[1]) * 60 + int(hms[2])
    
        
def parse_int(txt):
    txt = txt.strip()
    if len(txt) == 0:
        return 0
    return int(txt)
   
def parse_float(txt):
    txt = txt.strip()
    if len(txt) == 0:
        return 0.0
    txt = txt.replace(',','.')
    return Decimal(txt)

def to_base36(num):
    b36 = min(abs(int(num * Decimal('2.0'))),35)
    return '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'[b36]

# return -1 if different
# return 1 if equal
# return 0 if dont know
def is_equal(txt, struct1, struct2):
    if not (txt in struct1 and  txt in struct2):
        return 0
    val1 = struct1[txt]
    val2 = struct2[txt]
    if (type(val1) == type(0) and val1 == 0) or (type(val2) == type(0) and val2 == 0):
        return 0
    if (type(val1) == type('') and val1 == '') or (type(val2) == type('') and val2 == ''):
        return 0
    if val1 == val2:
        return 1
    else:
        return -1
    

#
# Solve point system    
# Input array of equations:
# sum = w * W + d * D + l * L + p * P + u * U + z * Z
# Solve w, d, l, p, u, z for variables where W, D, L, P, U and Z present in equautins
#

def solve_scoresystem_p(equations, pab):
    #print(equations) 
    score = {
        'sum': Decimal('0.0'),
        'W': 0,
        'D': 0,
        'L': 0,
        'P': 0,
        'U': 0,
        'Z': 0
    }
    #print ('PAB:', pab)
    res = {}
    for l in [Decimal('0.0'), Decimal('0.5'), Decimal('1.0')]:
       res['L'] = l
       for d in [l+Decimal('0.5'), l+Decimal('1.0'), l+Decimal('1.5'), l+Decimal('2.0')]:
            res['D'] = d
            for w in [d+d-l, d+d-l+1, d+d-l+Decimal('0.5'), d+d-l+Decimal('1.0'), d+d-l+Decimal('1.5'), d+d-l+Decimal('2.0')]:
                res['W'] = w
                for u in ['D', 'L', 'W']:
                    res['U'] = res[u]
                    ok = True
                    #if l != 0.0 or d != 0.5 or w != 1.0 or u != 'D':
                    #    continue
                    for result in equations:
                        tsum = 0
                        tsum += result['W'] * w
                        tsum += result['D'] * d
                        tsum += result['L'] * l
                        tsum += result['U'] * res[u]
                        res['U'] = u
                        res['Z'] = 0.0
                        for key, value in result.items():
                            if key != 'pab' and key != 'pres':
                                score[key] += value
                        pok = False
                        if result['P'] > 0:
                            for p in pab:
                                #print(tsum, result['P'], res[p],  tsum + result['P'] * res[p], result['sum'])
                                if tsum + result['P'] * res[p] == result['sum']:
                                    #print('TRUE', result['sum'])
                                    pok = True
                                    result['pres'] = p
                                    res['P'] = res[p]
                        else:
                            #print(tsum, result['P'], result['sum'])
                            pok = tsum == result['sum']
                        ok = ok and pok

                    if ok:
                        ret = {key: value for key, value in res.items() if score[key] != 0}
                        for key in ['X', 'U']:
                            if key in ret and res[key] in ['W', 'D', 'L', 'Z'] and ret[key] not in ret:
                                ret[res[key]] = res[res[key]]
                                
                        for eq in equations:
                            #print(eq)
                            if 'pab' in eq:
                                #print(eq)
                                eq['pab']['wResult'] = eq['pres']
                                res.pop('P', None) 
                                
                        #print(equations)
                        #print('Score:', score)
                        #print('Ret = ',  ret)
                        return ret
    #print('none')
    #return None

def solve_scoresystem(equations):
    res = False
    res = res or solve_scoresystem_p(equations, ['W'])
    res = res or solve_scoresystem_p(equations, ['D'])
    res = res or solve_scoresystem_p(equations, ['L'])
    res = res or solve_scoresystem_p(equations, ['W', 'D'])
    res = res or solve_scoresystem_p(equations, ['D', 'L'])
    res = res or solve_scoresystem_p(equations, ['W', 'D','L'])

    return(res)
    #print(equations) 
    

#
# Function: getFileFormat
# Returns a file format.
#
# Parameters:
#     $filename - Filename of tournament file
#
 

def getFileFormat(filename):
    parts = filename.split('.')
    lastp = parts[-1].lower()
    retval = ''
    match lastp:
        case 'jch' | 'json':
            return 'JSON'
        case 'txt' | 'trf' | 'trfx':
            return 'TRF'
        case 'trx':
            return 'TS'
        case _:
            return 'JSON'


def sortxval(x):
    return x['val']
    
def sortnum(x):
    return x['num']
    
# =================
#
# Json output
#
#

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
        return '_jpre_'+ str(obj) + '_jpost_'
    raise TypeError("Type not serializable")
    
    
def json_output(file, obj):
    if isinstance(file, str):
        f = sys.stdout if file == '-' else open(file, 'w')
    else:
        f = file
    jsonout = json.dumps(obj, indent=2, default=decimal_serializer) 
    f.write(jsonout.replace('"_jpre_', '').replace('_jpost_"', '') + '\n')
    if isinstance(file, str) and  file != '-':
        f.close()
        
        
        
        