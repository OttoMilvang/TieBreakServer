#! C:/Program Files/Python313/python.exe
# -*- coding: utf-8 -*-
# noqa
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Oct 25 08:16:13 2024
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
"""
Request:
{
    "filetype": "convert request" | "tiebreak request" ,
    "version": "1.0",
    "origin": "<Free text>",
    "published": "<date on format 2018-08-14 05:07:44>",
    "command": {
        "service" : "convert" | tiebreak,
        "filename" : "<original file name>",
        "filetype": "TRF" | "TS" | < other known format >,
        "content": ["<lines with base 64 encoded file>"],
        "tournamentno": <0 or tournamentno to convert>,
        "number_of_rounds": <int>, 
        // parameters for tiebreaks
            "tiebreaks" : [string list],
            "tournamenttype" : "" | "d" | "p" | "s"
        }
   
    }
}

Response:
{
    "filetype": "convert response" | "tiebreak response",
    "version": "1.0",
    "origin": "chessserver ver. 1.04",
    "published": "2024-10-01 14:32:16",
    "status": {
        "code": 0,
        "error": []
    },
    "convertResult": {
        <Json chess file>
    }
    "tiebreakResult": {
        "check": false,
        "tiebreaks": [ … ],
        "competitors": [ {
            "cid": <cid>,
            "rank": <rank>,
            "tiebreakScore": [ … ],
            "boardPoints": { … },
            "tiebreakDetails": [{ … }, … ]
    }
}


"""


class chessserver(commonmain):

    def __init__(self):
        super().__init__()
        self.origin = 'chessserver ver. 1.00'
        self.tournamentno = 0

    def read_command_line(self):
        self.read_common_server(True)


    def write_text_file(self, f, result, delimiter):                        
        pass
    
    def do_checker(self):
        params = self.params
        self.core = None
        match (params['service']):
            case 'convert':
               self.core = None
            case 'tiebreak':
                result = None
                if params['check']:
                    self.filetype = 'tiebreak'
                chessfile = self.chessfile
                if chessfile.get_status() == 0:
                    if self.tournamentno > 0:
                        tb  = tiebreak(chessfile, self.tournamentno, params['number_of_rounds'], params)
                        tb.compute_tiebreaks(chessfile, self.tournamentno, params) 
                    else: 
                        tb = tiebreak(chessfile, self.tournamentno, params['number_of_rounds'], params)
                self.core = tb
            case _:
                self.core = None


         
 
# run program
jch = chessserver()
code = jch.common_main()
sys.exit(code)
