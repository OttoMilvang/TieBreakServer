# -*- coding: utf-8 -*-
"""
FIDE C.04.6, the Swiss Team Pairing System.

Each test names the article it holds the engine to and builds a position in which that
article, and no other, decides.

The tournaments are built by hand, in the structure the readers produce: a team
competitor holds its players, a match holds its games, and a game holds the two players
and the board. The colour of a team in a match is the colour of the player on its first
board (art. 1.6.1), which is what "white" and "black" mean in a match record.
"""
import copy
import decimal
import os

import pytest

from gacrux import chessjson, pairingfideteam, trf2json
from gacrux.crosstablefideteam import crosstable_fideteam
from gacrux.drawresult import drawresult
from gacrux.gacruxexeptions import GacruxInputError, GacruxNoLegalPairing
from gacrux.pairingfideteam import (
    NO_COLOUR,
    SECONDARY_UNSTATED,
    SECONDARY_UNUSED,
    SECONDARY_USED,
    TYPE_A,
    TYPE_B,
    pairing_fideteam,
    resolve_colour_model,
    resolve_secondary_score,
)

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

    def __init__(self, numteams, numrounds, teamsize=2, typeb=False, primary=None, secondary=None, nocolor=False,
                 topcolor="w"):
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
            "pairingSystem": pairingsystem,
            "rankOrder": ["PTS"],
            "scoreSystem": scoresystem,
            "competitors": [],
            "gameList": [],
            "matchList": [],
        }
        if topcolor is not None:
            # A record 152 states the drawing of lots of art. 4.1. topcolor=None is a file
            # that does not, which the engine has to read back out of the round played.
            self.tournament["topColor"] = topcolor
            self.tournament["topColorExplicit"] = True
        for team in range(1, numteams + 1):
            self.tournament["competitors"].append(
                {
                    "cid": team,
                    "rank": team,
                    "teamId": team,
                    "present": True,
                    "rating": { "list": "Test", "rating": 2400 - 10 * team},
                    "random": team,
                    "cplayers": [
                        {"cid": self.player(team, board), "teamId": team, "rating": { "list": "Test", "rating": 2400 - 10 * team - board}}
                        for board in range(1, teamsize + 1)
                    ],
                }
            )

    def player(self, team, board):
        return 100 * team + board

    def initial_order(self, ranks):
        """The initial order of the field (Article 2 of the General Handling Rules for
        Swiss Tournaments), given as the rank of team 1, team 2 and so on.

        By default the harness makes the rank of a team its own number, so the two orders
        agree and nothing tells them apart. The -r option of the command line pairs on the
        rank order rather than on the competitor ids of the file, and the TPN of art.
        1.1.1 is then the place of a team in THIS order.
        """
        for team, rank in enumerate(ranks, start=1):
            self.tournament["competitors"][team - 1]["rank"] = rank

    def absent(self, team):
        """A team that is not ready for pairing (Article 2.5 of the General Handling
        Rules for Swiss Tournaments: a team that has withdrawn or is not present).

        The team keeps its place in the field and its TPN - art. 1.1.3, "once defined,
        the TPN should not be modified" - it is simply left out of this round-pairing.
        """
        self.tournament["competitors"][team - 1]["present"] = False

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
                "white": { "cid": self.player(first, board), "result": fres },
                "black": { "cid": self.player(second, board), "result": sres },
                "played": True,
                "rated": True,
            }
            self.tournament["gameList"].append(game)
            games.append(game["id"])
        bpoints = self.teamsize * WIN - wpoints
        wresult = "W" if wpoints > bpoints else ("D" if wpoints == bpoints else "L")
        self.tournament["matchList"].append(
            {
                "id": 1000 + len(self.tournament["matchList"]),
                "round": rnd,
                "white": { "cid": white, "result": wresult },
                "black": { "cid": black, "result": REVERSE[wresult] },
                "played": True,
                "games": games,
            }
        )

    def pab(self, rnd, team):
        """art. 1.4 - the pairing-allocated-bye: no opponent, no colour."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": { "cid": team, "result": "P" }, "black": None,
             "played": True, "games": []}
        )

    def fullpointbye(self, rnd, team):
        """The FIDE-deprecated full-point bye: a win without playing and without opponent."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": { "cid": team, "result": "W" }, "black": None,
             "played": False, "games": []}
        )

    def halfpointbye(self, rnd, team):
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": { "cid": team, "result": "D" }, "black": None,
             "played": False, "games": []}
        )

    def forfeit(self, rnd, winner, loser):
        """A match won by forfeit: it was not played, so it gives no colour (art. 1.6.1)."""
        self.tournament["matchList"].append(
            {"id": 1000 + len(self.tournament["matchList"]), "round": rnd, "white": { "cid": winner, "result": "W" }, "black": { "cid": loser, "result": "Z" },
             "played": False, "games": []}
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
# Art. 1.1 - the Tournament Pairing Number
# ---------------------------------------------------------------------------

def test_art_1_1_1_the_tpn_is_the_place_in_the_field_not_a_count_of_the_present():
    """Art. 1.1.1 - "each team must have a different TPN, from 1 to the number of teams" -
    and art. 1.1.3 - "once defined, the TPN should not be modified ... unless the Chief
    Arbiter decides otherwise".

    Five teams, of which team 1 is absent this round. The TPN of team 3 is 3, because the
    field has five teams and team 3 is the third of them. It is not 2, which is what a
    running count over the teams that are ready for pairing would make it: art. 1.1.1
    numbers the teams of the tournament, not the teams of the round, and art. 1.1.3 says
    the number a team was given does not move when the field thins out.

    Nothing but art. 1.1 is in play here. No round has been paired, so there is no colour
    history, no score difference and no float to distract - the assertion reads the TPN
    straight off the competitor structure that the seven articles which consult it (3.4.4,
    3.5.3, 3.5.4, 3.6.1, 3.6.2, 4.2.3 and 4.3.1) all read.
    """
    tournament = event(5, 5)
    tournament.absent(1)
    engine = tournament.engine(1)
    engine.compute_pairing(False)
    competitors = engine.crosstable.competitors
    assert competitors[3]["tpn"] == 3
    assert [competitors[team]["tpn"] for team in range(1, 6)] == [1, 2, 3, 4, 5]


def test_art_1_1_3_an_absent_team_does_not_shift_the_colours_of_the_others():
    """Art. 1.1.1 and 1.1.3, seen through art. 4.3.1 - the TPN an absent team leaves
    behind is not handed to the team after it.

    Five teams, team 1 absent, so teams 2, 3, 4 and 5 play round 1. Every score is equal,
    so the bracket in TPN order is 2, 3, 4, 5 and the identifiers of art. 3.6.2 are
    "2 3 4 5" (the pairs 2-4 and 3-5) and "2 3 5 4" (the pairs 2-5 and 3-4); the
    lexicographic minimum of art. 3.6.4 is the first, so the pairs are 2-4 and 3-5.

    That is the same pairing whether the TPNs are 2,3,4,5 or the compacted 1,2,3,4 -
    compaction preserves the order, and art. 3.5 and art. 3.6 read the TPN for its order
    alone. Only art. 4.3.1 reads it for its VALUE: "if the first-team has an odd TPN, give
    it the initial-colour; otherwise, give it the opposite colour". So this position
    isolates art. 1.1 exactly - every other article that consults the TPN is neutralised
    by giving them an order they agree on, and art. 4.3.1 alone is left to report which
    numbers the teams actually hold.

    With the initial-colour White (art. 4.1) and no match played, art. 4.2.3 makes the
    first-team of each pair the smaller TPN. Team 2's TPN is 2, which is even, so it takes
    the opposite of the initial-colour and plays Black. Team 3's TPN is 3, odd, so it
    takes the initial-colour and plays White. Compacted to 1 and 2 the parities invert and
    both colours come out reversed, which is what this asserts against.
    """
    tournament = event(5, 5)
    tournament.absent(1)
    tournament.tournament["topColor"] = "w"
    assert tournament.pair(1) == [(4, 2), (3, 5)]


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


def test_art_1_7_2_fifth_paragraph_final_round_cd_zero_after_two_blacks():
    """The first paragraph of art. 1.7.2 against its fifth - the one position on which the
    two conflict. (The regulation does not number the paragraphs of art. 1.7.2; they are
    counted here.) This test records the reading the engine takes.

    The first paragraph gives a strong preference for White when CD < -1, or when CD is 0
    or -1 and the last two played matches were Black. The fifth gives no type B
    preference to a team that has yet to play a match, or whose CD is zero when pairing
    for the last round.

    A team that played W, W, B, B has a colour difference of 0 and Black in its last two
    played matches, so the first paragraph gives it a strong preference for White. Pair
    the last round, and its colour difference is zero when pairing for the last round, so
    the fifth paragraph gives it no preference at all. Both clauses fire, and they say
    opposite things.

    The engine follows the first paragraph: the clauses of art. 1.7.2 are taken in the
    order they are written, and a team's colour preference is the first definition that
    fits it, so a team that satisfies the first paragraph never reaches the fifth.
    crosstable_fideteam.color_preference tests the strong clauses first, and if the point
    is ever settled the other way this test is the one to change.

    The comparisons below pin the reading exactly: the same team one round earlier, where
    the two paragraphs agree, and a team whose CD is zero without two Blacks behind it,
    where the first paragraph does not fire and the fifth alone decides - so the assertion
    below is about the conflict alone.
    """
    assert preference(0, "wwbb", typeb=True, rnd=9, numrounds=9) == "w2"
    # not the last round: the fifth paragraph is silent and the first says the same thing
    assert preference(0, "wwbb", typeb=True, rnd=8, numrounds=9) == "w2"
    # CD zero without two Blacks behind it: the first paragraph does not fire, and in the
    # last round the fifth is the clause that decides: no preference
    assert preference(0, "wb", typeb=True, rnd=9, numrounds=9) == "nc"
    assert preference(0, "wb", typeb=True, rnd=8, numrounds=9) == "w1"
    # and type A has no such clause at all, so the last round changes nothing there
    assert preference(0, "wwbb", typeb=False, rnd=9, numrounds=9) == "w2"


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
# Art. 1.7 - which of the three colour models the competition uses
# ---------------------------------------------------------------------------

# The three colour models of art. 1.7, each with the ways the two sources name it:
#   mtoken  the token "-m" writes into the pairing system: -m fideteam-typeb -> "typeb"
#   rtoken  the token the record 192 table of trf2json writes into it: "team_typeb"
#   code    the record 192 code resolve_colour_model reads the model from, or None when
#           none does - it reads TYPEA and TYPEB only
#   typeb / usecolor  the two questions the crosstable asks of the model
COLOUR_MODELS = [
    ("typea",   "typea",   "team_typea", "FIDE_TEAM_TYPEA_MP_GP", False, True),
    ("typeb",   "typeb",   "team_typeb", "FIDE_TEAM_TYPEB_MP_GP", True,  True),
    ("nocolor", "nocolor", "nocolor",    None,                    False, False),
]

TYPE_A_MODEL = (False, True)


def colour_model_engine(tokens, code):
    """An engine whose pairing system carries "tokens" and whose record 192 code is
    "code" - the two places art. 1.7's model can reach the engine from."""
    tournament = event(4, 5)
    tournament.tournament["pairingSystem"] = ["fideteam"] + list(tokens)
    tournament.tournament["tournamentInfo"] = {"typeOfTournament": code}
    return tournament.engine(1)


@pytest.mark.parametrize("model,mtoken,rtoken,code,typeb,usecolor", COLOUR_MODELS)
def test_art_1_7_each_source_names_the_colour_model_on_its_own(model, mtoken, rtoken, code, typeb, usecolor):
    """Art. 1.7 - "Type A colour preferences are used unless the rules of the team
    competition specify Type B, or no colour preferences at all."

    Three models, and two places the rules of the competition can reach the engine from: a
    token in the pairing system - which is where both the -m option and the record 192
    table of trf2json put it, in two different spellings - and the record 192 code of the
    file. Whichever source names a model, the whole model must come out of it.

    The engine asks two questions of the model - "type B?" and "colour preferences at
    all?" - and reading each of them from its own source is what lets a model be applied
    by halves. Here each source is given alone, and each must answer both.

    resolve_colour_model reads only TYPEA and TYPEB from the record 192 code, so a code
    that names neither, FIDE_TEAM_MP_GP say, falls to the type A default of art. 1.7's
    first sentence when it reaches the resolver alone. A file read by trf2json does not
    get there: its record 192 table turns a score-only code into the "nocolor" token of
    the pairing system before the resolver sees it.

    Nothing else is exercised: the engines are built and their model read, without pairing
    a round, so no scoregroup, no upfloater and no colour allocation is involved.
    """
    for token in (mtoken, rtoken):
        engine = colour_model_engine([token], "")
        assert (engine.typeb, engine.usecolor) == (typeb, usecolor), (model, token)
    expected = (typeb, usecolor) if code is not None else TYPE_A_MODEL
    engine = colour_model_engine([], code or "FIDE_TEAM_MP_GP")
    assert (engine.typeb, engine.usecolor) == expected, (model, code)


def test_art_1_7_the_resolver_names_one_model_for_the_whole_engine():
    """Art. 1.7 - the resolver itself, stated as the three models it can return.

    pairing_fideteam asks two questions of the colour model and the crosstable acts on
    both, so the two have to be answers to one question asked once. resolve_colour_model
    is that question; this pins its three answers and the precedence between its two
    sources, without an engine in the way.
    """
    assert resolve_colour_model(["fideteam", "typea"], "") == TYPE_A
    assert resolve_colour_model(["fideteam", "team_typea"], "") == TYPE_A
    assert resolve_colour_model(["fideteam", "typeb"], "") == TYPE_B
    assert resolve_colour_model(["fideteam", "team_typeb"], "") == TYPE_B
    assert resolve_colour_model(["fideteam", "nocolor"], "") == NO_COLOUR
    # the record 192 code, read only when the pairing system names no model
    assert resolve_colour_model(["fideteam"], "FIDE_TEAM_TYPEA_MP_GP") == TYPE_A
    assert resolve_colour_model(["fideteam"], "FIDE_TEAM_TYPEB_MP_BAKU") == TYPE_B
    # and art. 1.7's own default when neither source names one
    assert resolve_colour_model(["fideteam"], "") == TYPE_A
    assert resolve_colour_model([], "") == TYPE_A
    # a code that is not a C.04.6 team code states nothing about art. 1.7
    assert resolve_colour_model(["fideteam"], "CUSTOM_TEAM_SWISS_MP") == TYPE_A
    # and the pairing system wins over the code whenever it names a model
    assert resolve_colour_model(["fideteam", "typea"], "FIDE_TEAM_TYPEB_MP_GP") == TYPE_A
    assert resolve_colour_model(["fideteam", "nocolor"], "FIDE_TEAM_TYPEB_MP_GP") == NO_COLOUR


@pytest.mark.parametrize("model,mtoken,rtoken,code,typeb,usecolor", COLOUR_MODELS)
def test_art_1_7_a_named_colour_model_wins_over_the_code_of_the_file(model, mtoken, rtoken, code, typeb, usecolor):
    """Art. 1.7, and the precedence between the two sources that can name the model.

    The -m option replaces the pairing system of the tournament outright and does not
    touch the record 192 code, so a file paired with a model on the command line carries
    two statements of the model and they need not agree. The model the caller named is the
    one in the pairing system, and it decides; the code of the file is read only when the
    pairing system names no model at all.

    If the two questions were read from separate sources, both statements would apply at
    once: a file whose code says type B, paired with -m fideteam-typea, would keep the
    type B preferences that the flag was supposed to replace, and -m fideteam-nocolor on
    the same file would switch the preferences off while leaving them type B underneath.

    Again nothing but art. 1.7 is exercised: the models are read off freshly built engines.
    """
    for othercode in ["", "FIDE_TEAM_TYPEA_MP_GP", "FIDE_TEAM_TYPEB_MP_GP", "FIDE_TEAM_MP_GP"]:
        for token in (mtoken, rtoken):
            engine = colour_model_engine([token], othercode)
            assert (engine.typeb, engine.usecolor) == (typeb, usecolor), (model, token, othercode)


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


def test_art_2_1_1_c1_is_absolute_and_allows_one_meeting():
    """[C1] art. 2.1.1: "two participants shall not play against each other more than
    once".

    The pairing class reads a maxMeets limit, which the -K option and a "double" in the
    method list raise, so that a double round-robin run through the Swiss engine may
    pair the same two players twice. C.04.6 has no such variant: art. 2.1.1 is an
    absolute criterion of a Swiss team tournament, and the number it allows is one.

    Two teams, two rounds, and the file asks for two meetings. They played each other in
    round 1, so [C1] leaves round 2 with no legal pairing at all, and art. 3.3.3 hands
    that to the Chief Arbiter - which is what the engine reports. What it must not do is
    pair the rematch.

    The position is the smallest one there is: with two teams there is no scoregroup to
    choose from, no upfloater to select and no bye to assign ([C2] art. 2.1.2 never comes
    up, the field being even), so [C1] is the only criterion that can decide anything.
    """
    tournament = event(2, 2)
    tournament.tournament["maxMeets"] = 2       # -K 2, or a "double" in the method list
    tournament.match(1, 1, 2, ["W", "L"])
    engine = tournament.engine(2)
    assert engine.nummeets == 1
    with pytest.raises(GacruxNoLegalPairing):
        engine.compute_pairing(False)


def test_art_2_1_2_c2_no_second_pairing_allocated_bye():
    """[C2] art. 2.1.2 - a team that has already received the bye shall not receive it again.

    The same shape as the forfeit test below: team 7 had the bye of round 1 and lost its
    two matches since, so it comes into round 4 strictly lowest (1 match point against 3
    or more) with the largest TPN. Teams 6 and 5 had the byes of rounds 2 and 3. Of the
    candidates 1 to 4, teams 3 and 4 have the lower score, 3 match points, and 4 the
    larger TPN.

    Only team 7's earlier bye keeps the bye away from it, and the engine bars it twice:
    [C2] in update_canmeet, and the meeting count, which holds the round 1 bye as a
    meeting with competitor 0, so the one meeting [C1] allows removes that edge as well.
    Take out both and the bye is team 7's.
    """
    tournament = event(7, 5)
    tournament.pab(1, 7)                        # 7 -> 1 mp, the match points of a draw
    tournament.match(1, 1, 2, ["W", "L"])       # drawn: 1 mp each
    tournament.match(1, 3, 4, ["W", "L"])
    tournament.match(1, 5, 6, ["W", "L"])
    tournament.match(2, 1, 7, ["W", "W"])       # 1 -> 3, 7 stays on 1
    tournament.match(2, 2, 3, ["W", "L"])       # 2 -> 2, 3 -> 2
    tournament.match(2, 4, 5, ["W", "L"])       # 4 -> 2, 5 -> 2
    tournament.pab(2, 6)                        # 6 -> 2
    tournament.match(3, 2, 7, ["W", "W"])       # 2 -> 4, 7 stays on 1
    tournament.match(3, 1, 3, ["W", "L"])       # 1 -> 4, 3 -> 3
    tournament.match(3, 4, 6, ["W", "L"])       # 4 -> 3, 6 -> 3
    tournament.pab(3, 5)                        # 5 -> 3
    engine = tournament.engine(4)
    engine.compute_pairing(False)
    scores = {team: engine.competitors[team]["pts"] for team in range(1, 8)}
    assert scores[7] < min(scores[team] for team in range(1, 7))      # strictly lowest
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[7])
    pairs = [(pair["w"], pair["b"]) for bracket in engine.roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) != 7
    assert bye(pairs) == 4


