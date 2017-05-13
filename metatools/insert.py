#!/usr/bin/env python

from database import *
import argparse
import datetime
import csv
import re

PLAYER_FIELD_NAMES = {"Player", "Player Name", "Name"}
ARCHETYPE_FIELD_NAMES = {"Deck", "Deck Name", "Archetype", "Archetype Name"}
SUBARCHETYPE_FIELD_NAMES = {"Subtype", "Subtype Name", "Subarchetype",
        "Subarchetype Name", "Sub-Archetype", "Sub-Archetype Name"}
POINTS_FIELD_NAMES = {"Points", "Match Points"}
PLACE_FIELD_NAMES = {"Place", "Final Place"}

ROUND_FIELD_NAMES = {"Round"}
P1_FIELD_NAMES = {"Player", "Player 1"}
P2_FIELD_NAMES = {"Opponent", "Player 2"}
TABLE_FIELD_NAMES = {"Table", "Table"}
RESULT_FIELD_NAMES = {"Result"}
WIN_FIELD_NAMES = {"Won"}
LOSS_FIELD_NAMES = {"Lost"}
DRAW_FIELD_NAMES = {"Drew"}

def r(name):
    return name.replace('  ', ', ')

def insertTournament(deckPath, matchPath, tname, tformat, year, month, day, city,
        state, country, source, givenCounts, dryRun):
    eventdate = datetime.date(year, month, day)
    tourney = DBTournament(name=tname, date=eventdate.strftime('%Y-%m-%d'),
            city=city, state=state, country=country, format=tformat)
    tourney.source = source
    session.add(tourney)

    def getKey(options, findIn):
        for key in options:
            for exists in findIn:
                if key.lower() == exists.lower():
                    return exists
        return None
    def requiredKey(fieldnames, options, filename, desc):
        field = getKey(options, fieldnames)
        if field:
            return lambda x: x[field]
        else:
            msg = "{}: no field for {}.\n\tExpected one of {}\n\tFound {} " +\
                "(case-insensitive)"
            raise Exception(msg.format(filename, desc, options, fieldnames))
    def optionalKey(fieldnames, options, filename, desc, default):
        field = getKey(options, fieldnames)
        if field:
            return lambda x: x[field]
        else:
            msg = "{}: no field for {}. To specify, include a column with " +\
                "one of\n\t{} (case-insensitive)"
            print(msg.format(filename, desc, options))
            return lambda x: default

    with open(deckPath) as deckFile:
        reader = csv.DictReader(deckFile)
        getPlayer = requiredKey(reader.fieldnames, PLAYER_FIELD_NAMES,
                deckPath, "player name")
        getArchetype = requiredKey(reader.fieldnames, ARCHETYPE_FIELD_NAMES,
                deckPath, "deck/archetype name")
        getSubarchetype = optionalKey(reader.fieldnames, SUBARCHETYPE_FIELD_NAMES,
                deckPath, "subarchetype name", "")
        getPoints = optionalKey(reader.fieldnames, POINTS_FIELD_NAMES,
                deckPath, "total match points", None)
        getPlace = optionalKey(reader.fieldnames, PLACE_FIELD_NAMES,
                deckPath, "final place", None)

        for row in reader:
            deck = DBDeck(
                    place=getPlace(row),
                    player=getPlayer(row),
                    tournament=tourney,
                    points=getPoints(row),
                    archetype=getArchetype(row),
                    subarchetype=getSubarchetype(row))
        deck.original = deck.archetype
        session.add(deck)

    session.flush()

    with open(matchPath) as matchFile:
        reader = csv.DictReader(matchFile)
        getRound = requiredKey(reader.fieldnames, ROUND_FIELD_NAMES,
                matchPath, "round number")
        getP1 = requiredKey(reader.fieldnames, P1_FIELD_NAMES,
                matchPath, "first player name")
        getP2 = requiredKey(reader.fieldnames, P2_FIELD_NAMES,
                matchPath, "first player name")
        getTable = requiredKey(reader.fieldnames, TABLE_FIELD_NAMES,
                matchPath, "table number")
        if givenCounts:
            getGameWin = requiredKey(reader.fieldnames, WIN_FIELD_NAMES,
                    matchPath, "game win count")
            getGameLoss = requiredKey(reader.fieldnames, LOSS_FIELD_NAMES,
                    matchPath, "game loss count")
            getGameDraw = requiredKey(reader.fieldnames, DRAW_FIELD_NAMES,
                    matchPath, "game draw count")
            def getGameCounts(row): 
                return (getGameWin(row), getGameLoss(row), getGameDraw(row))
        else:
            getResult = requiredKey(reader.fieldnames, RESULT_FIELD_NAMES,
                    matchPath, "match result (e.g. 'Won 2-0')")
            byeExpr = re.compile(".*BYE.*", re.IGNORECASE)
            gameExpr = re.compile("^(Won|Lost|Draw) ([0-9-]*)$", re.IGNORECASE)
            def getGameCounts(row): 
                resultString = getResult(row)
                if byeExpr.match(resultString):
                    return (0, 0, 0)
                else:
                    match = gameExpr.match(resultString)
                    if match:
                        counts = match.group(2).split("-")
                        w = int(counts[0]) if len(counts) > 0 else 0
                        l = int(counts[1]) if len(counts) > 1 else 0
                        d = int(counts[2]) if len(counts) > 2 else 0
                        return (w, l, d)
                    else:
                        msg = "{}: Couldn't parse match result '{}'"
                        raise Exception(msg.format(matchFile, resultString))
        for row in reader:
            r = getRound(row)
            p1 = getP1(row)
            p2 = getP2(row)
            d1 = getDecks(tournaments=[tourney], players=[p1])
            d2 = getDecks(tournaments=[tourney], players=[p2])
            (w, l, d) = getGameCounts(row)
            skip = w + l + d == 0
            if len(d1) == 0:
                skip = True
                msg = "Round {}: Encountered unknown player: {}, skipping".format(r, p1)
                print(msg)
            if len(d2) == 0:
                skip = True
                msg = "Round {}: Encountered unknown player: {}, skipping".format(r, p2)
                print(msg)
            if not skip:
                match = RawMatch(d1[0], d2[0], w, l, d, getRound(row))
                match.table = getTable(row)
                session.add(match)

    tourney.numPlayers = tourney.getNumPlayers()
    print(tourney)
    if not dryRun:
        session.commit()
