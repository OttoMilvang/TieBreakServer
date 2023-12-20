# -*- coding: utf-8 -*-
"""
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
        return 0.0;
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
# Sole point system    
def solve_pointsystem(score):
    res = {}
    for l in [0, 0.5, 1]:
       res['L'] = l
       for d in [l+0.5, l+1, l+1.5, l+2]:
            res['D'] = d
            for w in [d+0.5, d+1, d+1.5, d+2, d+2.5, d+3]:
                res['W'] = w
                for p in ['W', 'D', 'L']:
                    for u in ['D', 'L', 'W']:
                        ok = True
                        for result in score:
                            tsum = 0
                            if 'W' in result:
                                tsum += result['W'] * w
                            if 'D' in result:
                                tsum += result['D'] * d
                            if 'L' in result:
                                tsum += result['L'] * l
                            if 'P' in result:
                                tsum += result['P'] * res[p]
                                res['P'] = p
                            if 'U' in result:
                                tsum += result['U'] * res[u]
                                res['U'] = u
                            if 'Z' in result:
                                res['Z'] = 0.0
                            if tsum != result['sum']:
                                ok = False
                        if ok:
                            return res
    return None
        