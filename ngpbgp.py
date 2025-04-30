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
        f.write("Spillere: " + str(len(result['players'])) + '\n')

        for gn, cnt in result['groups'].items():
            f.write(gn + ':      ' + str(cnt) + '\n')
        if not params['list']:
            for player in result['players']:
                d = ""
                line = ""
                for key, val in player.items():
                    line = line + d + str(val)
                    d = delimiter
                f.write(line + '\n')
    else:    
        json.dump(result, f, indent=2)
    if not params['output_file'] == '-':
        f.close()




def compute_tiebreaks(tournament, eventno, params):                                 
    
    # run tiebreak 
    #json.dump(tournament.__dict__, sys.stdout, indent=2)

    if tournament.get_status() == 0:
        tb  = tiebreak(tournament, eventno, -1, params)
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
        #with open('C:\\temp\\tbcmps.json', 'w') as f:
            #json.dump(tm['teamSection'], f, indent=2)
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
    return(tb)



def compute_one_group(result, tm, res, profiles, lookup, params):
    tmcmps = tm['playerSection']['competitors']
    groupname =   tm['name']
    players = []
    for competitor in res['competitors']:
        startno = competitor['startno']
        tmcmp = tmcmps[startno-1]
        #print(tmcmp)
        profile = profiles[lookup[tmcmp['profileId']]]
        gn = profile['other']['group'].strip().capitalize()
        if gn == '' or not params['split']:
            gn = groupname[0:3].capitalize()
        player = {
            'group' : gn,
            'rank' : competitor['rank'],
            'id' : profile['localId'], 
            'firstName' : profile['firstName'],
            'lastName' : profile['lastName'],
            'clubName' : profile['clubName'],
            'birth' : profile['birth'],
            'tiebreaks' : []
        }
        for tb in competitor['calculations']:
            player['tiebreaks'].append(tb['val']) 
        players.append(player)
    players = sorted(players, key=lambda p: (p['rank'])) 
    groups = {}
    for player in players:
        gn = player['group']
        if gn not in groups:
            groups[gn] = []
            player['rank'] = 1
        else: 
            if player['tiebreaks'] == groups[gn][-1]['tiebreaks']:
                player['rank'] = groups[gn][-1]['rank']
            else:
                player['rank'] = len(groups[gn]) + 1
        groups[gn].append(player)
    for gn, group in groups.items():
        result['groups'][gn] = len(group)
        for player in group:
            result['players'].append(player)                        



def compute_all_groups(tournament, params, estart, estop):
    profiles = tournament.event['profiles']   
    lookup = {}
    for nprofile in range(0, len(profiles)): 
        lookup[profiles[nprofile]['id']] = nprofile           

    result = {
        'filetype': 'NGP/BGP report file',
        'version' : '1.0',
        'origin'  : ' ngpbgp.py',
        'published' : '',
        'name' : tournament.event['eventName'],
        'site' : tournament.event['eventInfo']['site'],
        'startDate' : tournament.event['eventInfo']['startDate'],
        'endDate' : tournament.event['eventInfo']['endDate'],
        'rankOrder' : params['tie_break'],
        'groups' : {},
        'players' : []
    }
    for evtno in range(estart, estop+1):
        # run tiebreak 
        #json.dump(tournament.__dict__, sys.stdout, indent=2)
        tournament.tournament_setvalue(evtno, 'numRounds', params['number_of_rounds'] )
        tm = tournament.get_tournament(evtno)
        tb = compute_tiebreaks(tournament, evtno, params)
        tournament.event['status']['tiebreaks'] = tb.tiebreaks
        compute_one_group(result, tm, tournament.event['status'],profiles, lookup, params)
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
