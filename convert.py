# -*- coding: utf-8 -*-
# noqa
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Aug  7 16:48:53 2023
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

# ==============================


class convert2jch(commonmain):

    def __init__(self):
        super().__init__()
        self.origin = 'convert ver. 1.00'
        self.tournamentno = 0


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
        self.read_common_command_line(True)


    def write_text_file(self, f, result, delimiter):                        
        pass
    
    def do_checker(self):
        self.core = None
        
 
# run program
jch = convert2jch()
code = jch.common_main()
sys.exit(code)
