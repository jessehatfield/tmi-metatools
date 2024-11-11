#!/usr/bin/env python
"""Inserts data exported from spreadsheets in the form produced by the Legacy Data Collection Project."""

from metatools.database import session, getDecks, RawMatch
from metatools.insert import *

import argparse
import csv
import datetime
import os
import re
import sys

roundExpr = re.compile(r'Round (\d+)')
byeExpr = re.compile(".*BYE.*", re.IGNORECASE)
drawExpr = re.compile("^Draw$", re.IGNORECASE)
gameExpr = re.compile("^([0-9]+)-([0-9]+)(-([0-9]+))?$")
filenameExpr = re.compile(r'^([^ ]*) (.*Challenge)( \d+)? (\d{1,2})_(\d{1,2})_(\d{4})( - [\d]+)?')


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


def insertLDCPTournament(session, filename, nameArg=None, formatArg=None, dateArg=None):
    baseName = os.path.basename(filename)
    filenameMatch = filenameExpr.match(baseName)
    if filenameMatch is None:
        if nameArg is None or formatArg is None or dateArg is None:
            raise Exception(f"Couldn't parse filename {baseName}; expected format and date from "
                    "filename or command line arguments")
    mtg_format = formatArg if formatArg else filenameMatch.group(1)
    tournament_type = filenameMatch.group(2)
    tournament_size = filenameMatch.group(3) if filenameMatch.group(3) else ""
    tournament_number = filenameMatch.group(7) if filenameMatch.group(7) else ""
    eventdate = dateArg if dateArg else datetime.date(
            int(filenameMatch.group(6)), int(filenameMatch.group(4)), int(filenameMatch.group(5)))
    date_str = eventdate.strftime('%Y-%m-%d')
    t_name = nameArg if nameArg else f'{mtg_format} {tournament_type}{filenameMatch.group(3)} {date_str}{tournament_number}'
    tourney = DBTournament(name=t_name, date=eventdate, format=mtg_format)
    tourney.source = "MTGO Data Collection Project"
    session.add(tourney)
    nDecks = 0
    for playerName, deckName, place in parseChallengeDecks(filename):
        deck = DBDeck(
                place=place,
                player=playerName,
                tournament=tourney,
                archetype=deckName,
                points=0)
        deck.original = deckName
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
    p.add_argument("-D", "--dry_run", action="store_true",
            help="Perform a dry run: parse the data, but don't commit anything to the database")
    p.add_argument("-n", "--name", help="Tournament name (if not given, assume it can be extracted from filename)")
    p.add_argument("-f", "--format", help="Tournament format (if not given, assume it can be extracted from filename)")
    p.add_argument("-d", "--date", help="Tournament date (if not given, assume it can be extracted from filename)",
            type=datetime.date.fromisoformat)
    p.add_argument("files", type=str, nargs="+",
            help="TSV files containing matchup data, one per tournament.")
    args = p.parse_args()

    for filename in args.files:
        insertLDCPTournament(session, filename, args.name, args.format, args.date)
    if args.dry_run:
        print('(Not committing; dry run.)')
    else:
        session.commit()
