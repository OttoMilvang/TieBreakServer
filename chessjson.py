# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Wed Nov  1 11:01:49 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import sys
import random
import json
import helpers
import time
from decimal import *


class chessjson:

    # Read trf into a JSON for Chess data structure
    
   # constructor function    
    def __init__(self):
        random.seed(a=None, version=2)
        self.chessjson = {
	    'filetype': 'Event',
	    'version': '1.0',
	    'origin': 'chessjson ver. 1.00',
	    'published': '',
	    'status': {'code': 0, 'error': []},
        'event' : {
	        'eventName': '',
	        'eventInfo': {},
	        'ratingLists': [{'listName': 'Rating'}],
	        'scoreLists': [],
	        'profiles': [],
	        'teams': [],
            'tournaments': []
            }
        }
        self.event = self.chessjson['event']
        self.scoreLists = {
            'game' : {'W': Decimal('1.0'), 'D': Decimal('0.5'), 'L': Decimal('0.0'), 'Z': Decimal('0.0'), 'A': 'D', 'U': 'Z' },
            'match' : {'W': Decimal('2.0'), 'D': Decimal('1.0'), 'L': Decimal('0.0'), 'Z': Decimal('0.0'), 'A': 'D', 'U': 'Z' },
            'children': {'W': Decimal('3.0'), 'D': Decimal('2.0'), 'L': Decimal('1.0'), 'Z': Decimal('0.0'), 'A': 'D', 'U': 'Z' },
            'football': {'W': Decimal('3.0'), 'D': Decimal('1.0'), 'L': Decimal('0.0'), 'Z': Decimal('0.0'), 'A': 'D', 'U': 'Z' },
            'rating' : {'W': Decimal('1.0'), 'D': Decimal('0.5'), 'L': Decimal('0.0'), 'Z': Decimal('0.0'), 'A': 'Z', 'U': 'Z' },
            '_reverse': {'W': 'L', 'D': 'D', 'L': 'W', 'Z': 'W', 'A': 'A', 'U': 'U' }
           }
        self.numProfiles = 0
        self.numTeams = 0
        self.numResults = 0
        if sys.version_info[0] < 3 or sys.version_info[0] == 3 and sys.version_info[1]  <10:
            self.chessjson['status']['code'] = 500
            self.chessjson['result']['error'].append('Python version must be at least ver. 3.10')
 
    def print_warning(self, line):
        if self.debug:
            print(line)
            pass
        return


    def get_status(self):
        return self.chessjson['status']['code']

    def put_status(self, code, msg):
        self.chessjson['status']['code'] = code
        if code == 0:
            self.chessjson['status']['info'] = msg
        else:
            self.chessjson['status']['error'].append(msg) 


    def get_tournament(self, tournamentno):
        for tournament in self.event['tournaments']: 
            if tournament['tournamentNo'] == tournamentno:
                return tournament
        return None

    def get_scoresystem(self, scoreLists, name):
        for scoreList in scoreLists: 
            if scoreList['listName'] == name:
                return scoreList['scoreSystem']
        newlist = {
            'listName': name,
            'scoreSystem': {}
            }
        scoreLists.append(newlist)
        return(newlist['scoreSystem'])

            

    def parse_score_system(self, name, txt):
        scoresystem = self.get_scoresystem(self.event['scoreLists'], name)
        try:
            for param in txt.split(','):
                param = param.replace('=', ':')
                args = param.split(':')
                scoresystem[args[0]] = float(args[1])
        except:
            self.put_status(402, "Error in score system, " + str(txt))        
   
    
    def parse_file(self, lines, verbose):
        now = time.time()
        self.chessjson = json.loads(lines)


    def tournament_getvalue(self, tournamentno, key):
        tournament = self.get_tournament(tournamentno)
        if tournament == None:
            return None
        return(tournament[key])

    def tournament_setvalue(self, tournamentno, key, value):
        tournament = self.get_tournament(tournamentno)
        if tournament == None:
            return
        tournament[key] = value


    # append_profile
    # check if a profile exist in the profile list.
    # if True: Update the profile object and return the ID
    # if False: Add the profile to the profile list

    def append_profile(self, profile):
        if 'id' in profile and profile['id'] != 0:
            return max(0, profile['id'])
        self.numProfiles += 1
        pid = profile['id'] = self.numProfiles + self.numTeams
        self.event['profiles'].append(profile)
        return pid
            
    # append_team
    # check if a team exist in the profile list.
    # if True: Update the team object with the profileId (if > 0) and return the ID
    # if False: Add the team to the team list

    def append_team(self, team, profileid):
        if type(team) == type(''):
            team = {
                'id':0,
                'teamName': team,
                'players': []
                }
        teamname = team['teamName']            
        for elem in self.event['teams']:
            if elem['teamName'] != teamname:
                continue
            for key, value in team.items():
                if (type(value) == type(0) and value != 0) or (type(value) == type('0') and value != ''):
                    elem[key] = value;
                if profileid > 0 and not (profileid in elem['players']):
                    elem['players'].append(profileid)
            return elem['id']
        self.numTeams += 1
        tid = team['id'] = self.numProfiles + self.numTeams
        if profileid > 0 and not (profileid in team):
            team['players'].append(profileid)
        self.event['teams'].append(team)
        return tid
            
    # append_result
    # check if a result exist in the result list.
    # if True: Update the result object with the new result and return the ID
    # if False: Add the result to the result list

    def append_result(self, results, result):
        gamelist = list(filter(lambda elem: elem['round'] == result['round'] and elem['white'] == result['white'], results))
        if len(gamelist) > 0:
            elem = gamelist[0]
            if not('wResult' in elem) and ('wResult' in result):
                elem['wResult'] = result['wResult']
                #if (result['white'] == trace or result['black'] == trace):
                #    print('Update white', elem)
            if not('bResult' in elem) and ('bResult' in result):
                elem['bResult'] = result['bResult']
                #if (result['white'] == trace or result['black'] == trace):
                #    print('Update black', elem)
            return elem['id']
        self.numResults += 1
        rid = result['id'] = self.numResults
        #if (result['white'] == trace or result['black'] == trace):
        #    print('First', result)
        results.append(result)
        return rid 

    def update_results(self, results):
        for res in ['wResult', 'bResult']:
            for elem in results:
                if not(res in elem):
                    elem[res] = 'Z'

                
    def append_game_to_match(self, results, result):
        trace = 0
        for elem in results:
            if elem['round'] == result['round'] and (elem['white'] == result['white']):
                if not('wResult' in elem) and ('wResult' in result):
                    elem['wResult'] = result['wResult']
                    #if (result['white'] == trace or result['black'] == trace):
                    #    print('Update white', elem)
                if not('bResult' in elem) and ('bResult' in result):
                    elem['bResult'] = result['bResult']
                    #if (result['white'] == trace or result['black'] == trace):
                    #    print('Update black', elem)
                return elem['id']
        rid = result['id'] = next_game()
        #if (result['white'] == trace or result['black'] == trace):
        #    print('First', result)
        results.append(result)
        return rid 
            
    def next_game(self):
        self.numResults += 1
        return self.numResults
    
    
