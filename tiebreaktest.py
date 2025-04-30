# -*- coding: utf-8 -*-
"""
Created on Fri Apr 18 08:14:29 2025

@author: otto
"""

import json
import io
import helpers
import unittest
import tiebreakchecker
from pathlib import Path

FILEPATH = "../otestfiles/"
REFPATH = "../testjson/"

FILEPATH = "C:/Users/otto/Dropbox/Privat/spp/TieBreakChecker/otestfiles/"
FILEPATH = str(Path(__file__).parent.parent.absolute()) + "/unittest/tiebreakchecker/testfiles/"
REFPATH = str(Path(__file__).parent.parent.absolute()) + "/unittest/tiebreakchecker/references/"
RESPATH = str(Path(__file__).parent.parent.absolute()) + "/unittest/tiebreakchecker/results/"

TESTFILES = {
    "test1": { "type": "S", "team": False, "input_file" : "test1.trf", },
    "rrheld": { "type": "R", "team": False, "input_file" : "Round-Robin-Example.trf", },
    "t6681": { "type": "R", "team": False, "input_file" : "t6681.trf", },
    "swiss5held": { "type": "S", "team": False, "input_file" : "Swiss-5-Example.trf", },
    "swiss9held": { "type": "S", "team": False, "input_file" : "Swiss-9-Example.trf", },
    "nmunm24": { "type": "S", "team": False, "input_file" : "NMU-NMforbarnogungdom2024.trx", 
              "file_format" : "TS", 'tournament_number': '6', },
    #"teamheld": { "type": "S", "team": True, "input_file" : "team-Example.trf", }, 
    "elite": { "type": "R", "team": False, "input_file" : "elite19-20.trf" }, 
    "nccteam22": { "type": "S", "team": False, "input_file" : "nmlag2022.trf"}, 
#              "file_format" : "TS", 'tournament_number': '1', },

    }


TIEBREAKS = {
  "in-nu" : { "team": False, "tie_break": ["WIN", "WON", "BPG", "BWG", "REP"] }, 
  "tm-nu" : { "team": True, "tie_break": ['WIN:MP', 'WON:MP']  },
  "in-de" : { "team": False, "tie_break": ["DE", "DE/P"] }, 

  "co-ps" : { "team": False, "tie_break": ["PS", "PS/C1", "PS/C2 "] },
  "co-ks" : { "team": False, "tie_break": ["KS", "KS/L40", "KS/L-2"] }, 
  "co-bh" : { "team": False, "tie_break": ["ABH", "BH", "BH/C1", "BH/C2", "BH/M1", "BH/M2", "BH/P", 
                                            "ABH/P", "BH/C1/P", "BH/C2/P", "BH/M1/P", "BH/M2/P"] }, 
  "co-fb" : { "team": False, "tie_break": ["AFB", "FB", "FB/C1", "FB/C2", "FB/M1", "FB/M2", "FB/P", 
                                            "AFB/P", "FB/C1/P", "FB/C2/P", "FB/M1/P", "FB/M2/P"] },
  "in-sb" : { "team": False, "tie_break": ["SB", "SB/C1", "SB/C2", "SB/P", "SB/C1/P", "SB/C2/P"] }, 
  "co-ab" : { "team": False, "tie_break": ["AOB", "AOB/F"] },
  "in-rg" : { "team": False, "tie_break": ["ARO", "ARO/C1", "ARO/C2", "ARO/M1", "ARO/M2", "TPR", "PTP", "APRO", "APPO"] },

  "tm-bc" : { "team": True, "tie_break": ['TBR', 'BBE', 'BC'] },
  "tm-de" : { "team": True, "tie_break": ['EDE', 'EDE/P'] },

  "gg-sb" : { "team": True, "tie_break": ['ESB:GG', 'ESB:GG/C1', 'ESB:GG/C1/P', 'ESB:GG/C2', 'ESB:GG/C2/P', 'ESB:GG/P'] },
  "gm-sb" : { "team": True, "tie_break": ['ESB:GM', 'ESB:GM/C1', 'ESB:GM/C1/P', 'ESB:GM/C2', 'ESB:GM/C2/P', 'ESB:GM/P'] },
  "mg-sb" : { "team": True, "tie_break": ['ESB:MG', 'ESB:MG/C1', 'ESB:MG/C1/P', 'ESB:MG/C2', 'ESB:MG/C2/P', 'ESB:MG/P'] },
  "mm-sb" : { "team": True, "tie_break": ['ESB:MM', 'ESB:MM/C1', 'ESB:MM/C1/P', 'ESB:MM/C2', 'ESB:MM/C2/P', 'ESB:MM/P'] },

  "mg-gm" : { "team": True, "tie_break": ['MPvGP'] },
  "tm-ss" : { "team": True, "tie_break": ['SSSC', 'SSSC/F', 'SSSC/F/K5', 'SSSC/F/P', 'SSSC/F/P/K5', 
                                           'SSSC/K5', 'SSSC/P', 'SSSC/P/K5'] },
 
}

