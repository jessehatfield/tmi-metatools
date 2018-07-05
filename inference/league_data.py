#!/usr/bin/env python

import csv
import sys
from dateutil.parser import parse

def process(data_file):
    dataset = data_file.split('/')[-1].split('.')[0]
    writer = csv.DictWriter(sys.stdout, ['source', 'date', 'w', 'l', 'deck'])
    with open(data_file) as csvfile:
        reader = csv.DictReader(csvfile)
        wins = 0
        losses = 0
        current_run = ''
        for row in reader:
            run = row.get('run', '')
            if run != current_run:
                wins = 0
                losses = 0
                current_run = run
            transformed = {}
            transformed['source'] = dataset
            d = row.get('date')
            transformed['date'] = parse(d).strftime("%Y-%m-%d") if d else ''
            transformed['w'] = wins
            transformed['l'] = losses
            transformed['deck'] = row['deck'].lower()
            final = row.get('final_record', '')
            if len(final) > 0 or (wins+losses)==4:
                wins = 0
                losses = 0
                current_run = run
            elif row['result'] == '1':
                wins += 1
            elif row['result'] == '-1':
                losses += 1
            else:
                print("ERROR: row['result']=={}".format(row['result']))
            writer.writerow(transformed)

if __name__ == "__main__":
    process(sys.argv[1])
