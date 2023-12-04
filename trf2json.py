# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023

@author: otto
"""

import sys
import json
import argparse
import time
import chessjson
import berger
import helpers


class trf2json(chessjson.chessjson):

    # Read trf into a JSON for Chess data structure
    
   # constructor function    
    def __init__(self):
        super().__init__()
        self.event['origin'] = 'trf2json ver. 1.00'
        self.event['ratingLists'] = [{'listName': 'TRF'}]
        self.scorelist = []
 


# ==============================
#
# Read TRF file

    def parse_file(self, alines):
        now = time.time()
        self.event['published'] = time.strftime('%Y-%m %d %H:%M:%S', time.localtime(now))
        self.event['tournaments'].append({
            'tournamentNo': 1,
            'type': 'Tournament',
            'ratingList': 'TRF',
            'numRounds': 0,
            'currentRound': 0,
            'teamTournament': False,
            'rankOrder': [{
                'order': 1,
                'name': 'PTS'
                }],
            'playerSection': {
                'type': 'PlayerSection',
                'competitors': [],
                'results': [],
                'scoreSystem': 'game'
                },
           'teamSection': {
               'type': 'TeamSection',
               'competitors': [],
               'results': [],
               'scoreSystem': 'match'
               }        
            });
        lines = alines.replace('\r', '\n').split('\n')
        tournament = self.get_tournament(1)
        lineno = 0
        for line in lines:
            lineno += 1
            if True:
                trfkey = line[0:3];
                trfvalue =line[4:]; 
                match trfkey: # noqa
                    case '001': 
                        self.parse_trf_player(tournament, tournament['playerSection'], line)
                    case '012': 
                        self.parse_trf_info('fullName', trfvalue)
                    case '013': 
                        self.parse_trf_team(tournament, tournament['teamSection'], line)
                        tournament['teamTorunament'] = True
                    case '022': 
                        self.parse_trf_info('site', trfvalue)
                    case '032':
                        self.parse_trf_info('federation', trfvalue)
                    case '042':
                        self.parse_trf_info('startDate', helpers.parse_date(trfvalue))
                    case '052':
                        self.parse_trf_info('endDate', helpers.parse_date(trfvalue))
                    case '062':
                        numplayers = int(trfvalue)
                    case '072':
                        numrated = int(trfvalue)
                    case '082':
                        numteams = int(trfvalue)
                    case '092':
                        tournament['tournamentType'] = trfvalue
                    case '102':
                        self.parse_trf_arbiter(True, line)
                    case '112': 
                        self.parse_trf_arbiter(False, line)
                    case '122': 
                        tournament['timeControl'] = {'description:': trfvalue}
                    case '132':
                        self.parse_trf_dates(tournament, line)
                    case 'XXR':
                        self.parse_trf_absent(tournament, line)
                    case 'XXS':
                        self.parse_trf_points(tournament, line)
                    case 'XXC':
                        self.parse_trf_configuration(tournament, line)
                    case 'XXA':
                        self.parse_trf_accellerated(tournament, line)
                        tt = tournament['tournamentType'].upper()
            #except:
            #    print("Error in trffile, line " + str(lineno) + ", " + line)
                
            #    self.put_status(401, "Error in trffile, line " + str(lineno) + ", " + line)

 
        if tournament['teamTournament']:
            self.prepare_team_section(tournament)
            self.update_board_number(tournament, tournament['teamSection'])
        else:
            self.update_board_number(tournament, tournament['playerSection'])
            
        return        

    def update_board_number(self, tournament, competition):
        # is the tournament RR?
        tt = tournament['tournamentType'].upper()
        numcomp = len(competition['competitors'])
        numrounds = tournament['numRounds']
        rr = False
        if tt.find('SWISS') >= 0:
            rr = False
        elif tt.find('RR') >= 0 or tt.find('ROBIN') >= 0 or tt.find('BERGER') >= 0: 
            rr = True
        elif numcomp == numrounds + 1 or numcomp == numrounds:
            rr = True
        elif numcomp == (numrounds + 1)*2 or numcomp == numrounds * 2:
            rr = True

        # sort results in rounds
        results = {}
        score = helpers.solve_pointsystem(self.scorelist)
        scorename = competition['scoreSystem']
        scoresystem = self.get_scoresystem(self.event['scoreLists'], scorename)
        if score != None and 'P' in score :
            pval = score['P']          
        elif 'P' in scoresystem:
            pval = scoresystem['P']
        elif rr:
            pval = 'L'
        else:
            pval = 'W'
        if score != None and 'U' in score:
            uval = score['U']
        else:
            uval = 'D'

        for result in competition['results']:
            rnd = result['round']
            if not rnd in results:
                results[rnd] = []
            results[rnd].append(result)
        points = [0.0] * (numcomp+1)         
        
        # update each round
        for rnd, roundresults in results.items():
            if rr:
                self.update_rr_board_number(roundresults, numcomp, points)
            else:
                self.update_swiss_board_number(roundresults, numcomp, points)
            for  result in roundresults:
                if result['wResult'] == 'P':
                    result['wResult'] = pval
                if result['wResult'] == 'U':
                    result['wResult'] = uval
                points[result['white']] += self.get_score(scorename, result, 'white')
                if 'bResult' in result:
                    points[result['black']] += self.get_score(scorename, result, 'black')
                
                
    def update_rr_board_number(self, roundresults, numcomp, points):
        rr = berger.bergertables(numcomp)
        n = rr['players']
        cround = 0
        for result in roundresults:
            w = result['white']
            b = result['black'] if 'black' in result and result['black'] > 0 else n
            [rnd, pair] = berger.lookupbergerpairing(rr, w, b)
            rnd = rnd if rnd < n else rnd - n + 1
            if cround > 0 and cround != rnd:
                return self.update_swiss_board_number(roundresults, numcomp, points) # not rr
            cround = rnd 
            result['board'] = pair
        return

    def update_swiss_board_number(self, roundresults, numcomp, points):
        for result in roundresults:
            w = result['white']
            b = result['black'] if 'black' in result and result['black'] > 0 else 0
            c = 2 if b > 0 else 1
            result['rank'] = {
                'c': c, 
                'w': points[w], 
                'b': points[b], 
                'r': min(w,b) if b > 0 else w
            }
        
        roundresults = sorted(roundresults, key=lambda result: 
                              (-result['rank']['c'], 
                               -result['rank']['w'], 
                               -result['rank']['b'], 
                               result['rank']['r']))
        for i in range (0, len(roundresults)):
            roundresults[i]['board'] = i+1
            roundresults[i].pop('rank')

        
# ==============================
#
# Read TRF line

    def parse_trf_game(self, section, startno, currentround, sgame, score):
        if len(sgame.strip()) == 0: 
            return None
        opponent = helpers.parse_int(sgame[0:4])
        color = sgame[5].lower()
        if color != 'w' and color != 'b' and color != '-'and color != ' ':
            color = ' ';
        result = sgame[7].upper()
        points = 'U'
        played = False
        rated = False
    
        match result:  # noqa
            case '1':
                points = 'W'
                played = True
                rated = True
            case '=':
                points = 'D'
                played = True
                rated = True
            case '0':
                points = 'L'
                played = True
                rated = True
            case 'U':
                points = 'P'
                played = True
                rated = False
            case 'W':
                points = 'W'
                played = True;
                rated = False;
            case 'D':
                points = 'D'
                played = True;
                rated = False;
            case 'L':
                points = 'L'
                played = True;
                rated = False;
            case '?':
                points = 'U'
                played = True;
                rated = False;
            case '+' | 'F':
                points = 'W';
                played = False;
                rated = False;
            case 'H':
                points = 'D';
                played = False;
                rated = False;
            case '-' | 'Z' | ' ':
                points = 'Z';
                played = False;
                rated = False;
        
        if color == 'b':
            white = opponent
            black = startno
        else:
            white = startno
            black = opponent
        #game = None
        #for item in section['results']:
        #    if item['round'] == currentround and item['white'] == white and item['black'] == black:
        #       game = item                  
        #if game == None:
            #self.numResults += 1
        score[points] = (score[points] if points in score else 0) + 1
        game = {
            'id': 0,
            'round': currentround,
            'white': white,
            'black': black,
            'played': played,
            'rated': rated
            }
            #section['results'].append(game)
        if color == 'b':
            game['bResult'] = points
        else:
            game['wResult'] = points
        self.append_result(section['results'], game)
        return game
    
    
    
    
    def parse_trf_player(self, tournament, section, line):
    #    print("parse")
        fideName = line[14:47].rstrip()
        names = fideName.split(',')
        while len(names) < 2:
            names.append('')
        ftitle = title = line[10:13].strip()
        match title: # noqa
            case 'g': 
                ftitle = 'GM'
            case 'm': 
                ftitle = 'IM'
            case 'f': 
                ftitle = 'FM'
            case 'c': 
                ftitle = 'CM'
            case 'wg': 
                ftitle = 'WGM'
            case 'wm': 
                ftitle = 'WIM'
            case 'wf': 
                ftitle = 'WFM'
            case 'wc': 
                ftitle = 'WCM'

        profile = {
            'id': 0,
            'lastName': names[0].strip(),
            'firstName': names[1].strip(),
            'sex': line[9:10],
            'birth': helpers.parse_date(line[69:79]),
            'federation': line[53:56].strip(),
            'fideId': helpers.parse_int(line[57:68]),
            'fideName': fideName,
            'rating': [helpers.parse_int(line[48:52])],
            'fideTitle': ftitle
            }
        self.append_profile(profile)
    
        startno = helpers.parse_int(line[4:8])
        gamePoints = helpers.parse_float(line[80:84])
        competitor = {
            'cid': startno,
            'profileId': self.numProfiles,
            'present': startno > 0,
            'gamePoints': gamePoints,
            'rank': helpers.parse_int(line[85:89]),
            'rating': helpers.parse_int(line[48:52])
            }
        section['competitors'].append(competitor)
        score = {
            'sum': gamePoints
            }
        self.scorelist.append(score)
        linelen = len(line);
        currentround = 0
        lastplayed = 0
        lastpaired = 0
        for i in range(99, linelen, 10):
            currentround += 1
            game = self.parse_trf_game(section, startno, currentround, line[81 + 10 * currentround: 81 + 10 * currentround + 8], score)
            if game != None:
                if game['played'] and currentround > lastplayed:
                    lastplayed = currentround
                    if game['white'] > 0 and game['black'] > 0 and currentround > lastpaired:
                        lastpaired = currentround
        if lastplayed > tournament['numRounds']:
            tournament['numRounds'] = lastplayed
        if lastpaired > tournament['currentRound']:
            tournament['currentRound'] = lastpaired       
        return 1

    def parse_trf_team(self, tournament, section, line):
        linelen = len(line);
        teamname = line[4:36].rstrip()
        team = {
            'id': 0,
            'teamName': teamname,
            'players':[]
        }
        teamid = self.append_team(team, 0)
        competitor = {
            'cid': self.numTeams,
            'teamId': teamid,
            'present': True,
            'matchPoints': 0.0,
            'rank': 1,
            'tieBreak': [],
            'cplayers': []
            }
        cplayers = tournament['playerSection']['competitors']
        section['competitors'].append(competitor)
        for i in range(39, linelen, 5):
            pid = helpers.parse_int(line[i-3:i+1])
            competitor['cplayers'].append(pid)
            team['players'].append(cplayers[pid-1]['profileId'])
            cplayers[pid-1]['cteam'] = competitor['cid']
            

    def parse_trf_info(self, info, value):
        self.event['eventInfo'][info] = value
        return 1
    
    def parse_trf_dates(self, tournament, line):
        linelen = len(line);
        
        tournament['rounds'] = []
        currentround = 0
        for j in range(99, linelen, 10):
            currentround += 1
            date = line[81 + 10 * currentround: 81 + 10 * currentround + 8]
            tournament['rounds'].append( {'round': currentround,
                                         'startTime': helpers.parse_date(date)
                                         })
        return
    
    
    def parse_trf_arbiter(self, is_ca, line):
        global numProfiles
        linelen = len(line.rstrip())
        if (linelen == 3):
            return
        fideid = 0;
        if (linelen == 48):
            fideid = int(line[37:48])
            line = line[4:37].rstrip()
        else:
            line = line[4:].rstrip()
        nameparts = line.split(' ')
        sname = 0
        otitle = ''
        ename = len(nameparts) - 1
        if (nameparts[0] == "IA" or nameparts[0] == "FA"):
            sname = 1
            otitle = nameparts[0]
        lastname = nameparts[ename]
        firstname = ' '.join(nameparts[sname:ename])
        self.numProfiles += 1
        profile = {
            'id': self.numProfiles,
            'fideId': fideid,
            'firstName': firstname,
            'lastName': lastname,
            'fideName': lastname + ", " + firstname,
             'fideOtitle': otitle
            }
        self.event['profiles'].append(profile)
        if (not 'arbiters' in self.event['eventInfo']):
            self.event['eventInfo']['arbiters'] = {
                'chiefArbiter': 0,
                'arbiters': []
                } 
        if (is_ca):
            self.event['eventInfo']['arbiters']['chiefArbiter'] = self.numProfiles
        else:
            self.event['eventInfo']['arbiters']['arbiters'].append(self.numProfiles)
        return
    
    def parse_trf_absent(self, tournament, line):
        # TODO
        return
    
    def parse_trf_points(self, tournament, line):
        # TODO
        return
    
    def parse_trf_configuration(self, tournament, line):
        # TODO
        return
    
    def parse_trf_accellerated(self, tournament, line):
        # TODO
        return
        
    
                                 
                                                     
    def export_trf(self, params):
        #print(self.event)
        with open(params['output_file'], 'w') as f:
            json.dump(self.event, f, indent=2)
        
    def prepare_team_section(tournament):
        # update players in teams
        pcmps = {}  # player competitors cross pointer table     
    
    
#### Module test ####

def dotest(name, details):
    print('==== ' + name + ' ====')
    root = '..\\..\\..\\..\\Nordstrandsjakk\\Turneringsservice\\'
     
    with open(root + name + '\\' + name + details + '.txt') as f:
        lines = f.read()

    tournament = trf2json()
    tournament.parse_file(lines)
    with open(root + name + '\\' + name + details + '.json', 'w') as f:
        json.dump(tournament.event, f, indent=2)


def module_test():
    #dotest('escc2018')
    #dotest('h2023')
    dotest('lyn23', '-Rating-A-Lyn-FIDE')
    dotest('ngpl23', '-A-Langsjakk-FIDE')
    dotest('ngpl23', '-B-Langsjakk-FIDE')
    dotest('ngpl23', '-C-Langsjakk-FIDE')
    dotest('elite19-20', '-FIDE')
    #dotest('nm_lag_19')
    dotest('test-half-point', '-Langsjakk-FIDE')
    