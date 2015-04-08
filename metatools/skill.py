from metatools.database import *
from metatools.util import *
from metatools.table import *

def skillMatchup(deckA, deckB, tournaments):
    aDecks = getDecks(archetypes=[deckA], tournaments=tournaments)
    bDecks = getDecks(archetypes=[deckB], tournaments=tournaments)

    aplayers = { a.player for a in aDecks }
    bplayers = { b.player for b in bDecks }

    for player in aplayers:
        playerDecks = getDecks(players=[player], tournaments=tournaments)
        playerMatches = getMatches(decks1=playerDecks)
        matchupMatches = getMatches(decks1=aDecks, decks2=bDecks)
        playerOther = [ m for m in playerMatches if m.deck2.archetype != deckB ]
        matchupOther = [ m for m in matchupMatches if m.deck1.player != player ]
        matchupPlayer = [ m for m in playerMatches if m.deck2.archetype == deckB ]

        print(player)
        for l, s in [ (playerMatches, "Player's matches"), (matchupMatches,
            "Matchup"), (playerOther, "Player outside of matchup"),
            (matchupOther, "Matchup outside of player"), (matchupPlayer,
            "Matchup and player") ]:
            print("{0}: {1} ({2})".format(s, record(l), mwp(l)))
        print()

def skillDeck(decktypes, groups, historicalMetagame, tournies, min_other,
        min_deck, min_all, other):
    """Generate a table of players who have played the given decks, and their
    performance with the given decks.
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    min_other: require this many matches from other decks
    min_deck: require this many matches from individual deck
    min_all: require this many matches total
    other: If True, report win % with other decks as well.
    """
    decknames = decktypes[:]
    allarchetypes = decktypes[:]
    archetypelist = [ [deck] for deck in decktypes ]
    for g in groups:
        decknames += g[0]
        archetypelist.append(g[1:])
        allarchetypes += g[1:]

    table = Table()
    for name in decknames:
        if other:
            table.addField(Field('pnon{0}'.format(name), type='percent',
                fieldName='Win % (non-{0})'.format(name)))
        table.addField(Field('p{0}'.format(name), type='percent',
            fieldName='Win % ({0})'.format(name)))
        table.addField(Field('n{0}'.format(name), type='int',
            fieldName='# of Matches ({0})'.format(name)))

    deck = decktypes[0]

    alldecks = getDecks(archetypes=allarchetypes, tournaments=tournies)
    players = { d.player for d in alldecks }
    for player in players:
        row = []
        playerDecks = getDecks(players=[player], tournaments=tournies)
        playerMatches = getMatches(decks1=playerDecks)
        for i in range(len(decknames)):
            deck = decknames[i]
            archetypes = archetypelist[i]
            playerDeckMatches = []
            playerOtherMatches = []
            for match in playerMatches:
                if match.deck1.archetype in archetypes:
                    playerDeckMatches.append(match)
                else:
                    playerOtherMatches.append(match)

            pOther = mwp(playerOtherMatches)
            pDeck = mwp(playerDeckMatches)
            pAll = mwp(playerMatches)
            nOther = len(playerOtherMatches)
            nDeck = len(playerDeckMatches)
            nAll = len(playerMatches)

            if other:
                if nOther >= min_other and nDeck >= min_deck and nAll >= min_all:
                    row.extend([pOther, pDeck, nDeck])
                else:
                    row.extend([float('NaN'), float('NaN'), 0])
            else:
                if nDeck >= min_deck:
                    row.extend([pDeck, nDeck])
                else:
                    row.extend([float('NaN'), 0])
        table.addRecord(*row)
    return table

def recordsDeck(decktypes, groups, metagame, tournies):
    """Generate a table of players who have played the given decks, and
    their performance with the given decks.
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    tournies: a list of Tournaments from which to gather records.
    """
    decknames = decktypes[:]
    allarchetypes = decktypes[:]
    archetypelist = [ [deck] for deck in decktypes ]
    for g in groups:
        decknames += g[0]
        archetypelist.append(g[1:])
        allarchetypes += g[1:]

    table = Table()
    table.addField(Field('player', type='str'))
    for name in decknames:
        table.addField(Field('p{0}'.format(name), type='percent',
            fieldName='Win % ({0})'.format(name)))
        table.addField(Field('n{0}'.format(name), type='int',
            fieldName='# of Matches ({0})'.format(name)))

    deck = decktypes[0]

    alldecks = getDecks(archetypes=allarchetypes, tournaments=tournies)
    players = { d.player for d in alldecks }
    for player in players:
        row = [player]
        playerDecks = getDecks(players=[player], tournaments=tournies)
        playerMatches = getMatches(decks1=playerDecks)
        for i in range(len(decknames)):
            deck = decknames[i]
            archetypes = archetypelist[i]
            playerDeckMatches = []
#            playerOtherMatches = []
            for match in playerMatches:
                if match.deck1.archetype in archetypes:
                    playerDeckMatches.append(match)
#                else:
#                    playerOtherMatches.append(match)

#            pOther = mwp(playerOtherMatches)
            pDeck = mwp(playerDeckMatches)
#            pAll = mwp(playerMatches)
#            nOther = len(playerOtherMatches)
            nDeck = len(playerDeckMatches)
#            nAll = len(playerMatches)

            if nDeck > 0:
                row.extend([pDeck, nDeck])
        table.addRecord(*row)
    return table
