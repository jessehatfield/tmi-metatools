#!/usr/bin/env python

import csv
import pystan
import matplotlib.pyplot as plt
from sys import argv

def consolidate(data, n):
    transformed = {}
    transformed['n_archetypes'] = n+1
    transformed['n_rounds'] = data['n_rounds']
    transformed['paired_scores'] = data['paired_scores']
    transformed['pairings'] = []
    transformed['decks'] = []
    m = len(data['pairings'])
    for s_i in range(len(data['pairings'])):
        counts = data['pairings'][s_i]
        total = sum([counts[j] for j in range(n, len(counts))])
        new_counts = [counts[j] for j in range(n)]
        new_counts.append(total)
        transformed['pairings'].append(new_counts)
    for r_i in range(len(data['decks'])):
        record_counts = data['decks'][r_i]
        total = sum([record_counts[j] for j in range(n, len(record_counts))])
        new_record_counts = [record_counts[j] for j in range(n)]
        new_record_counts.append(total)
        transformed['decks'].append(new_record_counts)
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

def load_data(data_file, selection):
    archetype_pairings = {}
    archetype_totals = {}
    score_pairings = {}
    archetype_records = {}
    n_rounds = 0
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            w = int(row['w'])
            l = int(row['l'])
            opp_w = int(row['opp_w']) if len(row.get('opp_w', '')) > 0 else None
            opp_l = int(row['opp_l']) if len(row.get('opp_l', '')) > 0 else None
            opponent = row['deck']
            score = w-l
            n_rounds = max(n_rounds, abs(score))
            archetype_totals[opponent] = archetype_totals.get(opponent, 0) + 1
            if opponent not in archetype_pairings:
                archetype_pairings[opponent] = {}
            if opponent not in archetype_records:
                archetype_records[opponent] = {}
            if opp_w is not None and opp_l is not None:
                opp_record = (opp_w, opp_l)
                opp_score = opp_w - opp_l
                if opp_score not in score_pairings:
                    score_pairings[opp_score] = {}
                archetype_records[opponent][opp_record] = archetype_records[opponent].get(opp_record, 0) + 1
                score_pairings[opp_score][score] = score_pairings[opp_score].get(score, 0) + 1
            else:
                archetype_pairings[opponent][score] = archetype_pairings[opponent].get(score, 0) + 1
    archetypes = list(archetype_totals.keys())
    archetypes.sort(key=lambda x: -archetype_totals[x])
    if selection.isdigit():
        n = int(selection)
    else:
        archetypes = [selection] + [a for a in archetypes if a != selection]
        n = 1
    pairing_counts = []
    score_counts = []
    record_counts = []
    for i in range((2*n_rounds)+1):
        oppdeck_distribution = []
        oppscore_distribution = []
        for deck in archetypes:
            score = i - n_rounds
            oppdeck_distribution.append(archetype_pairings[deck].get(score, 0))
        for j in range((2*n_rounds)+1):
            score = i - n_rounds
            oppscore = j - n_rounds
            oppscore_distribution.append(score_pairings.get(oppscore, {}).get(score, 0))
        pairing_counts.append(oppdeck_distribution)
        score_counts.append(oppscore_distribution)
    for n_matches in range(n_rounds+1):
        for l in range(n_matches+1):
            w = n_matches - l
            deck_distribution = []
            for deck in archetypes:
                deck_distribution.append(archetype_records[deck].get((w, l), 0))
            record_counts.append(deck_distribution)
    data = {
        'n_archetypes': len(archetypes),
        'n_rounds': n_rounds,
        'pairings': pairing_counts,
        'paired_scores': score_counts,
        'decks': record_counts
    }
    archetype_list = archetypes[:n] + ["Misc."]
    consolidated_data = consolidate(data, n)
    print(consolidated_data)
    return (consolidated_data, archetype_list)

def save_names(archetype_list, filename):
    with open(filename, 'w') as outfile:
        for archetype in archetype_list:
            outfile.write(archetype)
            outfile.write("\n")

if __name__ == "__main__":
    pairings_file = argv[1]
    selected_decks = argv[2]
    n_chains = int(argv[3])
    n_warmup = int(argv[4])
    n_iterations = int(argv[5])
    archetype_output = argv[6]
    sample_output = argv[7] if len(argv) > 7 else None
    print("Loading {} and consolidating non-selected decks...".format(pairings_file))
    (data, archetypes) = load_data(pairings_file, selected_decks)
    print("Writing archetype names to {}...".format(archetype_output))
    print("\t({})".format(archetypes))
    save_names(archetypes, archetype_output)
    print("Running Bayesian inference...")
    print("\t({} chain(s))".format(n_chains))
    print("\t({} warmup iterations)".format(n_warmup))
    print("\t({} sampling iterations)".format(n_iterations))
    if sample_output:
        print("\t(recording samples at {})".format(sample_output))
    fit = run_inference(data, n_iterations+n_warmup, n_warmup, n_chains,
            sample_file=sample_output)
    fit.plot(pars=['pdeck', 'matchups', 'pwin_deck', 'wait_time'])
#    fit.plot(pars=['pdeck', 'matchups', 'pwin_deck'])
    plt.show()
