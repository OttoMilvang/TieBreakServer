# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 16:48:53 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import argparse
import base64
import datetime
import io
import json
import sys

import helpers
from chessjson import chessjson
from trf2json import trf2json
from ts2json import ts2json

# ==============================


class commonmain:

    # constructor function
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.params = None
        self.filetype = "chessjson"
        self.resulttype = "chessjsonResult"
        self.origin = "checker, version 1.00"
        self.tournamentno = 1

    def printhelp(self):
        print("checker [options]")

    # error
    #   print error and exit

    def error(self, code, txt):
        chessjson = {
            "filetype": "Error",
            "version": "1.0",
            "origin": self.origin,
            "published": str(datetime.datetime.now())[0:19],
            "status": {"code": 0, "error": []},
        }
        chessjson["status"]["code"] = code
        chessjson["status"]["error"].append(txt)
        json.dump(chessjson, sys.stdout, indent=2)
        if code >= 400:
            sys.exit(code)

    # read_command_line
    #   options:
    #   -@ = program
    #   -c = check
    #   -i = input-file
    #   -o = output-file
    #   -f = file-format
    #   -b = encoding
    #   -e = tournament-number
    #   -n = number-of-rounds
    #   -g = game-score
    #   -m = match-score
    #   -d = delimiter
    #   -v = verbose and debug
    #   -x = experimental


    helptxt = {
        "-c" : "check mode",
        "-i" : "path to input file",
        "-o" : "path to output file",
        "-f" : "filetype, JSON/TRF/TS, default use file-extention and then TRF",
        "-b" : "encoding ascii, utf-8, cp1252 ...",
        "-e" : "tournament number in file, start at 1",
        "-n" : "Number of rounds, overrides file value",
        "-g" : "Point system for matches, default W:2.0,D:1.0,L:0.0,Z:0,P:1.0,U:1.0",
        "-m" : "Point system for games, default W:1.0,D:0.5,L:0.0,Z:0,P:1.0,U:0.5",
        "-d" : "Delimiter in output text, T=tab, B=blank, S=semicolon, C=comma, txt=txt",
        "-x" : "Add experimental stuff",
        "-v" : "Verbose and debug",
        }

    def read_common_command_line(self, strict):
        parser = self.parser
        parser.add_argument("-c", "--check", required=False, action="count", default=0,  help=self.helptxt['-v'])
        parser.add_argument("-i", "--input-file", required=False, default="-", help=self.helptxt['-i'])
        parser.add_argument("-o", "--output-file", required=False, default="-", help=self.helptxt['-o']),
        parser.add_argument("-f", "--file-format", required=False, default="TRF", help=self.helptxt['-f'])
        parser.add_argument("-b", "--encoding", required=False, default="", help=self.helptxt['-b']) 
        parser.add_argument("-e", "--tournament-number", required=False, default=str(self.tournamentno), help=self.helptxt['-e'])
        parser.add_argument("-n", "--number-of-rounds", type=int, default=-1, help=self.helptxt['-n']) 
        parser.add_argument("-g", "--game-score", required=False, nargs="*", help=self.helptxt['-g']) 
        parser.add_argument("-m", "--match-score", required=False, nargs="*", help=self.helptxt['-m']) 
        parser.add_argument("-d", "--delimiter", required=False, help=self.helptxt['-d']) 
        parser.add_argument("-x", "--experimental", required=False, nargs="*", default=[], help=self.helptxt['-x'])
        parser.add_argument("-v", "--verbose", required=False, action="count", default=0, help=self.helptxt['-v'])

        if strict:
            self.params = params = vars(parser.parse_args())
        else:
            self.params = params = vars(parser.parse_known_args())
        #print(params)

        # Parse game-score and match-score
        for scoretype in ["game", "match"]:
            if scoretype + "_score" in params and params[scoretype + "_score"] is not None:
                scoresystem = {}
                for arg in params[scoretype + "_score"]:
                    for param in arg.split(","):
                        param = param.replace("=", ":")
                        args = param.split(":")
                        scoresystem[args[0]] = helpers.parse_float(args[1])
                params[scoretype + "_score"] = scoresystem
        return params

    def read_common_server(self, strict):
        # form = cgi.FieldStorage()
        # helpers.json_output('c:\\temp\\t.txt', form)
        charset = "utf-8"
        sys.stdin.reconfigure(encoding=charset)
        data = sys.stdin.read()
        jsondata = json.loads(data)
        command = jsondata["command"]
        # helpers.json_output('c:\\temp\\t2.txt', command)
        self.params = {
            "service": command["service"],
            "check": command["service"] == "tiebreak",
            "data": base64.b64decode(command["content"]),
            "encoding": command["encoding"] if "encoding" in command else "",
            "input_file": command["filename"],
            "output_file": "-",
            "file_format": helpers.getFileFormat(command["filename"]),
            "tournament_number": str(command["tournamentno"]),
            "number_of_rounds": (int(command["norounds"]) if command["norounds"] != "" else -1),
            "game_score": None,
            "match_score": None,
            "delimiter": None,
            "experimental": False,
            "verbose": 0,
        }
        if self.params["service"] == "tiebreak":
            self.params["tie_break"] = command["tiebreaks"]
            self.params["pre_determined"] = command["tournamenttype"] == "p"
            self.params["swiss"] = command["tournamenttype"] == "s"
        return self.params

    def read_input_file(self):
        # Read an input file
        try:    
            match (self.params["file_format"]):
                case "JSON":
                    chessfile = chessjson()
                    charset = "utf-8"
                case "TRF":
                    chessfile = trf2json()
                    charset = "latin1"

                case "TS":
                    chessfile = ts2json()
                    charset = "ascii"
                case _:
                    self.error(503, "Error in file format: " + self.params["file_format"])

            self.chessfile = chessfile
            if len(self.params["encoding"]) > 0:
                charset = self.params["encoding"]

            if "input_file" not in self.params:
                self.error(501, "Missing parameter --input-file")
            if "output_file" not in self.params:
                self.error(501, "Missing parameter --output-file")
            if "data" in self.params:
                lines = self.params["data"].decode(charset)
            elif self.params["input_file"] == "-":
                sys.stdin.reconfigure(encoding=charset)
                f = sys.stdin
                lines = f.read()
                f.close()
            else:
                f = io.open(self.params["input_file"], mode="r", encoding=charset)
                lines = f.read()
                f.close()

            if charset == "latin1" and lines[0] == "\xef" and lines[1] == "\xbb" and lines[2] == "\xbf":
                lines = lines[3:]
            chessfile.parse_file(lines, self.params["verbose"])
        except:
            filename = "(stdin)" if self.params["input_file"] == "-" else self.params["input_file"]
            chessfile.put_status(401, 'Error reading file: "' + filename + '"')
            raise

    def write_output_file(self):
        params = self.params
        chessfile = self.chessfile
        status = chessfile.chessjson["status"]
        code = status["code"] if "code" in status else 500
        if code == 0 and hasattr(chessfile, "result"):
            result = chessfile.result
            check = result["check"] if "check" in result else False
            code = 0 if check else 1
        else:
            result = None
            check = params["check"]

        if params["output_file"] == "-":
            f = sys.stdout
            if "data" in params:
                f.write("Content-Type: application/json; charset=utf-8\r\n\r\n")
        else:
            f = open(params["output_file"], "w")

        # if params["check"] and self.core is not None:
        if result is not None:
            chessjson = {
                "filetype": self.filetype,
                "version": "1.0",
                "origin": self.origin,
                "published": str(datetime.datetime.now())[0:19],
                "status": status,
                self.resulttype: result,
            }

            if "delimiter" in params and params["delimiter"] is not None and params["delimiter"].upper() != "JSON":
                printcheckstatus = 1 if params["delimiter"][0] == "@" else 0
                delimiter = params["delimiter"][printcheckstatus:]
                tr = {"B": " ", "T": "\t", "C": ",", "S": ";"}
                if delimiter.upper() in tr:
                    delimiter = tr[delimiter.upper()]
                if printcheckstatus:
                    f.write(str(code) + (delimiter + str(check) if len(delimiter) > 0 else "") + "\n")
                if (code == 0 or code == 1) and len(delimiter) > 0:
                    self.write_text_file(f, result, delimiter)
            else:
                helpers.json_output(f, chessjson)
        else:
            helpers.json_output(f, chessfile.chessjson)
        if not params["output_file"] == "-":
            f.close()
        return code

    def common_main(self):
        # Read command line
        try:
            self.read_command_line()
        except:
            raise
            self.error(501, "Bad command line")
        params = self.params
        try:
            self.read_input_file()

        except:
            if params["verbose"] > 0:
                raise
            stat = self.chessfile.chessjson["status"]
            if stat["code"] > 0:
                self.error(stat["code"], stat["error"])
            self.error(502, "Error when reading file: " + params["input_file"])

        if "tournament_number" not in self.params:
            self.error(501, "Missing parameter --tournament-number")
        self.tournamentno = helpers.parse_int(self.params["tournament_number"])
        if self.tournamentno < 0 or self.tournamentno > len(self.chessfile.event["tournaments"]):
            self.error(501, "Invalid parameter --tournament-number")

        # Add command line parameters
        for score in ["game", "match"]:
            if score + "_score" in params and params[score + "_score"] is not None:
                for arg in params[score + "_score"]:
                    self.chessfile.parse_score_system(score, arg)

        self.do_checker()

        try:
            code = self.write_output_file()
            if 'DUMP' in params["experimental"]:
                self.chessfile.dumpresults()
        except:
            if params["verbose"] > 0:
                raise
            self.error(503, "Error when writing file: " + params["output_file"])
        return code
