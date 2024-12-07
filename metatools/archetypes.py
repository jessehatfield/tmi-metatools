#!/usr/bin/env python
"""Assign archetype names using rule-based logic configured via JSON."""


from datetime import datetime
import json
import os
import sys

from metatools.deck import Deck


def _load_json(filename):
    try:
        with open(filename) as file:
            json_data = json.load(file)
        return json_data
    except Exception as e:
        print(f'Error reading {filename} (expects well-formed JSON):', e)


class ArchetypeParser:
    unknown = "Unknown Deck"

    def __init__(self, dirname):
        """Initialize using the format specification located under the given directory, using the
        data model described by github.com/Badaro/MTGOArchetypeParser"""
        foo = _load_json(f'{dirname}/metas.json')
        self.metas = _load_json(f'{dirname}/metas.json')['Metas']
        self.color_overrides = _load_json(f'{dirname}/color_overrides.json')
        self.archetypes = []
        self.fallbacks = []
        self.start_dates = []
        for filename in os.listdir(f'{dirname}/Fallbacks'):
            if filename.lower().endswith('.json'):
                self.fallbacks.append(_load_json(f'{dirname}/Fallbacks/{filename}'))
        for filename in os.listdir(f'{dirname}/Archetypes'):
            if filename.lower().endswith('.json'):
                self.archetypes.append(_load_json(f'{dirname}/Archetypes/{filename}'))
        for i in range(len(self.metas)):
            meta = self.metas[i]
            dt = datetime.strptime(meta['StartDate'], '%Y-%m-%d')
            self.start_dates.append((dt, i))
        self.start_dates.sort(key=lambda x: x[0])

    def _atleast(self, threshold, targets, *card_dicts):
        n = 0
        matches = set()
        for card_dict in card_dicts:
            for card_name in card_dict:
              if card_dict[card_name] > 0 and card_name in targets:
                  matches.add(card_name)
                  if len(matches) >= threshold:
                      return True
        return False

    def test_condition(self, condition, maindeck, sideboard):
        if condition['Type'].lower() == "doesnotcontain":
            return not self._atleast(1, condition['Cards'], maindeck, sideboard)
        elif condition['Type'].lower() == "doesnotcontainmainboard":
            return not self._atleast(1, condition['Cards'], maindeck)
        elif condition['Type'].lower() == "doesnotcontainsideboard":
            return not self._atleast(1, condition['Cards'], sideboard)
        elif condition['Type'].lower() == "inmainboard":
            return self._atleast(1, condition['Cards'], maindeck)
        elif condition['Type'].lower() == "insideboard":
            return self._atleast(1, condition['Cards'], sideboard)
        elif condition['Type'].lower() == "oneormoreinmainboard":
            return self._atleast(1, condition['Cards'], maindeck)
        elif condition['Type'].lower() == "oneormoreinsideboard":
            return self._atleast(1, condition['Cards'], sideboard)
        elif condition['Type'].lower() == "twoormoreinmainboard":
            return self._atleast(2, condition['Cards'], maindeck)
        elif condition['Type'].lower() == "inmainorsideboard":
            return self._atleast(1, condition['Cards'], maindeck, sideboard)
        else:
            raise Exception(f"Doesn't know how to parse archetype condition type: {condition}'")

    def test_archetype(self, archetype, maindeck, sideboard):
        match = True
        for condition in archetype['Conditions']:
            if not self.test_condition(condition, maindeck, sideboard):
                match = False
                break
        if match:
            name = archetype['Name']
            # TODO: handle archetype['IncludeColorInName']
            return name
        else:
            return None

    def test_fallback(self, fallback, maindeck, sideboard, verbose=False):
        n_matches = 0
        n_cards = 0
        targets = set(fallback['CommonCards'])
        for card_name in maindeck:
            n_cards += 1
            if card_name in targets:
                n_matches += maindeck[card_name]
                if verbose:
                    print(f"fallback {fallback['Name']}: + {maindeck[card_name]} {card_name}")
        for card_name in sideboard:
            n_cards += 1
            if card_name in targets:
                n_matches += sideboard[card_name]
                if verbose:
                    print(f"fallback {fallback['Name']}: + {sideboard[card_name]} {card_name}")
        strength = 0.0 if n_cards == 0 else float(n_matches) / n_cards
        size = len(fallback['CommonCards'])
        return fallback['Name'], fallback['IncludeColorInName'], strength, size

    def classify(self, deck, min_similarity=0.1, verbose=False):
        if not deck.maindeck:
            raise Exception(f"No maindeck loaded for {deck}")
        if deck.count() < 50:
            raise Exception(f"Maindeck only contains {deck.count()} cards")
        matching_names = set()
        for archetype in self.archetypes:
            test_result = self.test_archetype(archetype, deck.getMain(), deck.getSide())
            if test_result:
                variant_match = ''
                for variant in archetype.get('Variants', []):
                    variant_match = self.test_archetype(variant, deck.getMain(), deck.getSide())
                    if variant_match:
                        break
                matching_names.add((test_result, variant_match))
        if verbose:
            print(f'Matches archetypes: {matching_names}')
        if len(matching_names) > 1:
            # TODO: enable equivalent of ConflictSolvingMode
            print("--------")
            print("Error parsing decklist:")
            deck.printList()
            print("--------")
            raise Exception(f"Multiple archetype matches found: {matching_names}\n")
        elif len(matching_names) == 0:
            fallbacks = []
            for fallback in self.fallbacks:
                fallbacks.append(self.test_fallback(fallback, deck.getMain(), deck.getSide(),
                    verbose=verbose))
            fallbacks.sort(key=lambda x: -x[3])
            fallbacks.sort(key=lambda x: x[2])
            # TODO: handle 'IncludeColorInName'
            if verbose:
                print('Tested against fallbacks:')
                for fallback in fallbacks:
                    print(f'\t{fallback}')
            if len(fallbacks) >= 0 and fallbacks[-1][2] > min_similarity:
                matching_names.add((fallbacks[-1][0], ''))
        if len(matching_names) == 0:
            print("--------\nWARNING: couldn't find an archetype or fallback for decklist:")
            deck.printList()
            print(f"-------- (using '{ArchetypeParser.unknown}')\n")
            matching_names.add(ArchetypeParser.unknown)
        return list(matching_names)[0]

    def get_meta(self, date):
        index = -1
        for start_date, i in self.start_dates:
            if start_date <= date: 
                index = max(index, i)
        if index < 0:
            raise Exception(f"No meta defined in archetype parser config for date {date}")
        return self.metas[index]


if __name__ == "__main__":
    parser = ArchetypeParser(sys.argv[1])
    for decklist in sys.argv[2:]:
        d = Deck.fromFile(decklist)
        result = parser.classify(d, verbose=True)
        print(f'{decklist}: {result}')
