# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 10:41:41 2025

@author: Otto
"""
from enum import Enum

# Quality constants


class qdefs(Enum):
    C6 = 0
    C7 = 1
    N8 = 2
    C8 = 3
    C9 = 4
    MM = 5
    C10 = 6
    C11 = 7
    C12 = 8
    C13 = 9
    C14 = 10
    C15 = 11
    C16 = 12
    C17 = 13
    C18 = 14
    C19 = 15
    C20 = 16
    C21 = 17
    E1 = 18
    E2 = 19
    S1 = 20
    S2 = 21
    S3 = 22
    S4 = 23
    S5 = 24
    IW = 25
    QL = 26
    C0 = 26
    S0 = 27
    E0 = 28
    B0 = 29
    QS = 30


class flt(Enum):
    DF1 = 1
    UF1 = 2
    DF2 = 4
    UF2 = 8