class TestTiebreakMethods(unittest.TestCase):


    def get_parms(self, tb, tiebreaks, test, testfile, pts):
        params = {
            "file_format" : "TRF",
            "encoding" : "latin1", 
            "input_file" : "",
            "output_file" : "-",
            "pre_determined": False, 
            "swiss": False, 
            'rank': True, 
            'unrated': 0, 
            'testname': tb, 
            'tie_break': tiebreaks, 
            'check': 1,
            'tournament_number': '1', 
            'number_of_rounds': -1, 
            'game_score': None, 
            'match_score': None, 
            'delimiter': None, 
            'experimental': [], 
            'is_rr': None,
            "verbose": 0,
            }
        ptsprefix = ".". pts[0].lower() if len(pts) == 4 else ""
        for elem in [tiebreaks, testfile]:
            for (key, value) in elem.items():
                params[key] = value
        params['input_file'] = FILEPATH + testfile["input_file"]
        params['txt_file'] = REFPATH + test + ptsprefix + "."  + tb + "." + "txt"
        params['json_file'] = REFPATH + test + ptsprefix  + "."  + tb + "." + "json"
        params['txtout_file'] = RESPATH + test + ptsprefix  + "."  + tb + "." + "txt"
        params['jsonout_file'] = RESPATH + test + ptsprefix  + "."  + tb + "." + "txt"
        return params

        
    def read_tiebreak(self, params, tresult, jresult):
        res = []
        for (jsonload, filename, result) in [(False, params["txt_file"], tresult), (True, params["json_file"], jresult)]:
            try:
                f = io.open(filename, mode="r", encoding="utf8")
                lines = f.read()
                f.close()
                reference = json.loads(lines) if jsonload else lines
            except:
                yn = helpers.query_yes_no(filename + " not found, create?", "yes")
                if True:
                    if jsonload:
                        helpers.json_output(filename, jresult)
                        reference = jresult
                    else:
                        helpers.txt_output(filename, tresult)
                        reference = tresult
            res.append(reference)
        return (res[0], res[1])                    


    def compute_tiebreak(self, params):
        self.tbc = tbc = tiebreakchecker.tiebreakchecker()
        tbc.params = params

        tbc.read_input_file()
        tbc.do_checker()
        jresult = tbc.chessfile.result
        jresult = json.loads(json.dumps(jresult, default=helpers.decimal_serializer))
        f = io.StringIO()
        self.tbc.write_text_file(f, jresult, '\t')
        helpers.json_output(params['jsonout_file'], jresult)
        tresult = f.getvalue()
        helpers.txt_output(params['txtout_file'], tresult)
        return (tresult, jresult)
        
    def run_tiebreaktest(self, tb, tiebreaks, test, testfile, pts):
        params = self.get_parms(tb, tiebreaks, test, testfile, pts)
        (tresult, jresult) = self.compute_tiebreak(params)
        (treference, jreference) = self.read_tiebreak(params, tresult, jresult)
        self.assertEqual(tresult, treference, "Failed on test " + tiebreaks['tie_break'][1] + " tiebreak")
        self.assertEqual(jresult, jreference, "Failed on test " + tiebreaks['tie_break'][1] + " details")

    def run_all(self, tb, team, pts, typ):
        for (test, testfile) in TESTFILES.items():
            if testfile['type'] in typ and team == testfile['team']:
                for tbt in TIEBREAKS[tb]["tie_break"]:
                    self.run_tiebreaktest(tb + "-" + tbt.replace('/','-').replace(':','.').lower(), { "tie_break" : [pts, tbt, "SNO"] }, test, testfile, pts)


    def test_nu(self):
        self.run_all("in-nu", False, "PTS", "SR")
        self.run_all("tm-nu", True, "MPTS", "SR")

    def test_de(self):
        self.run_all("in-de", False, "PTS", "SR")
        self.run_all("tm-de", True, "MPTS", "SR")
        self.run_all("tm-de", True, "GPTS", "SR")

    def test_ps(self):
        self.run_all("co-ps", False, "PTS", "S")
        self.run_all("co-ps", True, "MPTS", "S")
        self.run_all("co-ps", True, "GPTS", "S")

    def test_ks(self):
        self.run_all("co-ks", False, "PTS", "R")
        self.run_all("co-ks", True, "MPTS", "R")
        self.run_all("co-ks", True, "GPTS", "R")

    def test_sb(self):
        self.run_all("in-sb", False, "PTS", "SR")
        self.run_all("mm-sb", True, "MPTS", "SR")
        self.run_all("mg-sb", True, "MPTS", "SR")
        self.run_all("gm-sb", True, "GPTS", "SR")
        self.run_all("gg-sb", True, "GPTS", "SR")


    def test_bh(self):
        self.run_all("co-bh", False, "PTS", "S")
        self.run_all("co-bh", True, "MPTS", "S")
        self.run_all("co-bh", True, "GPTS", "S")

    def test_fb(self):
        self.run_all("co-fb", False, "PTS", "S")
        self.run_all("co-fb", True, "MPTS", "S")
        self.run_all("co-fb", True, "GPTS", "S")

    def test_ab(self):
        self.run_all("co-ab", False, "PTS", "S")
        self.run_all("co-ab", True, "MPTS", "S")
        self.run_all("co-ab", True, "GPTS", "S")

    def test_rg(self):
        self.run_all("in-rg", False, "PTS", "SR")

    def test_bc(self):
        self.run_all("tm-bc", True, "PTS", "SR")

    def test_mg(self):
        self.run_all("mg-gm", True, "PTS", "SR")

    def test_ss(self):
        self.run_all("tm-ss", True, "PTS", "SR")


if __name__ == '__main__':
    unittest.main()
    