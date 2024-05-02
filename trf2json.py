# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
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
        self.cteam = {}       # pointer from cid-player to cid-team 
        self.cboard = {}
        self.p001 = {}
        self.o001 = {}
        self.pcompetitors = {} # pointer to player section competitors
        self.tcompetitors = {} # pointer to team section competitors
        self.cteam[0] = 0

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
            })
        self.gamescores = [] # used to calculate scoresystem
        self.teamscores = [] # used to calculate scoresystem
        lines = alines.replace('\r', '\n').split('\n')
        tournament = self.get_tournament(1)
        lineno = 0
        for line in lines:
            lineno += 1
            try:
                trfkey = line[0:3]
                trfvalue =line[4:] 
                match trfkey: # noqa
                    case '001': 
                        self.parse_trf_player(tournament, tournament['playerSection'], line)
                    case '012': 
                        self.parse_trf_info('fullName', trfvalue)
                    case '013': 
                        self.parse_trf_team(tournament, tournament['teamSection'], line)
                        tournament['teamTournament'] = True
                    case '022': 
                        self.parse_trf_info('site', trfvalue)
                    case '032':
                        self.parse_trf_info('federation', trfvalue)
                    case '042':
                        self.parse_trf_info('startDate', helpers.parse_date(trfvalue))
                    case '052':
                        self.parse_trf_info('endDate', helpers.parse_date(trfvalue))
                    case '062':
                        numplayers = int(trfvalue.split()[0])
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
## Roberto
                    case 'TSE':
                        self.parse_trf_tse(tournament, line)
                    case 'BBB':
                        tournament['teamSection']['competitors'] = sorted(tournament['teamSection']['competitors'], key=lambda x: x['cid'])
                        self.tcompetitors = { elem['cid']: elem for key, elem in self.tcompetitors.items()  }
                        (self.cplayers, self.cteam) = self.build_tournament_teamcompetitors(tournament)
                    case 'PAB':
                        self.parse_trf_bye(tournament, line, 'U', 0.5)
                    case 'FPB':
                        self.parse_trf_bye(tournament, line, 'F', 1.0)
                    case 'HPB':
                        self.parse_trf_bye(tournament, line, 'H', 0.5)
                    case 'ZPB':
                        self.parse_trf_bye(tournament, line, 'Z', 0.0)
                    case 'MFO':
                        self.parse_trf_forfeit(tournament, line, 'W', 'Z')
                    case 'DFM':
                        self.parse_trf_forfeit(tournament, line, 'Z', 'Z')
                    case 'OOO':
                        self.parse_trf_ooo(tournament, line)
                    case 'XXX':
                        self.parse_test_xxx(tournament, line)
                    case 'FFF':
                        #sys.exit(0)
                        pass
                    

            except:
                self.put_status(401, "Error in trf-file, line " + str(lineno) + ", " + line)
                return
 
        if tournament['teamTournament']:
            self.prepare_team_section(tournament)
            self.update_board_number(tournament, tournament['teamSection'], True)
        else:
            self.update_board_number(tournament, tournament['playerSection'], False)
            
        return        

    def update_board_number(self, tournament, competition, isteam):
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
        if isteam:
            score = None
            scorename =  'match'
        else:    
            score = helpers.solve_scoresystem(self.gamescores)
            #print(score)
            scorename = None
            for name, scoreList in self.scoreLists.items():
                if all(key not in score or score[key] == scoreList[key]  for key in ['W', 'D', 'L', 'Z']):
                    scorename = name
                    break
                if scorename == None:
                    scorename = "my" + '-' + (str(score['W'])  if 'W' in score else 0.0) + '-' + (str(score['D'])  if 'D' in score else 0.0) + '-' + (str(score['L'])  if 'L' in score else 0.0) + '-' + (str(score['Z'] if 'Z' in score else 0.0))
                    newlist = {
                        'listName': scorename,
                        'scoreSystem': score
                        }
                    self.event['scoreLists'].append(newlist)

        competition['scoreSystem'] =  scorename
        if scorename in self.scoreLists:
            scoresystem = self.scoreLists[scorename]
        else:
            scorelist = list(filter(lambda ss: ss['listName'] == scorename, self.event['scoreLists']))
            scoresystem = scorelist[0]['scoreSystem']

        #print(scorename)

       
        if score != None and 'P' in score :
            pval = score['P']          
        elif 'P' in scoresystem:
            pval = scoresystem['P']
        elif rr:
            pval = 'L'
        else:
            pval = 'D' if isteam else 'W'
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
                result['wScore'] = self.get_score(scorename, result, 'white')
                result['bScore']  = 0
                points[result['white']] += result['wScore']
                if 'bResult' in result:
                    result['bScore'] = self.get_score(scorename, result, 'black')
                    points[result['black']] += result['bScore']
                
                
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
            color = ' '
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
                played = True
                rated = False
            case 'D':
                points = 'D'
                played = True
                rated = False
            case 'L':
                points = 'L'
                played = True
                rated = False
            case '?':
                points = 'U'
                played = True
                rated = False
            case '+' | 'F':
                points = 'W'
                played = False
                rated = False
            case 'H':
                points = 'D'
                played = False
                rated = False
            case '-' | 'Z' | ' ':
                points = 'Z'
                played = False
                rated = False
        
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
        self.o001[startno] = line
        self.p001[startno] = line
        gamePoints = helpers.parse_float(line[80:84])
        # score accumulates number of wins, draws and losses and will compare it to sum in order to guess score system
        score = {
            'sum': gamePoints,
            'W': 0,
            'D': 0,
            'L': 0,
            'P': 0,
            'U': 0,
            'Z': 0
            }
        competitor = {
            'cid': startno,
            'profileId': self.numProfiles,
            'present': startno > 0,
            'gamePoints': gamePoints,
            'rank': helpers.parse_int(line[85:89]),
            'rating': helpers.parse_int(line[48:52])
            }
        self.gamescores.append(score)
        section['competitors'].append(competitor)
        self.pcompetitors[competitor['cid']] = competitor
        linelen = len(line)
        currentround = 0
        lastplayed = 0
        lastpaired = 0
        for i in range(99, linelen+1, 10):
            currentround += 1
            game = self.parse_trf_game(section, startno, currentround, line[i-8: i], score)
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
        linelen = len(line)
        teamname = line[4:36].rstrip()
        team = {
            'id': 0,
            'teamName': teamname,
        }
        teamid = self.append_team(team, 0)
        players = []

        competitor = {
            'cid': self.numTeams,
            'teamId': teamid,
            'present': True,
            'matchPoints': 0.0,
            'rank': 1,
            'tieBreak': [],
            'cplayers': []
            }
        #cplayers = tournament['playerSection']['competitors']
        section['competitors'].append(competitor)
        board = 0
        for i in range(40, linelen+1, 5):
            board += 1
            pid = helpers.parse_int(line[i-4:i])
            competitor['cplayers'].append(pid)
            #players.append(cplayers[pid-1]['profileId'])
            self.pcompetitors[pid]['teamId'] = teamid
            self.cboard[pid] = board
            self.cteam[pid] = competitor['cid']
        self.tcompetitors[self.numTeams] = competitor

    def parse_trf_info(self, info, value):
        self.event['eventInfo'][info] = value
        return 1
    
    def parse_trf_dates(self, tournament, line):
        linelen = len(line)
        
        tournament['rounds'] = []
        currentround = 0
        for j in range(99, linelen+1, 10):
            currentround += 1
            date = line[j-8: j]
            tournament['rounds'].append( {'round': currentround,
                                         'startTime': helpers.parse_date(date)
                                         })
        return
    
    
    def parse_trf_arbiter(self, is_ca, line):
        linelen = len(line.rstrip())
        if (linelen == 3):
            return
        fideid = 0
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
        profile = {
            'id': 0,
            'fideId': fideid,
            'firstName': firstname,
            'lastName': lastname,
            'fideName': lastname + ", " + firstname,
             'fideOtitle': otitle
            }
        pid = self.append_profile(profile)
        if (not 'arbiters' in self.event['eventInfo']):
            self.event['eventInfo']['arbiters'] = {
                'chiefArbiter': 0,
                'arbiters': []
                } 
        if (is_ca):
            self.event['eventInfo']['arbiters']['chiefArbiter'] = pid
        else:
            self.event['eventInfo']['arbiters']['arbiters'].append(pid)
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
        
