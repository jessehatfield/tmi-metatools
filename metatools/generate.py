#!/usr/bin/env python

import sys
import argparse
import subprocess

from metatools.tmi import *
from metatools.config import config

density=200

def matchup(fn, table, args):
    # Print text and LaTeX versions of the table.
    with open('{0}.txt'.format(fn), 'w') as f:
        table.printTable(stream=f)
    with open('{0}.tex'.format(fn), 'w') as f:
        table.printLatex(stream=f, booktabs=True, size="LARGE", width="9.25in")
    # Convert the LaTeX table into a PNG.
    subprocess.run(['latexmk', '-dvi', "{0}.tex".format(fn)])
    subprocess.run(['convert', '-trim', '-density', str(density),
        "{0}.dvi".format(fn), '-quality', '100', "{0}.png".format(fn)])
    #convert {0}.png -resize 475 -quality 100 {0}.png
    subprocess.run(['latexmk', '-C'])
    # Copy image to the final destination.
    if args.copy:
        subprocess.run(['cp', "{0}.png".format(fn),
            "{0}/images/{1}.png".format(args.copy, fn)])

def breakdown(fn, table, args):
    # Print text and LaTeX versions of the table.
    with open('{0}.txt'.format(fn), 'w') as f:
        table.printTable(stream=f)
    with open('{0}.tex'.format(fn), 'w') as f:
        table.printLatex(stream=f, booktabs=True, size="large", width="9.5in")
    # Convert the LaTeX table into a PNG.
    subprocess.run(['latexmk', '-dvi', "{0}.tex".format(fn)])
    subprocess.run(['convert', '-trim', '-density', str(density),
        "{0}.dvi".format(fn), '-quality', '100', '+repage', "{0}.png".format(fn)])
    #convert {0}.png -resize 625 -quality 100 {0}.png ;
    subprocess.run(['latexmk', '-C'])
    # Copy image to the final destination.
    if args.copy:
        subprocess.run(['cp', "{0}.png".format(fn),
            "{0}/images/{1}.png".format(args.copy, fn)])

def main():
    p = argparse.ArgumentParser(description="""Generate breakdowns and/or
            matchup tables for recent SCG Opens.""")
    p.add_argument('-c', '--copy', type=str, help='Copy the\
            resulting files to this directory.')
    p.add_argument('-d', '--date', type=str, default=config['defaults']['begin-date'],
            help='Use matchup data from this date forward.')
    p.add_argument('-f', '--field', type=float, default=.05, help='\
            Generate matchups for decks that were at least this popular.')
    p.add_argument('-i', '--include', nargs='+', type=str, default=[], help='\
            Generate matchups for these decks as well as the most popular decks.')
    p.add_argument('-I', '--include_extra', nargs='+', type=str, default=[], \
            help="""Generate matchups for these decks as well as the most
            popular decks, but don't include them in the other decks'
            matchup tables.""")
    p.add_argument('-o', '--overall', nargs=2, type=str, help='\
            Date range for Overall Matchup column.')
    p.add_argument('-O', '--overall_title', type=str, help='\
            Alternate title for Overall column.')
    p.add_argument('--no_breakdown', action='store_true', help='\
            Don\'t produce breakdowns.')
    p.add_argument('--no_matchups', action='store_true', help='\
            Don\'t produce matchup results.')
    p.add_argument('--no_overall', action='store_true', help='\
            Don\'t include Overall Matchups.')
    p.add_argument('-ne', '--no_ev', action='store_true', help="""Don't include
            an "EV" column.""")
    p.add_argument('-np', '--no_place', nargs='+', type=int, help="""Don't include
            an "Average Place" column for the specified (by number, starting from
            the earliest) tournaments.""")
    p.add_argument('-t', '--tournies', type=int, default=1, help='Focus on\
            the latest N tournaments.')
    p.add_argument('-u', '--unknown', action='store_true', help='Some information\
            from these tournaments is unknown; changes the kinds of stats we\
            might be interested in.')

    p.add_argument('decks', nargs='*', type=str)

    args = p.parse_args()

    if args.copy:
        subprocess.run(['mkdir', '-p' "{0}/images".format(args.copy)])

    # Get the popular decks from that period of time
    meta = buildMeta(begin=args.date, format='Legacy',# source='SCG',
            tournies=args.tournies, field=args.field)
    decks = meta[1]

    # Add explicitly included decks
    for other in args.include:
        if other not in decks:
            decks.append(other)
    print(decks)

    # Add the extra decks to a larger list of tables to generate.
    alldecks = decks[:]
    for deck in args.include_extra:
        if deck not in alldecks:
            alldecks.append(deck)

    included_decks = ''
    for deck in decks:
        included_decks += ' "' + deck + '"'

    #Generate the matchup tables.
    if not args.no_matchups:
        matchargs = {
            'tournies': args.tournies,
            'begin': args.date,
            'include': decks,
            'exclude_unselected': True }
        if args.overall:
            matchargs['overall'] = args.overall
        if args.overall_title:
            matchargs['overall_title'] = args.overall_title
        if args.no_overall:
            matchargs['no_overall'] = True
        for deck in alldecks:
            print(deck)
            fn = deck.replace(' ', '').replace('/', '').replace('&', '_and_')
            matchargs['deck'] = [deck]
            matchargs['label'] = deck
            table = tmi('matchups', **matchargs)
            matchup(fn, table, args)

    # Generate breakdowns.
    if not args.no_breakdown:
        # Generic breakdown arguments
        bargs = { 'field': 0.0, 'sub': True, 'begin': args.date,
                'tournies': args.tournies }
        # Breakdowns for all the tournaments
        for i in range(args.tournies, 0, -1):
            n = args.tournies - i + 1
            fn = 'breakdown{0}'.format(n)
            if args.unknown:
                bargs['outputs'] = ['n', 'field', 'matches', 'mwp', 'matchesk', 'mwpk']
            else:
                buildOutputs = ['n', 'field']
                if not args.no_place or n not in args.no_place:
                    buildOutputs = buildOutputs + ['avgplace']
                buildOutputs = buildOutputs + ['win', 'loss', 'draw', 'mwp']
                if not args.no_ev:
                    buildOutputs = buildOutputs + ['ev']
                bargs['outputs'] = buildOutputs
            table = tmi('breakdown', tournaments=[i], **bargs)
            breakdown(fn, table, args)

        # If there were more than one, generate a combined breakdown.
        if args.tournies > 1:
            if args.unknown:
                bargs['outputs'] = ['n', 'field', 'known', 'matches', 'mwp', 'matchesk', 'mwpk']
            elif args.no_ev:
                bargs['outputs'] = ['n', 'field', 'win', 'loss', 'draw', 'mwp']
            else:
                bargs['outputs'] = ['n', 'field', 'win', 'loss', 'draw', 'mwp', 'ev']
            table = tmi('breakdown', tournaments=range(args.tournies, 0, -1),
                    **bargs)
            breakdown("breakdownAll", table, args)

if __name__ == '__main__':
    main()
