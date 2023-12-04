# -*- coding: utf-8 -*-
"""
Created on Wed Nov  1 11:01:49 2023

@author: otto
"""
import sys
import json
import helpers
import time


class chessjson:

    # Read trf into a JSON for Chess data structure
    
   # constructor function    
    def __init__(self):
        self.event = {
	    'filetype': 'Event',
	    'version': '1.0',
	    'origin': 'chessjson ver. 1.00',
	    'published': '',
	    'status': {'code': 0, 'error': []},
	    'eventName': '',
	    'eventInfo': {},
	    'ratingLists': [{'listName': 'Rating'}],
	    'scoreLists': [],
	    'profiles': [],
	    'teams': [],
        'tournaments': []
        }
        self.scoreList = {
            'game' : {'W': 1.0, 'D': 0.5, 'L': 0.0, 'Z': 0.0, 'A': 'D', 'U': 'Z' },
            'match' : {'W': 2.0, 'D': 1.0, 'L': 0.0, 'Z': 0.0, 'A': 'D', 'U': 'Z' },
            'children': {'W': 3.0, 'D': 2.0, 'L': 1.0, 'Z': 0.0, 'A': 'D', 'U': 'Z' },
            'football': {'W': 3.0, 'D': 1.0, 'L': 0.0, 'Z': 0.0, 'A': 'D', 'U': 'Z' },
            'rating' : {'W': 1.0, 'D': 0.5, 'L': 0.0, 'Z': 0.0, 'A': 'Z', 'U': 'Z' },
            '_reverse': {'W': 'L', 'D': 'D', 'L': 'W', 'Z': 'W', 'A': 'A', 'U': 'U' }
           }
        self.numProfiles = 0
        self.numTeams = 0
        self.numResults = 0
        if sys.version_info[0] < 3 or sys.version_info[0] == 3 and sys.version_info[1]  <10:
            self.event['status']['code'] = 500
            self.event['result']['error'].append('Python version must be at least ver. 3.10')
 
    def print_warning(self, line):
        if self.debug:
            print(line)
        return


    def get_status(self):
        return self.event['status']['code']

    def put_status(self, code, msg):
        self.event['status']['code'] = code
        if code == 0:
            self.event['status']['info'] = msg
        else:
            self.event['status']['error'].append(msg) 


    def get_tournament(self, tournamentno):
        for tournament in self.event['tournaments']: 
            if tournament['tournamentNo'] == tournamentno:
                return tournament
        return None

    def get_scoresystem(self, scorelists, name):
        for scorelist in scorelists: 
            if scorelist['listName'] == name:
                return scorelist['scoreSystem']
        newlist = {
            'listName': name,
            'scoreSystem': {}
            }
        scorelists.append(newlist)
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
   
    
    def parse_file(self, lines):
        now = time.time()
        self.event = json.loads(lines)


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
        if 'id' in profile and profile['id'] < 0:
            return 0
        for elem in self.event['profiles']:
            eq = helpers.is_equal('fideId', elem, profile)
            if eq == 0:
                eq = helpers.is_equal('localId', elem, profile)
            if eq == 0:
                 eq = helpers.is_equal('federation', elem, profile)
                 if eq == 1:
                     eq = 0;
            if eq == 0:
                eq = helpers.is_equal('firstName', elem, profile) + helpers.is_equal('lastName', elem, profile) -1
            if eq == 1: # Found
                for key, value in profile.items():
                    if (type(value) == type(0) and value != 0) or (type(value) == type('0') and value != ''):
                        elem['key'] = value;
                return elem['id']
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
        trace = 0
        for elem in results:
            if elem['round'] == result['round'] and elem['white'] == result['white']:
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
        self.numResults += 1
        rid = result['id'] = self.numResults
        #if (result['white'] == trace or result['black'] == trace):
        #    print('First', result)
        results.append(result)
        return rid 
            

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
        team_competitors = tournament['teamSection']['competitors']
        player_competitors = tournament['playerSection']['competitors']
        clookup = {}
        cplayers = {}
        cteam = {}
        for team in team_competitors:
            cid = team['cid'] 
            cplayers[cid] = []
            teamid = team['teamId']
            clookup[teamid] = cid
        for player in player_competitors:
            cid = player['cid']
            teamid = player['teamId']
            if teamid in clookup:
                cplayers[clookup[teamid]].append(cid)
                cteam[cid] = clookup[teamid]
        with open('C:\\temp\\cteam.json', 'w') as f:
            json.dump(cteam, f, indent=2)
        with open('C:\\temp\\cplayer.json', 'w') as f:
            json.dump(cplayers, f, indent=2)
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
        scoreSystem = self.scoreList[name]
        reverse = self.scoreList['_reverse']
        if color[0] + 'Result' in result:
            res = result[color[0] + 'Result']
        elif result['black'] > 0:
            res = reverse[result[color[0] + 'Result']]
        else:     
            print("NOOOOOOOOOOOOOOOO", result)
            return 0.0
        while res in scoreSystem:
            if res == 'L' and result['played'] == False:
                res = 'Z'
            res = scoreSystem[res]
        return res
    
    # build_all_games for team
    # return a dict where where a competitors games in a list in 
    # allgames[round][cid] wher cid is cid for team

    def build_all_games(self, tournament, cteam, makecopy):
        allgames = {}
        for game in tournament['playerSection']['results']:
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
        with open('C:\\temp\\allgames.json', 'w') as f:
            json.dump(allgames, f, indent=2)
        return allgames