def test_art_2_1_2_c2_no_bye_after_a_forfeit_win():
    """[C2] art. 2.1.2 - nor shall a team that has won a match by forfeit.

    Seven teams, round 4 to be paired. Team 7 won round 1 by forfeit over team 1 and lost
    its two played matches since, so it comes into round 4 strictly lowest, on 2 match
    points, with the largest TPN: art. 3.4.2 and 3.4.4 point at it. Only the forfeit win
    bars it. Teams 6, 5 and 4 had the byes of rounds 1, 2 and 3, so the candidates are 1,
    2 and 3, all on 3 match points; 2 and 3 have played three matches to team 1's two
    (art. 3.4.3), and 3 has the larger TPN (art. 3.4.4).

    Without [C2] the bye is team 7's - which is what this test fails with when the
    criterion is taken out of update_canmeet.
    """
    tournament = event(7, 5)
    tournament.forfeit(1, 7, 1)                 # 7 wins by forfeit: 2 mp, no match played
    tournament.match(1, 2, 3, ["W", "L"])       # drawn: 1 mp each
    tournament.match(1, 4, 5, ["W", "L"])
    tournament.pab(1, 6)                        # 6 -> 1
    tournament.match(2, 1, 7, ["W", "W"])       # 1 -> 2, 7 stays on 2
    tournament.match(2, 2, 6, ["W", "L"])       # 2 -> 2, 6 -> 2
    tournament.match(2, 3, 4, ["W", "L"])       # 3 -> 2, 4 -> 2
    tournament.pab(2, 5)                        # 5 -> 2
    tournament.match(3, 5, 7, ["W", "W"])       # 5 -> 4, 7 stays on 2
    tournament.match(3, 1, 2, ["W", "L"])       # 1 -> 3, 2 -> 3
    tournament.match(3, 3, 6, ["W", "L"])       # 3 -> 3, 6 -> 3
    tournament.pab(3, 4)                        # 4 -> 3
    engine = tournament.engine(4)
    engine.compute_pairing(False)
    scores = {team: engine.competitors[team]["pts"] for team in range(1, 8)}
    assert scores[7] < min(scores[team] for team in range(1, 7))      # strictly lowest
    assert engine.competitors[7]["num"]["val"] == 2                    # the forfeit was not played
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[7])
    assert not engine.crosstable.had_bye_or_forfeit_win(engine.competitors[1])
    pairs = [(pair["w"], pair["b"]) for bracket in engine.roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) != 7
    assert bye(pairs) == 3


