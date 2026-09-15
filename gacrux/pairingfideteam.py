"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Sun Jul 12 09:12:44 2026
@author: Otto Milvang, sjakk@milvang.no

FIDE C.04.6, the Swiss Team Pairing System (approved by the Council on 28/10/2025,
applied from 1 February 2026).

The pairing process is the one of art. 3.3.2:

    1. the pairing-allocated-bye is assigned      (art. 3.4)   - find_pab
    2. the top-scoregroup is combined with a set of upfloaters (art. 3.5) and the
       bracket is paired (art. 3.6)               - pair_bracket
    3. step 2 is repeated until every team is paired
    4. the colours are allocated                  (art. 4)     - update_color

which is the loop of pairing.compute_pairing, so the base class drives it. Note two
differences from the Dutch system, both of them structural:

  * a bracket is the whole top-scoregroup and (possibly) upfloaters from below. There
    are no downfloaters: every resident of the top-scoregroup is paired in its own
    bracket, and a bracket that cannot be paired asks for more upfloaters instead of
    pushing a resident down. compute_hamilton has therefore nothing to precompute.
  * no criterion of C.04.6 is absolute in the colour: art. 4 allocates the colours after
    the whole round has been paired (art. 3.3.2 step 4), and it always succeeds. The
    colour enters the pairing only as the quality criteria [C8] and [C9].
