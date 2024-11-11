#!/usr/bin/env python

from metatools.archetypes import ArchetypeParser
from metatools.database import *

import argparse
import datetime
import json
import re
import sys

format_exprs = ['Legacy', 'Modern', 'Pauper', 'Pioneer', 'Standard', 'Vintage', 'Brawl', 'Team Draft',
        'Draft [A-Z0-9]{3} Block', 'Sealed [A-Z0-9]{3} Block', '[A-Z0-9]{3} Block']
def extract_format(name):
    for expr in format_exprs:
        match = re.compile('.*(' + expr + ')').match(name)
        if match:
            return match.group(1)
    return None

def load_json(filename):
    json_data = None
    with open(filename, 'r') as f:
        json_data = json.load(f)
    tname = json_data['Tournament']['Name']
    tdate = datetime.date.fromisoformat(json_data['Tournament']['Date'][:10])
    tformat = '?'
    standings = {}
    if json_data.get('Standings', None) is not None:
        for standing in json_data['Standings']:
            standings[standing['Player']] = (standing['Rank'], standing['Points'])
    tournament = DBTournament(name=tname, date=tdate, format=extract_format(tname),
            numPlayers=len(standings))
    decks = {}
    contents = {}
    for d in json_data['Decks']:
        place, points = standings.get(d['Player'], (None, None))
        decks[d['Player']] = DBDeck(place=place, player=d['Player'], tournament=tournament,
                points=points)
        if 'Result':
            if '-' in d['Result']:
                decks[d['Player']].record = d['Result']
            else:
                d['Result']
        decklist = {}
        for main in d['Mainboard']:
            name = main['CardName']
            md, sb = decklist.get(name, (0, 0))
            decklist[name] = (md+main['Count'], sb)
        for main in d['Sideboard']:
            name = main['CardName']
            md, sb = decklist.get(name, (0, 0))
            decklist[name] = (md, sb+main['Count'])
        contents[d['Player']] = decklist
    for player_name in standings:
        if player_name not in decks:
            print(f'Adding empty unknown deck for player {player_name}')
            place, points = standings[player_name]
            decks[player_name] = DBDeck(place=place, player=player_name, tournament=tournament, points=points)
    matches = []
    if json_data.get('Bracket', None) is not None:
        for key in json_data['Bracket'].keys():
            lst = json_data['Bracket'][key]
            if not isinstance(lst, list):
                lst = [lst]
            for match_data in lst:
                parts = match_data['Result'].split('-')
                if len(parts) != 2:
                    print(f"ERROR: couldn't parse match result {match_data['Result']}")
                else:
                    w = int(parts[0].strip())
                    l = int(parts[1].strip())
                    matches.append(RawMatch(decks[match_data['Player1']], decks[match_data['Player2']], w, l, 0, key))
                    matches.append(RawMatch(decks[match_data['Player2']], decks[match_data['Player1']], l, w, 0, key))
    if json_data.get('Rounds', None) is not None:
        n_rounds = 0
        for round_data in json_data['Rounds']:
            n_rounds += 1
            round_name = round_data.get('RoundName', f'Round {n_rounds}')
            for match_data in round_data['Matches']:
                parts = match_data['Result'].split('-')
                if len(parts) != 2 and len(parts) != 3:
                    print(f"ERROR: couldn't parse match result {match_data['Result']}")
                elif match_data['Player2'] not in decks:
                    if match_data['Player2'].strip() != '-' \
                            and match_data['Player2'].lower().strip() != 'bye' \
                            and match_data['Player2'].strip() != '':
                        print(f"ERROR: unrecognized opponent {match_data['Player2']}")
                else:
                    w = int(parts[0].strip())
                    l = int(parts[1].strip())
                    d = 0 if len(parts) < 3 else int(parts[2].strip())
                    matches.append(RawMatch(decks[match_data['Player1']], decks[match_data['Player2']], w, l, d, round_name))
                    matches.append(RawMatch(decks[match_data['Player2']], decks[match_data['Player1']], l, w, d, round_name))
    return tournament, decks, matches, contents

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Insert tournament(s) in JSON format such as from the "
            "MTGODecklistCache project.")
    p.add_argument("-a", "--archetypes",
            help="Archetype parsing rule directory, such as from the MTGOArchetypeParser project")
    p.add_argument("-D", "--dry_run", action="store_true",
            help="Perform a dry run: parse the data, but don't commit anything to the database")
    p.add_argument("files", nargs="+", help="JSON file(s) containing tournament(s)")
    args = p.parse_args()
    if args.archetypes:
        archetype_parser = ArchetypeParser(args.archetypes)
    else:
        archetype_parser = False
    for filename in args.files:
        tournament, decks, matches, contents = load_json(filename)
        session.add(tournament)
        for player in decks:
            if player in contents:
                slots = []
                for card in contents[player]:
                    slot = Slot()
                    slot.cardname = card
                    slot.main, slot.side = contents[player][card]
                    slots.append(slot)
                decks[player].slots = slots
                if archetype_parser:
                    decks[player].loadContents()
                    decks[player].setArchetype(archetype_parser.classify(decks[player]))
            session.add(decks[player])
        for m in matches:
            session.add(m)
        if not args.dry_run:
            session.commit()
        print(tournament)
        print(f'{len(tournament.decks)} decks, {len(matches)} matches')
