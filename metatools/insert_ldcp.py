#!/usr/bin/env python
"""Inserts data exported from spreadsheets in the form produced by the Legacy Data Collection Project."""

from metatools.archetypes import ArchetypeParser
from metatools.database import session, getDecks, RawMatch
from metatools.insert import *

import argparse
import csv
import datetime
import json
import os
import re
import sys


roundExpr = re.compile(r'Round (\d+)')
byeExpr = re.compile(".*BYE.*", re.IGNORECASE)
drawExpr = re.compile("^Draw$", re.IGNORECASE)
gameExpr = re.compile("^([0-9]+)-([0-9]+)(-([0-9]+))?$")
filenameExpr = re.compile(r'^([^ ]*) (.*Challenge|Super Qualifier|Rc Super Qualifier|Last Chance|Showcase Qualifier)( \d+)? (\d{1,2})_(\d{1,2})_(\d{4})( - [\d]+)?')


def matchesIgnoreCase(key, options):
    for candidate in options:
        if key.lower() == candidate.lower():
            return True
    return False


def parseChallengeDecks(filename, in_order=True):
    with open(filename) as playerFile:
        reader = csv.reader(playerFile, delimiter='\t')
        header = reader.__next__()
        playerIndex = None
        archetypeIndex = None
        for i in range(len(header)):
            columnName = header[i]
            if matchesIgnoreCase(columnName, PLAYER_FIELD_NAMES):
                playerIndex = i
            elif matchesIgnoreCase(columnName, ARCHETYPE_FIELD_NAMES):
                archetypeIndex = i
        n = 1
        for row in reader:
            playerName = row[playerIndex]
            deckName = row[archetypeIndex]
            place = n if in_order else None
            yield (playerName, deckName, place)
            n += 1


def parseChallengeMatches(filename):
    with open(filename) as matchFile:
        reader = csv.reader(matchFile, delimiter='\t')
        header = reader.__next__()
        playerIndex = None
        roundIndices = {}
        for i in range(len(header)):
            columnName = header[i]
            if matchesIgnoreCase(columnName, PLAYER_FIELD_NAMES):
                playerIndex = i
            else:
                roundMatch = roundExpr.match(columnName)
                if roundMatch:
                    roundIndices[int(roundMatch.group(1))] = i
        if playerIndex is None:
            raise Exception(f"Couldn't determine column for player name. " +
                    f"Expected one of {PLAYER_FIELD_NAMES}; found {header}.")
        nRounds = len(roundIndices)
        for row in reader:
            p1 = row[playerIndex]
            for r in range(1, nRounds+1):
                roundIndex = roundIndices[r]
                p2 = row[roundIndex].strip()
                game_match = gameExpr.match(row[roundIndex+1])
                if game_match:
                    w, l = (int(game_match.group(1)), int(game_match.group(2)))
                    d = int(game_match.group(4)) if game_match.group(4) else 0
                    yield (p1, p2, w, l, d, r)


