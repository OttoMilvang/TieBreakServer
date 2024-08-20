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
from chessjson import chessjson
from trf2json import trf2json
from ts2json import ts2json
from tiebreak import tiebreak

# ==============================

class commonmain:

    # constructor function    
    def __init__(self):
         self.parser = argparse.ArgumentParser()
         self.params = None
         self.filetype = 'chessjson'
         self.origin = 'checker, version 1.00'
         self.eventno = 1

    def printhelp(self):
        print('checker [options]')
    
    
    # error
    #   print error and exit
    
    def error(self, code, txt):
        event = {
    	    'filetype': 'Error',
    	    'version': '1.0',
    	    'origin': self.origin,
    	    'published': str(datetime.datetime.now())[0:19],
    	    'status': {'code': 0, 'error': []}
        }
        event['status']['code'] = code
        event['status']['error'].append(txt)
        json.dump(event, sys.stdout, indent=2)
        if code >= 400:
            sys.exit(code)

    # read_command_line
    #   options:
    #   -@ = program
    #   -c = check
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format    
    #   -e = event-number    
    #   -n = number-of-rounds
    #   -g = game-score
    #   -m = match-score
    #   -d = delimiter
    #   -v = verbose and debug
    #   -x = expirimental


    def read_common_command_line(self, strict):
        parser = self.parser
        parser.add_argument("-c", "--check", required=False, action='store_true',
            help="Shall we add checkflag to json file")
        parser.add_argument("-i", "--input-file", required=False,
            #default='C:\\temp\\ngpl23.trx',
            #default='C:\\temp\\ngpl23-A-Langsjakk-FIDE.txt',
            #default='C:\\temp\\T6681.trfx',
            default='-',
            help="path to input file")
        parser.add_argument("-o", "--output-file", required=False,
            #default='C:\\temp\\out.json',
            default='-',
            help="path to output file")
        parser.add_argument("-f", "--file-format", required=False,
            #default='TS',
            default='TRF',
            help="path to output file")
        parser.add_argument("-e", "--event-number", required=False,
            default= str(self.eventno),
            help="tournament number")
        parser.add_argument("-n", "--number-of-rounds", type=int,
            default=-1,
            help="Nuber of rounds, overrides file value")
        parser.add_argument("-g", "--game-score", required=False, nargs='*',
            help="Point system for matches, default W:2.0,D:1.0,L:0.0,Z:0,P:1.0,U:1.0" )
        parser.add_argument("-m", "--match-score", required=False, nargs='*',
            help="Point system for games, default W:1.0,D:0.5,L:0.0,Z:0,P:1.0,U:0.5" )
        parser.add_argument("-d", "--delimiter", required=False,
    #        default=' ',
            help="Delimiter in output text" )
        parser.add_argument("-x", "--experimental", required=False, action='store_true',
            help="Add experimental stuff")
        parser.add_argument("-v", "--verbose", required=False, action='store_true',
            help="Verbose and debug")

        if strict:   
            self.params = params = vars(parser.parse_args())
        else:
            self.params = params = vars(parser.parse_known_args())
       
        # Parse game-score and match-score
        for scoretype in ['game', 'match']:
            if scoretype + '_score' in params and params[scoretype + '_score'] != None:
                scoresystem = {}
                for arg in params[scoretype +  '_score']:
                    for param in arg.split(','):
                        param = param.replace('=', ':')
                        args = param.split(':')
                        scoresystem[args[0]] = helpers.parse_float(args[1])
                params[scoretype + '_score'] = scoresystem
    
        
        return params



    def read_input_file(self):
        # Read input file
        match(self.params['file_format']):
            case 'JSON':
                chessfile = chessjson()
                charset = "utf-8"
            case 'TRF':
                chessfile = trf2json()
                charset = "latin1"
        
            case 'TS':
                chessfile = ts2json()
                charset = "ascii"
            case _:
                error(503, "Error in file format: " + self.params['file_format'])
        
        
        
        if not 'input_file' in self.params:
            error(501, "Missing parameter --input-file")
        if not 'output_file' in self.params:
                error(501, "Missing parameter --output-file")
        if self.params['input_file'] == '-':
            sys.stdin.reconfigure(encoding = charset)
            f = sys.stdin
        else:
            f = io.open(self.params['input_file'], mode="r", encoding = charset)
        lines = f.read()
        f.close()
            
        if charset == "latin1" and lines[0] == '\xef' and lines[1] == '\xbb' and lines[2] == '\xbf' :
            lines = lines[3:]
        chessfile.parse_file(lines,  self.params['verbose'])
        self.chessfile = chessfile
            
    
    def write_output_file(self):
        params = self.params
        chessfile = self.chessfile
        status = chessfile.event['status']
        code = status['code'] if 'code' in status else 500
        if code == 0 and hasattr(chessfile, 'result'):
            result = chessfile.result
            check = result['check'] if 'check' in result else False
            code = 0 if check else 1
    
        if params['output_file'] == '-':
            f = sys.stdout
        else:
            f = open(params['output_file'], 'w')

        if params['check'] and self.core != None:
            event = {
    	        'filetype': self.filetype,
    	        'version': '1.0',
    	        'origin': self.origin,
    	        'published': str(datetime.datetime.now())[0:19],
    	        'status': status,
                'tiebreakResult': result
            }
    
    
            if 'delimiter' in params and params['delimiter'] != None and params['delimiter'].upper() != 'JSON':
                printcheckstatus = 1 if params['delimiter'][0] == '@' else 0
                delimiter = params['delimiter'][printcheckstatus:]
                tr = {'B': ' ', 'T': '\t', 'C': ',','S': ';'}
                if delimiter.upper() in tr:
                    delimiter = tr[delimiter.upper()]
                if printcheckstatus:
                    f.write(str(code) + (delimiter + str(check) if len(delimiter) > 0  else '')  + '\n')
                if code == 0 or code == 1 and len(delimiter) > 0:
                    self.write_text_file(f, result, delimiter)                    
            else:    
                helpers.json_output(f, event)
        else:
            helpers.json_output(f, chessfile.event)
        if not params['output_file'] == '-':
            f.close()
        return code
    
       
    def common_main(self):
        # Read command line
        try:
            self.read_command_line()
        except:
            raise
            self.error(501, "Bad command line")
        params = self.params
        try:
            self.read_input_file()
        except (RuntimeError, TypeError, NameError):
            if params['verbose']:
                raise
            self.error(502, "Error when reading file: " + params['input_file'])
    
    
        if not 'event_number' in params:
            self.error(501, "Missing parameter --event-number")
        self.eventno = helpers.parse_int(params['event_number'])
        if self.eventno < 0 or self.eventno > len(self.chessfile.event['tournaments']):
            self.error(501, "Invalid parameter --event-number")
    
        # Add command line parameters
        for score in ['game', 'match']:
            if score + '_score' in params and params[score +'_score'] != None:    
                for arg in params[score +  '_score']:
                    self.chessfile.parse_score_system(score, arg)

        self.do_checker()        
        
        try:
            code = self.write_output_file()
            if params['experimental']:
                self.chessfile.dumpresults()
        except:
            if params['verbose']:
                raise
            self.error(503, "Error when writing file: " + params['output_file'])
        return(code) 

        
