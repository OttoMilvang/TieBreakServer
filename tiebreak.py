# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Fri Aug  11 11:43:23 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
import math
from decimal import *

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
import helpers;

class tiebreak:

    

    # constructor function    
    def __init__(self, chessevent, tournamentno, currentround):
        event = chessevent.event
        tournament = chessevent.get_tournament(tournamentno)
        self.tiebreaks = []
        if tournament == None:
            return
        self.isteam = self.isteam = tournament['teamTournament'] if 'teamTournament' in tournament else False
        chessevent.update_tournament_random(tournament, self.isteam)
        self.rounds = tournament['numRounds']
        self.currentround = currentround if currentround >= 0 else self.rounds
        self.get_score = chessevent.get_score
        self.is_vur = chessevent.is_vur
        self.maxboard = 0
        self.lastplayedround = 0
        self.primaryscore = None # use default
        self.acceleration = tournament['acceleration'] if 'acceleration' in tournament else None   

        self.scoreLists = chessevent.scoreLists
        for scoresystem in event['scoreLists']:
            self.scoreLists[scoresystem['listName']] = scoresystem['scoreSystem']
        if self.isteam:
            self.matchscore = tournament['matchScoreSystem']
            self.gamescore = tournament['gameScoreSystem']
            [self.cplayers, self.cteam] = chessevent.build_tournament_teamcompetitors(tournament)
            self.allgames = chessevent.build_all_games(tournament, self.cteam, False)    
            self.teams = self.prepare_competitors(tournament, 'match')
            self.compute_score(self.teams, 'mpoints', self.matchscore, self.currentround)
            self.compute_score(self.teams, 'gpoints', self.gamescore, self.currentround)
        else:
            self.matchscore = tournament['gameScoreSystem']
            self.gamescore = tournament['gameScoreSystem']
            self.players = self.prepare_competitors(tournament, 'game')
            self.compute_score(self.players, 'points', self.gamescore, self.currentround)            
        self.cmps = self.teams if self.isteam  else self.players
        numcomp = len(self.cmps)
        self.rankorder = list(self.cmps.values()) 

        # find tournament type
        tt = tournament['tournamentType'].upper()
        #self.teamsize = round(len(tournament['playerSection']['results'])/ len(tournament['teamSection']['results'] )) if self.isteam else 1 
        self.teamsize = tournament['teamSize'] if 'teamSize' in tournament else 1 
        self.rr = False
        if tt.find('SWISS') >= 0:
            self.rr = False
        elif tt.find('RR') >= 0 or tt.find('ROBIN') >= 0 or tt.find('BERGER') >= 0: 
            self.rr = True
        elif numcomp == self.rounds + 1 or numcomp == self.rounds:
                self.rr = True
        elif numcomp == (self.rounds + 1)*2 or numcomp == self.rounds * 2:
            self.rr = True
    
    def prepare_competitors(self, tournament, scoretype):
        rounds = self.currentround
        #for rst in competition['results']: 
        #    rounds = max(rounds, rst['round'])
        #self.rounds = rounds
        ptype = 'mpoints' if self.isteam else 'points'
        #scoresystem = self.scoresystem['match']
        # Fill competition structure, replaze unplayed games with played=Fales, points=0.0    
        cmps = {}
        for competitor in tournament['competitors']:
            rnd = competitor['random'] if 'random' in competitor else 0
            cmp = {
                    'cid': competitor['cid'],
                    'rsts': {},
                    'orgrank': competitor['rank'] if 'rank' in competitor else 0,
                    'rank': 1,
                    'rating': (competitor['rating'] if 'rating' in competitor else 0),
                    'present': competitor['present'] if 'present' in competitor else True,
                    'tiebreakScore': [],
                    'tiebreakDetails': [],
                    'rnd': rnd,
                    'tbval': {}
                  }
            # Be sure that missing results are replaced by zero
            zero = self.scoreLists[scoretype]['Z']
            for rnd in range(1, rounds+1):
                cmp['rsts'][rnd] = {
                    ptype: zero, 
                    'rpoints': zero, 
                    'color': 'w', 
                    'played': False, 
                    'vur': True,
                    'rated': False, 
                    'opponent': 0,
                    'opprating': 0,
                    'board': 0,
                    'deltaR': 0 
                    } 
            cmps[competitor['cid']] = cmp
        for rst in tournament[scoretype + 'List']:
            if rst['round'] <= self.currentround or True:
                self.prepare_result(cmps, rst, self.matchscore)
                if self.isteam:
                    self.prepare_teamgames(cmps, rst, self.gamescore)
        #with open('C:\\temp\\cmps.json', 'w') as f:
            #json.dump(cmps, f, indent=2)
            #pass

        return cmps

    def prepare_result(self, cmps, rst, scoresystem):
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
                rst['bResult'] = self.scoreLists['reverse'][rst['wResult']]
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
        if (white> 0):
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
           self.lastplayedround = max(self.lastplayedround, rnd)
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
                'deltaR': (rating.ComputeDeltaR(Decimal(1.0)-expscore, brPoints) if not expscore == None else None  ) 
                }
        return

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
                    #print(rnd, white, black)
                    wVur = self.is_vur(game, 'white')
                    if self.cteam[white] == competitor and board > 0:
                        points = self.get_score(self.gamescore, game, 'white')
                        gpoints += points
                        games.append(
                            {
                                'points': points,
                                'rpoints': self.get_score('rating', game, 'white'),
                                'color': 'w',
                                'vur': wVur,
                                'played': game['played'],
                                'rated' : game['rated'] if 'rated' in rst else (game['played'] and black > 0), 
                                'player': white,
                                'opponent': black,
                                'board': board
                            }) 
                    if black > 0 and board > 0 and self.cteam[black] == competitor:
                        points = self.get_score(self.gamescore, game, 'black')
                        bVur = self.is_vur(game, 'black')
                        gpoints += points
                        games.append(
                            {
                                'points': points,
                                'rpoints': self.get_score('rating', game, 'black'),
                                'color': 'b',
                                'vur': bVur,
                                'played': game['played'],
                                'rated' : game['rated'] if 'rated' in rst else (game['played'] and black > 0), 
                                'player': black,
                                'opponent': white,
                                'board': board
                            })
                cmps[competitor]['rsts'][rnd]['gpoints'] = gpoints
                cmps[competitor]['rsts'][rnd]['games'] = games
        self.maxboard = max(self.maxboard, maxboard)
        #print('self.max', self.maxboard)
    
    
    def addtbval(self, obj, rnd, val):
        if rnd in obj:
            if type(val) == str:
                obj[rnd] = obj[rnd] + val
            else:
                obj[rnd] = obj[rnd] + val
        else: 
            obj[rnd] = val
        
    def compute_score(self, cmps, pointtype, scoretype, norounds):
        #scoresystem = self.scoresystem[scoretype]
        prefix = pointtype + "_" 
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            tbscore[prefix + 'sno'] = { 'val': startno }
            tbscore[prefix + 'rank'] = { 'val': cmp['orgrank'] }
            tbscore[prefix + 'rnd'] = { 'val': cmp['rnd'] }
            tbscore[prefix + 'cnt'] = { 'val' : 0 }    # count number of elements (why)
            tbscore[prefix + 'points'] = { 'val' : Decimal('0.0') } # total points
            tbscore[prefix + 'win'] = { 'val' : 0 }    # number of wins (played and unplayed)
            tbscore[prefix + 'won'] = { 'val' : 0 }    # number of won games over the board
            tbscore[prefix + 'bpg'] = { 'val' : 0 }    # number of black games played
            tbscore[prefix + 'bwg'] = { 'val' : 0 }    # number of games won with black
            tbscore[prefix + 'ge'] = { 'val' : 0 }     # number of games played + PAB
            tbscore[prefix + 'rep'] = { 'val' : 0 }    # number of rounds elected to play (same as GE)
            tbscore[prefix + 'vur'] = { 'val' : 0 }    # number of vurs (check algorithm)
            tbscore[prefix + 'cop'] = { 'val' : '' }   # color preference (for pairing)
            tbscore[prefix + 'cod'] = { 'val' : 0 }    # color difference (for pairing)
            tbscore[prefix + 'num'] = { 'val' : 0 }    # number of games played (for pairing)
            tbscore[prefix + 'lp'] =  0     # last round played 
            tbscore[prefix + 'lo'] = 0     # last round without vur
            tbscore[prefix + 'pfp'] = 0    # points from played games
            tbscore[prefix + 'lg'] = 0 #self.scoreLists[scoretype]['D'] # Result of last game
            tbscore[prefix + 'bp'] = {}    # Boardpoints
            #if startno == 1:
            #    helpers.json_output("c:\\temp\\new_trx_cmp_" + pointtype + '.json', cmp['rsts'])
            #cmpr = sorted(cmp, key=lambda p: (p['rank'], p['tbval'][prefix + name]['val'], p['cid']))
            #for rnd, rst in cmp['rsts'].items():
                #print(rnd, cmp['rsts'])
            #    if rnd <= norounds:
            for rnd in range(1, norounds+1):
                if rnd in cmp['rsts']:
                    rst = cmp['rsts'][rnd]
                    # total score
                    points = rst[pointtype] if pointtype in rst else 0
                    tbscore[prefix + 'points'][rnd] = points
                    tbscore[prefix + 'points']['val'] += points

                    # number of games
                    if self.isteam and scoretype == 'game':
                        gamelist = rst['games'] if 'games' in rst else []
                    else:
                        gamelist = [rst]