def insertLDCPTournament(session, filename, nameArg=None, formatArg=None, dateArg=None,
        archetypesFile=None, decklistsFile=None, ignore_given_archetypes=False):
    baseName = os.path.basename(filename)
    filenameMatch = filenameExpr.match(baseName)
    if filenameMatch is None:
        if nameArg is None or formatArg is None or dateArg is None:
            raise Exception(f"Couldn't parse filename {baseName}; expected format and date from "
                    "filename or command line arguments")
    mtg_format = formatArg if formatArg else filenameMatch.group(1)
    tournament_type = filenameMatch.group(2) if filenameMatch else None
    tournament_size = filenameMatch.group(3) if filenameMatch and filenameMatch.group(3) else ""
    tournament_number = filenameMatch.group(7) if filenameMatch and filenameMatch.group(7) else ""
    eventdate = dateArg if dateArg else datetime.date(
            int(filenameMatch.group(6)), int(filenameMatch.group(4)), int(filenameMatch.group(5)))
    date_str = eventdate.strftime('%Y-%m-%d')
    t_name = nameArg if nameArg else f'{mtg_format} {tournament_type}{tournament_size} {date_str}{tournament_number}'
    tourney = DBTournament(name=t_name, date=eventdate, format=mtg_format)
    tourney.source = "MTGO Data Collection Project"
    session.add(tourney)
    archetype_parser = ArchetypeParser(archetypesFile) if archetypesFile else None
    decklists = []
    if decklistsFile is not None:
        with open(decklistsFile) as f:
            decklists = json.load(f)
    name_to_index = {}
    place_to_index = {}
    name_to_indices = {}
    for i in range(len(decklists)):
        place_to_index[decklists[i]['place']] = i
        player_name = decklists[i]['player']
        if player_name in name_to_index:
            if player_name not in name_to_indices:
                name_to_indices[player_name] = {name_to_index[player_name]}
            name_to_indices[player_name].add(i)
        else:
            name_to_index[player_name] = i
    nDecks = 0
    for playerName, deckName, place in parseChallengeDecks(filename):
        deck = DBDeck(
                place=place,
                player=playerName,
                tournament=tourney,
                archetype=deckName,
                points=0)
        deck.original = deckName
        if decklists:
            i1 = place_to_index.get(place)
            i2 = name_to_index.get(playerName)
            i2s = name_to_indices.get(playerName, {i2})
            if i1 not in i2s:
                raise Exception(f'Error reading decklists: player name {playerName} associated '
                    f'with deck(s) {i2s} but place {place} associated with deck {i1}')
            elif i1 is None:
                print(f"WARNING: couldn't find decklist for player {playerName} in place {place}", file=sys.stderr)
            decklist_string = decklists[i1].get('decklist')
            if decklist_string is None or decklist_string.strip() == "":
                print(f"WARNING: no decklist for player {playerName} in place {place} -- "
                        + f"originally labeled '{deck.original}', now '{ArchetypeParser.unknown}'", file=sys.stderr)
                deck.archetype = ArchetypeParser.unknown
                deck.subarchetype = ''
            else:
                decklist_lines = [x.strip() for x in decklist_string.splitlines() if x.strip() != '']
                deck.readLines(decklist_lines)
                deck.saveContents()
                if archetype_parser is not None:
                    fallback = ArchetypeParser.unknown if ignore_given_archetypes else deck.archetype
                    try:
                        new_name, new_sub = archetype_parser.classify(deck, fallback=fallback)
                        deck.archetype = new_name
                        deck.subarchetype = new_sub
                    except Exception as e:
                        print(f"WARNING: {e} (using {fallback})")
                        deck.archetype = fallback
        session.add(deck)
        nDecks += 1
    tourney.numPlayers = nDecks
    session.flush()
    nMatches = 0
    for p1, p2, w, l, d, r in parseChallengeMatches(filename):
        d1 = getDecks(tournaments=[tourney], players=[p1])
        d2 = getDecks(tournaments=[tourney], players=[p2])
        if len(d1) == 0:
            raise Exception(f"Unexpected player name '{p1}' in match history")
        if len(d2) == 0:
            raise Exception(f"Unexpected player name '{p2}' in match history (round {r} opponent for {p1})")
        match = RawMatch(d1[0], d2[0], w, l, d, r)
        session.add(match)
        if w > l:
            d1[0].points += 3
        nMatches += 1
    session.flush()
    print(f"Inserted {tourney.name} with {len(tourney.decks)} decks and {nMatches} matches.")


if __name__ == "__main__":

    p = argparse.ArgumentParser(description="Insert tournament(s) exported from spreadsheets in the form "
            "produced by the Legacy Data Collection Project.")
    p.add_argument("-a", "--archetypes", help="Path to a directory containing archetype "
            + "definitions, which will override the deck names in the input files if --decklists is given.")
    p.add_argument("-i", "--ignore_given_archetypes", action="store_true", help="If using the archetype parser, "
            + "completely ignore the archetype field in the input file. If not specified, the "
            + "input field will be used as a fallback if the parser fails to label the deck. "
            + "Has no effect without both --archetypes / -a and --decklists / -l .")
    p.add_argument("-D", "--dry_run", action="store_true",
            help="Perform a dry run: parse the data, but don't commit anything to the database")
    p.add_argument("-n", "--name", help="Tournament name (if not given, assume it can be extracted from filename)")
    p.add_argument("-f", "--format", help="Tournament format (if not given, assume it can be extracted from filename)")
    p.add_argument("-d", "--date", help="Tournament date (if not given, assume it can be extracted from filename)",
            type=datetime.date.fromisoformat)
    p.add_argument("-l", "--decklists", help="Path to a JSON file containing decklist strings for each player format")
    p.add_argument("files", type=str, nargs="+",
            help="TSV files containing matchup data, one per tournament.")
    args = p.parse_args()

    for filename in args.files:
        insertLDCPTournament(session, filename, args.name, args.format, args.date,
                archetypesFile=args.archetypes,
                decklistsFile=args.decklists,
                ignore_given_archetypes=args.ignore_given_archetypes)
    if args.dry_run:
        print('(Not committing; dry run.)')
    else:
        session.commit()
