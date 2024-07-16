# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Thu Oct 19 11:55:32 2023
@author: Otto Milvang, sjakk@milvang.no
"""

import sys
import json
from decimal import *
import xml.etree.ElementTree as ET
import chessjson
import helpers

class ts2json(chessjson.chessjson):

    

    def __init__(self):
        super().__init__()
        self.debug = True
        self.event['origin'] = 'ts2json ver. 1.00'
        self.pcompetitors = {} # pointer to player section competitors
        self.bcompetitors = {} # pointer to team competitors via 1st board player
        self.tcompetitors = {} # pointer to team section competitors
        self.event['ratingLists'] = [{ 'listName': 'Local',
                          'listDescription': 'Local rating'
                        },{
                          'listName': 'FIDE',
                          'listDescription': 'FIDE standard rating'
                        },{
                          'listName': 'FIDErapid',
                          'listDescription': 'FIDE rapid rating'
                        },{
                          'listName': 'FIDEblitz',
                          'listDescription': 'FIDE blitz rating'
                        }]
                            
        self.isteam = False
                            


# ==============================
#
# Read TS file

    def parse_file(self, lines, verbose):
        event = ET.fromstring(lines)
        if event.tag != 'Tournament':
            return 1  # Not a TS file 
        self.parse_ts_tournament_attrib(event.attrib)
        for child in event:
            match child.tag:
                case 'Web':
                    self.parse_ts_web(child.attrib)
                case 'Groups':
                    for key, value in child.attrib.items():
                        match key:
                            case 'Num':
                                '3'
                            case 'SeparateFile':
                                'N'
                    tournamentno = 0 
                    for group in child:
                        if group.tag == 'Group':
                            tournamentno += 1
                            tournament = self.parse_ts_group(group, tournamentno)
                            if self.isteam:
                                self.prepare_team_section(tournament)
                            else:
                                self.prepare_player_section(tournament)
                            self.update_results(tournament['gameList'])
                            self.update_tournament_rating(tournament)
                            self.update_tournament_teamcompetitors(tournament)
                            self.update_tournament_random(tournament, self.isteam)

        return
                    

    def parse_ts_tournament_attrib(self, attrib):
        # Chief arbiter
        ca = {
            'id': -1,
            'fideId': 0,
            'firstName': '',
            'lastName': '',
            'fideName': '',
            'sex': 'u',
            'federation': '',
            'fideOTitle': ''
            }
        da = {
            'id': -1,
            'fideId': 0,
            'firstName': '',
            'lastName': '',
            'fideName': '',
            'sex': 'u',
            'federation': '',
            'fideOTitle': ''
            }        
        org = {
            'id': -1,
            'fideId': 0,
            'firstName': '',
            'lastName': '',
            'fideName': '',
            'sex': 'u',
            'federation': '',
            'fideOTitle': ''
            }        
        other = self.event['eventInfo']['other'] = {}
        for key, value in attrib.items(): 
            match key:
                case 'Dataversion':
                    '01.00'
                case 'Producer': 
                    self.event['origin'] = self.event['origin'] + ', from ' + value
                case 'TeamEvent': 
                   self.isteam = other['teamEvent'] = (value == 'Y')
                case 'Event': 
                    self.event['eventName'] = value
                    self.event['eventInfo']['fullName'] = value
                case 'Organiser':
                    self.parse_ts_arbiter(org, value)
                case 'Arbiter': 
                    self.parse_ts_arbiter(ca, value)
                case 'ArbiterFideId':
                    if value != '':
                        ca['id'] = 1
                        ca['fideId'] = int(value)
                case 'ArbiterEmail': 
                    if value != '':
                        ca['id'] = 1
                        ca['email'] = value
                case 'DeputyArbiter': 
                    self.parse_ts_arbiter(da, value)
                case 'DeputyArbiterFideId': 
                    if value != '':
                        da['id'] = 1
                        da['fideId'] = int(value)
                case 'DeputyArbiterEmail': 
                    if value != '':
                        da['id'] = 1
                        da['email'] = value
                case 'Treasurer': 
                    'Otto Milvang'
                case 'Site': 
                    self.event['eventInfo']['site'] = value
                case 'Federation': 
                    self.event['eventInfo']['federation'] = value
                case 'StartDate': 
                    self.event['eventInfo']['startDate'] = helpers.parse_date(value)
                case 'EndDate': 
                    self.event['eventInfo']['endDate'] = helpers.parse_date(value)
                case 'LogoFile':
                    ''
                case 'MemberFile':
                    ''
                case 'dflt_Available': 
                    ''
                case 'LichessVerify':
                    '' 
                case 'TStoken':
                    ''
                case 'PaymentVipps':
                    ''
                case 'PaymentOptional':
                    '' 
                case 'Name':
                    '' 
                case 'Phone':
                    '' 
                case 'OrgNo':
                    ''
                case _:
                    self.print_warning('parse_ts_tournament_attrib: ' + key + ' not matched')

        if org['id'] == 0:
            if not 'organizers' in self.event['eventInfo']:
                self.event['eventInfo']['organizers'] = {
                    'chiefOrganizer': self.append_profile(org),
                    'chiefSecretariat': 0,
                    'organizers': [],
                    'secretaries': []
                    }
        if ca['id'] == 0 or da['id'] == 0:
            if not 'arbiters' in self.event['eventInfo']:
                self.event['eventInfo']['arbiters'] = {
                    'chiefArbiter': self.append_profile(ca),
                    'deputyChiefArbiters': [ self.append_profile(da) ],
                    'ratingOfficer': 0,
                    'arbiters': []
                    }
        return
                
        
    def parse_ts_web(self, attrib):
        other = self.event['eventInfo']['other']
        for key, value in attrib.items(): 
            match key:
                case 'HTMLFile': 
                    other['htmlFile'] = value
                case 'BaseURL':
                    self.event['eventInfo']['website'] = value
                case 'WebserverID':
                    other['webserverId'] = value
                case 'WebPublishInterval':
                    other['webPublishInterval'] = value
                case 'LastEnrollTime':
                    other['lastEnrollTime'] = helpers.parse_date(value)
                case 'PublishEnrollPage':
                    other['PublishEnrollPage'] = helpers.parse_int(value)
                case 'PublishSerial': 
                    other['PublishSerial'] = helpers.parse_int(value)
                case 'PublishRoundReports':
                    other['PublishRoundReports'] = (value == 'Y')
                case 'PublishLivegames': 
                    other['PublishLivegames'] = (value == 'Y')
                case 'LiveGamesURL': 
                    other['LiveGamesURL'] = value
                case 'MaxNumEnrolled':
                    other['MaxNumEnrolled'] = helpers.parse_int(value)
                case 'PublishPayedStatus': 
                    other['PublishPayedStatus'] = value
                case 'WebPublishConfidentiality':
                    other['MaxNumEnrolled'] = helpers.parse_int(value)
                case 'ClonoToken':
                    other['ClonoToken'] = value
                case 'ClonoT_id':
                    other['ClonoT_id'] = helpers.parse_int(value)
                case 'ClonoPublishLevel':
                    other['ClonoPublishLevel'] = helpers.parse_int(value)
                case 'ClonoCategory':
                    other['ClonoCategory'] = helpers.parse_int(value)
                case 'ClonoT_uid':
                    other['ClonoT_id'] = value
                case 'ClonoTokenDate':
                    other['ClonoTokenDate'] = helpers.parse_date(value)
                case 'CheckinAllowed':
                    other['CheckinAllowed'] = value
                case _:
                    self.print_warning('parse_ts_web: ' + key + ' not matched')
        return


# ==============================
#
# Read tournamentb in TS file
#

                        

    def parse_ts_group(self, group, tournamentno):
        tournament = {
            'tournamentNo': tournamentno,
            'name': '',
            'tournamentType': 'Tournament',
    	    'tournamentInfo': {},
            'ratingList': 'Local',
            'numRounds': 0,
            'rounds' : [],
            'currentRound': 0,
            'teamTournament': self.event['eventInfo']['other']['teamEvent'],
            'rankOrder': [{
                'order': 1,
                'name': 'PTS'
                }],
            'competitors': [],
            'gameScoreSystem': 'game',
            'matchScoreSystem': 'match',
            'gameList': [],
            'matchList': [],
            'other': {}
        };

        
        self.parse_ts_group_attrib(group.attrib, tournament)
        for child in group:
            match child.tag:
                case 'Rounds':
                    self.parse_ts_group_rounds(child, tournament)
                case 'TieBreaksBy':
                    self.parse_ts_group_order(child, tournamentno, 'TieBreaksBy')
                case 'IndividualTieBreaksBy':
                    self.parse_ts_group_order(child, tournamentno, 'IndividualTieBreaksBy')
                case 'PairingGroupBy':
                    self.parse_ts_group_order(child, tournamentno, 'PairingGroupBy')
                case 'PrizeGroups':
                    self.parse_ts_group_prize(child, tournamentno)
                case 'ColWidths':
                    self.parse_ts_group_layout(child, tournamentno)
                case 'Reportsettings':
                    self.parse_ts_group_report(child, tournamentno)
                case 'Players':
                    self.parse_ts_group_players(child, tournament)
                case 'Teams':
                    self.parse_ts_group_teams(child, tournament)
                case _:
                    self.print_warning('parse_ts_group tag: ' + child.tag + ' not matched')

        self.event['tournaments'].append(tournament)
        return tournament
 


    def parse_ts_group_attrib(self, attrib, tournament):
        ca = {
            'id': -1,
            'fideId': 0,
            'firstName': '',
            'lastName': '',
            'fideName': '',
            'sex': 'u',
            'federation': '',
            'fideOTitle': ''
           }
        da = {
            'id': -1,
            'fideId': 0,
            'firstName': '',
            'lastName': '',
            'fideName': '',
            'sex': 'u',
            'federation': '',
            'fideOTitle': ''
           }
        #competition = tournament['teamSection'] if self.isteam else tournament['playerSection']
        scoresystem = {}
        frr = 1
        info = tournament['tournamentInfo']
        other = tournament['other']
        for key, value in attrib.items(): 
            match key:
                case 'Event':
                    tournament['name'] = value
                case 'Site': 
                    info['site'] = value
                    'Drammen, Norway'
                case 'Arbiter': 
                    self.parse_ts_arbiter(ca, value)
                case 'DeputyArbiter': 
                    self.parse_ts_arbiter(da, value)
                case 'StartDate': 
                    info['startDate'] = helpers.parse_date(value)
                case 'EndDate': 
                    info['endDate'] = helpers.parse_date(value)
                case 'ActiveRound':
                    tournament['currentRound'] = helpers.parse_int(value)
                case 'NumRounds': 
                    tournament['numRounds'] = helpers.parse_int(value)
                case 'LocalRatingCategory': 
                    other['localRatingCategory'] = helpers.parse_int(value)
                case 'RatingFactorA': 
                    other['ratingFactorA'] = helpers.parse_float(value)
                case 'RatingFactorB': 
                    other['ratingFactorB'] = helpers.parse_float(value)
                case 'RatingFactorC':
                    other['ratingFactorC'] = helpers.parse_float(value)
                case 'MaxMeets': 
                    tournament['maxMeet'] = helpers.parse_int(value)
                case 'PairingAccellerated': 
                    if value == 'Y':
                        tournament['accelerated'] = 'BAKU2016'
                    else:
                        tournament['accelerated'] = ''
                case 'AccelleratedLastGaSn': 
                    other['accelleratedLastGaSn'] = helpers.parse_int(value)
                case 'Pairing': 
                    tournament['tournamentType'] = value
                case 'FirstRatedRound': 
                    ffr = helpers.parse_int(value)
                case 'PointsForWin': 
                    todo = 1
                    scoresystem['W'] = helpers.parse_float(value)
                case 'PointsForLoss': 
                    todo = 1
                    scoresystem['L'] = helpers.parse_float(value)
                case 'PointsForBye':
                    todo = 1
                    if (value == 'd'):
                        scoresystem['P'] = 'D'
                    if (value == '+'):
                        scoresystem['P'] = 'W'
                case 'PostponedCalcAs': 
                    todo = 1
                    #scoresystem['A'] = value
                case 'RankPerClass': 
                    'N'
                case 'ShowRankNum':
                    '0'
                case 'Tie-breakOnStartno': 
                    'Y'
                case 'ActiveElo': 
                    tournament['ratingList'] = value
                case 'ShowAllTiebreaks': 
                    'Y'
                case 'SubmissionIndex':
                    '0'
                case 'EventCode': 
                    ''
                case 'YouthEvent': 
                    'N'
                case 'NumTiebreakGames': 
                    '1' 
                case 'SrchLocalLists': 
                    'Y'
                case 'SrchFideLists': 
                    'Y'
                case 'ClonoRd':
                    '0' 
                case 'ReportedRounds':
                    '8, 9, 10, 11, 12, 13, 14, 15, 16, 17' 
                case 'LastBulkPairing':
                    ''
                case 'JuniorFee':
                    '0' 
                case 'SeniorFee': 
                    '0'
                case 'NumBoards':
                    tournament['teamSize'] = helpers.parse_int(value)
                case 'HomeGuestNaming':
                    'Y'
                case 'Clr':
                    'W'
                case _:
                    self.print_warning('parse_ts_group attrib: ' + key + '=' + value + ' not matched')
        todo = 1
        if (scoresystem['W'] == Decimal('3.0') and scoresystem['L'] == Decimal('1.0')):
            tournament['playerSection']['scoreSystem'] = 'children'
        elif (scoresystem['W'] == Decimal('3.0') and scoresystem['L'] == Decimal('0.0')):
            tournament['playerSection']['scoreSystem'] = 'football'
#        match scoresystem['W']:
#            case 1.0:
#                scoresystem['D'] = 0.5
##            case 2.0:
 #               scoresystem['D'] = 1.0
 #           case 3.0:
#                scoresystem['D'] = scoresystem['L'] + 1.0
#        if scoresystem['P'] == '+':
#            scoresystem['P'] = 'W'
#        if scoresystem['P'] == '=':
#            scoresystem['P'] = 'D'
#        if scoresystem['A'] == '+':
#            scoresystem['A'] = 'W'
#        if scoresystem['A'] == '=':
#            scoresystem['A'] = 'D'
        if ca['id'] == 0 or da['id'] == 0:
            if not 'arbiters' in info:
                info['arbiters'] = {
                    'chiefArbiter': self.append_profile(ca),
                    'deputyChiefArbiters': [ self.append_profile(da) ],
                    'ratingOfficer': 0,
                    'arbiters': []
                    }

        return

    def parse_ts_group_rounds(self, rounds, tournament):
        for key, value in rounds.items(): 
            self.print_warning('parse_group_rounds attrib: ' + key + ' not matched')
        roundno = 0;
        for child in rounds:
            roundno += 1
            cround = {
                'roundNo': roundno,
                'timeControl': {
                'defaultTime': 0,
                'periods': []
                }}
            clast = {'moves': 0}
            periodno = 0
            match child.tag:
                case 'Rd':                   
                    for key, value in child.attrib.items():
                        match key:
                            case 'StartDate': 
                                cround['startTime'] = helpers.parse_date(value)
                            case 'IsRated':
                                cround['rated'] = (value == 'Y')
                            case 'ActiveElo': 
                                cround['ratingList'] = value
                            case 'TimeFirstMove':
                                cround['timeControl']['defaultTime'] = helpers.parse_minutes(value)
                            case 'AdditionPerMove':
                                increment = clast['increment'] = helpers.parse_seconds(value)
                            case 'TimeFinish':
                                clast['baseTime'] = helpers.parse_minutes(value)
                            case 'PointsForWin': 
                                '0' #Ignore
                            case 'PointsForLoss': 
                                '0' #Ignore
                            case _:
                                self.print_warning('parse_ts_group_rounds: ' + key + ' not matched')
                    for tc in child:
                        match tc.tag:
                            case 'TimeControls':
                                periodno = self.parse_ts_group_timecontrol(tc, cround['timeControl']['periods'], increment)
                            case _:
                                self.print_warning('parse_group_timecontrol tag: ' + tc.tag + ' not matched')
            clast['period'] = periodno + 1 
            cround['timeControl']['periods'].append(clast)
            tournament['rounds'].append(cround)
        return

    def parse_ts_group_timecontrol(self, tc, periods, increment):
        for key, value in tc.attrib.items(): 
            self.print_warning('parse_group_timecontrol attrib: ' + key + ' not matched')
        periodno = 0;
        for child in tc:
            periodno += 1
            period = {
                'period': periodno,
                'increment': increment
                }
            match child.tag:
                case 'phase':
                    for key, value in child.attrib.items():
                        match key:
                            case 'moves': 
                                period['moves'] = helpers.parse_int(value)
                            case 'Time':
                                period['baseTime'] = helpers.parse_minutes(value)
                            case _:
                                self.print_warning('parse_ts_group_timecontrol: ' + key + ' not matched')
            periods.append(period)        
        return periodno
    

    def parse_ts_group_order(self, rank, tournamentno, ordertype):
        for key, value in rank.items(): 
            if key == 'NumOrdersInPgroup':
                numberorder = value
            else:
                self.print_warning('parse_group_order attrib: ' + key + ' not matched')
        for order in rank:
            if order.tag != 'Order':    
                self.print_warning('parse_group_order attrib, tag: ' + order.tag + ' not matched')
            for key, value in order.items():     
                if key != 'Name':    
                    self.print_warning('parse_group_order attrib, attrib: ' + key + ' not matched')
                # use order
                
        return

    def parse_ts_group_prize(self, attrib, tournamentno):
        return

    def parse_ts_group_layout(self, attrib, tournamentno):
        return

    def parse_ts_group_report(self, attrib, tournamentno):
        return


    def parse_ts_group_players(self, players, tournament):
        for key, value in players.attrib.items():
            match key:
                case 'Num':
                    '3'
                case 'SeparateFile':
                    'N'
                case _:
                    self.print_warning('parse_ts_group_players attrib: ' + key + '=' + value + ' not matched')
        rank = 0
        for player in players:
            if player.tag == 'Player':
                rank += 1
                self.parse_ts_player(player, tournament, rank)
        return


    def parse_ts_group_teams(self, teams, tournament):
        for key, value in teams.attrib.items():
            match key:
                case 'SeparateFile':
                    'N'
                case _:
                    self.print_warning('parse_ts_group_teams attrib: ' + key + '=' + value + ' not matched')
        rank = 0
        for team in teams:
            if team.tag == 'Team':
                rank += 1
                self.parse_ts_team(team, tournament, rank)
        return

# ==============================
#
# Update tournament structure
#


    def update_tournament_rating(self, tournament):
        cround = None
        roundno = 0
        ratinglist = tournament['ratingList']
        for tround in tournament['rounds']:
            if tround['roundNo'] <= tournament['currentRound'] and tround['roundNo'] > roundno and tround['ratingList'] != 'Undefined':
                roundno = tround['roundNo']
                cround = tround
        if cround != None:
            ratinglist =  cround['ratingList']
        ratinglists = self.event['ratingLists']
        ratingindex = 0
        for nlist in range(0, len(ratinglists)):
            if ratinglist == ratinglists[nlist]['listName']:
                ratingindex = nlist
                break
        pids = self.all_pids()   
        competitors = tournament['competitors']
        for key, player in self.pcompetitors.items():
            player['rating'] = int(pids[player['profileId']]['rating'][ratingindex])            
        
    def update_tournament_teamcompetitors(self, tournament):
        if not tournament['teamTournament']:
            return
        [cplayers, cteam] = self.build_tournament_teamcompetitors(tournament)
        competitors = tournament['competitors']
        allgames = self.build_all_games(tournament, cteam, False)
        pscore = tournament['gameScoreSystem']
        tscore = tournament['matchScoreSystem']

        for competitor in competitors:
            competitor['matchPoints'] = 0
            competitor['gamePoints'] = 0
        for game in tournament['matchList']:
            rnd = game['round']
            gpoints = {}
            played = False
            for col in ['white', 'black']:
                if col in game and game[col] > 0: 
                    teamno = game[col] 
                    teamres = allgames[rnd][teamno]
                    sum = 0
                    for igame in teamres:
                        if teamno == cteam[igame['white']]:
                            sum +=  self.get_score(pscore, igame, 'white')
                            played = played or igame['played']
                        if 'black' in igame and igame['black'] > 0 and teamno == cteam[igame['black']]:
                            sum += self.get_score(pscore, igame, 'black')
                            played = played or igame['played']
                    gpoints[col] = sum
            game['played'] = played  
            if 'black' in gpoints:
                if gpoints['white'] > gpoints['black']:
                    game['wResult'] = 'W'
                    game['bResult'] = 'L' if played else 'Z'
                elif gpoints['white'] < gpoints['black']:
                    game['bResult'] = 'W'
                    game['wResult'] = 'L' if played else 'Z'
                else:
                    game['wResult'] = 'D'
                    game['bResult'] = 'D'
                competitors[game['black']-1]['gamePoints'] += gpoints['black']                
                competitors[game['black']-1]['matchPoints'] += self.get_score(tscore, game, 'black')
            competitors[game['white']-1]['gamePoints'] += gpoints['white']                
            competitors[game['white']-1]['matchPoints'] += self.get_score(tscore, game, 'white')
 #           if 'black' in game and game['black'] > 0:
               



# ==============================
#
# Read tournament player in TS file
#


    def parse_ts_player(self, player, tournament, rank):
        profile = {
            'id': 0,
            'rating': [0,0,0,0],
            'kFactor': [0,0,0,0],
            'other': {}
        }
        competitor = {
            'cid': 0
        }
        self.parse_ts_player_attrib(player.attrib, profile, competitor)
        profileid = competitor['profileId'] = self.append_profile(profile)
        if competitor['teamName'] != '':
            competitor['teamId'] = self.append_team(competitor['teamName'], profileid)
        else:
            competitor['rank'] = rank
        results = player[0]
        playerno = competitor['cid'] if 'cid' in competitor else 0

        self.pcompetitors[competitor['cid']] = competitor
        #competition['competitors'].append(competitor)
        for game in results:
            match game.tag:
                case 'Game':
                    self.parse_ts_game(game, tournament['gameList'], playerno, False)
                case _:
                    self.print_warning('parse_ts player, result key: ' + key + ' not matched')
        
        return



    def parse_ts_player_attrib(self, attrib, profile, competitor):
        for key, value in attrib.items(): 
            match key:
                case 'StartNo': 
                    competitor['cid'] = helpers.parse_int(value)
                case 'Available':
                    competitor['present'] = (value == 'Y')
                case 'Teamname': 
                    competitor['teamName'] = value
                case 'Group': 
                    profile['other']['group'] = value
                case 'Federation':
                    profile['federation'] = value
                case 'Pts':
                    competitor['gamePoints'] = helpers.parse_float(value)
                case 'Rank':
                    trank = helpers.parse_int(value)
                    if trank > 0: 
                        competitor['rank'] = trank
                case 'Pmt':
                    profile['other']['pmt'] = value
                case 'Rcpt':
                    'N'
                case 'EnrSt': 
                    '0'
                case 'EnrollDate':
                    competitor['enrolled'] = helpers.parse_date(value)
                case 'Custom1':
                    '0'
                case 'Custom2':
                    '0'
                case 'Info':
                    profile['other']['info'] = value
                case 'Title': 
                    profile['fideTitle'] = value
                case 'Gn':
                    profile['firstName'] = value
                case 'Ln':
                    profile['lastName'] = value
                case 'Table': 
                    '0'
                case 'GPgroup': 
                    'M'
                case 'Born':
                    birth = helpers.parse_date(value)
                    profile['birth'] = birth if (len(birth) > 2 and birth[0:2] != '18') else '' 
                case 'Club':
                    profile['clubName'] = value
                case 'LocalID': 
                    profile['localId'] = helpers.parse_int(value)
                case 'LocalRating':
                    profile['rating'][0] = helpers.parse_int(value)
                case 'LocalGames': 
                    '1483'
                case 'FideId': 
                    profile['fideId'] = helpers.parse_int(value) 
                case 'FideRating': 
                    profile['rating'][1] = helpers.parse_int(value)
                case 'FideRapidRating': 
                    profile['rating'][2] = helpers.parse_int(value)
                case 'FideBlitzRating':
                    profile['rating'][3] = helpers.parse_int(value)
                case 'FideGames':
                    '19'
                case 'FideRapidGames':
                    '7'
                case 'FideBlitzGames': 
                    '15'
                case 'RatingFactor': 
                    profile['kFactor'][1] = helpers.parse_float(value)
                case 'RapidRatingFactor': 
                    profile['kFactor'][2] = helpers.parse_float(value)
                case 'BlitzRatingFactor': 
                    profile['kFactor'][3] = helpers.parse_float(value)
                case 'BornYear': 
                    profile['yearBirth'] = helpers.parse_int(value)
                case 'MemberAsOf': 
                    '2018'
                case 'sex': 
                    profile['sex'] = (value + ' ')[0:1]
                case 'Phone': 
                    profile['phone'] = value
                case 'Email': 
                    profile['email'] = value
                case _:
                    self.print_warning('parse_ts_player attrib: ' + key + ' not matched')
        return

           
    def parse_ts_game(self, game, cresults, playerno, isteam):
        result = {
            'id': 0,
            'isTeam' : isteam
            }
        myclr = 'W'
        opponent = 0
        res = '?'
        for key, value in game.attrib.items(): 
            match key:
                case 'Rd':
                    result['round'] = helpers.parse_int(value)
                case 'Clr':
                    myclr = value
                case 'Opnt': 
                    opponent = helpers.parse_int(value)
                case 'Res': 
                    res = value
                case 'Table': 
                    result['board'] = helpers.parse_int(value)
                case 'PublishSerial': 
                    '0'
                case 'Flt':
                    '='
                case 'PGNdata':
                    '?'
                case _:
                    self.print_warning('parse_ts_game attrib: ' + key + ' not matched')
        score = self.parse_result(res, opponent, isteam)
        if myclr == 'B':
            result['white'] = max(0, opponent)
            result['black'] = playerno
            result['bResult'] = score
        else:
            result['white'] = playerno
            result['black'] = max(0, opponent)
            result['wResult'] = score
        result['played'] = (res == '1' or res == '=' or res == '0') and opponent > 0 or opponent == -1
        if score != 'U':
            self.append_result(cresults, result)
        return

    def parse_result(self, result, opponent, isteam):
 #       if opponent == -1:
 #           if isteam == self.isteam:
 #               return 'P'
        match result:
            case '1' | '+':
                return 'W'
            case '=' | 'd':   
                return 'D'
            case '0':
                return 'L'
            case '-':
                return 'Z'
            case 'A':
                return 'A'
            case '?':
                return ('U' if opponent == 0 else 'A')
        return 'U'


# ==============================
#
# Read tournament team in TS file
#


    def parse_ts_team(self, team, tournament, rank):
        teamProfile = {
            'id': 0,
            'other': {}
        }
        competitor = {
            'cid': 0,
            'rank': rank,
            'cplayers' : []
        }
        self.parse_ts_team_attrib(team.attrib, teamProfile, competitor)
        teamid = competitor['teamId'] = self.append_team(teamProfile, 0)
        tournament['competitors'].append(competitor)
        self.tcompetitors[teamProfile['teamName']] = competitor
        results = team[0]
        for game in results:
            match game.tag:
                case 'Game':
                    teamno = competitor['cid']
                    self.parse_ts_game(game, tournament['matchList'], teamno, True)
                case _:
                    self.print_warning('parse_ts team, result key: ' + key + ' not matched')
        
        return

    def parse_ts_team_attrib(self, attrib, teamProfile, competitor):
        for key, value in attrib.items(): 
            match key:
                case 'StartNo':
                    competitor['cid'] = helpers.parse_int(value)
                case 'Available':
                    teamProfile['present'] = value == 'Y'
                case 'Teamname':
                    teamProfile['teamName'] = value
                case 'Group':
                    '' 
                case 'Federation':
                    teamProfile['federation'] = value
                case 'Pts':
                    competitor['matchPoints'] = helpers.parse_float(value)
                case 'Rank':
                    trank = helpers.parse_int(value)
                    if trank > 0: 
                        competitor['rank'] = trank
                case 'Pmt':
                    '1000' 
                case 'Rcpt':
                    'N' 
                case 'EnrSt':
                    '0' 
                case 'EnrollDate':
                    '2019.05.15' 
                case 'Custom1':
                    '0' 
                case 'Custom2':
                    '0' 
                case 'Info':
                    teamProfile['other']['info'] = value
                case 'TeamLeader':
                    captain = {
                        'id': -1,
                        'fideId': 0,
                        'firstName': '',
                        'lastName': '',
                        'fideName': '',
                        'sex': 'u',
                        'federation': '',
                        'fideOTitle': ''
                    }
                    if value != '':
                        self.parse_ts_arbiter(captain, value)
                        teamProfile['captain'] = self.append_profile(captain)
                case _:
                    self.print_warning('parse_ts_team attrib: ' + key + ' not matched')
        return



# ==============================
#
# Converteers
#

    def parse_ts_arbiter(self, arbiter, name):
        line = name.rstrip()
        if line[0:3] == 'IA ' or line[0:3] == 'FA ':
            arbiter['fideOTitle'] = line[0:2]
            arbiter['arbiter'] = line[0:2]
            line = line[3:]
        nameparts = line.split(',', 1)
        if len(nameparts) > 1:
            arbiter['lastName'] = nameparts[0].strip()
            arbiter['firstName'] = nameparts[1].strip()
        else:
            nameparts = line.split(' ')
            arbiter['lastName'] = nameparts[-1:]
            arbiter['firstName'] = ' '.join(nameparts[0:-1])
        arbiter['id'] = 0
        return


    def prepare_player_section(self, tournament):
        tournament['competitors'] = sorted(list(self.pcompetitors.values()), key=lambda g: (g['cid']))

    def prepare_team_section(self, tournament):
        competitors = tournament['competitors']
        for key,competitor in self.pcompetitors.items():
            self.tcompetitors[competitor['teamName']]['cplayers'].append(competitor)
            competitor.pop('teamName')

 
                
        

#### Module test ####

def dotest(name):
    print('==== ' + name + ' ====')
    root = '..\\..\\..\\..\\Nordstrandsjakk\\Turneringsservice\\'
     
    with open(root + name + '\\' + name + '.trx') as f:
        lines = f.read()

    tournament = ts2json()
    tournament.parse_file(lines)
    helpers.json_output(root + name + '\\' + name + '.jch', tournament.event)

def module_test():
    dotest('escc2018')
    dotest('h2023')
    dotest('hur22')
    dotest('ngpl23')
    dotest('elite19-20')
    dotest('nm_lag_19')
    dotest('nm_lag2022')
    dotest('test-half-point')