"""

import time
from itertools import combinations, combinations_with_replacement

import networkx as nx

from gacrux.crosstablefideteam import crosstable_fideteam, qdefs, QC6
from gacrux.gacruxexeptions import GacruxInputError, GacruxInvariantError, GacruxNoLegalPairing
from gacrux.pairing import pairing


# The three colour models of art. 1.7: "Type A colour preferences are used unless the
# rules of the team competition specify Type B, or no colour preferences at all."
TYPE_A = "typea"          # art. 1.7.1, the default
TYPE_B = "typeb"          # art. 1.7.2
NO_COLOUR = "nocolor"     # art. 1.7, no colour preferences at all

# The tokens a pairing system can carry to name one of them. "-m fideteam-typeb" writes
# "typeb"; the record 192 table of trf2json writes "team_typeb".
COLOUR_MODEL_TOKENS = {
    "typea": TYPE_A, "team_typea": TYPE_A,
    "typeb": TYPE_B, "team_typeb": TYPE_B,
    "nocolor": NO_COLOUR, "team_nocolor": NO_COLOUR,
}

# The tokens of a record 192 team code that name one. The code vocabulary has only two:
# there is no TYPEC to write, so no record 192 code states the third model of art. 1.7.
# A FIDE_TEAM code without a TYPE token is mapped to a model by trf2json's record 192
# table - which is where that reading belongs - and the table writes the token of
# COLOUR_MODEL_TOKENS for it. It is not re-derived here.
COLOUR_MODEL_CODES = {"TYPEA": TYPE_A, "TYPEB": TYPE_B}

# The three states of art. 1.2. Art. 1.2.1 makes the rules of the competition state
# "whether the other (secondary score) is used for colour allocation", which is a question
# with two answers; art. 1.2.2 supplies a third state for the rules that do not answer it.
SECONDARY_USED = "used"           # art. 1.2.1 - the competition states that it is used
SECONDARY_UNUSED = "unused"       # art. 1.2.1 - the competition states that it is not
SECONDARY_UNSTATED = "unstated"   # art. 1.2.2 - nothing was stated, so the default applies

# The tokens that name a score in a pairing system: "-m fideteam-mp-gp" writes both.
SCORE_TOKENS = ["mp", "gp", "match", "game"]


def resolve_secondary_score(pairingsystem, scoresystem):
    """art. 1.2 - whether the secondary score is used for the colour allocation of art.
    4.2.2.

    Art. 1.2.1 asks the rules of the competition two questions - which score is the
    primary one, and whether the other one is used - and answering the first is not
    answering the second. The three states are read like this:

      * the command line names scores as tokens of the pairing system. Two of them
        ("-m fideteam-mp-gp") state that the secondary score is used. One of them
        ("-m fideteam-mp") names the primary score and says nothing about the other, so
        it leaves whatever the file stated in place, and failing that art. 1.2.2.
      * a record 192 code encodes both answers at once: FIDE_TEAM_TYPEA_MP_GP writes a
        secondary score into the score system, and FIDE_TEAM_TYPEA_MP writes none - which
        is the competition stating that the other score is not used. trf2json records
        that second answer as scoreSystem["secondaryUsed"], separately from the scores
        themselves, because commonmain overwrites "primary" from the -m option and the
        score system alone can then no longer say which source named it. The recorded
        answer is honoured whenever the command line named at most one score.
      * a source that states neither leaves both unset, and art. 1.2.2 answers: "the
        default is to use match points as the primary score and game points for colour
        allocation".
    """
    scores = [arg for arg in pairingsystem if arg in SCORE_TOKENS]
    if len(scores) > 1:
        return SECONDARY_USED
    if "secondaryUsed" in scoresystem:
        return SECONDARY_USED if scoresystem["secondaryUsed"] else SECONDARY_UNUSED
    if "secondary" in scoresystem:
        return SECONDARY_USED
    if len(scores) > 0:
        return SECONDARY_UNSTATED
    if "primary" in scoresystem:
        return SECONDARY_UNUSED
    return SECONDARY_UNSTATED


def resolve_colour_model(pairingsystem, typeoftournament):
    """art. 1.7 - which of the three colour models the rules of the competition state.

    The rules reach the engine from two places, and this is the precedence between them:

      1. a model named in the pairing system wins. Both ways of stating a model arrive
         here - the -m option of the command line replaces the pairing system outright,
         and trf2json's record 192 table writes the model into it as well - so a caller
         that named a model has named it here, whichever route it took.
      2. the record 192 code of the file is read only when the pairing system names no
         model at all, which is what -m fideteam leaves behind. The code names two of the
         three models and no more (see COLOUR_MODEL_CODES).
      3. failing both, art. 1.7's own default: "type A colour preferences are used unless
         the rules of the team competition specify Type B, or no colour preferences at
         all".

    One model answers both of the questions the crosstable asks - whether the preferences
    are the type B ones, and whether there are preferences at all - so the two cannot come
    out of different sources and leave a model half-applied.
    """
    for token in pairingsystem:
        if token in COLOUR_MODEL_TOKENS:
            return COLOUR_MODEL_TOKENS[token]
    code = typeoftournament.upper().split("_")
    if code[:2] == ["FIDE", "TEAM"]:
        for token in code[2:]:
            if token in COLOUR_MODEL_CODES:
                return COLOUR_MODEL_CODES[token]
    return TYPE_A


class pairing_fideteam(pairing):

    FIDETEAM_RULES = {
        0: "2026-02-01",   # Approved by the FIDE Council on 28/10/2025
    }

    # constructor function
    def __init__(self, tournament, rnd, params):
        super().__init__(tournament, rnd, params)
        self.rules = self.FIDETEAM_RULES[0]
        pairingsystem = tournament.get("pairingSystem", [])
        scoresystem = tournament.get("scoreSystem", {})
        typeoftournament = tournament.get("tournamentInfo", {}).get("typeOfTournament", "")
        self.numrounds = tournament["numRounds"]

        # art. 1.7 - type A colour preferences, unless the rules of the competition ask
        # for type B, or for no colour preferences at all. Record 192 states it
        # (FIDE_TEAM_TYPEB_MP_GP and friends), and so does -m fideteam-typeb. The one
        # model answers both of the questions the crosstable asks.
        self.colourmodel = resolve_colour_model(pairingsystem, typeoftournament)
        self.typeb = self.colourmodel == TYPE_B
        self.usecolor = self.colourmodel != NO_COLOUR

        # art. 1.2 - the rules of the competition state which of match points and game
        # points is the primary score, and whether the other one is used for the colour
        # allocation of art. 4.2.2. Only a competition that stated the other score is NOT
        # used switches art. 4.2.2 off; a competition that said nothing about it gets the
        # art. 1.2.2 default, which uses it.
        # (The primary score itself is read by crosstable.compute_tiebreak.)
        self.secondaryscore = resolve_secondary_score(pairingsystem, scoresystem)
        self.secondary = self.secondaryscore != SECONDARY_UNUSED

        # C.04.7 art. 1.4.4 - the Baku acceleration cannot be used when game points are
        # the primary score.
        accelerated = tournament.get("accelerated", None)
        if accelerated is not None and len(accelerated.get("values", [])) > 0:
            if scoresystem.get("primary", "match")[0] == "g":
                raise GacruxInputError(
                    "the primary score is game points and the tournament is accelerated,"
                    + " but an acceleration cannot be used with game points as the primary"
                    + " score (see C.04.7 art. 1.4.4)"
                )

        # art. 2.3.4 [C7] and art. 2.3.7 [C10] do not apply in the last two rounds.
        self.lasttworounds = rnd > self.numrounds - 2

    def get_crosstable(self, experimental, checkonly, verbose):
        return crosstable_fideteam(experimental, checkonly, verbose, self.typeb, self.usecolor)

    def qdefs_enum(self):
        return qdefs

    def compute_hamilton(self, nodes, edges):
        # The Dutch engine works out, for every scorelevel, whether the rest of the field
        # can still be paired, and shortcuts its brackets with it. C.04.6 enumerates the
        # sets of upfloaters (art. 3.5) and tests each one of them for [C3] on its own,
        # so there is nothing to precompute.
        return [{} for _ in range(self.levels)]

    def compute_degenerate_pairing(self):
        """Pair the maximum number of teams when no complete pairing exists."""
        self.checkonly = False
        self.reportlevel = 0
        self.crosstable = self.get_crosstable(self.experimental, False, self.verbose)
        competitors, opponents = self.crosstable.init_engine(
            self.tournament, self.rnd, self.nummeets, self.topcolor, self.rank
        )
        self.competitors = competitors
        self.opponents = opponents
        nodes = self.list_nodes(competitors)
        edges = self.list_edges(opponents)

        graph = nx.Graph()
        graph.add_weighted_edges_from((edge["ca"], edge["cb"], 0) for edge in edges)
        matched = sorted(
            (a, b) if a < b else (b, a)
            for a, b in nx.min_weight_matching(graph)
        )

        pairs = []
        seated = set()
        for a, b in matched:
            edge = opponents[a][b]
            self.update_color(edge)
            edge["board"] = len(pairs) + 1
            pairs.append(edge)
            seated.update((a, b))
        for node in nodes:
            cid = node["cid"]
            if cid != 0 and cid not in seated:
                pairs.append({"board": len(pairs) + 1, "w": cid, "b": 0})
        return pairs

    """
    can_be_paired - [C3] art. 2.2.1, the completion criterion

    "A pairing complying with all the absolute criteria shall always exist for all teams
    not yet paired". The absolute criteria are [C1] and [C2] (art. 2.1), and they are the
    edges of the crosstable, so the criterion is: the teams that are left have a perfect
    matching. Every perfect matching of the teams that are left can in fact be reached by
    the process of art. 3.3.2 - a bracket may take upfloaters from any lower scoregroup,
    and it pairs all of its teams - so the criterion is not only necessary but sufficient.
    """

    def can_be_paired(self, nodes, edges):
        if len(nodes) == 0:
            return True
        if len(nodes) % 2 == 1:
            return False
        return self.weighted_match(nodes, edges) == 0

    def weighted_match(self, nodes, edges):
        G = nx.Graph()
        G.add_weighted_edges_from([(edge["ca"], edge["cb"], 0) for edge in edges])
        matching = nx.min_weight_matching(G)
        return len(nodes) - 2 * len(matching)

    def remove_nodes(self, nodes, edges, cids):
        mod_nodes = [node for node in nodes if node["cid"] not in cids]
        mod_edges = self.get_edges(mod_nodes, edges)
        return (mod_nodes, mod_edges)

    """
    find_pab - art. 3.4, the assignment of the pairing-allocated-bye

    The bye is the first step of the pairing process (art. 3.3.2), and it goes to the team
    that
        3.4.1 leaves a legal pairing for all teams
        3.4.2 has the lowest score
        3.4.3 has played the highest number of matches
        3.4.4 has the largest TPN

    [C2] (art. 2.1.2) is already in the crosstable: a team that has received a bye, won a
    match by forfeit, or been given a full-point bye, has no edge to competitor 0, and so
    is not a candidate at all.

    The bye is a bracket of its own, and pairing.compute_pairing appends it after the
    round has been paired.
    """

    def find_pab(self, nodes, edges):
        cmp = self.competitors
        self.pablevel = -1
        if not cmp[0]["rfp"]:
            return (None, -1, nodes, edges)          # an even number of teams: no bye
        candidates = [edge for edge in edges if edge["ca"] == 0]
        if not self.checkonly:
            candidates = sorted(
                candidates,
                key=lambda edge: (
                    cmp[edge["cb"]]["scorelevel"],                 # 3.4.2 the lowest score
                    -cmp[edge["cb"]]["num"].get("val", 0),         # 3.4.3 the most matches played
                    -cmp[edge["cb"]]["tpn"],                       # 3.4.4 the largest TPN
                ),
            )
        for edge in candidates:
            (mod_nodes, mod_edges) = self.remove_nodes(nodes, edges, [0, edge["cb"]])
            # 3.4.1 - and the teams that are left must have a legal pairing
            if self.checkonly or self.can_be_paired(mod_nodes, mod_edges):
                pablevel = self.pablevel = cmp[edge["cb"]]["scorelevel"]
                self.crosstable.set_scorelevel(pablevel)
                self.crosstable.update_crosstable(pablevel, nodes, edges, pablevel)
                self.update_color(edge)
                bracket = {
                    "scorelevel": pablevel,
                    "competitors": [edge["cb"]],
                    "pairs": [edge],
                    "upfloaters": [],
                    "downfloaters": [],
                    "remaining": [],
                    "quality": self.crosstable.compute_weight([edge], None),
                    "bsne": {edge["cb"]: 1},
                    "pab": True,
                }
                return (bracket, pablevel, mod_nodes, mod_edges)
        # art. 3.3.3 - if it is impossible to complete a round-pairing, the Chief Arbiter
        # shall decide what to do.
        raise GacruxNoLegalPairing(
            "no team can be given the pairing-allocated-bye and leave a legal pairing for"
            + " all the other teams (see C.04.6 art. 3.3.3 and art. 3.4.1)"
        )

    """
    pair_bracket - art. 3.5 and art. 3.6

    The bracket is the top-scoregroup (the residents) and the set of upfloaters that
    art. 3.5 selects for it. Every team of the bracket is paired in it (art. 3.6.1).
    """

    def pair_bracket(self, scorelevel, nodes, edges, testpab):
        residents = [node for node in nodes if node["scorelevel"] == scorelevel]
        if len(residents) == 0:
            # the whole scoregroup was taken as upfloaters by a bracket above it
            return (None, nodes, edges, testpab)

        self.crosstable.set_scorelevel(scorelevel)
        self.crosstable.update_crosstable(scorelevel, nodes, edges, self.pablevel)
        t0 = time.time()

        if self.checkonly:
            (upfloaters, pairs) = self.analyse_bracket(scorelevel, nodes, edges)
        else:
            (upfloaters, pairs, c6) = self.select_upfloaters(scorelevel, residents, nodes, edges)

        bracketnodes = self.sort_nodes(residents + upfloaters)
        bracket = {
            "scorelevel": scorelevel,
            "competitors": [node["cid"] for node in bracketnodes],
            "pairs": pairs,
            "upfloaters": [node["cid"] for node in upfloaters],
            "downfloaters": [],        # C.04.6 knows no downfloaters
            "remaining": [],
            "quality": self.crosstable.compute_weight(pairs, None),
            # art. 3.6.1 - the position of a team in the bracket, the teams in TPN order,
            # the same map crosstable_fideteam.update_bracket paired the bracket with.
            "bsne": {
                node["cid"]: i + 1
                for i, node in enumerate(sorted(bracketnodes, key=lambda node: node["tpn"]))
            },
            "pab": scorelevel == self.pablevel,
        }
        if not self.checkonly:
            bracket["quality"][QC6] = 0 if c6 else 1

        for pair in pairs:
            self.update_color(pair)

        t1 = time.time()
        self.timer["bracket"] = self.timer.get("bracket", 0.0) + t1 - t0
        if self.verbose:
            print(
                f"{'Check ' if self.checkonly else 'Pair  '} round: {self.rnd},"
                + f" Scorelevel: {scorelevel:2}, Residents: {len(residents):2},"
                + f" Upfloaters: {len(upfloaters):2}, {t1 - t0:.2f}s"
            )
        if self.reportlevel >= 2:
            print("================================================")
            print("Scorelevel: ", scorelevel, ", nodes: ", len(nodes), ", edges: ", len(edges))
            print("Bracket       = ", self.crosstable.levels()[scorelevel])
            print("Competitors   = ", bracket["competitors"])
            print("Upfloaters    = ", bracket["upfloaters"])
            print("Pairs         = ", [(c["w"], c["b"]) for c in pairs])
            print("Quality       = ", bracket["quality"])

        (nodes, edges, npaired) = self.remove_pairs(nodes, edges, pairs)
        bracket["remaining"] = [node["cid"] for node in nodes]
        return (bracket, nodes, edges, testpab)

    def sort_nodes(self, nodes):
        return sorted(nodes, key=lambda node: (-node["scorelevel"], node[self.rank]))

    """
    analyse_bracket - the same decomposition, for the pairing that the tournament file
    already holds. In check mode the crosstable holds one edge per pair of the round, so
    a bracket is made of the pairs whose higher-scored team is a resident of it.
    """

    def analyse_bracket(self, scorelevel, nodes, edges):
        pairs = [edge for edge in edges if max(edge["sa"], edge["sb"]) == scorelevel]
        upfloaters = []
        for edge in pairs:
            for cid in [edge["ca"], edge["cb"]]:
                if self.competitors[cid]["scorelevel"] < scorelevel:
                    upfloaters.append(self.competitors[cid])
        return (upfloaters, pairs)

    """
    select_upfloaters - art. 3.5, the selection of the upfloaters for the top-scoregroup

    3.5.1 every team with a lower score than the residents is a potential upfloater
    3.5.2 consider all the sets of potential upfloaters that comply with [C4] and [C5],
          "which somehow determines the number of upfloaters in the set and their scores"
    3.5.3 in each set, the upfloaters are sorted by descending score, then ascending TPN
    3.5.4 the sets are sorted among themselves by the lexicographic order of their TPNs
    3.5.5 choose the first set that, together with the top-scoregroup, produces a legal
          pairing that also complies with [C6] and [C7]

    [C4] (art. 2.3.1, minimise the number of upfloaters) and [C5] (art. 2.3.2, maximise
    their scores, taken in ascending order) are the outer loops: the number of upfloaters
    grows from the fewest the parity of the bracket allows, and for each number the score
    profiles are tried best first. A number, or a profile, for which no set produces a
    legal pairing is no candidate at all - [C3] (art. 2.2.1) says a pairing must exist
    for all the teams not yet paired - so the search falls back to the next one, which is
    what "consider all sets that comply with [C4] and [C5]" comes down to once the sets
    that are not legal are removed from it.

    Within one profile, the sets are enumerated in the order of art. 3.5.4, and among the
    legal ones the criteria of art. 3.5.5 pick the winner: [C6] first, then [C7], then
    the first in that order. Reading "complies with [C7]" as "attains the smallest value
    of [C7] a legal set of this profile can attain" is the reading that gives the words
    of art. 2.3 ("comply as much as possible with the following criteria, given in
    descending priority") their meaning; the same holds for [C6], which is either
    complied with or not.
    """

    def select_upfloaters(self, scorelevel, residents, nodes, edges):
        lower = [node for node in nodes if node["scorelevel"] < scorelevel]
        for numup in range(len(residents) % 2, len(lower) + 1, 2):
            for profile in self.list_profiles(lower, numup):
                best = None
                for index, upfloaters in enumerate(self.list_upfloaters(lower, profile)):
                    bracketnodes = self.sort_nodes(residents + upfloaters)
                    bracketedges = self.get_edges(bracketnodes, edges)
                    pairs = self.pair_teams(scorelevel, bracketnodes, bracketedges)
                    if pairs is None:
                        continue                          # no legal pairing of the bracket
                    cids = [node["cid"] for node in bracketnodes]
                    (restnodes, restedges) = self.remove_nodes(nodes, edges, cids)
                    if not self.can_be_paired(restnodes, restedges):
                        continue                          # [C3] art. 2.2.1
                    c6 = self.check_c6(scorelevel, restnodes, restedges)
                    c7 = self.count_c7(upfloaters)
                    key = (0 if c6 else 1, c7, index)
                    if best is None or key < best[0]:
                        best = (key, upfloaters, pairs, c6)
                    if key[0] == 0 and key[1] == 0:
                        break                             # art. 3.5.5, the first such set
                if best is not None:
                    (key, upfloaters, pairs, c6) = best
                    return (upfloaters, pairs, c6)
        # art. 3.3.3 - if it is impossible to complete a round-pairing, the Chief Arbiter
        # shall decide what to do.
        raise GacruxNoLegalPairing(
            "score bracket " + str(scorelevel) + " has no legal pairing, with any set of"
            + " upfloaters (see C.04.6 art. 3.3.3)"
        )

    """
    list_profiles - the score profiles of a set of "numup" upfloaters, best first

    [C5] art. 2.3.2 - "minimise the score differences (taken in descending order) in the
    pairs involving upfloaters, i.e. maximise the scores (taken in ascending order) of
    the upfloaters" - so the profiles are compared as their scores in ascending order,
    and the largest of them wins.
    """

    def list_profiles(self, lower, numup):
        levels = {}
        for node in lower:
            levels[node["scorelevel"]] = levels.get(node["scorelevel"], 0) + 1
        profiles = []
        for profile in combinations_with_replacement(sorted(levels.keys(), reverse=True), numup):
            if all([profile.count(level) <= levels[level] for level in set(profile)]):
                profiles.append(profile)
        return sorted(profiles, key=lambda profile: sorted(profile), reverse=True)

    """
    list_upfloaters - every set of upfloaters with the given score profile, in the order
    of art. 3.5.3 and art. 3.5.4

    3.5.3 sorts the teams within a set: descending score, then ascending TPN.
    3.5.4 sorts the sets among themselves, by the lexicographic order of their TPNs. The
    example of the regulation - 2, 6, 8 with 3 points and 1, 3, 5 with 2.5, two
    upfloaters of 3 points and one of 2.5 - gives
        {2,6,1} < {2,6,3} < {2,6,5} < {2,8,1} < ... < {6,8,5}
    """

    def list_upfloaters(self, lower, profile):
        bylevel = {}
        for node in lower:
            bylevel.setdefault(node["scorelevel"], []).append(node)
        sets = [[]]
        for level in sorted(set(profile), reverse=True):          # 3.5.3 descending score
            newsets = []
            for chosen in combinations(bylevel[level], profile.count(level)):   # ascending TPN
                for upfloaters in sets:
                    newsets.append(upfloaters + list(chosen))
            sets = newsets
        return sorted(sets, key=lambda s: [node[self.rank] for node in s])      # 3.5.4

    """
    check_c6 - [C6] art. 2.3.3

    "Unless all the teams in the following scoregroup became or are upfloaters (thus this
    scoregroup is now empty), choose the set of upfloaters so that criteria [C1], [C3]
    and [C4] are complied with in the bracket where this (not empty) scoregroup is
    paired. Note: only the mentioned scoregroup is involved, even though some of the
    upfloaters come from lower scoregroups."

    So: the scoregroup right below the one being paired - what is left of it - must still
    be pairable ([C1] and [C3]) with the fewest upfloaters ([C4]) its own size allows,
    which is none when it is even and one when it is odd. Reading [C4] here as anything
    else would leave [C6] with no content at all, since the bracket of that scoregroup
    will minimise its upfloaters in any case, whatever this bracket leaves behind.
    """

    def check_c6(self, scorelevel, restnodes, restedges):
        following = [node for node in restnodes if node["scorelevel"] == scorelevel - 1]
        if len(following) == 0:
            return True
        lower = [node for node in restnodes if node["scorelevel"] < scorelevel - 1]
        numup = len(following) % 2
        candidates = [[]] if numup == 0 else [[node] for node in lower]
        for upfloaters in candidates:
            bracketnodes = self.sort_nodes(following + upfloaters)
            bracketedges = self.get_edges(bracketnodes, restedges)
            if not self.can_be_paired(bracketnodes, bracketedges):
                continue
            cids = [node["cid"] for node in bracketnodes]
            (mod_nodes, mod_edges) = self.remove_nodes(restnodes, restedges, cids)
            if self.can_be_paired(mod_nodes, mod_edges):
                return True
        return False

    """
    count_c7 - [C7] art. 2.3.4

    "With the exception of the last two rounds, minimise the number of upfloaters that
    were floaters in the previous round (see art. 1.5)". A floater is a team that played
    an opponent with a different score, so a team that received a bye is not one.
    """

    def count_c7(self, upfloaters):
        if self.lasttworounds:
            return 0
        return len([node for node in upfloaters if node["flt"]])

    """
    pair_teams - art. 3.6, the pairing of the bracket

    Art. 3.6.4 - the first pairing, in the lexicographic order of the identifiers of art.
    3.6.2, that complies with [C1], [C8], [C9] and [C10]. crosstable_fideteam.update_bracket
    writes that order into the weight of the edges, so one minimum weight matching answers
    it. A bracket that has no perfect matching has no pairing at all, and art. 3.5 then
    asks for another set of upfloaters.
    """

    def pair_teams(self, scorelevel, bracketnodes, bracketedges):
        if len(bracketedges) == 0:
            return None
        self.crosstable.update_bracket(scorelevel, bracketnodes, bracketedges)
        G = nx.Graph()
        G.add_weighted_edges_from([(edge["ca"], edge["cb"], edge["weight"]) for edge in bracketedges])
        wpairs = nx.min_weight_matching(G)
        if 2 * len(wpairs) != len(bracketnodes):
            return None
        pairs = [self.opponents[a][b] if a < b else self.opponents[b][a] for (a, b) in wpairs]
        return sorted(pairs, key=lambda edge: (edge["ca"], edge["cb"]))

    """
    update_board

    C.04.6 says nothing about the order of the matches on the boards, and art. 3.6 of the
    General Handling Rules is left to the rules of the competition. The matches are
    ordered the way the Dutch engine orders its games - by the higher score of the pair,
    then by the sum of the scores, then by the lower TPN - and the bye comes last.
    """

    def update_board(self, roundpairing):
        pairs = []
        cmp = self.competitors
        for bracket in roundpairing:
            for pair in bracket["pairs"]:
                (w, b) = (pair["w"], pair["b"])
                (ws, bs) = (cmp[w]["acc"], cmp[b]["acc"])
                pairs.append(
                    {
                        "pair": pair,
                        "ipab": w == 0 or b == 0,
                        "maxs": max(ws, bs),
                        "sums": ws + bs,
                        "rank": w if w < b else b,
                    }
                )
        board = 0
        npairs = []
        for pair in sorted(pairs, key=lambda c: (c["ipab"], -c["maxs"], -c["sums"], c["rank"])):
            npair = pair["pair"]
            board += 1
            npair["board"] = board
            npairs.append(npair)
        return npairs

    """
    update_color / color_allocation - art. 4, the colour allocation rules

    4.1  the initial-colour is drawn by lot before the pairing of the first round. It is
         topcolor: the colour of the team that art. 4.3.1 gives the initial-colour to.
    4.2  the first-team is the team with the higher primary score, then the higher
         secondary score (unless the rules of the competition state not to use it), then
         the smaller TPN.
    4.3  the rules, in descending priority.

    This is not article 5 of C.04.3. There is no absolute preference to grant first, no
    topscorer, and no rule that leaves a pair uncoloured: art. 4.3 always decides.
    """

    def update_color(self, c):
        ca = self.competitors[c["ca"]]
        cb = self.competitors[c["cb"]]
        colres = self.color_allocation(ca, cb)
        if self.checkonly:
            if ca["cid"] == 0:
                p = {"w": cb["cid"], "b": 0}
            else:
                p = {ca["hst"]["val"][-1]: ca["cid"], cb["hst"]["val"][-1]: cb["cid"]}
            c.update(p)
            c["colorrule"] = colres["colorrule"]
        else:
            (c["w"], c["b"], c["colorrule"]) = (colres["w"], colres["b"], colres["colorrule"])

    """
    first_team - art. 4.2

    The scores compared here are the standings scores, and not the pairing score of
    C.04.7 art. 1.5. That article enumerates what the pairing score is for - it is "used
    to define scoregroups, sort them internally, and sort boards per Article 3.6 of the
    General Handling Rules" - and the colour allocation is not on the list. Art. 4.2.1 and
    4.2.2 ask for the primary and the secondary score, and the virtual points of an
    acceleration are not points a team scored.

    (The Dutch engine makes the same choice in the same place - its E.4 and E.5 rank the
    two players by score level, which is built from the pairing score, and its update_board
    orders the boards by it. That is C.04.3 art. 5, a different text, and it is left as it
    is.)
    """

    def first_team(self, a, b):
        # art. 4.2 - a is the first-team?
        if a["pts"] != b["pts"]:
            return a["pts"] > b["pts"]                     # 4.2.1 the higher primary score
        if self.secondary and a["ptx"] != b["ptx"]:
            return a["ptx"] > b["ptx"]                     # 4.2.2 the higher secondary score
        return a["tpn"] < b["tpn"]                         # 4.2.3 the smaller TPN

    def color_allocation(self, a, b):
        other = {"w": "b", "b": "w"}
        # art. 1.4 - the pairing-allocated-bye has no colour. The team is reported as
        # white, as in the Dutch engine, so that the bye is a pair like any other.
        if a["cid"] == 0:
            return {"w": b["cid"], "b": a["cid"], "colorrule": "pab"}
        if b["cid"] == 0:
            return {"w": a["cid"], "b": b["cid"], "colorrule": "pab"}

        (first, second) = (a, b) if self.first_team(a, b) else (b, a)
        (fcop, scop) = (first["cop"], second["cop"])
        (fcid, scid) = (first["cid"], second["cid"])

        def give(color, rule):
            # give <color> to the first-team
            if color == "w":
                return {"w": fcid, "b": scid, "colorrule": rule}
            return {"w": scid, "b": fcid, "colorrule": rule}

        # 4.3.1 when both teams have yet to play a match, if the first-team has an odd
        #       TPN, give it the initial-colour; otherwise, give it the opposite colour.
        if first["num"].get("val", 0) == 0 and second["num"].get("val", 0) == 0:
            color = self.topcolor if first["tpn"] % 2 == 1 else other[self.topcolor]
            return give(color, "4.3.1")

        # 4.3.2 if only one team has a colour preference, grant it.
        if fcop != "nc" and scop == "nc":
            return give(fcop[0], "4.3.2")
        if fcop == "nc" and scop != "nc":
            return give(other[scop[0]], "4.3.2")

        # 4.3.3 if the two teams have opposite colour preferences, grant them.
        if fcop != "nc" and scop != "nc" and fcop[0] != scop[0]:
            return give(fcop[0], "4.3.3")

        # 4.3.4 (type B only) if only one team has a strong colour preference, grant it.
        #       Both teams want the same colour here, or neither wants one.
        if self.typeb and fcop != "nc" and scop != "nc":
            if fcop[1] == "2" and scop[1] != "2":
                return give(fcop[0], "4.3.4")
            if fcop[1] != "2" and scop[1] == "2":
                return give(other[scop[0]], "4.3.4")

        # 4.3.5 give White to the team with the lower colour difference.
        if first["cod"] != second["cod"]:
            return give("w" if first["cod"] < second["cod"] else "b", "4.3.5")

        # 4.3.6 alternate the colours to the most recent time in which one team had White
        #       and the other Black. The colour sequences hold the played matches only
        #       (art. 3.4 of the General Handling Rules), so they are compared from the
        #       end, position by position.
        (fsq, ssq) = (first["csq"], second["csq"])
        for i in range(1, min(len(fsq), len(ssq)) + 1):
            (fc, sc) = (fsq[-i], ssq[-i])
            if fc != sc and fc in "wb" and sc in "wb":
                return give(other[fc], "4.3.6")

        # 4.3.7 grant the colour preference of the first-team.
        if fcop != "nc":
            return give(fcop[0], "4.3.7")

        # 4.3.8 alternate the colour of the first-team from its last played round.
        if fsq.strip() != "":
            return give(other[fsq[-1]], "4.3.8")

        # 4.3.9 alternate the colour of the other team from its last played round.
        if ssq.strip() != "":
            return give(ssq[-1], "4.3.9")

        # Unreachable: a pair in which neither team has ever played a match is 4.3.1.
        raise GacruxInvariantError(
            "no rule of C.04.6 art. 4.3 allocates the colours of the pair "
            + str(fcid) + " - " + str(scid) + ", although one of them has played a match"
        )
