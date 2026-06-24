import runpy

def run_pairing():
    runpy.run_module("pairingchecker", run_name="__main__")

def run_tiebreak():
    runpy.run_module("tiebreakchecker", run_name="__main__")

def run_server():
    runpy.run_module("chessserver", run_name="__main__")

def run_generator():
    runpy.run_module("tournamentgenerator", run_name="__main__")