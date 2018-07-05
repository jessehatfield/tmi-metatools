#!/usr/bin/env python
"""Estimate a posterior distribution of matchup percentage based on historical
data, which should be suitable for generating a prior distribution for future
matchups."""

import csv

import pystan
import matplotlib.pyplot as plt
import sys

from metatools.database import *#getDecks, getMatches, getTournaments
from metatools.dbmeta import DBMeta
from metatools.util import record

def generate():
    metagame = DBMeta(getTournaments(format='Legacy', source='SCG'))
    skip = set({'Unknown', '(Not Submitted)', ''})
    def clean(string):
        return string.replace('"', '').replace(',', '').strip().lower()
    archetypes = [deck for deck in metagame.archetypes if deck not in skip]
    for i in range(len(archetypes)):
        a1 = archetypes[i]
        if metagame.archetypes[a1] == 0:
            continue
        decks1 = getDecks(tournaments=metagame.tournaments, archetypes=[a1])
        for j in range(i+1, len(archetypes)):
            a2 = archetypes[j]
            if metagame.archetypes[a2] == 0:
                continue
            decks2 = getDecks(tournaments=metagame.tournaments, archetypes=[a2])
            matches = getMatches(tournaments=metagame.tournaments,
                    decks1=decks1, decks2=decks2)
            if len(matches) == 0:
                continue
            # Matches are doubled up for some reason, but given in the same
            # order, so just divide counts by 2
            w_both, l_both, d_both = record(matches)
            w = int(w_both / 2)
            l = int(l_both / 2)
            n = w + l
            if n > 0:
                print("{0},{1},{2},{3}".format(clean(a1), clean(a2), n, w))

def analyze(data_file):
    n_model = 0
    max_matchups = 0
    data = {
            'w': [],
            'n': []
    }
    matchups = []
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if max_matchups > 0 and len(matchups) >= max_matchups:
                break
            w = int(row['w'])
            n = int(row['n'])
            data['w'].append(w)
            data['n'].append(n)
            matchups.append(row['deck1'] + "," + row['deck2'])
    data['n_matchups'] = len(matchups)
    data['n_modeled'] = min(n_model, len(matchups))
    sm = pystan.StanModel(file="models/matchup.stan")
    fit = sm.sampling(data=data, iter=5000, chains=8, n_jobs=-1)
    print(fit)
    print(matchups[:n_model])
    fit.plot()
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
    else:
        generate()