def test_art_2_1_2_c2_no_bye_after_a_full_point_bye():
    """[C2] art. 2.1.2 - "(or been given a FIDE-deprecated full-point bye)".

    The same shape as the forfeit test: team 7 was given a full-point bye in round 1 and
    lost its two matches since, so it is strictly lowest before round 4 (2 match points
    against 3 or more) and has the largest TPN. Teams 6 and 5 had the byes of rounds 2
    and 3. Of the candidates 1 to 4, teams 3 and 4 have the lower score, 3 match points,
    and 4 the larger TPN.

    Without [C2] the bye is team 7's.
    """
    tournament = event(7, 5)
    tournament.fullpointbye(1, 7)               # 7 -> 2 mp, no match played
    tournament.match(1, 1, 2, ["W", "L"])       # drawn: 1 mp each
    tournament.match(1, 3, 4, ["W", "L"])
    tournament.match(1, 5, 6, ["W", "L"])
    tournament.match(2, 1, 7, ["W", "W"])       # 1 -> 3, 7 stays on 2
    tournament.match(2, 2, 3, ["W", "L"])       # 2 -> 2, 3 -> 2
    tournament.match(2, 4, 5, ["W", "L"])       # 4 -> 2, 5 -> 2
    tournament.pab(2, 6)                        # 6 -> 2
    tournament.match(3, 2, 7, ["W", "W"])       # 2 -> 4, 7 stays on 2
    tournament.match(3, 1, 3, ["W", "L"])       # 1 -> 4, 3 -> 3
    tournament.match(3, 4, 6, ["W", "L"])       # 4 -> 3, 6 -> 3
    tournament.pab(3, 5)                        # 5 -> 3
    engine = tournament.engine(4)
    engine.compute_pairing(False)
    scores = {team: engine.competitors[team]["pts"] for team in range(1, 8)}
    assert scores[7] < min(scores[team] for team in range(1, 7))      # strictly lowest
    assert engine.crosstable.had_bye_or_forfeit_win(engine.competitors[7])
    pairs = [(pair["w"], pair["b"]) for bracket in engine.roundpairing for pair in bracket["pairs"]]
    assert bye(pairs) != 7
    assert bye(pairs) == 4


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


def test_art_2_1_2_c2_check_mode_names_a_second_bye():
    """[C2] art. 2.1.2 in check mode.

    A check reproduces the round the file declares, so its crosstable keeps the declared
    bye even where [C2] would have removed the edge when pairing. find_pab then flags the
    bracket, so the criterion the file broke can be named.

    Round 2 gives team 5 the bye it already had in round 1. The same round with the bye
    on team 4, which is entitled to it, carries no flag.
    """
    tournament = event(5, 3)
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 4, ["W", "W"])
    tournament.pab(1, 5)
    tournament.match(2, 1, 3, ["W", "W"])
    tournament.match(2, 2, 4, ["W", "W"])
    tournament.pab(2, 5)                        # the second bye [C2] forbids
    engine = tournament.engine(2)
    brackets = engine.compute_pairing(True)
    pab = [bracket for bracket in brackets if bracket.get("pab")]
    assert len(pab) == 1
    assert pab[0]["competitors"] == [5]         # reproduced as declared
    assert "team 5" in pab[0]["c2"]
    assert "2.1.2" in pab[0]["c2"]

    entitled = event(5, 3)
    entitled.match(1, 1, 2, ["W", "W"])
    entitled.match(1, 3, 4, ["W", "W"])
    entitled.pab(1, 5)
    entitled.match(2, 1, 3, ["W", "W"])
    entitled.match(2, 2, 5, ["W", "W"])
    entitled.pab(2, 4)
    engine = entitled.engine(2)
    brackets = engine.compute_pairing(True)
    pab = [bracket for bracket in brackets if bracket.get("pab")]
    assert pab[0]["competitors"] == [4]
    assert "c2" not in pab[0]


# ---------------------------------------------------------------------------
# Art. 3.4 - the pairing-allocated-bye
# ---------------------------------------------------------------------------

def test_art_1_4_only_one_bracket_is_the_pairing_allocated_bye():
    """Art. 1.4 - "should the number of teams to be paired be odd, ONE team is not paired.
    This team receives a pairing-allocated-bye" - and art. 3.3.2, which makes assigning it
    step 1 of the round-pairing, ahead of the brackets.

    The bye is therefore a bracket of its own, holding the one team art. 3.4 chose, and it
    is the only bracket of the round that is the bye. The scoregroup the byed team came
    from is a bracket like any other: it pairs the teams that are left in it, and it does
    not hold the bye.

    Five teams in round 1. Every team has the same score, so the byed team's scoregroup is
    also the scoregroup being paired - the one position in which "the bracket of the byed
    team's score" and "the bracket that is the bye" can be confused with each other. Art.
    3.4 gives the bye to team 5 (art. 3.4.2 and 3.4.3 tie, art. 3.4.4 takes the largest
    TPN) and the remaining four teams are paired in their own bracket.
    """
    tournament = event(5, 5)
    (engine, brackets) = tournament.brackets(1)
    byebrackets = [bracket for bracket in brackets if bracket["pab"]]
    assert len(byebrackets) == 1
    assert byebrackets[0]["competitors"] == [5]
    assert [(pair["w"], pair["b"]) for pair in byebrackets[0]["pairs"]] == [(5, 0)]
    # and the scoregroup bracket that the byed team came from is an ordinary bracket
    level = engine.competitors[5]["scorelevel"]
    assert quality(brackets, level, "QC8") == 0
    assert upfloaters(brackets, level) == []


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


def test_art_3_4_2_the_bye_is_chosen_on_the_pairing_score_under_baku():
    """Art. 3.4.2 - "has the lowest score" - is read on the pairing score of C.04.7 art.
    1.5, the standings points plus the virtual points of the acceleration.

    The bye is the first step of the pairing process (art. 3.3.2 step 1), taken on the
    same scoregroups the rest of the process then pairs, and those are formed on the
    pairing score (art. 1.3.1, C.04.7 art. 1.5). Every other bare "score" of C.04.6 is
    read that way here - the floaters of art. 1.5 and the potential upfloaters of art.
    3.5.1 - and the Dutch engine assigns its bye on the same score
    (crosstable_dutch.compute_pab_weight). Nothing in art. 3.4 singles the bye out.

    Baku gives team 1 two virtual match points, so its pairing score is 2 while its
    standings score is 0; teams 2 to 5 took a half-point bye in round 1 and have 1 point
    on both counts. On the standings score team 1 would be lowest and take the bye; on
    the pairing score it is highest, and the bye goes to the largest TPN among the four
    teams on 1 point (art. 3.4.4), team 5.
    """
    tournament = event(5, 3)
    tournament.tournament["accelerated"] = {
        "name": "BAKU2016",
        "values": [{
            "matchPoints": decimal.Decimal("2.0"),
            "gamePoints": decimal.Decimal("1.0"),
            "firstRound": 1,
            "lastRound": 3,
            "firstCompetitor": 1, "lastCompetitor": 1,
        }],
    }
    for team in range(2, 6):
        tournament.halfpointbye(1, team)

    engine = tournament.engine(2)
    roundpairing = engine.compute_pairing(False)
    pairs = [(pair["w"], pair["b"]) for bracket in roundpairing for pair in bracket["pairs"]]
    assert engine.competitors[1]["pts"] < engine.competitors[2]["pts"]              # standings
    assert engine.competitors[1]["scorelevel"] > engine.competitors[2]["scorelevel"]  # pairing
    assert bye(pairs) == 5


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
    of them that qualifies - so it is the order that decides which set is chosen. The sets
    are yielded one at a time rather than collected, so the order has to be the order they
    come out in; listing them here is what checks that.
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


