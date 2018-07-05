from .deck import *
from .util import mwp

from decimal import *
from math import floor
from numpy.random import multinomial
from sys import stderr

class Metagame(object):
    """Model of a metagame. Keeps track of:
        1) What archetypes exist
        2) How popular each one is
        3) Their matchups against each other"""

    def __init__(self, decks={}, matchups={}):
        """Explicitly specify a metagame.
        
        decks: A dictionary of the form {main:{sub1:count1, sub2:count2}},
               specifying popularity.
        matchups: A dictionary of the form
                  { mainA: { subA1: { mainB: { subB1: mwpA1B1, subB2: mwpA1B2 } } } }
        """
        self.archetypes = decks
        self.matchups = matchups
        self.total = 0
        for main in self.archetypes:
            for sub in self.archetypes[main]:
                self.total += self.archetypes[main][sub]

    @staticmethod
    def fromList(decks, counts, matchups):
        """Initialize a Metagame from a series of lists. Cannot specify
        subarchetypes.

        decks:  A list of deck names
        counts: A list of corresponding counts
        matchups: A 2-D list of matchups"""
        newdecks = {}
        newmatchups = {}
        for i in range(len(decks)):
            newdecks[decks[i]] = { '':counts[i] }
            newmatchups[decks[i]] = { '':{} }
            for j in range(len(decks)):
                newmatchups[decks[i]][''][decks[j]] = { '': matchups[i][j] }
        return Metagame(newdecks, newmatchups)

    def toList(self):
        """Express matchups as a two-dimensional list. Subarchetypes are ignored."""
        return [ [ self.getSingleMatchup(deck, deck2, None, None)
            for deck2 in self.archetypes ] for deck in self.archetypes ]


    def getCount(self, deck, sub=None):
        """Get the number of a particular deck present. If no
        subarchetype is given, total up all subarchetypes."""
        if sub:
            main = self.archetypes.get(deck, {})
            return main.get(sub, 0)
        else:
            if deck in self.archetypes:
                totals = [ self.archetypes[deck][x] for x in self.archetypes[deck] ]
                return sum(totals)
            else:
                return 0

    def getSub(self, deck):
        """Get a list of subarchetype names for a given deck name, in decreasing
        order of count."""
        counts = self.archetypes[deck]
        subnames = [ k for k in counts.keys() ]
        subnames.sort(key=lambda s: counts[s], reverse=True)
        return subnames

    def getTotal(self, decktypes, subarchetypes=False):
        """Get the total number of all decks in a list. If subarchetypes is
        true, expects a list of (main, sub) tuples; otherwise expects a list of
        archetype names."""
        total = 0
        if subarchetypes:
            for deck, sub in decktypes:
                total += self.getCount(deck, sub)
        else:
            for deck in decktypes:
                total += self.getCount(deck)
        return total

    def getPercent(self, deck, sub=None):
        """Get the percentage of the field made up by a particular deck.
        If no subarchetype is given, total up all subarchetypes."""
        return Decimal(self.getCount(deck, sub)) / self.total

    def getTotalPercent(self, decktypes, subarchetypes=False):
        """Get a total percentage of the field for a list of decks, or, if
        subarchetypes is true, (deck, sub) pairs."""
        return Decimal(self.getTotal(decktypes, subarchetypes)) / self.total

    def subPercent(self, deck, sub):
        """Get the percentage of decks of a particular archetype which
        have the given subarchetype."""
        return Decimal(self.getCount(deck, sub)) / self.getCount(deck)

    def getSingleMatchup(self, deck1, deck2, sub1='', sub2=''):
        """Get the match win percentage for a particular matchup.
        When subarchetype is None, get an average, weighted by the
        popularity of each subarchetype.

        deck1: Deck 1 (higher values mean this deck wins more)
        deck2: Deck 2
        sub1:  Subarchetype 1
        sub2:  Subarchetype 2"""
        if sub2 is None and sub1 is None:
            total = 0
            for sub1 in self.archetypes[deck1]:
                weight = self.subPercent(deck1, sub1)
                matchup = self.getSingleMatchup(deck1, deck2, sub1, None)
                total += (weight * matchup)
            return Decimal(total) / len(self.archetypes[deck1])
        elif sub2 is None:
            total = 0
            for sub2 in self.archetypes[deck2]:
                weight = self.subPercent(deck2, sub2)
                matchup = self.matchups[deck1][sub1][deck2][sub2]
                total += (weight * Decimal(matchup))
            return Decimal(total) / len(self.archetypes[deck2])
        elif sub1 is None:
            return 1 - self.getSingleMatchup(deck2, deck1, sub2, sub1)
        else:
            return self.matchups[deck1][sub1][deck2][sub2]

    def getFloatMatchup(self, deck1, deck2, sub1='', sub2=''):
        """Float version of getSingleMatchup. Less precise but faster."""
        if sub2 is None and sub1 is None:
            total = 0.0
            for sub1 in self.archetypes[deck1]:
                weight = float(self.subPercent(deck1, sub1))
                matchup = self.getFloatMatchup(deck1, deck2, sub1, None)
                total += weight * matchup
            return total / len(self.archetypes[deck1])
        elif sub2 is None:
            total = 0.0
            for sub2 in self.archetypes[deck2]:
                weight = float(self.subPercent(deck2, sub2))
                matchup = float(self.matchups[deck1][sub1][deck2][sub2])
                total += weight * matchup
            return total / len(self.archetypes[deck2])
        elif sub1 is None:
            return 1 - self.getFloatMatchup(deck2, deck1, sub2, sub1)
        else:
            return float(self.matchups[deck1][sub1][deck2][sub2])

    def getAggregateMatchup(self, group1, group2):
        """Get an aggregate match win percentage for decks in group 1
        against decks in group 2, weighted by the popularity of each
        archetype/subarchetype.
        
        group1: A collection of (archetype, subarchetype) pairs or just archetype names.
        group2: A collection of (archetype, subarchetype) pairs."""
        total1 = sum([ self.getCount(t[0], t[1]) for t in group1 ])
        total2 = sum([ self.getCount(t[0], t[1]) for t in group2 ])
        result = 0.0
        for main1, sub1 in group1:
            p1 = Decimal(self.getCount(main1, sub1)) / total1
            for main2, sub2 in group2:
                p2 = Decimal(self.getCount(main2, sub2)) / total2
                mu = getSingleMatchup(main1, sub1, main2, sub2)
                result += mu * p1 * p2
        return result

    def getMultipleMatchups(self, decks1, decks2, fromSub=False, toSub=False):
        """Get MWPs for all combinations of decks in one group and decks
        in another, broken down by archetype.

        decks1: List of 'from' archetypes.
        decks2: List of 'to' archetypes.
        fromSub: Break down 'from' decks by subarchetype.
        """
        matchups = {}
        for d1 in decks1:
            for d2 in decks2:
                if fromSub:
                    for s1 in self.archetypes[d1]:
                        matchups[(d1,s1)] = matchups.get((d1,s1), {})
                        if toSub:
                            for s2 in self.archetypes[d2]:
                                matchups[(d1,s1)][(d2,s2)] = self.getSingleMatchup(d1, d2, s1, s2)
                        else:
                            matchups[(d1,s1)][d2] = self.getSingleMatchup(d1, d2, s1, None)
                else:
                    matchups[d1] = matchups.get(d1, {})
                    matchups[d1][d2] = self.getSingleMatchup(d1, d2, None, None)
        return matchups

    def factory(self):
        """Initialize a MetaFactory based on this Metagame. Ignores subarchetypes."""
        decknames = sorted(self.archetypes.keys())
        popularity = []
        matchups = []
        for deck in decknames:
            popularity.append(self.getPercent(deck))
        matchups = self.toList()
        return MetaFactory(decknames, popularity, matchups)

    def winningField(self, numrounds, initial=None, matchups=None):
        """Get three list of tables, each containing a table for each
        round up to numrounds: 1) mapping each deck to the proportion of
        undefeated players expected to be playing that deck; 2) mapping
        each deck to the proporion of players of that deck expected to be
        undefeated; and 3) mapping each deck to a ratio of current field
        presence to original field presence.
        
        Assumes a single-eliminatino tournament with a number of players
        equal to some power of two."""
        precision = getcontext().prec
        getcontext().prec = 50
        winp = [ {} for i in range(numrounds+1) ]
        field = [ {} for i in range(numrounds+1) ]
        alive = [ {} for i in range(numrounds+1) ]
        norm = [ {} for i in range(numrounds+1) ]
        # field[0] is just the initial breakdown
        for deck in self.archetypes:
            if initial is None:
                field[0][deck] = Decimal(self.getPercent(deck))
            else:
                field[0][deck] = Decimal(initial[deck])
            alive[0][deck] = Decimal(1)
            norm[0][deck] = Decimal(1)
        for deck in self.archetypes:
            winp[0][deck] = Decimal(0)
            for deck2 in self.archetypes:
                matchup = None
                if matchups:
                    matchup = matchups[deck].get(deck2, None)
                else:
                    matchup = self.getSingleMatchup(deck, deck2)
                if matchup is None:
                    matchup = .5
                winp[0][deck] += Decimal(matchup) * field[0][deck2]
        # From then on,
        # alive[i][deck] = alive[i-1][deck] * winp[i-1][deck]
        # field[i][deck] = alive[i][deck] * field[0][deck] * 2^i
        # norm[i][deck] = field[i][deck] / field[0][deck]
        print >> stderr, 0, sum(field[0].values())
        for i in range(1, numrounds+1):
            for deck in self.archetypes:
                alive[i][deck] = alive[i-1][deck] * winp[i-1][deck]
                field[i][deck] = alive[i][deck] * field[0][deck] * (2**i)
                norm[i][deck] = field[i][deck] / field[0][deck]
            print >> stderr, i, sum(field[i].values())
            for deck in self.archetypes:
                winp[i][deck] = 0
                for deck2 in self.archetypes:
                    matchup = None
                    if matchups:
                        matchup = matchups[deck].get(deck2, None)
                    else:
                        matchup = self.getSingleMatchup(deck, deck2)
                    if matchup is None:
                        matchup = .5
                    winp[i][deck] += Decimal(matchup) * field[i][deck2]
        getcontext().prec = precision
        return (field, alive, norm, winp)

