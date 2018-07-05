#!/usr/bin/env python

import pystan
import matplotlib.pyplot as plt
from random import Random
from sys import argv

rand = Random()

class League(object):
    def __init__(self, field_distribution, matchups, score_distribution):
        self.matchups = matchups
        self.max_rounds = max(score_distribution.keys())
        self.field = {}
        self.field_distribution = field_distribution
        self.decks = range(len(field_distribution))
        self.n = 0
        self.score_counts = {}
        self.scores = []
        self.score_distribution = score_distribution
        for i in range(2*self.max_rounds + 1):
            score = i - self.max_rounds
            self.scores.append(score)
            self.field[score] = {deck: 0 for deck in self.decks}
            self.score_counts[score] = 0

    def add(self, n):
        new_decks = rand.choices(self.decks, self.field_distribution, k=n)
        for d in new_decks:
            self.field[0][d] = self.field[0][d] + 1
            self.score_counts[0] = self.score_counts[0] + 1
        self.n += n

    def choose_score(self):
        p = [self.score_counts[score]/float(self.n) for score in self.scores]
        return rand.choices(self.scores, p, k=1)[0]

    def choose_paired_score(self, score1):
        p = [self.score_distribution[score1][score2] for score2 in self.scores]
        return rand.choices(self.scores, p, k=1)[0]

    def choose_deck(self, score):
        n = float(self.score_counts[score])
        if n == 0:
            return None
        else:
            p_deck = [self.field[score][deck]/n for deck in self.decks]
            return rand.choices(self.decks, p_deck, k=1)[0]

    def add_score(self, deck, new_score):
        if new_score > self.max_rounds or new_score < -self.max_rounds:
            self.add_score(deck, 0)
        else:
            self.field[new_score][deck] = self.field[new_score][deck] + 1
            self.score_counts[new_score] = self.score_counts[new_score] + 1

    def play_match(self):
        p1_score = self.choose_score()
        p1_deck = self.choose_deck(p1_score)
        if p1_deck is None:
            return
        p2_score = self.choose_paired_score(p1_score)
        p2_deck = self.choose_deck(p2_score)
        if p2_deck is None:
            return
        self.field[p1_score][p1_deck] = self.field[p1_score][p1_deck] - 1
        self.field[p2_score][p2_deck] = self.field[p2_score][p2_deck] - 1
        self.score_counts[p1_score] = self.score_counts[p1_score] - 1
        self.score_counts[p2_score] = self.score_counts[p2_score] - 1
        p_win_p1 = self.matchups[p1_deck][p2_deck]
        if rand.random() < p_win_p1:
            self.add_score(p1_deck, p1_score+1)
            self.add_score(p2_deck, p2_score-1)
        else:
            self.add_score(p1_deck, p1_score-1)
            self.add_score(p2_deck, p2_score+1)

    def ev(self, deck, score):
        p = 0.0
        for score2 in self.scores:
            p_pair_score = self.score_distribution[score][score2]
            n = self.score_counts[score2]
            if n > 0:
                for deck2 in self.decks:
                    p_pair_deck = self.field[score2][deck2] / float(n)
                    p_win = self.matchups[deck][deck2]
                    p += p_pair_score * p_pair_deck * p_win
        return p

def generate():
    n_decks = 1000
    n_samples = 5000
    n_matches = 10
    n_rounds = 4
    field = [0.3, 0.5, 0.2]
    matchups = {
            0: {0: 0.5, 1: 0.3, 2: 0.8},
            1: {0: 0.7, 1: 0.5, 2: 0.3},
            2: {0: 0.2, 1: 0.7, 2: 0.5}
    }
    scores = [i-n_rounds for i in range((n_rounds*2)+1)]
    score_map = {s1: {s2: 0.0 for s2 in scores} for s1 in scores}
    for i in scores:
        score_map[i][i] = 1.0
    l = League(field, matchups, score_map)
    l.add(n_decks)
    actual_field = l.field[0]
    actual_distribution = {d: actual_field[d]/float(n_decks) for d in actual_field}
    ev = {d: l.ev(d, 0) for d in actual_field}
    print("Sample distribution:", actual_distribution)
    print("Sample EV:", ev)
    counts = {s: [0]*len(field) for s in scores}
    for i in range(n_samples):
        for j in range(n_matches):
            l.play_match()
    for i in range(n_samples):
        for j in range(n_matches):
            l.play_match()
        for s in scores:
            i = l.choose_deck(s)
            if i is not None:
                counts[s][i] += 1
    data = {
            'n_decks': len(field),
            'n_rounds': n_rounds,
            'deck': [counts[s] for s in scores]
    }
    for s in scores:
        n_score = float(sum(counts[s]))
        p_score = [x/n_score for x in counts[s]]
        print("score distribution[{}]: {}".format(s, p_score))
    return data

def consolidate(data, n):
    transformed = {}
    transformed['n_decks'] = n+1
    transformed['n_rounds'] = data['n_rounds']
    transformed['deck'] = []
    m = len(data['deck'])
    for s_i in range(len(data['deck'])):
        counts = data['deck'][s_i]
        total = sum([counts[j] for j in range(n, len(counts))])
        new_counts = [counts[j] for j in range(n)]
        new_counts.append(total)
        transformed['deck'].append(new_counts)
    return transformed

def run_inference(data, iterations, warmup, chains):
    sm = pystan.StanModel(file="models/league.stan")
    fit = sm.sampling(data=data, iter=iterations, warmup=warmup,
            chains=chains, n_jobs=-1)
    print(fit)
    #print(fit.extract(pars=varnames))
    return fit

def test():
    test_data = generate()
    print(test_data)
    fit = run_inference(test_data, 2000, 500, 2)
    fit.plot(pars=['pdeck', 'matchups', 'pwin_deck'])
    plt.show()

def main(data_file):
    data = {
        'n_decks': 0,
        'n_rounds': 5,
        'deck': []
    }
    fit = run_inference(data, 5000, 1000, 2)
    fit.plot(pars=['pdeck', 'matchups', 'pwin_deck'])
    plt.show()

if __name__ == "__main__":
    if len(argv) > 1:
        data_file = argv[1]
        main(data_file)
    else:
        test()
