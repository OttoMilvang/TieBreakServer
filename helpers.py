# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Tue Oct 31 13:57:55 2023
@author: Otto Milvang, sjakk@milvang.no
"""

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
    return float(txt)

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

def solve_scoresystem(equations):
    res = {}
    score = {
        'sum': 0,
        'W': 0,
        'D': 0,
        'L': 0,
        'P': 0,
        'U': 0,
        'Z': 0
    }
    for l in [0, 0.5, 1]:
       res['L'] = l
       for d in [l+0.5, l+1, l+1.5, l+2]:
            res['D'] = d
            for w in [d+0.5, d+1, d+1.5, d+2, d+2.5, d+3]:
                res['W'] = w
                for p in ['W', 'D', 'L']:
                    res['P'] = res[p]
                    for u in ['D', 'L', 'W']:
                        ok = True
                        for result in equations:
                            tsum = 0
                            tsum += result['W'] * w
                            tsum += result['D'] * d
                            tsum += result['L'] * l
                            tsum += result['P'] * res[p]
                            res['P'] = p
                            tsum += result['U'] * res[u]
                            res['U'] = u
                            res['Z'] = 0.0
                            for key, value in result.items():
                                score[key] += value
                            if (res['W'] == 1 and res['D'] == 0.5 and res['L'] == 0.0 and res['P'] == 'W' ):                                
                                #print(result, tsum, result['sum'])
                                pass
                            if tsum != result['sum']:
                                ok = False
                        if ok:
                            ret = {key: value for key, value in res.items() if score[key] != 0}
                            for key in ['P', 'U']:
                                if key in ret and res[key] in ['W', 'D', 'L', 'Z'] and ret[key] not in ret:
                                    ret[res[key]] = res[res[key]]
                            #print(score)
                            #print(ret)
                            return ret
    return None
        