def test_art_3_5_4_the_sets_are_produced_one_at_a_time_in_that_order(monkeypatch):
    """Art. 3.5.4 and 3.5.5 - "the sets are sorted among themselves by the lexicographic
    order of their TPNs", and the set to take is the FIRST one that complies.

    The regulation is a "first that applies" rule, so the sets it asks for are a
    sequence to walk in order. The order is fixed and each set is the successor of the
    one before it, so the engine never needs the whole sequence in hand: a bracket whose
    first candidate set complies has to build one set.

    A bracket of a 60-team event that needs two upfloaters from a lower scoregroup of 20
    has C(20,2) = 190 sets; one that needs ten of them has C(20,10) = 184 756, and every
    one of them costs a matching to test.

    This asserts the order and the laziness together, with ten upfloaters out of twenty
    candidates of one score. The first set is teams 1 to 10 - the lexicographic minimum
    of art. 3.5.4 - and it costs exactly one combination to produce, the second costs
    exactly one more. The count is of tuples actually drawn from itertools.combinations.

    Nothing but art. 3.5.3 and 3.5.4 is exercised: list_upfloaters reads a score level and
    a pairing number from each candidate and nothing else, so the candidates here are
    given as exactly that, with no result, colour or opponent to interact with.
    """
    engine = event(4, 5).engine(1)
    lower = [{"cid": cid, "rnk": cid, "scorelevel": 1} for cid in range(1, 21)]
    profile = (1,) * 10                                   # ten upfloaters of one score

    drawn = [0]
    combinations = pairingfideteam.combinations

    def counting(candidates, take):
        for chosen in combinations(candidates, take):
            drawn[0] += 1
            yield chosen

    monkeypatch.setattr(pairingfideteam, "combinations", counting)

    sets = iter(engine.list_upfloaters(lower, profile))
    assert [node["cid"] for node in next(sets)] == list(range(1, 11))
    assert drawn[0] == 1                                  # out of 184 756
    assert [node["cid"] for node in next(sets)] == list(range(1, 10)) + [11]
    assert drawn[0] == 2


def test_art_3_5_3_a_set_is_sorted_by_descending_score_then_ascending_tpn():
    """Art. 3.5.3 - within a set, the upfloaters are sorted by descending score first.

    {2, 6, 1} is 2 and 6 (3 points) and then 1 (2.5 points) - not 1, 2, 6. That is what
    makes {2,6,5} come before {2,8,1} in art. 3.5.4: the comparison is on the sequence.
    """
    engine = event(8, 5).engine(2)
    lower = [{"cid": cid, "rnk": cid, "scorelevel": 3 if cid in (2, 6, 8) else 2} for cid in (1, 2, 3, 5, 6, 8)]
    first = next(iter(engine.list_upfloaters(lower, (3, 3, 2))))
    assert [node["cid"] for node in first] == [2, 6, 1]
    assert [node["scorelevel"] for node in first] == [3, 3, 2]


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


def test_art_2_3_1_c4_counts_the_upfloaters_and_not_the_pairs_that_hold_them():
    """[C4] art. 2.3.1 - "minimise the number of upfloaters".

    The criterion counts teams. A pair of a resident and an upfloater holds one upfloater;
    a pair of two upfloaters holds two, not one, and a pair of two residents holds none.
    Art. 1.3.2 says which is which: a bracket is "resident teams from the same scoregroup
    and (possibly) upfloaters from lower scoregroups", so a team of the bracket is an
    upfloater exactly when its score is below the score of the bracket - which is a
    property of the team and the bracket, and not of the two teams of a pair compared with
    each other.

    The position is the one of test_art_3_6_1_a_heterogeneous_bracket_is_read_in_tpn_order:
    the bracket at the 1 MP scoregroup has the residents 5 and 9 and the upfloaters 2 and
    7, both of which come from the 0 MP scoregroup, so the two upfloaters have the same
    score as each other and a different one from the bracket.

    The pair 2-7 is one of the pairs of that bracket - art. 3.6 weighed it as a candidate,
    and rejected it because 5 and 9 have met and cannot take the other half of that
    pairing. It holds two of the bracket's upfloaters and is worth 2 to [C4]. Comparing
    the two teams with each other instead makes it worth 0, because they are level with
    one another; comparing two upfloaters of DIFFERENT scores that way makes it worth 1.
    Neither is the number of upfloaters in the pair.

    Nothing else is being measured. [C5] (art. 2.3.2) is about the score differences of
    the pairs and is read off the same edge without being asserted on here; [C7] and [C10]
    (art. 2.3.4, 2.3.7) are zero throughout, because round 1 paired equal scores and left
    no floaters; and [C8] and [C9] (art. 2.3.5, 2.3.6) are zero because no team has a type
    A colour preference after a single match.
    """
    tournament = event(10, 5)
    tournament.match(1, 5, 9, ["W", "L"])       # drawn: teams 5 and 9 have met
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 7, ["W", "W"])
    tournament.match(1, 4, 8, ["W", "W"])
    tournament.match(1, 6, 10, ["W", "W"])
    (engine, brackets) = tournament.brackets(2)
    level = engine.competitors[5]["scorelevel"]
    assert upfloaters(brackets, level) == [2, 7]
    assert engine.competitors[2]["scorelevel"] == engine.competitors[7]["scorelevel"] < level

    # the bracket as it was paired: one upfloater in each of its two pairs
    assert quality(brackets, level, "QC4") == 2
    assert engine.opponents[2][9]["quality"]["QC4"] == 1
    assert engine.opponents[5][7]["quality"]["QC4"] == 1
    # and the candidate pair that holds both of them, weighed in the same bracket
    assert engine.opponents[2][7]["quality"]["QC4"] == 2
    # (the pair 5-9 is not weighed at all: [C1] removed it from the bracket. A pair of two
    # residents that IS weighed - 1 and 3, in the 2 MP bracket above - holds none.)
    assert engine.opponents[1][3]["quality"]["QC4"] == 0


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


def test_art_2_3_3_c6_has_nothing_to_ask_when_the_bye_emptied_the_following_scoregroup():
    """[C6] art. 2.3.3 - "unless all the teams in the following scoregroup became or are
    upfloaters (thus this scoregroup is now empty)".

    The carve-out names upfloaters, but a scoregroup can also be emptied by the bye: art.
    1.4 says the byed team "is not paired", so it is no longer among the teams [C6] asks to
    be paired, and a scoregroup with nobody left in it has no bracket in which [C1], [C3]
    and [C4] could be complied with. The criterion then has nothing to ask and passes -
    see check_c6.

    Seven teams before round 4: 1 and 2 on 6 match points, 4 on 4, 7 on 2, and 3, 5 and 6
    on 1 with a bye each ([C2]). The bye goes to team 7, the lowest score that may take it,
    and the scoregroup below team 4's is then empty. Team 4's bracket takes one upfloater
    from the scoregroup below that and reports [C6] as complied with.
    """
    tournament = event(7, 5)
    tournament.pab(1, 5)
    tournament.match(1, 7, 6, ["W", "W"])
    tournament.match(1, 1, 3, ["W", "W"])
    tournament.match(1, 2, 4, ["W", "W"])
    tournament.pab(2, 6)
    tournament.match(2, 1, 7, ["W", "W"])
    tournament.match(2, 2, 3, ["W", "W"])
    tournament.match(2, 4, 5, ["W", "W"])
    tournament.pab(3, 3)
    tournament.match(3, 1, 5, ["W", "W"])
    tournament.match(3, 2, 6, ["W", "W"])
    tournament.match(3, 4, 7, ["W", "W"])
    (engine, brackets) = tournament.brackets(4)
    pairs = [(pair["w"], pair["b"]) for bracket in brackets for pair in bracket["pairs"]]
    assert bye(pairs) == 7
    level = engine.competitors[4]["scorelevel"]
    # the scoregroup right below team 4's holds the byed team and nobody else
    assert [team for team in range(1, 8) if engine.competitors[team]["scorelevel"] == level - 1] == [7]
    assert upfloaters(brackets, level) == [3]
    assert quality(brackets, level, "QC6") == 0


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


def test_art_2_3_4_c7_cannot_be_evaluated_without_a_round_count():
    """[C7] art. 2.3.4 and [C10] art. 2.3.7 are defined by "the last two rounds", and a
    file that does not declare its round count cannot say which those are.

    The same position with the count only inferred: two rounds played, no record 142, so
    trf2json leaves numRounds at 2 and marks it as not explicit. Pairing round 3 on that
    would switch [C7] off and upfloat team 2, the previous-round floater. The round is
    refused instead, naming the record, the flag and the article.
    """
    tournament = c7_tournament(2)
    tournament.tournament["numRoundsExplicit"] = False
    with pytest.raises(GacruxInputError) as excinfo:
        tournament.engine(3)
    message = str(excinfo.value)
    assert "142" in message
    assert "2.3.4" in message
    assert "-N" in message


def test_art_2_3_4_c7_applies_when_record_142_says_the_event_continues():
    """The control: the same two rounds under a declared six, so round 3 is not one of the
    last two and [C7] keeps team 2 out of the bracket."""
    tournament = c7_tournament(6)
    tournament.tournament["numRoundsExplicit"] = True
    (engine, brackets) = tournament.brackets(3)
    assert not engine.lasttworounds
    top = engine.competitors[1]["scorelevel"]
    assert upfloaters(brackets, top) == [3]


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


