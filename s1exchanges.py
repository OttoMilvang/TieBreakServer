# -*- coding: utf-8 -*-
"""
Created on Sun Jan 26 08:43:27 2025

@author: otto
"""

from itertools import combinations
import functools


def listexchanges(s1, s2):
    src = [i+1 for i in range(s1+s2)]
    e1 = [list(i) for i in combinations(src, s1)]   
    e2 = [list(i) for i in combinations(src, s2)]   
    exchanges = []
    elen = len(e1)
    for i in  range(elen):
        l1 = e1[i]
        l2 = e2[elen-i-1][-s1:]
        if all([l1[j] < l2[j] for j in range(s1)]):
            exchanges.append(l1)
    
    print(s1, s2, len(exchanges))    
    return exchanges 

def compare_flex(p1, p2):
    plen = len(p1)
    for i in range(plen):
        if p1[i] != p2[i]:
            return p1[i] - p2[i]
    return(0)

def compare_rlex(p1, p2):
    plen = len(p1)
    for i in range(plen-1, -1, -1):
        if p1[i] != p2[i]:
            return p1[i] - p2[i]
    return(0)

def compare_fide(p1, p2):
    plen = len(p1)
    n1 = n2 = 0
    s1 = s2 = 0
    for i in range(plen):
        n1 = n1 + 1 if p1[i] > plen else n1
        n2 = n2 + 1 if p2[i] > plen else n2
        s1 += p1[i]
        s2 += p2[i]
    if n1 != n2:
        return n1 - n2
    if s1 != s2:
        return s1 - s2
    res = compare_rlex(p1[0:plen-n1], p2[0:plen-n2])
    if res != 0:
        return(res)
    return compare_flex(p1[-n1:], p2[-n2:])



src = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
a = combinations(src, 8) 
#y = [list(i) for i in a]
z = []
for i in a:
    p = list(i)
    #for j in range(len(j)):
        
for s1 in range(3,4):
  for s2 in range(s1, s1+4): 
      l1 = listexchanges(s1, s2)
      flex = sorted(l1, key=functools.cmp_to_key(compare_flex))
      rlex = sorted(l1, key=functools.cmp_to_key(compare_rlex))
      fide = sorted(l1, key=functools.cmp_to_key(compare_fide))
      for i in range(len(flex)):
          print(fide[i], flex[i])
      print()

