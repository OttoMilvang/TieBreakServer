# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import sys

import helpers
import version
from commonmain import commonmain
from tiebreak import tiebreak

# ==============================


class tiebreakchecker(commonmain):

    def __init__(self):
        super().__init__()
        ver = version.version()
        self.origin = "tiebreakchecker ver. " + ver["version"]
        self.resulttype = "tiebreakResult"

    # read_command_line
    #   options:
    #   -c = check
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format
    #   -b = encoding
    #   -e = tournament-number
    #   -n = number-of-rounds
    #   -p = use rules for tournament with pre-determined pairing (Round Robin)
    #   -s = use rules for swiss tournament
    #   -g = game-score
    #   -m = match-score
    #   -d = delimiter
    #   -r = sort on rank order
    #   -u = set rating for unrated players
    #   -t = tie-break
    #   -v = verbose and debug
    #   -x = experimental

    def read_command_line(self):
        self.parser.add_argument(
            "-p",
            "--pre-determined",
            required=False,
            action="store_true",
            help="Use rules for tournament with pre-determined pairing",
        )
        self.parser.add_argument("-s", "--swiss", required=False, action="store_true", help="Use rules for swiss tournament")
        self.parser.add_argument("-r", "--rank", required=False, action="store_true", help="Sort on rank order")
        self.parser.add_argument("-u", "--unrated", required=False, default=0, help="rating for unrated players")
        self.parser.add_argument(
            "-t",
            "--tie-break",
            required=False,
            nargs="*",
            default=[],
            # default=['PTS', 'DE'],
            help="Delimiter in output text",
        )
        self.read_common_command_line(self.origin, True)

        # Parse game-score and match-score
        for scoretype in ["game", "match"]:
            if scoretype + "_score" in self.params and self.params[scoretype + "_score"] is not None:
                scoresystem = {}
                for arg in self.params[scoretype + "_score"]:
                    for param in arg.split(","):
                        param = param.replace("=", ":")
                        args = param.split(":")
                        scoresystem[args[0]] = helpers.parse_float(args[1])
                self.params[scoretype + "_score"] = scoresystem


    def write_text_file(self, f, result, delimiter):
        if self.params["rank"]:
            sortorder = sorted(result["competitors"], key=lambda cmp: (cmp["rank"], cmp["cid"]))
            header = ["Rank", "StartNo"]
            field = ["rank", "cid"]
        else:
            sortorder = result["competitors"]
            header = ["StartNo", "Rank"]
            field = ["cid", "rank"]
        line = header[0] + delimiter + header[1]
        for arg in self.params["tie_break"]:
            line += delimiter + arg
        f.write(line + "\n")
        for competitor in sortorder:
            line = str(competitor[field[0]]) + delimiter + str(competitor[field[1]])
            for val in competitor["tiebreakScore"]:
                if "." in str(val):
                    line += delimiter + str(val)
                else:
                    line += delimiter + str(val)
            f.write(line + "\n")

    def do_checker(self):
        params = self.params
        if params["check"]:
            self.filetype = "tiebreak"
        chessfile = self.chessfile
        if chessfile.get_status() == 0:
            if self.tournamentno > 0:
                tb = tiebreak(chessfile, self.tournamentno, params["number_of_rounds"], params)
                tb.compute_tiebreaks(chessfile, self.tournamentno, params)
            else:
                tb = tiebreak(chessfile, self.tournamentno, params["number_of_rounds"], params)
        self.core = tb


# run program
if __name__ == "__main__":
    tbc = tiebreakchecker()
    code = tbc.common_main()
    sys.exit(code)
