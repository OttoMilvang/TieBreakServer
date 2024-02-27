# -*- coding: utf-8 -*-
# noqa
"""
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
#   -c = check
#   -i = input-file
#   -o = output-file
#   -f = file-format    
#   -e = event-number    
#   -n = number-of-rounds
#   -g = game-score
#   -m = match-score
#   -d = delimiter
#   -t = tie-break

def read_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check", required=False, action='store_true',
        help="Shall we add checkflag to json file")
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
        #default='TS',
        default='TRF',
        help="path to output file")
    parser.add_argument("-e", "--event-number", required=False,
        default='1',
        help="tournament number")
    parser.add_argument("-n", "--number-of-rounds", type=int,
        default=0,
        help="Nuber of rounds, overrides file value")
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
    tournament.parse_file(lines)

    return(tournament)
        

def write_output_file(params, tournament, tb):
    if params['output_file'] == '-':
        f = sys.stdout
    else:
        f = open(params['output_file'], 'w')
    if params['check']:
        tournament.event['status']['tiebreaks'] = tb.tiebreaks 
        res = tournament.event['status']
        if 'delimiter' in params and params['delimiter'] != None and params['delimiter'].upper() != 'JSON':
            tr = {'B': ' ', 'T': '\t', 'C': ',','S': ';'}
            if params['delimiter'].upper() in tr:
                delimiter = tr[params['delimiter'].upper()]
            else:
                delimiter = params['delimiter']
            code = res['code'] if 'code' in res else 500
            check = res['check'] if 'check' in res else False
            print(str(code) + delimiter + str(check))
            if code == 0:
                for competitor in res['competitors']:
                    line = str(competitor['startno']) + delimiter + str(competitor['rank'])
                    for val in competitor['tieBreak']:
                        line += delimiter + str(val)
                    print (line)
        else:    
            json.dump(res, f, indent=2)
    else:
        json.dump(tournament.event, f, indent=2)
    if not params['output_file'] == '-':
        f.close()


def compute_tiebreaks(tournament, tb, eventno, params):                                 
    
    # run tiebreak 
    #json.dump(tournament.__dict__, sys.stdout, indent=2)

    if tournament.get_status() == 0:
        tblist = params['tie_break']
        for pos in range (0, len(tblist)):
            mytb = tb.parse_tiebreak(pos+1, tblist[pos])
            tb.compute_tiebreak(mytb)
            #json.dump(tb.__dict__, sys.stdout, indent=2)
        #print()
        for i in range(0,len(tb.rankorder)):
            t = tb.rankorder[i]
            #print(t['id'], t['rank'], t['tieBreak'])
    if tournament.get_status() == 0:
        tm = tournament.get_tournament(eventno)
        tm['rankOrder'] = tb.tiebreaks;
        if 'teamTournament' in tm and tm['teamTournament']:
            jsoncmps = tm['teamSection']['competitors']
        else:
            jsoncmps = tm['playerSection']['competitors']
        #with open('C:\\temp\\tm.json', 'w') as f:
        #    json.dump(tm, f, indent=2)
        with open('C:\\temp\\tbcmps.json', 'w') as f:
            json.dump(tm['teamSection'], f, indent=2)
        correct = True
        competitors = []
        for cmp in jsoncmps:
            competitor = {}
            competitor['startno'] = startno = cmp['cid']
            correct = correct and cmp['rank'] == tb.cmps[startno]['rank']
            competitor['rank'] = cmp['rank'] = tb.cmps[startno]['rank']
            if tb.isteam:
                competitor['boardPoints'] = tb.cmps[startno]['tbval']['gpoints_' + 'bp']
            competitor['calculations'] = cmp['calculations'] = tb.cmps[startno]['calculations']
            competitor['tieBreak'] = cmp['tieBreak'] = tb.cmps[startno]['tieBreak']
            competitors.append(competitor)
            #print(startno, cmp['rank'], cmp['tieBreak'])
        tournament.event['status']['check'] = correct
        tournament.event['status']['competitors'] = competitors
    #return(tb)

   
def tiebreakchecker():
    # Read command line
    try:
        params = read_command_line()
    except:
        error(501, "Bad command line")

    #try:
    tournament = read_input_file(params)
    #except:
    #    error(502, "Error when reading file: " + params['input_file'])


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
    

    tb = None
    if tournament.get_status() == 0:
        if eventno > 0:
            tournament.tournament_setvalue(eventno, 'numRounds', params['number_of_rounds'] )
            tb  = tiebreak(tournament, eventno)
            compute_tiebreaks(tournament, tb, eventno, params)
    

    #try:
    write_output_file(params, tournament, tb)
    #except:
    #    error(503, "Error when writing file: " + params['output_file'])
    

        
# tournament.export_trf(params)
 
# run program
tiebreakchecker()