def test_art_2_3_4_and_2_3_7_count_both_upfloaters_in_one_pair():
    """A bracket pair may contain two upfloaters, and both criteria count teams.

    Teams 2 and 3 are below this bracket's score level and both floated in the previous
    round. Their pair therefore contributes two to [C7]. Each is also the other
    upfloater's previously-floated opponent, so it contributes two to [C10].

    The edge weights show the ordering inside this candidate bracket. Teams 1 and 4 are
    residents that did not float. The identifier of art. 3.6.2 prefers 1-4, 2-3, but
    [C10] comes first and makes the two cross-pairs 1-2, 3-4 better. The outer [C4]
    search prevents a selected bracket from pairing two of its own upfloaters: dropping
    that pair would leave a legal round with two fewer. The hand-built bracket is useful
    here because the edge-quality checker still has to report every criterion correctly.
    """
    engine = crosstable_fideteam([], False, False, lasttworounds=False)   # [C7], [C10] apply
    engine.scorelevel = 2
    engine.maxpsd = 2
    engine.BLOB = 5
    engine.competitors = [
        None,
        {"cid": 1, "tpn": 1, "scorelevel": 2, "flt": 0, "cop": "nc"},
        {"cid": 2, "tpn": 2, "scorelevel": 1, "flt": 1, "cop": "nc"},
        {"cid": 3, "tpn": 3, "scorelevel": 1, "flt": 2, "cop": "nc"},
        {"cid": 4, "tpn": 4, "scorelevel": 2, "flt": 0, "cop": "nc"},
    ]

    def edge(a, b):
        return {
            "ca": a,
            "cb": b,
            "canmeet": True,
            "qlevel": -1,
            "quality": None,
            "weight": 0,
        }

    edges = [edge(a, b) for a in range(1, 5) for b in range(a + 1, 5)]
    engine.update_bracket(2, engine.competitors[1:], edges)
    by_pair = {(item["ca"], item["cb"]): item for item in edges}

    together = by_pair[(2, 3)]["quality"]
    assert together["QC5"] == [0, 2]
    assert together["QC7"] == 2
    assert together["QC10"] == 2
    assert (
        by_pair[(1, 4)]["weight"] + by_pair[(2, 3)]["weight"]
        > by_pair[(1, 2)]["weight"] + by_pair[(3, 4)]["weight"]
    )


# ---------------------------------------------------------------------------
# Art. 2.3.5 / 2.3.6 - the colour criteria
# ---------------------------------------------------------------------------

