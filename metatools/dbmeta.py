from metatools.meta import ObservedMeta, MetaFactory, Metagame
from metatools.database import getDecks, getMatches, deckQuery, DBDeck, func, getMatchTotals
from metatools.deck import Card, Deck
from metatools.util import mwp, mwp_record, record

from decimal import Decimal

class DBMeta(ObservedMeta):
    """Describe the metagame based on tournament results in the database."""
    def __init__(self, tournaments, players=[]):
        """Instantiate an observed metagame.
        
        tournaments: A list of Tournament objects.
        players: An optional list of players to restrict the field to."""
        self.tournaments = set(tournaments)
        self.tids = [ t.id for t in self.tournaments ]
        self.decks = []
        self.matches = []
        self.archetypes = { }
        self.matchups = { }
        self.players = players
#        for t in self.tournaments:
#            self.decks.extend(t.decks)
#        for t in self.tournaments:
#            self.matches.extend(t.matches)
        self.total = 0
        #Compute the metagame. 
        deckq = deckQuery(tournaments=self.tournaments, players=self.players)\
            .from_self(DBDeck.archetype, DBDeck.subarchetype, func.count('*'))\
            .group_by(DBDeck.archetype, DBDeck.subarchetype)
        for main, sub, count in deckq:
            if main not in self.archetypes:
                self.archetypes[main] = {}
            self.archetypes[main][sub] = count
            self.total += count

    def getSingleMatches(self, deck1, sub1, deck2, sub2):
        """Get Match objects for deck1,sub1 against deck2,sub2."""
        sublist1 = []
        sublist2 = []
        if sub1:
            sublist1 = [ sub1 ]
        if sub2:
            sublist2 = [ sub2 ]
        d1 = getDecks(tournaments=self.tournaments, archetypes=[deck1],
                subarchetypes=sublist1)
        if deck2:
            d2 = getDecks(tournaments=self.tournaments, archetypes=[deck2],
                    subarchetypes=sublist2)
            return getMatches(decks1=d1, decks2=d2)
        else:
            return getMatches(decks1=d1)

    def getNumMatches(self, deck, sublist=[]):
        """Get the number of matches for a deck, optionally restricted to
        specific subarchetypes."""
        decks = getDecks(tournaments=self.tournaments, archetypes=[deck],
                subarchetypes=sublist)
        total = 0
        for deck in decks:
            total += len(deck.matches)
        return total

    def getAggregateMatches(self, sub1, group1, sub2, group2):
        """Get Match objects for decks in group 1
        against decks in group 2.
        
        sub1: Break down group 1 into subarchetypes.
        group1: A collection of either archetypes or (archetype, subarchetype) pairs.
        sub2: Break down group 2 into subarchetypes.
        group2: A collection of either archetypes or (archetype, subarchetype) pairs."""
        decks1 = []
        if sub1:
            decks1 = getDecks(tids=self.tids, deckTypes=group1)
        else:
            decks1 = getDecks(tids=self.tids, archetypes=group1)
        decks2 = []
        if sub2:
            decks2 = getDecks(tids=self.tids, deckTypes=group2)
        else:
            decks2 = getDecks(tids=self.tids, archetypes=group2)
        if decks1 and decks2:
            return getMatches(decks1=decks1, decks2=decks2)
        else:
            return []

    def getSingleMatchup(self, deck1, deck2, sub1=None, sub2=None,
            datatype=Decimal):
        """Get the match win percentage for a particular matchup.

        deck1: Deck 1 (higher values mean this deck wins more)
        deck2: Deck 2
        sub1:  Subarchetype 1
        sub2:  Subarchetype 2
        datatype:  Type of result. Default is Decimal; float may be faster."""
        return mwp(self.getSingleMatches(deck1, sub1, deck2, sub2), datatype)

    def getFloatMatchup(self, deck1, deck2, sub1=None, sub2=None):
        return self.getSingleMatchup(deck1, deck2, sub1, sub2, float)

    def getAggregateMatchup(self, sub1, group1, sub2, group2):
        """Get an aggregate match win percentage for decks in group 1
        against decks in group 2, based on matches actually played.
        
        sub1: Break down group 1 into subarchetypes.
        group1: A collection of either archetypes or (archetype, subarchetype) pairs.
        sub1: Break down group 2 into subarchetypes.
        group1: A collection of either archetypes or (archetype, subarchetype) pairs."""
        matches = self.getAggregateMatches(sub1, group1, sub2, group2)
        return mwp(matches)

    def getMultipleMatchups(self, decks1, decks2, fromSub=False, correction=0):
        """Get MWPs for all combinations of decks in one group and decks
        in another, broken down by archetype.

        decks1: List of 'from' archetypes.
        decks2: List of 'to' archetypes.
        fromSub: Break down 'from' decks by subarchetype.
        """
        result = getMatchTotals(self.tids, decks1, decks2, fromSub)
        matchups = {}
        if fromSub:
            for d1, d2, s1, win, loss, draw in result:
                win += correction
                loss += correction
                matchups[(d1,s1)] = matchups.get((d1,s1), {})
                matchups[(d1,s1)][d2] = mwp_record(win, loss, draw)
        else:
            for d1, d2, win, loss, draw in result:
                win += correction
                loss += correction
                matchups[d1] = matchups.get(d1, {})
                matchups[d1][d2] = mwp_record(win, loss, draw)
        return matchups

    def factory(self, correction=0):
        """Initialize a MetaFactory based on this Metagame. Ignores subarchetypes."""
        decknames = sorted(self.archetypes.keys())
        popularity = []
        matchups = []
        mdict = self.getMultipleMatchups(decknames, decknames, correction=correction)
        for deck in decknames:
            row = []
            popularity.append(self.getPercent(deck))
            for deck2 in decknames:
                if deck in mdict and deck2 in mdict[deck]:
                    row.append(mdict[deck][deck2])
                else:
                    row.append(.5)
            matchups.append(row)
        return MetaFactory(decknames, popularity, matchups)

    def winningField(self, numrounds, initial=None, matchups=None, correction=1):
        if matchups is None:
            matchups = self.getMultipleMatchups(self.archetypes.keys(), self.archetypes.keys(), correction=correction)
        return Metagame.winningField(self, numrounds, initial=initial, matchups=matchups)
