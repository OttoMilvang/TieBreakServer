# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import sys
from commonmain import commonmain

# ==============================


class convert2jch(commonmain):

    def __init__(self):
        super().__init__()
        self.origin = "convert ver. 1.00"
        self.tournamentno = 0

    # read_command_line
    #   options:
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format
    #   -b = encoding
    #   -e = tournament-number
    #   -n = number-of-rounds
    #   -g = game-score
    #   -m = match-score
    #   -v = verbose and debug

    def read_command_line(self):
        self.read_common_command_line(True)

    def write_text_file(self, f, result, delimiter):
        pass

    def do_checker(self):
        self.core = None


# run program
jch = convert2jch()
code = jch.common_main()
sys.exit(code)