def test_art_2_3_5_c8_minimise_the_unfulfilled_colour_preferences():
    """[C8] art. 2.3.5 - minimise the number of teams whose colour preference is not
    fulfilled.

    Four teams on 4 match points. 1 and 2 have played White twice (a preference for Black
    under both types), 3 and 4 have played Black twice (a preference for White). Pairing
    1-2 and 3-4 would leave two preferences unfulfilled; pairing 1 and 2 against 3 and 4
    leaves none, and [C8] says so. The identifier of art. 3.6.2 asks for the same pairing
    here - "1 2 3 4" for 1-3 2-4 against "1 3 2 4" for 1-2 3-4 - so this position pins
    what [C8] counts, not that it comes first (art. 3.6.4); simple_preferences below is
    the position in which [C8] overrides the identifier.
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


def simple_preferences(nocolor):
    """Eight teams again, and 1 to 4 have won every match without meeting each other: a
    bracket of four before round 3.

    1 and 3 played Black twice and 2 and 4 played White twice, so art. 1.7.1 gives 1 and 3
    a preference for White and 2 and 4 a preference for Black - simple preferences, the
    ones type A has. With "colour preferences ... not to be used at all" (art. 1.7) the
    same four teams have none.
    """
    tournament = event(8, 6, nocolor=nocolor)
    tournament.match(1, 5, 1, ["L", "L"])       # 1 Black, and wins
    tournament.match(1, 2, 6, ["W", "W"])       # 2 White
    tournament.match(1, 7, 3, ["L", "L"])       # 3 Black
    tournament.match(1, 4, 8, ["W", "W"])       # 4 White
    tournament.match(2, 6, 1, ["L", "L"])       # 1 Black again -> cd -2 -> White
    tournament.match(2, 2, 5, ["W", "W"])       # 2 White again -> cd +2 -> Black
    tournament.match(2, 8, 3, ["L", "L"])       # 3 Black again -> cd -2 -> White
    tournament.match(2, 4, 7, ["W", "W"])       # 4 White again -> cd +2 -> Black
    return tournament


def test_art_1_7_no_colour_preferences_pair_the_position_differently_from_type_a():
    """Art. 1.7 - "or colour preferences are not to be used at all", in the pairing.

    The bracket is 1, 2, 3, 4. Under type A, 1 and 3 want White and 2 and 4 want Black, so
    1-3 2-4 leaves two teams unserved and costs [C8] = 2 while 1-4 2-3 costs nothing: art.
    2.3.5 rejects the pairing that the identifier of art. 3.6.2 would otherwise have taken
    first, and the bracket is paired 1-4 2-3.

    With no colour preferences at all, nobody wants anything, [C8] costs nothing whatever
    the pairing is, and the identifier decides alone: 1-3 2-4, the identifier "1 2 3 4"
    against "1 2 4 3".
    """
    (enginea, bracketsa) = simple_preferences(nocolor=False).brackets(3)
    (enginen, bracketsn) = simple_preferences(nocolor=True).brackets(3)
    assert [enginea.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["w2", "b2", "w2", "b2"]
    assert [enginen.competitors[team]["cop"] for team in (1, 2, 3, 4)] == ["nc", "nc", "nc", "nc"]
    assert sorted(sorted(pair) for pair in bracket_pairs(bracketsa, {1, 2, 3, 4})) == [[1, 4], [2, 3]]
    assert sorted(sorted(pair) for pair in bracket_pairs(bracketsn, {1, 2, 3, 4})) == [[1, 3], [2, 4]]


def test_art_2_3_5_c8_is_inert_when_colour_preferences_are_not_used():
    """[C8] art. 2.3.5 - "minimise the number of teams whose colour preference is not
    fulfilled" has nothing to minimise when art. 1.7 asks for no colour preferences.

    In the position of simple_preferences the criterion is what separates the candidate
    pairings under type A: 1-3 2-4 costs 2 and the other two cost nothing. Without colour
    preferences every candidate costs 0, so [C8] can no longer reject anything, and the
    pairing that type A refuses is the one the bracket is given.
    """
    (enginea, _) = simple_preferences(nocolor=False).brackets(3)
    (enginen, bracketsn) = simple_preferences(nocolor=True).brackets(3)
    candidates = [[(1, 3), (2, 4)], [(1, 4), (2, 3)], [(1, 2), (3, 4)]]

    def weight(engine, candidate):
        edges = [engine.opponents[a][b] for (a, b) in candidate]
        return engine.crosstable.compute_weight(edges, None)["QC8"]

    assert [weight(enginea, candidate) for candidate in candidates] == [2, 0, 0]
    assert [weight(enginen, candidate) for candidate in candidates] == [0, 0, 0]
    top = enginen.competitors[1]["scorelevel"]
    assert quality(bracketsn, top, "QC8") == 0


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


def test_art_3_6_1_a_heterogeneous_bracket_is_read_in_tpn_order():
    """Art. 3.6.1 - "the team with the smaller TPN is the top member of the pair" - and
    art. 3.6.2, which builds the identifier of a pairing out of those positions.

    The order the bracket is read in is the TPN order, and only the TPN order. The
    residents of a heterogeneous bracket do not come first because they are residents:
    art. 3.6 knows nothing about which team upfloated into the bracket, and an upfloater
    with a small TPN is a top member ahead of a resident with a large one.

    Ten teams, five rounds. Round 1: 5 v 9 is drawn, and 1, 3, 4 and 6 win their matches.
    Going into round 2 the scoregroups are {1,3,4,6} on 2 MP, {5,9} on 1 MP and
    {2,7,8,10} on 0. The 2 MP bracket pairs inside itself; teams 5 and 9 are the whole
    1 MP scoregroup and have already met, so [C1] (art. 2.1.1) forbids the only pairing
    the scoregroup has of its own and art. 3.5 brings up the lexicographically first legal
    set of two upfloaters, {2, 7}. The bracket is therefore residents 5 and 9 with
    upfloaters 2 and 7, and its only barred pair is 5-9.

    Two pairings remain, and art. 3.6.2 separates them. Read in TPN order the bracket is
    2, 5, 7, 9, giving the positions 2->1, 5->2, 7->3, 9->4, so

        {2-9, 5-7}   identifier "2 5 9 7"
        {2-5, 7-9}   identifier "2 7 5 9"

    and "2 5 9 7" is the smaller, so art. 3.6.4 requires 2-9 and 5-7.

    The engine expresses that order as the weight of a minimum weight matching (see
    crosstable_fideteam.update_bracket): with B = 4 teams, base = B + 1 = 5 and
    wtop = base**B = 625, a pair weighs 625 * 2**(B - bsn(bottom)) + bsn(bottom) *
    base**(B - bsn(top)). No team has a colour preference after one match and no team
    floated in round 1, so [C8], [C9] and [C10] are all zero and the weight is the
    position alone. In TPN order:

        2-9  625*2**0 + 4*5**3 = 625 + 500 = 1125     2-5  625*2**2 + 2*5**3 = 2750
        5-7  625*2**1 + 3*5**2 = 1250 +  75 = 1325    7-9  625*2**0 + 4*5**1 =  645
        {2-9, 5-7} = 2450                             {2-5, 7-9} = 3395

    In the score order the residents come first - 5, 9, 2, 7, giving 5->1, 9->2, 2->3,
    7->4 - and the same two candidates come out the other way round:

        2-5  625*2**1 + 3*5**3 = 1250 + 375 = 1625    2-9  625*2**1 + 3*5**2 = 1325
        7-9  625*2**0 + 4*5**2 =  625 + 100 =  725    5-7  625*2**0 + 4*5**3 = 1125
        {2-5, 7-9} = 2350                             {2-9, 5-7} = 2450

    which is 2-5 and 7-9: the pairing whose identifier "2 7 5 9" art. 3.6.4 rejects.

    Nothing but art. 3.6 is in play. [C4] and [C5] (art. 2.3.1, 2.3.2) fixed the number of
    upfloaters and their score before this choice is reached, and both candidates pair one
    upfloater with each resident, so they are equal on both. [C7] and [C10] (art. 2.3.4,
    2.3.7) count floaters of the previous round and there are none - round 1 paired equal
    scores throughout. [C8] and [C9] (art. 2.3.5, 2.3.6) count unfulfilled colour
    preferences and after a single match no team has a type A preference at all.
    """
    tournament = event(10, 5)
    tournament.match(1, 5, 9, ["W", "L"])       # drawn: teams 5 and 9 have met
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 7, ["W", "W"])
    tournament.match(1, 4, 8, ["W", "W"])
    tournament.match(1, 6, 10, ["W", "W"])
    (engine, brackets) = tournament.brackets(2)
    level = engine.competitors[5]["scorelevel"]
    assert upfloaters(brackets, level) == [2, 7]
    pairs = sorted(sorted(pair) for pair in tournament.pair(2))
    assert pairs == [[1, 4], [2, 9], [3, 6], [5, 7], [8, 10]]


def test_art_3_6_2_picks_the_smallest_identifier_a_played_history_still_allows():
    """Art. 3.6.2 - the smallest identifier that the played history still allows.

    art. 3.6.1 - "for each pair, the smaller-TPN player is the top member, the larger-TPN
    player is the bottom member". art. 3.6.2 - "a pairing is identified by the TPNs of the
    top members (ascending), followed by the TPNs of the corresponding bottom members",
    and the pairing chosen is the one with the lexicographically smallest identifier.

    Eight teams, round 3. The bracket holds the residents 3, 4 and 5 and the single
    upfloater 1. Three pairings of it exist, and their identifiers are:

        {1-4, 3-5}  ->  1 3 4 5     the smallest, and barred: 1 and 4 met in round 2
        {1-5, 3-4}  ->  1 3 5 4     the smallest that art. 2.1.1 [C1] still allows
        {1-3, 4-5}  ->  1 4 3 5

    So the answer is 1-5 and 3-4. 1 and 4 have met and nothing else in the bracket has,
    and everything that could decide the bracket on some other ground is held level, so
    art. 3.6.2 is the only article left to choose:

      * [C1] (art. 2.1.1) bars exactly one of the three pairings.
      * [C4] and [C5] (art. 2.3.1, 2.3.2) are equal across the two surviving pairings:
        each pairs the one upfloater with one resident and the other two residents
        together, so each has one upfloater and the same score differences.
      * [C7] and [C10] (art. 2.3.4, 2.3.7) are zero: round 2 paired equal scores in every
        bracket, so no team of this bracket floated in the previous round.
      * [C8] and [C9] (art. 2.3.5, 2.3.6) are zero: this is type A, and after two matches
        every team here has a colour difference of zero with alternating colours, so no
        team carries a colour preference to fulfil or to leave unfulfilled.

    Number the bracket in score order instead of TPN order and this returns 1-3 and 4-5.
    """
    tournament = event(8, 5)

    # Round 1 - four winners on 2 MP (1, 3, 4, 5) and four losers on 0 MP.
    tournament.match(1, 1, 7, ["W", "W"])
    tournament.match(1, 3, 6, ["W", "W"])
    tournament.match(1, 4, 2, ["W", "W"])
    tournament.match(1, 5, 8, ["W", "W"])

    # Round 2 - team 1 meets team 4 and loses, which is the prohibition the bracket then
    # has to pair around. Teams 3 and 5 win and stay level with 4; the colours alternate
    # for every team, so no type A preference survives into round 3.
    tournament.match(2, 4, 1, ["W", "W"])
    tournament.match(2, 6, 3, ["L", "L"])
    tournament.match(2, 7, 5, ["L", "L"])
    tournament.match(2, 2, 8, ["W", "W"])

    pairs = tournament.pair(3)
    bracket = sorted(
        tuple(sorted(pair)) for pair in pairs if set(pair) <= {1, 3, 4, 5}
    )

    assert bracket == [(1, 5), (3, 4)]


def test_the_barred_pairing_is_the_one_with_the_smallest_identifier():
    """The premise of the test above: [C1] is what removes 1-4, not the identifier order.

    Without this, the test above would still pass if the engine rejected 1-4 for some
    other reason. Art. 2.1.1 [C1] - "two teams shall not play against each other more than
    once" - is absolute, so {1-4, 3-5} is unavailable however small its identifier is.

    Removing the round 2 meeting of 1 and 4, and nothing else, must therefore change the
    answer to that pairing - it is then the smallest identifier available.
    """
    tournament = event(8, 5)

    tournament.match(1, 1, 7, ["W", "W"])
    tournament.match(1, 3, 6, ["W", "W"])
    tournament.match(1, 4, 2, ["W", "W"])
    tournament.match(1, 5, 8, ["W", "W"])

    # Team 1 loses to team 2 instead of to team 4, so it arrives in the same bracket with
    # the same score and the same colour history, and 1-4 is now an available pair.
    tournament.match(2, 2, 1, ["W", "W"])
    tournament.match(2, 6, 3, ["L", "L"])
    tournament.match(2, 7, 5, ["L", "L"])
    tournament.match(2, 4, 8, ["W", "W"])

    pairs = tournament.pair(3)
    bracket = sorted(
        tuple(sorted(pair)) for pair in pairs if set(pair) <= {1, 3, 4, 5}
    )

    assert bracket == [(1, 4), (3, 5)]


# ---------------------------------------------------------------------------
# The board order - art. 3.6 of the General Handling Rules
# ---------------------------------------------------------------------------

def test_the_board_order_runs_on_the_tpn_and_not_on_the_competitor_id():
    """Article 3.6 of the General Handling Rules for Swiss Tournaments - the order the
    matches are put on the boards. C.04.7 art. 1.5 names it as one of the three things the
    pairing score is used for, "sort boards per Article 3.6 of the General Handling
    Rules", and what breaks a tie of equal scores there is the pairing number - the TPN of
    C.04.6 art. 1.1.1 - not the competitor id the file happens to carry.

    The two are the same number in an ordinary file, and the -r option of the command line
    is what tells them apart: it pairs on the initial order of the field (Article 2 of the
    General Handling Rules) rather than on the ids, and the TPN is then the place of a team
    in that order. Four teams whose initial order reverses their ids: team 4 has TPN 1,
    team 3 has TPN 2, team 2 has TPN 3 and team 1 has TPN 4.

    Round 1, so every score is equal and the whole board order rests on this one tie-break
    - which is what isolates it. Art. 3.6.2 pairs TPN 1 with TPN 3 and TPN 2 with TPN 4,
    that is teams 4-2 and 3-1, and art. 4.3.1 colours them: the first-team of each pair is
    the smaller TPN (art. 4.2.3, all the scores being zero), team 4 with the odd TPN 1
    takes the initial-colour White and team 3 with the even TPN 2 takes Black.

    On the boards, the match holding TPN 1 comes before the match holding TPN 2. Ordering
    on the competitor ids instead puts the match holding team 1 first, which is the last
    team of the field.
    """
    tournament = event(4, 5)
    tournament.initial_order([4, 3, 2, 1])
    engine = tournament.engine(1, rank=True)
    engine.compute_pairing(False)
    assert [engine.competitors[team]["tpn"] for team in range(1, 5)] == [4, 3, 2, 1]
    assert tournament.pair(1, rank=True) == [(4, 2), (1, 3)]


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


def test_art_4_1_the_drawn_initial_colour_is_recovered_through_art_4_3_1():
    """Art. 4.1 - "the initial-colour is determined by drawing of lots before the pairing
    of the first round" - read back out of a file that does not record the draw.

    The initial-colour is not the colour of the lowest-numbered team of round 1. Art.
    4.3.1 stands between the two: "if the first-team has an odd TPN, give it the
    initial-colour; otherwise, give it the opposite colour". Only an ODD TPN shows the
    drawn colour directly; an even one shows its negation.

    Five teams, and no record 152 in the file. Team 1 takes a pairing-allocated-bye in
    round 1, so the lowest-numbered MATCH is 2 v 3 - a bye has "no opponent, no colour"
    (art. 1.4) and cannot carry the initial-colour at all, which is why the engine skips
    it. That match was played with team 2 as the white team.

    The chain, and nothing else, is in play. Round 1 is the only round, so every team's
    primary and secondary score is zero and art. 4.2.1 and 4.2.2 cannot fire: art. 4.2.3
    makes the first-team of the pair the smaller TPN, team 2. No team has played a match,
    so of art. 4.3 only 4.3.1 can fire. Team 2's TPN is 2, which is even, so team 2 was
    given the OPPOSITE of the initial-colour - it played White, so the lot fell on Black.
    """
    tournament = event(5, 5, topcolor=None)
    tournament.pab(1, 1)
    tournament.match(1, 2, 3, ["W", "L"])
    tournament.match(1, 4, 5, ["W", "L"])
    assert "topColor" not in tournament.tournament
    assert tournament.engine(2).topcolor == "b"

    # and the same file with the colours of the match the other way round recovers White:
    # team 2 having Black is the even TPN taking the opposite of an initial White.
    mirror = event(5, 5, topcolor=None)
    mirror.pab(1, 1)
    mirror.match(1, 3, 2, ["W", "L"])
    mirror.match(1, 5, 4, ["W", "L"])
    assert mirror.engine(2).topcolor == "w"


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
    assert four["pts"] > two["pts"]
    assert four["tpn"] > two["tpn"]
    assert engine.first_team(four, two) is True
    assert engine.first_team(two, four) is False


def test_art_4_2_1_the_first_team_is_the_standings_score_not_the_pairing_score():
    """Art. 4.2.1 - "the first-team is the team with the higher primary score" - read
    against C.04.7 art. 1.5, which defines the OTHER score an accelerated tournament
    carries: "the pairing score of a participant (used to define scoregroups, sort them
    internally, and sort boards per Article 3.6 of the General Handling Rules) is the sum
    of their standings points and their assigned virtual points".

    That sentence enumerates what the pairing score is for, and the colour allocation is
    not on the list. Art. 4.2.1 asks for the primary score, which is the standings score:
    the virtual points of an acceleration are not points the team scored.

    The position makes the two disagree. Four teams; C.04.7 art. 1.4.2 gives teams 1 and 2
    a virtual match win (2 MP) in rounds 1 to 3. Round 1 pairs 1-2 (pairing score 2 each)
    and 3-4 (0 each); 1 v 2 is drawn and 3 beats 4. Going into round 2:

        team   standings MP   virtual MP   pairing score
          1         1              2             3
          2         1              2             3
          3         2              0             2
          4         0              0             0

    Teams 1 and 2 are the top scoregroup and have already met, so [C1] (art. 2.1.1) keeps
    the bracket from pairing inside itself and art. 3.5 brings teams 3 and 4 up. Art.
    3.6.2 then pairs 1-3 and 2-4 ("1 2 3 4" beats "1 2 4 3"). In the pair 1-3 the pairing
    score names team 1 (3 > 2) and the standings score names team 3 (2 > 1): the two
    disagree, which is the whole point of the position.

    Art. 4.3 is then made to depend on that and nothing else. Both teams played round 1,
    so 4.3.1 cannot fire. Neither has a type A preference after one match (colour
    difference +1, and "the last two played matches" needs two), so 4.3.2, 4.3.3, 4.3.4
    and 4.3.7 cannot fire. Both had White in round 1, so their colour differences are
    equal (+1) and 4.3.5 cannot fire, and their colour sequences never differ, so 4.3.6
    cannot fire either. Art. 4.3.8 is left: "alternate the colour of the first-team from
    its last played round". The first-team had White, so the first-team takes Black - and
    which team that is, is the whole question.
    """
    tournament = event(4, 5)
    tournament.tournament["accelerated"] = {
        "name": "Acc",
        "values": [
            {"matchPoints": decimal.Decimal("2.0"), "gamePoints": decimal.Decimal("2.0"),
             "firstRound": 1, "lastRound": 3, "firstCompetitor": 1, "lastCompetitor": 2},
        ],
    }
    tournament.match(1, 1, 2, ["W", "L"])       # drawn: one match point each
    tournament.match(1, 3, 4, ["W", "W"])       # 3 beats 4: two match points
    engine = tournament.engine(2)
    roundpairing = engine.compute_pairing(False)
    (one, three) = (engine.competitors[1], engine.competitors[3])
    assert (one["pts"], one["acc"]) == (decimal.Decimal("1.0"), decimal.Decimal("3.0"))
    assert (three["pts"], three["acc"]) == (decimal.Decimal("2.0"), decimal.Decimal("2.0"))
    assert one["cop"] == "nc" and three["cop"] == "nc"
    assert one["cod"] == three["cod"] == 1

    # art. 4.2.1 on the standings score: team 3 is the first-team of the pair 1-3
    assert engine.first_team(three, one) is True
    assert engine.first_team(one, three) is False

    rules = {
        (pair["w"], pair["b"]): pair["colorrule"]
        for bracket in roundpairing
        for pair in bracket["pairs"]
    }
    # art. 4.3.8 - and it is 4.3.8 that decides, so the test proves which rule fired
    assert rules == {(1, 3): "4.3.8", (2, 4): "4.3.8"}


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
    assert two["pts"] == three["pts"]           # the same match points
    assert three["ptx"] > two["ptx"]            # more game points
    assert engine.first_team(three, two) is True

    noscondary = event(4, 5, primary="match")   # FIDE_TEAM_TYPEA_MP: no secondary score
    noscondary.match(1, 2, 4, ["W", "D"])
    noscondary.match(1, 3, 1, ["W", "W"])
    engine = noscondary.engine(2)
    engine.compute_pairing(False)
    (two, three) = (engine.competitors[2], engine.competitors[3])
    assert not engine.secondary
    assert engine.first_team(two, three) is True    # art. 4.2.3: the smaller TPN


def test_art_1_2_the_three_states_of_the_secondary_score():
    """Art. 1.2.1 and 1.2.2 - the resolver itself, stated as the three states it can
    return.

    Art. 1.2.1 asks the rules of the competition "whether the other (secondary score) is
    used for colour allocation", and art. 1.2.2 answers for the rules that do not: stated
    and used, stated and not used, and unstated. Only the middle one switches art. 4.2.2
    off, and a boolean that cannot tell the third state from the second switches it off
    for tournaments whose rules never said so.
    """
    # -m fideteam-mp-gp names both scores: the competition stated that the other is used
    assert resolve_secondary_score(["fideteam", "mp", "gp"], {"primary": "mp"}) == SECONDARY_USED
    # a record 192 _MP_GP code writes both into the score system
    assert resolve_secondary_score(["fideteam"], {"primary": "match", "secondary": "game"}) == SECONDARY_USED
    # a record 192 _MP code writes one score and no other: the other is stated unused
    assert resolve_secondary_score(["fideteam"], {"primary": "match"}) == SECONDARY_UNUSED
    # -m fideteam-mp names the primary score only, which states nothing about the other
    assert resolve_secondary_score(["fideteam", "mp"], {"primary": "mp"}) == SECONDARY_UNSTATED
    # and a file that names no score at all leaves art. 1.2.2 to answer
    assert resolve_secondary_score(["fideteam"], {}) == SECONDARY_UNSTATED


def test_art_1_2_2_naming_the_primary_score_does_not_switch_the_secondary_off():
    """Art. 1.2.1 - "the rules of the competition shall state which, between match points
    and game points, is called primary score, AND WHETHER the other (secondary score) is
    used for colour allocation" - and art. 1.2.2, which answers when they do not: "the
    default is to use match points as the primary score and game points for colour
    allocation".

    The article asks two questions, and answering the first is not answering the second.
    "-m fideteam-mp" names match points as the primary score on the command line; it says
    nothing at all about game points, so art. 1.2.2 still supplies the answer and game
    points are used for the colour allocation of art. 4.2.2.

    That is the opposite case to a record 192 code, which encodes both decisions at once -
    FIDE_TEAM_TYPEA_MP_GP writes a secondary score and FIDE_TEAM_TYPEA_MP deliberately
    writes none - so there the absence of a secondary score IS the competition stating
    that the other score is not used, and art. 4.2.2 must not fire. Both files reach the
    engine with a primary score and no secondary one, and what tells them apart is which
    source stated it.

    Two teams equal on match points and unequal on game points. Art. 4.2.1 cannot separate
    them, so art. 4.2.2 has the pair to itself: the first-team is team 3, with 2.0 game
    points against team 2's 1.5. Art. 4.2.3 would say team 2, the smaller TPN, so the two
    articles disagree and the assertion reports which one fired.
    """
    tournament = event(4, 5)
    # -m fideteam-mp, as commonmain builds it: the method list becomes the pairing system,
    # and the score token in it becomes the primary score.
    tournament.tournament["pairingSystem"] = ["fideteam", "mp"]
    tournament.tournament["scoreSystem"]["primary"] = "mp"
    tournament.match(1, 2, 4, ["W", "D"])       # team 2: 1.5 game points, 2 match points
    tournament.match(1, 3, 1, ["W", "W"])       # team 3: 2.0 game points, 2 match points
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    (two, three) = (engine.competitors[2], engine.competitors[3])
    assert engine.secondary
    assert two["pts"] == three["pts"]           # the same match points: 4.2.1 is silent
    assert three["ptx"] > two["ptx"]            # more game points
    assert two["tpn"] < three["tpn"]            # and 4.2.3 would have said the other team
    assert engine.first_team(three, two) is True
    assert engine.first_team(two, three) is False


def test_art_1_2_1_a_command_line_primary_keeps_the_files_secondary_answer():
    """Art. 1.2.1 - a record 192 code answers both questions at once, and naming the
    primary score on the command line must not throw the file's answer to the second one
    away.

    FIDE_TEAM_TYPEA_MP states that game points are not used for colour allocation, and
    trf2json records that answer as scoreSystem["secondaryUsed"]. "-m fideteam-mp" then
    names match points as the primary score - the same score the file named - and says
    nothing about the other, so the file's answer stands: art. 4.2.2 stays off. Only a
    command line that names both scores ("-m fideteam-mp-gp") states that the secondary
    score is used and overrides the file.

    The two teams are the ones of the test above: equal on match points, unequal on game
    points, so art. 4.2.2 would make team 3 the first-team and art. 4.2.3 makes it team 2.
    """
    # the resolver itself
    assert resolve_secondary_score(["fideteam", "mp"], {"primary": "mp", "secondaryUsed": False}) == SECONDARY_UNUSED
    assert resolve_secondary_score(["fideteam", "mp"], {"primary": "mp", "secondaryUsed": True}) == SECONDARY_USED
    assert resolve_secondary_score(["fideteam", "mp", "gp"], {"primary": "mp", "secondaryUsed": False}) == SECONDARY_USED
    # and the engine, on the tournament commonmain builds from a FIDE_TEAM_TYPEA_MP file
    # read with -m fideteam-mp
    tournament = event(4, 5, primary="match")
    tournament.tournament["scoreSystem"]["secondaryUsed"] = False
    tournament.tournament["pairingSystem"] = ["fideteam", "mp"]
    tournament.tournament["scoreSystem"]["primary"] = "mp"
    tournament.match(1, 2, 4, ["W", "D"])       # team 2: 1.5 game points, 2 match points
    tournament.match(1, 3, 1, ["W", "W"])       # team 3: 2.0 game points, 2 match points
    engine = tournament.engine(2)
    engine.compute_pairing(False)
    assert engine.secondaryscore == SECONDARY_UNUSED
    assert not engine.secondary
    (two, three) = (engine.competitors[2], engine.competitors[3])
    assert three["ptx"] > two["ptx"]
    assert engine.first_team(two, three) is True


def test_art_1_7_the_three_colour_models_and_where_they_are_named():
    """Art. 1.7 - "Type A colour preferences are used unless the rules of the team
    competition specify Type B, or no colour preferences at all".

    The model reaches the engine from two places - the pairing system, which both -m and
    trf2json's record 192 table write into, and the record 192 code itself - and this is
    the precedence between them. One model answers both of the questions the crosstable
    asks, so the two cannot come out of different sources and leave a model half-applied.
    """
    # a model named in the pairing system wins, whichever spelling it arrived in
    assert resolve_colour_model(["fideteam", "typeb"], "") == TYPE_B
    assert resolve_colour_model(["fideteam", "team_typeb"], "") == TYPE_B
    assert resolve_colour_model(["fideteam", "nocolor"], "") == NO_COLOUR
    assert resolve_colour_model(["fideteam", "typea"], "") == TYPE_A
    # and it wins over the code of the file, which is what -m is for
    assert resolve_colour_model(["fideteam", "typea"], "FIDE_TEAM_TYPEB_MP_GP") == TYPE_A
    # the code is read when the pairing system names no model, as -m fideteam leaves it
    assert resolve_colour_model(["fideteam"], "FIDE_TEAM_TYPEB_MP_GP") == TYPE_B
    assert resolve_colour_model(["fideteam"], "FIDE_TEAM_TYPEA_MP") == TYPE_A
    # no record 192 code states the third model: there is no TYPEC token to write, so a
    # code with no TYPE token falls to the art. 1.7 default here, and the record 192
    # table of trf2json is what maps such a code to "nocolor".
    assert resolve_colour_model(["fideteam"], "FIDE_TEAM_MP_GP") == TYPE_A
    # failing both, art. 1.7's own default
    assert resolve_colour_model(["fideteam"], "") == TYPE_A


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


NOCOLOR_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "fideteam_nocolor.trf")


def nocolor_file():
    """fixtures/fideteam_nocolor.trf, a nine-team event whose record 192 code asks for no
    colour preferences."""
    reader = trf2json.trf2json()
    with open(NOCOLOR_FIXTURE, encoding="utf-8") as handle:
        reader.parse_file(handle.read(), 0)
    return reader.get_tournament(1)


def nocolor_file_pairs(rnd, pairingsystem=None):
    """The engine for one round of that file, optionally forced onto another colour model,
    and its pairing as (white team, black team, the art. 4.3 rule)."""
    tournament = nocolor_file()
    if pairingsystem is not None:
        tournament["pairingSystem"] = pairingsystem
    engine = pairing_fideteam(tournament, rnd, {"experimental": [], "verbose": 0, "rank": False, "top_color": "w"})
    roundpairing = engine.compute_pairing(False)
    return (engine, sorted(
        (pair["w"], pair["b"], pair["colorrule"])
        for bracket in roundpairing
        for pair in bracket["pairs"]
    ))


def test_art_4_3_2_cannot_grant_a_preference_that_does_not_exist():
    """Art. 4.3.2 - "if only one team has a colour preference, grant it" - against art.
    4.3.5 - "give White to the team with the lower colour difference".

    Round 6, the match between teams 2 and 3. Team 3 has played w,w,b,b: its colour
    difference is 0 and its last two played matches were Black, so art. 1.7.1 gives it a
    simple preference for White. Team 2 has played b,w,b,b,w: its colour difference is -1
    and its last two are not both Black, so under type A it has no preference. Art. 4.3.2
    then grants team 3 the White it wants.

    With no colour preferences at all, neither team wants anything, art. 4.3.2 cannot fire
    and the first rule that decides is art. 4.3.5: team 2 has the lower colour difference
    (-1 against 0) and takes White. The file pairs 2-3 with 2 as White.
    """
    (typea, typeapairs) = nocolor_file_pairs(6, ["fideteam", "team_typea"])
    (nocolor, nocolorpairs) = nocolor_file_pairs(6)

    assert (typea.competitors[2]["cop"], typea.competitors[3]["cop"]) == ("nc", "w2")
    assert (nocolor.competitors[2]["cop"], nocolor.competitors[3]["cop"]) == ("nc", "nc")
    assert (typea.competitors[2]["cod"], typea.competitors[3]["cod"]) == (-1, 0)

    assert (3, 2, "4.3.2") in typeapairs
    assert (2, 3, "4.3.5") in nocolorpairs
    chj = chessjson.chessjson()
    declared = [
        (chj.get_result_cid(match, "white"), chj.get_result_cid(match, "black"))
        for match in nocolor_file()["matchList"] if match["round"] == 6
    ]
    assert (2, 3) in declared


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


def test_check_mode_measures_the_same_quality_criteria_as_the_pairing():
    """Art. 2.3 - the quality criteria of a bracket, measured on both sides of the
    comparison the checker makes.

    pairingchecker prints the criteria of the pairing the engine would make beside those
    of the pairing the file holds, and reads the first criterion on which the two differ
    as the reason the two pairings differ. That only works if both sides measure the same
    criteria: a criterion that one side computes and the other leaves at zero reports a
    difference on every bracket.

    [C6] (art. 2.3.3) is the criterion that can differ here: "unless the following
    scoregroup is now empty, choose the set of upfloaters so that [C1], [C3] and [C4] are
    complied with in the bracket where this scoregroup is paired". It is a property of the
    bracket's set of upfloaters, not of any one pair, so it does not fall out of the pairs
    the way [C4], [C5], [C7], [C8], [C9] and [C10] do, and has to be asked for.

    The position makes [C6] fail. Ten teams; after round 1 the scoregroups are {1,3,4,6}
    on 2 MP, {5,9} on 1 MP and {2,7,8,10} on 0. The 2 MP bracket is even and pairs inside
    itself with no upfloaters at all - but teams 5 and 9 are the whole scoregroup below it
    and have already met, so that scoregroup cannot be paired with [C4]'s fewest
    upfloaters (none, its size being even) whatever the bracket above does. [C6] is not
    complied with, and both sides must say so.

    Round 2 is then paired, written back into the file exactly as it was paired, and read
    again: the two decompositions agree on the pairs and on the brackets, so every
    criterion must agree as well.
    """
    tournament = event(10, 5)
    tournament.match(1, 5, 9, ["W", "L"])
    tournament.match(1, 1, 2, ["W", "W"])
    tournament.match(1, 3, 7, ["W", "W"])
    tournament.match(1, 4, 8, ["W", "W"])
    tournament.match(1, 6, 10, ["W", "W"])
    played = tournament.pair(2)
    for (w, b) in played:
        if b == 0:
            tournament.pab(2, w)
        else:
            tournament.match(2, w, b, ["W", "L"])

    paired = tournament.engine(2).compute_pairing(False)
    analysed = tournament.engine(2).compute_pairing(True)
    quality_by_level = {
        bracket["scorelevel"]: bracket["quality"]
        for brackets in (paired,)
        for bracket in brackets
    }
    # the two sides decomposed the round into the same brackets, with the same pairs
    assert [bracket["scorelevel"] for bracket in analysed] == list(quality_by_level)
    for bracket in analysed:
        assert sorted((pair["w"], pair["b"]) for pair in bracket["pairs"]) == sorted(
            (pair["w"], pair["b"])
            for pair in next(b for b in paired if b["scorelevel"] == bracket["scorelevel"])["pairs"]
        )
        assert bracket["quality"] == quality_by_level[bracket["scorelevel"]]
    # and [C6] did fail in the 2 MP bracket
    top = next(b for b in paired if b["scorelevel"] == max(quality_by_level))
    assert top["upfloaters"] == [] and top["quality"]["QC6"] == 1


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


def simulate(numteams, numrounds, seed, teamsize=2, typeb=False, primary=None,
             secondary=None, nocolor=False, colorrules=None):
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
    tournament = event(numteams, numrounds, teamsize=teamsize, typeb=typeb, primary=primary,
                       secondary=secondary, nocolor=nocolor)
    ratings = {team["cid"]: team["rating"]["rating"] for team in tournament.tournament["competitors"]}
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
            if colorrules is not None:
                colorrules.append(pair["colorrule"])
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
    """Type A tournaments paired round by round: every round-pairing is legal.

    [C1] and [C2] hold, every team is paired or byed exactly once, and the colours are
    consistent. The results of the boards are drawn with drawresult, Gacrux's own result
    model.
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


