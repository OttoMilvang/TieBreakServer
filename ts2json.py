# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 11:55:32 2023
@author: Otto Milvang, sjakk@milvang.no
"""
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 11:55:32 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import xml.etree.ElementTree as ET
from decimal import Decimal
import chessjson
import helpers
import scoresystem


class ts2json(chessjson.chessjson):
    def __init__(self):
        super().__init__()
        self.debug = False
        self.version = "ts2json ver. 1.00"
        self.pcompetitors = {}  # pointer to player section competitors
        self.bcompetitors = {}  # pointer to team competitors via 1st board player
        self.tcompetitors = {}  # pointer to team section competitors
        self.chessjson["event"]["ratingLists"] = [
            {"listName": "Local", "listDescription": "Local rating"},
            {"listName": "FIDE", "listDescription": "FIDE standard rating"},
            {"listName": "FIDErapid", "listDescription": "FIDE rapid rating"},
            {"listName": "FIDEblitz", "listDescription": "FIDE blitz rating"},
        ]
        self.translatetb = {
            "Points": "PTS",
            "ExpectedPoints": "ExpectedPoints",
            "Accellerated1": "Accellerated1",
            "Accellerated2": "Accellerated2",
            "StartNo": "StartNo",
            "Monrad": "Monrad",
            "Monrad-1low": "Monrad-1low",
            "Monrad-2low": "Monrad-2low",
            "Monrad-1low-1high": "Monrad-1low-1high",
            "Buchholz": "BH",
            "Buchholz-1low": "BH/C1",
            "Buchholz-2low": "BH/C2",
            "Buchholz-1low-1high": "BH/M1",
            "FB": "FB",
            "FB-1low": "FB/C1",
            "FB-2low": "FB/C2",
            "Berger": "SB",
            "Berger-1low": "SB/C1",
            "Berger-2low": "SB/C2",
            "MutualResult": "MutualResult",
            "DE": "DE",
            "MutualColor": "MutualColor",
            "FIDEtitle": "FIDEtitle",
            "FideRating": "FideRating",
            "LocalRating": "LocalRating",
            "SumProgressiveScore": "SumProgressiveScore",
            "SumProgressiveScore-1": "SumProgressiveScore-1",
            "SumProgressiveScore-2": "SumProgressiveScore-2",
            "AvgFideRatingOpponnent": "ARO",
            "AvgFideRatingOpponnent-1low": "ARO/C1",
            "AvgLocalRatingOpponnent": "AvgLocalRatingOpponnent",
            "AvgLocalRatingOpponnent-1low": "AvgLocalRatingOpponnent-1low",
            "FIDERatingPrestation": "FIDERatingPrestation",
            "LocalRatingPrestation": "LocalRatingPrestation",
            "Alphabetically": "Alphabetically",
            "PctScoreMin75": "PctScoreMin75",
            "Cup": "Cup",
            "NumWins": "WON",
            "NumBlackWins": "NumBlackWins",
            "NumBlacks": "NumBlacks",
            "PerfectTournamentPerformance": "PTP",
            "Koya": "KS",
            "Custom1": "Custom1",
            "Custom2": "Custom2",
            "GamePoints": "GPTS",
            "TeamPointsPlusGamePoints": "TeamPointsPlusGamePoints",
            "IndividualMonrad": "IndividualMonrad",
            "IndividualMonrad-1low": "IndividualMonrad-1low",
            "IndividualMonrad-2low": "IndividualMonrad-2low",
            "IndividualMonrad-2low-2high": "IndividualMonrad-2low-2high",
            "IndividualBerger": "IndividualBerger",
            "PctScoreLeague": "PctScoreLeague",
        }
        self.isteam = False

    # ==============================
    #
    # Read TS file
    def parse_file(self, lines, verbose=False):
        event = ET.fromstring(lines)
        if event.tag != "Tournament":
            return 1  # Not a TS file
        self.parse_ts_tournament_attrib(event.attrib)
        for child in event:
            if child.tag == "Web":
                self.parse_ts_web(child.attrib)
            elif child.tag == "Groups":
                for key, value in child.attrib.items():
                    if key == "Num":
                        pass
                    elif key == "SeparateFile":
                        pass
                tournamentno = 0
                for group in child:
                    if group.tag == "Group":
                        tournamentno += 1
                        self.pcompetitors = {}  # reset per group
                        self.bcompetitors = {}
                        self.tcompetitors = {}
                        tournament = self.parse_ts_group(group, tournamentno)
                        if self.isteam:
                            self.prepare_team_section(tournament)
                        else:
                            self.prepare_player_section(tournament)
                        self.update_results(tournament["gameList"])
                        self.update_tournament_rating(tournament)
                        self.update_tournament_teamcompetitors(tournament)
                        self.update_tournament_random(tournament, self.isteam)
                        self.add_accelerated(tournament)
        return

    def parse_ts_tournament_attrib(self, attrib):
        # Chief arbiter / deputy / organizer
        ca = {
            "id": -1,
            "fideId": 0,
            "firstName": "",
            "lastName": "",
            "fideName": "",
            "sex": "u",
            "federation": "",
            "fideOTitle": "",
        }
        da = {
            "id": -1,
            "fideId": 0,
            "firstName": "",
            "lastName": "",
            "fideName": "",
            "sex": "u",
            "federation": "",
            "fideOTitle": "",
        }
        org = {
            "id": -1,
            "fideId": 0,
            "firstName": "",
            "lastName": "",
            "fideName": "",
            "sex": "u",
            "federation": "",
            "fideOTitle": "",
        }
        event = self.chessjson["event"]
        other = event["eventInfo"]["other"] = {}
        for key, value in attrib.items():
            if key == "Dataversion":
                pass
            elif key == "Producer":
                event["origin"] = value
            elif key == "TeamEvent":
                self.isteam = other["teamEvent"] = value == "Y"
            elif key == "Event":
                event["eventName"] = value
                event["eventInfo"]["fullName"] = value
            elif key == "Organiser":
                self.parse_ts_arbiter(org, value)
            elif key == "Arbiter":
                self.parse_ts_arbiter(ca, value)
            elif key == "ArbiterFideId":
                if value != "":
                    ca["id"] = 1
                    ca["fideId"] = int(value)
            elif key == "ArbiterEmail":
                if value != "":
                    ca["id"] = 1
                    ca["email"] = value
            elif key == "DeputyArbiter":
                self.parse_ts_arbiter(da, value)
            elif key == "DeputyArbiterFideId":
                if value != "":
                    da["id"] = 1
                    da["fideId"] = int(value)
            elif key == "DeputyArbiterEmail":
                if value != "":
                    da["id"] = 1
                    da["email"] = value
            elif key == "Treasurer":
                pass
            elif key == "Site":
                event["eventInfo"]["site"] = value
            elif key == "Federation":
                event["eventInfo"]["federation"] = value
            elif key == "StartDate":
                event["eventInfo"]["startDate"] = helpers.parse_date(value)
            elif key == "EndDate":
                event["eventInfo"]["endDate"] = helpers.parse_date(value)
            elif key == "LogoFile":
                pass
            elif key == "MemberFile":
                pass
            elif key == "dflt_Available":
                pass
            elif key == "LichessVerify":
                pass
            elif key == "TStoken":
                pass
            elif key == "PaymentVipps":
                pass
            elif key == "PaymentOptional":
                pass
            elif key == "Name":
                pass
            elif key == "Phone":
                pass
            elif key == "OrgNo":
                pass
            else:
                self.print_warning("parse_ts_tournament_attrib: " + key + " not matched")

        if org["id"] == 0:
            if "organizers" not in event["eventInfo"]:
                event["eventInfo"]["organizers"] = {
                    "chiefOrganizer": self.append_profile(org),
                    "chiefSecretariat": 0,
                    "organizers": [],
                    "secretaries": [],
                }
        if ca["id"] == 0 or da["id"] == 0:
            if "arbiters" not in event["eventInfo"]:
                event["eventInfo"]["arbiters"] = {
                    "chiefArbiter": self.append_profile(ca),
                    "deputyChiefArbiters": [self.append_profile(da)],
                    "ratingOfficer": 0,
                    "arbiters": [],
                }
        return

    def parse_ts_web(self, attrib):
        event = self.chessjson["event"]
        other = event["eventInfo"]["other"]
        for key, value in attrib.items():
            if key == "HTMLFile":
                other["htmlFile"] = value
            elif key == "BaseURL":
                event["eventInfo"]["website"] = value
            elif key == "WebserverID":
                other["webserverId"] = value
            elif key == "WebPublishInterval":
                other["webPublishInterval"] = value
            elif key == "LastEnrollTime":
                other["lastEnrollTime"] = helpers.parse_date(value)
            elif key == "PublishEnrollPage":
                other["PublishEnrollPage"] = helpers.parse_int(value)
            elif key == "PublishSerial":
                other["PublishSerial"] = helpers.parse_int(value)
            elif key == "PublishRoundReports":
                other["PublishRoundReports"] = value == "Y"
            elif key == "PublishLivegames":
                other["PublishLivegames"] = value == "Y"
            elif key == "LiveGamesURL":
                other["LiveGamesURL"] = value
            elif key == "MaxNumEnrolled":
                other["MaxNumEnrolled"] = helpers.parse_int(value)
            elif key == "PublishPayedStatus":
                other["PublishPayedStatus"] = value
            elif key == "WebPublishConfidentiality":
                other["MaxNumEnrolled"] = helpers.parse_int(value)
            elif key == "ClonoToken":
                other["ClonoToken"] = value
            elif key == "ClonoT_id":
                other["ClonoT_id"] = helpers.parse_int(value)
            elif key == "ClonoPublishLevel":
                other["ClonoPublishLevel"] = helpers.parse_int(value)
            elif key == "ClonoCategory":
                other["ClonoCategory"] = helpers.parse_int(value)
            elif key == "ClonoT_uid":
                other["ClonoT_id"] = value
            elif key == "ClonoTokenDate":
                other["ClonoTokenDate"] = helpers.parse_date(value)
            elif key == "CheckinAllowed":
                other["CheckinAllowed"] = value
            else:
                self.print_warning("parse_ts_web: " + key + " not matched")
        return

    # ==============================
    #
    # Read tournament (group) in TS file
    #
    def parse_ts_group(self, group, tournamentno):
        self.scores = scoresystem.scoresystem()
        tournament = {
            "tournamentNo": tournamentno,
            "name": "",
            "tournamentType": "Tournament",
            "tournamentInfo": {},
            "ratingList": "Local",
            "numRounds": 0,
            "rounds": [],
            "currentRound": 0,
            "teamTournament": False,
            "rankOrder": ["PTS"],
            "competitors": [],
            "scoreSystem": self.scores.score,
            "gameList": [],
            "matchList": [],
            "other": {},
        }
        self.parse_ts_group_attrib(group.attrib, tournament)
        for child in group:
            if child.tag == "Rounds":
                self.parse_ts_group_rounds(child, tournament)
            elif child.tag == "TieBreaksBy":
                self.parse_ts_group_order(child, tournament, "TieBreaksBy")
            elif child.tag == "IndividualTieBreaksBy":
                self.parse_ts_group_order(child, tournament, "IndividualTieBreaksBy")
            elif child.tag == "PairingGroupBy":
                self.parse_ts_group_order(child, tournament, "PairingGroupBy")
            elif child.tag == "PrizeGroups":
                self.parse_ts_group_prize(child, tournamentno)
            elif child.tag == "ColWidths":
                self.parse_ts_group_layout(child, tournamentno)
            elif child.tag == "Reportsettings":
                self.parse_ts_group_report(child, tournamentno)
            elif child.tag == "Players":
                self.parse_ts_group_players(child, tournament)
            elif child.tag == "Teams":
                tournament["teamTournament"] = True
                self.parse_ts_group_teams(child, tournament)
            else:
                self.print_warning("parse_ts_group tag: " + child.tag + " not matched")

        self.scores.fill_default_scoresystem("game")
        if tournament["teamTournament"]:
            self.scores.fill_default_scoresystem("match")
        self.chessjson["event"]["tournaments"].append(tournament)
        return tournament

    def parse_ts_group_attrib(self, attrib, tournament):
        ca = {
            "id": -1,
            "fideId": 0,
            "firstName": "",
            "lastName": "",
            "fideName": "",
            "sex": "u",
            "federation": "",
            "fideOTitle": "",
        }
        da = {
            "id": -1,
            "fideId": 0,
            "firstName": "",
            "lastName": "",
            "fideName": "",
            "sex": "u",
            "federation": "",
            "fideOTitle": "",
        }
        scoresystem_map = self.scores.score
        info = tournament["tournamentInfo"]
        other = tournament["other"]
        for key, value in attrib.items():
            if key == "Event":
                tournament["name"] = value
            elif key == "Site":
                info["site"] = value
            elif key == "Arbiter":
                self.parse_ts_arbiter(ca, value)
            elif key == "DeputyArbiter":
                self.parse_ts_arbiter(da, value)
            elif key == "StartDate":
                info["startDate"] = helpers.parse_date(value)
            elif key == "EndDate":
                info["endDate"] = helpers.parse_date(value)
            elif key == "ActiveRound":
                tournament["currentRound"] = helpers.parse_int(value)
            elif key == "NumRounds":
                tournament["numRounds"] = helpers.parse_int(value)
            elif key == "LocalRatingCategory":
                other["localRatingCategory"] = helpers.parse_int(value)
            elif key == "RatingFactorA":
                other["ratingFactorA"] = helpers.parse_float(value)
            elif key == "RatingFactorB":
                other["ratingFactorB"] = helpers.parse_float(value)
            elif key == "RatingFactorC":
                other["ratingFactorC"] = helpers.parse_float(value)
            elif key == "MaxMeets":
                tournament["maxMeet"] = helpers.parse_int(value)
            elif key == "PairingAccellerated":
                if value == "Y":
                    tournament["accelerated"] = { "name" : "BAKU2016", "values": []}
            elif key == "AccelleratedLastGaSn":
                if "accelerated" in tournament:
                    tournament["accelerated"]["bakuGa"] = helpers.parse_int(value)
            elif key == "Pairing":
                tournament["tournamentType"] = value
            elif key == "FirstRatedRound":
                pass
            elif key == "PointsForWin":
                if value.find(".") < 0:
                    value += ".0"
                scoresystem_map["game"]["W"] = helpers.parse_float(value)
            elif key == "PointsForLoss":
                if value.find(".") < 0:
                    value += ".0"
                scoresystem_map["game"]["L"] = helpers.parse_float(value)
            elif key == "PointsForBye":
                if value == "d":
                    scoresystem_map["game"]["P"] = "D"
                if value == "+":
                    scoresystem_map["game"]["P"] = "W"
            elif key == "PostponedCalcAs":
                if value == "d" or value == "=": 
                    scoresystem_map["game"]["A"] = "D"
                if value == "+":
                    scoresystem_map["game"]["A"] = "W"
            elif key == "RankPerClass":
                pass
            elif key == "ShowRankNum":
                pass
            elif key == "Tie-breakOnStartno":
                pass
            elif key == "ActiveElo":
                tournament["ratingList"] = value
            elif key == "ShowAllTiebreaks":
                pass
            elif key == "SubmissionIndex":
                pass
            elif key == "EventCode":
                pass
            elif key == "YouthEvent":
                pass
            elif key == "NumTiebreakGames":
                pass
            elif key == "SrchLocalLists":
                pass
            elif key == "SrchFideLists":
                pass
            elif key == "ClonoRd":
                pass
            elif key == "ReportedRounds":
                pass
            elif key == "LastBulkPairing":
                pass
            elif key == "JuniorFee":
                pass
            elif key == "SeniorFee":
                pass
            elif key == "NumBoards":
                tournament["teamSize"] = helpers.parse_int(value)
            elif key == "HomeGuestNaming":
                pass
            elif key == "Clr":
                pass
            else:
                self.print_warning("parse_ts_group attrib: " + key + "=" + value + " not matched")

        if scoresystem_map["game"]["W"] == Decimal("1.0"):
            scoresystem_map["game"]["D"] = Decimal("0.5")
        elif scoresystem_map["game"]["W"] == Decimal("3.0") and scoresystem_map["game"]["L"] == Decimal("1.0"):
            scoresystem_map["game"]["D"] = Decimal("2.0")
        elif scoresystem_map["game"]["W"] == Decimal("3.0") and scoresystem_map["game"]["L"] == Decimal("0.0"):
            scoresystem_map["game"]["D"] = Decimal("1.0")
        scoresystem_map["game"]["Z"] = Decimal("0.0")
        scoresystem_map["game"]["F"] = "W"
        scoresystem_map["game"]["H"] = "D"
        scoresystem_map["game"]["U"] = "Z"

        if ca["id"] == 0 or da["id"] == 0:
            if "arbiters" not in info:
                info["arbiters"] = {
                    "chiefArbiter": self.append_profile(ca),
                    "deputyChiefArbiters": [self.append_profile(da)],
                    "ratingOfficer": 0,
                    "arbiters": [],
                }
        return

    def parse_ts_group_rounds(self, rounds, tournament):
        for key, value in rounds.items():
            self.print_warning("parse_group_rounds attrib: " + key + " not matched")
        roundno = 0
        for child in rounds:
            roundno += 1
            cround = {"roundNo": roundno, "timeControl": {"defaultTime": 0, "periods": []}}
            clast = {"moves": 0}
            periodno = 0
            if child.tag == "Rd":
                for key, value in child.attrib.items():
                    if key == "StartDate":
                        cround["startTime"] = helpers.parse_date(value)
                    elif key == "IsRated":
                        cround["rated"] = value == "Y"
                    elif key == "ActiveElo":
                        cround["ratingList"] = value
                    elif key == "TimeFirstMove":
                        cround["timeControl"]["defaultTime"] = helpers.parse_minutes(value)
                    elif key == "AdditionPerMove":
                        increment = clast["increment"] = helpers.parse_seconds(value)
                    elif key == "TimeFinish":
                        clast["baseTime"] = helpers.parse_minutes(value)
                    elif key == "PointsForWin":
                        pass  # Ignore
                    elif key == "PointsForLoss":
                        pass  # Ignore
                    else:
                        self.print_warning("parse_ts_group_rounds: " + key + " not matched")
                for tc in child:
                    if tc.tag == "TimeControls":
                        periodno = self.parse_ts_group_timecontrol(tc, cround["timeControl"]["periods"], increment)
                    else:
                        self.print_warning("parse_group_timecontrol tag: " + tc.tag + " not matched")
                clast["period"] = periodno + 1
                cround["timeControl"]["periods"].append(clast)
                tournament["rounds"].append(cround)
        return

    def parse_ts_group_timecontrol(self, tc, periods, increment):
        for key, value in tc.attrib.items():
            self.print_warning("parse_group_timecontrol attrib: " + key + " not matched")
        periodno = 0
        for child in tc:
            periodno += 1
            period = {"period": periodno, "increment": increment}
            if child.tag == "phase":
                for key, value in child.attrib.items():
                    if key == "moves":
                        period["moves"] = helpers.parse_int(value)
                    elif key == "Time":
                        period["baseTime"] = helpers.parse_minutes(value)
                    else:
                        self.print_warning("parse_ts_group_timecontrol: " + key + " not matched")
                periods.append(period)
            else:
                self.print_warning("parse_group_timecontrol tag: " + child.tag + " not matched")
        return periodno

    def parse_ts_group_order(self, rank, tournament, ordertype):
        if ordertype == "TieBreaksBy":
            tournament["rankOrder"] = []
        for key, value in rank.items():
            if key == "NumOrdersInPgroup":
                pass
            else:
                self.print_warning("parse_group_order attrib: " + key + " not matched")
        for order in rank:
            if order.tag != "Order":
                self.print_warning("parse_group_order attrib, tag: " + order.tag + " not matched")
            tb = {}
            for key, value in order.items():
                tb[key] = value
            if "Name" in tb and tb["Name"] in self.translatetb:
                name = self.translatetb[tb["Name"]]
            else:
                self.print_warning("parse_group_order attrib, attrib: " + (list(tb.keys())[-1] if tb else "") + " not matched")
                name = "NOOP"
            if "IncludeForfeits" in tb and tb["IncludeForfeits"] == "Y":
                name += "/P"
            if "Limit" in tb:
                name += "/L"
                if helpers.parse_int(tb["Limit"]) >= 0:
                    name += "+"
                name += tb["Limit"]
            if "Factor" in tb:
                name += "/K" + tb["Factor"]
            if "Fore" in tb and tb["Fore"] == "Y":
                name += "/F"
            if ordertype == "TieBreaksBy":
                tournament["rankOrder"].append(name)
        return

    def parse_ts_group_prize(self, attrib, tournamentno):
        return

    def parse_ts_group_layout(self, attrib, tournamentno):
        return

    def parse_ts_group_report(self, attrib, tournamentno):
        return

    def parse_ts_group_players(self, players, tournament):
        for key, value in players.attrib.items():
            if key == "Num":
                pass
            elif key == "SeparateFile":
                pass
            else:
                self.print_warning("parse_ts_group_players attrib: " + key + "=" + value + " not matched")
        rank = 0
        for player in players:
            if player.tag == "Player":
                rank += 1
                self.parse_ts_player(player, tournament, rank)
        return

    def parse_ts_group_teams(self, teams, tournament):
        for key, value in teams.attrib.items():
            if key == "SeparateFile":
                pass
            else:
                self.print_warning("parse_ts_group_teams attrib: " + key + "=" + value + " not matched")
        rank = 0
        for team in teams:
            if team.tag == "Team":
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
        ratinglist = tournament["ratingList"]
        for tround in tournament["rounds"]:
            if (
                tround["roundNo"] <= tournament["currentRound"]
                and tround["roundNo"] > roundno
                and tround.get("ratingList", "Undefined") != "Undefined"
            ):
                roundno = tround["roundNo"]
                cround = tround
        if cround is not None:
            ratinglist = cround["ratingList"]
        ratinglists = self.chessjson["event"]["ratingLists"]
        ratingindex = 0
        for nlist in range(0, len(ratinglists)):
            if ratinglist == ratinglists[nlist]["listName"]:
                ratingindex = nlist
                break
        pids = self.all_pids()
        for key, player in self.pcompetitors.items():
            player["rating"] = int(pids[player["profileId"]]["rating"][ratingindex])

    def update_tournament_teamcompetitors(self, tournament):
        if not tournament["teamTournament"]:
            return
        [cplayers, cteam] = self.build_tournament_teamcompetitors(tournament)
        competitors = tournament["competitors"]
        allgames = self.build_all_games(tournament, cteam, False)
        pscore = tournament["gameScoreSystem"]
        tscore = tournament["matchScoreSystem"]
        for competitor in competitors:
            competitor["matchPoints"] = 0
            competitor["gamePoints"] = 0
        for game in tournament["matchList"]:
            rnd = game["round"]
            gpoints = {}
            played = False
            for col in ["white", "black"]:
                if col in game and game[col] > 0:
                    teamno = game[col]
                    teamres = allgames[rnd][teamno]
                    tsum = 0
                    for igame in teamres:
                        if teamno == cteam[igame["white"]]:
                            tsum += self.get_score(pscore, igame, "white")
                            played = played or igame["played"]
                        if "black" in igame and igame["black"] > 0 and teamno == cteam[igame["black"]]:
                            tsum += self.get_score(pscore, igame, "black")
                            played = played or igame["played"]
                    gpoints[col] = tsum
            game["played"] = played
            if "black" in gpoints:
                if gpoints["white"] > gpoints["black"]:
                    game["wResult"] = "W"
                    game["bResult"] = "L" if played else "Z"
                elif gpoints["white"] < gpoints["black"]:
                    game["bResult"] = "W"
                    game["wResult"] = "L" if played else "Z"
                else:
                    game["wResult"] = "D"
                    game["bResult"] = "D"
                competitors[game["black"] - 1]["gamePoints"] += gpoints["black"]
                competitors[game["black"] - 1]["matchPoints"] += self.get_score(tscore, game, "black")
                competitors[game["white"] - 1]["gamePoints"] += gpoints["white"]
                competitors[game["white"] - 1]["matchPoints"] += self.get_score(tscore, game, "white")
        return

    # ==============================
    #
    # Read tournament player in TS file
    #
    def parse_ts_player(self, player, tournament, rank):
        profile = {"id": 0, "rating": [0, 0, 0, 0], "kFactor": [0, 0, 0, 0], "other": {}}
        competitor = {"cid": 0}
        self.parse_ts_player_attrib(player.attrib, profile, competitor)
        profileid = competitor["profileId"] = self.append_profile(profile)
        if competitor.get("teamName", "") != "":
            competitor["teamId"] = self.append_team(competitor["teamName"], profileid)
        elif "rank" not in competitor or competitor.get("rank", 0) == 0:
            competitor["rank"] = rank
        results = player[0]
        playerno = competitor["cid"] if "cid" in competitor else 0
        if playerno == 0:
            playerno = len(self.pcompetitors) + 1
        self.pcompetitors[playerno] = competitor
        for game in results:
            if game.tag == "Game":
                self.parse_ts_game(game, tournament["gameList"], playerno, False)
            else:
                self.print_warning("parse_ts player, result key: " + game.tag + " not matched")
        return

    def parse_ts_player_attrib(self, attrib, profile, competitor):
        for key, value in attrib.items():
            if key == "StartNo":
                competitor["cid"] = helpers.parse_int(value)
            elif key == "Available":
                competitor["present"] = value == "Y"
            elif key == "Teamname":
                competitor["teamName"] = value
            elif key == "Group":
                profile["other"]["group"] = value
            elif key == "Federation":
                profile["federation"] = value
            elif key == "Pts":
                competitor["gamePoints"] = helpers.parse_float(value)
            elif key == "Rank":
                trank = helpers.parse_int(value)
                if trank > 0:
                    competitor["rank"] = trank
            elif key == "Pmt":
                profile["other"]["pmt"] = value
            elif key == "Rcpt":
                pass
            elif key == "EnrSt":
                pass
            elif key == "EnrollDate":
                competitor["enrolled"] = helpers.parse_date(value)
            elif key == "Custom1":
                pass
            elif key == "Custom2":
                pass
            elif key == "Info":
                profile["other"]["info"] = value
            elif key == "Title":
                profile["fideTitle"] = value
            elif key == "Gn":
                profile["firstName"] = value
            elif key == "Ln":
                profile["lastName"] = value
            elif key == "Table":
                pass
            elif key == "GPgroup":
                pass
            elif key == "Born":
                birth = helpers.parse_date(value)
                profile["birth"] = birth if (len(birth) > 2 and birth[0:2] != "18") else ""
            elif key == "Club":
                profile["clubName"] = value
            elif key == "LocalID":
                profile["localId"] = helpers.parse_int(value)
            elif key == "LocalRating":
                profile["rating"][0] = helpers.parse_int(value)
            elif key == "LocalGames":
                pass
            elif key == "FideId":
                profile["fideId"] = helpers.parse_int(value)
            elif key == "FideRating":
                profile["rating"][1] = helpers.parse_int(value)
            elif key == "FideRapidRating":
                profile["rating"][2] = helpers.parse_int(value)
            elif key == "FideBlitzRating":
                profile["rating"][3] = helpers.parse_int(value)
            elif key == "FideGames":
                pass
            elif key == "FideRapidGames":
                pass
            elif key == "FideBlitzGames":
                pass
            elif key == "RatingFactor":
                profile["kFactor"][1] = helpers.parse_float(value)
            elif key == "RapidRatingFactor":
                profile["kFactor"][2] = helpers.parse_float(value)
            elif key == "BlitzRatingFactor":
                profile["kFactor"][3] = helpers.parse_float(value)
            elif key == "BornYear":
                profile["yearBirth"] = helpers.parse_int(value)
            elif key == "MemberAsOf":
                pass
            elif key == "sex":
                profile["sex"] = (value + " ")[0:1]
            elif key == "Phone":
                profile["phone"] = value
            elif key == "Email":
                profile["email"] = value
            else:
                self.print_warning("parse_ts_player attrib: " + key + " not matched")
        return

    def parse_ts_game(self, game, cresults, playerno, isteam):
        result = {"id": 0, "isTeam": isteam}
        myclr = "W"
        opponent = 0
        res = "?"
        for key, value in game.attrib.items():
            if key == "Rd":
                result["round"] = helpers.parse_int(value)
            elif key == "Clr":
                myclr = value
            elif key == "Opnt":
                opponent = helpers.parse_int(value)
            elif key == "Res":
                res = value
            elif key == "Table":
                result["board"] = helpers.parse_int(value)
            elif key == "PublishSerial":
                pass
            elif key == "Flt":
                pass
            elif key == "PGNdata":
                pass
            else:
                self.print_warning("parse_ts_game attrib: " + key + " not matched")

        score = self.parse_result(res, opponent, isteam)
        if myclr == "B":
            result["white"] = max(0, opponent)
            result["black"] = playerno
            result["bResult"] = score
        else:
            result["white"] = playerno
            result["black"] = max(0, opponent)
            result["wResult"] = score
        result["played"] = ((res == "1" or res == "=" or res == "0" or res == "A") and opponent > 0) or (opponent == -1)
        if score != "U":
            self.append_result(cresults, result)
        return

    def parse_result(self, result, opponent, isteam):
        # if opponent == -1:
        #     if isteam == self.isteam:
        #         return 'P'
        if result in ("1", "+"):
            return "W"
        elif result in ("=", "d"):
            return "D"
        elif result == "0":
            return "L"
        elif result == "-":
            return "Z"
        elif result == "A":
            return "A"
        elif result == "?":
            return "U" if opponent == 0 else "A"
        return "U"

    # ==============================
    #
    # Read tournament team in TS file
    #
    def parse_ts_team(self, team, tournament, rank):
        teamProfile = {"id": 0, "other": {}}
        competitor = {"cid": 0, "rank": rank, "cplayers": []}
        self.parse_ts_team_attrib(team.attrib, teamProfile, competitor)
        tournament["competitors"].append(competitor)
        self.tcompetitors[teamProfile["teamName"]] = competitor
        results = team[0]
        for game in results:
            if game.tag == "Game":
                teamno = competitor["cid"]
                self.parse_ts_game(game, tournament["matchList"], teamno, True)
            else:
                self.print_warning("parse_ts team, result key: " + game.tag + " not matched")
        return

    def parse_ts_team_attrib(self, attrib, teamProfile, competitor):
        for key, value in attrib.items():
            if key == "StartNo":
                competitor["cid"] = helpers.parse_int(value)
            elif key == "Available":
                teamProfile["present"] = value == "Y"
            elif key == "Teamname":
                teamProfile["teamName"] = value
            elif key == "Group":
                pass
            elif key == "Federation":
                teamProfile["federation"] = value
            elif key == "Pts":
                competitor["matchPoints"] = helpers.parse_float(value)
            elif key == "Rank":
                trank = helpers.parse_int(value)
                if trank > 0:
                    competitor["rank"] = trank
            elif key == "Pmt":
                pass
            elif key == "Rcpt":
                pass
            elif key == "EnrSt":
                pass
            elif key == "EnrollDate":
                pass
            elif key == "Custom1":
                pass
            elif key == "Custom2":
                pass
            elif key == "Info":
                teamProfile["other"]["info"] = value
            elif key == "TeamLeader":
                captain = {
                    "id": -1,
                    "fideId": 0,
                    "firstName": "",
                    "lastName": "",
                    "fideName": "",
                    "sex": "u",
                    "federation": "",
                    "fideOTitle": "",
                }
                if value != "":
                    self.parse_ts_arbiter(captain, value)
                teamProfile["captain"] = self.append_profile(captain)
            else:
                self.print_warning("parse_ts_team attrib: " + key + " not matched")
        return

    # ==============================
    #
    # Converters
    #
    def parse_ts_arbiter(self, arbiter, name):
        line = name.rstrip()
        if line[0:3] == "IA " or line[0:3] == "FA ":
            arbiter["fideOTitle"] = line[0:2]
            arbiter["arbiter"] = line[0:2]
            line = line[3:]
        nameparts = line.split(",", 1)
        if len(nameparts) > 1:
            arbiter["lastName"] = nameparts[0].strip()
            arbiter["firstName"] = nameparts[1].strip()
        else:
            nameparts = line.split(" ")
            arbiter["lastName"] = nameparts[-1:]
            arbiter["firstName"] = " ".join(nameparts[0:-1])
        arbiter["id"] = 0
        return

    def prepare_player_section(self, tournament):
        tournament["competitors"] = sorted(list(self.pcompetitors.values()), key=lambda g: (g["cid"]))

    def prepare_team_section(self, tournament):
        for key, competitor in self.pcompetitors.items():
            self.tcompetitors[competitor["teamName"]]["cplayers"].append(competitor)
            competitor.pop("teamName", None)

    def add_accelerated(self, tournament):
        if tournament.get("accelerated", {}).get("name", "") == "BAKU2016":
            acc = tournament["accelerated"]
            bakuga = acc["bakuGa"]
            numrounds = tournament["numRounds"]
            accDrounds = (numrounds + 1)//2
            accWrounds = (accDrounds + 1)//2
            for (res, start, stop) in [("W", 1, accWrounds), ("D", accWrounds+1, accDrounds)]:
                value = {
                    "matchResult": res,
                    "gameResult": res,
                    "firstRound": start,
                    "lastRound": stop,
                    "firstCompetitor": 1,
                    "lastCompetitor": bakuga,
                }
                tournament["accelerated"]["values"].append(value)

    

# ============ Module test ==============
def dotest(name):
    print("==== " + name + " ====")
    root = "..\\..\\..\\..\\Nordstrandsjakk\\Turneringsservice\\"
    with open(root + name + "\\" + name + ".trx") as f:
        lines = f.read()
    tournament = ts2json()
    tournament.parse_file(lines)
    helpers.json_output(root + name + "\\" + name + ".jch", tournament.chessjson["event"])


def module_test():
    dotest("escc2018")
    dotest("h2023")
    dotest("hur22")
    dotest("ngpl23")
    dotest("elite19-20")
    dotest("nm_lag_19")
    dotest("nm_lag2022")
    dotest("test-half-point")
 
    
if __name__ == "__main__":
    module_test()
     
    