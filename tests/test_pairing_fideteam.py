# -*- coding: utf-8 -*-
"""
FIDE C.04.6, the Swiss Team Pairing System.

There is no second implementation of C.04.6 to check this one against - bbpPairings does
not pair team tournaments, and no other engine implements the regulation - so these tests
are the evidence that the engine follows it. Every one of them names the article it holds
the engine to, and constructs a position in which that article, and no other, decides.

The tournaments are built by hand, in the structure the readers produce: a team
competitor holds its players, a match holds its games, and a game holds the two players
and the board. The colour of a team in a match is the colour of the player on its first
board (art. 1.6.1), which is what "white" and "black" mean in a match record.
"""
import copy
import decimal

import pytest

from gacrux.crosstablefideteam import crosstable_fideteam
from gacrux.drawresult import drawresult
from gacrux.gacruxexeptions import GacruxNoLegalPairing
from gacrux.pairingfideteam import pairing_fideteam

WIN = decimal.Decimal("1.0")
DRAW = decimal.Decimal("0.5")
LOSS = decimal.Decimal("0.0")

GAMESCORE = {"W": WIN, "D": DRAW, "L": LOSS, "F": "W", "H": "D", "Z": LOSS, "P": "W", "A": "D", "U": "Z"}
MATCHSCORE = {
    "W": decimal.Decimal("2.0"),
    "D": decimal.Decimal("1.0"),
    "L": decimal.Decimal("0.0"),
    "F": "W",
    "H": "D",
    "Z": decimal.Decimal("0.0"),
    "P": "D",       # art. 1.4 - the bye is worth the match points of a draw
    "A": "D",
    "U": "Z",
    "FG": "W*",
    "HG": "D*",
    "ZG": "Z*",
    "PG": "D*",     # art. 1.4 - and the game points of a draw
}

REVERSE = {"W": "L", "D": "D", "L": "W"}


