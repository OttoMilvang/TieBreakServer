# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 13:57:55 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
from decimal import Decimal

# ==============================
#
#  Helpers


def parse_date(date):
    datetime = date.split(" ", 1)
    dateparts = datetime[0].split(".")
    if len(dateparts) == 3:
        if len(dateparts[0]) == 4:
            return date.replace(".", "-")
        if len(dateparts) == 2:
            return dateparts[2] + "-" + dateparts[1] + "-" + dateparts[0] + " " + datetime[1]
        return dateparts[2] + "-" + dateparts[1] + "-" + dateparts[0]
    dateparts = datetime[0].split("/")
    if len(dateparts) == 3:
        if len(dateparts[0]) == 4:
            return date.replace("/", "-")
        return "20" + date.replace("/", "-")
    return date


def parse_minutes(time):
    hms = time.split(":")
    if len(hms) != 3:
        return 0
    return int(hms[0]) * 60 + int(hms[1])


def parse_seconds(time):
    hms = time.split(":")
    if len(hms) != 3:
        return 0
    return int(hms[0]) * 3600 + int(hms[1]) * 60 + int(hms[2])


def parse_int(txt):
    txt = txt.strip()
    if len(txt) == 0:
        return 0
    return int(txt)


def parse_float(txt):
    txt = txt.strip()
    if len(txt) == 0:
        return Decimal("0.0")
    txt = txt.replace(",", ".")
    return Decimal(txt)


def to_base36(num):
    b36 = min(abs(int(num * Decimal("2.0"))), 35)
    return "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[b36]

def from_base36(s):
    if s == '':
        return 0
    b36 = int(s, 36)
    return b36


def spilt_my_line(line, maxlen, delimiter):
    if len(line) < maxlen:
        return(line, "")
    pos = line[:maxlen].rfind(delimiter)
    return(line[:pos+1], line[pos+1:]) 

# return -1 if different
# return 1 if equal
# return 0 if dont know
def is_equal(txt, struct1, struct2):
    if not (txt in struct1 and txt in struct2):
        return 0
    val1 = struct1[txt]
    val2 = struct2[txt]
    if (type(val1) is type(0) and val1 == 0) or (type(val2) is type(0) and val2 == 0):
        return 0
    if (type(val1) is type("") and val1 == "") or (type(val2) is type("") and val2 == ""):
        return 0
    if val1 == val2:
        return 1
    else:
        return -1


#
# Solve point system
# Input array of equations:
# sum = w * W + d * D + l * L + p * P + u * U + z * Z
# Solve w, d, l, p, u, z for variables where W, D, L, P, U and Z present in equautins
#


def solve_scoresystem_p(equations, pab):
    # print(equations)
    score = {"sum": Decimal("0.0"), "W": 0, "D": 0, "L": 0, "P": 0, "U": 0, "Z": 0}
    # print ('PAB:', pab)
    res = {}
    for loss in [Decimal("0.0"), Decimal("0.5"), Decimal("1.0")]:
        res["L"] = loss
        for draw in [loss + Decimal("0.5"), loss + Decimal("1.0"), loss + Decimal("1.5"), loss + Decimal("2.0")]:
            res["D"] = draw
            for win in [
                draw + draw - loss,
                draw + draw - loss + 1,
                draw + draw - loss + Decimal("0.5"),
                draw + draw - loss + Decimal("1.0"),
                draw + draw - loss + Decimal("1.5"),
                draw + draw - loss + Decimal("2.0"),
            ]:
                res["W"] = win
                for unknown in ["D", "L", "W"]:
                    res["U"] = res[unknown]
                    ok = True
                    # if loss != 0.0 or draw != 0.5 or win != 1.0 or unknown != 'D':
                    #    continue
                    for result in equations:
                        tsum = 0
                        tsum += result["W"] * win
                        tsum += result["D"] * draw
                        tsum += result["L"] * loss
                        tsum += result["U"] * res[unknown]
                        res["U"] = unknown
                        res["Z"] =  Decimal("0.0")
                        for key, value in result.items():
                            if key != "pab" and key != "pres":
                                score[key] += value
                        pok = False
                        if result["P"] > 0:
                            for p in pab:
                                # print(tsum, result['P'], res[p],  tsum + result['P'] * res[p], result['sum'])
                                if tsum + result["P"] * res[p] == result["sum"]:
                                    # print('TRUE', result['sum'])
                                    pok = True
                                    result["pres"] = p
                                    res["P"] = res[p]
                        else:
                            # print(tsum, result['P'], result['sum'])
                            pok = tsum == result["sum"]
                        ok = ok and pok

                    if ok:
                        ret = {key: value for key, value in res.items() if score[key] != 0}
                        for key in ["X", "U"]:
                            if key in ret and res[key] in ["W", "D", "L", "Z"] and ret[key] not in ret:
                                ret[res[key]] = res[res[key]]

                        for eq in equations:
                            # print(eq)
                            if "pab" in eq:
                                # print(eq)
                                eq["pab"]["wResult"] = eq["pres"]
                                res.pop("P", None)

                        # print(equations)
                        # print('Score:', score)
                        # print('Ret = ',  ret)
                        return ret
    # print('none')
    # return None