# Exprimental 

    def trf_update_game(self, tournament, game, trans):
        rnd = game['round']
        score = {'-': 0.0, '+': 1.0, 'Z': 0.0, 'H': 0.5 , 'F': 1.0, 'U': 0.5}
        for player in ['white', 'black']:
            sno = game[player]
            if sno > 0:
                line = self.p001[sno]
                gp = helpers.parse_float(line[80:84])
                other = game['white'] if player == 'black' else game['black'] 
                tno = self.cteam[sno]
                #if tno == 3:
                    #print(line)
                col = player[0] if game['black'] > 0 else '-'
                oldres = line[88+10*rnd]
                newres = trans[game[col + 'Result']] if col != '-' else  trans[game['wResult']]
                opp = '{0:4}'.format(other) if other > 0 else '0000'
                line = line[:81+10*rnd] + opp + ' ' + col + ' ' + newres + line[89+10*rnd:]
                if oldres != newres:
                    gp = gp - score[oldres] + score[newres]
                    line = line[:80] + '{0:4.1f}'.format(gp) + line[84:]   
                self.p001[game[player]] = line
                #if tno == 3:
                    #print(line)
                tno = self.cteam[sno]
                team = self.tcompetitors[tno]
                #print(team)
                #sys.exit(0)
            
            
    def parse_trf_tse(self, tournament, line):
        linelen = len(line)
        tpn = helpers.parse_int(line[4:7])
        tp  = helpers.parse_int(line[8:12])
        nickname =  line[13:18]          
        strength = helpers.parse_int(line[19:25])
        rank = helpers.parse_int(line[26:29])
        matchPoints = helpers.parse_int(line[30:34])
        gamePoints = helpers.parse_float(line[35:41])
        cid = self.cteam[tp]
        team = self.tcompetitors[cid]
        team['cid']         = tpn
        team['rank']        = tpn
        team['matchPoints'] = matchPoints
        team['gamePoints'] = gamePoints

    def parse_trf_ooo(self, tournament, line):
        linelen = len(line)
        debug = line[0:27] == '?OOO   1   14    0   29   39'
        
        rnd = helpers.parse_int(line[4:7])
        players = {}
        nulls = 0
        pnums = []
        snums = [] 
        pteam = steam = 0
        trans = {'W': '+', 'L': '-', 'Z': '-'}
        for i in range(12, linelen+1, 5):
            num = helpers.parse_int(line[i-4:i])
            pnums.append(num)
            if num > 0:
                nteam = self.cteam[num]
                if pteam == 0 or pteam == nteam:
                    pteam = nteam
                else:
                     steam = nteam
            else:
                nulls += 1
        pgames = []
        sgames = []
        glen = len(pnums)//2
        if steam == 0:
            glen = len(pnums)
            for game in tournament['playerSection']['results']: 
                if game['round'] == rnd:
                    wteam = self.cteam[game['white']]
                    bteam = self.cteam[game['black']]
                    if pteam in [wteam, bteam] and wteam > 0 and bteam > 0:
                        
                        steam = wteam + bteam - pteam
        else: 
            snums = pnums[len(pnums)//2:]
            pnums = pnums[:len(pnums)//2]
        presults = tournament['playerSection']['results']
        for game in presults: 
            if game['round'] == rnd:
                wteam = self.cteam[game['white']]
                bteam = self.cteam[game['black']]
                if pteam in [wteam, bteam]:
                    pgames.append(game)
                if steam in [wteam, bteam]:
                    sgames.append(game)
        if len(snums) == 0:
            cplayers = self.tcompetitors[steam]['cplayers']
            for player in cplayers:
                game = list(filter(lambda game: game['white'] == player or game['black'] == player, sgames))[0]
                sgames.append(game)
            p = s = 0
            lastc = 'b'
            for i in range(0, len(pnums)):
                c = pnums[i] 
                if c > 0:
                    while(pgames[p]['white'] != c and pgames[p]['black'] != c):
                        p = (p + 1) % len(pgames)
                    game = pgames[p]
                    lastc = 'w' if game['white'] == c else 'b'
                    while sgames[s % len(sgames)]['id'] != game['id'] and s < len(sgames) *(p+1):
                        s += 1
                    if sgames[s % len(sgames)]['id'] == game['id']:
                        snums.append(game['white'] + game['black']-c)
                        s += 1
                    p = (p + 1) % len(pgames)
                else: 
                    while(pgames[p]['wResult'] != 'Z' or pgames[p]['black'] != 0):
                        p = (p + 1) % len(pgames)
                 
                    while(sgames[s]['wResult'] != 'W' or sgames[s]['black'] != 0):
                        s += 1
                    pplayer = pgames[p]['white']    
                    splayer = sgames[s]['white']    
                    game = {
                        'id': 0,
                        'round': rnd,
                        'white': splayer if lastc == 'w' else pplayer ,
                        'black': pplayer if lastc == 'w' else splayer,
                        'played': False,
                        'rated': False
                        }
                    presults.remove(pgames[p])
                    presults.remove(sgames[s])
                    pgames[p] = game
                    sgames[s] = game
                    #section['results'].append(game)
                    game['wResult'] = 'W' if game['white'] == splayer else 'L'
                    game['bResult'] = 'W' if game['black'] == splayer else 'L'
                    self.append_result(tournament['playerSection']['results'], game)
                    self.trf_update_game(tournament, game, trans)
            
        
        
        if debug:
            json.dump(pgames, sys.stdout, indent=2)
            json.dump(sgames, sys.stdout, indent=2)
        #print('OOQ ' + '{0:3}'.format(rnd)+ '{0:4}'.format(pteam) + ' ' + line[7:])
        for i in range(0, glen):
            num = pnums[i]
            game = list(filter(lambda game: game['white'] == num or game['black'] == num, pgames))
            if debug:
                print(num)
                print( game)
        
        return
        games = []
        #steam = 0                       # secondary tesm
        while nulls > 0:
            wteam = bteam = 0
            wgame = bgame = 0
            for game in tournament['playerSection']['results']: 
                if game['round'] == rnd:
                    wteam = self.cteam[game['white']]
                    bteam = self.cteam[game['black']]
                    if pteam in [wteam, bteam] and wteam > 0 and bteam > 0:
                        players[game['white']] = 'w'
                        players[game['black']] = 'b'
                        steam = wteam + bteam - pteam
                        if (wteam == pteam):
                            wgame +=1
                        if (bteam == pteam):
                            bgame +=1
            pplayer = splayer = 0 
            for player in self.tcompetitors[pteam]['cplayers']:
                if player not in players:
                    pplayer = player
                    break
            for player in self.tcompetitors[steam]['cplayers']:
                if player not in players:
                    splayer = player
                    break
            game = {
                'id': 0,
                'round': rnd,
                'white': splayer if bgame < wgame else pplayer ,
                'black': pplayer if bgame < wgame else splayer,
                'played': False,
                'rated': False
                }
                #section['results'].append(game)
            game['wResult'] = 'W' if game['white'] == splayer else 'L'
            game['bResult'] = 'W' if game['black'] == splayer else 'L'
            self.append_result(tournament['playerSection']['results'], game)
            self.trf_update_game(tournament, game, trans)
            nulls -= 1                     


    def parse_trf_ooq(self, tournament, line):
        linelen = len(line)
        pteam = helpers.parse_int(line[4:7])
        rnd = helpers.parse_int(line[8:11])
        players = {}
        nulls = 0
        pteam = 0
        trans = {'W': '+', 'L': '-'}
        for i in range(16, linelen+1, 5):
            num = helpers.parse_int(line[i-4:i])
            if num > 0:
                nteam = self.cteam[num]
                if pteam == 0 or pteam == nteam:
                    pteam = nteam
                else:
                    print('OOO error ' + Line)
            else:
                nulls += 1
        return
        games = []
        steam = 0                       # secondary tesm
        while nulls > 0:
            wteam = bteam = 0
            wgame = bgame = 0
            for game in tournament['playerSection']['results']: 
                if game['round'] == rnd:
                    wteam = self.cteam[game['white']]
                    bteam = self.cteam[game['black']]
                    if pteam in [wteam, bteam] and wteam > 0 and bteam > 0:
                        players[game['white']] = 'w'
                        players[game['black']] = 'b'
                        steam = wteam + bteam - pteam
                        if (wteam == pteam):
                            wgame +=1
                        if (bteam == pteam):
                            bgame +=1
            pplayer = splayer = 0 
            for player in self.tcompetitors[pteam]['cplayers']:
                if player not in players:
                    pplayer = player
                    break
            for player in self.tcompetitors[steam]['cplayers']:
                if player not in players:
                    splayer = player
                    break
            game = {
                'id': 0,
                'round': rnd,
                'white': splayer if bgame < wgame else pplayer ,
                'black': pplayer if bgame < wgame else splayer,
                'played': False,
                'rated': False
                }
                #section['results'].append(game)
            game['wResult'] = 'W' if game['white'] == splayer else 'L'
            game['bResult'] = 'W' if game['black'] == splayer else 'L'
            self.append_result(tournament['playerSection']['results'], game)
            self.trf_update_game(tournament, game, trans)
            nulls -= 1                     


    def parse_trf_bye(self, tournament, line, letter, points):
        linelen = len(line)
        trans = {'U': 'U', 'Z': '-', 'H': 'H', 'F': 'F', '-': '-' }
        trres = {'U': 'D', 'Z': 'Z', 'H': 'D', 'F': 'W', '-': 'L'}
        rnd = 0
        for i in range(7, linelen+1, 4):
            rnd += 1
            num = helpers.parse_int(line[i-3:i])
            if num > 0:
                games = list(filter(lambda game: game['round'] == rnd and self.cteam[game['white']] == num, tournament['playerSection']['results']))
                nzgames = list(filter(lambda game: game['wResult'] != 'Z', games))
                
                pteam = self.tcompetitors[num]
                ind = 0
                myletter = letter
                for cplayer in pteam['cplayers']:
                    lgame1 = list(filter(lambda game: game['white'] == cplayer, nzgames))
                    lgame2 = list(filter(lambda game: game['white'] == cplayer, games))
                    game = lgame2[0] if len(lgame1) == 0 else lgame1[0] 
                    if ind >= 4:         
                        myletter = '-'
                    game['wResult']  = myletter 
                    game['played']  = myletter == 'U'
                    game['rated'] = False
                        
                    self.trf_update_game(tournament, game, trans)
                    game['wResult']  = trres[myletter] 
                    ind += 1


    def parse_trf_forfeit(self, tournament, line, wletter, lletter):
        linelen = len(line)
        trans = {'W': '+', 'L': '-', 'Z': '-'}
        rnd = helpers.parse_int(line[4:7])
        win = helpers.parse_int(line[8:11])
        los = helpers.parse_int(line[12:15])
        #print("FF", rnd, win, los, wletter, lletter)
        wpteam = self.tcompetitors[win]
        lpteam = self.tcompetitors[los] 
        ind = 0
        for i in range(0, len(wpteam['cplayers'])):
            if ind == 4:
                break
            wp = wpteam['cplayers'][i]
            lp = lpteam['cplayers'][ind]
            game = {
                'id': 0,
                'round': rnd,
                'white': wp if i in [0,2] else lp,
                'black': lp if i in [0,2] else wp,
                'wResult': wletter if i in [0,2] else lletter, 
                'bResult': lletter if i in [0,2] else wletter, 
                'played': False,
                'rated': False
            }
            presults = tournament['playerSection']['results']
            games = list(filter(lambda game: game['round'] == rnd and (game['white'] == wp or game['white'] == lp), presults))
            #nzgames = list(filter(lambda game: game['wResult'] != 'Z', games))
            
            if len(games) == 2 and (games[0]['wResult'] == wletter or games[1]['wResult']  == wletter):
                for rgame in games:
                    presults.remove(rgame)
                self.append_result(presults, game)
                self.trf_update_game(tournament, game, trans)
                ind += 1
            games = list(filter(lambda game: game['round'] == rnd and (game['white'] == wp or game['white'] == lp), presults))
            #print(games)
            
            
    def parse_test_xxx(self, tournament, line): 
        gp = {}
        for key, line in self.p001.items():
            cid = self.cteam[helpers.parse_int(line[4:8])]
            gp2 = helpers.parse_float(line[80:84])
            
            gp[cid] = (gp[cid] + gp2) if cid in gp else gp2

        sum1 = sum2 = 0
        for key, competitor in self.tcompetitors.items():
            cid = competitor['cid']
            gp1 = competitor['gamePoints']
            gp2 = gp[cid]
            sum1 += gp1
            sum2 += gp2
        #if gp1 != gp2:
        #        print(cid, gp1, gp2)
        #print(sum1, sum2)
        
# More 
                                                     
    def export_trf(self, params):
        #print(self.event)
        with open(params['output_file'], 'w') as f:
            json.dump(self.event, f, indent=2)
        
    def prepare_team_section(self, tournament):
        # update players in teams
        #[cplayers, cteam] = self.build_tournament_teamcompetitors(tournament)
        #cplayers = self.cplayers
        cteam = self.cteam
        teams = tournament['teamSection']['competitors']
        for team in teams:
            if 'gamePoints' not in team:
                team['gamePoints'] = 0
            if 'matchPoints' not in team:
                team['matchPoints'] = 0
            team['result'] = []
        games = sorted(tournament['playerSection']['results'][:], key=lambda g: (g['round'])) 
        matches = {}
        byes = {}        
        numboards = 0

        for game in games: 
            rnd = game['round']
            wt = cteam[game['white']]
            bt = cteam[game['black']] if 'black' in game and game['black'] > 0 else 0
            if wt > bt:
                index = str(rnd) + '-' + str(wt) + '-' + str(bt)
            else:
                index = str(rnd) + '-' + str(bt) + '-' + str(wt)
            if bt > 0:
                if not (index in matches):
                    matches[index] = { 'games':[] }
                matches[index]['games'].append(game)
                if len(matches[index]['games']) > numboards:
                    numboards = len(matches[index]['games'])
            else:
                if not (index in byes):
                    byes[index] = { 'games':[] }
                byes[index]['games'].append(game)
        self.merge_matches(matches, byes, numboards)
        rnd = 0 
        board = 0
        for key, tmatch in matches.items():
            if tmatch['round'] != rnd:
                rnd = tmatch['round']
                board = 0
            board += 1
            tmatch['board'] = board
            tmatch.pop('games')
            self. append_result(tournament['teamSection']['results'], tmatch)
            
    def merge_matches(self, matches, byes, numboards):
        for key in matches.keys():
            (rnd, p1, p2) = key.split('-')
            arg = int(p1)
            b1 = rnd + '-' + p1  + '-'+ '0' 
            b2 = rnd + '-' + p2  + '-'+ '0' 
            if b1 in byes:
                byes.pop(b1)
            if b2 in byes:
                byes.pop(b2)
        for key in byes.keys():
            matches[key] = byes[key]
            matches[key]['games'] = matches[key]['games']
        for key, tmatch in matches.items():
            (rnd, p1, p2) = key.split('-')
            arg = int(p1)
            games = tmatch['games']
            for i in range(0, len(games)-1):
                for j in range(i+1, len(games)):
                    #print(games[i])
                    #print(games[j])
                    #print(self.cteam[games[i]['white']], arg, (self.cteam[games[i]['white']] == arg))
                    if self.cteam[games[i]['white']] == arg:
                        t1 = self.cboard[games[i]['white']]
                    else:
                        t1 = self.cboard[games[i]['black']]
                    if self.cteam[games[j]['white']] == arg:
                        t2 = self.cboard[games[j]['white']]
                    else:
                        t2 = self.cboard[games[j]['black']]
                    if t2 < t1:
                        (games[i], games[j]) = (games[j], games[i])
            scorename = self.event['tournaments'][0]['playerSection']['scoreSystem']
            scoresystem = self.scoreLists[scorename]
            if not 'P' in scoresystem:
                scoresystem['P'] = 'D'
            reverse = self.scoreLists['_reverse']
            white = self.cteam[games[0]['white']]
            black = self.cteam[games[0]['black']]
            tmatch['round'] = games[0]['round']
            tmatch['white'] = white
            tmatch['black'] = black
            played = False
            wscore = 0 
            bscore = 0
            #if (len(games) < numboards):
            #    print(numboards, key, tmatch, len(games))
            ind = 0
            preres = None
            #print("GEO:", games)
            for i in range(0, len(games)):
                ind += 1
                game = None
                g0 =  list(filter(lambda game: 'board' in game and game['board'] == ind , games))
                if len(g0) >  0:
                    game = g0[0]
                else:
                    g1 =  list(filter(lambda game: game['black'] > 0 or game['wResult'] != 'L' or game['played'] , games))
                    if len(g1) > 0:
                        game = g1[0]
                    else:
                        game = games[0]
                game['board'] = ind
                if preres == None:
                    preres = game['wResult']
                played = played or game['played']
                #print('Sel', game)
                ws = self.get_score(scorename, game, 'white')
                bs = self.get_score(scorename, game, 'black') if 'bResult' in game else 0
                if self.cteam[game['white']] == white:
                    wscore += ws
                    bscore += bs
                else:
                    wscore += bs
                    bscore += ws
                games.remove(game)
                if ind == 4:
                    break
            tmatch['played'] = played
            if black > 0:
                if wscore > bscore:
                    tmatch['wResult'] = 'W'
                    tmatch['bResult'] = 'L'
                elif bscore > wscore:
                    tmatch['wResult'] = 'L'
                    tmatch['bResult'] = 'W'
                elif wscore > 0 and bscore > 0:
                    tmatch['wResult'] = 'D'
                    tmatch['bResult'] = 'D'
                else: 
                    tmatch['wResult'] = 'L'
                    tmatch['bResult'] = 'L'
            else:
                tmatch['wResult'] = preres

#### Module test ####

    def  dumpresults(self):
        cmps = self.event['status']['competitors']
        print(cmps)
        tcmps = { elem['startno']: elem for elem in cmps  }
        competitors = self.event['tournaments'][0]['teamSection']['competitors']
        for competitor in competitors:
            cid = competitor['cid']
            sgp = 0
            for player in competitor['cplayers']:
                trf = self.p001[player]
                country = trf[53:56]
                gp = helpers.parse_float(trf[80:84])
                sgp += gp
 
           
            print('{0:2}'.format(cid) + '  - ' + country)                 
            eq = competitor['matchPoints'] == tcmps[cid]['calculations'][0]['val'] and competitor['gamePoints'] == tcmps[cid]['calculations'][1]['val']
            print('TSE:', '{0:4.1f}'.format(competitor['matchPoints']), '{0:5.1f}'.format(competitor['gamePoints']))
            print('001:', '{0:4}'.format(' '), '{0:5.1f}'.format(sgp))
            print('TBS:', '{0:4.1f}'.format(tcmps[cid]['calculations'][0]['val']), '{0:5.1f}'.format(tcmps[cid]['calculations'][1]['val']), "" if eq else "*****"  )
            print('Org:')
            for player in competitor['cplayers']:
                trf = self.o001[player]
                print(trf)
            print('Mod:')
            for player in competitor['cplayers']:
                trf = self.p001[player]
                print(trf)
            currentround = 0
            linelen = len(trf)
            line = '{0:89}'.format(' ')
            for i in range(99, linelen+1, 10):
                currentround += 1
                line += '{0:10.1f}'.format(tcmps[cid]['calculations'][0][currentround])
            print(line)
            currentround = 0
            line = '{0:89}'.format(' ')
            for i in range(99, linelen+1, 10):
                currentround += 1
                line += '{0:10.1f}'.format(tcmps[cid]['calculations'][1][currentround])
            print(line)
 
        print()
        for key, trf in self.p001.items():
            print(trf)
               
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
    dotest('Team-Example', '')
    #dotest('nm_lag_19')
    dotest('test-half-point', '-Langsjakk-FIDE')
    dotest('test-half-point2', '-Langsjakk-FIDE')
    