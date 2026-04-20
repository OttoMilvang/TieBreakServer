#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 25 08:16:13 2024
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import json
import sys
from convert import convert2jch
import helpers
from pairingchecker import pairingchecker
from tiebreakchecker import tiebreakchecker
import version
from commonmain import commonmain
from tiebreak import tiebreak
from pairing import pairing


"""
==============================
Request:
{
    "filetype": "convert request" | "tiebreak request" ,
    "version": "1.0",
    "origin": "<Free text>",
    "published": "<date on format 2018-08-14 05:07:44>",
    "options": {
        "service" : "convert" | tiebreak,
        "input_filename" : "<original file name>",
        "input_filetype": "TRF" | "TS" | < other known format >,
        "data": ["<lines with base 64 encoded file>"],
        "tournament_number": <0 or tournamentno to convert>,
        "current_round": <int>,
        "number_of_rounds": <int>,
        // parameters for tiebreaks
            "tiebreak" : [string list],
            "pre-determined" : true | false,
            "swiss" : true | false, 
            "unrated" : <rating for unrated players>,
        // parameters for pairing   
            "pairing" : true | false,
            "method" : "dutch",
            "top_color" : "white" | "black",
            "maxmeets" : <int>,
            "unpaired" : [<cid>, …],
            "analysis" : true | false,  }

    }
}

Response:
{
    "filetype": "convert response" | "tiebreak response",
    "version": "1.0",
    "origin": "chessserver ver. 1.04",
    "published": "2024-10-01 14:32:16",
    "status": {
        "code": 0,
        "error": []
    },
    "convertResult": {
        <Json chess file>
    }
    "tiebreakResult": {
        "check": false,
        "tiebreaks": [ … ],
        "competitors": [ {
            "cid": <cid>,
            "rank": <rank>,
            "tiebreakScore": [ … ],
            "boardPoints": { … },
            "tiebreakDetails": [{ … }, … ]
    }
}


"""


class chessserver(commonmain):

    methods = {
         "convert":  convert2jch,  
         "tiebreak": tiebreakchecker, 
         "pairing":  pairingchecker 
         }


    def __init__(self):
        super().__init__()
        self.origin = "chessserver ver. " + version.version()["version"]
        self.tournamentno = 0

    def read_command_line(self):
        # form = cgi.FieldStorage()
        # helpers.json_output('c:\\temp\\t.txt', form)
        charset = "utf-8"
        sys.stdin.reconfigure(encoding=charset)
        data = sys.stdin.read()
        jsondata = json.loads(data)
        command = jsondata["command"]
        # helpers.json_output('c:\\temp\\t2.txt', command)
        self.params = {
            "service": "",
            "input_file": "@",
            "output_file": "-",
            "output_format": "JSON",
            "encoding": "ascii",
            "tournament_number": 1,
            "current_round": -1,
            "delimiter": None,
            "check": False,
            "experimental": [],
            "verbose": 0,
        }

        self.params.update(command)
        if "input_format" not in self.params:
            self.params["input_format"] = helpers.getFileFormat(command["input_file"])
        self.baseclass = self.methods.get(self.params["service"], convert2jch)()
        self.baseclass.params = self.params
        self.baseclass.resultjson["options"] = self.params
        return self.params

    def read_input_file(self):
        self.baseclass.read_input_file()
        
    def test_tournamentno(self):
        self.baseclass.test_tournamentno()

    def test_add_score(self):
        self.baseclass.test_add_score()

    def write_text_file(self, f, result, delimiter):
        pass

    def do_checker(self):
        self.baseclass.do_checker()
        return

    def apply_result(self):
         self.baseclass.apply_result()
         self.chessfile = self.baseclass.chessfile
         self.resultjson = self.baseclass.resultjson
         pass

    def write_output_file(self):
        self.baseclass.write_output_file()


# run program
jch = chessserver()
code = jch.common_main()
sys.exit(code)