@pytest.mark.parametrize("numteams,numrounds", [(7, 5), (12, 7), (15, 7)])
def test_invariant_sweep_no_colour_preferences(numteams, numrounds):
    """The same, with no colour preferences at all (art. 1.7)."""
    for seed in range(1, 9):
        simulate(numteams, numrounds, seed, nocolor=True)


def test_art_4_3_allocates_the_colours_without_any_colour_preference():
    """Art. 4.3 - a match still gets its two colours when no team has a preference.

    Without colour preferences the teams still play White and Black, and art. 4.3 "always
    decides". Four of its rules grant a colour preference - 4.3.2, 4.3.3, 4.3.4 and
    4.3.7 - and none of them can fire when there is none to grant, so a whole tournament
    is coloured by 4.3.1 (both teams have yet to play), 4.3.5 (the lower colour
    difference), 4.3.6 (alternate from the most recent difference) and 4.3.8 / 4.3.9
    (alternate from the last played round) alone.
    """
    rules = []
    (tournament, rounds) = simulate(14, 7, seed=5, nocolor=True, colorrules=rules)

    assert rounds == 7
    # every match that was paired got both of its colours
    chj = chessjson.chessjson()
    played = [match for match in tournament.tournament["matchList"] if chj.get_result_cid(match, "black") > 0]
    assert len(played) == len(rules)
    for match in played:
        (white, black) = (chj.get_result_cid(match, "white"), chj.get_result_cid(match, "black"))
        assert white > 0 and black > 0
        assert white != black
    # and art. 4.3 named a rule for every one of them - never one that grants a preference
    assert set(rules) <= {"4.3.1", "4.3.5", "4.3.6", "4.3.8", "4.3.9"}
    assert set(rules) & {"4.3.2", "4.3.3", "4.3.4", "4.3.7"} == set()
    # the rounds after the first are decided by the later rules
    assert len(set(rules) - {"4.3.1"}) > 1


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
    chj = chessjson.chessjson()
    for match in tournament.tournament["matchList"]:
        if chj.get_result_cid(match, "black") > 0:
            key = (min(chj.get_result_cid(match, "white"), chj.get_result_cid(match, "black")), 
                   max(chj.get_result_cid(match, "white"), chj.get_result_cid(match, "black")))
            played[key] = played.get(key, 0) + 1
    assert sorted(played.values()) == [1] * 10          # all ten pairs, once each
    byes = [chj.get_result_cid(match, "white") for match in tournament.tournament["matchList"] if chj.get_result_cid(match, "black") == 0]
    assert sorted(byes) == [1, 2, 3, 4, 5]              # and one bye each
