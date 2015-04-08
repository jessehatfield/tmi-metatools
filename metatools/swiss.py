#!/usr/bin/env python
"""Simulate a Swiss Tournament."""

from deck import Deck
from meta import Metagame
from tournament import Tournament
from match import Match
from stats import *
import pair

from math import log, ceil, floor
from random import random, shuffle
from operator import attrgetter

def alreadyPaired(deck1, deck2):
    """Check to see if two decks have played against each other
    already."""
    for match in deck1.matches:
        if match.deck2 == deck2:
            return True
    return False

class SimulatedTournament(Tournament):
    def __init__(self, name, meta):
        """Initialize a tournament and fill it with decks, based on the
        given metagame."""
        Tournament.__init__(self, name=name, numPlayers=meta.total)
        self.meta = meta
        self.byes = set()
        self.players = []
        p = 1
        for main in meta.archetypes:
            for sub in meta.archetypes[main]:
                for i in range(meta.archetypes[main][sub]):
                    deck = Deck(player=str(p), tournament=self, points=0, archetype=main, subarchetype=sub)
                    self.players.append(deck)
                    p += 1

    def run(self, numrounds=None, top8=True, trackDecks=[]):
        """Run a swiss tournament."""
        self.order()
        if numrounds:
            self.numRounds = numrounds
        else:
            self.numRounds = int(ceil(log(self.numPlayers, 2)))
        topx = { x : [ { deck: 0 for deck in self.meta.archetypes }
                for i in range(self.numRounds+1) ] for x in trackDecks }
        for x in trackDecks:
            for deck in self.players[:x]:
                topx[x][0][deck.archetype] += 1.0/x
        # Pair all but one rounds without tiebreakers...
        for round in range(1, self.numRounds):
            self.simplePair(round)
            for i in range(self.numPlayers):
                self.players[i].place = i+1
            self.order()
            for x in trackDecks:
                for deck in self.players[:x]:
                    topx[x][round][deck.archetype] += 1.0/x
        # Then consider tiebreakers for the final round.
        self.order(True)
        self.simplePair(self.numRounds)
        for i in range(self.numPlayers):
            self.players[i].place = i+1
        # Play the elimination rounds.
        if top8:
            self.topElim(8)
        # Finally, populate self.decks.
        for deck in self.players:
            self.decks.append(deck)

        for x in trackDecks:
            for deck in self.players[:x]:
                topx[x][self.numRounds][deck.archetype] += 1.0/x
        return topx

    def topElim(self, topx):
        """Play out the top X elimination rounds."""
        if self.numPlayers < 2 or topx < 2:
            return self.players[0]
        if self.numPlayers < topx:
            return self.topElim(topx/2)
        winners = []
        losers = []
        for i in range(topx/2):
            if self.play(self.players[i], self.players[topx-1-i], None):
                winners.append(i)
                losers.append(topx-1-i)
            else:
                winners.append(topx-1-i)
                losers.append(i)
        losers.sort()
        temp = self.players[:topx]
        for i in range(topx/2):
            self.players[i] = temp[winners[i]]
            self.players[topx/2 + i] = temp[losers[i]]
        return self.topElim(topx/2)

    def singleElim(self):
        """Run a single elimination tournament."""
        self.numRounds = int(floor(log(self.numPlayers, 2)))
        startingPlayers = 2 ** self.numRounds
        round = 1
        # If the number of players isn't a power of two, play matches until it is.
        # Give players who do not play byes.
        if self.numPlayers > startingPlayers:
            numPlaying = self.numPlayers - startingPlayers
            self.order()
            for i in range(0, numPlaying, 2):
                self.play(self.players[i], self.players[i+1], round)
            for i in range(numPlaying+1, self.numPlayers):
                self.players[i].points += 3
            # That was round 1
            self.numRounds += 1
            round += 1
        # Then play out each remaining round; each time pairing the previous winning half.
        numPlaying = startingPlayers
        while round <= self.numRounds:
            self.order()
            for i in range(0, numPlaying, 2):
                self.play(self.players[i], self.players[i+1], round)
            round += 1
            numPlaying /= 2
        # Assign final places.
        self.order()
        for i in range(self.numPlayers):
            self.players[i].place = i+1

    def order(self, tiebreakers=False):
        """Sort the list of players from highest placing to lowest. By default,
        don't consider tiebreakers: randomize within each point bracket."""
        shuffle(self.players)
        self.players.sort(key=attrgetter('points'), reverse=True)

    def awardBye(self):
        """If anyone should get a bye, make it the lowest-ranked player
        who hasn't gotten one yet. (Assumes self.players has been sorted.)"""
        index = None
        if self.numPlayers % 2 > 0:
            for i in range(self.numPlayers-1, -1, -1):
                if self.players[i] not in self.byes:
                    index = i
                    self.byes.add(self.players[i])
                    self.players[i].points += 3
                    #If everyone has somehow gotten a bye now, reset the bye list.
                    if len(self.byes) == self.numPlayers:
                        self.byes = set()
                    break
        return index

    def pair(self, round):
        """Generate and play pairings for this round. Guaranteed to find a
        valid pairing if one is possible. Uses a recursive pairing function to
        backtrack when necessary."""
        # Initialize
        players = self.players[:]
        bye = self.awardBye()
        if bye:
            players.pop(bye)
        pairings = []
        # Generate 
        pair.pair(players, pairings, alreadyPaired)
        # Play
        for i in range(0, len(pairings), 2):
            self.play(pairings[i], pairings[i+1], round)

    def simplePair(self, round):
        """Generate pairings for this round, then play them out.
        Begin at the top of the list of decks/players, and pair each
        player against the first unpaired player he/she hasn't played
        against already. If the end of the list is reached and there are
        no good pairings, pair the player against the next player in the
        list regardless."""
        pairings = []
        skip = set()
        bye = self.awardBye()
        if bye:
            skip.add(self.players[bye])
                    
        # Now pair the remaining players top-down.
        for i in range(self.numPlayers):
            paired = False
            if i in skip:
                continue
            for num_pass in (1, 2):
                for j in range(i+1, self.numPlayers):
                    if j in skip:
                        continue
                    # Only allow a repeat pairing if there is no other
                    # option (other than backtracking, i.e. don't mess
                    # with the pairings we've made so far).
                    if num_pass==1 and alreadyPaired(self.players[i], self.players[j]):
                        continue
                    pairings.append((i, j))
                    skip.add(i)
                    skip.add(j)
                    paired = True
                    break
                if paired:
                    break

        # Finally, play out the matches.
        for i, j in pairings:
            self.play(self.players[i], self.players[j], round)
        
    def play(self, deck1, deck2, round):
        """Play out a match between two decks, based on the matchup
        percentage given by the Metagame. Update the points and store
        the Match object."""
        p = self.meta.getFloatMatchup(deck1.archetype, deck2.archetype,
                deck1.subarchetype, deck2.subarchetype)
        d1 = 0
        d2 = 0
        winner = None
        loser = None
        if random() < p:
            d1 += 2
            deck1.points += 3
            winner = deck1
            loser = deck2
        else:
            d2 += 2
            deck2.points += 3
            winner = deck2
            loser = deck1
        m1 = Match(deck1, deck2, d1, d2, round=round)
        m2 = Match(deck2, deck1, d2, d1, round=round)
        deck1.matches.append(m1)
        deck2.matches.append(m2)
        return winner == deck1