class event:
    """A team tournament, built round by round."""

    def __init__(self, numteams, numrounds, teamsize=2, typeb=False, primary=None, secondary=None, nocolor=False):
        pairingsystem = ["fideteam"] + (["typeb"] if typeb else []) + (["nocolor"] if nocolor else [])
        scoresystem = {"game": dict(GAMESCORE), "match": dict(MATCHSCORE)}
        if primary is not None:
            scoresystem["primary"] = primary
        if secondary is not None:
            scoresystem["secondary"] = secondary
        self.numteams = numteams
        self.teamsize = teamsize
        self.gameid = 0
        self.tournament = {
            "tournamentNo": 1,
            "tournamentType": "Team-Swiss",
            "numRounds": numrounds,
            "currentRound": 0,
            "teamTournament": True,
            "teamSize": teamsize,
            "topColor": "w",
            "pairingSystem": pairingsystem,
            "rankOrder": ["PTS"],
            "scoreSystem": scoresystem,
            "competitors": [],
            "gameList": [],
            "matchList": [],
        }
        for team in range(1, numteams + 1):
            self.tournament["competitors"].append(
                {
                    "cid": team,
                    "rank": team,
                    "teamId": team,
                    "present": True,
                    "rating": 2400 - 10 * team,
                    "random": team,
                    "cplayers": [
                        {"cid": self.player(team, board), "teamId": team, "rating": 2400 - 10 * team - board}
                        for board in range(1, teamsize + 1)
                    ],
                }
            )

    def player(self, team, board):
        return 100 * team + board

    def points(self, result):
        return GAMESCORE[result]

    def match(self, rnd, white, black, results):
        """A played match. results are the results of the boards, seen from the white team."""
        games = []
        wpoints = decimal.Decimal("0.0")
        for board, result in enumerate(results, start=1):
            self.gameid += 1
            wpoints += self.points(result)
            (first, second) = (white, black) if board % 2 == 1 else (black, white)
            (fres, sres) = (result, REVERSE[result]) if board % 2 == 1 else (REVERSE[result], result)
            game = {
                "id": self.gameid,
                "round": rnd,
                "board": board,
                "white": self.player(first, board),
                "black": self.player(second, board),
                "played": True,
                "rated": True,
                "wResult": fres,
                "bResult": sres,
            }
            self.tournament["gameList"].append(game)
            games.append(game["id"])
        bpoints = self.teamsize * WIN - wpoints
        wresult = "W" if wpoints > bpoints else ("D" if wpoints == bpoints else "L")
        self.tournament["matchList"].append(
            {
                "id": 1000 + len(self.tournament["matchList"]),
                "round": rnd,
                "white": white,
                "black": black,
                "played": True,
                "wResult": wresult,
                "bResult": REVERSE[wresult],
                "games": games,
            }
        )

    def pab(self, rnd, team):
        """art. 1.4 - the pairing-allocated-bye: no opponent, no colour."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": team, "black": 0,
             "played": True, "wResult": "P", "games": []}
        )

    def fullpointbye(self, rnd, team):
        """The FIDE-deprecated full-point bye: a win without playing and without opponent."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": team, "black": 0,
             "played": False, "wResult": "W", "games": []}
        )

    def halfpointbye(self, rnd, team):
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": team, "black": 0,
             "played": False, "wResult": "D", "games": []}
        )

    def forfeit(self, rnd, winner, loser):
        """A match won by forfeit: it was not played, so it gives no colour (art. 1.6.1)."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": winner, "black": loser,
             "played": False, "wResult": "W", "bResult": "Z", "games": []}
        )

    def engine(self, rnd, **params):
        allparams = {"experimental": [], "verbose": 0}
        allparams.update(params)
        return pairing_fideteam(copy.deepcopy(self.tournament), rnd, allparams)

    def pair(self, rnd, **params):
        """Pair a round. Returns the pairs, board by board, as (white team, black team)."""
        engine = self.engine(rnd, **params)
        roundpairing = engine.compute_pairing(False)
        pairs = [pair for bracket in roundpairing for pair in bracket["pairs"]]
        return [(pair["w"], pair["b"]) for pair in sorted(pairs, key=lambda pair: pair["board"])]

    def brackets(self, rnd, **params):
        engine = self.engine(rnd, **params)
        return (engine, engine.compute_pairing(False))

    def colorrules(self, rnd, **params):
        engine = self.engine(rnd, **params)
        roundpairing = engine.compute_pairing(False)
        return {
            (pair["w"], pair["b"]): pair["colorrule"]
            for bracket in roundpairing
            for pair in bracket["pairs"]
        }


def quality(brackets, scorelevel, name):
    for bracket in brackets:
        if bracket["scorelevel"] == scorelevel and not bracket.get("pab", False):
            return bracket["quality"][name]
    return None


def upfloaters(brackets, scorelevel):
    for bracket in brackets:
        if bracket["scorelevel"] == scorelevel and not bracket.get("pab", False):
            return sorted(bracket["upfloaters"])
    return []


def bye(pairs):
    for (w, b) in pairs:
        if b == 0:
            return w
    return None


# ---------------------------------------------------------------------------
# Art. 1.7 - colour preference
# ---------------------------------------------------------------------------

def preference(cod, csq, typeb=False, rnd=3, numrounds=9):
    crosstable = crosstable_fideteam({}, False, 0, typeb, True)
    crosstable.rnd = rnd
    crosstable.numrounds = numrounds
    return crosstable.color_preference(cod, csq)


# (colour difference, colour sequence) -> the type A preference of art. 1.7.1 and the
# type B preference of art. 1.7.2. "w2"/"b2" is a simple (A) or strong (B) preference,
# "w1"/"b1" is a mild (B) preference, "nc" is none.
COLOUR_TRUTH_TABLE = [
    #  cd   played colours    type A   type B
    (   0,  "",                "nc",   "nc"),   # 1.7.2 - a team that has yet to play
    (  +1,  "w",               "nc",   "b1"),
    (  -1,  "b",               "nc",   "w1"),
    (   0,  "wb",              "nc",   "w1"),   # 1.7.2 - Black in the last played match
    (   0,  "bw",              "nc",   "b1"),   # 1.7.2 - White in the last played match
    (  +2,  "ww",              "b2",   "b2"),   # cd > +1
    (  -2,  "bb",              "w2",   "w2"),   # cd < -1
    (  +1,  "wbw",             "nc",   "b1"),   # cd +1, last two are not both White
    (  -1,  "bwb",             "nc",   "w1"),
    (   0,  "bwwb",            "nc",   "w1"),
    (  +1,  "bwww",            "b2",   "b2"),   # cd +1 and the last two are White
    (  -1,  "wbbb",            "w2",   "w2"),   # cd -1 and the last two are Black
    (   0,  "wbww",            "b2",   "b2"),   # cd 0 and the last two are White
    (   0,  "bwbb",            "w2",   "w2"),   # cd 0 and the last two are Black
    (  +3,  "wwbww",           "b2",   "b2"),
    (  -3,  "bbwbb",           "w2",   "w2"),
    (  +2,  "wbwww",           "b2",   "b2"),
    (  -2,  "bwbbb",           "w2",   "w2"),
    (  +3,  "wwwbw",           "b2",   "b2"),   # cd > +1 - the last two do not matter
    (  -3,  "bbbwb",           "w2",   "w2"),
    (  +1,  "wwwbb",           "nc",   "b1"),   # the divergence: see the test below
    (  -1,  "bbbww",           "nc",   "w1"),
]


@pytest.mark.parametrize("cod,csq,typea,typeb", COLOUR_TRUTH_TABLE)
def test_art_1_7_1_type_a_colour_preference(cod, csq, typea, typeb):
    """Art. 1.7.1 - the simple (type A) colour preference, and its strength."""
    assert preference(cod, csq, typeb=False) == typea


@pytest.mark.parametrize("cod,csq,typea,typeb", COLOUR_TRUTH_TABLE)
def test_art_1_7_2_type_b_colour_preference(cod, csq, typea, typeb):
    """Art. 1.7.2 - the strong and mild (type B) colour preferences, and their strength."""
    assert preference(cod, csq, typeb=True) == typeb


def test_art_1_7_colour_difference_plus_one_after_two_blacks():
    """Art. 1.7.1 and 1.7.2 - the case the team system was written for.

    A team whose played colours are W,W,W,B,B has a colour difference of +1 and had Black
    in its last two played matches.

    C.04.3 art. 1.7.1 would give this player an ABSOLUTE preference for White ("the
    preference is for White ... when the last two games were played with Black"), which
    under C.04.3 art. 2.1.3 [C3] would even keep two such players apart.

    C.04.6 says something else, and in the other direction. Art. 1.7.1: the White clause
    needs a colour difference of 0 or -1, so a team on +1 gets no simple preference at
    all, and none of the other clauses fires either - no type A preference. Art. 1.7.2:
    the strong clauses are worded exactly as the simple ones and fire no more than they
    do, and the mild clause "for Black if its CD is +1" does - a MILD preference for
    BLACK, the colour C.04.3 would have refused it.
    """
    assert preference(+1, "wwwbb", typeb=False) == "nc"
    assert preference(+1, "wwwbb", typeb=True) == "b1"


def test_art_1_7_2_no_mild_preference_on_zero_in_the_last_round():
    """Art. 1.7.2 - "no preference ... when its CD is zero when pairing for the last round"."""
    assert preference(0, "wb", typeb=True, rnd=8, numrounds=9) == "w1"
    assert preference(0, "wb", typeb=True, rnd=9, numrounds=9) == "nc"
    # but a colour difference of +/-1 is a mild preference in the last round as well:
    # art. 1.7.2 attaches "and it is not the last round" to the CD-zero clause only.
    assert preference(+1, "wbw", typeb=True, rnd=9, numrounds=9) == "b1"


def test_art_1_7_no_colour_preferences_at_all():
    """Art. 1.7 - "or colour preferences are not to be used at all"."""
    assert preference(+2, "ww", typeb=False) == "b2"
    crosstable = crosstable_fideteam({}, False, 0, False, False)
    crosstable.rnd = 3
    crosstable.numrounds = 9
    assert crosstable.color_preference(+2, "ww") == "nc"


def test_art_1_6_1_a_match_that_was_not_played_gives_no_colour():
    """Art. 1.6.1 - a team has a colour in a match only if the match was actually played.

    Team 1 wins round 1 by forfeit as the white team, and plays round 2 with White. Only
    the second one counts, so its colour difference is +1 and its colour sequence is "w" -
    not +2 and "ww", which would be a preference for Black under both types.
    """
    tournament = event(6, 5, typeb=True)
    tournament.forfeit(1, 1, 2)
    tournament.match(1, 3, 4, ["W", "D"])
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(2, 1, 3, ["D", "D"])
    tournament.match(2, 5, 2, ["W", "W"])
    tournament.match(2, 6, 4, ["D", "D"])
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    team1 = engine.competitors[1]
    assert team1["cod"] == 1
    assert team1["csq"].strip() == "w"
    assert team1["cop"] == "b1"          # mild Black, not the strong "b2" of two Whites


# ---------------------------------------------------------------------------
# The Preface - a colour never prevents a pairing
# ---------------------------------------------------------------------------

def test_preface_a_colour_never_prevents_two_teams_from_meeting():
    """The Preface - "the colour will never be a factor so decisive as to prevent two
    teams from playing against each other. Therefore, there are no absolute colour
    preferences outlined in these regulations."

    Teams 1 and 2 have both played White twice: under C.04.3 art. 1.7.1 both would have an
    ABSOLUTE preference for Black, and art. 2.1.3 [C3] would forbid the pairing outright.
    Here they are the only two teams left with 4 match points, and C.04.6 pairs them: one
    of them simply does not get the colour it prefers, which costs [C8] (art. 2.3.5) and
    nothing else.
    """
    tournament = event(6, 5)
    tournament.match(1, 1, 3, ["W", "W"])       # 1 white
    tournament.match(1, 2, 4, ["W", "W"])       # 2 white
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(2, 1, 4, ["W", "W"])       # 1 white again -> cd +2
    tournament.match(2, 2, 5, ["W", "W"])       # 2 white again -> cd +2
    tournament.match(2, 3, 6, ["W", "W"])
    engine = tournament.engine(3)
    pairs = [(pair["w"], pair["b"]) for bracket in engine.compute_pairing(False) for pair in bracket["pairs"]]
    assert engine.competitors[1]["cop"] == "b2"
    assert engine.competitors[2]["cop"] == "b2"
    assert (1, 2) in pairs or (2, 1) in pairs
    # one of the two does not get Black: that is one unfulfilled preference, [C8] = 1
    brackets = engine.roundpairing
    assert quality(brackets, engine.competitors[1]["scorelevel"], "QC8") == 1


# ---------------------------------------------------------------------------
# Art. 2.1 - the absolute criteria
# ---------------------------------------------------------------------------

def test_art_2_1_1_c1_two_teams_shall_not_meet_twice():
    """[C1] art. 2.1.1 (Basic Rules art. 2) - two teams shall not play each other twice.

    After round 1, teams 1 and 2 both have 2 match points and would be the whole
    top-scoregroup - but they have already met, so the bracket cannot be paired within
    itself and art. 3.5 must bring upfloaters in.
    """
    tournament = event(4, 3)
    tournament.match(1, 1, 2, ["W", "D"])       # 1 beats 2
    tournament.match(1, 3, 4, ["W", "D"])       # 3 beats 4
    pairs = tournament.pair(2)
    assert (1, 2) not in pairs and (2, 1) not in pairs
    assert sorted(sorted(pair) for pair in pairs) == [[1, 3], [2, 4]]


def test_art_2_1_2_c2_no_second_pairing_allocated_bye():
    """[C2] art. 2.1.2 - a team that has already received the bye shall not receive it again.

    Team 5 has the lowest score and the largest TPN after round 1, so art. 3.4 would give
    it the bye - but it had one in round 1. Team 4, the next candidate, gets it.
    """
    tournament = event(5, 3)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.pab(1, 5)
    pairs = tournament.pair(2)
    assert bye(pairs) != 5
    assert bye(pairs) == 4                      # 4 and 2 have 0 points, 4 has the larger TPN


def test_art_2_1_2_c2_no_bye_after_a_forfeit_win():
    """[C2] art. 2.1.2 - nor shall a team that has won a match by forfeit.

    Team 5 wins round 1 by forfeit over team 4 and would otherwise be a bye candidate in
    round 2 (it is not: it has 2 points). Team 4 lost the forfeit and stays a candidate.
    Round 3: team 5 has the lowest score of the teams that may still take a bye, but the
    forfeit win bars it, so the bye goes to the next candidate.
    """
    tournament = event(5, 3)
    tournament.forfeit(1, 5, 4)                 # 5 wins by forfeit, 4 loses
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.pab(1, 3)
    tournament.match(2, 1, 5, ["L", "L"])       # 5 beats 1
    tournament.match(2, 3, 2, ["L", "L"])       # 2 beats 3
    tournament.pab(2, 4)
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    # 5 has 4 match points and 4 has 1: both are barred from the bye ([C2]), 3 is not.
    assert engine.competitors[5]["cop"] is not None
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[5])
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[4])   # it had the bye in r2
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[3])   # it had the bye in r1
    assert not engine.crosstable.had_bye_or_forfeit_win(engine.competitors[1])
    pairs = [(pair["w"], pair["b"]) for bracket in engine.roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) in (1, 2)


def test_art_2_1_2_c2_no_bye_after_a_full_point_bye():
    """[C2] art. 2.1.2 - "(or been given a FIDE-deprecated full-point bye)"."""
    tournament = event(5, 3)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.fullpointbye(1, 5)
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[5])
    pairs = [(pair["w"], pair["b"]) for bracket in engine.roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) != 5


def test_art_2_1_2_c2_a_half_point_bye_does_not_bar_the_bye():
    """[C2] art. 2.1.2 - it names the bye, the forfeit win and the full-point bye, and
    nothing else. A team that took a half-point bye may still be given the bye."""
    tournament = event(5, 3)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.halfpointbye(1, 5)
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    assert not engine.crosstable.had_bye_or_forfeit_win(engine.competitors[5])


# ---------------------------------------------------------------------------
# Art. 3.4 - the pairing-allocated-bye
# ---------------------------------------------------------------------------

def test_art_3_4_2_the_bye_goes_to_the_lowest_score():
    """Art. 3.4.2 - the bye goes to the team with the lowest score."""
    tournament = event(5, 3)
    tournament.match(1, 1, 2, ["W", "W"])       # 1 wins
    tournament.match(1, 3, 4, ["L", "L"])       # 4 wins
    tournament.pab(1, 5)
    pairs = tournament.pair(2)
    # 2 and 3 have 0 points, 5 has 1 (the bye), 1 and 4 have 2. The bye may not go to 5
    # again ([C2]), so it goes to a team on 0 points - the largest TPN of them, 3.
    assert bye(pairs) == 3


def test_art_3_4_3_the_bye_goes_to_the_most_matches_played():
    """Art. 3.4.3 - among the teams with the lowest score, to the one that has played the
    highest number of matches - and it comes before art. 3.4.4, the TPN.

    Teams 4 and 5 both have 0 match points before round 3. Team 4 played both of its
    matches and lost them; team 5 was not paired in round 1 (C.04.2 art. 3.3 - a team known
    in advance not to play) and lost its only match. Team 4 has played the more matches, so
    the bye is team 4's - although team 5 has the larger TPN, which art. 3.4.4 would take
    if art. 3.4.3 had not already decided.
    """
    tournament = event(5, 5)
    tournament.match(1, 1, 2, ["W", "W"])       # 1 beats 2
    tournament.match(1, 3, 4, ["W", "W"])       # 3 beats 4       (5 is not paired at all)
    tournament.match(2, 1, 4, ["W", "W"])       # 1 beats 4 again (3 is not paired)
    tournament.match(2, 2, 5, ["W", "W"])       # 2 beats 5
    engine = tournament.engine(3)
    roundpairing = engine.compute_pairing(False)
    assert engine.competitors[4]["acc"] == engine.competitors[5]["acc"]   # 3.4.2 is a tie
    assert engine.competitors[4]["num"]["val"] == 2                       # 3.4.3 decides
    assert engine.competitors[5]["num"]["val"] == 1
    assert engine.competitors[4]["tpn"] < engine.competitors[5]["tpn"]    # 3.4.4 would not
    pairs = [(pair["w"], pair["b"]) for bracket in roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) == 4


def test_art_3_4_4_the_bye_goes_to_the_largest_tpn():
    """Art. 3.4.4 - and among those, to the team with the largest TPN."""
    tournament = event(5, 3)
    tournament.match(1, 1, 4, ["W", "W"])       # 4 loses
    tournament.match(1, 2, 5, ["W", "W"])       # 5 loses
    tournament.pab(1, 3)
    pairs = tournament.pair(2)
    # 4 and 5 have 0 points and both have played one match; 5 has the larger TPN
    assert bye(pairs) == 5


def test_art_3_4_1_the_bye_must_leave_a_legal_pairing():
    """Art. 3.4.1 - the bye goes to the team that "leaves a legal pairing for all teams",
    and it says so before art. 3.4.2 says anything about the score.

    Five teams. Round 1: 1 beat 4, 2 beat 5, and 3 was not paired. Three pairs are
    forbidden by record 260 (1-2, 2-4 and 3-4 may not meet), so the pairs that are still
    available are 1-3, 1-5, 2-3, 3-5 and 4-5.

    By art. 3.4.2 - 3.4.4 alone the bye would go to team 5: it shares the lowest score with
    teams 3 and 4, it has played as many matches as team 4, and it has the largest TPN.
    But the four teams that are left - 1, 2, 3 and 4 - cannot then all be paired (1 and 3
    would both need team 3), so team 5 leaves no legal pairing and art. 3.4.1 rules it out.
    Team 3 is ruled out for the same reason. The bye goes to team 4, the first candidate
    that leaves the rest pairable.
    """
    tournament = event(5, 5)
    tournament.tournament["prohibited"] = [
        {"firstRound": 1, "lastRound": 5, "competitors": [1, 2]},
        {"firstRound": 1, "lastRound": 5, "competitors": [2, 4]},
        {"firstRound": 1, "lastRound": 5, "competitors": [3, 4]},
    ]
    tournament.match(1, 1, 4, ["W", "W"])       # 1 beats 4
    tournament.match(1, 2, 5, ["W", "W"])       # 2 beats 5      (3 is not paired)
    engine = tournament.engine(2)
    roundpairing = engine.compute_pairing(False)
    # the candidates, in the order of art. 3.4.2 - 3.4.4: 5 first, then 4, then 3
    assert engine.competitors[5]["acc"] == engine.competitors[4]["acc"]
    assert engine.competitors[5]["num"]["val"] == engine.competitors[4]["num"]["val"]
    assert engine.competitors[5]["tpn"] > engine.competitors[4]["tpn"]
    pairs = [(pair["w"], pair["b"]) for bracket in roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) == 4
    assert sorted(sorted(pair) for pair in pairs if pair[1] != 0) == [[1, 5], [2, 3]]


# ---------------------------------------------------------------------------
# Art. 3.5 - the selection of the upfloaters
# ---------------------------------------------------------------------------

def test_art_3_5_4_the_sets_are_sorted_lexicographically():
    """Art. 3.5.4 and its example.

    "Let's assume that 2,6,8 have 3 points, and 1,3,5 have 2.5 points. [C4] determines
    that a set of three upfloaters is needed, and [C5] determines that two upfloaters must
    have 3 points and the other 2.5 points. The possible set of upfloaters are:
    {2,6,1} < {2,6,3} < {2,6,5} < {2,8,1} < {2,8,3} < {2,8,5} < {6,8,1} < {6,8,3} < {6,8,5},
    already sorted in the proper order."

    The order is the one the engine enumerates the sets in, and art. 3.5.5 takes the first
    of them that qualifies - so it is the order that decides which set is chosen.
    """
    engine = event(8, 5).engine(2)
    engine.rank = "cid"
    lower = [{"cid": cid, "scorelevel": 3 if cid in (2, 6, 8) else 2, "cid": cid} for cid in (1, 2, 3, 5, 6, 8)]
    for node in lower:
        node["rnk"] = node["cid"]
    profile = (3, 3, 2)                         # two upfloaters of 3 points, one of 2.5
    sets = engine.list_upfloaters(lower, profile)
    assert [[node["cid"] for node in s] for s in sets] == [
        [2, 6, 1], [2, 6, 3], [2, 6, 5],
        [2, 8, 1], [2, 8, 3], [2, 8, 5],
        [6, 8, 1], [6, 8, 3], [6, 8, 5],
    ]


def test_art_3_5_3_a_set_is_sorted_by_descending_score_then_ascending_tpn():
    """Art. 3.5.3 - within a set, the upfloaters are sorted by descending score first.

    {2, 6, 1} is 2 and 6 (3 points) and then 1 (2.5 points) - not 1, 2, 6. That is what
    makes {2,6,5} come before {2,8,1} in art. 3.5.4: the comparison is on the sequence.
    """
    engine = event(8, 5).engine(2)
    lower = [{"cid": cid, "rnk": cid, "scorelevel": 3 if cid in (2, 6, 8) else 2} for cid in (1, 2, 3, 5, 6, 8)]
    sets = engine.list_upfloaters(lower, (3, 3, 2))
    assert [node["cid"] for node in sets[0]] == [2, 6, 1]
    assert [node["scorelevel"] for node in sets[0]] == [3, 3, 2]


def test_art_2_3_1_c4_minimise_the_number_of_upfloaters():
    """[C4] art. 2.3.1 - minimise the number of upfloaters.

    After round 1 three teams have 2 match points (1, 2 and 3 won), two have 1 (4 and 8
    drew) and three have 0. The top-scoregroup is odd, so the bracket cannot be paired
    without an upfloater - and one upfloater is enough. [C4] takes one, not three, and the
    bracket is 1, 2, 3 and the upfloater.
    """
    tournament = event(8, 5)
    tournament.match(1, 1, 5, ["W", "W"])       # 1 -> 2 mp
    tournament.match(1, 2, 6, ["W", "W"])       # 2 -> 2 mp
    tournament.match(1, 3, 7, ["W", "W"])       # 3 -> 2 mp
    tournament.match(1, 4, 8, ["W", "L"])       # 4 and 8 draw -> 1 mp each
    (engine, brackets) = tournament.brackets(2)
    top = engine.competitors[1]["scorelevel"]
    floated = upfloaters(brackets, top)
    assert len(floated) == 1
    assert quality(brackets, top, "QC4") == 1
    # and [C5] (art. 2.3.2) takes it from the scoregroup right below, not from the 0-point one
    assert engine.competitors[floated[0]]["acc"] == decimal.Decimal("1.0")


def test_art_2_3_2_c5_maximise_the_scores_of_the_upfloaters():
    """[C5] art. 2.3.2 - "maximise the scores (taken in ascending order) of the upfloaters".

    One team has 4 match points, four teams have 2 and two have 0. The top-scoregroup is a
    single team, so it needs one upfloater, and [C5] takes it from the 2-point scoregroup -
    never from the 0-point one.
    """
    tournament = event(7, 5)
    tournament.match(1, 1, 2, ["W", "W"])       # 1 beats 2
    tournament.match(1, 3, 4, ["D", "D"])       # 3 and 4 draw
    tournament.match(1, 5, 6, ["D", "D"])       # 5 and 6 draw
    tournament.pab(1, 7)                        # 7 gets a draw's worth of match points
    tournament.match(2, 1, 3, ["W", "W"])       # 1 -> 4 points
    tournament.match(2, 4, 5, ["W", "W"])       # 4 -> 3 points ... etc
    tournament.match(2, 6, 7, ["L", "L"])
    tournament.pab(2, 2)
    (engine, brackets) = tournament.brackets(3)
    top = engine.competitors[1]["scorelevel"]
    floated = upfloaters(brackets, top)
    assert len(floated) == 1
    # the upfloater comes from the scoregroup right below the top one
    assert engine.competitors[floated[0]]["scorelevel"] == top - 1


def c7_tournament(numrounds):
    """Twelve teams. Before round 3 the top-scoregroup is team 1 alone (4 match points),
    and the scoregroup below it holds teams 2, 3, 4, 5 and 6 (3 match points each). Team 1
    has met none of them, so any of the five may be its upfloater - and team 2 is the first
    of them in the lexicographic order of art. 3.5.4.

    Team 2 got its third point by drawing against team 9, which had none: it was a floater
    in round 2 (art. 1.5). Teams 3 to 6 drew among themselves and were not.
    """
    tournament = event(12, numrounds)
    tournament.match(1, 1, 7, ["W", "W"])       # 1..6 -> 2 mp, 7..12 -> 0 mp
    tournament.match(1, 2, 8, ["W", "W"])
    tournament.match(1, 3, 9, ["W", "W"])
    tournament.match(1, 4, 10, ["W", "W"])
    tournament.match(1, 5, 11, ["W", "W"])
    tournament.match(1, 6, 12, ["W", "W"])
    tournament.match(2, 1, 8, ["W", "W"])       # 1 -> 4 mp
    tournament.match(2, 2, 9, ["W", "L"])       # 2 (2 mp) draws with 9 (0 mp) -> 3 mp: A FLOATER
    tournament.match(2, 3, 4, ["W", "L"])       # 3 and 4 draw -> 3 mp : same score, no float
    tournament.match(2, 5, 6, ["W", "L"])       # 5 and 6 draw -> 3 mp : same score, no float
    tournament.match(2, 10, 11, ["W", "L"])
    tournament.match(2, 12, 7, ["W", "L"])
    return tournament


def test_art_2_3_4_c7_minimise_upfloaters_that_floated_in_the_previous_round():
    """[C7] art. 2.3.4 - "with the exception of the last two rounds, minimise the number of
    upfloaters that were floaters in the previous round".

    Art. 3.5.4 would take team 2, the first set in lexicographic order. [C7] comes before
    it (art. 3.5.5) and takes team 3, the first team of the scoregroup that did not float.
    """
    tournament = c7_tournament(6)
    (engine, brackets) = tournament.brackets(3)
    assert not engine.lasttworounds
    assert engine.competitors[2]["flt"] != 0    # team 2 floated in round 2
    assert engine.competitors[3]["flt"] == 0    # team 3 did not
    assert engine.competitors[5]["flt"] == 0
    top = engine.competitors[1]["scorelevel"]
    assert upfloaters(brackets, top) == [3]
    assert quality(brackets, top, "QC7") == 0


def test_art_2_3_4_c7_does_not_apply_in_the_last_two_rounds():
    """[C7] art. 2.3.4 - "with the exception of the last two rounds".

    The same position, in a four-round tournament: round 3 is now the second-to-last, [C7]
    is inert, and art. 3.5.4 decides on its own - the upfloater is team 2, the very team
    [C7] kept out of the bracket in the test above.
    """
    tournament = c7_tournament(4)
    (engine, brackets) = tournament.brackets(3)
    assert engine.lasttworounds
    assert engine.competitors[2]["flt"] != 0
    top = engine.competitors[1]["scorelevel"]
    assert upfloaters(brackets, top) == [2]


def test_art_2_3_7_c10_minimise_the_upfloaters_opponents_that_floated():
    """[C10] art. 2.3.7 - "with the exception of the last two rounds, minimise the number
    of upfloaters' opponents that were floaters in the previous round".

    Ten teams. Every team has played one match with White and one with Black, so no team
    has a colour preference at all (art. 1.7.1) and [C8] and [C9] are silent: the bracket
    is decided by [C10] and by the identifier, and by nothing else.

    Before round 3 the top-scoregroup is 1, 2, 3, 4 and 5 (3 match points each) and the
    scoregroup below holds 6 to 10 (1 point each). The top-scoregroup is odd, so one
    upfloater joins it - team 6, by art. 3.5.4 - and exactly one of the five residents is
    paired with it. Team 3 was a floater in round 2 (it drew with team 10, which had no
    points); teams 1, 2, 4 and 5 were not.

    The smallest identifier (art. 3.6.2) of this bracket belongs to 1-4 2-5 3-6, which
    pairs the upfloater with team 3. [C10] comes before the identifier (art. 3.6.4) and
    rules it out: the upfloater's opponent must not be a team that floated. The smallest
    identifier that respects [C10] is 1-4 2-6 3-5, and that is the answer.
    """
    tournament = event(10, 6)
    tournament.match(1, 1, 6, ["W", "W"])       # 1..5 -> 2 mp, 6..10 -> 0 mp
    tournament.match(1, 7, 2, ["L", "L"])       # the colours alternate: 2 and 4 win as
    tournament.match(1, 3, 8, ["W", "W"])       # the black team, so that no team ends the
    tournament.match(1, 9, 4, ["L", "L"])       # second round with two Whites or two
    tournament.match(1, 5, 10, ["W", "W"])      # Blacks - and none has a preference
    tournament.match(2, 2, 1, ["W", "L"])       # 1 and 2 draw -> 3 mp : no float
    tournament.match(2, 4, 5, ["W", "L"])       # 4 and 5 draw -> 3 mp : no float
    tournament.match(2, 10, 3, ["W", "L"])      # 3 (2 mp) draws with 10 (0 mp): A FLOATER
    tournament.match(2, 6, 7, ["W", "L"])
    tournament.match(2, 8, 9, ["W", "L"])
    (engine, brackets) = tournament.brackets(3)
    for team in range(1, 11):
        assert engine.competitors[team]["cop"] == "nc"      # [C8] and [C9] are silent
    assert engine.competitors[3]["flt"] != 0
    for team in (1, 2, 4, 5):
        assert engine.competitors[team]["flt"] == 0
    top = engine.competitors[1]["scorelevel"]
    assert upfloaters(brackets, top) == [6]
    assert quality(brackets, top, "QC8") == 0
    assert quality(brackets, top, "QC10") == 0
    pairs = [(pair["w"], pair["b"]) for bracket in brackets for pair in bracket["pairs"]]
    bracketpairs = sorted(sorted(pair) for pair in pairs if set(pair) <= {1, 2, 3, 4, 5, 6})
    assert bracketpairs == [[1, 4], [2, 6], [3, 5]]


# ---------------------------------------------------------------------------
# Art. 2.3.5 / 2.3.6 - the colour criteria
# ---------------------------------------------------------------------------

def test_art_2_3_5_c8_minimise_the_unfulfilled_colour_preferences():
    """[C8] art. 2.3.5 - minimise the number of teams whose colour preference is not
    fulfilled.

    Four teams on 2 match points. 1 and 2 have played White twice (a preference for Black
    under both types), 3 and 4 have played Black twice (a preference for White). Pairing
    1-2 and 3-4 would leave two preferences unfulfilled; pairing 1 and 2 against 3 and 4
    leaves none, and [C8] says so - even though the identifier of art. 3.6.2 prefers
    1-2 / 3-4 (identifier "1 3 2 4" against "1 2 3 4"). [C8] comes first (art. 3.6.4).
    """
    tournament = event(8, 6)
    tournament.match(1, 1, 5, ["W", "W"])       # 1 white
    tournament.match(1, 2, 6, ["W", "W"])       # 2 white
    tournament.match(1, 7, 3, ["L", "L"])       # 3 black, and wins
    tournament.match(1, 8, 4, ["L", "L"])       # 4 black, and wins
    tournament.match(2, 1, 7, ["W", "W"])       # 1 white again -> cd +2 -> Black
    tournament.match(2, 2, 8, ["W", "W"])       # 2 white again -> cd +2 -> Black
    tournament.match(2, 5, 3, ["L", "L"])       # 3 black again -> cd -2 -> White
    tournament.match(2, 6, 4, ["L", "L"])       # 4 black again -> cd -2 -> White
    (engine, brackets) = tournament.brackets(3)
    for team in (1, 2):
        assert engine.competitors[team]["cop"] == "b2"
    for team in (3, 4):
        assert engine.competitors[team]["cop"] == "w2"
    top = engine.competitors[1]["scorelevel"]
    assert quality(brackets, top, "QC8") == 0
    pairs = [(pair["w"], pair["b"]) for bracket in brackets for pair in bracket["pairs"]]
    bracketpairs = sorted(sorted(pair) for pair in pairs if set(pair) <= {1, 2, 3, 4})
    assert bracketpairs == [[1, 3], [2, 4]]
    # and the colours are the ones both teams want (art. 4.3.3)
    assert (3, 1) in pairs and (4, 2) in pairs


def strong_and_mild(typeb):
    """Eight teams, three rounds played, and teams 1 to 4 have won every match and have
    never met each other: before round 4 they are a bracket of four, on 6 match points.

    Their colours are w,b,b (1 and 3) and b,w,b (2 and 4), so all four have a colour
    difference of -1, and all four want White:
        1 and 3 - the last two played matches were with Black: art. 1.7.1 gives them a
                  SIMPLE preference for White, art. 1.7.2 a STRONG one.
        2 and 4 - the last two were not: art. 1.7.1 gives them NO preference at all, and
                  art. 1.7.2 a MILD one (their colour difference is -1).
    """
    tournament = event(8, 6, typeb=typeb)
    tournament.match(1, 1, 5, ["W", "W"])       # 1 White
    tournament.match(1, 6, 2, ["L", "L"])       # 2 Black, and wins
    tournament.match(1, 3, 7, ["W", "W"])       # 3 White
    tournament.match(1, 8, 4, ["L", "L"])       # 4 Black, and wins
    tournament.match(2, 6, 1, ["L", "L"])       # 1 Black
    tournament.match(2, 2, 5, ["W", "W"])       # 2 White
    tournament.match(2, 8, 3, ["L", "L"])       # 3 Black
    tournament.match(2, 4, 7, ["W", "W"])       # 4 White
    tournament.match(3, 7, 1, ["L", "L"])       # 1 Black -> w,b,b
    tournament.match(3, 8, 2, ["L", "L"])       # 2 Black -> b,w,b
    tournament.match(3, 5, 3, ["L", "L"])       # 3 Black -> w,b,b
    tournament.match(3, 6, 4, ["L", "L"])       # 4 Black -> b,w,b
    return tournament


def test_art_2_3_6_c9_is_type_b_only_and_decides_the_bracket():
    """[C9] art. 2.3.6 - "(Type B only) minimise the number of teams whose strong colour
    preference, if any, is not fulfilled".

    The bracket is 1, 2, 3, 4 - all four want White, 1 and 3 strongly, 2 and 4 mildly.
    Under type B every pair of the bracket is a pair of teams that want the same colour, so
    [C8] is 2 whichever way it is paired and cannot separate anything. The smallest
    identifier (art. 3.6.2) is 1-3 2-4 ("1 2 3 4"), and that pairing puts the two STRONG
    preferences against each other: [C9] = 1. The engine must reject it and take the next
    identifier that does not, 1-4 2-3 ("1 2 4 3").

    Under type A teams 2 and 4 have no preference at all, [C9] does not exist, and it is
    [C8] that rejects 1-3 2-4 - the only pairing that puts two teams that want White
    against each other.
    """
    typea = strong_and_mild(typeb=False)
    typeb = strong_and_mild(typeb=True)
    (enginea, bracketsa) = typea.brackets(4)
    (engineb, bracketsb) = typeb.brackets(4)
    assert [enginea.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["w2", "nc", "w2", "nc"]
    assert [engineb.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["w2", "w1", "w2", "w1"]

    top = engineb.competitors[1]["scorelevel"]
    chosen = sorted(sorted(pair) for pair in bracket_pairs(bracketsb, {1, 2, 3, 4}))
    assert chosen == [[1, 4], [2, 3]]
    # under type B, [C8] cannot have rejected 1-3 2-4: it costs 2 either way
    assert quality(bracketsb, top, "QC8") == 2
    assert quality(bracketsb, top, "QC9") == 0
    rejected = engineb.crosstable.compute_weight(
        [engineb.opponents[1][3], engineb.opponents[2][4]], None
    )
    assert rejected["QC8"] == 2                 # the same as the chosen pairing ...
    assert rejected["QC9"] == 1                 # ... and [C9] is what rules it out

    # type A: [C9] is inert, and the pairing that [C8] rejects is the same one
    assert quality(bracketsa, top, "QC9") == 0
    rejected = enginea.crosstable.compute_weight(
        [enginea.opponents[1][3], enginea.opponents[2][4]], None
    )
    assert rejected["QC8"] == 1                 # against 0 for the chosen pairing
    assert rejected["QC9"] == 0                 # type A has no strong preferences
    assert quality(bracketsa, top, "QC8") == 0


def bracket_pairs(brackets, teams):
    pairs = [(pair["w"], pair["b"]) for bracket in brackets for pair in bracket["pairs"]]
    return [pair for pair in pairs if set(pair) <= teams]


def mild_only(typeb):
    """The same eight teams, but the colours of 1 and 3 are b,w,b and those of 2 and 4 are
    w,b,w: all four have a colour difference of +/-1 and none of them played its last two
    matches with the same colour.

    Art. 1.7.1 gives none of them a preference. Art. 1.7.2 gives 1 and 3 a mild preference
    for White and 2 and 4 a mild preference for Black.
    """
    tournament = event(8, 6, typeb=typeb)
    tournament.match(1, 5, 1, ["L", "L"])       # 1 Black, and wins
    tournament.match(1, 2, 6, ["W", "W"])       # 2 White
    tournament.match(1, 7, 3, ["L", "L"])       # 3 Black
    tournament.match(1, 4, 8, ["W", "W"])       # 4 White
    tournament.match(2, 1, 6, ["W", "W"])       # 1 White
    tournament.match(2, 5, 2, ["L", "L"])       # 2 Black
    tournament.match(2, 3, 8, ["W", "W"])       # 3 White
    tournament.match(2, 7, 4, ["L", "L"])       # 4 Black
    tournament.match(3, 7, 1, ["L", "L"])       # 1 Black -> b,w,b
    tournament.match(3, 2, 8, ["W", "W"])       # 2 White -> w,b,w
    tournament.match(3, 5, 3, ["L", "L"])       # 3 Black -> b,w,b
    tournament.match(3, 4, 6, ["W", "W"])       # 4 White -> w,b,w
    return tournament


def test_art_1_7_type_a_and_type_b_pair_the_same_position_differently():
    """Art. 1.7.1 against art. 1.7.2, in the pairing rather than in the preference.

    The bracket is 1, 2, 3, 4 again. Under type A none of them has a colour preference, so
    [C8] costs nothing whatever the pairing is, and the smallest identifier wins: 1-3 2-4.

    Under type B, 1 and 3 want White and 2 and 4 want Black - mildly, but art. 2.3.5 [C8]
    counts a mild preference like any other. 1-3 2-4 then leaves two teams unserved and
    costs [C8] = 2, while 1-4 2-3 costs nothing. The two types pair the same position
    differently, and that is the whole reason art. 1.7 offers both.
    """
    (enginea, bracketsa) = mild_only(typeb=False).brackets(4)
    (engineb, bracketsb) = mild_only(typeb=True).brackets(4)
    assert [enginea.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["nc", "nc", "nc", "nc"]
    assert [engineb.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["w1", "b1", "w1", "b1"]
    assert sorted(sorted(pair) for pair in bracket_pairs(bracketsa, {1, 2, 3, 4})) == [[1, 3], [2, 4]]
    assert sorted(sorted(pair) for pair in bracket_pairs(bracketsb, {1, 2, 3, 4})) == [[1, 4], [2, 3]]
    top = engineb.competitors[1]["scorelevel"]
    assert quality(bracketsa, top, "QC8") == 0
    assert quality(bracketsb, top, "QC8") == 0
    # and under type B the type A answer would have cost two unfulfilled preferences
    rejected = engineb.crosstable.compute_weight(
        [engineb.opponents[1][3], engineb.opponents[2][4]], None
    )
    assert rejected["QC8"] == 2


# ---------------------------------------------------------------------------
# Art. 3.6 - the pairing of a bracket
# ---------------------------------------------------------------------------

def test_art_3_6_the_first_round_is_the_first_pairing_in_lexicographic_order():
    """Art. 3.6.2 - 3.6.4 - the identifier, and the order of the identifiers.

    In round 1 no team has met another, no team has a colour preference, and no team is an
    upfloater, so [C1] and [C8] to [C10] are satisfied by every pairing of the field. The
    first pairing in the lexicographic order of the identifiers of art. 3.6.2 is then the
    one whose top members are 1..H - the smallest they can be - and whose bottom members
    are H+1..2H in that same order: 1-9, 2-10, 3-11 ... for sixteen teams.
    """
    tournament = event(16, 9)
    pairs = sorted(sorted(pair) for pair in tournament.pair(1))
    assert pairs == [[team, team + 8] for team in range(1, 9)]


def test_art_3_6_2_top_and_bottom_members():
    """Art. 3.6.1 and 3.6.2 - "the team with the smaller TPN is the top member of the
    pair", and the identifier holds all the top members before the bottom ones.

    Round 1 of a six-team event: the pairing 1-4 2-5 3-6 has the identifier "1 2 3 4 5 6".
    The pairing 1-2 3-4 5-6 has the identifier "1 3 5 2 4 6", which is larger at the second
    position, so it loses - even though it pairs teams that are closer together.
    """
    tournament = event(6, 5)
    pairs = sorted(sorted(pair) for pair in tournament.pair(1))
    assert pairs == [[1, 4], [2, 5], [3, 6]]


# ---------------------------------------------------------------------------
# Art. 4 - the colour allocation
# ---------------------------------------------------------------------------

def test_art_4_3_1_the_initial_colour_and_the_parity_of_the_tpn():
    """Art. 4.3.1 - "when both teams have yet to play a match, if the first-team has an odd
    TPN, give it the initial-colour; otherwise, give it the opposite colour".

    In round 1 every team has yet to play, and the first-team of a pair is the one with the
    smaller TPN (art. 4.2.3, the scores being equal). With the initial-colour White, the
    pairs are 1-5 (1 is odd: White), 6-2 (2 is even: Black), 3-7 (odd: White), 8-4 (even).
    """
    tournament = event(8, 5)
    tournament.tournament["topColor"] = "w"
    assert tournament.pair(1) == [(1, 5), (6, 2), (3, 7), (8, 4)]
    tournament.tournament["topColor"] = "b"
    assert tournament.pair(1) == [(5, 1), (2, 6), (7, 3), (4, 8)]


def test_art_4_2_the_first_team_is_the_higher_primary_score():
    """Art. 4.2.1 - the first-team is the one with the higher primary score, and the score
    comes before the TPN of art. 4.2.3.

    Team 4 won its first match and team 2 lost its own: team 4 is the first-team of the
    two, although its TPN is the larger one.
    """
    tournament = event(4, 5)
    tournament.match(1, 1, 4, ["L", "L"])       # 4 wins with Black -> 2 match points
    tournament.match(1, 2, 3, ["L", "L"])       # 2 loses with White -> 0 match points
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    (four, two) = (engine.competitors[4], engine.competitors[2])
    assert four["acc"] > two["acc"]
    assert four["tpn"] > two["tpn"]
    assert engine.first_team(four, two) is True
    assert engine.first_team(two, four) is False


def test_art_4_2_2_the_secondary_score_and_the_rules_that_switch_it_off():
    """Art. 4.2.2 - the first-team is then the one with the higher secondary score,
    "unless the rules of the competition state not to use it".

    Two teams with the same match points and different game points. With a secondary score
    the first-team is the one with more game points (team 3); without one, art. 4.2.3
    decides and the first-team is the smaller TPN (team 2).
    """
    tournament = event(4, 5, primary="match", secondary="game")
    tournament.match(1, 2, 4, ["W", "D"])       # team 2: 1.5 game points, 2 match points
    tournament.match(1, 3, 1, ["W", "W"])       # team 3: 2.0 game points, 2 match points
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    (two, three) = (engine.competitors[2], engine.competitors[3])
    assert engine.secondary
    assert two["acc"] == three["acc"]           # the same match points
    assert three["acx"] > two["acx"]            # more game points
    assert engine.first_team(three, two) is True

    noscondary = event(4, 5, primary="match")   # FIDE_TEAM_TYPEA_MP: no secondary score
    noscondary.match(1, 2, 4, ["W", "D"])
    noscondary.match(1, 3, 1, ["W", "W"])
    engine = noscondary.engine(2)
    engine.compute_pairing(False)
    (two, three) = (engine.competitors[2], engine.competitors[3])
    assert not engine.secondary
    assert engine.first_team(two, three) is True    # art. 4.2.3: the smaller TPN


def test_art_4_3_2_grant_the_only_preference():
    """Art. 4.3.2 - if only one team has a colour preference, grant it."""
    tournament = event(4, 5)
    tournament.match(1, 1, 2, ["W", "W"])       # 1 white, 2 black
    tournament.match(1, 3, 4, ["W", "W"])       # 3 white, 4 black
    tournament.match(2, 1, 3, ["W", "W"])       # 1 white again: cd +2, Black
    tournament.match(2, 4, 2, ["W", "W"])       # 4 white: cd 0.  2 black again: cd -2, White
    rules = tournament.colorrules(3)
    # team 1 (Black, type A "b2") meets team 4 (no preference): art. 4.3.2
    assert (4, 1) in rules and rules[(4, 1)] == "4.3.2"


def test_art_4_3_3_grant_two_opposite_preferences():
    """Art. 4.3.3 - if the two teams have opposite colour preferences, grant them.

    Teams 1 and 2 have won both of their matches and are the top-scoregroup, so they are
    paired with each other. Team 1 played both matches with Black (colour difference -2)
    and wants White; team 2 played both with White and wants Black. Both are granted.
    """
    tournament = event(6, 5)
    tournament.match(1, 3, 1, ["L", "L"])       # 1 wins with Black
    tournament.match(1, 2, 4, ["W", "W"])       # 2 wins with White
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(2, 5, 1, ["L", "L"])       # 1 wins with Black again -> wants White
    tournament.match(2, 2, 6, ["W", "W"])       # 2 wins with White again -> wants Black
    tournament.match(2, 3, 4, ["W", "W"])
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    assert engine.competitors[1]["cop"] == "w2"
    assert engine.competitors[2]["cop"] == "b2"
    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in engine.roundpairing
        for pair in bracket["pairs"]
    }
    assert rules[(1, 2)] == "4.3.3"


def test_art_4_3_4_grant_the_strong_preference_over_the_mild_one():
    """Art. 4.3.4 - "(Type B only) If only one team has a strong colour preference, grant
    it".

    The strong_and_mild bracket is paired 1-4 and 2-3, and in both pairs the two teams want
    White: 1 and 3 strongly, 2 and 4 mildly. Art. 4.3.2 and 4.3.3 have nothing to say - both
    teams of each pair have a preference and it is the same one - and art. 4.3.4 grants the
    strong one. Under type A the mild teams have no preference at all, so it is art. 4.3.2
    that grants the other one, and the colours come out the same way for a different reason.
    """
    rules = strong_and_mild(typeb=True).colorrules(4)
    assert rules[(1, 4)] == "4.3.4"              # 1 is strong, 4 is mild: 1 gets White
    assert rules[(3, 2)] == "4.3.4"              # 3 is strong, 2 is mild: 3 gets White
    rules = strong_and_mild(typeb=False).colorrules(4)
    assert rules[(1, 4)] == "4.3.2"              # type A: only team 1 has a preference
    assert rules[(3, 2)] == "4.3.2"


def test_art_4_3_7_grant_the_colour_preference_of_the_first_team():
    """Art. 4.3.7 - grant the colour preference of the first-team.

    Teams 1 and 2 have both played their two matches with White: they have the same colour
    preference (Black), the same strength, the same colour difference and the same colour
    history, so art. 4.3.2 to 4.3.6 all pass without deciding anything. The first-team is
    team 1 - the scores are equal and its TPN is the smaller - and it gets what it wants.
    """
    tournament = event(6, 5)
    tournament.match(1, 1, 3, ["W", "W"])       # 1 White
    tournament.match(1, 2, 4, ["W", "W"])       # 2 White
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(2, 1, 4, ["W", "W"])       # 1 White again -> cd +2, wants Black
    tournament.match(2, 2, 5, ["W", "W"])       # 2 White again -> cd +2, wants Black
    tournament.match(2, 3, 6, ["W", "W"])
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    assert engine.competitors[1]["cop"] == engine.competitors[2]["cop"] == "b2"
    assert engine.competitors[1]["cod"] == engine.competitors[2]["cod"] == 2
    assert engine.competitors[1]["csq"] == engine.competitors[2]["csq"]
    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in engine.roundpairing
        for pair in bracket["pairs"]
    }
    assert rules[(2, 1)] == "4.3.7"             # team 1 is the first-team and gets Black


def test_art_4_3_9_alternate_the_other_team_from_its_last_played_round():
    """Art. 4.3.9 - alternate the colour of the other team from its last played round.

    Team 1 has not played a match at all: it took the bye in round 1 and a half-point bye in
    round 2, and it has two match points all the same. Team 3 has drawn both of its matches,
    with Black and then with White. Neither has a colour preference, their colour differences
    are both zero, and team 1 has no colour history to compare or to alternate - so art.
    4.3.1 to 4.3.8 all pass, and art. 4.3.9 alternates the colour of team 3 instead: it had
    White, so it gets Black, and team 1 gets White.
    """
    tournament = event(5, 5)
    tournament.pab(1, 1)                        # 1 match point, no colour (art. 1.4)
    tournament.match(1, 2, 3, ["W", "L"])       # a draw: 2 White, 3 Black
    tournament.match(1, 4, 5, ["W", "L"])       # a draw: 4 White, 5 Black
    tournament.halfpointbye(2, 1)               # one more match point, still no colour
    tournament.match(2, 2, 5, ["W", "L"])       # a draw
    tournament.match(2, 3, 4, ["W", "L"])       # a draw: 3 White, 4 Black
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    assert engine.competitors[1]["num"]["val"] == 0     # never played a match
    assert engine.competitors[1]["cop"] == "nc" and engine.competitors[3]["cop"] == "nc"
    assert engine.competitors[1]["cod"] == engine.competitors[3]["cod"] == 0
    assert engine.competitors[3]["csq"].strip() == "bw"
    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in engine.roundpairing
        for pair in bracket["pairs"]
    }
    assert rules[(1, 3)] == "4.3.9"


def test_art_4_3_5_white_to_the_lower_colour_difference():
    """Art. 4.3.5 - give White to the team with the lower colour difference.
    "Note: -2 is lower than -1; +1 is lower than +2."

    Teams 1 and 2 have won all three of their matches and are paired with each other.
    Team 1 played b,w,b and team 2 played w,b,w: neither has a type A colour preference
    (art. 1.7.1 - a colour difference of +/-1 is not enough, and their last two played
    matches were not the same colour), so art. 4.3.2 to 4.3.4 have nothing to say. Their
    colour differences are -1 and +1, and White goes to the lower one: team 1.
    """
    tournament = event(8, 9)
    tournament.match(1, 3, 1, ["L", "L"])       # 1 Black, wins
    tournament.match(1, 2, 4, ["W", "W"])       # 2 White, wins
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(1, 7, 8, ["W", "W"])
    tournament.match(2, 1, 4, ["W", "W"])       # 1 White, wins
    tournament.match(2, 3, 2, ["L", "L"])       # 2 Black, wins
    tournament.match(2, 5, 7, ["W", "W"])
    tournament.match(2, 6, 8, ["W", "W"])
    tournament.match(3, 5, 1, ["L", "L"])       # 1 Black, wins  -> b,w,b : cd -1
    tournament.match(3, 2, 6, ["W", "W"])       # 2 White, wins  -> w,b,w : cd +1
    tournament.match(3, 3, 7, ["W", "W"])
    tournament.match(3, 4, 8, ["W", "W"])
    engine = tournament.engine(4)
    engine.compute_pairing(False)
    assert engine.competitors[1]["cod"] == -1 and engine.competitors[1]["cop"] == "nc"
    assert engine.competitors[2]["cod"] == +1 and engine.competitors[2]["cop"] == "nc"
    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in engine.roundpairing
        for pair in bracket["pairs"]
    }
    assert rules[(1, 2)] == "4.3.5"


def test_art_4_3_6_alternate_from_the_most_recent_difference():
    """Art. 4.3.6 - "alternate the colours to the most recent time in which one team had
    White and the other Black", and the note: art. 3.4 of the General Handling Rules, so
    only played matches count and the histories are compared as compressed sequences.
    """
    tournament = event(6, 9)
    tournament.match(1, 1, 3, ["W", "W"])       # 1 White, wins
    tournament.match(1, 4, 2, ["L", "L"])       # 2 Black, wins
    tournament.match(1, 5, 6, ["W", "W"])
    tournament.match(2, 4, 1, ["L", "L"])       # 1 Black, wins -> w,b : cd 0
    tournament.match(2, 2, 5, ["W", "W"])       # 2 White, wins -> b,w : cd 0
    tournament.match(2, 3, 6, ["W", "W"])
    engine = tournament.engine(3)
    engine.compute_pairing(False)
    assert engine.competitors[1]["csq"].strip() == "wb"
    assert engine.competitors[2]["csq"].strip() == "bw"
    assert engine.competitors[1]["cod"] == 0 and engine.competitors[2]["cod"] == 0
    assert engine.competitors[1]["cop"] == "nc" and engine.competitors[2]["cop"] == "nc"
    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in engine.roundpairing
        for pair in bracket["pairs"]
    }
    # No preference for either, and their colour differences are equal, so art. 4.3.2 to
    # 4.3.5 pass. The most recent time one had White and the other Black is round 2, where
    # team 1 had Black and team 2 had White: they alternate, and team 1 gets White.
    assert rules[(1, 2)] == "4.3.6"


def test_art_4_3_8_alternate_the_first_team_from_its_last_played_round():
    """Art. 4.3.8 - when nothing else decides, alternate the colour of the first-team from
    its last played round.

    Two teams that have played one match each, both with White: same colour difference,
    identical colour sequences, no preference under type A. Art. 4.3.5 and 4.3.6 have
    nothing to say and 4.3.7 has no preference to grant, so the first-team - the one with
    the higher score, or the smaller TPN - takes the colour it did not have.
    """
    tournament = event(4, 9)
    tournament.match(1, 1, 3, ["W", "W"])       # 1 white, wins
    tournament.match(1, 2, 4, ["W", "W"])       # 2 white, wins
    engine = tournament.engine(2)
    roundpairing = engine.compute_pairing(False)
    pairs = {(pair["w"], pair["b"]): pair["colorrule"] for bracket in roundpairing for pair in bracket["pairs"]}
    assert (2, 1) in pairs                      # 1 is the first-team and had White: it gets Black
    assert pairs[(2, 1)] == "4.3.8"


# ---------------------------------------------------------------------------
# Art. 1.2 - the primary score
# ---------------------------------------------------------------------------

def test_art_1_2_match_points_and_game_points_pair_differently():
    """Art. 1.2.1 - "The rules of the competition shall state which, between match points
    and game points, is called primary score". The scoregroups are built on the primary
    score (art. 1.3.1), so the two settings pair the same tournament differently.

    Six teams of two players. Round 1: team 1 wins 2-0, team 2 wins 1.5-0.5, team 5 wins
    2-0. On match points teams 1, 2 and 5 are on 2 and are one scoregroup. On game points
    team 1 and team 5 are on 2.0 and team 2 is on 1.5, which is a scoregroup of its own,
    below them and above the 1.0 of teams 3 and 6 - and 1 and 5 are then the whole
    top-scoregroup and are paired with each other.
    """
    matchpoints = event(6, 5, primary="match")
    gamepoints = event(6, 5, primary="game")
    for tournament in (matchpoints, gamepoints):
        tournament.match(1, 1, 4, ["W", "W"])       # 1: 2 mp, 2.0 gp   4: 0 mp, 0.0 gp
        tournament.match(1, 2, 5, ["W", "D"])       # 2: 2 mp, 1.5 gp   5: 0 mp, 0.5 gp
        tournament.match(1, 3, 6, ["L", "D"])       # 6: 2 mp, 1.5 gp   3: 0 mp, 0.5 gp

    (mengine, mbrackets) = matchpoints.brackets(2)
    (gengine, gbrackets) = gamepoints.brackets(2)
    assert mengine.competitors[1]["acc"] == decimal.Decimal("2.0")     # match points
    assert gengine.competitors[1]["acc"] == decimal.Decimal("2.0")     # game points
    assert mengine.competitors[2]["acc"] == decimal.Decimal("2.0")     # 2 match points
    assert gengine.competitors[2]["acc"] == decimal.Decimal("1.5")     # 1.5 game points
    # on match points 1, 2 and 6 share the top scoregroup; on game points team 1 is alone
    # in it, and the pairings differ
    assert matchpoints.pair(2) != gamepoints.pair(2)


# ---------------------------------------------------------------------------
# Art. 3.3.3 - an impossible round-pairing
# ---------------------------------------------------------------------------

def test_art_3_3_3_an_impossible_pairing_is_reported():
    """Art. 3.3.3 - "If it is impossible to complete a round-pairing, the Chief Arbiter
    shall decide what to do". The engine cannot take that decision, so it reports the
    state and stops.

    Four teams, everybody has met everybody: there is no legal pairing left at all.
    """
    tournament = event(4, 5)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.match(2, 1, 3, ["W", "W"])
    tournament.match(2, 2, 4, ["W", "W"])
    tournament.match(3, 1, 4, ["W", "W"])
    tournament.match(3, 2, 3, ["W", "W"])
    with pytest.raises(GacruxNoLegalPairing):
        tournament.pair(4)


def test_art_3_3_3_checker_fallback_byes_the_unmatched_teams():
    tournament = event(4, 5)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.match(2, 1, 3, ["W", "W"])
    tournament.match(2, 2, 4, ["W", "W"])
    tournament.match(3, 1, 4, ["W", "W"])
    tournament.match(3, 2, 3, ["W", "W"])

    pairs = tournament.engine(4).compute_degenerate_pairing()

    assert sorted((pair["w"], pair["b"]) for pair in pairs) == [
        (1, 0), (2, 0), (3, 0), (4, 0)
    ]


# ---------------------------------------------------------------------------
# Check mode - the pairing that the tournament file already holds
# ---------------------------------------------------------------------------

def test_check_mode_reproduces_the_pairing_of_the_file():
    """pairingchecker -c reads the round that was played and decomposes it into the
    brackets it was made of, so that it can be compared with the one the engine would
    have made. The bye, the upfloaters and the brackets must come back out.
    """
    tournament = event(9, 5)
    for rnd in (1, 2):
        pairs = tournament.pair(rnd)
        for (w, b) in pairs:
            if b == 0:
                tournament.pab(rnd, w)
            else:
                tournament.match(rnd, w, b, ["W", "L"])       # every match a draw
    played = tournament.pair(3)
    for (w, b) in played:
        if b == 0:
            tournament.pab(3, w)
        else:
            tournament.match(3, w, b, ["W", "L"])

    engine = tournament.engine(3)
    analysis = engine.compute_pairing(True)                    # check mode
    checked = [
        (pair["w"], pair["b"])
        for pair in sorted(
            [pair for bracket in analysis for pair in bracket["pairs"]],
            key=lambda pair: pair["board"],
        )
    ]
    assert sorted(checked) == sorted(played)
    assert bye(checked) == bye(played)


# ---------------------------------------------------------------------------
# The invariant sweep
# ---------------------------------------------------------------------------

def can_be_paired(teams, met, memo):
    """A perfect matching of "teams" in which no two teams that have met are paired - by
    plain recursion, so that it owes nothing to the engine it is checking."""
    if len(teams) == 0:
        return True
    if teams in memo:
        return memo[teams]
    (first, rest) = (teams[0], teams[1:])
    answer = False
    for i, other in enumerate(rest):
        if (first, other) in met:
            continue
        if can_be_paired(rest[:i] + rest[i + 1:], met, memo):
            answer = True
            break
    memo[teams] = answer
    return answer


def has_legal_pairing(teams, met, byes):
    """A legal round-pairing (art. 3.3.1): every team paired but at most one, which takes
    the bye - and [C2] (art. 2.1.2) says which teams may take it."""
    memo = {}
    if len(teams) % 2 == 0:
        return can_be_paired(tuple(teams), met, memo)
    for team in teams:
        if team in byes:
            continue
        rest = tuple(other for other in teams if other != team)
        if can_be_paired(rest, met, memo):
            return True
    return False


def simulate(numteams, numrounds, seed, teamsize=2, typeb=False, primary=None, secondary=None):
    """Pair a whole tournament, round by round, drawing the results of every board with
    Gacrux's own rating model, and check every round-pairing against the absolute criteria.

    A Swiss tournament can run out of legal pairings altogether - a small field that has
    played nearly all of its round-robin does it in a completely ordinary way - and art.
    3.3.3 hands that case to the Chief Arbiter, so the engine reports it and stops. When it
    does, the sweep checks that no legal round-pairing existed: the engine may not give up
    on a round it could have paired.
    """
    statistics = drawresult(seed)
    statistics.set_team(1)
    tournament = event(numteams, numrounds, teamsize=teamsize, typeb=typeb, primary=primary, secondary=secondary)
    ratings = {team["cid"]: team["rating"] for team in tournament.tournament["competitors"]}
    allteams = list(range(1, numteams + 1))
    met = set()
    byes = set()
    rounds = 0
    for rnd in range(1, numrounds + 1):
        engine = tournament.engine(rnd)
        try:
            roundpairing = engine.compute_pairing(False)
        except GacruxNoLegalPairing:
            # art. 3.3.3 - and there really is no legal pairing left
            assert not has_legal_pairing(allteams, met, byes), f"round {rnd}: the engine gave up too early"
            break
        rounds += 1
        pairs = [pair for bracket in roundpairing for pair in bracket["pairs"]]
        teams = []
        for pair in pairs:
            (w, b) = (pair["w"], pair["b"])
            teams += [team for team in (w, b) if team > 0]
            if b == 0:
                # [C2] art. 2.1.2 - no team is given a second bye
                assert w not in byes, f"round {rnd}: team {w} took a second bye"
                byes.add(w)
                tournament.pab(rnd, w)
                continue
            # [C1] art. 2.1.1 - two teams shall not meet twice
            assert (w, b) not in met and (b, w) not in met, f"round {rnd}: {w} and {b} meet twice"
            met.add((w, b))
            met.add((b, w))
            results = []
            for board in range(1, teamsize + 1):
                (first, second) = (w, b) if board % 2 == 1 else (b, w)
                res = statistics.result(ratings[first] - board, ratings[second] - board)
                res = {"W": "W", "D": "D", "B": "L", "+": "W", "-": "L"}[res]
                results.append(res if board % 2 == 1 else REVERSE[res])
            tournament.match(rnd, w, b, results)
        # art. 3.3.1 - every team is paired, or byed, exactly once
        assert sorted(teams) == allteams, f"round {rnd}: {sorted(teams)}"
        # and no team is White and Black in the same round
        whites = [pair["w"] for pair in pairs]
        blacks = [pair["b"] for pair in pairs if pair["b"] > 0]
        assert len(set(whites) & set(blacks)) == 0
    return (tournament, rounds)


@pytest.mark.parametrize("numteams,numrounds", [(6, 5), (7, 5), (10, 7), (11, 7), (16, 7), (21, 7)])
def test_invariant_sweep_type_a(numteams, numrounds):
    """Many generated team tournaments, type A: every round-pairing is legal.

    [C1] and [C2] hold, every team is paired or byed exactly once, and the colours are
    consistent. The results of the boards are drawn with drawresult, the model Gacrux uses
    to generate its own tournaments.
    """
    for seed in range(1, 9):
        simulate(numteams, numrounds, seed)


@pytest.mark.parametrize("numteams,numrounds", [(7, 5), (12, 7), (15, 7)])
def test_invariant_sweep_type_b(numteams, numrounds):
    """The same, with the type B colour preferences of art. 1.7.2."""
    for seed in range(1, 9):
        simulate(numteams, numrounds, seed, typeb=True)


@pytest.mark.parametrize("numteams,numrounds", [(9, 7), (14, 7)])
def test_invariant_sweep_game_points_primary(numteams, numrounds):
    """The same, with game points as the primary score (art. 1.2.1)."""
    for seed in range(1, 6):
        simulate(numteams, numrounds, seed, primary="game", teamsize=4)


@pytest.mark.parametrize("seed", [3, 11, 17, 29, 101])
def test_c3_carries_a_five_team_event_through_its_whole_round_robin(seed):
    """[C3] art. 2.2.1 - "a pairing complying with all the absolute criteria shall always
    exist for all teams not yet paired".

    Five teams and five rounds: every team must meet all four others and take exactly one
    bye, and there is no room anywhere for a wrong choice. The engine has to pair every
    round without ever leaving a state it cannot pair its way out of - which is what the
    completion criterion is for, and it holds whatever the results are.
    """
    (tournament, rounds) = simulate(5, 5, seed=seed)
    assert rounds == 5
    played = {}
    for match in tournament.tournament["matchList"]:
        if match["black"] > 0:
            key = (min(match["white"], match["black"]), max(match["white"], match["black"]))
            played[key] = played.get(key, 0) + 1
    assert sorted(played.values()) == [1] * 10          # all ten pairs, once each
    byes = [match["white"] for match in tournament.tournament["matchList"] if match["black"] == 0]
    assert sorted(byes) == [1, 2, 3, 4, 5]              # and one bye each
