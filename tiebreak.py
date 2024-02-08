# -*- coding: utf-8 -*-
"""
Created on Fri Aug  11 11:43:23 2023

@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
import math
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
|                   tbval: {  - intermediate results from tb calculations }
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
        chessevent.update_tournament_random(tournament, self.isteam)
        self.currentround = 0
        self.rounds = tournament['numRounds']
        self.get_score = chessevent.get_score
        self.is_vur = chessevent.is_vur
        self.maxboard = 0
        self.primaryscore = None # use default

        self.scoreList = {}
        for name, scoresystem in chessevent.scoreList.items():
            self.scoreList[name] = scoresystem
        for scoresystem in event['scoreLists']:
            for key, value in scoresystem['scoreSystem'].items():
                self.scoreList[scoresystem['listName']][key] = value
        if self.isteam:
            self.matchscore = tournament['teamSection']['scoreSystem']
            self.gamescore = tournament['playerSection']['scoreSystem']
            [self.cplayers, self.cteam] = chessevent.build_tournament_teamcompetitors(tournament)
            self.allgames = chessevent.build_all_games(tournament, self.cteam, False)    
            self.teams = self.prepare_competitors(tournament['teamSection'], 'match')
            self.compute_score(self.teams, 'mpoints', self.matchscore, self.currentround)
            self.compute_score(self.teams, 'gpoints', self.gamescore, self.currentround)
        else:
            self.matchscore = tournament['playerSection']['scoreSystem']
            self.gamescore = tournament['playerSection']['scoreSystem']
            self.players = self.prepare_competitors(tournament['playerSection'], 'game')
            self.compute_score(self.players, 'points', self.gamescore, self.currentround)            
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
            rnd = competitor['random'] if 'random' in competitor else 0
            cmp = {
                    'cid': competitor['cid'],
                    'rsts': {},
                    'orgrank': competitor['rank'],
                    'rank': 1,
                    'rating': (competitor['rating'] if 'rating' in competitor else 0),
                    'tieBreak': [],
                    'calculations': [],
                    'rnd': rnd,
                    'tbval': {}
                  }
            cmps[competitor['cid']] = cmp
        for rst in competition['results']: 
            rounds = self.prepare_result(cmps, rst, self.matchscore, rounds)
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
        wVur = self.is_vur(rst, 'white')
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
            bVur = self.is_vur(rst, 'black')
            if (rst['played']):
                if 'rating' in cmps[white] and cmps[white]['rating'] > 0:
                    wrating = cmps[white]['rating']
                if 'rating' in cmps[black] and cmps[black]['rating'] > 0:
                    brating = cmps[black]['rating']
                expscore = rating.ComputeExpectedScore(wrating, brating)
        board = rst['board'] if 'board' in rst else 0
        cmps[white]['rsts'][rnd] = {
            ptype: wPoints, 
            'rpoints': wrPoints, 
            'color': 'w', 
            'played': rst['played'], 
            'vur': wVur,
            'rated': rst['rated'] if 'rated' in rst else (rst['played'] and black > 0), 
            'opponent': black,
            'opprating': brating,
            'board': board,
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
                'vur' : bVur,
                'rated': rst['rated']  if 'rated' in rst else (rst['played'] and white > 0),
                'opponent': white,
                'opprating': wrating,
                'board': board,
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
                    board = game['board'] if 'board' in game else 0
                    maxboard = max(maxboard, board)
                    if self.cteam[white] == competitor and board > 0:
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
                                'board': board
                            }) 
                    if black > 0 and board > 0 and self.cteam[black] == competitor:
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
                                'board': board
                            })
                cmps[competitor]['rsts'][rnd]['gpoints'] = gpoints
                cmps[competitor]['rsts'][rnd]['games'] = games
        self.maxboard = max(self.maxboard, maxboard)
    
    
    def addtbval(self, obj, rnd, val):
        if rnd in obj:
            if type(val) == str:
                obj[rnd] = obj[rnd] + "\t" + val
            else:
                obj[rnd] = obj[rnd] + val
        else: 
            obj[rnd] = val
        
    def compute_score(self, cmps, pointtype, scoretype, rounds):
#        scoresystem = self.scoresystem[scoretype]
        prefix = pointtype + "_" 
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            tbscore[prefix + 'sno'] = { 'val': startno }
            tbscore[prefix + 'rank'] = { 'val': cmp['orgrank'] }
            tbscore[prefix + 'rnd'] = { 'val': cmp['rnd'] }
            tbscore[prefix + 'num'] = { 'val' : 0 }    # number of elements
            tbscore[prefix + 'points'] = { 'val' : 0 } # total points
            tbscore[prefix + 'win'] = { 'val' : 0 }    # number of wins (played and unplayed)
            tbscore[prefix + 'won'] = { 'val' : 0 }    # number of won games over the board
            tbscore[prefix + 'bpg'] = { 'val' : 0 }    # number of black games played
            tbscore[prefix + 'bwg'] = { 'val' : 0 }    # number of games won with black
            tbscore[prefix + 'ge'] = { 'val' : 0 }     # number of games played + PAB
            tbscore[prefix + 'lp'] =  0     # last round played 
            tbscore[prefix + 'lo'] = 0     # last round with opponent
            tbscore[prefix + 'pfp'] = 0    # points from played games
            tbscore[prefix + 'lg'] = self.scoreList[scoretype]['D'] # Result of last game
            tbscore[prefix + 'bp'] = {}    # Boardpoints
            for rnd, rst in cmp['rsts'].items():
                # total score
                points = rst[pointtype]
                tbscore[prefix + 'points'][rnd] = points
                tbscore[prefix + 'points']['val'] += points
                # number of games
                if self.isteam and scoretype == 'game':
                    gamelist = rst['games']
                else:
                    gamelist = [rst]
                for game in gamelist:
                    if self.isteam and scoretype == 'game':
                        points = game['points']
                        if game['played'] and game['opponent'] <= 0:  # PAB
                            points = self.scoreList[self.gamescore]['W']
                        board = game['board'];
                        tbscore[prefix + 'bp'][board] = tbscore[prefix + 'bp'][board]  + points if board in tbscore[prefix + 'bp']  else points
                    
                    self.addtbval(tbscore[prefix + 'num'], rnd, 1)
                    self.addtbval(tbscore[prefix + 'num'], 'val', 1)

                    # last round with opponent, pab or fpb (16.2.1, 16.2.2, 16.2.3 and 16.2.4)
                    if rnd > tbscore[prefix + 'lo'] and (game['played'] or game['opponent'] > 0 or points == self.scoreList[scoretype]['W']):
                        tbscore[prefix + 'lo'] = rnd

                    # result in last game
                    if rnd == self.rounds and game['opponent'] > 0:
                        tbscore[prefix + 'lg'] = points 

                    # points from played games    
                    if game['played'] and game['opponent'] > 0:
                        tbscore[prefix + 'pfp'] += points

                    # last played game (or PAB)
                    if rnd > tbscore[prefix + 'lp'] and game['played']:
                        tbscore[prefix + 'lp'] = rnd
                        
                    # number of win
                    win = 1 if points == self.scoreList[scoretype]['W'] else 0
                    self.addtbval(tbscore[prefix + 'win'], rnd, win)
                    self.addtbval(tbscore[prefix + 'win'], 'val', win)

                    # number of win played over the board
                    won = 1 if points == self.scoreList[scoretype]['W'] and game['played'] else 0
                    self.addtbval(tbscore[prefix + 'won'], rnd, won)
                    self.addtbval(tbscore[prefix + 'won'], 'val', won)

                    # number of games played with black
                    bpg = 1 if game['color'] == 'b' and game['played'] else 0
                    self.addtbval(tbscore[prefix + 'bpg'], rnd, bpg)
                    self.addtbval(tbscore[prefix + 'bpg'], 'val', bpg)
                        
                    # number of win played with black
                    bwg = 1 if game['color'] == 'b' and game['played'] and points == self.scoreList[scoretype]['W'] else 0
                    self.addtbval(tbscore[prefix + 'bwg'], rnd, bwg)
                    self.addtbval(tbscore[prefix + 'bwg'], 'val', bwg)

                    # number of games elected to play
                    ge = 1 if game['played'] or (game['opponent'] > 0 and points == self.scoreList[scoretype]['W']) else 0
                    self.addtbval(tbscore[prefix + 'ge'], rnd, ge)
                    self.addtbval(tbscore[prefix + 'ge'], 'val', ge)



    def compute_recursive_if_tied(self, tb, cmps, rounds, compute_singlerun):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        name = tb['name'].lower()
        ro = self.rankorder
        for player in ro:
            player['tbval'][prefix + name] = {}
            player['tbval'][prefix + name]['val'] = player['rank']  # rank value initial value = rank
            player['tbval']['moreloops'] = True  #  As long as True we have more to check
        loopcount = 0
        moretodo = compute_singlerun(tb, cmps, rounds, ro, loopcount)
        while moretodo:
            moretodo = False
            loopcount += 1
            start = 0;
            while start < len(ro):
                currentrank = ro[start]['tbval'][prefix + name]['val']
                for stop in range( start+1,  len(ro)+1):
                    if stop == len(ro) or currentrank !=  ro[stop]['tbval'][prefix + name]['val']:
                        break
                # we have a range start .. stop-1 to check for top board result
                #print("start-stop", start, stop)
                if ro[start]['tbval']['moreloops']:
                    if stop - start == 1:
                        moreloops = False
                        ro[start]['tbval']['moreloops'] = moreloops
                    else:
                        subro = ro[start:stop] # subarray of rankorder
                        moreloops = compute_singlerun(tb,cmps, rounds, subro, loopcount) 
                        for player in subro:
                            player['tbval']['moreloops'] = moreloops  # 'de' rank value initial value = rank
                        moretodo = moretodo or moreloops
                start = stop            
            #json.dump(ro, sys.stdout, indent=2)
            ro = sorted(ro, key=lambda p: (p['rank'], p['tbval'][prefix + name]['val'], p['cid']))
            
        # reorder 'tb' 
        start = 0;
        while start < len(ro):
            currentrank = ro[start]['rank']
            for stop in range( start,  len(ro)+1):
                if stop == len(ro) or currentrank !=  ro[stop]['rank']:
                    break
                # we have a range start .. stop-1 to check for direct encounter
            offset = ro[start]['tbval'][prefix + name]['val']
            if ro[start]['tbval'][prefix + name]['val'] != ro[stop-1]['tbval'][prefix + name]['val']:
                offset -=1 
            for p in range(start, stop):
                ro[p]['tbval'][prefix + name]['val'] -= offset
            start = stop
        return name

           


    def compute_singlerun_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        name = tb['name'].lower()
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        if loopcount == 0:
            tb['modifiers']['points'] = points
            tb['modifiers']['scoretype'] = scoretype
            tb['modifiers']['edechanges'] = 0
            return True
        points = tb['modifiers']['points'] 
        scoretype = tb['modifiers']['scoretype'] 
        changes = 0
        currentrank = subro[0]['tbval'][prefix + name]['val']
        metall = True          # Met all opponents on same range
        metmax = len(subro)-1  # Max number of opponents
        for player in range(0, len(subro)):
            de = subro[player]['tbval']
            de['denum'] = 0    # number of opponens
            de['deval'] = 0    # sum score against of opponens
            de['demax'] = 0    # sum score against of opponens, unplayed = win
            de['delist'] = { }  # list of results numgames, score, maxscore 
            for rnd, rst in subro[player]['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                          played = True if tb['modifiers']['p4f'] else rst['played']
                          if played and cmps[opponent]['tbval'][prefix + name]['val'] == currentrank:
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
                #print('F', metmax, de['deval'], de['demax'], de['denum'])
            else:
                de['demax'] = de['deval']
                #print('T', metmax, de['deval'], de['demax'], de['denum'])
        if metall: # 6.2 All players have met
            subro = sorted(subro, key=lambda p: (-p['tbval']['deval'], p['cid']))
            crank = rank = subro[0]['tbval'][prefix + name]['val']
            val = subro[0]['tbval']['deval']
            self.addtbval(subro[0]['tbval'][prefix + name],loopcount, val)    
            for i in range(1, len(subro)):
                rank += 1
                de = subro[i]['tbval']
                if (val != de['deval']):
                    crank = de[prefix + name]['val'] = rank
                    val = de['deval']
                    changes += 1
                else:
                    de[prefix + name]['val'] = crank
                self.addtbval(de[prefix + name], loopcount, val)    
        else: # 6.2 swiss tournament
            subro = sorted(subro, key=lambda p: (-p['tbval']['deval'], -p['tbval']['demax'], p['cid']))
            crank = rank = subro[0]['tbval'][prefix + name]['val']
            val = subro[0]['tbval']['deval']
            maxval = subro[0]['tbval']['demax']
            self.addtbval(subro[0]['tbval'][prefix + name],loopcount, str(val) + '/' + str(maxval))    
            unique = True
            for i in range(1, len(subro)):
                rank += 1
                de = subro[i]['tbval']
                if (unique and val > de['demax']):
                    crank = de[prefix + name]['val'] = rank
                    val = de['deval']
                    maxval = de['demax']
                    changes += 1
                else:
                    val = de['deval']
                    maxval = de['demax']
                    de[prefix + name]['val'] = crank
                    unique = False
                self.addtbval(de[prefix + name],loopcount, str(val) + '/' + str(maxval))    
        tb['modifiers']['edechanges'] += changes
        if changes == 0 and tb['name'] == 'EDE':
            if tb['modifiers']['edechanges'] > 0:
                tb['modifiers']['points'] = self.reverse_pointtype(tb['modifiers']['points'])
                tb['modifiers']['scoretype'] = self.matchscore if tb['modifiers']['points'][0] == 'm' else self.gamescore
                changes = 1
                tb['modifiers']['edechanges'] = 0
                ro = self.rankorder
                for player in ro:
                    player['tbval']['moreloops'] = True  # 'de' rank value initial value = rank
        return changes > 0 and loopcount < 30

        

    def copmute_progressive_score(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        low = tb['modifiers']['low'] 
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            ps = 0
            tbscore[prefix + 'ps'] = { 'val': ps, 'cut': []}
            for rnd in range(1, rounds+1):
                p = cmp['rsts'][rnd][points] if rnd in cmp['rsts'] else 0.0
                p = p * (rounds+1-rnd)
                tbscore[prefix + 'ps'][rnd] = p
                if rnd <= low:
                    tbscore[prefix + 'ps']['cut'].append(rnd)
                else:                    
                    ps += p
            tbscore[prefix + 'ps']['val'] = ps
        return 'ps'
              

    def copmute_koya(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        lim = tb['modifiers']['lim'] 
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            ks = 0
            tbscore[prefix + 'ks'] = {'val':ks, 'cut': [] }
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                        val = cmp['tbval'][prefix + 'points']['val']
                        tbscore[prefix + 'ks'][rnd] = val          
                        if val + 0.000001  >= lim * self.scoreList[scoretype]['W']*rounds / 100:
                            ks += val
                        else:
                            tbscore[prefix + 'ks']['cut'].append(rnd)
            tbscore[prefix + 'ks']['val'] = ks
        return 'ks'


            
    def compute_buchholz_sonneborn_berger(self, tb, cmps, rounds):
        (opoints, oscoretype, oprefix) = self.get_scoreinfo(tb, True)
        (spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, True)
        name = tb['name'].lower()
        if name == 'aob': 
            name = 'bh'
        is_sb = name == 'sb' or name == 'esb'
        if name == 'esb':
            (spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, False)
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            # 16.3.2    Unplayed rounds of category 16.2.5 are evaluated as draws.
            tbscore[oprefix + 'ownbh'] = 0
            for rnd, rst in cmp['rsts'].items():
                if rnd <= tbscore[oprefix + 'lo']:
                    tbscore[oprefix + 'ownbh'] += rst[opoints]
            tbscore[oprefix + 'ownbh'] = tbscore[oprefix + 'ownbh'] + (rounds - tbscore[oprefix + 'lo']) * self.scoreList[oscoretype]['D']  # own score used for bh
            if name == 'fb' and tbscore[oprefix + 'lo'] == self.rounds:
                tbscore[oprefix + 'ownbh'] = tbscore[oprefix + 'ownbh'] - tbscore[oprefix + 'lg'] + self.scoreList[oscoretype]['D']
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            bhvalue = [] 
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    vur = rst['vur']
                    if opponent > 0:
                        played = True if tb['modifiers']['p4f'] else rst['played']
                        if played or not tb['modifiers']['urd']:
                            score = cmps[opponent]['tbval'][oprefix + 'ownbh']
                            tbvalue = score * rst[spoints] if is_sb else score
                        else:
                            score = cmps[startno]['tbval'][oprefix + 'ownbh']
                            tbvalue = score * rst[spoints] if is_sb else score
                    else:
                        played = False
                        score = cmps[startno]['tbval'][oprefix + 'ownbh'] 
                        tbvalue = score * rst[spoints] if is_sb else score
                    bhvalue.append({'played': not vur, 'tbvalue': tbvalue, 'score': score, 'rnd': rnd }) 
            # add unplayed rounds
            for rnd in range(len(bhvalue), rounds):
                score = tbscore[sprefix + 'ownbh'] 
                tbvalue = 0.0 if is_sb else score
                bhvalue.append({'played': False, 'tbvalue': tbvalue, 'score': score, 'rnd': rnd}) 
            tbscore = cmp['tbval']
            tbscore[oprefix + name] ={ 'val' : 0, 'cut': [] }
            for game in bhvalue:
                self.addtbval(tbscore[oprefix + name], game['rnd'], game['tbvalue'])

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
                    tbscore[oprefix + name]['cut'].append(sortall[0]['rnd'])
                else:
                    bhvalue = sortexp[1:]
                    tbscore[oprefix + name]['cut'].append(sortexp[0]['rnd'])
                low -= 1

            while high > 0:
                sortall = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))
                sortexp = sorted(bhvalue, key=lambda game: (game['played'], -game['score'], -game['tbvalue']))
                if tb['modifiers']['vun']:
                    bhvalue = sortall[1:]
                    tbscore[oprefix + name]['cut'].append(sortall[0]['rnd'])
                else:
                    bhvalue = sortexp[1:]
                    tbscore[oprefix + name]['cut'].append(sortexp[0]['rnd'])
                high -= 1

#            if high > 0:
#                if tb['modifiers']['vun']:
#                    bhvalue = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))[high:]
#                else:
#                    bhvalue = sorted(bhvalue, key=lambda game: (game['played'], -game['score'], -game['tbvalue']))[high:]

            for game in bhvalue:
                self.addtbval(tbscore[oprefix + name], 'val', game['tbvalue'])
        return name

    def compute_ratingperformance(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        name = tb['name'].lower()
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            tbscore[prefix + 'aro'] = { 'val': 0, 'cut': [] } 
            tbscore[prefix + 'tpr'] = { 'val': 0, 'cut': [] }
            tbscore[prefix + 'ptp'] = { 'val': 0, 'cut': [] }
            ratingopp = []
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds and rst['played'] and rst['opprating'] > 0:
                    rst['rnd'] = rnd
                    ratingopp.append(rst)
                    self.addtbval(cmp['tbval'][prefix + 'aro'], rnd, rst['opprating'])
                    self.addtbval(cmp['tbval'][prefix + 'tpr'], rnd, rst['opprating'])
                    self.addtbval(cmp['tbval'][prefix + 'ptp'], rnd, rst['opprating'])
            trounds = rounds
            low = tb['modifiers']['low'] 
            if low > rounds:
                low = rounds 
            high = tb['modifiers']['high']
            if low + high > rounds: 
                high = rounds - low 
            while low > 0:
                if trounds == len(ratingopp):
                    newopp = sorted(ratingopp, key=lambda p: (p['opprating']))
                    tbscore[prefix + name]['cut'].append(newopp[0]['rnd'])
                    ratingopp = newopp[1:] 
                trounds -= 1
                low -= 1
            while high > 0:
                if trounds == len(ratingopp):
                    newopp = sorted(ratingopp, key=lambda p: (p['opprating']))
                    tbscore[prefix + name]['cut'].append(newopp[-1]['rnd'])
                    ratingopp = newopp[:-1]
                trounds -= 1
                high -= 1
            rscore = 0
            ratings = []
            for p in ratingopp:
                rscore += p['rpoints']
                ratings.append(p['opprating'])
                
                   
            tbscore[prefix + 'aro']['val'] = rating.ComputeAverageRatingOpponents(ratings) 
            tbscore[prefix + 'tpr']['val'] = rating.ComputeTournamentPerformanceRating(rscore, ratings)
            tbscore[prefix + 'ptp']['val'] = rating.ComputePerfectTournamentPerformance(rscore, ratings)
        return tb['name'].lower()


    def compute_boardcount(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            bc = 0
            tbscore[prefix + 'bc'] = { 'val': bc }
            for val, points in tbscore['gpoints_' + 'bp'].items():
                bc += val * points
                self.addtbval(tbscore[prefix + 'bc'], val, val*points)
            tbscore[prefix + 'bc']['val'] = bc
        return 'bc'

    def compute_singlerun_topbottomboardresult(self, tb, cmps,  rounds, ro, loopcount):
        name = tb['name'].lower()
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        if loopcount == 0:
            for player in ro:
                player['tbval']['tbrval'] = 0
                player['tbval']['bbeval'] = player['tbval']['gpoints_' + 'points']['val']
            return True
        for player in range(0, len(ro)):
            ro[player]['tbval']['tbrval'] = ro[player]['tbval']['gpoints_' + 'bp'][loopcount]
            ro[player]['tbval']['bbeval'] -= ro[player]['tbval']['gpoints_' + 'bp'][self.maxboard - loopcount +1]
        subro = sorted(ro, key=lambda p: (-p['tbval'][name + 'val'], p['cid']))
        count = currentrank = ro[0]['tbval'][prefix + name]['val']
        for player in range(0, len(subro)):
            if subro[player]['tbval'][name + 'val'] != subro[player - 1]['tbval'][name + 'val']:
                currentrank = count
            subro[player]['tbval'][prefix + name]['val'] = currentrank
            self.addtbval(subro[player]['tbval'][prefix + name], loopcount, subro[player]['tbval'][name + 'val'])    
            #print(">", loopcount, subro[player]['cid'], subro[player]['tbval']['mpoints_tbr'], subro[player]['tbval']['tbrval'], subro[player]['tbval']['moreloops'])
            count += 1
        return loopcount < self.maxboard

    def compute_score_Strength_combination(self, tb, cmps, currentround):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            dividend = cmp['tbval'][prefix + 'sssc']['val']
            divisor = 1 
            key = points[0]
            if key == 'm':
                score = cmp['tbval']["gpoints_" + 'points']['val']    
                divisor = math.floor(self.scoreList[scoretype]['W'] * currentround / self.scoreList[self.gamescore]['W'] / self.maxboard)
            elif key == 'g':
                score = cmp['tbval']["mpoints_" + 'points']['val']    
                divisor = math.floor(self.scoreList[scoretype]['W'] * currentround *  self.maxboard / self.scoreList[self.matchscore]['W'])
            cmp['tbval'][prefix + 'sssc'] = { 'val': score + dividend / divisor }
      
        return 'sssc'


 

    def reverse_pointtype(self, txt):
        match txt:
            case 'mpoints':
                return 'gpoints'
            case 'gpoints':
                return 'mpoints'
            case 'mmpoints':
                return 'ggpoints'
            case 'mgpoints':
                return 'gmpoints'
            case 'gmpoints':
                return 'mgpoints'
            case 'ggpoints':
                return 'mmgpoints'
        return txt
      
    def parse_tiebreak(self,  order, txt):
        # BH@23:IP!C1-P4F
        txt = txt.upper()
        comp = txt.split('!')
        if len(comp) == 1:
            comp = txt.split('#')
        if len(comp) == 1:
            comp = txt.split('-')
        nameparts = comp[0].split(':')
        name = nameparts[0]
        scoretype = 'x'
        if self.primaryscore != None:
            pointtype = self.primaryscore    
        elif self.isteam:
            pointtype = 'mpoints'                         
        else:    
            pointtype = 'points'                         
        if name == "MPTS":
          pointtype = 'mpoints'
        if name == "GPTS":
            pointtype = 'gpoints'

        if len(nameparts) == 2:
            match nameparts[1].upper():
                case 'MP':
                    pointtype = 'mpoints'
                case 'GP':
                    pointtype = 'gpoints'
                case 'MM':
                    pointtype = 'mmpoints'
                case 'MG':
                    pointtype = 'mgpoints'
                case 'GM':
                    pointtype = 'gmpoints'
                case 'GG':
                    pointtype = 'ggpoints'
        if self.primaryscore == None and (name == "PTS" or name == "MPTS" or name == "GPTS") :
            self.primaryscore = pointtype
        #if name == 'MPVGP':
        #    name = 'PTS'
        #        pointtype = self.reverse_pointtype(self.primaryscore)

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
                            'p4f': False,
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
        if self.rr and (tb['modifiers']['sws']) == False:  # Default for RR is to treat unplayed games as played
            tb['modifiers']['p4f'] = True
        return tb
        
    def addval(self, cmps, tb, value):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            #print(prefix, scoretype, cmp['tbval'])
            cmp['tieBreak'].append(cmp['tbval'][prefix + value]['val'])
            cmp['calculations'].append(cmp['tbval'][prefix + value])
            
            

    def compute_average(self, tb, name, cmps, ignorezero):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        tbname = tb['name'].lower()
        for startno, cmp in cmps.items():
            cmp['tbval'][prefix + tbname] = {'val': 0, 'cut':[] } 
            sum = 0
            num = 0
            for rnd, rst in cmp['rsts'].items():
                if rst['played'] and rst['opponent'] > 0:
                    opponent = rst['opponent']
                    value = cmps[opponent]['tbval'][prefix + name]['val']
                    if not ignorezero or value > 0:
                        num += 1
                        sum += value            
                        self.addtbval(cmp['tbval'][prefix + tbname], rnd, value)
            cmp['tbval'][prefix + tbname]['val'] = int(round(sum /num)) if num > 0 else 0
        return tbname
 
    # get_scoreinfo(self, tb, primary)
    # tb - tie break
    # primary or secondary score



    def get_scoreinfo(self, tb, primary):
        pos = 0 if primary else 1;
        key = tb['pointtype'][pos]
        if not primary and (key != 'g' and key != 'm'):
            key = tb['pointtype'][0]
            if (key == 'g'):
                key = 'm'
            elif (key == 'm'):
                key = 'g'
        match tb['pointtype'][pos]:
            case 'g':
                return ["gpoints", self.gamescore, "gpoints_"]
            case 'm':
                return ["mpoints", self.matchscore, "mpoints_"]
            case _:
                return ["points", self.gamescore, "points_"]

                                
    def compute_tiebreak(self, tb):
        cmps = self.cmps
        order = tb['order']
        tbname = ''
        match tb['name']:
            case 'PTS' | 'MPTS' | 'GPTS':
                tbname = 'points'
            case 'MPVGP':
                tb['pointtype'] =  self.reverse_pointtype(self.primaryscore)
                tbname = 'points'
            case 'SNO' | 'RANK' | 'RND':
                tb['modifiers']['reverse'] = False
                tbname = tb['name'].lower()
            case 'DF':
                tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
            case 'DE' | 'EDE':
                #tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, self.currentround, self.compute_singlerun_direct_encounter)
            case 'WIN' | 'WON' | 'BPG' | 'BWG' | 'GE':
                tbname = tb['name'].lower()
            case 'PS':
                tbname = self.copmute_progressive_score(tb, cmps, self.currentround)
            case 'KS':
                tbname = self.copmute_koya(tb, cmps, self.currentround)
            case 'BH' | 'FB' | 'SB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
            case 'AOB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'bh', cmps, True)    
            case 'ARO' | 'TPR' | 'PTP' :
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
            case 'APRO' :
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'tpr', cmps, True)    
            case 'APPO':
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'ptp', cmps, True)
            case 'ESB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
            case'BC':
                tb['modifiers']['reverse'] = False
                tbname = self.compute_boardcount(tb, cmps, self.currentround)
            case'TBR' | 'BBE':
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, self.currentround, self.compute_singlerun_topbottomboardresult)
            case'SSSC':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
                tbname = self.compute_score_Strength_combination(tb, cmps, self.currentround)
            case _:
                tbname = None
                return

        self.tiebreaks.append(tb)
        index = len(self.tiebreaks) - 1 
        self.addval(cmps, tb, tbname)
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
                    
                    
        