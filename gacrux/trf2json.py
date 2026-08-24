# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
import time
import re
from decimal import Decimal

from gacrux import berger
from gacrux import chessjson
from gacrux import games2matches
from gacrux import scoresystem
from gacrux.gacruxexeptions import GacruxError, GacruxInputError
from gacrux import helpers 


class trf2json(chessjson.chessjson):

    # Read trf into a JSON for Chess data structure

    # constructor function
    def __init__(self):
        super().__init__()
        self.trfrecords = [
            {"id": "###", "read": self.parse_trf_noop,          "write": self.output_trf_noop,          "desc": "Comments"},
            {"id": "012", "read": self.parse_trf_tournament,    "write": self.output_trf_info,          "desc": "Tournament Name"},
            {"id": "022", "read": self.parse_trf_site,          "write": self.output_trf_info,          "desc": "City"},
            {"id": "032", "read": self.parse_trf_federation,    "write": self.output_trf_info,          "desc": "Federation"},
            {"id": "042", "read": self.parse_trf_startdate,     "write": self.output_trf_datetime,      "desc": "Date of start"},
            {"id": "052", "read": self.parse_trf_enddate,       "write": self.output_trf_datetime,      "desc": "Date of end"},
            {"id": "062", "read": self.parse_trf_noop,          "write": self.output_trf_num_comp,      "desc": "Number of players"},
            {"id": "072", "read": self.parse_trf_noop,          "write": self.output_trf_num_comp,      "desc": "Number of rated players"},
            {"id": "082", "read": self.parse_trf_noop,          "write": self.output_trf_noop,          "desc": "Number of teams"},
            {"id": "092", "read": self.parse_trf_ttype,         "write": self.output_trf_ttype,         "desc": "Type of tournament"},
            {"id": "102", "read": self.parse_trf_ca_arbiter,    "write": self.output_trf_arbiter,       "desc": "Chief Arbiter"},
            {"id": "112", "read": self.parse_trf_da_arbiter,    "write": self.output_trf_arbiter,       "desc": "Deputy Chief Arbiter"},
            {"id": "122", "read": self.parse_trf_timecontrol,   "write": self.output_trf_timecontrol,   "desc": "Times per moves/game"},
            {"id": "132", "read": self.parse_trf_dates,         "write": self.output_trf_dates,         "desc": "Dates of the round"},
            {"id": "142", "read": self.parse_trf_numbrounds,    "write": self.output_trf_numrounds,     "desc": "Number of rounds"},
            {"id": "152", "read": self.parse_trf_initialcolor,  "write": self.output_trf_topcolor,      "desc": "Initial-colour"},
            {"id": "162", "read": self.parse_trf_gamescore,     "write": self.output_trf_gamescore,     "desc": "Game score system"},
            {"id": "172", "read": self.parse_trf_natsupport,    "write": self.output_trf_noop,          "desc": "National support"},
            {"id": "182", "read": self.parse_trf_ttype,         "write": self.output_trf_noop,          "desc": "Pairing Controller Identifier"},
            {"id": "192", "read": self.parse_trf_typetournament,"write": self.output_trf_noop,          "desc": "Encoded Type Of Tournament"},
            {"id": "202", "read": self.parse_tiebreaks202,      "write": self.output_trf_noop,          "desc": "FIDE Tie-Breaks used to break ties"},
            {"id": "212", "read": self.parse_tiebreaks212,      "write": self.output_trf_noop,          "desc": "FIDE Tie-Breaks used to define standings"},
            {"id": "222", "read": self.parse_trf_timecontrol,   "write": self.output_trf_noop,          "desc": "Encoded Time Control"},
            {"id": "352", "read": self.parse_colorsequence,     "write": self.output_trf_noop,          "desc": "Colour sequence (W or B) for boards in team competitions"},
            {"id": "362", "read": self.parse_trf_matchscore,    "write": self.output_trf_noop,          "desc": "Scoring point system for teams"},
            {"id": "001", "read": self.parse_trf_player,        "write": self.output_trf_player,        "desc": "Player section"},
            {"id": "FID", "read": self.parse_trf_natrating,     "write": self.output_trf_noop,          "desc": "National Rating Support"},
            {"id": "310", "read": self.parse_trf_team,          "write": self.output_trf_noop,          "desc": "Team section"},
            {"id": "013", "read": self.parse_trf_team,          "write": self.output_trf_noop,          "desc": "Team section"},
            {"id": "250", "read": self.parse_trf_accelerated,   "write": self.output_trf_accelerated,  "desc": "Accelerated Round"},
            {"id": "260", "read": self.parse_trf_prohibited,    "write": self.output_trf_prohibited,    "desc": "Prohibited pairings"},
            {"id": "240", "read": self.parse_trf_bye4,          "write": self.output_trf_noop,          "desc": "Bye section HPB and FPB"},
            {"id": "320", "read": self.parse_trf_pab,           "write": self.output_trf_noop,          "desc": "Bye section PAB"},
            {"id": "330", "read": self.parse_forfeited,         "write": self.output_trf_noop,          "desc": "Forfeited matches"},
            {"id": "299", "read": self.parse_trf_abnormal,      "write": self.output_trf_noop,          "desc": "Abnormal Assignment points"},
            {"id": "300", "read": self.parse_trf_outoforder,    "write": self.output_trf_noop,          "desc": "Out of order"},
            {"id": "801", "read": self.parse_trf_noop,          "write": self.output_trf_noop,          "desc": "Informative records for teams"},
            {"id": "802", "read": self.parse_trf_noop,          "write": self.output_trf_noop,          "desc": "Informative records for teams"},
            {"id": "XXR", "read": self.parse_trf_numbrounds,    "write": self.output_trf_noop,          "desc": "Nuber of rounds"},
            {"id": "XXZ", "read": self.parse_trf_absent,        "write": self.output_trf_noop,          "desc": "Will not meet"},
        ]

        self.results = {
            "1": {"result": "W", "played": True , "rated": True  },
            "=": {"result": "D", "played": True , "rated": True  },
            "0": {"result": "L", "played": True , "rated": True  },
            "U": {"result": "P", "played": True , "rated": False },
            "W": {"result": "W", "played": True , "rated": False },
            "D": {"result": "D", "played": True , "rated": False },
            "L": {"result": "L", "played": True , "rated": False },
            "X": {"result": "A", "played": True , "rated": False },
            "?": {"result": "A", "played": True , "rated": False },
            "+": {"result": "W", "played": False, "rated": False },
            "F": {"result": "W", "played": False, "rated": False },
            "H": {"result": "D", "played": False, "rated": False },
            "-": {"result": "Z", "played": False, "rated": False },
            "Z": {"result": "Z", "played": False, "rated": False },
            "A": {"result": "Z", "played": False, "rated": False },
            " ": {"result": "Z", "played": False, "rated": False },
         }
 
        self.titles = {
            "g": "GM",
            "m": "IM",
            "f": "FM",
            "c": "CM",
            "wg": "WGM",
            "wm": "WIM",
            "wf": "WFM",
            "wc": "WCM",
        }

        self.code192 = {
            "FIDE_DUTCH_2017"              : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        },    
            "FIDE_DUTCH_2025"              : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        }, 
            "FIDE_DUTCH"                   : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        }, 
            "FIDE_DUBOV"                   : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dobov"]        }, 
            "FIDE_BURSTEIN"                : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["burstein"]     }, 
            "FIDE_DUTCH_2017_BAKU"         : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        }, 
            "FIDE_DUTCH_2025_BAKU"         : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        }, 
            "FIDE_DUTCH_BAKU"              : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dutch"]        }, 
            "FIDE_DUBOV_BAKU"              : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["dobov"]        }, 
            "FIDE_BURSTEIN_BAKU"           : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["burstein"]     }, 
            "CUSTOM_SWISS"                 : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["custom"]       }, 
            "FIDE_DOUBLESWISS"             : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["doubleswiss"]  }, 
            "FIDE_DOUBLESWISS_BAKU"        : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["doubleswiss"]  }, 
            "CUSTOM_DOUBLESWISS"           : {"format": "swiss",        "teamTournament": False, "pairingSystem": ["doubleswiss"]  },
            "BERGER_ROUNDROBIN"            : {"format": "roundrobin",   "teamTournament": False, "pairingSystem": ["berger"]       }, 
            "BERGER_DOUBLEROUNDROBIN"      : {"format": "roundrobin",   "teamTournament": False, "pairingSystem": ["berger", "double"]       },
            "FIDE_ROUNDROBIN"              : {"format": "roundrobin",   "teamTournament": False, "pairingSystem": ["berger", "fide"]       },
            "FIDE_DOUBLEROUNDROBIN"        : {"format": "roundrobin",   "teamTournament": False, "pairingSystem": ["berger", "fide", "double"] },
            "CUSTOM_ROUNDROBIN"            : {"format": "roundrobin",   "teamTournament": False, "pairingSystem": ["custom"]       },
            "FIDE_SCHILLER"                : {"format": "schiller",     "teamTournament": True , "pairingSystem": ["schiller"]     },
            "CUSTOM_SCHILLER"              : {"format": "schiller",     "teamTournament": True , "pairingSystem": ["schiller"]     },
            "FIDE_SCHEVENINGEN"            : {"format": "scheveningen", "teamTournament": True , "pairingSystem": ["scheveningen"] },
            "FIDE_DOUBLESCHEVENINGEN"      : {"format": "scheveningen", "teamTournament": True , "pairingSystem": ["scheveningen"] },
            "CUSTOM_SCHEVENINGEN"          : {"format": "scheveningen", "teamTournament": True , "pairingSystem": ["scheveningen"] },
            "CUSTOM_KNOCKOUT"              : {"format": "knokout",      "teamTournament": False, "pairingSystem": ["custom"]       },
            "FIDE_TEAM_TYPEA_MP_GP"        : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEA_GP_MP"        : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEA_MP"           : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEA_GP"           : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEB_MP_GP"        : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_TYPEB_GP_MP"        : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_TYPEB_MP"           : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_TYPEB_GP"           : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_MP_GP"              : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM_GP_MP"              : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM_MP"                 : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM_GP"                 : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM"                    : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "CUSTOM_TEAM_SWISS_MP"         : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["custom"]       },
            "CUSTOM_TEAM_SWISS_GP"         : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["custom"]       },
            "FIDE_TEAM_TYPEA_MP_GP_BAKU"   : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEA_MP_BAKU"      : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "FIDE_TEAM_TYPEB_MP_GP_BAKU"   : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_TYPEB_MP_BAKU"      : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typeb"] },
            "FIDE_TEAM_MP_GP_BAKU"         : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM_MP_BAKU"            : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "nocolor"] },
            "FIDE_TEAM_BAKU"               : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["fideteam", "team_typea"] },
            "CUSTOM_TEAM_SWISS"            : {"format": "swiss",        "teamTournament": True , "pairingSystem": ["custom"]       },
            "BERGER_TEAM_ROUNDROBIN"       : {"format": "roundrobin",   "teamTournament": True , "pairingSystem": ["berger"]       },
            "BERGER_TEAM_DOUBLEROUNDROBIN" : {"format": "roundrobin",   "teamTournament": True , "pairingSystem": ["berger"]       },
            "FIDE_TEAM_ROUNDROBIN"         : {"format": "roundrobin",   "teamTournament": True , "pairingSystem": ["berger"]       },
            "FIDE_TEAM_DOUBLEROUNDROBIN"   : {"format": "roundrobin",   "teamTournament": True , "pairingSystem": ["berger"]       },
            "CUSTOM_TEAM_ROUNDROBIN"       : {"format": "roundrobin",   "teamTournament": True , "pairingSystem": ["custom"]       }, 
            "CUSTOM_TEAM_KNOCKOUT"         : {"format": "knokout",      "teamTournament": True , "pairingSystem": ["custom"]       }, 
        }       
        
        self.cteam = {}  # pointer from cid-player to cid-team
        self.cboard = {}
        self.p001 = {}
        self.byelist = []
        self.forfeitedlist = []
        self.ooolist = []
        self.aatlist = []
        self.o001 = {}
        self.pcompetitors = {}  # pointer to player section competitors
        self.bcompetitors = {}  # pointer to team competitors, index id 1st board player cid
        self.tcompetitors = {}  # pointer to team section competitors, index is team cid
        self.cteam[0] = 0
        self.cboard[0] = 0

        self.national = {
            "federation": "FID", 
            "mode": "FIDE", 
            "func": helpers.rating_fide
        }

    # ==============================
    #
    # Read TRF file

    def parse_file(self, alines, verbose):
        #
        # Set up the structure
        #
        self.gamescores = []  # used to calculate scoresystem
        self.teamscores = []  # used to calculate scoresystem

        self.scores = scoresystem.scoresystem()
        self.chessjson["event"]["tournaments"].append(
            {
                "tournamentNo": 1,
                "tournamentType": "Tournament",
                "tournamentInfo": {},
                "ratingList": "TRF",
                "numRounds": 0,
                "currentRound": 0,
                "teamTournament": False,
                "rankOrder": ["PTS"],
                "competitors": [],
                "teamSize": 0,
                "scoreSystem": self.scores.score,
                "gameList": [],
                "matchList": [],
                "timeControl": {"description": "", "encoded": ""},
            }
        )

        self.chessjson["origin"] = "trf2json ver. 1.03"
        self.add_ratinglist("TRF")

        tournament = self.get_tournament(1)
        self.all_lines = self.read_all_lines(tournament, alines, verbose)
        # json_output("-", self.scores.score)

        self.scores.update_gamescore(self.chessjson, tournament, self.gamescores, "162" in self.all_lines or "222" in self.all_lines)
        if tournament["teamTournament"]:
            self.scores.update_teamscore(tournament, self.teamscores, "310" in self.all_lines)
            if len(self.tcompetitors) == 0:
                self.prepare_team_section_013(tournament)
            else:
                self.prepare_team_section_310(tournament)
                self.update_board_number(tournament, "match", True)
            if tournament["teamSize"] == 0 and len(tournament["gameList"]) > 0:
                if len(tournament["matchList"]) == 0:
                    self.put_status(401, "Error in trf-file, Minning 362 record for team tournament")
     
                tournament["teamSize"] = round(len(tournament["gameList"]) / len(tournament["matchList"]))
        else:
            self.prepare_player_section(tournament)
            self.update_board_number(tournament, "game", False)
        self.update_individualbye_list(tournament)
        self.update_forfeited_list(tournament)
        if (topcolor := self.get_topcolor(tournament, None)) is not None:
            tournament["topColor"] = topcolor
        return

    # Read all lines into a structure

    def read_all_lines(self, tournament, alines, verbose):
        #
        # Pass 1
        # Read all lines into a structure sorted by trfid
        #

        lines = alines.replace("\r", "\n").split("\n")
        lineno = 0
        all_lines = {}
        for line in lines:
            # print(line)
            lineno += 1
            if len(line) >= 3:
                trfkey = line[0:3]
                if trfkey not in all_lines:
                    all_lines[trfkey] = []
                all_lines[trfkey].append({"no": lineno, "txt": line, "parse": False})

        #
        # Pass 2
        # Parse all lines in a spesific order
        #

    
        nexttrfid = None
        for record in self.trfrecords:
            # For national rating "FID" is replaced NRS code
            trfid = record["id"] if nexttrfid is None else nexttrfid
            parser = record["read"]
            # print(trfid, parser, record["desc"])
            if trfid in all_lines:
                if trfid == "013" and "310" in all_lines:
                    continue
                for trfline in all_lines[trfid]:
                    lineno = trfline["no"]
                    line = trfline["txt"]
                    try:
                        # self.parse_line(tournament, record["id"], line)
                        parser(tournament, line)
                        trfline["parse"] = True
                    except GacruxError:
                        # A parser that has itself worked out what is wrong with the record
                        # says so. Do not turn that into a status code and a return: the
                        # return leaves all_lines unset, and parse_file then reads it.
                        raise
                    except:
                        if verbose:
                            raise
                        self.put_status(401, "Error in trf-file, line " + str(lineno) + ", " + line)
                        return
            nexttrfid = self.post_parse_line(tournament, trfid)
        if "001" not in all_lines and "092" not in all_lines:
            self.put_status(401, "Error in trf, no 001 records")

        return all_lines

    """
    def parse_line(self, tournament, trfkey, line):
                trfvalue = line[4:]
                match trfkey:  # noqa
                    case "###":
                        pass
                    case "001":
                        self.parse_trf_player(tournament, line)
                    case "012":
                        self.parse_trf_info("fullName", trfvalue)
                    case "013":
                        self.parse_trf_team(tournament, line)
                        tournament["teamTournament"] = True
                    case "022":
                        self.parse_trf_info("site", trfvalue)
                    case "032":
                        self.parse_trf_info("federation", trfvalue)
                    case "042":
                        self.parse_trf_info("startDate", parse_date(trfvalue))
                    case "052":
                        self.parse_trf_info("endDate", parse_date(trfvalue))
                    case "062":
                        # numplayers = int(trfvalue.split()[0])
                        pass
                    case "072":
                        # numrated = int(trfvalue)
                        pass
                    case "082":
                        # numteams = int(trfvalue)
                        pass
                    case "092":
                        tournament["tournamentType"] = trfvalue
                    case "102":
                        self.parse_trf_arbiter(True, line)
                    case "112":
                        self.parse_trf_arbiter(False, line)
                    case "122":
                        tournament["timeControl"]["description"] = trfvalue
                    case "123":
                        pass # Comment
                    case "132":
                        self.parse_trf_dates(tournament, line)
                    case "142":
                        self.parse_trf_numbrounds(tournament, line)
                    case "152":
                        self.parse_trf_initialcolor(tournament, line)
                    case "162":
                        self.parse_trf_scoresystem(tournament, line, "game")
                    case "172":
                        self.parse_trf_natsupport(tournament, line)
                    case "182":
                        self.parse_trf_pairingid(tournament, line)
                    case "192":
                        self.parse_trf_info("typeOfTournament", trfvalue)
                    case "202":
                        self.parse_tiebreaks(tournament, line, False)
                    case "212":
                        self.parse_tiebreaks(tournament, line, True)
                    case "222":
                        tournament["timeControl"]["encoded"] = trfvalue
                    case "240":
                        self.parse_trf_bye(tournament, line, 4)
                    case "250":
                        self.parse_trf_accelerated(tournament, line)
                    case "260":
                        self.parse_trf_prohibited(tournament, line)
                    case "299":
                        self.parse_trf_abnormal(tournament, line)
                    case "300":
                        self.parse_trf_outoforder(tournament, line)
                    case "310":
                        self.parse_trf_team(tournament, line)
                        tournament["teamTournament"] = True
                    case "320":
                        self.parse_trf_pab(tournament, line)
                    case "330":
                        self.parse_forfeited(tournament, line)
                    case "352":
                        self.parse_colorsequence(tournament, line)
                    case "362":
                        self.parse_trf_scoresystem(tournament, line, "match")
                    case "801":
                        pass # TODO
                    case "802":
                        pass # TODO
                    case "FID":
                        self.parse_trf_natrating(tournament, line)
                    case "XXR":
                        self.parse_trf_numbrounds(tournament, line)
                    case "XXZ":
                        self.parse_trf_absent(tournament, line)
                    case "XXS":
                        self.parse_trf_points(tournament, line)
                    case "XXC":
                        self.parse_trf_configuration(tournament, line)
                    case "XXA":
                        self.parse_trf_acceleratedv4(tournament, line)
                        # tt = tournament["tournamentType"].upper()
                    # Roberto
                    case "ACC":
                        self.parse_trf_acc(tournament, line)
                    case "TSE":
                        self.parse_trf_tse(tournament, line)
                    case "PAB":
                        self.parse_trf_npg(tournament, line, "P", Decimal("0.5"))
                    case "FPB":
                        self.parse_trf_npg(tournament, line, "F", Decimal("1.0"))
                    case "HPB":
                        self.parse_trf_npg(tournament, line, "H", Decimal("0.5"))
                    case "ZPB":
                        self.parse_trf_npg(tournament, line, "Z", Decimal("0.0"))
                    case "MFO":
                        self.parse_trf_forfeit(tournament, line, "W", "Z")
                    case "DFM":
                        self.parse_trf_forfeit(tournament, line, "Z", "Z")
                    # case 'OOO':
                    #    self.parse_trf_ooo(tournament, line)
                    # case 'XXX':
                    #    self.parse_test_xxx(tournament, line)
                    case "FFF":
                        # sys.exit(0)
                        pass
                    case _:
                        if self.verbose:
                            print("Unknown key:", trfkey)
                        # sys.exit(0)
                        pass
        """

    def post_parse_line(self, tournament, trfkey):
        trfid = None
        if trfkey == "001":
                self.pids = self.all_pids()
                self.check_player_section(tournament)
                trfid = self.national["federation"] # This is next record
        elif trfkey == "013":
                teamsize = tournament["teamSize"]
                if tournament["teamTournament"] and (teamsize == 0):
                    countgames = [{} for i in range(tournament["currentRound"])]
                    teamsize = 0
                    for game in tournament["gameList"]:
                        if game["played"] and self.get_result_cid(game, "white") > 0 and self.get_result_cid(game, "black") > 0:
                            rnd = game["round"] - 1
                            for col in ["white", "black"]:
                                player = game[col]
                                teamid = self.pcompetitors[self.get_result_cid(game, col)]["teamId"]
                                countgames[rnd][teamid] = countgames[rnd][teamid] + 1 if teamid in countgames[rnd] else 1
                                teamsize = max(teamsize, countgames[rnd][teamid])
                    # print(teamsize)
                    tournament["teamSize"] = teamsize
        return trfid

    # ==============================
    #
    # Pairing numbers read from a record
    #
    # The reader keeps the competitors in dicts and lists that are indexed by pairing
    # number, and it indexed them with the numbers a record named without ever asking
    # whether the tournament has such a competitor. A number that names nobody -- a
    # typo, a competitor removed from the player section but left in a later record --
    # therefore came out as "IndexError: list index out of range" or "KeyError: 6" from
    # somewhere deep in the reader, naming neither the record, nor the number, nor the
    # numbers that would have been right.
    #
    # Which competitors a number may name depends on the record and on the tournament.
    # TRF-2026 calls the field of records 240, 300, 320 and 330 a "(Team) Pairing
    # Number": in a team tournament it is the pairing number of a *team* (240 is
    # written out with "two teams (26 and 47) getting a HPB in the third round"), and in
    # an individual tournament it is the pairing number of a player. The player ids that
    # records 300, 310 and 013 list within a team are always players, in either
    # tournament. So the two checks are separate.

    def check_competitor(self, tournament, record, competitor, what=""):
        # A team pairing number in a team tournament, a player pairing number otherwise.
        if what != "player" and tournament["teamTournament"]:
            # Record 310 fills tcompetitors, the older record 013 fills bcompetitors.
            competitors = self.tcompetitors if len(self.tcompetitors) > 0 else self.bcompetitors
            what = "team"
        else:
            competitors = self.pcompetitors
            what = "player"
        return self.check_pairing_number(record, competitor, competitors, what)

    def check_player(self, record, player):
        # A player pairing number, in an individual as well as in a team tournament.
        return self.check_pairing_number(record, player, self.pcompetitors, "player")

    def check_pairing_number(self, record, competitor, competitors, what):
        if competitor in competitors:
            return competitor
        numbers = sorted(competitors.keys())
        if len(numbers) == 0:
            # Nothing was read to check the number against, so it cannot be wrong here.
            return competitor
        message = (
            "Record " + record + " names " + what + " " + str(competitor)
            + ", the tournament has " + str(len(numbers)) + " " + what + "s ("
            + str(numbers[0]) + " - " + str(numbers[-1]) + ")"
        )
        self.put_status(401, message)
        raise GacruxInputError(message)

    def check_player_section(self, tournament):
        # Every opponent a 001 record names has to be a player the player section has.
        # The number cannot be checked while the record is read -- the opponent may be
        # further down the file -- so it is checked once the section is complete.
        for game in tournament["gameList"]:
            for color in ["white", "black"]:
                if self.get_result_cid(game, color) > 0:
                    self.check_player("001", self.get_result_cid(game, color))

    def is_rr(self, tournament):
        if "rr" not in self.__dict__:
            tt = tournament["tournamentType"].upper()
            numcomp = len(tournament["competitors"])
            numrounds = tournament["numRounds"]
            rr = False
            if tt.find("SWISS") >= 0:
                rr = False
            elif tt.find("RR") >= 0 or tt.find("ROBIN") >= 0 or tt.find("BERGER") >= 0:
                rr = True
            elif numcomp == numrounds + 1 or numcomp == numrounds:
                rr = True
            elif numcomp * 2 == (numrounds + 1) or numcomp * 2 == numrounds:
                rr = True
            self.rr = rr
        return self.rr

    def update_board_number(self, tournament, name, isteam):
        # is the tournament RR?
        slist = self.scores.score["match"] if isteam else self.scores.score["game"]
        results = {}

        for result in tournament[name + "List"]:
            rnd = result["round"]
            if rnd not in results:
                results[rnd] = []
            results[rnd].append(result)

        numcomp = len(tournament["competitors"])
        points = [Decimal("0.0")] * (numcomp + 1)

        # update each round
        for rnd, roundresults in results.items():
            if self.is_rr(tournament):
                self.update_rr_board_number(roundresults, numcomp, points)
            else:
                self.update_swiss_board_number(roundresults, numcomp, points)
            for result in roundresults:
                wScore = self.get_score(slist, result, "white")
                bScore = Decimal("0")
                points[self.get_result_cid(result, "white")] += wScore
                if self.get_result_res(result, "black", None) is not None:
                    bScore = self.get_score(slist, result, "black")
                    points[self.get_result_cid(result, "black")] += bScore

    def update_rr_board_number(self, roundresults, numcomp, points):
        rr = berger.bergertables(numcomp)
        n = rr["players"]
        cround = 0
        for result in roundresults:
            w = self.get_result_cid(result, "white")
            b = self.get_result_cid(result, "black") if "black" in result and self.get_result_cid(result, "black") > 0 else n
            blku = berger.bergerlookup(rr, w, b)
            if blku:
                rnd = blku["round"] if blku["round"] < n else blku["round"] - n + 1
                if cround > 0 and cround != rnd:
                    return self.update_swiss_board_number(roundresults, numcomp, points)  # not rr
                cround = rnd
                result["board"] = blku["board"]
            else:
                result["board"] = 0
        return

    def update_swiss_board_number(self, roundresults, numcomp, points):
        for result in roundresults:
            w = self.get_result_cid(result, "white")
            b = self.get_result_cid(result, "black")
            c = 2 if b > 0 else 1
            result["rank"] = {"c": c, "w": points[w], "b": points[b], "r": min(w, b) if b > 0 else w}

        roundresults = sorted(
            roundresults,
            key=lambda result: (-result["rank"]["c"], -result["rank"]["w"], -result["rank"]["b"], result["rank"]["r"]),
        )
        for i in range(0, len(roundresults)):
            roundresults[i]["board"] = i + 1
            roundresults[i].pop("rank")

    def update_individualbye_list(self, tournament):
        # json_output('-', tournament['gameList'])
        if tournament["teamTournament"]:
            return
        trans = {"F": "W", "H": "D", "P": "P", "W": "W", "D": "D", "L": "L", "U": "U", "A": "A", "Z": "Z"}
        gameList = tournament["gameList"]
        for bye in self.byelist:
            elemlist = [game for game in gameList if bye["round"] == game["round"] and bye["competitor"] == self.get_result_cid(game, "white")]
            if len(elemlist) == 0:
                game = {
                    "id": 0, 
                    "round": bye["round"], 
                    "white": {"cid": bye["competitor"], "result": bye["score"]}, 
                    "black": None, 
                    "played": False, 
                    "rated": False, 
                }
                self.append_result(gameList, game)
            else:
                elem = elemlist[0]
                if self.get_result_res(elem, "white", "") != bye["score"]:
                    self.put_status(405, "Error in bye score, competitor " + str(bye["competitor"]))

    #    forfeited
    #    {
    #        'type': ftype,  'WZ'/'ZZ'/'ZW'
    #        'round': rnd,
    #        'white': whiteteam,
    #        'black': blackteam,
    #    }

    def update_forfeited_list(self, tournament):
        # json_output('-', tournament['gameList'])
        # trans = {"F": "W", "H": "D", "P": "D", "W": "W", "D": "D", "L": "L", "U": "U", "Z": "Z"}
        for forfeited in self.forfeitedlist:
            # print(forfeited)
            white = list(
                filter(
                    lambda match: forfeited["round"] == match["round"] 
                       and (self.get_result_cid(match, "white") == forfeited["white"] 
                       or self.get_result_cid(match, "black") == forfeited["white"]),
                    tournament["matchList"],
                )
            )
            black = list(
                filter(
                    lambda match: forfeited["round"] == match["round"] 
                        and (self.get_result_cid(match, "white") == forfeited["black"] 
                         or self.get_result_cid(match, "black") == forfeited["black"]),
                    tournament["matchList"],
                )
            )
            # print('White', white, 'Black', black)
            if len(white) > 0 and len(black) > 0:
                white = white[0]
                black = black[0]
                if white != black:
                    white["black"]["cid"] = max(self.get_result_cid(black, "white"), self.get_result_cid(black, "black"))
                    white["white"]["result"] = forfeited["type"][0]
                    white["black"]["result"] = forfeited["type"][1]
                    matches = filter(lambda match: match["id"] != black["id"], tournament["matchList"])
                    tournament["matchList"] = list(matches)


    # ==============================
    #
    # Read TRF line

    def parse_trf_noop(self, tournament, line):
        pass

    def parse_trf_game(self, tournament, startno, currentround, sgame, score):
        if len(sgame.strip()) == 0:
            return None
        opponent = helpers.parse_int(sgame[0:4])
        color = sgame[5].lower()
        if color != "w" and color != "b" and color != "-" and color != " ":
            color = " "
        result = sgame[7].upper()
        res = self.results.get(result , self.results[" "])
        result = res["result"]
        played = res["played"]
        rated = res["rated"]
        # opponetnt == 0 and draw??

        if color == "b":
            white = opponent
            black = startno
        else:
            white = startno
            black = opponent
        score[result] = (score[result] if result in score else 0) + 1
        game = {"id": 0, "round": currentround, "white": {"cid": white}, "black": {"cid": black}, "played": played, "rated": rated}
        # section['results'].append(game)
        if color == "b":
            game["black"]["result"] = result
        else:
            game["white"]["result"] = result
        # if result == "U":
        #    score["pab"] = game
        if game["black"]["cid"] == 0:
            game["black"] = None
        self.append_result(tournament["gameList"], game)
        return game

    def parse_trf_player(self, tournament, line):
        #    print('parse')
        fideName = line[14:47].rstrip()
        names = fideName.split(",")
        while len(names) < 2:
            names.append("")
        ftitle = line[10:13].strip()
        ftitle = self.titles.get(ftitle, ftitle)

        rating = helpers.parse_int(line[48:52])
        profile = {
            "id": 0,
            "lastName": names[0].strip(),
            "firstName": names[1].strip(),
            "sex": line[9:10],
            "birth": helpers.parse_date(line[69:79]),
            "federation": line[53:56].strip(),
            "fideId": helpers.parse_int(line[57:68]),
            "fideName": fideName,
            "rating": [{"list": "TRF", "rating": rating}] if rating > 0 else [],
            "fideTitle": ftitle,
        }
        self.append_profile(profile)

        startno = helpers.parse_int(line[4:8])
        self.o001[startno] = line
        self.p001[startno] = line
        col = max(0, line[86:].find("w"), line[86:].find("b"))
        if col % 10:
            self.put_status(467, "Player " + str(startno) + " has misaligned data, may be bad character encoding") 
        gamePoints = helpers.parse_float(line[80:84])
        # score accumulates number of wins, draws and losses and will compare it to sum in order to guess score system
        competitor = {
            "cid": startno,
            "profileId": profile["id"],
            "present": startno > 0,
            "gamePoints": gamePoints,
            "rank": helpers.parse_int(line[85:89]),
            "rating": profile["rating"][0] if rating > 0 else None,
        }
        score = {"sum": gamePoints, "W": 0, "D": 0, "L": 0, "P": 0, "A": 0, "U": 0, "Z": 0}
        self.gamescores.append(score)
        # section['competitors'].append(competitor)
        self.pcompetitors[competitor["cid"]] = competitor
        linelen = len(line)
        currentround = 0
        lastplayed = 0
        lastpaired = 0
        for i in range(99, linelen + 1, 10):
            currentround += 1
            game = self.parse_trf_game(tournament, startno, currentround, line[i - 8 : i], score)
            # if startno == 31:
            #    print(currentround, game)
            if game is not None:
                if game["played"] and currentround > lastplayed:
                    lastplayed = currentround
                    if self.get_result_cid(game, "white") > 0 and self.get_result_cid(game, "black") > 0 and currentround > lastpaired:
                        lastpaired = currentround
        if lastplayed > tournament["numRounds"]:
            tournament["numRounds"] = lastplayed
        if lastpaired > tournament["currentRound"]:
            tournament["currentRound"] = lastpaired
        return 1

    def parse_trf_team(self, tournament, line):
        ext = line[0] == "3"
        tournament["teamTournament"] = True
        linelen = len(line)
        cid = helpers.parse_int(line[4:7]) if ext else len(self.bcompetitors) + 1
        teamname = (line[8:40] if ext else line[4:36]).rstrip()
        # nickname = line[41:46].rstrip() if ext else ""
        # strength = helpers.parse_int(line[47:53]) if ext else 0
        matchPoints = helpers.parse_float(line[54:60]) if ext else Decimal("0.0")
        gamePoints = helpers.parse_float(line[61:67]) if ext else Decimal("0.0")
        rank = helpers.parse_int(line[68:71]) if ext else 0
        if ext and line[71:74].strip() != "":
            self.put_status(467, "Team " + str(cid) + " has misaligned data, may be bad character encoding") 
        team = {"id": 0, "teamName": teamname, "players": []}
        teamid = self.append_team(team, 0)
        # players = []

        competitor = {
            "cid": cid,
            "teamId": teamid,
            "rank": rank,
            "present": True,
            "matchPoints": matchPoints,
            "gamePoints": gamePoints,
            "cplayers": [],
        }
        # cplayers = tournament['playerSection']['competitors']
        tournament["competitors"].append(competitor)
        board = 0
        for i in range(77 if ext else 40, linelen + 1, 5):
            board += 1
            pid = helpers.parse_int(line[i - 4 : i])
            if pid == 0:
                continue
            self.check_player(line[0:3], pid)
            self.pcompetitors[pid]["order"] = board 
            competitor["cplayers"].append(self.pcompetitors[pid])
            self.pcompetitors[pid]["teamId"] = teamid
            self.cboard[pid] = board
            # self.cteam[pid] = competitor['cid']
        if ext:
            self.tcompetitors[cid] = competitor
        else:
            self.bcompetitors[cid] = competitor

    def parse_trf_info(self, tournament, info, value):
        self.chessjson["event"]["eventInfo"][info] = value
        tournament["tournamentInfo"][info] = value

    def parse_trf_tournament(self, tournament, line):
        trfvalue = line[4:]
        self.parse_trf_info(tournament, "fullName", trfvalue)

    def parse_trf_site(self, tournament, line):
        trfvalue = line[4:]
        self.parse_trf_info(tournament, "site", trfvalue)

    def parse_trf_federation(self, tournament, line):
        trfvalue = line[4:]
        self.parse_trf_info(tournament, "federation", trfvalue)

    def parse_trf_startdate(self, tournament, line):
        trfvalue = line[4:]
        self.parse_trf_info(tournament, "startDate", helpers.parse_date(trfvalue))

    def parse_trf_enddate(self, tournament, line):
        trfvalue = line[4:]
        self.parse_trf_info(tournament, "endDate", helpers.parse_date(trfvalue))

    def parse_trf_ttype(self, tournament, line):
        trfvalue = line[4:]
        if line[0] == "0":
            tournament["tournamentType"] = trfvalue
        else:
            tournament["pairingcontrollerid"] = trfvalue

    def parse_trf_typetournament(self, tournament, line):
        trfvalue = line[4:].upper()
        self.parse_trf_info(tournament, "typeOfTournament", trfvalue)
        rec = self.code192[trfvalue] if trfvalue in self.code192 else {}
        tournament.update(rec)
        if "_MP_GP" in trfvalue:
            tournament["scoreSystem"]["primary"] = "match"
            tournament["scoreSystem"]["secondary"] = "game"
        elif "_GP_MP" in trfvalue:
            tournament["scoreSystem"]["primary"] = "game"
            tournament["scoreSystem"]["secondary"] = "match"
        elif "_MP" in trfvalue:
            tournament["scoreSystem"]["primary"] = "match"
        elif "_GP" in trfvalue:
            tournament["scoreSystem"]["primary"] = "game"

    def parse_timecontrol(self, tournament, line):
        trfvalue = line[4:]
        if line[0] == "1":
            tournament["timeControl"]["description"] = trfvalue
        else:
            tournament["timeControl"]["encoded"] = trfvalue

    def parse_trf_dates(self, tournament, line):
        linelen = len(line)

        tournament["rounds"] = []
        currentround = 0
        for j in range(99, linelen + 1, 10):
            currentround += 1
            date = line[j - 8 : j]
            tournament["rounds"].append({"roundNo": currentround, "startTime": helpers.parse_date(date)})
        return

    def parse_trf_arbiter(self, is_ca, line):
        linelen = len(line.rstrip())
        if linelen == 3:
            return
        numbers = re.findall(r'\d+', line)
        maxval = max([int(n) for n in numbers] )
        fideid = maxval if maxval > 100000 else 0
        if fideid:
            line = line.replace(str(fideid), "")
        line = line[4:].rstrip()
        nameparts = line.split(" ")
        sname = 0
        otitle = ""
        ename = len(nameparts) - 1
        if nameparts[0] == "IA" or nameparts[0] == "FA":
            sname = 1
            otitle = nameparts[0]
        lastname = nameparts[ename]
        firstname = " ".join(nameparts[sname:ename])
        profile = {
            "id": 0,
            "fideId": fideid,
            "firstName": firstname,
            "lastName": lastname,
            "sex": "u",
            "federation": "",
            "fideName": lastname + ", " + firstname,
            "fideOTitle": otitle,
        }
        pid = self.append_profile(profile)
        event = self.chessjson["event"]
        if "arbiters" not in event["eventInfo"]:
            event["eventInfo"]["arbiters"] = {"chiefArbiter": 0, "arbiters": []}
        if is_ca:
            event["eventInfo"]["arbiters"]["chiefArbiter"] = pid
        else:
            event["eventInfo"]["arbiters"]["arbiters"].append(pid)
        return

    def parse_trf_ca_arbiter(self, tournament, line):
        self.parse_trf_arbiter(True, line)

    def parse_trf_da_arbiter(self, tournament, line):
        self.parse_trf_arbiter(False, line)

    def parse_trf_timecontrol(self, tournament, line):
        trfvalue = line[4:]
        tournament["timeControl"]["description"] = trfvalue

    def parse_tiebreaks(self, tournament, line, has_pts):
        pts = "" if has_pts else "PTS "
        self.tiebreaks = (pts + line[4:]).replace(",", " ").split(" ")
        tournament["rankOrder"] = self.tiebreaks

    def parse_tiebreaks202(self, tournament, line):
        self.parse_tiebreaks(tournament, line, False)

    def parse_tiebreaks212(self, tournament, line):
        self.parse_tiebreaks(tournament, line, True)

    def parse_colorsequence(self, tournament, line):
        seq = line[4:].strip()
        tournament["teamSize"] = len(seq)
        tournament["teamColor"] = seq[0].upper()
        tournament["teamSequence"] = seq.upper()

    def parse_trf_numbrounds(self, tournament, line):
        tournament["numRounds"] = helpers.parse_int(line[4:].rstrip())

    def parse_trf_initialcolor(self, tournament, line):
        tournament["topColor"] = line[4:].rstrip().upper()

    def parse_trf_gamescore(self, tournament, line):
        self.parse_trf_scoresystem(tournament, line, "game")

    def parse_trf_matchscore(self, tournament, line):
        self.parse_trf_scoresystem(tournament, line, "match")

    def parse_trf_scoresystem(self, tournament, line, scoretype):
        scoresystem = {}
        trans = {
            "W": "W",
            "D": "D",
            "L": "L",
            "P": "P",
            "A": "Z",
            "X": "A",
        }
        for pos in range(5, len(line) - 1, 9):
            sym = line[pos].upper()
            pts = helpers.parse_float(line[pos + 1 : pos + 5])
            if sym in trans:
                # print(sym, pts)
                scoresystem[trans[sym]] = pts
        self.scores.add_scoresystem(scoretype, scoresystem)

    def parse_trf_natsupport(self, tournament, line):
        national = self.national
        national["federation"] = line[4:7].strip()
        national["mode"] = line[8:13].strip()
        # match national["mode"]:
        if national["mode"] == "FIDE":
            national["func"] = helpers.rating_fide
        elif national["mode"] == "NRO":
            national["func"] = helpers.rating_nro
        elif national["mode"] == "FIDON":
            national["func"] = helpers.rating_fidon
        elif national["mode"] == "NIDOF":
            national["func"] = helpers.rating_nidof
        elif national["mode"] == "HBFN":
            national["func"] = helpers.rating_hbfn
        elif national["mode"] == "LBFN":
            national["func"] = helpers.rating_lbfn
        elif national["mode"] == "OTHER":
            national["func"] = helpers.rating_other
        else:
            self.put_status(472, "parse_trf_nationalsupport: " + national["mode"] + " not matched")
        self.add_ratinglist(national["federation"])

    def parse_trf_natrating(self, tournament, line):
        startno = helpers.parse_int(line[4:8])
        rating = helpers.parse_int(line[48:52])
        if rating == 0:
            rating = None

        fideName = line[14:47].rstrip()
        names = fideName.split(",")
        while len(names) < 2:
            names.append("")
        title = line[10:13].strip()
        competitor = self.pcompetitors[startno]
        profile = self.pids[competitor["profileId"]]
        profile["lastName"] = names[0].strip()
        profile["lfirstName"] = names[1].strip()
        profile["sex"] = line[9:10]
        rating = {"list": self.national["federation"], "rating": rating} if rating is not None else None
        if rating is not None:
            profile["rating"].append(rating)
        competitor["rating"] = self.national["func"](competitor["rating"], rating)
        return 1

    def parse_trf_absent(self, tournament, line):
        for elem in line[4:].replace(",", " ").replace("/", " ").split(" "):
            num = helpers.parse_int(elem)
            if num > 0:
                self.check_player(line[0:3], num)
                self.pcompetitors[num]["present"] = False
        return

    def parse_trf_configuration(self, tournament, line):
        # TODO+4 XXC  -not really important
        return

    def parse_trf_accelerated(self, tournament, line):
        if "accelerated" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["accelerated"] = acc
        matchPoints = helpers.parse_float(line[4:8])
        gamePoints = helpers.parse_float(line[9:13])
        firstround = helpers.parse_int(line[14:17])
        lastround = helpers.parse_int(line[18:21])
        if lastround == 0:
            lastround = firstround
        firstcompetitor = helpers.parse_int(line[22:26])
        lastcompetitor = helpers.parse_int(line[27:31]) if len(line) >= 31 else 0
        if lastcompetitor == 0:
            lastcompetitor = firstcompetitor
        value = {
            "matchPoints": matchPoints,
            "gamePoints": gamePoints,
            "firstRound": firstround,
            "lastRound": lastround,
            "firstCompetitor": firstcompetitor,
            "lastCompetitor": lastcompetitor,
        }
        tournament["accelerated"]["values"].append(value)
        self.check_competitor(tournament, line[0:3], firstcompetitor)
        self.check_competitor(tournament, line[0:3], lastcompetitor)
        return

    def parse_trf_prohibited(self, tournament, line):
        linelen = len(line)
        if "prohibited" not in tournament:
            pro = {"name": "Pro", "values": []}
            tournament["prohibited"] = pro = []
        firstround = helpers.parse_int(line[4:7])
        lastround = helpers.parse_int(line[8:11])
        if lastround == 0:
            lastround = firstround

        competitors = []
        for i in range(16, len(line) + 1, 5):
            competitor = helpers.parse_int(line[i - 4 : i])
            self.check_competitor(tournament, line[0:3], competitor)
            competitors.append(competitor)
        value = {
            "firstRound": firstround,
            "lastRound": lastround,
            "competitors": competitors,
        }
        tournament["prohibited"].append(value)
        
        return

    def parse_trf_outoforder(self, tournament, line):
        order = []
        rnd = helpers.parse_int(line[4:7])
        oooteam = helpers.parse_int(line[8:11])
        otherteam = helpers.parse_int(line[12:15])
        self.check_competitor(tournament, line[0:3], oooteam)
        self.check_competitor(tournament, line[0:3], otherteam)

        for i in range(20, len(line) + 1, 5):
            if len(line[i - 4:]):
                player = helpers.parse_int(line[i - 4 : i])
                if player > 0:
                    self.check_competitor(tournament, line[0:3], player, "player")
                order.append(player)
        ooo = {"round": rnd, "oooteam": oooteam, "otherteam": otherteam, "order": order}
        self.ooolist.append(ooo)
        # print(ooo)

    def parse_trf_abnormal(self, tournament, line):
        linelen = len(line)
        teams = []
        att = {
            "att": line[4],
            "matchPoints": helpers.parse_float(line[7:11]),
            "gamePoints": helpers.parse_float(line[13:17]),
            "round": helpers.parse_int(line[19:22]),
            "teams": teams,
        }
        for i in range(27, linelen + 1, 5):
            team = helpers.parse_int(line[i - 4 : i])
            teams.append(team)
            self.check_competitor(tournament, line[0:3], team)
        if att["round"] == 0 and (len(teams) == 0 or teams[0] == 0):
            self.scores.add_unplayed(att["att"], att["matchPoints"], att["gamePoints"])
        else:
            self.aatlist.append(att)

    def parse_trf_acceleratedv4(self, tournament, line):
        linelen = len(line)
        if "accelerated" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["accelerated"] = acc
        # scorename = tournament["scoreSystem"] if tournament["teamTournament"] else tournament["gameScoreSystem"]
        scoresystem = self.scoreLists[tournament["scoreSystem"]]
        competitor = helpers.parse_int(line[4:8])
        groups = {"W": [], "D": [], "L": [], "Z": []}
        currentround = 0
        # lastplayed = 0
        # lastpaired = 0
        for i in range(9, linelen - 3, 5):
            currentround += 1
            points = helpers.parse_float(line[i : i + 4])
            score = "Z"
            for s in groups.keys():
                if scoresystem[s] == points:
                    score = s
            groups[score].append(currentround)
        for s in ["W", "D", "L"]:
            start = 0
            cgroup = groups[s]
            c_len = len(cgroup)
            while start < c_len:
                stop = start
                while stop < c_len and cgroup[stop] - cgroup[start] == stop - start:
                    stop += 1
                value = {
                    "matchScore": s,
                    "gameScore": s,
                    "firstRound": cgroup[start],
                    "lastRound": cgroup[stop - 1],
                    "firstCompetitor": competitor,
                    "lastCompetitor": competitor,
                }
                tournament["accelerated"]["values"].append(value)
                start = stop
        return

    def parse_trf_pab(self, tournament, line):
        matchPoints = helpers.parse_float(line[4:8])
        gamePoints = helpers.parse_float(line[9:13])
        self.scores.add_unplayed("P", matchPoints, gamePoints)
        rnd = 1
        for i in range(17, len(line) + 1, 4):
            competitor = helpers.parse_int(line[i - 3 : i])
            if competitor > 0:
                self.check_competitor(tournament, line[0:3], competitor)
                self.byelist.append(
                    {
                        "type": "P",
                        "competitor": competitor,
                        "round": rnd,
                        "matchPoints": matchPoints,
                        "gamePoints": gamePoints,
                    }
                )
            rnd += 1

    def parse_trf_bye(self, tournament, line, idsize):
        # for 240 record idsize=4, for 330 record idsize=3
        trans = {" ": "Z", "Z": "Z", "H": "D", "F": "W"}
        bye = line[4].upper()
        score = trans[bye]
        rnd = helpers.parse_int(line[6:9])
        for i in range(10 + idsize, len(line) + 1, idsize + 1):
            competitor = helpers.parse_int(line[i - idsize : i])
            if competitor > 0:
                self.check_competitor(tournament, line[0:3], competitor)
                self.byelist.append(
                    {
                        "type": bye,
                        "wResult": score,
                        "competitor": competitor,
                        "round": rnd,
                        "score": score,
                    }
                )

    def parse_trf_bye3(self, tournament, line):
        self.parse_trf_bye(tournament, line, 3)

    def parse_trf_bye4(self, tournament, line):
        self.parse_trf_bye(tournament, line, 4)

    def parse_forfeited(self, tournament, line):
        forfeit = line[4:6].upper()
        rnd = helpers.parse_int(line[7:10])
        whiteteam = helpers.parse_int(line[11:14])
        blackteam = helpers.parse_int(line[15:18])
        forfeitedtrans = { "10": "WZ", "WL": "WZ", "WZ": "WZ", "+-": "WZ",  
                           "00": "ZZ", "LL": "ZZ", "ZZ": "ZZ", "--": "ZZ", 
                           "01": "ZW", "LW": "ZW", "ZW": "ZW", "-+": "ZW", 
                           }
        
        ftype = forfeitedtrans[forfeit]
        self.forfeitedlist.append(
            {
                "type": ftype,
                "round": rnd,
                "white": whiteteam,
                "black": blackteam,
            }
        )

    # Experimental

    def trf_update_game(self, tournament, game, trans):
        rnd = game["round"]
        score = {
            "-": Decimal("0.0"),
            "+": Decimal("1.0"),
            "Z": Decimal("0.0"),
            "H": Decimal("0.5"),
            "F": Decimal("1.0"),
            "U": Decimal("0.5"),
        }
        for player in ["white", "black"]:
            sno = game[player["cid"]]
            if sno > 0:
                line = self.p001[sno]
                gp = helpers.parse_float(line[80:84])
                other = self.get_result_cid(game, "white") if player == "black" else self.get_result_cid(game, "black")
                # tno = self.cteam[sno]
                # if tno == 3:
                # print(line)
                col = player[0] if self.get_result_cid(game, "black") > 0 else "-"
                oldres = line[88 + 10 * rnd]
                newres = trans[game[player]["result"]] if col != "-" else trans[game["white"]["result"]]
                opp = f"{other:4}" if other > 0 else "0000"
                line = line[: 81 + 10 * rnd] + opp + " " + col + " " + newres + line[89 + 10 * rnd :]
                if oldres != newres:
                    gp = gp - score[oldres] + score[newres]
                    line = line[:80] + f"{gp:4.1f}" + line[84:]
                self.p001[game[player]] = line
                # if tno == 3:
                # print(line)
                # tno = self.cteam[sno]
                # team = self.tcompetitors[tno]
                # print(team)
                # sys.exit(0)

    def parse_trf_acc(self, tournament, line):
        if "accelerated" not in tournament:
            acc = {"name": "Acc", "values": []}
            tournament["accelerated"] = acc
        points = helpers.parse_float(line[4:8])
        firstround = helpers.parse_int(line[9:12])
        lastround = helpers.parse_int(line[13:16])
        firstcompetitor = helpers.parse_int(line[17:21])
        lastcompetitor = helpers.parse_int(line[22:26])
        score = self.points2score(tournament, tournament["teamTournament"], points)
        value = {
            "matchScore": score,
            "gameScore": score,
            "firstRound": firstround,
            "lastRound": lastround,
            "firstCompetitor": firstcompetitor,
            "lastCompetitor": lastcompetitor,
        }
        tournament["accelerated"]["values"].append(value)

    def parse_trf_tse(self, tournament, line):
        # print(line)
        # linelen = len(line)
        tpn = helpers.parse_int(line[4:7])
        tp = helpers.parse_int(line[8:12])
        # nickname = line[13:18]
        # strength = helpers.parse_int(line[19:25])
        rank = helpers.parse_int(line[26:29])
        matchPoints = helpers.parse_int(line[30:34])
        gamePoints = helpers.parse_float(line[35:41])
        # team = self.tcompetitors[cid]
        competitor = {
            "cid": tpn,
            "teamId": 0,
            "rank": rank,
            "present": True,
            "matchPoints": matchPoints,
            "gamePoints": gamePoints,
            "tieBreakScore": [],
            "cplayers": [],
            "topPlayer": tp,
        }
        self.tcompetitors[tpn] = competitor

    def parse_trf_ooo(self, tournament, line):
        linelen = len(line)
        debug = line[0:27] == "?OOO   1   14    0   29   39"

        rnd = helpers.parse_int(line[4:7])
        nulls = 0
        pnums = []
        snums = []
        pteam = steam = 0
        trans = {"W": "+", "L": "-", "Z": "-"}
        for i in range(12, linelen + 1, 5):
            num = helpers.parse_int(line[i - 4 : i])
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
        glen = len(pnums) // 2
        if steam == 0:
            glen = len(pnums)
            for game in tournament["playerSection"]["results"]:
                if game["round"] == rnd:
                    wteam = self.cteam[self.get_result_cid(game, "white")]
                    bteam = self.cteam[self.get_result_cid(game, "black")]
                    if pteam in [wteam, bteam] and wteam > 0 and bteam > 0:

                        steam = wteam + bteam - pteam
        else:
            snums = pnums[len(pnums) // 2 :]
            pnums = pnums[: len(pnums) // 2]
        presults = tournament["playerSection"]["results"]
        for game in presults:
            if game["round"] == rnd:
                wteam = self.cteam[self.get_result_cid(game, "white")]
                bteam = self.cteam[self.get_result_cid(game, "black")]
                if pteam in [wteam, bteam]:
                    pgames.append(game)
                if steam in [wteam, bteam]:
                    sgames.append(game)
        if len(snums) == 0:
            cplayers = self.tcompetitors[steam]["cplayers"]
            for player in cplayers:
                game = list(filter(lambda game: self.get_result_cid(game, "white") == player["cid"] or self.get_result_cid(game, "black") == player["cid"], sgames))[0]
                sgames.append(game)
            p = s = 0
            lastc = "b"
            for i in range(0, len(pnums)):
                c = pnums[i]
                if c > 0:
                    while self.get_result_cid(pgames[p], "white") != c and self.get_result_cid(pgames[p], "black") != c:
                        p = (p + 1) % len(pgames)
                    game = pgames[p]
                    lastc = "w" if self.get_result_cid(game, "white") == c else "b"
                    while sgames[s % len(sgames)]["id"] != game["id"] and s < len(sgames) * (p + 1):
                        s += 1
                    if sgames[s % len(sgames)]["id"] == game["id"]:
                        snums.append(self.get_result_cid(game, "white") + self.get_result_cid(game, "black") - c)
                        s += 1
                    p = (p + 1) % len(pgames)
                else:
                    while self.get_result_res(pgames[p], "white") != "Z" or self.get_result_cid(pgames[p], "black") != 0:
                        p = (p + 1) % len(pgames)

                    while self.get_result_res(sgames[s], "white") != "W" or self.get_result_cid(sgames[s], "black") != 0:
                        s += 1
                    pplayer = self.get_result_cid(pgames[p], "white")
                    splayer = self.get_result_cid(sgames[s], "white")
                    game = {
                        "id": 0,
                        "round": rnd,
                        "white": {"cid": splayer if lastc == "w" else pplayer},
                        "black": {"cid": pplayer if lastc == "w" else splayer},
                        "played": False,
                        "rated": False,
                    }
                    presults.remove(pgames[p])
                    presults.remove(sgames[s])
                    pgames[p] = game
                    sgames[s] = game
                    # section['results'].append(game)
                    game["white"]["result"] = "W" if self.get_result_cid(game, "white") == splayer else "L"
                    game["black"]["result"] = "W" if self.get_result_cid(game, "black") == splayer else "L"
                    self.append_result(tournament["gameList"], game)
                    self.trf_update_game(tournament, game, trans)

        if debug:
            json.dump(pgames, sys.stdout, indent=2)
            json.dump(sgames, sys.stdout, indent=2)
        # print('OOQ ' + f"{rnd:3}"+ f"{pteam:4}" + ' ' + line[7:])
        for i in range(0, glen):
            num = pnums[i]
            game = list(filter(lambda game: self.get_result_cid(game, "white") == num or self.get_result_cid(game, "black") == num, pgames))
        return

    def parse_trf_npg(self, tournament, line, letter, points):
        linelen = len(line)
        trans = {"U": "U", "Z": "-", "H": "H", "F": "F", "-": "-"}
        trres = {"U": "D", "Z": "Z", "H": "D", "F": "W", "-": "L"}
        rnd = 0
        for i in range(7, linelen + 1, 4):
            rnd += 1
            num = helpers.parse_int(line[i - 3 : i])
            if num > 0:
                games = list(
                    filter(
                        lambda game: game["round"] == rnd and self.cteam[self.get_result_cid(game, "white")] == num,
                        tournament["playerSection"]["results"],
                    )
                )
                nzgames = list(filter(lambda game: self.get_result_res(game, "white") != "Z", games))

                pteam = self.tcompetitors[num]
                ind = 0
                myletter = letter
                for cplayer in pteam["cplayers"]:
                    lgame1 = list(filter(lambda game: self.get_result_cid(game, "white") == cplayer, nzgames))
                    lgame2 = list(filter(lambda game: self.get_result_cid(game, "white") == cplayer, games))
                    game = lgame2[0] if len(lgame1) == 0 else lgame1[0]
                    if ind >= 4:
                        myletter = "-"
                    game["white"]["result"] = myletter
                    game["played"] = myletter == "U"
                    game["rated"] = False

                    self.trf_update_game(tournament, game, trans)
                    game["white"]["result"] = trres[myletter]
                    ind += 1

    def parse_trf_forfeit(self, tournament, line, wletter, lletter):
        # linelen = len(line)
        trans = {"W": "+", "L": "-", "Z": "-"}
        rnd = helpers.parse_int(line[4:7])
        win = helpers.parse_int(line[8:11])
        los = helpers.parse_int(line[12:15])
        # print('FF', rnd, win, los, wletter, lletter)
        wpteam = self.tcompetitors[win]
        lpteam = self.tcompetitors[los]
        ind = 0
        for i in range(0, len(wpteam["cplayers"])):
            # if ind == 4:
            #    break
            wp = wpteam["cplayers"][i]
            lp = lpteam["cplayers"][ind]
            game = {
                "id": 0,
                "round": rnd,
                "white": {"cid": wp if i in [0, 2] else lp, "result": wletter if i in [0, 2] else lletter},
                "black": {"cid": lp if i in [0, 2] else wp, "result": lletter if i in [0, 2] else wletter},
                "played": False,
                "rated": False,
            }
            presults = tournament["playerSection"]["results"]
            games = list(filter(lambda game: game["round"] == rnd and (self.get_result_cid(game, "white") == wp["cid"] or self.get_result_cid(game, "white") == lp["cid"]), presults))
            # nzgames = list(filter(lambda game: game['wResult'] != 'Z', games))

            if len(games) == 2 and (games[0]["white"]["result"] == wletter or games[1]["white"]["result"] == wletter):
                for rgame in games:
                    presults.remove(rgame)
                self.append_result(presults, game)
                self.trf_update_game(tournament, game, trans)
                ind += 1
            games = list(filter(lambda game: game["round"] == rnd and (self.get_result_cid(game, "white") == wp["cid"] or self.get_result_cid(game, "white") == lp["cid"]), presults))
            # print(games)

    def parse_test_xxx(self, tournament, line):
        gp = {}
        for key, line in self.p001.items():
            cid = self.cteam[helpers.parse_int(line[4:8])]
            gp2 = helpers.parse_float(line[80:84])

            gp[cid] = (gp[cid] + gp2) if cid in gp else gp2

        sum1 = sum2 = 0
        for key, competitor in self.tcompetitors.items():
            cid = competitor["cid"]
            gp1 = competitor["gamePoints"]
            gp2 = gp[cid]
            sum1 += gp1
            sum2 += gp2
        # if gp1 != gp2:
        #        print(cid, gp1, gp2)
        # print(sum1, sum2)

    # More

    def export_trf(self, params):
        with open(params["output_file"], "w") as f:
            json.dump(self.chessjson["event"], f, indent=2)

    def prepare_player_section(self, tournament):
        tournament["competitors"] = sorted(list(self.pcompetitors.values()), key=lambda g: (g["cid"]))

    def prepare_team_section_013(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.bcompetitors.items():
            cplayers = competitor["cplayers"]
            competitor["cplayers"] = []
            for pcid in cplayers:
                cplayer = self.pcompetitors[pcid["cid"]]
                competitor["cplayers"].append(cplayer)
                tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])

            self.tcompetitors[competitor["cid"]] = competitor
        # print(self.tcompetitors)
        self.prepare_team_section(tournament, False)

    def prepare_team_section_310(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.tcompetitors.items():
            if "topPlayer" in competitor:
                pcid = competitor["topPlayer"]
                competitor.pop("topPlayer")
                bcompetitor = self.bcompetitors[pcid]
                competitor["teamId"] = bcompetitor["teamId"]
                for pcid in bcompetitor["cplayers"]:
                    cplayer = self.pcompetitors[pcid]
                    competitor["cplayers"].append(cplayer)
                    tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])
            else:
                bcompetitor = competitor
                for pcid in competitor["cplayers"]:
                    # print(type(pcid))
                    cplayer = self.pcompetitors[pcid if isinstance(pcid, int) else pcid["cid"]]
                    tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])

                # print(self.pcompetitors[pcid])
        # print('TSE')
        self.prepare_team_section(tournament, True)

    def prepare_team_section_tse(self, tournament):
        # pids = self.all_pids()
        tids = self.all_tids()
        for key, competitor in self.tcompetitors.items():
            pcid = competitor["topPlayer"]
            competitor.pop("topPlayer")
            bcompetitor = self.bcompetitors[pcid]
            competitor["teamId"] = bcompetitor["teamId"]
            for pcid in bcompetitor["cplayers"]:
                cplayer = self.pcompetitors[pcid]
                competitor["cplayers"].append(cplayer)
                tids[cplayer["teamId"]]["players"].append(cplayer["profileId"])
                # print(self.pcompetitors[pcid])
        # print('TSE')
        # print(self.tcompetitors)
        self.prepare_team_section(tournament, True)

    def prepare_team_section(self, tournament, haspointsupdated):
        # update players in teams

        
        cteam = self.cteam
        for cid, team in self.tcompetitors.items():
            for player in team["cplayers"]:
                cteam[player["cid"]] = cid
        options = {
            "byelist": self.byelist,
            "forfeitedlist": self.forfeitedlist,
            "ooolist": self.ooolist,
            "current_id": self.current_id
            }
        g2m = games2matches.games2matches(self, tournament, options)
        matches = g2m.merge_matches()
        self.current_id = g2m.get_current_id()
        tournament["matchList"] = [match for key, match in matches.items()]
        # self.merge_matches(tournament)

        # tournament['matchList'] = sorted(list(matches.values()), key=lambda g: (g['id']))
        tournament["competitors"] = sorted(list(self.tcompetitors.values()), key=lambda g: (g["cid"]))
        if haspointsupdated:
            self.validate_team_scores(tournament)
        else:
            self.update_team_score(tournament)

    def validate_team_scores(self, tournament):
        """Check the match- and game-point totals declared by TRF26 record 310."""
        calculated_match = {competitor["cid"]: Decimal("0.0") for competitor in tournament["competitors"]}
        for match in tournament["matchList"]:
            if match["round"] > tournament["currentRound"] and self.get_result_res(match, "white") != "P":
                continue
            white = self.get_result_cid(match, "white")
            black = self.get_result_cid(match, "black")

            if white > 0:
                calculated_match[white] += self.scores.get_score(
                tournament, "match", self.get_result_res(match, "white")
                )
            if black > 0:
                calculated_match[black] += self.scores.get_score(
                tournament, "match", self.get_result_res(match, "black")
                )

        badteams = []
        for competitor in tournament["competitors"]:
            cid = competitor["cid"]
            calculated_game = sum(
                (player["gamePoints"] for player in competitor["cplayers"]),
                Decimal("0.0"),
            )
            if (
                competitor["matchPoints"] != calculated_match[cid]
                or competitor["gamePoints"] != calculated_game
            ):
                badteams.append(str(cid))

        if badteams and False:
            raise GacruxInputError(
                "record 310 reports incorrect match or game points for team(s) "
                + ", ".join(badteams)
            )


    def update_team_score(self, tournament):
        for competitor in tournament["competitors"]:
            pass

    # Module test

    def dumpresults(self):
        event = self.chessjson["event"]
        cmps = event["status"]["competitors"]
        print(cmps)
        tcmps = {elem["startno"]: elem for elem in cmps}
        competitors = event["tournaments"][0]["teamSection"]["competitors"]
        for competitor in competitors:
            cid = competitor["cid"]
            sgp = 0
            for player in competitor["cplayers"]:
                trf = self.p001[player]
                country = trf[53:56]
                gp = helpers.parse_float(trf[80:84])
                sgp += gp

            print(f"{cid:2}" + "  - " + country)
            eq = competitor["matchPoints"] == tcmps[cid]["tiebreakDetails"][0]["val"] and competitor["gamePoints"] == tcmps[cid]["calculations"][1]["val"]
            print("TSE:", f"{competitor['matchPoints']:4.1f}", f"{competitor['gamePoints']:5.1f}")
            print("001:", f"{'':4}", f"{sgp:5.1f}")
            print(
                "TBS:",
                f"{tcmps[cid]['tiebreakDetails'][0]['val']:4.1f}",
                f"{tcmps[cid]['calculations'][1]['val']:5.1f}",
                "" if eq else "*****",
            )
            print("Org:")
            for player in competitor["cplayers"]:
                trf = self.o001[player]
                print(trf)
            print("Mod:")
            for player in competitor["cplayers"]:
                trf = self.p001[player]
                print(trf)
            currentround = 0
            linelen = len(trf)
            line = f"{'':89}"
            for i in range(99, linelen + 1, 10):
                currentround += 1
                line += f"{tcmps[cid]['tiebreakDetails'][0][currentround]:10.1f}"
            print(line)
            currentround = 0
            line = f"{'':89}"
            for i in range(99, linelen + 1, 10):
                currentround += 1
                line += f"{tcmps[cid]['tiebreakDetails'][1][currentround]:10.1f}"
            print(line)

        print()
        for key, trf in self.p001.items():
            print(trf)

    # ==============================
    #
    # Write TRF file

    def output_file(self, event, tournamentno, verbose):
        #
        # Set up the structure
        #

        self.chessjson["event"] = event
        tournament = self.get_tournament(tournamentno)
        self.scores = scoresystem.scoresystem()
        self.scores.score = tournament["scoreSystem"]
        self.profiles = {p["id"]: p for p in self.chessjson["event"]["profiles"]}
        return self.output_all_lines(tournament, verbose)

    def output_all_lines(self, tournament, verbose):
        all_lines = ""
        for record in self.trfrecords:
            trfid = record["id"]
            func = record["write"]
            try:
                all_lines += func(tournament, record["id"])
                # all_lines += self.output_line(tournament, record["id"])
            except:
                if verbose:
                    raise
                self.put_status(401, "Error writing trf-file, line " + trfid)
                return ""
        return all_lines

    """
    def output_line(self, tournament, trfkey):
        line = ""
        match trfkey:  # noqa
            case "001":
                line = self.output_trf_player(tournament, trfkey)
            case "012":
                line = self.output_trf_info(tournament, trfkey)
            case "022":
                line = self.output_trf_info(tournament, trfkey)
            case "032":
                line = self.output_trf_info(tournament, trfkey)
            case "042":
                line = self.output_trf_datetime(tournament, trfkey)
            case "052":
                line = self.output_trf_datetime(tournament, trfkey)
            case "062":
                line = self.output_trf_num_comp(tournament, trfkey)
                pass
            case "072":
                line = self.output_trf_num_comp(tournament, trfkey)
                pass
            case "082":
                # numteams = int(trfvalue)
                return ""
            case "092":
                line = self.output_trf_ttype(tournament, trfkey)
            case "102":
                line = self.output_trf_arbiter(tournament, trfkey)
            case "112":
                line = self.output_trf_arbiter(tournament, trfkey)
            case "122":
                time = self.output_trf_timecontrol(tournament, trfkey)
            case "132":
                line = self.output_trf_dates(tournament, trfkey)
            case "142":
                line = self.output_trf_numrounds(tournament, trfkey)
            case "152":
                line = self.output_trf_topcolor(tournament, trfkey)
            case "162":
                line = self.output_trf_gamescore(tournament, trfkey)
            case "250":
                line = self.output_trf_accelerated(tournament, trfkey)
            case "260":
                line = self.output_trf_prohibited(tournament, trfkey)
            case _:
                # print("Unknown key:", trfkey)
                # sys.exit(0)
                pass
        return line
    """

    def output_trf_noop(self, tournament, trfkey):
        return ""

    def output_trf_player(self, tournament, trfkey):
        resw = [{"W": "+", "D": "D", "L": "-", "Z": "-", "A": "?"}, {"W": "1", "D": "=", "L": "0", "Z": "0", "A": "?"}]
        resb = [{"W": "-", "D": "D", "L": "+", "Z": "+", "A": "?"}, {"W": "0", "D": "=", "L": "1", "Z": "1", "A": "?"}]
        unpl = [{"W": "F", "D": "H", "L": "Z", "Z": "Z", "A": "?", "P": "U"}, {"W": "U", "D": "U", "L": "U", "Z": "U", "A": "?", "P": "U"}]

        t001 = ""
        for cmp in sorted(tournament["competitors"], key=lambda c: c["cid"]):
            profile = self.profiles[cmp["profileId"]]
            if len(profile['federation']) > 3: 
                self.put_status(402, "Error when writing trf-file, Federation = "+ profile['federation'])
                return ""
            line = (
                f"001 {cmp['cid']:>4} "
                + f"{profile['sex']:1}"
                + f"{profile['fideTitle'] if 'fideTitle' in profile else '':>3} "
                + f"{helpers.format_name(profile):<33} "
                + f"{cmp['rating']['rating'] if 'rating' in cmp and cmp['rating'].get('rating', 0) > 0 else '':>4} "
                + f"{profile['federation'] if 'federation' in profile else '':<3} "
                + f"{profile['fideId'] if 'fideId' in profile and profile['fideId'] > 0 else '':>11} "
                + f"{profile['birth'] if 'birth' in profile else '':>10} "
                + f"{cmp['gamePoints']:>4.1f} "
                + f"{cmp['rank']:>4}"
            )
            games = sorted([game for game in tournament["gameList"] if self.get_result_cid(game, "white") == cmp["cid"] or self.get_result_cid(game, "black") == cmp["cid"]], key=lambda c: c["round"])
            maxround = tournament["currentRound"]
            for rnd in range(1, maxround + 1):
                cgame = [game for game in games if game["round"] == rnd]
                if len(cgame) > 0:
                    game = cgame[0]
                    played = 1 if game["played"] else 0
                    if self.get_result_cid(game, "white") == cmp["cid"]:
                        if "black" in game and self.get_result_cid(game, "black") > 0:
                            opp = self.get_result_cid(game, "black")
                            col = "w"
                            res = resw[played][self.get_result_res(game, "white")]
                        else:
                            opp = "0000"
                            col = "-"
                            res = unpl[played][self.get_result_res(game, "white")]
                    else:
                        opp = self.get_result_cid(game, "white")
                        col = "b"
                        res = resw[played][self.get_result_res(game, "black")] if "black" in game else resb[played][self.get_result_res(game, "white")]
                    line += f"  {opp:>4} {col:1} {res:1}"
                else:
                    line += "          "
            t001 += line + "\n"
        return t001

    def output_trf_info(self, tournament, trfkey):
        if trfkey == "012":
            info = "fullName"
        elif trfkey == "022":
            info = "site"
        elif trfkey == "032":
            info = "federation"
        txt = trfkey + " " + self.chessjson["event"]["eventInfo"][info] + "\n" if self.chessjson["event"].get("eventInfo", {}).get(info, "") != "" else ""
        txt = trfkey + " " + tournament["tournamentInfo"][info] + "\n" if tournament.get("tournamentInfo", {}).get(info, "") != "" else txt
        return(txt )

    def output_trf_datetime(self, tournament, trfkey):
        keyword = "startDate" if trfkey == "042" else "endDate"
        line = trfkey + " " + helpers.format_datetime(helpers.safe([tournament, self.chessjson["event"]], ["eventInfo", keyword], "")) + "\n"
        return line
        
    def output_trf_num_comp(self, tournament, trfkey):
        if trfkey == "062":
            line = "062 " + str(len(tournament["competitors"])) + "\n"
        elif trfkey == "072":
           line = trfkey + " " + str(len([c for c in tournament["competitors"] if "rating" in c and c["rating"].get("rating", 0) > 0])) + "\n"
        return line

    def output_trf_ttype(self, tournament, trfkey):
        line = "092 " + tournament["tournamentType"] + "\n"
        return line

    def output_trf_arbiter(self, tournament, trfkey):
        line = ""
        if trfkey == "102":
            profile = tournament.get("tournamentInfo", {}).get("arbiters", {}).get("chiefArbiter", 0) or \
                      self.chessjson["event"].get("eventInfo", {}).get("arbiters", {}).get("chiefArbiter", 0)
            if profile > 0:
                line = "102 " + helpers.format_name(self.profiles[profile]) + "\n"
        elif trfkey == "112":
            profiles = tournament.get("tournamentInfo", {}).get("arbiters", {}).get("arbiters", None) or \
                       self.chessjson["event"].get("eventInfo", {}).get("arbiters", {}).get("arbiters", [])
            arbiters = helpers.safe([tournament, self.chessjson["event"]], ["eventInfo", "arbiters", "arbiters"], [])
            for arbiter in arbiters:
                line += "112 " + helpers.format_name(self.profiles[arbiter]) + "\n"
        return line
            
    def output_trf_timecontrol(self, tournament, trfkey):
        line = ""
        if "timeControl" in tournament:
            line = "122 " + tournament["timeControl"]["description"] + "\n"
        return line
    
    def output_trf_dates(self, tournament, trfkey):
        line = "" 
        if "rounds" in tournament:
            line = "132 " +(" "*(85+10*tournament["numRounds"]))
            for round in tournament["rounds"]:
                start = round["startTime"]
                rno = round["roundNo"]
                seg = "  " + start[2:4] + "/" + start[5:7] + "/" + start[8:10]
                first =  79 + rno*10
                last = first + 10 
                line = line[:first] + seg + line[last:]
            line +=  "\n"            
        return line



    def output_trf_numrounds(self, tournament, trfkey):
        line = "142 " + str(tournament["numRounds"]) + "\n"
        return line

    def output_trf_topcolor(self, tournament, trfkey):
        line = "152 " + tournament["topColor"].upper() + "\n" if "topColor" in tournament else ""
        return line

    def output_trf_gamescore(self, tournament, trfkey):
        line = "162  W{0:4.1f}    D{1:4.1f}    L{2:4.1f}    A{3:4.1f}    P{4:4.1f}    X{5:4.1f}\n".format(
            self.scores.get_score(tournament, "game", "W"),
            self.scores.get_score(tournament, "game", "D"),
            self.scores.get_score(tournament, "game", "L"),
            self.scores.get_score(tournament, "game", "Z"),
            self.scores.get_score(tournament, "game", "P"),
            self.scores.get_score(tournament, "game", "A"),
        )
        return line


    def output_trf_accelerated(self, tournament, trfkey):
        t250 = ""
        if "accelerated" in tournament and "values" in tournament["accelerated"]:
            acc = tournament["accelerated"]["values"]
            for value in acc:
                match = self.scores.score.get("match", {}).get(value["matchResult"], 0.0)
                game = self.scores.score.get("game", {}).get(value["gameResult"], 0.0)
                line = "250 " + f"{match:>4.1f} " + f"{game:>4.1f} " + f"{value['firstRound']:>3} " + f"{value['lastRound']:>3} " + f"{value['firstCompetitor']:>4} " + f"{value['lastCompetitor']:>4}"
                t250 += line + "\n"
        return t250


    def output_trf_prohibited(self, tournament, trfkey):
        line = ""
        if "prohibited" in tournament:
            for elem in tournament["prohibited"]:
                line += f"260 {elem['firstRound']:3} {elem['lastRound']:3} " + " ".join([f"{c:4}" for c in elem["competitors"]]) + "\n"
        return line



# ============== Module test ================


def dotest(name, details):
    print("==== " + name + " ====")
    root = "..\\..\\..\\..\\Nordstrandsjakk\\Turneringsservice\\"

    with open(root + name + "\\" + name + details + ".txt") as f:
        lines = f.read()

    tournament = trf2json()
    tournament.parse_file(lines, True)
    with open(root + name + "\\" + name + details + ".json", "w") as f:
        json.dump(tournament.event, f, indent=2)


def module_test():
    # dotest('escc2018')
    # dotest('h2023')
    dotest("lyn23", "-Rating-A-Lyn-FIDE")
    dotest("ngpl23", "-A-Langsjakk-FIDE")
    dotest("ngpl23", "-B-Langsjakk-FIDE")
    dotest("ngpl23", "-C-Langsjakk-FIDE")
    dotest("elite19-20", "-FIDE")
    dotest("Team-Example", "-013")
    dotest("Team-Example", "-TSE")
    dotest("nm_lag_19", "-Langsjakk-FIDE")
    dotest("test-half-point", "-Langsjakk-FIDE")
    dotest("test-half-point2", "-Langsjakk-FIDE")


if __name__ == "__main__":
    tournament = trf2json()
    tournament.trfrecords[0]["read"](None, " ### TXT")