def solve_scoresystem(equations):
    res = False
    res = res or solve_scoresystem_p(equations, ["W"])
    res = res or solve_scoresystem_p(equations, ["D"])
    res = res or solve_scoresystem_p(equations, ["L"])
    res = res or solve_scoresystem_p(equations, ["W", "D"])
    res = res or solve_scoresystem_p(equations, ["D", "L"])
    res = res or solve_scoresystem_p(equations, ["W", "D", "L"])

    return res
    # print(equations)


#
# Function: getFileFormat
# Returns a file format.
#
# Parameters:
#     $filename - Filename of tournament file
#


def getFileFormat(filename):
    parts = filename.split(".")
    lastp = parts[-1].lower()
    # retval = ""
    match lastp:
        case "jch" | "json":
            return "JSON"
        case "txt" | "trf" | "trfx":
            return "TRF"
        case "trx":
            return "TS"
        case _:
            return "JSON"


def sortxval(x):
    return x["val"]


def sortnum(x):
    return x["num"]




# =================
#
# format
#
#

def print_pair(c, pcmps, bsn, sno):
    a = c['w']
    b = c['b']
    sa = ('   ' + str(pcmps[a][sno]))[-3:]
    sb = (str(pcmps[b][sno])+'   ')[0:3]
    ba = ('   ' + (str(bsn[pcmps[a]['cid']]))[-3:]) if pcmps[a]['cid'] in bsn else "  ?"
    bb = ((str(bsn[pcmps[b]['cid']])+'   ')[:3]) if pcmps[b]['cid'] in bsn else "  ?"
    return sa+' - '+sb + " (" + ba+' - '+bb + ")"
    

def print_down(c, pcmps, bsn):
    sa = ('   ' + str(c))[-3:]
    sb = '   '
    ba = ('   ' +str(bsn[pcmps[c]['cid']]))[-3:] if pcmps[c]['cid'] in bsn else "  ?"
    bb = '   '
    return sa+' - '+sb + " (" + ba+' - '+bb + ")"

# =================
#
# rating selector
#
#

def rating_fide(fide, nrs):
    return fide

def rating_nro(fide, nrs):
    return nrs

def rating_fidon(fide, nrs):
    return fide if fide > 0 else nrs

def rating_nidof(fide, nrs):
    return nrs if nrs > 0 else fide

def rating_hbfn(fide, nrs):
    return max(fide, nrs)

def rating_lbfn(fide, nrs):
    return min(fide, nrs) if fide > 0 and nrs > 0 else max(fide, nrs)

def rating_other(fide, nrs):
    return 0


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")


# =================
#
# Json output
#
#


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
        return "_jpre_" + str(obj) + "_jpost_"
    raise TypeError("Type not serializable")


def json_output(file, obj):
    if isinstance(file, str):
        f = sys.stdout if file == "-" else open(file, "w")
    else:
        f = file
    jsonout = json.dumps(obj, indent=2, default=decimal_serializer)
    f.write(jsonout.replace('"_jpre_', "").replace('_jpost_"', "") + "\n")
    if isinstance(file, str) and file != "-":
        f.close()

def txt_output(file, obj):
    if isinstance(file, str):
        f = sys.stdout if file == "-" else open(file, "w")
    else:
        f = file
    f.write(obj)
    if isinstance(file, str) and file != "-":
        f.close()