class ObservedMeta(Metagame):
    """Describe the metagame based on observed tournament results."""

    def __init__(self, tournaments, players=[], matchups={}):
        """Instantiate an observed metagame.
        
        tournaments: A list of Tournament objects.
        players: An optional list of players to restrict the field to.
        matchups: An optional dict of matchups.
        """
        self.tournaments = set(tournaments)
        self.players = players
        self.matchups = {}
        self.archetypes = {}
        self.total = 0
        #Compute the metagame. 
        for tournament in self.tournaments:
            for deck in tournament:
                if self.players and deck.player not in self.players:
                    continue
                main = deck.archetype
                sub = deck.subarchetype
                if main not in self.archetypes:
                    self.archetypes[main] = {}
                if sub not in self.archetypes[main]:
                    self.archetypes[main][sub] = 0
                self.archetypes[main][sub] += 1
                self.total += 1

    def getDecks(self, types=[], players=[]):
        """Return Deck objects belonging to this Metagame's Tournaments.
        
        types: return only those Decks with the listed archetypes
        players: return only those Decks with the listed players"""
        decks = []
        for t in self.tournaments:
            for d in t.decks:
                if types and d.archetype not in types:
                    continue
                if players and d.player not in players:
                    continue
                decks.append(d)
        return decks

class MetaFactory(object):
    """An object that can instantiate Metagames, based on some
    configuration."""

    def __init__(self, decknames, pvalues, matchups):
        """Create a MetaFactory, which can create Metagames.

        decknames: A list of archetype names.
        pvalues: A list of proportions, each corresponding to the
            appropriate deck in decknames. Should sum to 1.
        matchups: A 2D array of matchups, ordered in the same way, e.g.
            (1vs1, 1vs2, 1vs3), (2vs1, 2vs2, 2vs3), (3vs1, 3vs2, 3vs3))
            Should be fully specified."""
        self.decknames = decknames
        self.p = pvalues
        self.matchups = self.matchupGen(matchups)

    def matchupGen(self, matchups):
        """Take a 2D array of matchups and turn it into a dictionary
        that Metagame will be able to interpret."""
        sub = {}
        for i in range(len(self.decknames)):
            name = self.decknames[i]
            sub[name] = {'':{}}
            for j in range(len(self.decknames)):
                name2 = self.decknames[j]
                mp = matchups[i][j]
                sub[name][''][name2] = {'': mp}
        return sub

    def countGen(self, counts):
        """Take a list of counts and turn it into a dictionary that
        Metagame will be able to interpret."""
        decks = {}
        for i in range(len(self.decknames)):
            name = self.decknames[i]
            decks[name] = {}
            decks[name][''] = counts[i]
        return decks

    def sampleMeta(self, n):
        """Generate a Metagame with n players by randomly sampling from
        the distribution."""
        counts = multinomial(n, self.p)
        sample = self.countGen(counts)
        return Metagame(sample, self.matchups)

    def exactMeta(self, n):
        """Generate a Metagame with n players, with each deck making up
        as close to the proportion of the field that was specified as
        possible."""
        counts = [ n * p for p in self.p ]
        intcounts = [ int(floor(c)) for c in counts ]
        diff = [ c-int(floor(c)) for c in counts ]
        ndecks = len(self.decknames)
        add = sorted(range(ndecks), key=lambda i:diff[i], reverse=True)
        if sum(intcounts) < n:
            for i in add:
                intcounts[i] += 1
                if sum(intcounts) >= n:
                    break
        exact = self.countGen(intcounts)
        return Metagame(exact, self.matchups)