if __name__ == "__main__":
    matchups = {
        'A': {
            '': {'A': {'': 0.5}, 'C': {'y': 0.55, 'x': 0.3}, 'B': {'': 0.6}}
        },
        'C': {
            'y': {'A': {'': 0.45}, 'C': {'y': 0.5, 'x': 0.4}, 'B': {'': 0.5}},
            'x': {'A': {'': 0.7}, 'C': {'y': 0.6, 'x': 0.5}, 'B': {'': 0.4}}
        },
        'B': {
            '': {'A': {'': 0.4}, 'C': {'y': 0.5, 'x': 0.6}, 'B': {'': 0.5}}}
        }
    counts = {'A': {'': 10}, 'C': {'y': 8, 'x': 4}, 'B': {'': 12}}
    meta = Metagame(counts, matchups)
    stats = [ getMWP(), getPercentile() ]

    decks = []
    for main in counts:
        for sub in counts[main]:
            deck = [ main, sub, [], {} ]
            for f, name, datatype in stats:
                deck[3][name] = []
            decks.append(deck)
    trials = 500
    for i in range(trials):
        t = SimulatedTournament('Trial {0}'.format(i), meta)
        t.run()
        for deck in decks:
            current = [ d for d in t if d.archetype == deck[0] and d.subarchetype == deck[1] ]
            deck[2].extend(current)
            for f, name, datatype in stats:
                deck[3][name].append(f(current))

    header = ','.join([s[1] for s in stats])
    print(header)
    deck = decks[0]
    for i in range(trials):
        row = []
        for f, name, datatype in stats:
            row.append(str(deck[3][name][i]))
        print(','.join(row))
