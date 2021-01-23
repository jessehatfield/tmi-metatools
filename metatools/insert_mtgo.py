#!/usr/bin/env python

from metatools.database import *

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
    tournament = DBTournament(name=tname, date=tdate, format=extract_format(tname))
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
    return tournament, decks, matches, contents

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(f"Usage: {sys.argv[0]} <json file> [[json file 2] ...]")
    for filename in sys.argv[1:]:
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
            session.add(decks[player])
        for m in matches:
            session.add(m)
        session.commit()
        print(tournament)
