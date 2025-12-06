# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 21:37:29 2025

@author: otto
"""
import random

class drawresult:
    
    # constructor function
    def __init__(self, seed):
        random.seed(seed if seed else 4711) 
        self.sigma = 0
        self.zpb = 0.0
        self.hpb = 0.0
        self.forfeited = 0.0
        self.team = 1

    def prob(self, rw, rb): 
        # rw = Rating white player 
        # rb = Rating black player 
        # parameters 
        wa = 0.0986  
        wb = 96. 
        ba = -0.157  
        bb = -150. 
        s = 370 
        # rmean  
        rm = (rw+rb)/2.0 
        # Probability of white win 
        w = (rm-2000)*wa + wb 
        expw = (rb-rw+w)/s 
        pw = 1.0 / (1.0 + pow(10.0, expw)) 
        # Probability of black win 
        b = (rm-2000)*ba + bb 
        expb = (rw-rb-b)/s 
        pb = 1.0 / (1.0 + pow(10.0, expb)) 
        # Probability of draw 
        pd = 1.0 - pw -pb 
        return [pw, pd, pb] 

    def teamprob(self, rw, rb):
        dist = [1]
        swap = False
        for games in range(self.team):
            ndist = [0]*(len(dist)+2)
            res = self.prob(rb, rw) if swap else self.prob(rw, rb)
            if swap: res.reverse() 
            for a in range(len(res)):
                for b in range(len(dist)):
                    ndist[a+b] += res[a]*dist[b]
            dist = ndist
            swap = not swap
        dlen = len(ndist)
        return [sum(ndist[:dlen//2]), ndist[dlen//2], sum(ndist[dlen//2+1:]) ]
    
    
    def result(self, rw, rb):
        res = self.prob(rw,rb) if self.team <= 1 else self.teamprob(rw,rb)
        rand = random.random() * (1.0 + self.forfeited)
        if rand < res[0]:
            return "W"
        if rand < res[0] + res[1]:
            return "D"
        if rand < res[0] + res[1] + res[2]:
            return "B"
        if rand < 1.0 + self.forfeited/2.0:
            return "+"
        return "-"

    def has_bye(self):
        rand = random.random() 
        if rand < self.zpb:
            return "Z"
        if rand < self.zpb + self.hpb:
            return "H"
        return ""

    def set_params(self, zpb = 0.0, hpb=0.0, forfeited=0.0):
        self.zpb = zpb
        self.hpb = hpb
        self.forfeited = forfeited

    def set_sigma(self, sigma= 0.0):
        self.sigma = sigma
        
    def set_hpb(self, hpb=0.0):
        self.hpb = hpb

    def set_team(self, team=1):
        self.team = team

        
    def add_sigma(self, rating):
        return rating + int(round(random.gauss(0.0, self.sigma)))

    def get_random(self):
        return random.random()
   
# run program
if __name__ == '__main__':
    import sys
    import version   
    import argparse
    import helpers
    
    def read_command_line(version, strict):
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--check", required=False, action="count", default=0, help="check")
        parser.add_argument("-w", "--white", required=False, default="2000", help="White rating")
        parser.add_argument("-b", "--black", required=False, default="1800", help="Black rating")
        parser.add_argument("-v", "--verbose", required=False, action="count", default=0, help="verbose")
        parser.add_argument("-V", "--version", required=False, action="count", default=0, help="Version")
        if strict:
            params = vars(parser.parse_args())
        else:
            params = vars(parser.parse_known_args())
        # print(params)

        if params.get("version", 0) > 0 or params.get("verbose", 0) > 0:
            print(version)
            if params["version"] > 0:
                sys.exit(0)
        return params


    def do_test(w, b, c):    
        dr = drawresult(None)
        rs = ""
        for i in range(40):
            rs += dr.result(w, b)
        if not c: 
            print("Test individual:", w, b)
            print(rs)
        
        print(dr.prob(w,b))
        if not c:
            print(dr.prob(b,w))
            print(dr.prob(w,w))
            print(dr.prob(b,b))
            dr.set_team(2)
            print("Test team 2 players:", w, b)
            print(dr.teamprob(w,b))
            print(dr.teamprob(w,w))
            dr.set_team(4)
            print("Test team 4 players:", w, b)
            print(dr.teamprob(w,b))
            print(dr.teamprob(w,w))

    params = read_command_line("drawresult ver. " + version.version()["version"], True)
    w = helpers.parse_int(params["white"])
    b = helpers.parse_int(params["black"])
    c = params["check"]
    do_test(w, b, c)
        
        