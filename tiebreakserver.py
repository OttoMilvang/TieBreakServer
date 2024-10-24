#! C:/Program Files/Python313/python.exe
# -*- coding: utf-8 -*-
# noqa
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Oct 16 13:46:19 2024
@author: Otto Milvang, sjakk@milvang.no
"""
import argparse
import json
import io
import sys
import datetime
import codecs
import helpers
from commonmain import commonmain
from chessjson import chessjson
from tiebreak import tiebreak

# ==============================


class tiebreakserver(commonmain):

    def __init__(self):
        super().__init__()
        self.origin = 'tiebreakserver ver. 1.00'
        self.eventno = 0


    # read_command_line
    #   options:
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format    
    #   -e = event-number    
    #   -n = number-of-rounds
    #   -g = game-score
    #   -m = match-score
    #   -v = verbose and debug


    def read_command_line(self):
        self.read_common_server(True, True)


    def write_text_file(self, f, result, delimiter):                        
        pass
    
    def do_checker(self):
        result = None
        params = self.params
        if params['check']:
            self.filetype = 'tiebreak'
        chessfile = self.chessfile
        if chessfile.get_status() == 0:
            if self.eventno > 0:
                tb  = tiebreak(chessfile, self.eventno, params['number_of_rounds'], params)
                tb.compute_tiebreaks(chessfile, self.eventno, params) 
            else: 
                tb = tiebreak(chessfile, self.eventno, params['number_of_rounds'], params)
        self.core = tb
         
 
# run program
jch = tiebreakserver()
code = jch.common_main()
sys.exit(code)
