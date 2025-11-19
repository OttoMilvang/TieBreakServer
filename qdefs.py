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
    C10 = 5
    C11 = 6
    C12 = 7
    C13 = 8
    C14 = 9
    C15 = 10
    C16 = 11
    C17 = 12
    C18 = 13
    C19 = 14
    C20 = 15
    C21 = 16
    E1 = 17
    E2 = 18
    S1 = 19
    S2 = 20
    S3 = 21
    S4 = 22
    S5 = 23
    IW = 24
    QL = 25
    C0 = 25
    S0 = 26
    E0 = 27
    B0 = 28
    QS = 29


class flt(Enum):
    DF1 = 1
    UF1 = 2
    DF2 = 4
    UF2 = 8
