# -*- coding: utf-8 -*-
"""
Created on Fri Aug  11 11:43:23 2023

@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
import rating as rating


"""
Structre 

+--- tiebreaks: [  - added in compute-tiebreak
|         {
|             order: priority of tiebreak
|             name: Acronym from regulations
|             pointtype: mpoints (match points) gpoints (game points) or points 
|             modifiers: { low / high / lim / urd / p4f / fmo / rb5 / z4h / vuv }
|         }, 
|         ...
|    
|       ]
+--- isteam: True/False
+--- currentRound: Standings after round 'currentround'
+--- rounds: Total number of rounds
+--- rr: RoundRobin (True/False)
+--- scoresystem: {
|        game: { W:1.0, D:0.5, L:0.0, Z:0.0, P:1.0, A:0.5, U: 0.0 }
|        team: { W:1.0, D:1.0, L:0.0, Z:0.0, P:1.0, A:1.0, U: 0.0 }
|                 }
+--- players/teams:  {
|              1: {
|                    cid: startno
|                    rating: rating
|                    kfactor: k
|                    rating: rating
|                    rrst: {  - results, games for players, matches for teams
|                        1: {  - round
|                              points - points for game / match
|                              rpoints - for games, points with score system 1.0 / 0.5 / 0.0 
|                              color - w / b 
|                              played  - boolean
|                              rated - boolean
|                              opponent - id of opponent
|                              opprating - rating of opponent
|                              deltaR - for rating change
|                            }
|                        2: {  - round 2 }
|                           ...
|                           }
|                   game/match: {  - intermediate results from tb calculations }
|     ---- output for each player / team
|                   score: [ array of tie-breaks values, same order and length as 'tiebreaks'
|                   rank: final rank of player / team
|                 },
|              2: { ... },
|                  ...
|         }
+--- rankorder: [ array of rankorder,  players/teams ]  
|
                                 
"""


class tiebreak:

    

    # constructor function    
    def __init__(self, chessevent, tournamentno):
        event = chessevent.event
        tournament = chessevent.get_tournament(tournamentno)
        self.tiebreaks = []
        self.isteam = self.isteam = tournament['teamTournament'] if 'teamTournament' in tournament else False
        self.currentround = 0
        self.rounds = tournament['numRounds']
        self.get_score = chessevent.get_score
        self.maxboard = 0   

        self.scoreList = {}
        for name, scoresystem in chessevent.scoreList.items():
            self.scoreList[name] = scoresystem
        for scoresystem in event['scoreLists']:
            for key, value in scoresystem['scoreSystem'].items():
                self.scoreList[scoresystem['listName']][key] = value
        if self.isteam:
            self.teamscore = tournament['teamSection']['scoreSystem']
            self.gamescore = tournament['playerSection']['scoreSystem']
            [self.cplayers, self.cteam] = chessevent.build_tournament_teamcompetitors(tournament)
            self.allgames = chessevent.build_all_games(tournament, self.cteam, False)    
            self.teams = self.prepare_competitors(tournament['teamSection'], 'match')
            self.compute_score(self.teams, 'match', self.currentround)
            self.compute_score(self.teams, 'game', self.currentround)
        else:
            self.teamscore = tournament['playerSection']['scoreSystem']
            self.gamescore = tournament['playerSection']['scoreSystem']
            self.players = self.prepare_competitors(tournament['playerSection'], 'game')
            self.compute_score(self.players, 'game', self.currentround)            
        self.cmps = self.teams if self.isteam  else self.players
        numcomp = len(self.cmps)
        self.rankorder = list(self.cmps.values()) 

        if 'currentRound' in tournament:
            self.currentround = tournament['currentRound']
        
        # find tournament type
        tt = tournament['tournamentType'].upper()
        self.rr = False
        if tt.find('SWISS') >= 0:
            self.rr = False
        elif tt.find('RR') >= 0 or tt.find('ROBIN') >= 0 or tt.find('BERGER') >= 0: 
            self.rr = True
        elif numcomp == self.rounds + 1 or numcomp == self.rounds:
                self.rr = True
        elif numcomp == (self.rounds + 1)*2 or numcomp == self.rounds * 2:
            self.rr = True

   
    
    def prepare_competitors(self, competition, scoretype):
        rounds = self.currentround
        #scoresystem = self.scoresystem['match']

        cmps = {}
        for competitor in competition['competitors']:
            cmp = {
                    'cid': competitor['cid'],
                    'rsts': {},
                    'orgrank': competitor['rank'],
                    'rank': 1,
                    'rating': (competitor['rating'] if 'rating' in competitor else 0),
                    'tieBreak': [],
                    'tbval': {}
                  }
            cmps[competitor['cid']] = cmp
        for rst in competition['results']: 
            rounds = self.prepare_result(cmps, rst, self.teamscore, rounds)
            if self.isteam:
                self.prepare_teamgames(cmps, rst, self.gamescore)
        self.currentround = rounds
        with open('C:\\temp\\cmps.json', 'w') as f:
            json.dump(cmps, f, indent=2)

        return cmps

    def prepare_result(self, cmps, rst, scoresystem, rounds):
        ptype = 'mpoints' if self.isteam else 'points'
        rnd = rst['round']
        white = rst['white']
        wPoints = self.get_score(scoresystem, rst, 'white')
        wrPoints = self.get_score('rating', rst, 'white')
        wrating = 0
        brating = 0
        expscore = None
        if 'black' in rst:
            black = rst['black']
        else:
            black = 0
        if  black > 0:
            if not 'bResult' in rst:
                rst['bResult'] = self.scoreList['reverse'][rst['wResult']]
            bPoints = self.get_score(scoresystem, rst, 'black')
            brPoints = self.get_score('rating', rst, 'black')
            if (rst['played']):
                if 'rating' in cmps[white] and cmps[white]['rating'] > 0:
                    wrating = cmps[white]['rating']
                if 'rating' in cmps[black] and cmps[black]['rating'] > 0:
                    brating = cmps[black]['rating']
                expscore = rating.ComputeExpectedScore(wrating, brating)
                
        cmps[white]['rsts'][rnd] = {
            ptype: wPoints, 
            'rpoints': wrPoints, 
            'color': 'w', 
            'played': rst['played'], 
            'rated': rst['rated'] if 'rated' in rst else (rst['played'] and black > 0), 
            'opponent': black,
            'opprating': brating,
            'board': rst['board'],
            'deltaR': (rating.ComputeDeltaR(expscore, wrPoints) if not expscore == None else None  ) 
            } 
        if (black> 0):
            if rnd > rounds:
                rounds = rnd
            cmps[black]['rsts'][rnd] = {
                ptype: bPoints, 
                'rpoints': brPoints, 
                'color': "b", 
                'played': rst['played'], 
                'rated': rst['rated']  if 'rated' in rst else (rst['played'] and white > 0),
                'opponent': white,
                'opprating': wrating,
                'board': rst['board'],
                'deltaR': (rating.ComputeDeltaR(1.0-expscore, brPoints) if not expscore == None else None  ) 
                }
        return rounds

    def prepare_teamgames(self, cmps, rst, scoresystem):
        maxboard = 0
        rnd = rst['round']
        for col in ['white', 'black']:
            if col in rst and rst[col] > 0:
                gpoints = 0
                competitor = rst[col]
                games = []
                for game in self.allgames[rnd][competitor]:
                    white = game['white']
                    black = game['black'] if 'black' in game else 0
                    maxboard = max(maxboard, game['board'])
                    if self.cteam[white] == competitor:
                        points = self.get_score(self.gamescore, game, 'white')
                        gpoints += points
                        games.append(
                            {
                                'points': points,
                                'rpoints': self.get_score('rating', game, 'white'),
                                'color': 'w',
                                'played': game['played'],
                                'rated' : game['rated'] if 'rated' in rst else (game['played'] and black > 0), 
                                'player': white,
                                'opponent': black,
                                'board': game['board']
                            }) 
                    if black > 0 and self.cteam[black] == competitor:
                        points = self.get_score(self.gamescore, game, 'black')
                        gpoints += points
                        games.append(
                            {
                                'points': points,
                                'rpoints': self.get_score('rating', game, 'black'),
                                'color': 'b',
                                'played': game['played'],
                                'rated' : game['rated'] if 'rated' in rst else (game['played'] and black > 0), 
                                'player': black,
                                'opponent': white,
                                'board': game['board']
                            })
                cmps[competitor]['rsts'][rnd]['gpoints'] = gpoints
                cmps[competitor]['rsts'][rnd]['games'] = games
        self.maxboard = max(self.maxboard, maxboard)
    
    def compute_score(self, cmps, scoretype, rounds):
#        scoresystem = self.scoresystem[scoretype]
        prefix = scoretype[0] if self.isteam else ''
        for startno, cmp in cmps.items():
            tbscore = cmp[scoretype] = {}
            tbscore['sno'] = startno
            tbscore['rank'] = cmp['orgrank'];
            tbscore['num'] = 0    # number of elements
            tbscore['lo'] = 0     # last round with opponent
            tbscore['lp'] = 0     # last round played 
            tbscore['points'] = 0 # total points
            tbscore['pfp'] = 0    # points from played games
            tbscore['win'] = 0    # number of wins (played and unplayed)
            tbscore['won'] = 0    # number of won games over the board
            tbscore['bpg'] = 0    # number of black games played
            tbscore['bwg'] = 0    # number of games won with black
            tbscore['ge'] = 0     # number of games played + PAB
            tbscore['lg'] = self.scoreList[scoretype]['D'] # Result of last game
            tbscore['bp'] = {}    # Boardpoints
            for rnd, rst in cmp['rsts'].items():
                # total score
                points = rst[prefix + 'points']
                tbscore['points'] += points
                # number of games
                if self.isteam and scoretype == 'game':
                    gamelist = rst['games']
                else:
                    gamelist = [rst]
                for game in gamelist:
                    if self.isteam and scoretype == 'game':
                        points = game['points']
                        board = game['board'];
                        tbscore['bp'][board] = tbscore['bp'][board]  + points if board in tbscore['bp']  else points
                    tbscore['num'] += 1
                    # last round with opponent, pab or fpb (16.2.1, 16.2.2, 16.2.3 and 16.2.4)
                    if rnd > tbscore['lo'] and (game['played'] or game['opponent'] > 0 or points == self.scoreList[scoretype]['W']):
                        tbscore['lo'] = rnd
                    # points from played games    
                    if game['played'] and game['opponent'] > 0:
                        tbscore['pfp'] += points
                    # last played game (or PAB)
                    if rnd > tbscore['lp'] and game['played']:
                        tbscore['lp'] = rnd
                    # number of win
                    if points == self.scoreList[scoretype]['W']:
                        tbscore['win'] += 1
                    # number of win played over the board
                    if points == self.scoreList[scoretype]['W'] and game['played']:
                        tbscore['won'] += 1
                    # number of games played with black
                    if game['color'] == 'b' and game['played']:
                        tbscore['bpg'] += 1
                    # number of win played with black
                    if game['color'] == 'b' and game['played'] and points == self.scoreList[scoretype]['W']:
                        tbscore['bwg'] += 1
                    # number of games elected to play
                    if game['played'] or (game['opponent'] > 0 and points == self.scoreList[scoretype]['W']):
                        tbscore['ge'] += 1
                    # result in last game
                    if rnd == self.rounds and game['opponent'] > 0:
                        tbscore['lg'] = points 


    def compute_recursive_if_tied(self, tb, cmps, scoretype, rounds, compute_singlerun):
        name = tb['name'].lower()
        ro = self.rankorder
        for player in ro:
            player[scoretype][name] = player['rank']  # 'de' rank value initial value = rank
            player[scoretype]['moreloops'] = True  # 'de' rank value initial value = rank
        loopcount = 0
        moretodo = compute_singlerun(tb, cmps, scoretype, rounds, ro, loopcount)
        while moretodo:
            moretodo = False
            loopcount += 1
            start = 0;
            while start < len(ro):
                currentrank = ro[start][scoretype][name]
                for stop in range( start+1,  len(ro)+1):
                    if stop == len(ro) or currentrank !=  ro[stop][scoretype][name]:
                        break
                # we have a range start .. stop-1 to check for top board result
                if ro[start][scoretype]['moreloops']:
                    if stop - start == 1:
                        moreloops = False
                        ro[start][scoretype]['moreloops'] = moreloops
                    else:
                        subro = ro[start:stop] # subarray of rankorder
                        moreloops = compute_singlerun(tb,cmps, scoretype, rounds, subro, loopcount) 
                        for player in subro:
                            player[scoretype]['moreloops'] = moreloops  # 'de' rank value initial value = rank
                        moretodo = moretodo or moreloops
                start = stop            
            #json.dump(ro, sys.stdout, indent=2)
            ro = sorted(ro, key=lambda p: (p['rank'], p[scoretype][name], p['cid']))
            
        # reorder 'tb' 
        start = 0;
        while start < len(ro):
            currentrank = ro[start]['rank']
            for stop in range( start,  len(ro)+1):
                if stop == len(ro) or currentrank !=  ro[stop]['rank']:
                    break
                # we have a range start .. stop-1 to check for direct encounter
            offset = ro[start][scoretype][name]
            if ro[start][scoretype][name] != ro[stop-1][scoretype][name]:
                offset -=1 
            for p in range(start, stop):
                ro[p][scoretype][name] -= offset
            start = stop
        return name

           


    def compute_singlerun_direct_encounter(self, tb, cmps, scoretype, rounds, subro, loopcount):
        if loopcount == 0:
            return True
        changes = 0
        points = tb['pointtype']
        currentrank = subro[0][scoretype]['de']
        metall = True          # Met all opponents on same range
        metmax = len(subro)-1  # Max number of opponents
        for player in range(0, len(subro)):
            de = subro[player][scoretype]
            de['denum'] = 0    # number of opponens
            de['deval'] = 0    # sum score against of opponens
            de['demax'] = 0    # sum score against of opponens, unplayed = win
            de['delist'] = { }  # list of results numgames, score, maxscore 
            for rnd, rst in subro[player]['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                          played = True if tb['modifiers']['p4f'] else rst['played']
                          if played and cmps[opponent][scoretype]['de'] == currentrank:
                              # 6.1.2 compute average score 
                              if opponent in de['delist']:
                                  score = de['delist'][opponent]['score']
                                  num = de['delist'][opponent]['num']
                                  sumscore = score * num
                                  de['deval'] -= score
                                  num += 1
                                  sumscore += rst['points']
                                  score = sumscore / num
                                  de['denum'] = 1
                                  de['deval'] += score
                                  de['delist'][opponent]['num'] = 1 
                                  de['delist'][opponent]['score'] = score
                              else:
                                  de['denum'] += 1
                                  de['deval'] += rst[points]
                                  de['delist'][opponent] = { 'num': 1,
                                                             'score': rst[points]
                                                            }
            #if not tb['modifiers']['p4f'] and de['denum'] < metmax:
            if (not tb['modifiers']['p4f'] and de['denum'] < metmax) or tb['modifiers']['sws']:
                metall = False
                de['demax'] = de['deval'] + (metmax - de['denum']) * self.scoreList[scoretype]['W']
            else:
                de['demax'] = de['deval']
        if metall: # 6.2 All players have met
            subro = sorted(subro, key=lambda p: (-p[scoretype]['deval'], p['cid']))
            rank = subro[0][scoretype]['de']
            val = subro[0][scoretype]['deval']
            for i in range(1, len(subro)):
                rank += 1
                if (val != subro[i][scoretype]['deval']):
                    subro[i][scoretype]['de'] = rank
                    val = subro[i][scoretype]['deval']
                    changes += 1
                else:
                    subro[i][scoretype]['de'] = subro[i-1][scoretype]['de']
        else: # 6.2 swiss tournament
            subro = sorted(subro, key=lambda p: (-p[scoretype]['deval'], -p[scoretype]['demax'], p['cid']))
            rank = subro[0][scoretype]['de']
            val = subro[0][scoretype]['deval']
            unique = True
            for i in range(1, len(subro)):
                rank += 1
                if (unique and val > subro[i][scoretype]['demax']):
                    subro[i][scoretype]['de'] = rank
                    val = subro[i][scoretype]['deval']
                    changes += 1
                else:
                    subro[i][scoretype]['de'] = subro[i-1][scoretype]['de']
                    unique = False
        return changes > 0 and loopcount < 30

        
    def compute_direct_encounter(self, tb, cmps, scoretype, rounds):
        tb['modifiers']['reverse'] = False
        points = tb['pointtype']
        low = tb['modifiers']['low'] 
        ro = self.rankorder
        for player in ro:
            player[scoretype]['de'] = player['rank']  # 'de' rank value initial value = rank
        changes = 1
        tr = 0 
        while changes >0:
            tr += 1
            changes = 0
            start = 0;
            while start < len(ro):
                currentrank = ro[start][scoretype]['de']
                for stop in range( start+1,  len(ro)+1):
                    if stop == len(ro) or currentrank !=  ro[stop][scoretype]['de']:
                        break
                # we have a range start .. stop-1 to check for direct encounter
                metmax = stop-start-1  # Max number of opponents
                metall = True          # Met all opponents on same range
                subro = ro[start:stop] # subarray of rankorder
                for player in range(0, len(subro)):
                    de = subro[player][scoretype]
                    de['denum'] = 0    # number of opponens
                    de['deval'] = 0    # sum score against of opponens
                    de['demax'] = 0    # sum score against of opponens, unplayed = win
                    de['delist'] = { }  # list of results numgames, score, maxscore 
                    for rnd, rst in subro[player]['rsts'].items():
                        if rnd <= rounds:
                            opponent = rst['opponent']
                            if opponent > 0:
                                  played = True if tb['modifiers']['p4f'] else rst['played']
                                  if played and cmps[opponent][scoretype]['de'] == currentrank:
                                      # 6.1.2 compute average score 
                                      if opponent in de['delist']:
                                          score = de['delist'][opponent]['score']
                                          num = de['delist'][opponent]['num']
                                          sumscore = score * num
                                          de['deval'] -= score
                                          num += 1
                                          sumscore += rst['points']
                                          score = sumscore / num
                                          de['deval'] += score
                                          de['delist'][opponent]['num'] = 1 
                                          de['delist'][opponent]['score'] = score
                                      else:
                                          de['denum'] += 1
                                          de['deval'] += rst[points]
                                          de['delist'][opponent] = { 'num': 1,
                                                                     'score': rst[points]
                                                                    }
                    #if not tb['modifiers']['p4f'] and de['denum'] < metmax:
                    if (not tb['modifiers']['p4f'] and de['denum'] < metmax) or tb['modifiers']['sws']:
                        metall = False
                        de['demax'] = de['deval'] + (metmax - de['denum']) * self.scoreList[scoretype]['W']
                    else:
                        de['demax'] = de['deval']
                if metall: # 6.2 All players have met
                    subro = sorted(subro, key=lambda p: (-p[scoretype]['deval'], p['cid']))
                    rank = subro[0][scoretype]['de']
                    val = subro[0][scoretype]['deval']
                    for i in range(1, len(subro)):
                        rank += 1
                        if (val != subro[i][scoretype]['deval']):
                            subro[i][scoretype]['de'] = rank
                            val = subro[i][scoretype]['deval']
                            changes += 1
                        else:
                            subro[i][scoretype]['de'] = subro[i-1][scoretype]['de']
                else: # 6.2 swiss tournament
                    subro = sorted(subro, key=lambda p: (-p[scoretype]['deval'], -p[scoretype]['demax'], p['cid']))
                    rank = subro[0][scoretype]['de']
                    val = subro[0][scoretype]['deval']
                    unique = True
                    for i in range(1, len(subro)):
                        rank += 1
                        if (unique and val > subro[i][scoretype]['demax']):
                            subro[i][scoretype]['de'] = rank
                            val = subro[i][scoretype]['deval']
                            changes += 1
                        else:
                            subro[i][scoretype]['de'] <= subro[i-1][scoretype]['de']
                            unique = False
                start = stop            
            #json.dump(ro, sys.stdout, indent=2)
            ro = sorted(ro, key=lambda p: (p['rank'], p[scoretype]['de'], p['cid']))
            if (tr > 20):  # Avoid infinite loop if error
                break
        # reorder 'de' 
        start = 0;
        while start < len(ro):
            currentrank = ro[start]['rank']
            for stop in range( start,  len(ro)+1):
                if stop == len(ro) or currentrank !=  ro[stop]['rank']:
                    break
                # we have a range start .. stop-1 to check for direct encounter
            offset = ro[start][scoretype]['de']
            if ro[start][scoretype]['de'] != ro[stop-1][scoretype]['de']:
                offset -=1 
            for p in range(start, stop):
                ro[p][scoretype]['de'] -= offset
            start = stop
        return 'de'
              


    def copmute_progressive_scoresself(self, tb, cmps, scoretype, rounds):
        points = tb['pointtype']
        low = tb['modifiers']['low'] 
        for startno, cmp in cmps.items():
            tbscore = cmp[scoretype]
            ps = 0
            for rnd in range(low, rounds+1):
                p = cmp['rsts'][rnd][points] if rnd in cmp['rsts'] else 0.0
                ps += p * (rounds+1-rnd)
            tbscore['ps'] = ps
        return 'ps'
              

    def copmute_koya(self, tb, cmps, scoretype, rounds):
        points = tb['pointtype']
        scoresystem = self.scoresystem[scoretype]
        lim = tb['modifiers']['lim'] 
        for startno, cmp in cmps.items():
            tbscore = cmp[scoretype]
            ks = 0
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                        if cmps[opponent][scoretype][points] * low + 0.000001  >= 100 * scoresystem['W']*rounds:
                            ks += cmp[scoretype][points] 
            tbscore['ks'] = ks
        return 'ks'


            
    def compute_buchholz_sonneborn_berger(self, tb, cmps, scoretype, rounds):
        points = tb['pointtype']
        name = tb['name'].lower()
        if name == 'aob': 
            name = 'bh'
        is_sb = name == 'sb' or name == 'esb'
        if name == 'esb':
            oscoretype = 'game' if tb['pointtype'][0] == 'gpoints' else 'match' # opponent
            sscoretype = 'game' if tb['pointtype'][1] == 'gpoints' else 'match' # selv score
        else:
            oscoretype = sscoretype = scoretype
        for startno, cmp in cmps.items():
            tbscore = cmp[oscoretype]
            # 16.3.2    Unplayed rounds of category 16.2.5 are evaluated as draws.
            tbscore['ownbh'] = 0
            for rnd, rst in cmp['rsts'].items():
                if rnd <= tbscore['lo']:
                    tbscore['ownbh'] += rst[points]
            tbscore['ownbh'] = tbscore['ownbh'] + (rounds - tbscore['lo']) * self.scoreList[scoretype]['D']  # own score used for bh
            if name == 'fb' and tbscore['lo'] == self.rounds:
                tbscore['ownbh'] = tbscore['ownbh'] - tbscore['lg'] + self.scoreList[scoretype]['D']
        for startno, cmp in cmps.items():
            tbscore = cmp[sscoretype]
            bhvalue = [] 
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                        played = True if tb['modifiers']['p4f'] else rst['played']
                        if played or not tb['modifiers']['urd']:
                            score = cmps[opponent][oscoretype]['ownbh']
                            tbvalue = score * rst[points] if is_sb else score
                        else:
                            score = cmps[startno][oscoretype]['ownbh']
                            tbvalue = score * rst[points] if is_sb else score
                    else:
                        played = False
                        score = cmps[startno][oscoretype]['ownbh'] 
                        tbvalue = score * rst['points'] if is_sb else score
                    bhvalue.append({'played': played, 'tbvalue': tbvalue, 'score': score}) 
            # add unplayed rounds
            for x in range(len(bhvalue), rounds):
                score = tbscore['ownbh'] 
                tbvalue = 0.0 if is_sb else score
                bhvalue.append({'played': played, 'tbvalue': tbvalue, 'score': score}) 
            low = tb['modifiers']['low'] 
            if low > rounds:
                low = rounds 
            high = tb['modifiers']['high']
            if low + high > rounds: 
                high = rounds - low 
            while low > 0:
                sortall = sorted(bhvalue, key=lambda game: (game['score'], game['tbvalue']))
                sortexp = sorted(bhvalue, key=lambda game: (game['played'], game['score'], game['tbvalue']))
                if (tb['modifiers']['vun'] or sortall[0]['tbvalue'] > sortexp[0]['tbvalue']):
                    bhvalue = sortall[1:]
                else:
                    bhvalue = sortexp[1:]
                low -= 1
            if high > 0:
                if tb['modifiers']['vun']:
                    bhvalue = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))[high:]
                else:
                    bhvalue = sorted(bhvalue, key=lambda game: (game['played'], -game['score'], -game['tbvalue']))[high:]
            tbscore = cmp[sscoretype]
            tbscore[name] = 0   
            for game in bhvalue:
                tbscore[name] += game['tbvalue']
        return name

    def compute_ratingperformance(self, tb, cmps, scoretype, rounds):
        for startno, cmp in cmps.items():
            rscore = 0
            ratingopp = []
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds and rst['played'] and rst['opprating'] > 0:
                    rscore += rst['rpoints']
                    ratingopp.append(rst['opprating'])
            cmp[scoretype]['aro'] = rating.ComputeAverageRatingOpponents(ratingopp)
            cmp[scoretype]['tpr'] = rating.ComputeTournamentPerformanceRating(rscore, ratingopp)
            cmp[scoretype]['ptp'] = rating.ComputePerfectTournamentPerformance(rscore, ratingopp)
        return tb['name'].lower()


    def compute_boardcount(self, tb, cmps, scoretype, rounds):
        for startno, cmp in cmps.items():
            tbscore = cmp[scoretype]
            bc = 0
            for val, points in tbscore['bp'].items():
                bc += val * points
            tbscore['bc'] = bc
        return 'bc'

    def compute_singlerun_topbottomboardresult(self, tb, cmps, scoretype, rounds, ro, loopcount):
        if loopcount == 0:
            for player in ro:
                player[scoretype]['tbrval'] = 0
                player[scoretype]['bbeval'] = player[scoretype]['points']
            return True
        for player in range(0, len(ro)):
            ro[player][scoretype]['tbrval'] = ro[player][scoretype]['bp'][loopcount]
            ro[player][scoretype]['bbeval'] -= ro[player][scoretype]['bp'][self.maxboard - loopcount +1]
        return loopcount < self.maxboard

 

    def parse_tiebreak(self,  order, txt):
        #BH@23:IP#C1-P4F
        txt = txt.upper()
        comp = txt.split('#')
        if len(comp) == 1:
            comp = txt.split('-')
        nameparts = comp[0].split(':')
        name = nameparts[0]
        scoretype = 'x'
        if self.isteam:
            pointtype = 'mpoints'                         
        else:    
            pointtype = 'points'                         
        if len(nameparts) == 2:
            match nameparts[1].upper():
                case 'MP':
                    pointtype = 'mpoints'
                case 'GP':
                    pointtype = 'gpoints'
                case 'MM':
                    pointtype = ['mpoints', 'mpoints']
                case 'MG':
                    pointtype = ['mpoints', 'gpoints']
                case 'GM':
                    pointtype = ['gpoints', 'mpoints']
                case 'GG':
                    pointtype = ['gpoints', 'gpoints']
        modifiers = []  
        if len(comp) == 2:
            modifiers = comp[1].split('-')              
        tb = {'order': order,
              'name': name,
              'pointtype': pointtype,
              'modifiers': {'low': 0,
                            'high': 0,
                            'lim': 50,
                            'urd': False,
                            'p4f': self.rr,
                            'sws': False,
                            'fmo': False,
                            'rb5': False,
                            'z4h': False,
                            'vun': False
                            } 
                  }
        for mf in modifiers:
            mf = mf.upper()
            for index in range (0, len(mf)):  
                match mf[index]:
                    case 'C':
                        if mf[1:].isdigit():
                            tb['modifiers']['low'] = int(mf[1:])
                    case 'M':
                        if mf[1:].isdigit():
                            tb['modifiers']['low'] = int(mf[1:])
                            tb['modifiers']['high'] = int(mf[1:])
                    case 'L':
                        if mf[1:].isdigit():
                            tb['modifiers']['lim'] = int(mf[1:])
                    case 'U':
                        tb['modifiers']['urd'] = True;    
                    case 'P':
                        tb['modifiers']['p4f'] = True;    
                    case 'F':
                        tb['modifiers']['fmo'] = True;    
                    case 'R':
                        tb['modifiers']['rb5'] = True;    
                    case 'S':
                        tb['modifiers']['sws'] = True;    
                    case 'Z':
                        tb['modifiers']['z4h'] = True;    
                    case 'V':
                        tb['modifiers']['vun'] = True;    
#        print(tb)
        return tb
        
    def addval(self, cmps, scoretype, value):
        for startno, cmp in cmps.items():
            #print(scoretype, cmp[scoretype])
            cmp['tieBreak'].append(cmp[scoretype][value])
            
            

    def compute_average(self, name, cmps, scoretype, ignorezero):
        for startno, cmp in cmps.items():
            sum = 0
            num = 0
            for rnd, rst in cmp['rsts'].items():
                if rst['played'] and rst['opponent'] > 0:
                    opponent = rst['opponent']
                    value = cmps[opponent][scoretype][name]
                    if not ignorezero or value > 0:
                        num += 1
                        sum += value            
            cmp[scoretype]['avg'] = int(round(sum /num)) if num > 0 else 0
        return 'avg'
                             
    def compute_tiebreak(self, tb):
        cmps = self.cmps
        order = tb['order']
        tbname = ''
        if tb['pointtype'] == 'gpoints':
            scoretype = self.gamescore;
        else:
            scoretype = self.teamscore;
        match tb['name']:
            case 'PTS':
                tbname = 'points'
            case 'SNO' | 'RANK':
                tb['modifiers']['reverse'] = False
                tbname = tb['name'].lower()
            case 'DF':
                tbname = self.compute_direct_encounter(tb, cmps, scoretype, self.currentround)
            case 'DE':
                #tbname = self.compute_direct_encounter(tb, cmps, scoretype, self.currentround)
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, scoretype, self.currentround, self.compute_singlerun_direct_encounter)
            case 'WIN' | 'WON' | 'BPG' | 'BWG' | 'GE':
                tbname = tb['name'].lower()
            case 'PS':
                tbname = self.compute_progressive_scores(tb, cmps, scoretype, self.currentround)
            case 'BH' | 'FB' | 'SB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, scoretype, self.currentround)
            case 'AOB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, scoretype, self.currentround)
                tbname = self.compute_average('bh', cmps, scoretype, True)    
            case 'ARO' | 'TRP' | 'PTP' :
                tbname = self.compute_ratingperformance(tb, cmps, scoretype, self.currentround)
            case 'APRO' :
                tbname = self.compute_ratingperformance(tb, cmps, scoretype, self.currentround)
                tbname = self.compute_average('tpr', cmps, scoretype, True)    
            case 'APPO':
                tbname = self.compute_ratingperformance(tb, cmps, scoretype, self.currentround)
                tbname = self.compute_average('ptp', cmps, scoretype, True)
            case'BC':
                tb['modifiers']['reverse'] = False
                scoretype = self.gamescore;
                tbname = self.compute_boardcount(tb, cmps, scoretype, self.currentround)
            case'TBR' | 'BBE':
                tb['modifiers']['reverse'] = False
                scoretype = self.gamescore;
                tbname = self.compute_recursive_if_tied(tb, cmps, scoretype, self.currentround, self.compute_singlerun_topbottomboardresult)
            case _:
                tbname = None
                return

        self.tiebreaks.append(tb)
        index = len(self.tiebreaks) - 1 
        self.addval(cmps, scoretype, tbname)
        reverse = 1 if 'reverse' in tb['modifiers'] and not tb['modifiers']['reverse'] else -1
        #for cmp in self.rankorder:
        #    print(index, cmp['tieBreak'][index])
        self.rankorder = sorted(self.rankorder, key=lambda cmp: (cmp['rank'], cmp['tieBreak'][index]*reverse, cmp['cid']))
        rank = 1
        val = self.rankorder[0]['tieBreak'][index]
        for i in range(1, len(self.rankorder)):
            rank += 1
            if (self.rankorder[i]['rank'] == rank or self.rankorder[i]['tieBreak'][index] != val):
                self.rankorder[i]['rank'] = rank
                val = self.rankorder[i]['tieBreak'][index]
            else:
                self.rankorder[i]['rank'] = self.rankorder[i-1]['rank']
        #for i in range(0,len(self.rankorder)):
        #    t = self.rankorder[i]
        #    print(t['cid'], t['rank'], t['score'])
        #json.dump(self.cmps, sys.stdout, indent=2)
                    
                    
        