# -*- coding: utf-8 -*-
# noqa
"""
Copyright 2024, Otto Milvang
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import sys
import time

from collections import defaultdict
import version
from helpers import *
from chessjson import chessjson
from commonmain import commonmain
from tiebreak import tiebreak
from pairing import pairing
from qdefs import qdefs

AHEAD = "  Tournament pairings   "
PHEAD = "  Checker pairings      "

# ==============================


class pairingchecker(commonmain):
    """
    Method: common_main():
    python pairingchecker.py [options]
        -i input-file        # default is stdin
        -o output-file       # default is stdout
        -f TRF | TS | JSON   # use extention
        -e <eventno>         # default is 1, TRF has one event / file
        -b ascii | utf8 | latin1
        -t w | b             # initial color on top ranked player in round 1
        -u [list of illagal pairings]
        -n <no>              # Round to pair, default next round, or all rounds in check mode
        -m <method>          # dutch | berger
        -c                   # check mode, look if tournament pairing is correct
        -a                   # Analyze and show tournament pairing
        -p                   # Dhow the correct pairing of next round (or another round with -n)
        -c [-a] [-p]         # Show correct pairing and explain tournament pairing / checker pairing
        -d @ | T | J         # Print result in result format, text format or JSON formet (default)


    --- Return object ---
        {
         "filetype": "chessjson",
         "version": "1.0",
         "origin": "pairingchecker ver. 1.00",
         "published": "2025-04-14 16:42:21",
         "status": {
             "code": 0,                             # In checkmode 0 for correct, 1 if difference
             "error": []
             },
         "pairingResult" : [                         # Array, 1 element per round
           {
             "round": 3,                             # round number
             "check": True,                          # in check mode, true if equal
             "pairs": [(1,45),(46,2), ...]           # program pairing
             "current": [(1,45),(46,2), ...]         # current pairing from input file
             "analyze": [                            # Tournament analyze array af scorebrackets, may be empty
              {
                "scorelevel": 3                      # internal scorelevel
                "competitors: [6,7,9,12],            # Array of competitor id's
                "pairs": [                           # Array of pair objects
                  {
                    "w": 6,                          # competitor id of white player
                    "b": 19,                         # competitor id of black player, or 0 if PAB
                    "ca": 6,                         # Internal color independed id of player a
                    "cb": 19,                        # Internal color independed id of player b
                    "sa": 5,                         # score level for player a
                    "sb": 5,                         # score level for player b
                    "canmeet": true,                 # If false, then invalid pairing.
                    "psd": 0,                        # difference in scorelevel
                    "played": 0,                     # Number of times these players has met
                    "mode": "S",                     # E: paaired in hetrogenious mode, S: homogenious
                    "quality": [..],                 # Array of c6-c21, q1-q7, see qdefs.py
                    "e-rule": "E.1",                 # Rules used to determine colors
                    "board": 4                       # board number
                     }, { ... }, ...
                    ],
                "downfloaters":  [5, 10, 11],       # Array of downfloated competitors
                "remaining": [13, 14, 15, 16]       # Array of remaining players
                "quality": [..],                    # Array of c6-c21, q1-q7, see qdefs.py
                "valid": true                       # Is bracket valid
              }, {...}, ...
             ]
             "checker": [...]                       # Pairing array af scorebrackets, may be empty, same format as analyze
             "competitors": [                       # Array of competitors
              {
                "cid": 6,                           # competitor id
                "pts": 2.0,                         # points so far
                "acc": 2.0,                         # point + accelerated
                "rfp": true,                        # present (ready for pairing)
                "pop": 19,                          # paired opponent
                "pco": "w",                         # paired color
                "hst": {                            # history
                  "val": "19w",                     # current
                  "1": "32w",
                  "2": "23b"
                },
                "num": 2,                           # number of played games
                "rip": 2,                           # number of rounds paired
                "met": {                            # opponents met
                  "val": 2,
                  "1": 32,
                  "2": 23
                },
                "cod": 0,                           # color difference
                "cop": "w0",                        # color preference
                "csq": " wb",                       # color sequence
                "flt": 0,                           # float bitwise 1=df, 2=up, 3=df prev r, 4 uf prev r
                "top": false,                       # topscorer
                "mdp": 0,                           # moved down
                "lmb": -1,                          # limbo in scorelevel
                "scorelevel": 5,                    # scorelevel
              }
             "level2score": [-1.0,0.0, ...]         # Translate scorelevel to acc
            }
          ]
        }
    """

    def __init__(self):
        super().__init__()
        ver = version.version()
        self.origin = "pairingchecker ver. " + ver["version"]
        self.resulttype = "pairingResult"

    def read_command_line(self):
        self.parser.add_argument("-a", "--analyze", required=False, action="count", default=0, help="Analyze pairing")
        self.parser.add_argument("-p", "--pairing", required=False, action="count", default=0, help="Do pairing")
        self.parser.add_argument("-m", "--method", required=False, action="store_true", help="dutch | berger")
        self.parser.add_argument("-t", "--top-color", required=False, default=" ", help="Color on top board")
        self.parser.add_argument("-u", "--unpaired", required=False, nargs="*", default=[])
        self.read_common_command_line(self.origin, True)

    def write_text_pairing(self, lines, pairs):
        lines.append(str(len(pairs)))
        for w, b in pairs:
            lines.append(str(w) + " " + str(b))

    def write_text_diff(self, lines, apairs, ppairs):
        eq = True
        head = PHEAD + AHEAD
        for i in range(max(len(apairs), len(ppairs))):
            apair = (str(apairs[i][0]) + "  - " + str(apairs[i][1])) if i < len(apairs) else "-"
            ppair = (str(ppairs[i][0]) + "  - " + str(ppairs[i][1])) if i < len(ppairs) else "-"
            if apair != ppair:
                if head:
                    lines.append(head)
                    head = None
                    eq = False
                apos = apair.find("-")
                a = "         "[apos:] + apair + "                         "[: 15 + apos - len(apair)]
                ppos = ppair.find("-")
                p = "         "[ppos:] + ppair + "                         "[: 15 + ppos - len(ppair)]
                lines.append(p + a)
        return eq

    def xxwrite_text_diff(self, lines, analyze, pairing):
        eq = True
        apairs = []
        ppairs = []
        for pairs, result in [(apairs, analyze), (ppairs, pairing)]:
            for bracket in result:
                if bracket is not None and "pairs" in bracket:
                    for pair in bracket["pairs"]:
                        pairs.append(pair)
        apairs = sorted(apairs, key=lambda c: (c["board"]))
        ppairs = sorted(ppairs, key=lambda c: (c["board"]))
        head = PHEAD + AHEAD
        for i in range(max(len(apairs), len(ppairs))):
            apair = (str(apairs[i]["w"]) + "  - " + str(apairs[i]["b"])) if i < len(apairs) else "-"
            ppair = (str(ppairs[i]["w"]) + "  - " + str(ppairs[i]["b"])) if i < len(ppairs) else "-"
            if apair != ppair:
                if head:
                    lines.append(head)
                    head = None
                    eq = False
                apos = apair.find("-")
                a = "         "[apos:] + apair + "                         "[: 15 + apos - len(apair)]
                ppos = ppair.find("-")
                p = "         "[ppos:] + ppair + "                         "[: 15 + ppos - len(ppair)]
                lines.append(p + a)
        return eq

    def write_text_details(self, lines, analyze, pairing, competitors):
        eq = True
        cr = self.pairingengine.crosstable
        if analyze and pairing:
            alen = sum([len((bracket["pairs"] if bracket is not None and "pairs" in bracket else [])) for bracket in analyze])
            plen = sum([len((bracket["pairs"] if bracket is not None and "pairs" in bracket else [])) for bracket in pairing])
            eq = eq and (alen == plen)

        for bno in range(max(len(pairing), len(analyze))):
            allcompetitors = acmps = pcmps = apairs = ppairs = adown = pdown = []
            bsn = {}
            if analyze:
                work = analyze
                if bno < len(analyze):
                    scorelevel = analyze[bno]["scorelevel"]
                    bsn = "bsn-" + str(scorelevel)
                    # print(bsn, analyze[bno]['competitors'])
                    allcompetitors = acmps = sorted(
                        [competitors[c] for c in analyze[bno]["competitors"]], key=lambda s: (-s["scorelevel"], s["cid"])
                    )
                    bsn = analyze[bno]["bsne"]
                    apairs = (
                        sorted(analyze[bno]["pairs"], key=lambda c: (c["board"]))
                        if bno < len(analyze) and bno < len(analyze)
                        else []
                    )
                    acomp = pcomp = {c["cid"]: c for c in allcompetitors}
                    aopp = {
                        **{c["w"]: str(c["b"]) + "w" for c in apairs},
                        **{c["b"]: str(c["w"]) + "b" for c in apairs},
                        **{c: "down" for c in analyze[bno]["downfloaters"]},
                    }
                    adown = sorted(
                        [c for c in analyze[bno]["downfloaters"]], key=lambda s: (-pcomp[s]["scorelevel"], pcomp[s]["cid"])
                    )
                else:
                    allcompetitors = acmps = bsn = apairs = adown = []
                    aopp = {}
            if pairing:
                work = pairing
                scorelevel = pairing[bno]["scorelevel"]
                allcompetitors = pcmps = sorted(
                    [competitors[c] for c in pairing[bno]["competitors"]], key=lambda s: (-s["scorelevel"], s["cid"])
                )
                bsn = pairing[bno]["bsne"]
                pcomp = {c["cid"]: c for c in allcompetitors}
                ppairs = (
                    sorted(pairing[bno]["pairs"], key=lambda c: (c["board"])) if bno < len(pairing) and bno < len(pairing) else []
                )
                popp = {
                    **{c["w"]: str(c["b"]) + "w" for c in ppairs},
                    **{c["b"]: str(c["w"]) + "b" for c in ppairs},
                    **{c: "down" for c in pairing[bno]["downfloaters"]},
                }
                pdown = sorted([c for c in pairing[bno]["downfloaters"]], key=lambda s: (-pcomp[s]["scorelevel"], pcomp[s]["cid"]))

            if len(acmps) > 0 and len(pcmps) > 0 and [c["cid"] for c in acmps] != [c["cid"] for c in pcmps]:
                aopp = {}
                acmps = None

            df = [" ", "D", "U", "B"]
            if len(allcompetitors) > 0:  # Dont print brackets without competitors
                # print("Scorelevel", work[bno]['scorelevel'])
                scorelevel = work[bno]["scorelevel"]
                scorebracket = str(cr.level2score[scorelevel]) if work[bno] is not None and len(cr.level2score) > scorelevel else "--"
                lines.append(
                    "== Bracket: " + scorebracket + ", scorelevel: " + str(scorelevel) + (", PAB" if work[bno]["pab"] else "")
                )
                #         3   4    5    5          5                         2  3  3
                line = "SNO BSN  PTS" + ("    P" if len(pcmps) else "") + ("    A" if acmps else "") + " T CP CD F1 F2"
                l0 = allcompetitors[0]["hst"]
                line += "".join([f"{key:>5}" for key in l0.keys() if isinstance(key, int)])
                lines.append(line)
                # print([c['cid'] for c in competitors])
                # print(pairing[bno]['competitors'])
                # print(analyze[bno]['competitors'])
                # print(popp)
                # print(aopp)
                # print([(c['w'], c['b']) for c in ppairs])
                # print([(c['w'], c['b']) for c in apairs])
                # print([c['cid'] for c in allcompetitors])
                colorprefs = defaultdict(int)
                for cmp in allcompetitors:
                    try:
                        line = (
                            f"{cmp['cid']:>3}"
                            + f"{bsn[cmp['cid']] if cmp['cid'] in bsn else '?':>4}"
                            + f"{cmp['acc']:>5}"
                            + (f"{popp[cmp['cid']]:>5}" if len(pcmps) else "")
                            + (f"{aopp[cmp['cid']]:>5}" if acmps and len(acmps) else "")
                            + " "
                            + ("T" if cmp["top"] else " ")
                            + " "
                            + cmp["cop"]
                            + " "
                            + f"{cmp['cod']:>2}"
                            + "  "
                            + df[cmp["flt"] % 4]
                            + "  "
                            + df[(cmp["flt"] // 4) % 4]
                        )
                    except:
                        pass
                        # breakpoint()
                    line += "".join([f"{val:>5}" for key, val in cmp["hst"].items() if isinstance(key, int)])
                    lines.append(line)
                    cop = cmp["cop"].replace("  ", "nc")
                    colorprefs[cop] += 1
                    colorprefs[cop[:1]] += 1
                lines.append("")
                line = "Colors:   "
                lines.append(line)
                for i in range(3):
                    w = "w" + str(i)
                    b = "b" + str(i)
                    line = "      " + w + ": " + f"{colorprefs.get(w, 0):>3}" + "   " + b + ": " + f"{colorprefs.get(b, 0):>3}"
                    lines.append(line)
                line = (
                    "Tot:  "
                    + "wc: "
                    + f"{colorprefs.get('w', 0):>3}"
                    + "   bc: "
                    + f"{colorprefs.get('b', 0):>3}"
                    + "   nc: "
                    + f"{colorprefs.get('n', 0):>3}"
                )
                # print("Col:", colorprefs.get("n", 0),
                #      colorprefs.get("w0", 0),
                #      colorprefs.get("w", 0),
                #      colorprefs.get("b0", 0),
                #      colorprefs.get("b", 0),
                #      analyze[bno]['quality'][qdefs.C6.value],
                #      analyze[bno]['quality'][qdefs.C12.value],
                #      analyze[bno]['quality'][qdefs.C13.value]
                #      )
                lines.append(line)
                lines.append("")

                sno = "tpn" if "TPN" in self.params["experimental"] else "cid"
                line = "Pairs    :    Pairing      BSN        Analyze      BSN    "
                lines.append(line)
                for pno in range(max(len(ppairs), len(apairs))):
                    pp = format_pair(ppairs[pno], pcomp, bsn, sno) if pno < len(ppairs) else ""
                    ap = format_pair(apairs[pno], acomp, bsn, sno) if pno < len(apairs) else ""
                    arrow = "       <=======  " if eq else ""
                    eq = eq and (pp == ap)
                    arrow = arrow if not eq else ""
                    line = "          " + f"{pp:>24}" + f"{ap:>24}" + arrow
                    lines.append(line)
                line = "Down     :"
                for pno in range(max(len(pdown), len(adown))):
                    pp = format_down(pdown[pno], pcomp, bsn) if pno < len(pdown) else ""
                    ap = format_down(adown[pno], acomp, bsn) if pno < len(adown) else ""
                    eq = eq and (pp == ap)
                    line += f"{pp:>24}" + f"{ap:>24}"
                    lines.append(line)
                    line = "          "
                lines.append("")

                head = "Rule " + (PHEAD if len(pairing) > 0 else "") + (AHEAD if len(analyze) > 0 else "")
                lines.append(head)
                for i in range(24):  # (crosstable.IW):

                    label = qdefs(i).name
                    p = str(pairing[bno]["quality"][i] if bno < len(pairing) else "")
                    a = str(analyze[bno]["quality"][i] if bno < len(analyze) else "")
                    label = f"{label:<5}"
                    plen = len(PHEAD) if len(p) > 0 else 0
                    alen = len(AHEAD) if len(a) > 0 else 0
                    maxlen = len(AHEAD) - 1

                    while len(p) or len(a):
                        (ppart, p) = spilt_my_line(p, maxlen, ",")
                        (apart, a) = spilt_my_line(a, maxlen, ",")
                        line = label + format("  " + ppart, "<" + str(maxlen + 1)) + format("  " + apart, "<" + str(maxlen + 1))
                        label = "     "
                        lines.append(line)
                lines.append("")
        return eq

    def write_text_file(self, f, result, delimiter):
        lines = []
        eq = True
        for rndpairing in result:
            analyze = rndpairing["analyze"]
            pairing = rndpairing["checker"]
            competitors = rndpairing["competitors"]

            if not self.docheck:
                self.write_text_pairing(lines, rndpairing["pairs"])
                lines.append("")
            else:
                lines.append("================= Round #" + str(rndpairing["round"]) + " =================")
                if self.doanalyze or self.dopairing:
                    eq = eq and self.write_text_details(lines, analyze, pairing, competitors)
                else:
                    eq = self.write_text_diff(lines, rndpairing["current"], rndpairing["pairs"]) and eq
                lines.append("")
        f.writelines(line + "\n" for line in lines)
        print("Check:", eq)
        # if not eq: breakpoint()
        return eq

    def compute_tiebreak(self, chessfile, tb, eventno, params):
        if chessfile.get_status() == 0:
            tblist = ["PTS", "ACC", "RFP", "NUM", "RIP", "COD", "COP", "CSQ", "FLT", "TOP"]
            for pos in range(0, len(tblist)):
                mytb = tb.parse_tiebreak(pos + 1, tblist[pos])
                tb.compute_tiebreak(mytb)
            # for i in range(0, len(tb.rankorder)):
            #     t = tb.rankorder[i]

    def compute_pairs(self, pairing):
        # pairing = analyze if pairing is None or len(pairing) == 0 else pairing
        pairs = []
        for bracket in pairing:
            if bracket is not None and "pairs" in bracket:
                for pair in bracket["pairs"]:
                    pairs.append(pair)
        return [(pair["w"], pair["b"]) for pair in sorted(pairs, key=lambda c: (c["board"]))]

    def compute_pairing(self, chessfile, pairingengine, params):
        # print('PARAMS', params)
        self.pairingengine = pairingengine
        analyze = pairing = []
        acompetitors = pcompetitors = {}
        if self.doanalyze or (self.docheck and not self.doanalyze and not self.dopairing):
            analyze = pairingengine.compute_pairing(True, self.doanalyze)
            acompetitors = sorted(
                [{key: value for (key, value) in c.items() if key != "opp"} for c in pairingengine.crosstable.crosstable],
                key=lambda c: (c["cid"]),
            )

        if self.dopairing or (self.docheck and not self.doanalyze and not self.dopairing):
            pairing = pairingengine.compute_pairing(False, self.dopairing)
            pcompetitors = sorted(
                [{key: value for (key, value) in c.items() if key != "opp"} for c in pairingengine.crosstable.crosstable],
                key=lambda c: (c["cid"]),
            )
        result = {
            "round": pairingengine.rnd,
            "check": self.docheck,
            "pairs": self.compute_pairs(pairing),
            "current": self.compute_pairs(analyze),
            "analyze": [],
            "checker": [],
            "competitors": [],
            "level2score": pairingengine.crosstable.level2score,
        }
        if self.docheck:
            result["analyze"] = analyze
            result["checker"] = pairing
            result["competitors"] = pcompetitors if len(pcompetitors) >= len(acompetitors) else acompetitors

        # chessfile.chessjson["status"]["code"] = 1
        return result

    def do_checker(self):
        params = self.params
        chessfile = self.chessfile
        chessfile.result = []
        if chessfile.get_status() == 0:
            if self.tournamentno > 0:
                tournament = chessfile.get_tournament(self.tournamentno)
                currentround = tournament["currentRound"]
                numrounds = tournament["numRounds"]
                firstround = lastround = params["number_of_rounds"]
                self.dopairing = params["pairing"]
                self.docheck = params["check"]
                self.doanalyze = params["analyze"]
                if firstround == -1:
                    if self.dopairing:
                        firstround = lastround = currentround + 1
                    if self.doanalyze:
                        firstround = lastround = currentround
                    if self.docheck:
                        firstround = 1
                        lastround = currentround
                if lastround > numrounds:
                    self.error(504, "Number of rounds = " + str(numrounds) + ", can't pair round " + str(lastround))
                params["is_rr"] = False
                topcolor = chessjson.get_topcolor(chessfile, self.tournamentno, params["top_color"])
                for rnd in range(firstround, min(numrounds, lastround) + 1):
                    tb = tiebreak(chessfile, self.tournamentno, rnd - 1, None)
                    self.compute_tiebreak(chessfile, tb, self.tournamentno, params)
                    cpairing = pairing(
                        chessfile,
                        self.tournamentno,
                        rnd,
                        topcolor,
                        params["unpaired"],
                        1,
                        params["experimental"],
                        params["verbose"],
                    )
                    result = self.compute_pairing(chessfile, cpairing, params)
                    chessfile.result.append(result)
                    # print("================= Round #" + str(rnd )+ " =================")
        self.core = result
        # print('self.core')
        # json_output('-', self.core)


# tournament.export_trf(params)


# run program
if __name__ == "__main__":
    sys.set_int_max_str_digits(15000)
    start_time = time.time()
    pch = pairingchecker()
    code = pch.common_main()
    if "time" in pch.params["experimental"]:
        print("--- %s seconds ---" % (time.time() - start_time))