# ==============================
#
# Common function to build help structures
#
 
    # build_tournament_teamcompetitors
    # return two lists cplayers and cteam that uses competition cid as index
    # cplayers[teamCid] is an array of all player-competiotors cid
    # cteam[playerCid] is the cid of the corresonding team  
       
    def build_tournament_teamcompetitors(self, tournament):
        if not tournament['teamTournament']:
            return [None, None]
        team_competitors = tournament['competitors']
        #player_competitors = tournament['playerSection']['competitors']
        #with open('C:\\temp\\team.json', 'w') as f:
            #json.dump(self.cteam, f, indent=2)
        #with open('C:\\temp\\results.json', 'w') as f:
            #json.dump(tournament['teamSection']['results'], f, indent=2)
        #with open('C:\\temp\\player.json', 'w') as f:
            #json.dump(self.cplayers, f, indent=2)
        clookup = {}
        cplayers = {}
        cteam = {0: 0}
        for team in team_competitors:
            cid = team['cid'] 
            cplayers[cid] = []
            teamid = team['teamId']
            clookup[teamid] = cid
            for player in team['cplayers']:
                pcid = player['cid']
                teamid = player['teamId']
                if teamid in clookup:
                    cplayers[clookup[teamid]].append(cid)
                cteam[pcid] = cid   #clookup[teamid]
        #with open('C:\\temp\\cteam.json', 'w') as f:
            #json.dump(cteam, f, indent=2)
        #with open('C:\\temp\\cplayer.json', 'w') as f:
            #json.dump(cplayers, f, indent=2)
        return [cplayers, cteam]
    
    # prepare_scoresystem
    # return a dict where all values are float

    def prepare_scoresystem(self, competition):
        scoreSystem = {}
        for key, value in competition['scoreSystem'].items():
            scoreSystem[key] = value
            if isinstance(value, str):
                scoreSystem[key] = competition['scoreSystem'][value]
        return scoreSystem

    # get_score 
    # return a float value from result struct and color


    def get_score(self, name, result, color):
        scoreSystem = self.scoreLists[name] if name in self.scoreLists else self.get_scoresystem(self.event['scoreLists'], name)
        
        reverse = self.scoreLists['_reverse']
        if color[0] + 'Result' in result:
            res = result[color[0] + 'Result']
        elif result['black'] > 0:
            res = reverse[result[color[0] + 'Result']]
        else:     
            return 0.0
        while res in scoreSystem:
            if res == 'L' and result['played'] == False:
                res = 'Z'
            res = scoreSystem[res]
        return res

    def is_vur(self, result, color):  #
        reverse = self.scoreLists['_reverse']
        if result['played']:
            return False

        if color[0] + 'Result' in result:
            res = result[color[0] + 'Result']
        elif result['black'] > 0:
            res = reverse[result[color[0] + 'Result']]
        else:     
            return 0.0
        #if res == 'W' and result['black'] > 0:  // Full point bye is not vur
        if res == 'W':
            return False
        return True


    
    # build_all_games for team
    # return a dict where where a competitors games in a list in 
    # allgames[round][cid] wher cid is cid for team

    def all_pids(self):
        if not hasattr(self,'pids') or len(self.event['profiles']) != len(self.pids):
            self.pids = {elem['id']: elem for elem in self.event['profiles'] }
        return self.pids
        
    def all_tids(self):
        if not hasattr(self,'tids') or len(self.event['teams']) != len(self.tids):
            self.tids = {elem['id']: elem for elem in self.event['teams'] }
        return self.tids

    def build_all_games(self, tournament, cteam, makecopy):
        allgames = {}
        for game in tournament['gameList']:
            rnd = game['round']
            if not rnd in allgames:
                allgames[rnd] = {}
            arnd = allgames[rnd]
            for col in [game['white'], game['black']]:
                if col in cteam:
                    nteam = cteam[col]
                    if not nteam in arnd:
                        arnd[nteam] = []
                    cgame = game.copy() if makecopy else game
                    arnd[nteam].append(cgame)
        #with open('C:\\temp\\allgames.json', 'w') as f:
        #    json.dump(allgames, f, indent=2)
        return allgames


    # update_tournament_random
    # Update all competitors with random value 

    def update_tournament_random(self, tournament, isteam):
        update = False
        competitors = tournament['competitors']
        for competitor in competitors:
            if not 'random' in competitor:
                competitor['random'] = random.random()
                update = True
        if update:
            ro = sorted(competitors, key=lambda p: (p['random'], p['cid']))
            rnd = 0
            for competitor in ro:
                rnd += 1
                competitor['random'] = rnd
        
        
    # update_chessjson_format
    # Remove  'teamSection' and 'playerSection'
    
    
    def points2score(self, tournament, match, points):
        scorename = tournament['matchScoreSystem'] if match else tournament['gameScoreSystem']
        scoresystem = self.scoreLists[scorename]
        score = 'U'
        for s in ['W', 'D', 'L','Z']:
            if scoresystem[s] == points:
                score = s
        return score            


    def update_chessjson_format(self, tournament, isteam):
        pass
                

