# -*- coding: utf-8 -*-
"""
Created on Tue Oct 31 13:57:55 2023
@author: Otto Milvang, sjakk@milvang.no
"""
import json
import sys
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal.Decimal):
            return str(o)
        return super().default(o)


# ==============================
#
#  Helpers


#  Dict access


def safe(dict_list, acc_list, default=None):
    for d in dict_list:
        val = d
        for a in acc_list:
            if val is not None:
                val = val.get(a)
        if val is not None:
            return val
    return default


#  Parse


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
    if s == "":
        return 0
    b36 = int(s, 36)
    return b36


def spilt_my_line(line, maxlen, delimiter):
    if len(line) < maxlen:
        return (line, "")
    pos = line[:maxlen].rfind(delimiter)
    return (line[: pos + 1], line[pos + 1:])


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
    # match lastp:
    if lastp == "jch" or lastp == "json":
        return "JSON"
    if lastp == "txt" or lastp == "trf" or  lastp == "trfx":
        return "TRF"
    if lastp == "trx":
        return "TS"
    return "JSON"


def sortxval(x):
    return x["val"]


def sortnum(x):
    return x["num"]


def subtract_lowest(x, y):
    minval = min(x, y)
    return (x - minval, y - minval)


# =================
#
# format
#
#


def format_pair(c, pcmps, bsn, sno):
    a = c["w"]
    b = c["b"]
    sa = ("    " + str(pcmps[a][sno]))[-4:]
    sb = (str(pcmps[b][sno]) + "   ")[0:4]
    ba = ("    " + str(bsn[pcmps[a]["cid"]]))[-4:] if pcmps[a]["cid"] in bsn else "  ?"
    bb = ((str(bsn[pcmps[b]["cid"]]) + "    ")[:4]) if pcmps[b]["cid"] in bsn else "  ?"
    return sa + " - " + sb + " (" + ba + " - " + bb + ")"


def format_down(c, pcmps, bsn):
    sa = ("    " + str(c))[-4:]
    sb = "    "
    ba = ("    " + str(bsn[pcmps[c]["cid"]]))[-4:] if pcmps[c]["cid"] in bsn else "  ?"
    bb = "    "
    return sa + " - " + sb + " (" + ba + " - " + bb + ")"


def format_name(profile):
    if "fideName" in profile and profile["fideName"].find(",") > 0:
        # if "fideName" in profile and len(profile["fideName"]) > 0:
        name = profile["fideName"]
    elif len(profile["lastName"]) > 0 and len(profile["firstName"]) > 0:
        name = profile["lastName"] + ", " + profile["firstName"]
    elif len(profile["lastName"]) > 0:
        name = profile["lastName"]
    elif len(profile["firstName"]) > 0:
        name = profile["firstName"]
    else:
        name = ""  # f"Player {profile['id']:4}"
    return name


def format_datetime(datetime):
    if len(datetime) == 10 and datetime[4] == "-" and datetime[7] == "-":
        return datetime[2:4] + "/" + datetime[5:7] + "/" + datetime[8:10]
    return datetime


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


def json_input(file, json, obj):
    if isinstance(file, str):
        f = sys.stdin if file == "-" else open(file, "r")
    else:
        f = file
    jsonout = json.dumps(obj, indent=2, default=decimal_serializer)
    f.write(jsonout.replace('"_jpre_', "").replace('_jpost_"', "") + "\n")
    if isinstance(file, str) and file != "-":
        f.close()


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
