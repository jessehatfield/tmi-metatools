#!/usr/bin/env python

import csv
import pystan
import matplotlib.pyplot as plt
from sys import argv

def consolidate(data, n):
    transformed = {}
    transformed['n_archetypes'] = n+1
    transformed['n_rounds'] = data['n_rounds']
    transformed['pairings'] = []
    m = len(data['pairings'])
    for s_i in range(len(data['pairings'])):
        counts = data['pairings'][s_i]
        total = sum([counts[j] for j in range(n, len(counts))])
        new_counts = [counts[j] for j in range(n)]
        new_counts.append(total)
        transformed['pairings'].append(new_counts)
    return transformed

def run_inference(data, iterations, warmup, chains, init='random',
        sample_file=None):
    sm = pystan.StanModel(file="models/league.stan")
    fit = sm.sampling(data=data,
            iter=iterations, warmup=warmup, chains=chains,
            n_jobs=-1,
            sample_file=sample_file, init=init)
    print(fit)
    return fit

def load_data(data_file, n):
    archetype_pairings = {}
    archetype_totals = {}
    n_rounds = 0
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            w = int(row['w'])
            l = int(row['l'])
            opponent = row['deck']
            score = w-l
            n_rounds = max(n_rounds, abs(score))
            archetype_totals[opponent] = archetype_totals.get(opponent, 0) + 1
            if opponent not in archetype_pairings:
                archetype_pairings[opponent] = {}
            archetype_pairings[opponent][score] = archetype_pairings[opponent].get(score, 0) + 1
    archetypes = list(archetype_totals.keys())
    archetypes.sort(key=lambda x: -archetype_totals[x])
    pairing_counts = []
    for i in range((2*n_rounds)+1):
        distribution = []
        for deck in archetypes:
            score = i - n_rounds
            distribution.append(archetype_pairings[deck].get(score, 0))
        pairing_counts.append(distribution)
    data = {
        'n_archetypes': len(archetypes),
        'n_rounds': n_rounds,
        'pairings': pairing_counts
    }
    archetype_list = archetypes[:n] + ["other"]
    consolidated_data = consolidate(data, n)
    return (consolidated_data, archetype_list)

def save_names(archetype_list, filename):
    with open(filename, 'w') as outfile:
        for archetype in archetype_list:
            outfile.write(archetype)
            outfile.write("\n")

if __name__ == "__main__":
    pairings_file = argv[1]
    n_decks = int(argv[2])
    n_chains = int(argv[3])
    n_warmup = int(argv[4])
    n_iterations = int(argv[5])
    archetype_output = argv[6]
    sample_output = argv[7] if len(argv) > 7 else None
    print("Loading {} and consolidating top {} decks...".format(pairings_file,
        n_decks))
    (data, archetypes) = load_data(pairings_file, n_decks)
    print("Writing archetype names to {}...".format(archetype_output))
    print("\t({})".format(archetypes))
    save_names(archetypes, archetype_output)
    print("Running Bayesian inference...")
    print("\t({} chain(s))".format(n_chains))
    print("\t({} warmup iterations)".format(n_warmup))
    print("\t({} sampling iterations)".format(n_iterations))
    if sample_output:
        print("\t(recording samples at {})".format(sample_output))
    fit = run_inference(data, n_iterations, n_warmup, n_chains,
            sample_file=sample_output)
    fit.plot(pars=['pdeck', 'matchups', 'pwin_deck', 'wait_time'])
    plt.show()
