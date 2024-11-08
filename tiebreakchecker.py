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
from trf2json import trf2json
from ts2json import ts2json
from tiebreak import tiebreak

# ==============================


class tiebreakchecker(commonmain):

    def __init__(self):
        super().__init__()
        self.origin = 'tiebreakchecker ver. 1.04'
     

    # read_command_line
    #   options:
    #   -c = check
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format    
    #   -e = event-number    
    #   -n = number-of-rounds
    #   -p = use rules for tournament with pre-determined pairing (Round Robin)
    #   -s = use rules for swiss tournament
    #   -g = game-score
    #   -m = match-score
    #   -d = delimiter
    #   -r = sort on rank order
    #   -u = set rating for unrated players
    #   -t = tie-break
    #   -v = verbose and debug
    #   -x = expirimental
    
    
    def read_command_line(self):
        self.parser.add_argument("-p", "--pre-determined", required=False, action='store_true',
            help="Use rules for tournament with pre-determined pairing")
        self.parser.add_argument("-s", "--swiss", required=False, action='store_true',
            help="Use rules for swiss tournament")
        self.parser.add_argument("-r", "--rank", required=False, action='store_true',
            help="Sort on rank order")
        self.parser.add_argument("-u", "--unrated", required=False,
            default=0,
            help="rating for unrated players")
        self.parser.add_argument("-t", "--tie-break", required=False, nargs='*',
            default=['PTS', 'BH/C2/p'],
            #default=['PTS', 'DE'],
            help="Delimiter in output text" )
        self.read_common_command_line(True)
       
        # Parse game-score and match-score
        for scoretype in ['game', 'match']:
            if scoretype + '_score' in self.params and self.params[scoretype + '_score'] != None:
                scoresystem = {}
                for arg in self.params[scoretype +  '_score']:
                    for param in arg.split(','):
                        param = param.replace('=', ':')
                        args = param.split(':')
                        scoresystem[args[0]] = helpers.parse_float(args[1])
                self.params[scoretype + '_score'] = scoresystem
    
        # Set pre-determined or swiss
        self.params['is_rr'] = None
        if self.params['pre_determined']:
            self.params['is_rr'] = True
        if self.params['swiss']:
            self.params['is_rr'] = False
        
    
    
          

    def write_text_file(self, f, result, delimiter):                        
        if self.params['rank']:
            sortorder = sorted(result['competitors'], key=lambda cmp: (cmp['rank'], cmp['cid']))
            header = ['Rank', 'StartNo']
            field = ['rank', 'cid']
        else:
            sortorder = result['competitors']
            header = ['StartNo', 'Rank']
            field = ['cid', 'rank']
        line = header[0] + delimiter + header[1]
        for arg in self.params['tie_break']:
            line += delimiter + arg
        f.write(line + '\n')
        for competitor in sortorder:
            line = str(competitor[field[0]]) + delimiter + str(competitor[field[1]])
            for val in competitor['tiebreakScore']:
                if '.' in str(val):
                    line += delimiter + str(val)
                else:
                    line += delimiter + str(val)
            f.write(line + '\n')
    
    
    
    
 
  
    def do_checker(self):
        result = None
        params = self.params
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
        
 
# run program
tbc = tiebreakchecker()
code = tbc.common_main()
sys.exit(code)
