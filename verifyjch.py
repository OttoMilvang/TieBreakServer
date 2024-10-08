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
import jsonscheme
from chessjson import chessjson
from trf2json import trf2json
from ts2json import ts2json
from tiebreak import tiebreak
from decimal import *

# ==============================

def help():
    print('tiebreakchecker [options]')
    
    
# error
#   print error and exit

def error(code, txt):
    event = {
	    'filetype': 'Error',
	    'version': '1.0',
	    'origin': 'tiebreakchecker ver. 1.03',
	    'published': str(datetime.datetime.now())[0:19],
	    'status': {'code': 0, 'error': []}
    }
    event['status']['code'] = code
    event['status']['error'].append(txt)
    json.dump(event, sys.stdout, indent=2)
    if code >= 400:
        sys.exit()

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
#   -t = tie-break
#   -v = verbose and debug
#   -x = expirimental


def read_command_line():
    parser = argparse.ArgumentParser()
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
        default='1',
        help="tournament number")
    parser.add_argument("-n", "--number-of-rounds", type=int,
        default=0,
        help="Nuber of rounds, overrides file value")
    parser.add_argument("-p", "--pre-determined", required=False, action='store_true',
        help="Use rules for tournament with pre-determined pairing")
    parser.add_argument("-s", "--swiss", required=False, action='store_true',
        help="Use rules for swiss tournament")
    parser.add_argument("-g", "--game-score", required=False, nargs='*',
        help="Point system for matches, default W:2.0,D:1.0,L:0.0,Z:0,P:1.0,U:1.0" )
    parser.add_argument("-m", "--match-score", required=False, nargs='*',
        help="Point system for games, default W:1.0,D:0.5,L:0.0,Z:0,P:1.0,U:0.5" )
    parser.add_argument("-d", "--delimiter", required=False,
#        default=' ',
        help="Delimiter in output text" )
    parser.add_argument("-t", "--tie-break", required=False, nargs='*',
        default=['PTS', 'BH#C2-p'],
        #default=['PTS', 'DE'],
        help="Delimiter in output text" )
    parser.add_argument("-x", "--experimental", required=False, action='store_true',
        help="Add experimental stuff")
    parser.add_argument("-v", "--verbose", required=False, action='store_true',
        help="Verbose and debug")

    params = vars(parser.parse_args())
   
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

    # Set pre-determined or swiss
    params['is_rr'] = None
    if params['pre_determined']:
        params['is_rr'] = True
    if params['swiss']:
        params['is_rr'] = False
    
    return params



def read_input_file(params):
    # Read input file
    match(params['file_format']):
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
            error(503, "Error in file format: " + params['file_format'])
    
    
    
    if not 'input_file' in params:
        error(501, "Missing parameter --input-file")
    if not 'output_file' in params:
            error(501, "Missing parameter --output-file")
    if params['input_file'] == '-':
        sys.stdin.reconfigure(encoding = charset)
        f = sys.stdin
    else:
        f = io.open(params['input_file'], mode="r", encoding = charset)
    lines = f.read()
    f.close()
        
    if charset == "latin1" and lines[0] == '\xef' and lines[1] == '\xbb' and lines[2] == '\xbf' :
        lines = lines[3:]
    is_rr = None
    if params['pre_determined']:
        is_rr = True
    if params['swiss']:
        is_rr = False
    chessfile.parse_file(lines,  params['verbose'])
    
    return(chessfile )
        

def write_output_file(params, chessfile, tb):
    return
    if params['output_file'] == '-':
        f = sys.stdout
    else:
        f = open(params['output_file'], 'w')
    if params['check'] and tb != None:
        status = chessfile.event['status']
        result = chessfile.result
        event = {
	        'filetype': 'TieBreak',
	        'version': '1.0',
	        'origin': 'tiebreakchecker ver. 1.00',
	        'published': str(datetime.datetime.now())[0:19],
	        'status': status,
            'result': result
        }

        if 'delimiter' in params and params['delimiter'] != None and params['delimiter'].upper() != 'JSON':
            tr = {'B': ' ', 'T': '\t', 'C': ',','S': ';'}
            if params['delimiter'].upper() in tr:
                delimiter = tr[params['delimiter'].upper()]
            else:
                delimiter = params['delimiter']
            code = status['code'] if 'code' in status else 500
            check = result['check'] if 'check' in result else False
            f.write(str(code) + delimiter + str(check) + '\n')
            if code == 0:
                for competitor in result['competitors']:
                    line = str(competitor['startno']) + delimiter + str(competitor['rank'])
                    for val in competitor['tieBreak']:
                        if '.' in str(val):
                            line += delimiter + str(float(str(val)))
                        else:
                            line += delimiter + str(val)
                    f.write(line + '\n')
        else:    
            helpers.json_output(f, event)
    else:
        helpers.json_output(f, chessfile.event)
    if not params['output_file'] == '-':
        f.close()


# node - noe in tree
# name - name on structure
def parse_node(node, name, pre):
    #The definition must exist
    if name in jsonscheme.json_scheme:
        nodedef = jsonscheme.json_scheme[name]
    elif name != '' and name != 'int' and name != 'bool' and name != 'string':
        print(node)
        print(pre + '"' + name+'": missing')
        return
    else:
        return
    
    match(nodedef['type']):
        case 'string':
            pass
        case 'bool':
            pass
        case 'int':
            pass
        case 'object':
            #print(pre + name + ': object')
            for key in (nodedef['required'] if 'required' in nodedef else []):
                if key not in node:
                    print(pre + name + '[' + key + ']: reqired')
            for key, value in node.items():
                if key in nodedef['properties']:
                    nodearr = nodedef['properties'][key].split(':')
                    nodetype = nodearr[0] 
                    nodename = nodearr[1] if len(nodearr) == 2 else ''
                    if nodetype == 'object' and name != '':
                        parse_node(value, nodename, pre + '  ')
                    if nodetype == 'array':
                        for elem in value:
                            parse_node(elem, nodename, pre + '  ')
                else:
                    #print(|nodedef)
                    print(pre + name + '[' + key + ']: unknown')
        case _:
            print(pre + 'other')
             
    
    #parse_node(chessfile, 'event')                                


def compute_chessfile(chessfile, params): 
    parse_node(chessfile.event, 'event' , '')                                


def xcompute_chessfile(chessfile, params):                                 
    txt = ""
    pids = {elem['id']: elem for elem in chessfile.event['profiles'] }        
    tids = {elem['id']: elem for elem in chessfile.event['teams'] }        
    for tournament in chessfile.event['tournaments']:
        for competitor in tournament['competitors']:
            team = tids[competitor['teamId']]
            print(team['teamName'])
            for cplayer in competitor['cplayers']:
                p = pids[cplayer['profileId']]
                t = tids[cplayer['teamId']]
                print('', p['firstName'] + ' ' + p['lastName'] + ', ' + t['teamName']) 
    #return(tb)

   
def listjch():
    # Read command line
    try:
        params = read_command_line()
    except:
        error(501, "Bad command line")
    try:
        chessfile = read_input_file(params)
    except (RuntimeError, TypeError, NameError):
        if params['verbose']:
            raise
        error(502, "Error when reading file: " + params['input_file'])



    txt = compute_chessfile(chessfile, params)
    
    #try:
    write_output_file(params, chessfile, txt)
    if params['experimental']:
        chessfile.dumpresults()
    #except:
    #    error(503, "Error when writing file: " + params['output_file'])
    

        
# tournament.export_trf(params)
 
# run program
listjch()
