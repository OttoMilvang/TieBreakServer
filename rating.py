# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Fri Aug 18 08:28:13 2023
@author: Otto Milvang, sjakk@milvang.no
"""

from decimal import *

# Tables from FIDE Handbook

ScoreToDp = [ -800,
          -677,-589,-538,-501,-470,-444,-422,-401,-383,-366,
          -351,-336,-322,-309,-296,-284,-273,-262,-251,-240,
          -230,-220,-211,-202,-193,-184,-175,-166,-158,-149,
          -141,-133,-125,-117,-110,-102, -95, -87, -80, -72,
           -65, -57, -50, -43, -36, -29, -21, -14,  -7,   0,
             7,  14,  21,  29,  36,  43,  50,  57,  65,  72,
            80,  87,  95, 102, 110, 117, 125, 133, 141, 149,
           158, 166, 175, 184, 193, 202, 211, 220, 230, 240,
           251, 262, 273, 284, 296, 309, 322, 336, 351, 366,
           383, 401, 422, 444, 470, 501, 538, 589, 677, 800,
        ];
DiffToPd = [50,                                     # 0
            50,  50,  50,  51,  51,  51,  51,  51,  51,  51,
            52,  52,  52,  52,  52,  52,  52,  53,  53,  53,
            53,  53,  53,  53,  53,  54,  54,  54,  54,  54,
            54,  54,  55,  55,  55,  55,  55,  55,  55,  56,
            56,  56,  56,  56,  56,  56,  57,  57,  57,  57,
            57,  57,  57,  58,  58,  58,  58,  58,  58,  58,
            58,  59,  59,  59,  59,  59,  59,  59,  60,  60,
            60,  60,  60,  60,  60,  60,  61,  61,  61,  61,
            61,  61,  61,  62,  62,  62,  62,  62,  62,  62,
            62,  63,  63,  63,  63,  63,  63,  63,  64,  64, # 100
            64,  64,  64,  64,  64,  64,  65,  65,  65,  65,
            65,  65,  65,  66,  66,  66,  66,  66,  66,  66,
            66,  67,  67,  67,  67,  67,  67,  67,  67,  68,
            68,  68,  68,  68,  68,  68,  68,  69,  69,  69,
            69,  69,  69,  69,  69,  70,  70,  70,  70,  70,
            70,  70,  70,  71,  71,  71,  71,  71,  71,  71,
            71,  71,  72,  72,  72,  72,  72,  72,  72,  72,
            73,  73,  73,  73,  73,  73,  73,  73,  73,  74,
            74,  74,  74,  74,  74,  74,  74,  74,  75,  75,
            75,  75,  75,  75,  75,  75,  75,  76,  76,  76, # 200
            76,  76,  76,  76,  76,  76,  77,  77,  77,  77,
            77,  77,  77,  77,  77,  78,  78,  78,  78,  78,
            78,  78,  78,  78,  78,  79,  79,  79,  79,  79,
            79,  79,  79,  79,  79,  80,  80,  80,  80,  80,
            80,  80,  80,  80,  80,  81,  81,  81,  81,  81,
            81,  81,  81,  81,  81,  81,  82,  82,  82,  82,
            82,  82,  82,  82,  82,  82,  82,  83,  83,  83,
            83,  83,  83,  83,  83,  83,  83,  83,  84,  84,
            84,  84,  84,  84,  84,  84,  84,  84,  84,  84,
            85,  85,  85,  85,  85,  85,  85,  85,  85,  85, # 300
            85,  85,  86,  86,  86,  86,  86,  86,  86,  86,
            86,  86,  86,  86,  86,  87,  87,  87,  87,  87,
            87,  87,  87,  87,  87,  87,  87,  87,  88,  88,
            88,  88,  88,  88,  88,  88,  88,  88,  88,  88,
            88,  88,  88,  88,  89,  89,  89,  89,  89,  89,
            89,  89,  89,  89,  89,  89,  89,  90,  90,  90,
            90,  90,  90,  90,  90,  90,  90,  90,  90,  90,
            90,  90,  90,  90,  91,  91,  91,  91,  91,  91,
            91,  91,  91,  91,  91,  91,  91,  91,  91,  91,
            91,  92,  92,  92,  92,  92,  92,  92,  92,  92, # 400
            92,  92,  92,  92,  92,  92,  92,  92,  92,  92,
            93,  93,  93,  93,  93,  93,  93,  93,  93,  93,
            93,  93,  93,  93,  93,  93,  93,  93,  93,  93,
            93,  93,  94,  94,  94,  94,  94,  94,  94,  94,
            94,  94,  94,  94,  94,  94,  94,  94,  94,  94,
            94,  94,  94,  94,  94,  94,  95,  95,  95,  95,
            95,  95,  95,  95,  95,  95,  95,  95,  95,  95,
            95,  95,  95,  95,  95,  95,  95,  95,  95,  95,
            95,  95,  95,  95,  96,  96,  96,  96,  96,  96,
            96,  96,  96,  96,  96,  96,  96,  96,  96,  96, # 500
            96,  96,  96,  96,  96,  96,  96,  96,  96,  96,
            96,  96,  96,  96,  96,  96,  96,  97,  97,  97,
            97,  97,  97,  97,  97,  97,  97,  97,  97,  97,
            97,  97,  97,  97,  97,  97,  97,  97,  97,  97,
            97,  97,  97,  97,  97,  97,  97,  97,  97,  97,
            97,  97,  97,  97,  97,  97,  97,  97,  97,  98,
            98,  98,  98,  98,  98,  98,  98,  98,  98,  98,
            98,  98,  98,  98,  98,  98,  98,  98,  98,  98,
            98,  98,  98,  98,  98,  98,  98,  98,  98,  98,
            98,  98,  98,  98,  98,  98,  98,  98,  98,  98, # 600
            98,  98,  98,  98,  98,  98,  98,  98,  98,  99,
            98,  98,  98,  98,  98,  98,  98,  98,  98,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99, # 700
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99,  99,  99,  99,  99,  99,
            99,  99,  99,  99,  99, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
           100, 100, 100, 100, 100, 100, 100, 100, 100, 100, # 800
        ]


############################################
#
# Exact computation on integers (pd*100)
#

def ComputeExpectedScore(ratingPlayer, ratingOpponent):
    if ratingPlayer == 0 or ratingOpponent == 0:
        return None
    diff = ratingOpponent - ratingPlayer
    if diff > 800:
        diff = 800  
    elif diff < -800:
        diff = -800
    sign = 1
    if diff < 0:
        sign = -1
        diff = -diff
    pd = DiffToPd[diff]
    if sign > 0:
        pd = 100 - pd
    return Decimal(pd)/100

def ComputeSumExpectedScore(ratingPlayer, ratingOpponents):
    sum = 0
    for opponent in ratingOpponents:
        sum += ComputeExpectedScore(ratingPlayer, opponent)
    return sum


def xxComputeExpectedScore(ratingPlayer, ratingOpponent):
    ces = ComputeExpectedScore100(ratingPlayer, ratingOpponent)
    if ces == None:
        return None
    return  float(ces)/ 100.0


def ComputeDeltaR(pd, score):
    return score - pd


def ComputeAverageRatingOpponents(ratingsopp):
    num = len(ratingsopp)
    if num == 0: return 0
    return int(round(sum(ratingsopp) / num + 0.000001))
    
def ComputeTournamentPerformanceRating(score, ratingsopp):
    num = len(ratingsopp)
    if num == 0: return 0
    score100 = int(round(score*100))
    scr = int(round(score100 / num + 0.000001))
    return(ComputeAverageRatingOpponents(ratingsopp) + ScoreToDp[scr])    
    

def ComputePerfectTournamentPerformance(score, ratingsopp):
    # exception for score == 0 
    if len(ratingsopp) == 0:
        return 0
    if score == Decimal('0.0'):
        return min(ratingsopp) - 800
    # avoid infinite loop on illegal input
    if score > len(ratingsopp):
        return max(ratingsopp) + 800
    # invariant: low < ptp,  high >= ptp 
    # when high-low == 1 then ptp = high
    num = len(ratingsopp)
    if num == 0: return 0
    #score100 = Decimal(int(round(score*100))) / 100
    start = ComputeTournamentPerformanceRating(score, ratingsopp)
    step = 16   #  Seems to be a good start value
    expscore = ComputeSumExpectedScore(start, ratingsopp)
    if expscore >= score:
        high = start
        while ComputeSumExpectedScore(start-step, ratingsopp) >= score:
            high = start -step
            step *= 2 
        low = start- step
    else:         
        low = start
        while ComputeSumExpectedScore(start+step, ratingsopp) < score:
            low = start +step
            step *= 2
        high = start + step
    step = high - low
    while high-low > 1:
        step = step//2
        if ComputeSumExpectedScore(low+step, ratingsopp) >= score:
            high = high - step
        else:
            low = low + step
    return high
    

