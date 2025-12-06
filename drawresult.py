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
    dr = drawresult(None)
    rs = ""
    for i in range(40):
        rs += dr.result(2100,1700)
    print(rs)
    
    print(dr.prob(2000,1800))
    print(dr.prob(1800,2000))
    print(dr.prob(2000,2000))
    dr.set_team(2)
    print(dr.teamprob(2000,1800))
    print(dr.teamprob(2000,2000))
    dr.set_team(4)
    print(dr.teamprob(2000,1800))
    print(dr.teamprob(2000,2000))
