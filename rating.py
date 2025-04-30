# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 08:28:13 2023
@author: Otto Milvang, sjakk@milvang.no
"""

from decimal import Decimal

# import tables from FIDE Handbook
import fidetables


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
    pd = fidetables.DiffToPd[diff]
    if sign > 0:
        pd = 100 - pd
    return Decimal(pd) / 100


#
# Compute Ecpected Score baed on own rating
#


def ComputeSumExpectedScore(ratingPlayer, ratingOpponents):
    sum = 0
    for opponent in ratingOpponents:
        sum += ComputeExpectedScore(ratingPlayer, opponent)
    return sum


#
# Coppute Delta R, the differnce between score and ecpecter score
#


def ComputeDeltaR(pd, score):
    return score - pd


#
# Compute Average Rating of Opponents
#


def ComputeAverageRatingOpponents(ratingsopp):
    num = len(ratingsopp)
    if num == 0:
        return 0
    return int(round(sum(ratingsopp) / num + 0.000001))


#
# Compute Tournament Performance Rating, and also check for norms (GM/IM/WGM/WIM)
#


def ComputeTournamentPerformanceRating(score, ratingsopp, norm=""):
    num = len(ratingsopp)
    if num == 0:
        return 0
    tnorm = norm.upper()
    if len(tnorm) > 0:
        rfloor = {"GM": 2200, "IM": 2050, "WGM": 2000, "WIM": 1850}
        sortopp = sorted(ratingsopp)
        ratingsopp = [max(rfloor[norm], sortopp[0])] + sortopp[1:]
    score100 = int(round(score * 100))
    scr = int(round(score100 / num + 0.000001))
    return ComputeAverageRatingOpponents(ratingsopp) + fidetables.ScoreToDp[scr]


#
# Compute Perfect Tournament Performance
#


def ComputePerfectTournamentPerformance(score, ratingsopp):
    # exception for score == 0
    if len(ratingsopp) == 0:
        return 0
    if score == Decimal("0.0"):
        return min(ratingsopp) - 800
    # avoid infinite loop on illegal input
    if score > len(ratingsopp):
        return max(ratingsopp) + 800
    # invariant: low < ptp,  high >= ptp
    # when high-low == 1 then ptp = high
    num = len(ratingsopp)
    if num == 0:
        return 0
    # score100 = Decimal(int(round(score*100))) / 100
    start = ComputeTournamentPerformanceRating(score, ratingsopp)
    step = 16  # Seems to be a good start value
    expscore = ComputeSumExpectedScore(start, ratingsopp)
    if expscore >= score:
        high = start
        while ComputeSumExpectedScore(start - step, ratingsopp) >= score:
            high = start - step
            step *= 2
        low = start - step
    else:
        low = start
        while ComputeSumExpectedScore(start + step, ratingsopp) < score:
            low = start + step
            step *= 2
        high = start + step
    step = high - low
    while high - low > 1:
        step = step // 2
        if ComputeSumExpectedScore(low + step, ratingsopp) >= score:
            high = high - step
        else:
            low = low + step
    return high
