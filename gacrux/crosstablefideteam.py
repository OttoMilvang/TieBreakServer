# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 09:12:44 2026
@author: Otto Milvang, sjakk@milvang.no

Crosstable for the FIDE Swiss Team Pairing System, C.04.6.

The team system is not the Dutch system with a team where a player used to be, and
crosstable_dutch cannot be reused for it:

  * art. 1.6 - a team "had" a colour in a match only if the match was actually played,
    and the colour is the one the player on the first board was scheduled to play.
  * art. 1.7 - the colour preferences are graded far more weakly than the ones of
    C.04.3, and there are two sets of them: type A (the default) knows one strength,
    type B knows two. A team with a colour difference of +1 whose last two played
    matches were with Black has an absolute preference for White under C.04.3, no
    preference at all under C.04.6 type A, and a mild preference for Black under type B.
  * the Preface - there are no absolute colour preferences, so a colour never keeps two
    teams apart. update_canmeet must not remove an edge for a colour, only for [C1] and
    [C2] (art. 2.1).
  * art. 2.3 - the quality criteria are [C4] to [C10] and they are not the [C6] to [C21]
    of the Dutch system. They have their own qdefs.

Everything else - the competitor and opponent structures, the score levels, the TPNs,
the prohibited pairings of record 260 - is the one of the base class.
"""

from gacrux.crosstable import crosstable
from enum import Enum


class qdefs(Enum):
    QC4 = 0
    QC5 = 1
    QC6 = 2
    QC7 = 3
    QC8 = 4
    QC9 = 5
    QC10 = 6
    IW = 7
    QL = 8


# Quality constants
QC4 = qdefs.QC4.name
QC5 = qdefs.QC5.name
QC6 = qdefs.QC6.name
QC7 = qdefs.QC7.name
QC8 = qdefs.QC8.name
QC9 = qdefs.QC9.name
QC10 = qdefs.QC10.name
IW = qdefs.IW.name
QL = qdefs.QL.value

# History of a team that art. 2.1.2 [C2] bars from the pairing-allocated-bye:
# "pab" - it has already received one, "+" - it has won a match by forfeit,
# "F" - it has been given a (FIDE-deprecated) full-point bye.
NOPAB = ["pab", "+", "F"]


class crosstable_fideteam(crosstable):

    # constructor function
    def __init__(self, experimental, checkonly, verbose, typeb=False, usecolor=True,
                 lasttworounds=False):
        super().__init__(experimental, checkonly, verbose)
        self.typeb = typeb
        self.usecolor = usecolor
        # art. 2.3.4 [C7] and art. 2.3.7 [C10] - "with the exception of the last two
        # rounds". Decided once by pairing_fideteam and not recomputed here, so the
        # diagnostic and the pairing cannot disagree about which rounds they apply to.
        self.lasttworounds = lasttworounds
        self.maxpsd = 0
        self.pablevel = -1

    """
    Art. 2.3.4 [C7] and art. 2.3.7 [C10] look at the previous round only - unlike the
    Dutch system, which looks two rounds back. FLTFT keeps the float of the previous
    round only: 1 = the team played an opponent with a higher score, 2 = with a lower
    score, 0 = it played an opponent with the same score, or did not play at all. Art.
    1.5 - a team that received a bye is not a floater.
    """

    def floatrule(self):
        return "FLTFT"

    def maxquality(self):
        return qdefs.IW.value

    """
    assign_tpn - art. 1.1, the tournament pairing number

    art. 1.1.1 - "each team must have a different TPN, from 1 to the number of teams".
    art. 1.1.2 - "the rules of the team competition shall describe how to assign a TPN to
    each team. Otherwise, it is a decision of the Chief Arbiter", with the note that this
    "overrides Articles 2.1 to 2.3 of the General Handling Rules for Swiss Tournaments".
    art. 1.1.3 - "once defined, the TPN should not be modified (except as stated in
    Articles 2.4 and 2.5 of the General Handling Rules for Swiss Tournaments), unless the
    Chief Arbiter decides otherwise".

    So C.04.6 does not derive the number from the standings: it is assigned once, outside
    these rules, and then held. What states that assignment here is the fixed order the
    engine is given - the declared start numbers, or the original ranking when the caller
    selects that - and neither changes from round to round. Each team therefore keeps its
    place in that order, rather than taking the running count over the teams ready to be
    paired that the base class keeps for the individual systems: a team that is absent must
    keep its own number and must not hand it down to the team behind it. Seven articles
    read the number back - 3.4.4, 3.5.3, 3.5.4, 3.6.1, 3.6.2, 4.2.3 and 4.3.1 - and 4.3.1
    reads its parity, so one absent team would otherwise reverse the colours of every team
    below it.

    In a field where every team is present the two numberings are the same value, which is
    why only an absence ever tells them apart.
    """

    def assign_tpn(self, competitors, size):
        rr = sorted(competitors, key=lambda s: (s[self.rank]))
        for i in range(1, size):
            rr[i]["tpn"] = i

    """
    color_preference - art. 1.7

    cop is the colour, then the strength:
        "w2" / "b2" - a simple (type A) or a strong (type B) colour preference
        "w1" / "b1" - a mild (type B) colour preference
        "nc"        - no colour preference
    Type A knows no mild preference, so under type A the strength is always 2, and
    art. 2.3.6 [C9] - which is type B only - is inert.

    cod and csq are the colour difference (art. 1.6.2) and the colour sequence (art. 1.6.1)
    of the team, and both are built from played matches only: art. 3.4 of the General
    Handling Rules compresses the colour history over the unplayed rounds. csq holds one
    letter per played match and nothing else, so csq[-2:] is two colours only when the
    team really has played two matches - "the last two played matches" of art. 1.7.
    """

    def color_preference(self, cod, csq):
        if not self.usecolor:
            return "nc"
        # art. 1.7.1 first two paragraphs (simple), art. 1.7.2 first two (strong) - the
        # two are worded identically and only their names differ.
        if cod < -1 or (cod == 0 or cod == -1) and csq[-2:] == "bb":
            return "w2"
        if cod > 1 or (cod == 0 or cod == 1) and csq[-2:] == "ww":
            return "b2"
        if not self.typeb:
            # art. 1.7.1 third paragraph - in all other situations, type A has none.
            return "nc"
        # art. 1.7.2 third and fourth paragraph - the mild preferences of type B.
        if cod == -1:
            return "w1"
        if cod == 1:
            return "b1"
        if cod == 0 and self.rnd != self.numrounds:
            if csq[-1:] == "b":
                return "w1"
            if csq[-1:] == "w":
                return "b1"
        # art. 1.7.2 fifth paragraph - a team that has yet to play a match, and a team
        # whose colour difference is zero when pairing for the last round.
        return "nc"

    """
    update_canmeet - art. 2.1, the absolute criteria

    [C1] art. 2.1.1 - two teams shall not meet more than once. The base class counts the
    meetings and is enough for it.
    [C2] art. 2.1.2 - a team that has already received the pairing-allocated-bye, has
    won a match by forfeit, or has been given a full-point bye, shall not receive the
    pairing-allocated-bye. Competitor 0 is the bye, so the criterion removes the edge
    between it and such a team.

    There is no third absolute criterion. C.04.3 has one - [C3], two players with the
    same absolute colour preference shall not meet - and the Preface of C.04.6 says the
    team system has none: "the colour will never be a factor so decisive as to prevent
    two teams from playing against each other".
    """

    def update_canmeet(self, edge, a, b, bhasmet):
        canmeet = super().update_canmeet(edge, a, b, bhasmet)
        if canmeet and not self.checkonly and a["cid"] == 0:
            canmeet = not self.had_bye_or_forfeit_win(b)
        return canmeet

    def had_bye_or_forfeit_win(self, competitor):
        history = competitor.get("hst", {})
        return len([rnd for rnd, val in history.items() if isinstance(rnd, int) and val in NOPAB]) > 0

    def update_crosstable(self, scorelevel, nodes, edges, pablevel, update_maxpsd=True):
        self.pablevel = pablevel
        # A bracket is the top-scoregroup and (possibly) upfloaters from any lower
        # scoregroup (art. 1.3.2), so the score difference of a pair reaches from 1 down
        # to the lowest scoregroup of the tournament.
        self.maxpsd = scorelevel

    """
    update_edge - the quality criteria of art. 2.3 that a single pair can carry

    [C4] and [C5] (art. 2.3.1 and 2.3.2) are decided when the set of upfloaters is chosen
    (art. 3.5), but they can be read off a pair all the same - the upfloaters a pair holds
    and the score difference between its teams - and are computed here, so that the
    quality vector of a bracket, which pairingchecker prints and compares, reports them.

    [C6] (art. 2.3.3) cannot: it is a property of the whole set of upfloaters and of the
    scoregroup the bracket leaves behind, so no pair carries any of it. It stays zero here
    and pairing_fideteam.pair_bracket writes the bracket's value over it.

    In a bracket, a team of the top-scoregroup is a resident and every other team is an
    upfloater (art. 1.3.2), so a team is an upfloater when its score level is below the
    score level of the bracket.
    """

    def update_edge(self, edge):
        c = edge
        if c["qlevel"] == self.scorelevel and c["cb"] < self.BLOB:
            return
        c["qlevel"] = self.scorelevel
        c["quality"] = q = {qd.name: None for qd in qdefs if qd.value < QL}
        maxpsd = self.maxpsd
        q[QC4] = 0
        q[QC5] = [0] * maxpsd
        q[QC6] = 0
        q[QC7] = 0
        q[QC8] = 0
        q[QC9] = 0
        q[QC10] = 0
        if not c["canmeet"] or c["ca"] == 0:
            return
        a = self.competitors[c["ca"]]
        b = self.competitors[c["cb"]]
        if a["scorelevel"] < b["scorelevel"]:
            (a, b) = (b, a)
        # [C4] art. 2.3.1 - "minimise the number of upfloaters". The criterion counts
        # teams, so a pair is worth the number of ITS teams that are upfloaters: none, one
        # or two. A team of the bracket is an upfloater when its score is below the score
        # of the bracket (art. 1.3.2) - which is not the same test as "lower than the
        # other team of the pair", and differs from it in a pair of two upfloaters.
        q[QC4] = len([team for team in (a, b) if team["scorelevel"] < self.scorelevel])
        # [C5] art. 2.3.2 reads the score of every upfloater, not the score difference
        # between the two teams of the pair. Those are the same only when the pair holds
        # one upfloater and one resident. Count from the bracket's score level so a pair
        # of two upfloaters reports both members at their respective distances.
        for team in (a, b):
            if team["scorelevel"] < self.scorelevel:
                psd = self.scorelevel - team["scorelevel"]
                q[QC5][maxpsd - psd] += 1
        if not self.lasttworounds:
            # A pair can contain two upfloaters: an upfloater is a team below the score
            # level of the bracket, not merely the lower-scoring team of this pair.
            # [C7] art. 2.3.4 counts every upfloater that was a floater in the previous
            # round. [C10] art. 2.3.7 counts the opponent of every such upfloater when
            # that opponent was a floater. In a pair of two upfloaters, each team is the
            # other's opponent and either or both can contribute to both criteria.
            q[QC7] = sum(
                bool(team["flt"])
                for team in (a, b)
                if team["scorelevel"] < self.scorelevel
            )
            q[QC10] = sum(
                bool(opponent["flt"])
                for team, opponent in ((a, b), (b, a))
                if team["scorelevel"] < self.scorelevel
            )
        # [C8] art. 2.3.5 - a pair of teams that want the same colour leaves one of them
        # unfulfilled, whatever the colour allocation of art. 4 does with it.
        (acop, bcop) = (a["cop"], b["cop"])
        if acop != "nc" and acop[0] == bcop[0]:
            q[QC8] = 1
            # [C9] art. 2.3.6 - and the one left unfulfilled has a strong preference only
            # when both of them have one: art. 4.3.4 grants the strong one when the other
            # is mild. Type A has no strong preferences, so [C9] is then always zero.
            if self.typeb and acop[1] == "2" and bcop[1] == "2":
                q[QC9] = 1
        c["colordiff"] = acop[0] + bcop[0]

    """
    update_bracket - art. 3.6, the pairing of a bracket

    Art. 3.6.3 and 3.6.4: of all the pairings of the bracket that comply with [C1], the
    one to choose is the first, in the lexicographic order of the identifiers of art.
    3.6.2, among those that comply with [C8], [C9] and [C10]. The order is expressed as
    the weight of a minimum weight matching, the way pairingdutch expresses the criteria
    of C.04.3:

        [C8]  - the teams that do not get the colour they prefer      (art. 2.3.5)
        [C9]  - the teams that do not get a strong preference, type B (art. 2.3.6)
        [C10] - upfloaters' opponents that floated in the previous round (art. 2.3.7)
        the top members of the identifier                             (art. 3.6.2)
        the bottom members of the identifier                          (art. 3.6.2)

    bsn is the position of a team in the bracket, the teams taken in TPN order. The team
    with the smaller bsn in a pair is the top member of the pair (art. 3.6.1). The map is
    built here, out of the TPNs of the teams that were handed in, rather than read off the
    order they arrive in: the callers order a bracket by score first (get_edges needs
    that), and residents therefore precede upfloaters whatever their TPNs are, which is
    not the order art. 3.6 reads a bracket in. Deriving bsn here leaves the two ends
    nothing to disagree about.

    The identifier holds all the top members before the first bottom member, so a pairing
    that makes a low-TPN team a bottom member is worse than any pairing that does not,
    no matter what the bottom members then are. A bottom member therefore weighs
    2**(B - bsn) - one bit per team, the low TPNs the heavy ones - scaled above every sum
    the bottom-member part can reach. The bottom-member part is bsn(bottom) * (B+1)**(B -
    bsn(top)), the same trick one order down: base B+1, so that no bsn can carry into the
    position of the next top member, which makes the sum compare the bottom members in
    the order of their top members - and that is what art. 3.6.2 asks for.
    """

    def update_bracket(self, scorelevel, nodes, edges):
        # art. 3.6.1 - the teams of the bracket, taken in TPN order
        self.bsn = bsn = {
            node["cid"]: i + 1
            for i, node in enumerate(sorted(nodes, key=lambda node: node["tpn"]))
        }
        self.B = B = len(nodes)
        base = B + 1
        self.weight = weight = {qd.name: 0 for qd in qdefs}
        wbottom = 1                                     # art. 3.6.2, the bottom members
        wtop = base ** B                                # art. 3.6.2, the top members
        weight[QC10] = wtop * 2 ** B                    # [C10] art. 2.3.7
        weight[QC9] = weight[QC10] * base               # [C9] art. 2.3.6
        weight[QC8] = weight[QC9] * base                # [C8] art. 2.3.5
        for c in edges:
            q = self.get_edge_quality(c)["quality"]
            (top, bottom) = (c["ca"], c["cb"]) if bsn[c["ca"]] < bsn[c["cb"]] else (c["cb"], c["ca"])
            c["weight"] = (
                q[QC8] * weight[QC8]
                + q[QC9] * weight[QC9]
                + q[QC10] * weight[QC10]
                + wtop * 2 ** (B - bsn[bottom])
                + wbottom * bsn[bottom] * base ** (B - bsn[top])
            )
            c["mode"] = "QC"
            c["levels"] = scorelevel
        return weight

    def compute_weight(self, wpairs, bquality):
        quality = {qd.name: None for qd in qdefs if qd.value < QL}
        for c in wpairs:
            q = self.get_edge_quality(c)["quality"]
            for elem in range(QL):
                nelem = qdefs(elem).name
                if q[nelem] is None:
                    pass
                elif quality[nelem] is None:
                    quality[nelem] = q[nelem] if isinstance(q[nelem], int) else list(q[nelem])
                elif isinstance(quality[nelem], int):
                    quality[nelem] += q[nelem]
                else:
                    for i in range(len(quality[nelem])):
                        quality[nelem][i] += q[nelem][i]
        return quality
