# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 10:41:41 2025

@author: Otto
"""
from enum import Enum

# Quality constants

c1 = 0
class qdefs(Enum):
    QC6 = 0
    QC7 = 1
    QN8 = 2
    QC8 = 3
    QC9 = 4
    QMM = 5
    QC10 = 6
    QC11 = 7
    QC12 = 8
    QC13 = 9
    QC14 = 10
    QC15 = 11
    QC16 = 12
    QC17 = 13
    QC18 = 14
    QC19 = 15
    QC20 = 16
    QC21 = 17
    HE1 = 18
    HE2 = 19
    HO1 = 20
    HO2 = 21
    HO3 = 22
    HO4 = 23
    HO5 = 24
    IW = 25
    QL = 26
    QC0 = 26
    HE0 = 27
    HO0 = 28
    B0 = 29
    QS = 30


class flt(Enum):
    DF1 = 1
    UF1 = 2
    DF2 = 4
    UF2 = 8
