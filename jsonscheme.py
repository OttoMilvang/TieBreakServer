# -*- coding: utf-8 -*-
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Thu Jun 27 07:51:15 2024

@author: otto
"""

json_scheme = {
    'profileId' : { 
        'type' : 'int'
    },
    'teamId' : { 
        'type' : 'int'
    },
    'gameId' : { 
        'type' : 'int'
    },
    'points' : { 
        'type' : 'Decimal'
    },
    'event' : { 
        'type' : 'object',
        'properties' : {
            'filetype' : 'string',
            'version' : 'string',
            'origin' : 'string',
            'published' : 'string', 
            'revision' : 'string',
            'status' : 'object:status',
            'description' : 'string',
            'eventName' : 'string',
            'eventInfo' : 'object:eventInfo',
            'ratingLists' : 'array:ratingList',
            'scoreLists' : 'array:scoreList',
            'profiles' : 'array:profile',
            'teams' : 'array:team',
            'organization' : 'array:organization',
            'tournaments' : 'array:tournament'
            },
        'required' : ['filetype', 'version', 'origin', 'published', 'eventName']
        },
    'eventInfo' : { 
        'type' : 'object',
        'properties' : {
            'fullName' : 'string',
            'site' : 'string',
            'organizers' : 'object:organizer',
            'arbiters' : 'object:arbiter',
            'federation' : 'string',
            'startDate' : 'string',
            'endDate' : 'string',
            'website' : 'string',
            'logo' : 'string',
            'other' : 'object'
            },   
        'required' : ['fullName']
        },
    'organizer' : {
        'type' : 'object',
        'properties' : {
            'chiefOrganizer' : 'profileId',
            'chiefSecretariat' : 'profileId',
            'organizers' : 'array:profileId',
            'secretaries' : 'array:profileId'
            }
        },
    'arbiter' : {
        'type' : 'object',
        'properties' : {
            'chiefArbiter' : 'profileId',
            'deputyChiefArbiters' : 'array:profileId',
            'ratingOfficer' : 'profileId',
            'arbiters' : 'array:profileId'
            }
        },
    'status' : {
        'type' : 'object',
        'properties' : {
            'code' : 'int',
            'info' : 'string',
            'error' : 'string'
            },   
        'required' : ['code']
        },
    'ratingList' : {
        'type' : 'object',
        'properties' : {
            'listName' : 'string',
            'listDescription' : 'string'
            },   
        'required' : ['listName']
        },
    'scoreList' : {
        'type' : 'object',
        'properties' : {
            'listName' : 'string',
            'scoreSystem' : 'scoreSystem'
            },   
        'required' : ['listName', 'scoreSystem']
        },
    'profile' : {
        'type' : 'object',
        'properties' : {
            'id' : 'profileId',
            'lastName' : 'string',
            'firstName' : 'string',
            'sex' : 'String',
            'yearBirth' : 'int',
            'birth' : 'string',
            'federation' : 'string',
            'fideId' : 'int',
            'fideName' : 'string',
            'rating' : 'array:int',
            'kFactor' : 'array:int',
            'fideTitle' : 'string',
            'fideWTitle' : 'string',
            'fideOTitle' : 'string',
            'localId' : 'int',
            'category' : 'array:string',
            'ageCatecory' : 'string',
            'clubId' : 'int',
            'clubName' : 'string',
            'arbiter' : 'string',
            'membership' : 'int, string, bool',
            'email' : 'string',
            'phone' : 'string',
            'publish' : 'object',
            'other' : 'object'
            },   
        'required' : ['id', 'lastName', 'firstName', 'sex', 'federation']
        },
    'team' : {
        'type' : 'object',
        'properties' : {
            'id' : 'teamId',
            'teamName' : 'string',
            'federation' : 'string',
            'captain' : 'profileId',
            'coach' : 'profileId',
            'players' : 'array:profileId'
            },   
        'required' : ['id', 'teamName', 'players']
        },
    'organization' : {
        'type' : 'object',
        'properties' : {
            'id' : 'int',
            'orgName' : 'string',
            'orgType' : 'string',
            'shortName' : 'string',
            'parentId' : 'int',
            'parentName' : 'string',
            'Active' : 'bool',
            'Count' : 'int'
            },   
        'required' : ['id', 'orgName']
        },
    'tournament' : {
        'type' : 'object',
        'properties' : {
            'tournamentNo' : 'int',
            'name' : 'string',
            'tournamentType' : 'string',
            'tournamentInfo' : 'tournamentInfo',
            'accelerated' : 'string',
            'teamTournament' : 'bool',
            'teamSize' : 'int',
            'numRounds' : 'int',
            'rounds' : 'array:round',
            'currentRound' : 'int',
            'maxMeet' : 'int',
            'ratingList' : 'string',
            'initialOrder' : 'array:rankOrder',
            'scoreBracket' : 'array:rankOrder',
            'rankOrder' : 'array:rankOrder',
            'rated' : 'bool',
            'timeControl' : 'timeControl',
            'gameScoreSystem' : 'string',
            'matchScoreSystem' : 'string',
            'gameList' : 'array:result',
            'matchList' : 'array:result',
            'competitors' : 'array:competitor',
            'other' : 'object'
            }
        },
    'round' : {
        'type' : 'object',
        'properties' : {
            'roundNo' : 'int',
            'startTime' : 'string',
            'rated' : 'bool',
            'ratingList' : 'string',
            'timeControl' : 'timeControl'
            }
        },
    'timeControl' : {
        'type' : 'object',
        'properties' : {
           'description' : 'string',
           'defaultTime' : 'int',
           'periods' : 'array:timePeriod'
           }
        },
    'timePeriod' : {
        'type' : 'object',
        'properties' : {
           'period' : 'int',
           'mode' : 'string',
           'baseTime' : 'int',
           'increment' : 'int',
           'moves' : 'int'
           }
        },
    'rankOrder' : {
        'type' : 'object',
        'properties' : {
           'order' : 'int',
           'name' : 'string',
           'scoreType' : 'string',
           'modifiers' : 'object',
           'reverse' : 'bool',
           'description' : 'string'
           }
        },

    'competitor' : {
        'type' : 'object',
        'properties' : {
           'cid' : 'int',
           'profileId' : 'profileId',
           'teamId' : 'teamId',
           'cteam' : 'int',
           'cplayers' : 'array:competitor',
           'present' : 'bool',
           'enrolled' : 'string',
           'gamePoints' : 'points',
           'matchPoints' : 'points',
           'tieBreakScore' : 'array:points',
           'rank' : 'int',
           'tpn' : 'int',
           'rating' : 'int',
           'kFactor' : 'int',
           'random' : 'int'
           }
        },
    'result' : {
        'type' : 'object',
        'properties' : {
           'id' : 'resultId',
           'isTeam' : 'bool',
           'round' : 'int',
           'board' : 'int',
           'white' : 'int',
           'black' : 'int',
           'wResult' : 'string',
           'bResult' : 'string',
           'played' : 'bool',
           'rated' : 'bool',
           'date' : 'string',
           'eco' : 'string',
           'pgn' : 'string',
           'comment' : 'string',
           }
        }
    }   