#                    if startno == 1: 
#                        print(pointtype, gamelist)
                    for game in gamelist:
                        #print(game)
                        if self.isteam and scoretype == 'game':
                            points = game['points']
                            if game['played'] and game['opponent'] <= 0:  # PAB
                                points = self.scoreLists[self.gamescore]['W']
                            board = game['board'];
                            tbscore[prefix + 'bp'][board] = tbscore[prefix + 'bp'][board]  + points if board in tbscore[prefix + 'bp']  else points
                        
                        self.addtbval(tbscore[prefix + 'cnt'], rnd, 1)   
                        self.addtbval(tbscore[prefix + 'cnt'], 'val', 1)
    
    
                        # result in last game
                        if rnd == self.rounds and game['opponent'] > 0:
                            tbscore[prefix + 'lg'] += points 
                            #if startno == 1:
                            #    print(pointtype, points, tbscore[prefix + 'lg'])
    
                        # points from played games    
                        if game['played']:
                            self.addtbval(tbscore[prefix + 'num'], rnd, game['opponent'])                                 
                            if game['opponent'] > 0:
                                self.addtbval(tbscore[prefix + 'num'], 'val', 1)                                 
                                tbscore[prefix + 'pfp'] += points
                                ocol = game['color']
                                ncol = ocol.upper() if ocol.upper() == tbscore[prefix + 'cop']['val'].upper() else ocol
                                pf = 1 if ocol == 'w' else -1
                                self.addtbval(tbscore[prefix + 'cod'], rnd, pf)
                                self.addtbval(tbscore[prefix + 'cod'], 'val', pf)
   
                                self.addtbval(tbscore[prefix + 'cop'], rnd, ncol)
                                tbscore[prefix + 'cop']['val'] = ncol
    
                            # last played game (or PAB)
                            if rnd > tbscore[prefix + 'lp']:
                                tbscore[prefix + 'lp'] = rnd
                            

                        # number of win
                        win = 1 if points == self.scoreLists[scoretype]['W'] else 0
                        self.addtbval(tbscore[prefix + 'win'], rnd, win)
                        self.addtbval(tbscore[prefix + 'win'], 'val', win)
    
                        # number of win played over the board
                        won = 1 if points == self.scoreLists[scoretype]['W'] and game['played'] and game['opponent'] > 0  else 0
                        self.addtbval(tbscore[prefix + 'won'], rnd, won)
                        self.addtbval(tbscore[prefix + 'won'], 'val', won)
    
                        # number of games played with black
                        bpg = 1 if game['color'] == 'b' and game['played'] else 0
                        self.addtbval(tbscore[prefix + 'bpg'], rnd, bpg)
                        self.addtbval(tbscore[prefix + 'bpg'], 'val', bpg)
                            
                        # number of win played with black
                        bwg = 1 if game['color'] == 'b' and game['played'] and points == self.scoreLists[scoretype]['W'] else 0
                        self.addtbval(tbscore[prefix + 'bwg'], rnd, bwg)
                        self.addtbval(tbscore[prefix + 'bwg'], 'val', bwg)
    
                        # number of games elected to play
                        #ge = 1 if game['played'] or (game['opponent'] > 0 and points == self.scoreLists[scoretype]['W']) else 0
                        ge = 1 if game['played'] or (points == self.scoreLists[scoretype]['W']) else 0
                        self.addtbval(tbscore[prefix + 'ge'], rnd, ge)
                        self.addtbval(tbscore[prefix + 'ge'], 'val', ge)
                        self.addtbval(tbscore[prefix + 'rep'], rnd, ge)
                        self.addtbval(tbscore[prefix + 'rep'], 'val', ge)
    
                        vur = 1 if game['vur'] else 0
                        self.addtbval(tbscore[prefix + 'vur'], rnd, vur)
                        self.addtbval(tbscore[prefix + 'vur'], 'val', vur)
    
                        # last round with opponent, pab or fpb (16.2.1, 16.2.2, 16.2.3 and 16.2.4)
                        if rnd > tbscore[prefix + 'lo'] and (vur == 0):
                            tbscore[prefix + 'lo'] = rnd



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
            moreloops = compute_singlerun(tb,cmps, rounds, [], loopcount)
            moretodo = moretodo or moreloops
            ro = sorted(ro, key=lambda p: (p['rank'], p['tbval'][prefix + name]['val'], p['cid']))
        #print('L=' + str(loopcount))
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

           

    def compute_basic_direct_encounter(self, tb, cmps, rounds, subro, loopcount, points, scoretype, prefix):
        name = tb['name'].lower()
        (xpoints, xscoretype, prefix) = self.get_scoreinfo(tb, True)
        changes = 0
        rpos = loopcount - tb['modifiers']['swap']   # Report pos
        postfix =  ' ' + scoretype[0] if tb['name'] == 'EDE' else '' 
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
                                  num = de['delist'][opponent]['cnt']
                                  sumscore = score * num
                                  de['deval'] -= score
                                  num += 1
                                  sumscore += rst[points]
                                  score = sumscore / num
                                  de['denum'] = 1
                                  de['deval'] += score
                                  de['delist'][opponent]['cnt'] = 1 
                                  de['delist'][opponent]['score'] = score
                              else:
                                  de['denum'] += 1
                                  de['deval'] += rst[points]
                                  de['delist'][opponent] = { 'cnt': 1,
                                                             'score': rst[points]
                                                            }
            #if not tb['modifiers']['p4f'] and de['denum'] < metmax:
            #if (not tb['modifiers']['p4f'] and de['denum'] < metmax) or tb['modifiers']['sws']:
            if (not self.rr and de['denum'] < metmax) or tb['modifiers']['sws']:
                metall = False
                de['demax'] = de['deval'] + (metmax - de['denum']) * self.scoreLists[scoretype]['W'] * (self.teamsize if points == 'gpoints' else 1)
                #print('F', metmax, de['deval'], de['demax'], de['denum'])
            else:
                de['demax'] = de['deval']
                #print('T', metmax, de['deval'], de['demax'], de['denum'])
        if metall: # 6.2 All players have met
            #print("T")
            subro = sorted(subro, key=lambda p: (-p['tbval']['deval'], p['cid']))
            crank = rank = subro[0]['tbval'][prefix + name]['val']
            val = subro[0]['tbval']['deval']
            sprefix = '\t' if rpos in subro[0]['tbval'][prefix + name] else ''
            self.addtbval(subro[0]['tbval'][prefix + name], rpos, sprefix + str(val) + postfix)    
            for i in range(1, len(subro)):
                rank += 1
                de = subro[i]['tbval']
                if (val != de['deval']):
                    crank = de[prefix + name]['val'] = rank
                    val = de['deval']
                    changes += 1
                else:
                    de[prefix + name]['val'] = crank
                sprefix = '\t' if rpos in de[prefix + name] else ''
                self.addtbval(de[prefix + name], rpos, sprefix + str(val) + postfix)    
        else: # 6.2 swiss tournament
            #print("F")
            subro = sorted(subro, key=lambda p: (-p['tbval']['deval'], -p['tbval']['demax'], p['cid']))
            crank = rank = subro[0]['tbval'][prefix + name]['val']
            val = subro[0]['tbval']['deval']
            maxval = subro[0]['tbval']['demax']
            sprefix = '\t' if rpos in subro[0]['tbval'][prefix + name] else ''
            self.addtbval(subro[0]['tbval'][prefix + name], rpos, sprefix + str(val) + '/' + str(maxval) + postfix)    
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
                sprefix = '\t' if rpos in de[prefix + name] else ''
                self.addtbval(de[prefix + name], rpos,  sprefix + str(val) + '/' + str(maxval) + postfix)    
                #self.addtbval(de[prefix + name], rpos,  str(val) + '/' + str(maxval) + postfix)    
        #print(loopcount, scoretype, changes)
        return changes


    def compute_singlerun_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        tb['modifiers']['swap'] = 0
        changes = 1 if loopcount == 0 else 0
        if loopcount > 0 and len(subro) > 0:
            changes = self.compute_basic_direct_encounter(tb, cmps, rounds, subro, loopcount, points, scoretype, prefix)
        return changes                

    def compute_singlerun_ext_direct_encounter(self, tb, cmps, rounds, subro, loopcount):
        name = tb['name'].lower()
        (points, scoretype, prefix) = self.get_scoreinfo(tb, loopcount == 0 or tb['modifiers']['primary'])
        changes = 0
        if loopcount == 0:
            tb['modifiers']['primary'] = True
            tb['modifiers']['points'] = points
            (spoints, secondary, sprefix) = self.get_scoreinfo(tb, False)
            tb['modifiers']['loopcount'] = 0
            tb['modifiers']['edechanges'] = {scoretype: 0, secondary: 1 }
            tb['modifiers']['swap'] = 0
            return True
        if tb['modifiers']['loopcount'] != loopcount:
            #print(scoretype)
            tb['modifiers']['loopcount'] = loopcount
            tb['modifiers']['changes'] = 0
        if len(subro) == 0: 
            if tb['modifiers']['changes'] == 0:
                tb['modifiers']['primary'] = not tb['modifiers']['primary']
                tb['modifiers']['edechanges'][scoretype] = 0
                tb['modifiers']['swap'] += 1
                ro = self.rankorder
                for player in ro:
                    player['tbval']['moreloops'] = True  # 'de' rank value initial value = rank
            else:
                (spoints, secondary, sprefix) = self.get_scoreinfo(tb, not tb['modifiers']['primary'])
                tb['modifiers']['edechanges'][secondary] = 1
            retsum = tb['modifiers']['edechanges']['match'] + tb['modifiers']['edechanges']['game']
            #print('E', loopcount, tb['modifiers']['changes'], retsum, tb['modifiers']['edechanges'])
            return retsum > 0  and loopcount < 30
        changes = self.compute_basic_direct_encounter(tb, cmps, rounds, subro, loopcount, points, scoretype, prefix)
        tb['modifiers']['changes'] += changes
        #print(loopcount, tb['modifiers']['scoretype'], tb['modifiers']['edechanges'], changes)
        #print(len(subro),loopcount, changes, tb['modifiers']['edechanges'], scoretype)
        return changes > 0 and loopcount < 30

        

    def copmute_progressive_score(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        low = tb['modifiers']['low'] 
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            ps = 0
            ssf = 0 # Sum so far
            tbscore[prefix + 'ps'] = { 'val': ps, 'cut': []}
            for rnd in range(1, rounds+1):
                p = cmp['rsts'][rnd][points] if rnd in cmp['rsts']  and points in cmp['rsts'][rnd] else Decimal('0.0')
                ssf += p
                #p = p * (rounds+1-rnd) 
                tbscore[prefix + 'ps'][rnd] = ssf
                if rnd <= low:
                    tbscore[prefix + 'ps']['cut'].append(rnd)
                else:                    
                    ps += ssf
            tbscore[prefix + 'ps']['val'] = ps
        return 'ps'
              

    def copmute_koya(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        plim = tb['modifiers']['plim'] 
        nlim = tb['modifiers']['nlim'] 
        lim = plim * self.scoreLists[scoretype]['W']*rounds * (self.teamsize if points == 'gpoints' else 1)/ Decimal('100.0') + nlim
        #print(lim)
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            ks = 0
            tbscore[prefix + 'ks'] = {'val':ks, 'cut': [] }
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    if opponent > 0:
                        oppscore = cmps[opponent]['tbval'][prefix + 'points']['val']
                        ownscore = cmp['tbval'][prefix + 'points'][rnd]
                        tbscore[prefix + 'ks'][rnd] = ownscore          
                        if oppscore  >= lim:
                            ks += ownscore
                        else:
                            tbscore[prefix + 'ks']['cut'].append(rnd)
            tbscore[prefix + 'ks']['val'] = ks
        return 'ks'


            
    def compute_buchholz_sonneborn_berger(self, tb, cmps, rounds):
        name = tb['name'].lower()
        isfb = name == 'fb' or name == 'afb' or tb['modifiers']['fmo']
        (opoints, oscoretype, oprefix) = self.get_scoreinfo(tb, True)
        (spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, name == 'sb')
        opointsfordraw = self.scoreLists[oscoretype]['D'] * (self.teamsize if opoints == 'gpoints' else 1)
        spointsfordraw = self.scoreLists[sscoretype]['D'] * (self.teamsize if spoints == 'gpoints' else 1)
        #print(opointsfordraw, spointsfordraw)
        name = tb['name'].lower()
        if name == 'aob': 
            name = 'bh'
        is_sb = name == 'sb' or name == 'esb' or (len(name) == 5 and name[0] == 'e' and name[3:5] == 'sb')
        if name == 'esb' or (len(name) == 5 and name[0] == 'e' and name[3:5] == 'sb'):
            (spoints, sscoretype, sprefix) = self.get_scoreinfo(tb, False)
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            tbscore[oprefix + 'abh'] = { 'val' : 0 }     # Adjusted score for BH (check algorithm)
            # 16.3.2    Unplayed rounds of category 16.2.5 are evaluated as draws.
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    points_no_opp = Decimal(0.0) if self.rr else opointsfordraw
                    tbval = rst[opoints] if rnd <= tbscore[oprefix + 'lo'] or rst['opponent'] > 0 else points_no_opp
                    tbscore[oprefix + 'abh'][rnd] = tbval
                    tbscore[oprefix + 'abh']['val'] += tbval
            fbscore = tbscore[oprefix + 'points']['val']
            if isfb and rst['opponent'] > 0 and tbscore[oprefix + 'lo'] == self.rounds:
                #print(startno, tbscore[oprefix + 'abh']['val'], tbscore[oprefix + 'abh']['val'] - tbscore[oprefix + 'lg'] + opointsfordraw)
                adjust = opointsfordraw - tbscore[oprefix + 'lg']
                #print(tbscore[oprefix + 'lg'])
                tbscore[oprefix + 'abh'][self.rounds] += adjust 
                tbscore[oprefix + 'abh']['val'] += adjust
                fbscore += adjust
                #print(self.rounds, isfbandlastround)
            tbscore[oprefix + 'ownscore'] = fbscore
        if name == 'abh' or name == 'afb':
            return('abh')

        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            bhvalue = [] 
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds:
                    opponent = rst['opponent']
                    vur = rst['vur']
                    played = True if tb['modifiers']['p4f'] or (isfb and rnd == self.rounds) else rst['played']
                    if played and opponent > 0:
                        vur = False
                        score = cmps[opponent]['tbval'][oprefix + 'abh']['val']
                        #if startno == 2:
                        #    print(startno, rnd, isfbandlastround)
                    elif not self.rr:
                        score = cmps[startno]['tbval'][oprefix + 'ownscore']
                        #       cmps[startno]['tbval'][oprefix + 'points']['val']
                    else:                        
                        score = 0
                    #print(startno, rnd, opponent,played, vur, score)
                    if tb['modifiers']['urd'] and not self.rr:
                        sres = spointsfordraw
                    else:
                        sres = rst[spoints] if spoints in rst else Decimal('0.0')
                    tbvalue = score * sres if is_sb else score
                    #if  opponent >  0 or not tb['modifiers']['p4f'] :
                    bhvalue.append({'vur': vur, 'tbvalue': tbvalue, 'score': score, 'rnd': rnd }) 
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
                sortexp = sorted(bhvalue, key=lambda game: (-game['vur'], game['score'], game['tbvalue']))
                if (tb['modifiers']['vun'] or sortall[0]['tbvalue'] > sortexp[0]['tbvalue']):
                    bhvalue = sortall[1:]
                    tbscore[oprefix + name]['cut'].append(sortall[0]['rnd'])
                    #print(startno, low, 'ALL', sortall[0]['rnd'], sortexp[0]['rnd'])
                else:
                    bhvalue = sortexp[1:]
                    tbscore[oprefix + name]['cut'].append(sortexp[0]['rnd'])
                    #print(startno, low, 'VUR', sortexp[0]['rnd'], sortexp[0]['rnd'])
                low -= 1

            while high > 0:
                sortall = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))
                #sortexp = sorted(bhvalue, key=lambda game: (-game['vur'], -game['score'], -game['tbvalue'])) // No execption on high
                sortexp = sorted(bhvalue, key=lambda game: (-game['score'], -game['tbvalue']))
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
            trounds = 0
            for rnd, rst in cmp['rsts'].items():
                if rnd <= rounds and rst['played'] and rst['opponent'] > 0:
                    trounds += 1
                if rnd <= rounds and rst['played'] and rst['opprating'] > 0:
                    rst['rnd'] = rnd
                    ratingopp.append(rst)
                    self.addtbval(cmp['tbval'][prefix + 'aro'], rnd, rst['opprating'])
                    self.addtbval(cmp['tbval'][prefix + 'tpr'], rnd, rst['opprating'])
                    self.addtbval(cmp['tbval'][prefix + 'ptp'], rnd, rst['opprating'])
            #trounds = rounds  // This is correct only if unplayed gmes are cut.
            low = tb['modifiers']['low'] 
            if low > rounds:
                low = rounds 
            high = tb['modifiers']['high']
            if low + high > rounds: 
                high = rounds - low 
            while low > 0:
                if trounds == len(ratingopp):  
                    newopp = sorted(ratingopp, key=lambda p: (p['opprating']))
                    if len(newopp) > 0:
                        tbscore[prefix + name]['cut'].append(newopp[0]['rnd'])
                    ratingopp = newopp[1:] 
                trounds -= 1
                low -= 1
            while high > 0:
                if trounds == len(ratingopp):
                    newopp = sorted(ratingopp, key=lambda p: (p['opprating']))
                    if len(newopp) > 0:
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
        if len(ro) == 0:
            return False
        for player in range(0, len(ro)):
            #helpers.json_output('-', ro[player]['tbval'])
            #print(self.maxboard, loopcount, self.maxboard - loopcount +1)
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

    def compute_score_strength_combination(self, tb, cmps, currentround):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        for startno, cmp in cmps.items():
            dividend = cmp['tbval'][prefix + 'sssc']['val']
            divisor = 1 
            key = points[0]
            if key == 'm':
                score = cmp['tbval']["gpoints_" + 'points']['val']    
                divisor = math.floor(self.scoreLists[scoretype]['W'] * currentround / self.scoreLists[self.gamescore]['W'] / self.maxboard)
            elif key == 'g':
                score = cmp['tbval']["mpoints_" + 'points']['val']    
                divisor = math.floor(self.scoreLists[scoretype]['W'] * currentround *  self.maxboard / self.scoreLists[self.matchscore]['W'])
            if tb['modifiers']['nlim'] > 0:
                divisor = tb['modifiers']['nlim']
            val = (score + dividend / divisor).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)    
            cmp['tbval'][prefix + 'sssc'] = { 'val': val }     
        return 'sssc'


    def get_accelerated(self, rnd, startno):
        if self.acceleration == None:
            return 'Z'
        for val in self.acceleration['values']:
            if rnd >= val['firstRound'] and rnd <= val['lastRound'] and startno >= val['firstCompetitor'] and startno <= val['lastCompetitor']:
                return val['score']
        return 'Z'

    def compute_acc(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        if prefix + 'acc' in cmps[1]['tbval']:
            return 'acc'
        scorelist = self.scoreLists[scoretype]

        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            acc = self.get_accelerated(1, startno)
            val = self.scoreLists[scoretype][acc] 
            tbscore[prefix + 'acc'] = { 'val': val, 0: val }
            spoints = 0 #Points so far
            for rnd in range(1, rounds+1):
                p = cmp['rsts'][rnd][points] if rnd in cmp['rsts']  and points in cmp['rsts'][rnd] else Decimal('0.0')
                spoints += p
                acc = self.get_accelerated(rnd+1, startno)
                val = spoints + self.scoreLists[scoretype][acc] 
                tbscore[prefix + 'acc'][rnd] = val
            tbscore[prefix + 'acc']['val'] = val
        return 'acc'
              

    def compute_flt(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        scorelist = self.scoreLists[scoretype]
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            tbscore[prefix + 'flt'] = { 'val': 0 }
            sfloat = 0 # Float so far
            for rnd in range(1, rounds+1):
                sfloat //= 4
                p = cmp['rsts'][rnd][points] if rnd in cmp['rsts']  and points in cmp['rsts'][rnd] else Decimal('0.0')
                opp = cmp['rsts'][rnd]['opponent'] if rnd in cmp['rsts']  and 'opponent' in cmp['rsts'][rnd] else 0
                if opp > 0: 
                    ownacc = cmp['tbval'][prefix + 'acc'][rnd-1]
                    oppacc = cmps[opp]['tbval'][prefix + 'acc'][rnd-1]                    
                elif p > scorelist['L']:
                    ownacc = 1
                    oppacc = 0
                else:
                    ownacc = 0
                    oppacc = 0
                if ownacc > oppacc:
                    cfloat = 'd'
                    ifloat = 8
                elif ownacc < oppacc:
                    cfloat = 'u'
                    ifloat = 4
                else:
                    cfloat = ' '
                    ifloat = 0
                if rnd == 1 and cfloat =='u':
                    #print(startno, opp)
                    #print(cmp['tbval'])
                    #print(cmps[opp]['tbval'])
                    pass
                self.addtbval(tbscore[prefix + 'flt'], rnd, cfloat) 
                sfloat += ifloat
            tbscore[prefix + 'flt']['val'] = sfloat
        return 'flt'
              

    def compute_rfp(self, tb, cmps, rounds):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        #print(self.lastplayedround)
        for startno, cmp in cmps.items():
            tbscore = cmp['tbval']
            val = True  
            tbscore[prefix + 'rfp'] = { 'val': val }
            for rnd in range(1, rounds+2):
                val = True
                if rnd in cmp['rsts']:
                    val = cmp['rsts'][rnd]['played'] or (cmp['rsts'][rnd]['opponent'] > 0)
                elif rnd > self.lastplayedround:
                    val = cmp['present']
                else: 
                    val = False
                if rnd <= rounds:
                    tbscore[prefix + 'rfp'][rnd] = val
            tbscore[prefix + 'rfp']['val'] = val
        return 'rfp'


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
        # BH@23:IP/C1-P4F
        txt = txt.upper()
        comp = txt.replace('!', '/').replace('#', '/').split('/', 2)
        #if len(comp) == 1:
        #    comp = txt.split('-')
        nameparts = comp[0].split(':')
        nameyear = nameparts[0].split('@')
        nameyear.append('24')
        name = nameyear[0]
        year = int(nameyear[1])
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

        tb = {'order': order,
              'name': name,
              'year': year,
              'pointtype': pointtype,
              'modifiers': {'low': 0,
                            'high': 0,
                            'plim': Decimal('50.0'),
                            'nlim' : Decimal('0.0'),
                            'urd': False,
                            'p4f': False,
                            'sws': False,
                            'fmo': False,
                            'rb5': False,
                            'z4h': False,
                            'vun': False
                            } 
                  }
        for mf in comp[1:]:
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
                        scale = Decimal('1.0') if '.' in mf else Decimal(0.5)
                        numbers = mf.replace('.','')
                        if mf[1:].isdigit():
                            tb['modifiers']['plim'] = Decimal(mf[1:])
                        elif mf[1] == '+' and numbers[2:].isdigit():
                            tb['modifiers']['nlim'] = Decimal(mf[2:]) *scale
                        elif mf[1] == '-' and numbers[2:].isdigit():
                            tb['modifiers']['nlim'] = -Decimal(mf[2:]) *scale
                    case 'K':
                        if mf[1:].isdigit():
                            tb['modifiers']['nlim'] = Decimal(mf[1:])
                    case 'U':
                        tb['modifiers']['urd'] = True;    
                    case 'P':
                        tb['modifiers']['p4f'] = True;    
                    case 'F':
                        tb['modifiers']['fmo'] = True;    
                    case 'R':
                        tb['modifiers']['rb5'] = True;    
                    case 'd.S':
                        tb['modifiers']['sws'] = True;    
                    case 'Z':
                        tb['modifiers']['z4h'] = True;    
                    case 'V':
                        tb['modifiers']['vun'] = True;    
        if self.rr and (tb['modifiers']['sws']) == False:  # Default for RR is to treat unplayed games as played
            tb['modifiers']['p4f'] = True
        return tb
        
    def addval(self, cmps, tb, value):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        precision = 0
        for startno, cmp in cmps.items():
            #print(prefix, scoretype, cmp['tbval'])
            cmp['tiebreakScore'].append(cmp['tbval'][prefix + value]['val'])
            cmp['tiebreakDetails'].append(cmp['tbval'][prefix + value])
            if isinstance(cmp['tbval'][prefix + value]['val'], Decimal):
                (s,n,e) = cmp['tbval'][prefix + value]['val'].as_tuple()
                precision = min(precision, e)
        tb['precision'] = -precision      
            

    def compute_average(self, tb, name, cmps, rounds, ignorezero, norm):
        (points, scoretype, prefix) = self.get_scoreinfo(tb, True)
        tbname = tb['name'].lower()
        for startno, cmp in cmps.items():
            cmp['tbval'][prefix + tbname] = {'val': 0, 'cut':[] } 
            sum = Decimal(0.0)
            num = 0
            for rnd, rst in cmp['rsts'].items():
                if rst['played'] and rst['opponent'] > 0 and rnd <= rounds:
                    opponent = rst['opponent']
                    value = cmps[opponent]['tbval'][prefix + name]['val']
                    if not ignorezero or value > 0:
                        num += 1
                        sum += value            
                        self.addtbval(cmp['tbval'][prefix + tbname], rnd, value)
            val = sum / Decimal(num) if num > 0 else Decimal('0.0') 
            cmp['tbval'][prefix + tbname]['val'] = val.quantize(Decimal(norm), rounding=ROUND_HALF_UP)
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
        match key:
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
            case 'DE':
                #tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, self.currentround, self.compute_singlerun_direct_encounter)
            case 'EDE':
                #tbname = self.compute_direct_encounter(tb, cmps, self.currentround)
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, self.currentround, self.compute_singlerun_ext_direct_encounter)
            case 'WIN' | 'WON' | 'BPG' | 'BWG' | 'GE' |  'REP' | 'VUR' | 'NUM' | 'COP' | 'COD':
                tbname = tb['name'].lower()
            case 'PS':
                tbname = self.copmute_progressive_score(tb, cmps, self.currentround)
            case 'KS':
                tbname = self.copmute_koya(tb, cmps, self.currentround)
            case 'BH' | 'FB' | 'SB' | 'ABH' | 'AFB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
            case 'AOB':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'bh', cmps, self.currentround, True, '0.01')    
            case 'ARO' | 'TPR' | 'PTP' :
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
            case 'APRO' :
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'tpr', cmps, self.currentround, True, '1.')    
            case 'APPO':
                tbname = self.compute_ratingperformance(tb, cmps, self.currentround)
                tbname = self.compute_average(tb, 'ptp', cmps, self.currentround, True, '1.')
            case 'ESB' | 'EMMSB' | 'EMGSB' | 'EGMSB' | 'EGGSB':
                if len(tb['name']) == 5:
                    tb['pointtype'] = tb['name'][1:3].lower() + 'points'
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
            case'BC':
                tb['modifiers']['reverse'] = False
                tbname = self.compute_boardcount(tb, cmps, self.currentround)
            case'TBR' | 'BBE':
                tb['modifiers']['reverse'] = False
                tbname = self.compute_recursive_if_tied(tb, cmps, self.currentround, self.compute_singlerun_topbottomboardresult)
            case'SSSC':
                tbname = self.compute_buchholz_sonneborn_berger(tb, cmps, self.currentround)
                tbname = self.compute_score_strength_combination(tb, cmps, self.currentround)
            case 'ACC':
                tbname = self.compute_acc(tb, cmps, self.currentround)
            case 'FLT':
                tbname = self.compute_acc(tb, cmps, self.currentround)
                tbname = self.compute_flt(tb, cmps, self.currentround)
            case 'RFP':
                tbname = self.compute_rfp(tb, cmps, self.currentround)
            case _:
                tbname = None
                return

        self.tiebreaks.append(tb)
        index = len(self.tiebreaks) - 1 
        self.addval(cmps, tb, tbname)
        reverse = 1 if 'reverse' in tb['modifiers'] and not tb['modifiers']['reverse'] else -1
        #for cmp in self.rankorder:
        #    print(index, cmp['tiebreakScore'][index])
        self.rankorder = sorted(self.rankorder, key=lambda cmp: (cmp['rank'], cmp['tiebreakScore'][index]*reverse, cmp['cid']))
        rank = 1
        val = self.rankorder[0]['tiebreakScore'][index]
        for i in range(1, len(self.rankorder)):
            rank += 1
            if (self.rankorder[i]['rank'] == rank or self.rankorder[i]['tiebreakScore'][index] != val):
                self.rankorder[i]['rank'] = rank
                val = self.rankorder[i]['tiebreakScore'][index]
            else:
                self.rankorder[i]['rank'] = self.rankorder[i-1]['rank']
        #for i in range(0,len(self.rankorder)):
        #    t = self.rankorder[i]
        #    print(t['cid'], t['rank'], t['score'])
        #json.dump(self.cmps, sys.stdout, indent=2)
                    
                    
        