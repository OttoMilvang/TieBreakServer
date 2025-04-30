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
import codecs
import helpers
from chessjson import chessjson
from trf2json import trf2json
from ts2json import ts2json
from tiebreak import tiebreak

# ==============================

def help():
    print('tiebreakchecker [options]')
    
    
# error
#   print error and exit

def error(code, txt):
    print('Error: ' + str(code) + ', ' + txt)
    print('tiebreakchecker [options]')
    sys.exit()

# read_command_line
#   options:
#   -i = input-file
#   -o = output-file
#   -f = file-format    
#   -e = event-number    
#   -d = delimiter
#   -s = split
#   -t = tie-break

def read_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--list", required=False, action='store_true',
        help="List file content")
    parser.add_argument("-s", "--split", required=False, action='store_true',
        help="List file content")
    parser.add_argument("-i", "--input-file", required=False,
        #default='C:\\temp\\ngpl23.trx',
        default='C:\\temp\\ngpl23-A-Langsjakk-FIDE.txt',
        #default='C:\\temp\\T6681.trfx',
        #default='C:\\temp\\nm_lag2022.trx',
        help="path to input file")
    parser.add_argument("-o", "--output-file", required=False,
        #default='C:\\temp\\out.json',
        default='-',
        help="path to output file")
    parser.add_argument("-f", "--file-format", required=False,
        default='TS',
        help="path to output file")
    parser.add_argument("-e", "--event-number", required=False,
        default='0',
        help="tournament number")
    parser.add_argument("-n", "--number-of-rounds", type=int,
        default=0,
        help="Nuber of rounds, overrides file value")
    parser.add_argument("-d", "--delimiter", required=False,
#        default=' ',
        help="Delimiter in output text" )
    parser.add_argument("-t", "--tie-break", required=False, nargs='*',
        default=['PTS', 'BH/C1', 'BH', 'ARO'],
        #default=['PTS', 'DE'],
        help="Tie break list" )

    args = vars(parser.parse_args())
    return args


def read_input_file(params):
    # Read input file
    match(params['file_format']):
        case 'JSON':
            tournament = chessjson()
            charset = "utf-8"
        case 'TRF':
            tournament = trf2json()
            charset = "latin1"
    
        case 'TS':
            tournament = ts2json()
            charset = "ascii"
        case _:
            error(503, "Error in file format: " + params['file_format'])
    
    
    
    if not 'input_file' in params:
        error(501, "Missing parameter --input-file")
    if not 'output_file' in params:
            error(501, "Missing parameter --output-file")
    f = io.open(params['input_file'], mode="r", encoding = charset)
    lines = f.read()
    f.close()
        
    if charset == "latin1" and lines[0] == '\xef' and lines[1] == '\xbb' and lines[2] == '\xbf' :
        lines = lines[3:]
    tournament.parse_file(lines, False)
    #json.dump(tournament.event, sys.stdout, indent=2)
    return(tournament)
        

def write_output_file(params, result):
    if params['output_file'] == '-':
        f = sys.stdout
    else:
        f = open(params['output_file'], 'w')
    if params['list'] or 'delimiter' in params and params['delimiter'] != None and params['delimiter'].upper() != 'JSON':
        tr = {'B': ' ', 'T': '\t', 'C': ',','S': ';'}
        if not 'delimiter' in params or params['delimiter'] == None:
            delimiter = ' '
        elif params['delimiter'].upper() in tr:
            delimiter = tr[params['delimiter'].upper()]
        else:
            delimiter = params['delimiter']
        
        f.write("Navn:     " + result['name'] + '\n')
        f.write("Sted:     " + result['site'] + '\n')
        f.write("Fra:      " + result['startDate'] + '\n')
        f.write("Til:      " + result['endDate'] + '\n')

        for gn in result['groups']:
            f.write('Gruppe: ' + gn['groupname'] + ': ' + str(gn['score']) + '\n')
    else:    
        json.dump(result, f, indent=2)
    if not params['output_file'] == '-':
        f.close()





def compute_one_group(result, tm, res, profiles, params):
    lim = params['number_of_rounds']
    tmcmps = { cmp['cid'] : cmp for cmp in tm['competitors'] }  
    group = {
        'groupname' : tm['name'],
        'pairs':  None,
        'emails': []
        }
    pairs = []
    score = {'W': 2, 'D':1, 'L':0}
    n = 0 
    s = 0
    for game in tm['gameList']:
        if (game['wResult'] == 'W' or game['wResult'] == 'D'  or game['wResult'] == 'L' ) and (game['bResult'] == 'W' or game['bResult'] == 'D'  or game['bResult'] == 'L' ) and (lim == 0 or game['round'] <= lim):
            #print(game)
            if game['white'] < game['black']:
                s += score[game['wResult']]
            else:
                s += score[game['bResult']]
            n += 1
    group['score'] = round(0.5 * float(s)/float(n)*100.0) / 100.0
    return(group)


def compute_all_groups(tournament, params, estart, estop):

    result = {
        'filetype': 'NGP/BGP report file',
        'version' : '1.0',
        'origin'  : ' ngpbgp.py',
        'published' : '',
        'name' : tournament.event['eventName'],
        'site' : tournament.event['eventInfo']['site'],
        'startDate' : tournament.event['eventInfo']['startDate'],
        'endDate' : tournament.event['eventInfo']['endDate'],
        'groups' : [],
    }
    profiles = { profile['id'] : profile for profile in tournament.event['profiles'] }  
    for evtno in range(estart, estop+1):
        # run tiebreak 
        #json.dump(tournament.__dict__, sys.stdout, indent=2)
        tournament.tournament_setvalue(evtno, 'numRounds', params['number_of_rounds'] )
        tm = tournament.get_tournament(evtno)
        result['groups'].append(compute_one_group(result, tm, tournament.event['status'], profiles, params))
    return(result)
    
   
def ngpbgp():
    # Read command line
    try:
        params = read_command_line()
        #json.dump(params, sys.stdout, indent=2)
        #sys.exit(0)
    except:
        error(501, "Bad command line")


    tournament = read_input_file(params)
    try:
        tournament = read_input_file(params)
    except:
        error(502, "Error when reading file: " + params['input_file'])


    if not 'event_number' in params:
        error(501, "Missing parameter --event-number")
    eventno = helpers.parse_int(params['event_number'])
    if eventno < 0 or eventno > len(tournament.event['tournaments']):
        error(501, "Invalid parameter --event-number")

    # Add command line parameters
    if 'individual_score' in params and params['individual_score'] != None:    
        for arg in params['individual_score']:
            tournament.parse_score_system('game', arg)
    if 'match_score' in params and params['match_score'] != None:    
        for arg in params['match_score']:   
            tournament.parse_score_system('match', arg)
    
    estart = eventno if eventno > 0 else 1
    estop = eventno if eventno > 0 else len(tournament.event['tournaments'])
                                                
    if tournament.get_status() == 0:
        result = compute_all_groups(tournament, params, estart, estop)
        write_output_file(params, result)
        
# tournament.export_trf(params)
 
# run program
ngpbgp()
