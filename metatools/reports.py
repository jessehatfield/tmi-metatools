from metatools.util import *
from metatools.stats import *
from metatools.meta import *
from metatools.table import *

from math import log
import sys
import re
from operator import itemgetter

# Helper functions

def getStats(tournaments, context, outputs=[], top=[],
        percentTop=[], penetration=[], conversion=[], players=[]):
    """Return a list of statistics to report about a deck type (or group
    of decks).
    
    tournaments: List of tournaments to generate the statistic for
    context: Metagame to draw matchups from
    outputs: List of strings which correspond to statistics to include
             (see list below).
    top: List of numbers: include stats of the form "# of Top X"
    percentTop: List of numbers: include stats of the form "% of Top X"
    penetration: List of numbers: include stats of the form "% which made Top X"
    conversion: List of numbers: include stats of the form "% with at least X wins"
    players: Player names -- restrict the field to these players

    Each element of the returned list is a tuple of (key, (function,
    printable name, datatype)), where the function accepts one argument:
    a list of Decks.

    Supported statistics:
    n: number of decks 
    win: number of match wins
    loss: number of match losses
    draw: number of match draws
    matches: number of matches played
    avgplace: average (mean) place
    field: percentage of field
    known: percentage of known field
    mwp: match win percentage
    mwpo: match win percentage vs. other decks (no mirrors)
    percentile: average percentile (1 - place / players)
    ev: expected value (based on matchups from context and field breakdown of tournaments)
    """
    functions = {
        'n': getN(),
        'win': getRecord(0),
        'loss': getRecord(1),
        'draw': getRecord(2),
        'matches': getMatchTotal(),
        'matcheso': getMatchTotal(exclude_mirrors=True),
        'matchesk': getMatchTotal(known=True),
        'avgplace': getAvgPlace(),
        'field': getFieldP(tournaments=tournaments, players=players),
        'known': getFieldP(tournaments=tournaments, players=players, known=True),
        'mwp': getMWP(),
        'mwpk': getMWP(known=True),
        'mwpo': getMWP(exclude_mirrors=True),
        'percentile': getPercentile(),
        'mwpTop': getMWP(interval=[.5,1]),
        'mwpBottom': getMWP(interval=[0,.5]),
        'size': getSize(tournaments),
        'place': getExactPlace()
    }
    stats = []
    for key in outputs:
        if key in functions:
            stats.append((key, functions[key]))
        elif key == 'ev':
            stats.append((key, getEV(context, tournaments=tournaments, players=players)))
    for n in top:
        key = 't{0}'.format(n)
        stats.append((key, getTop(n)))
    for n in percentTop:
        key = 'p{0}'.format(n)
        stats.append((key, getPercentTop(n)))
    for n in penetration:
        key = 't{0}pen'.format(n)
        stats.append((key, getTopPenetration(n, tournaments=tournaments)))
    for n in conversion:
        key = 'wins>={0}'.format(n)
        stats.append((key, getPercentWinning(n, tournaments=tournaments)))
    return stats

def getTourneyStats(outputs=[], card_count=[], containing=[], p_card=[],
        p_containing=[]):
    """Return a list of statistics to report about a tournament.
    Each element is a tuple of
    (key, (function, printable name, datatype)), where the function
        accepts 1 argument: a list of Decks.
    outputs: List of strings which correspond to statistics to include
             (see list below).
    card_count: List of card names -- produces stats of the form
                "# of copies of X"
    containing: List of card names -- produces stats of the form
                "# of decks containing X"
    p_card: List of card names -- produces stats of the form
            "% of all copies X out of all copies of all cards"
    p_containing: List of card names -- produces stats of the form
                  "% of decks containing X"

    Supported statistics:
    date: Tournament date
    igr: Information Gain Ratio
    d: Simpson's Index of Diversity
    D: Simpson's Index of Diversity (w/replacement)
    nd: # of distinct decks
    sumd: Total # of decks
    cigr: Information Gain Ratio (Cards)
    cd: Simpson's Index of Diversity (Cards)
    cD: Simpson's Index of Diversity (w/replacement) (Cards)
    nc: # of distinct cards
    sumc: Total # of cards
    mi: Mutual information between card and archetype
    h: Information Entropy (Archetype)
    ch: Information Entropy (Cards)
    hC: Conditional entropy of card given archetype
    hCd: Conditional entropy of card given exact deck
    joint3: Joint entropy of 3 cards
    joint2: Joint entropy of 2 cards
    joint1: "Joint" entropy of 1 card
    hgiven1: Conditional entropy of card given another card
    hgiven2: Conditional entropy of card given two other cards
    """
    functions = {
        'date': (getDate, 'date', 'str'),
        'igr': (getDeckDiversity(igr), 'Info Gain Ratio (Deck)', 'precise'),
        'd': (getDeckDiversity(simpson), "Simpson's D (Deck)", 'precise'),
        'D': (getDeckDiversity(simpsonR), "Simpson's D (w/rep) (Deck)", 'precise'),
        'nd': (getDeckDiversity(len), "Distinct Decks", 'int'),
        'sumd': (getDeckDiversity(sum), "Total # of Decks", 'int'),
        'cigr': (getCardDiversity(igr), 'Info Gain Ratio (Card)', 'precise'),
        'cd': (getCardDiversity(simpson), "Simpson's D (Card)", 'precise'),
        'cD': (getCardDiversity(simpsonR), "Simpson's D (w/rep) (Card)", 'precise'),
        'nc': (getCardDiversity(len), "Distinct Cards", 'int'),
        'sumc': (getCardDiversity(sum), "Total # of Cards", 'int'),
        'mi' : (getMutualInformation(), "I(Card;Archetype)", 'float'),
        'h': (getDeckDiversity(entropy), 'Entropy (Archetype)', 'float'),
        'ch': (getCardDiversity(entropy), 'Entropy (Card)', 'float'),
        'ch2' : (getJointEntropy(2), "Joint Entropy (2 Cards)", 'float'),
        'ch3' : (getJointEntropy(3), "Joint Entropy (3 Cards)", 'float'),
        'hC' : (getConditionalEntropy(), "Entropy (Card|Archetype)", 'float'),
        'hgiven1' : (getCompoundEntropy(1), "Entropy (Card|1 Card)", 'float'),
        'hgiven2' : (getCompoundEntropy(2), "Entropy (Card|2 Cards)", 'float'),
        'hgiven3' : (getCompoundEntropy(3), "Entropy (Card|3 Cards)", 'float'),
        'hCd' : (getEntropyGivenDeck(), "Entropy (Card|Deck)", 'float')
    }
    stats = []
    for key in outputs:
        if key in functions:
            stats.append((key, functions[key]))
    for cn in card_count:
        key = 'total-{0}-count'.format(cn)
        stats.append((key, getCardCopies(cn, 'both')))
    for cn in containing:
        key = 'containing-{0}'.format(cn)
        stats.append((key, getNumContaining(cn, 'both')))
    for cn in p_card:
        key = 'p-{0}'.format(cn)
        stats.append((key, getPCopies(cn, 'both')))
    for cn in p_containing:
        key = 'p-containing-{0}'.format(cn)
        stats.append((key, getPContaining(cn, 'both')))
    return stats

def getCardStats(tournaments, outputs, top=None):
    """Return a list of statistics to report about a card.
    Each element is a tuple of
    (key, (function, printable name, datatype)), where the function
        accepts two arguments: a card name, and a list of decks.

    tournaments: List of tournaments to generate the statistic for.
    outputs: List of strings which correspond to statistics to include
             (see list below).
    top: A number: restrict stats to the top X decks.

    Supported statistics:
    decks: # of decks containing the card
    main: # of maindecks containin the card
    side: # of sideboards containing the card
    pdecks: % of decks containing the card
    pmain: % of maindecks containing the card
    pside: % of sideboards containing the card
    copies: Copies of the card
    maincopies: Maindeck copies of the card
    sidecopies: Sideboard copies of the card
    pcopies: Percent of all cards which are this card
    pmaincopies: Percent of all maindeck cards which are this card
    psidecopies: Percent of all sideboard cards which are this card
    mwp: Match win percentage of decks containing this card
    mwpWithout: Match win percentage of decks not containing this card
    """
    decks = []
    for t in tournaments:
        if top:
            decks.extend([d for d in t.decks if d.place and d.place <= top])
        else:
            decks.extend(t.decks)
    functions = {
        'decks': getNumContaining_card(decks, 'both'),
        'main': getNumContaining_card(decks, 'main'),
        'side': getNumContaining_card(decks, 'side'),
        'pdecks': getPContaining_card(decks, 'both'),
        'pmain': getPContaining_card(decks, 'main'),
        'pside': getPContaining_card(decks, 'side'),
        'copies': getCardCopies_card(decks, 'both'),
        'maincopies': getCardCopies_card(decks, 'main'),
        'sidecopies': getCardCopies_card(decks, 'side'),
        'pcopies': getPCopies_card(decks, 'both'),
        'pmaincopies': getPCopies_card(decks, 'main'),
        'psidecopies': getPCopies_card(decks, 'side'),
        'mwp': getMWP_card(decks, True),
        'mwpWithout': getMWP_card(decks, False)
    }
    stats = []
    for key in outputs:
        if key in functions:
            stats.append((key, functions[key]))
    return stats


# Report functions

def getList(decktypes, groups={}):
    """Generate a table that just lists the selected decks. 
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    """
    table = Table()
    table.addField(Field('Deck'))
    for decktype in decktypes:
        table.addRecord(decktype)
    for group in groups:
        table.addRecord(group)
    return table

def getBreakdown(tournaments, context, outputs=[], top=[], percentTop=[],
        penetration=[], conversion=[], decktypes=[], groups={}, players=[],
        sub=False):
    """
    tournaments: The list of Tournaments for which to generate a breakdown
    context: historical metagame, used for matchup data
    outputs: List of strings which correspond to statistics to include
             (see getStats for a list).
    top: List of numbers: include stats of the form "# of Top X"
    percentTop: List of numbers: include stats of the form "% of Top X"
    penetration: List of numbers: include stats of the form "% which made Top X"
    conversion: List of numbers: include stats of the form "% with at least X wins"
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    players: Player names -- restrict the field to these players
    sub: If true, break things down by subarchetype.
    """
    names = [ '{0} ({1})'.format(t.name, t.date) for t in tournaments ]
    deckstats = {}
    substats = {}
    groupstats = {}
    subtypes = {}
    groupnames = list(groups.keys())
    stats = getStats(tournaments, context, outputs=outputs, top=top,
            percentTop=percentTop, penetration=penetration,
            conversion=conversion,
            players=players)

    # Gather all relevant Deck objects:
    decks = {}  # Map deck types to Deck objects
    subdecks = {}  # Map deck types to maps from subtype to Deck object
    groupdecks = {}  # Map group names to Deck objects
    deckgroups = {}  # Map deck names to group names
    # Initialize dicts
    for decktype in decktypes:
        decks[decktype] = []
        deckgroups[decktype] = []
        if sub:
            subdecks[decktype] = {}
    for groupname in groupnames:
        groupdecks[groupname] = []
        for decktype in groups[groupname]:
            deckgroups[decktype].append(groupname)
    # Fill dicts
    for t in tournaments:
        for d in t.decks:
            # Skip if it's a player we're not interested in
            if players and d.player not in players:
                continue
            # Add to the appropriate deck (if we care about that deck)
            if d.archetype in decks:
                decks[d.archetype].append(d)
                # Add to the subarchetype, if we care about subarchetypes
                if sub:
                    if d.subarchetype in subdecks[d.archetype]:
                        subdecks[d.archetype][d.subarchetype].append(d)
                    else:
                        subdecks[d.archetype][d.subarchetype] = [d]
            # Add to the appropriate groups
            if d.archetype in deckgroups:
                for groupname in deckgroups[d.archetype]:
                    groupdecks[groupname].append(d)

    # Remove deck types with no corresponding decks:
    decktypes = [ dt for dt in decktypes if decks[dt] ]

    # Apply statistics to decks
    for decktype in decktypes:
        row = [ decktype ]
        for key, func in stats:
            f, name, datatype = func
            row.append(f(decks[decktype]))
        deckstats[decktype] = (decks[decktype], row)
        # Apply statistics to subarchetypes
        if sub:
            substats[decktype] = {}
            for subtype in subdecks[decktype]:
                row = [ subtype ]
                for key, func in stats:
                    f, name, datatype = func
                    row.append(f(subdecks[decktype][subtype]))
                substats[decktype][subtype] = (subdecks[decktype][subtype], row)
    # Apply statistics to groups
    for groupname in groupnames:
        row = [ groupname ]
        for key, func in stats:
            f, name, datatype = func
            row.append(f(groupdecks[groupname]))
        groupstats[groupname] = (groupdecks[groupname], row)
    # Sort decks and groups
    decktypes.sort()
    decktypes.sort(key=lambda d: len(deckstats[d][0]), reverse=True)
    groupnames.sort()
    groupnames.sort(key=lambda g: len(groupstats[g][0]), reverse=True)
    if sub:
        for decktype in decktypes:
            subtypes[decktype] = [ key for key in substats[decktype] ]
            subtypes[decktype].sort()
            subtypes[decktype].sort(key=lambda s: len(substats[decktype][s][0]),
                    reverse=True)


    # Prepare and return a Table for output
    table = Table()
    table.setTitle(', '.join(names))
    table.addField(Field('Deck'))
    for key, func in stats:
        f, name, datatype = func
        table.addField(Field(key, type=datatype, fieldName=name))
    for decktype in decktypes:
        row = deckstats[decktype][1]
        table.addRecord(*row)
        if sub and len(subtypes[decktype]) > 1:
            for subtype in subtypes[decktype]:
                row = substats[decktype][subtype][1]
                if row[0] == '':
                    row[0] = "Generic"
                table.addRecordLevel(1, *row)
    for groupname in groupnames:
        row = groupstats[groupname][1]
        table.addRecord(*row)
    return table

def getTrend(decktypes, tournies, context, outputs=[], top=[],
        percentTop=[], penetration=[], conversion=[], players=[], groupBy=None,
        begin=None, end=None, tstats=[], groups={}, onlyTopX=0, window=1):
    """
    decktypes: list of strings representing archetype names
    tournies: a list of Tournaments for the relevant time period
    context: historical metagame, used for matchup data
    outputs: List of strings which correspond to statistics to include
             (see getStats for a list).
    top: List of numbers: include stats of the form "# of Top X"
    percentTop: List of numbers: include stats of the form "% of Top X"
    penetration: List of numbers: include stats of the form "% which made Top X"
    conversion: List of numbers: include stats of the form "% with at least X wins"
    players: Player names -- restrict the field to these players
    groupBy: "week", "month", or None. Defaults to None -- treat
             tournaments individually.
    begin: Begin date. Must be set if groupBy is set.
    end:   End date. Must be set if groupBy is set.
    tstats: List of stats which are applied to entire tournaments.
            See getTourneyStats.
    groups: Dictionary of named groups of archetypes.
    onlyTopX: Only consider decks which placed <= X (if set to zero, don't use).
    window: Use a sliding window of n tournaments (overlapping), rather than
            treat them individually.
    """
    stats = getStats(tournies, context, outputs, top, percentTop,
            penetration, conversion, players)
    def buildName(deckname, statname):
        if len(decktypes) > 1:
            if len(stats) > 1:
                return '{0} {1}'.format(deckname, statname)
            else:
                return deckname
        else:
            if len(stats) > 1:
                return statname
            else:
                return '{0} {1}'.format(deckname, statname)

    # By default, treat the tournaments individually:
    xlabel = 'Tournament'
    tgroups = [ [t] for t in tournies ]
    xvalues = [ '{0} ({1})'.format(t.name, t.date) for t in tournies ]

    # If specified, group them by month:
    if groupBy == "month":
        xlabel = 'Month'
        tgroups, xvalues = groupByMonth(tournies, begin=begin,
                end=end)
        xvalues = [ d.strftime("%Y-%m") for d in xvalues ]

    # If specified, group them by week:
    elif groupBy == "week":
        xlabel = 'Week of'
        tgroups, xvalues = groupByWeek(tournies, begin=begin,
                end=end)
        xvalues = [ d.strftime("%Y-%m-%d") for d in xvalues ]

    # If specified, group them by sliding window of N tournaments:
    elif window > 1:
        xlabel = 'Latest {0} Events as of'.format(window)
        tgroups = groupByWindow(tournies, window)
        xvalues = [ '{0} ({1})'.format(g[-1].name, g[-1].date) for g in tgroups ]

    table = Table()
    table.addField(Field(xlabel))

    # Add Fields for deck-specific stats.
    for decktype in decktypes:
        for key, stat in stats:
            func, name, datatype = stat
            table.addField(Field('{0}--{1}'.format(decktype, key),
                type=datatype, fieldName=buildName(decktype, name)))
    # Add Fields for group-specific stats.
    for groupname in sorted(groups.keys()):
        for key, stat in stats:
            func, name, datatype = stat
            table.addField(Field('{0}--{1}'.format(groupname, key),
                type=datatype, fieldName=buildName(groupname, name)))
    # Add Fields for general tournament stats.
    for key, stat in tstats:
        func, name, datatype = stat
        table.addField(Field(name, type=datatype))

    # For each tournament or group of tournaments, construct a row.
    for i in range(len(tgroups)):
        row = [ xvalues[i] ]
        # Feed the stat functions the current tournament.

        stats = getStats(tgroups[i], context, outputs, top,
                percentTop, penetration, conversion, players)
        alldecks = set()
        for t in tgroups[i]:
            alldecks |= set(t.decks)
        # Restrict to top X decks if specified.
        if onlyTopX > 0:
            alldecks = [ d for d in alldecks if d.place and d.place <= onlyTopX ]
        # First, add deck-specific stats (once for each deck).
        for decktype in decktypes:
            decks = [ d for d in alldecks if d.archetype == decktype ]
            if players:
                decks = [ d for d in decks if d.player in players ]
            for key, stat in stats:
                func, name, datatype = stat
                row.append(func(decks))
        # Then, add archetype-group-specific stats (once for each group).
        for group in sorted(groups.keys()):
            decks = [ d for d in alldecks if d.archetype in groups[group] ]
            if players:
                decks = [ d for d in decks if d.player in players ]
            for key, stat in stats:
                func, name, datatype = stat
                row.append(func(decks))
        # Then, add general tournament stats (once only).
        for key, stat in tstats:
            func, name, datatype = stat
            row.append(func(alldecks))
        # Add the row to the resulting table.
        table.addRecord(*row)
    return table

def getDiversity(tournies, funcnames, top, infogain, infogainmatch, summary=False):
    """
    tournies: a list of Tournaments for the relevant time period
    funcnames: A list of strings corresponding to functions:
               h: Information entropy
               r: information gain ratio
               d: Simpson's index of diversity
               D: Simpson's index of diversity with replacement.
    top: A list of numbers; generates stats of the form "Diversity of Top X"
    infogain: A list of floats; generates stats of the form "Info gain (Top X%)"
    infogainmatch: Add "Information gain (match winners)"
    summarize: Summarize statistics for all tournaments examined.
    """
    functions = {
        'h': { 'func': entropy, 'precision': 2, 'display': 'H' },
        'r': { 'func': igr, 'precision': 4, 'display': 'Info Gain Ratio' },
        'd': { 'func': simpson, 'precision': 4, 'display': 'D' },
        'D': { 'func': simpsonR, 'precision': 4, 'display': 'D (w/rep)' }
    }
    if not funcnames:
        funcnames = ('h', 'd')

    # Create the table and appropriate fields.
    table = Table()
    table.addField(Field('Tournament'))
    for name in funcnames:
        if name == '-':
            continue
        display = functions[name]['display']
        precision = functions[name]['precision']
        table.addField(Field(display, type='float', precision=precision))
        for t in top:
            table.addField(Field('{0} (Top {1})'.format(display, t),
                type='float', precision=precision))
    if infogain is not None:
        if len(infogain) == 0:
            infogain = [.5]
        for x in infogain:
            table.addField(Field('InfoGain{0}'.format(x), fieldName='Information Gain (Top {0}%)'.format(x*100)))
    if infogainmatch:
        table.addField(Field('InfoGainMatch', fieldName='Information Gain (Match winners)'))

    # Fill the table with data.
    alldecks = []
    tophalves = {}
    for tournament in tournies:
        row = [ tournament.city ]
        counts = getCounts(tournament.decks)
        alldecks.extend(tournament.decks)
        for name in funcnames:
            if name == '-':
                continue
            func = functions[name]['func']
            row.append(func(counts))
            for t in top:
                topdecks = [ d for d in tournament.decks if d.place <= t ]
                row.append(func(getCounts(topdecks)))
        if infogain:
            for x in infogain:
                midpoint = tournament.numPlayers * x
                tophalf = [ d for d in tournament.decks if d.place <= midpoint ]
                topgain = entropy(getCounts(tournament.decks)) - entropy(getCounts(tophalf))
                row.append(topgain)
                if summary:
                    tophalves[x] = tophalves.get(x, []) + tophalf
        if infogainmatch:
            matchGain = infogainMatches(tournament.matches)
            row.append(matchGain)
        table.addRecord(*row)


    # Calculate overall statistics.
    if summary:
        row = [ 'Overall' ]
        counts = getCounts(alldecks)
        for name in funcnames:
            if name == '-':
                continue
            func = functions[name]['func']
            row.append(func(counts))
            for t in top:
                topdecks = [ d for d in alldecks if d.place <= t ]
                row.append(func(getCounts(topdecks)))
        if infogain:
            for x in infogain:
                topgain = entropy(getCounts(alldecks)) - entropy(getCounts(tophalves[x]))
                row.append(topgain)
        if infogainmatch:
            allmatches = []
            for deck in alldecks:
                allmatches.extend(deck.matches)
            matchGain = infogainMatches(allmatches)
            row.append(matchGain)
        table.addRecord(*row)

    return table

def getCardInfo(tournies, outputs, top):
    """Get information about the actual contents of the decks.
    tournies: a list of Tournaments for the relevant time period
    outputs: A list of statistics to output (see getCardStats).
    top: A number -- restrict stats to the top X decks.
    """
    # Get the statistics we'll be using.
    cstats = getCardStats(tournies, outputs, top)
    # Get the list of cards.
    allcards = set()
    for t in tournies:
        for d in t.decks:
            if (not top) or (d.place and d.place <= top):
                for s in d.slots:
                    allcards.add(s.cardname)
    cardnames = [ c for c in allcards ]

    # Calculate the statistics.
    cardstats = {}
    for cardname in allcards:
        row = [ cardname ]
        for key, func in cstats:
            f, name, datatype = func
            row.append(f(cardname))
        cardstats[cardname] = row

    # Build a table.
    table = Table()
    table.setTitle('Card Statistics')
    table.addField(Field('Card'))
    for key, func in cstats:
        f, name, datatype = func
        table.addField(Field(key, type=datatype, fieldName=name))
    for cardname in cardnames:
        row = cardstats[cardname]
        table.addRecord(*row)

    # Sort the table.
    table.sortKey(*outputs, **{'reverse': True})

    return table

def getMatchups(decktypes, label, meta, alternateMeta, altLabel, otherDecks,
        groups, players, nmatches=False, sub=False):
    """Get information about a deck/group's matchups against other
    decks/groups.
    decktypes: a list of deck names -- combine them and return their matchups
    label: what to call the deck/list of decks in the table
    meta: a Metagame to get matches from.
    alternateMeta: a Metagame to get another sample of matches from,
        or None to only report one result for each matchup (useful for current +
        historical data).
    altLabel: what to call the alternate metagame
    otherDecks: list of deck names -- get matchups against these.
    groups: list of groups, where a group is a list of the form
        [ groupname deckname1 deckname2 ... ] -- also get matchups against these
        groups.
    players: if empty, include all players; otherwise, include only listed
        players
    nmatches: if true, add a column with the total number of matches
    sub: if true, also get matchups against subarchetypes of other decks
    """
    decks = meta.getDecks(decktypes)
    field = getFieldP(players=players)[0](decks)
    winpercent = getMWP()[0](decks)

    # Create a Table, figure out what columns we need
    table = Table()
    table.setTitle('{0} -- {1:.2f}% of field, won {2:.2f}% of matches'.\
            format(label, field*100.0, winpercent*100.0))
    table.addField(Field('otherdeck', fieldName=label + ' vs. ', align='<'))
    table.addField(Field('record', fieldName='Record', align='^'))
    table.addField(Field('mwp', fieldName='Win %', type='percent'))
    if nmatches:
        table.addField(Field('n', fieldName='# of Matches', type='int'))
    if alternateMeta:
        table.addField(Field('alt_record', fieldName='{0} Record'.format(
            altLabel), align='^'))
        table.addField(Field('alt_mwp', fieldName='{0} Win %'.format(altLabel),
            type='percent'))
        if nmatches:
            table.addField(Field('alt_n', fieldName='# {0} Matches'.format(
                altLabel), type='int'))

    # Combine decks and groups into one list, where each group is then a list of
    # the form [ percent, name, deck1, deck2, ... ]
    otherDecks = [ [meta.getCount(other), other, other]
            for other in otherDecks ]
    groups = [ [meta.getTotal(groups[name]), name] + groups[name]
            for name in groups ]
    otherDecks.sort(key=itemgetter(2))
    otherDecks.sort(key=itemgetter(1))
    otherDecks.sort(key=itemgetter(0), reverse=True)
    groups.sort(key=itemgetter(1))
    allgroups = otherDecks + sorted(groups, reverse=True)

    # Get matchups against groups
    for group in allgroups:
        # If we're looking at the matchups for a single deck, and this is that
        # deck, skip its matchup against itself. Unless we're also doing
        # subarchetypes and this deck happens to have some.
        if len(group) == 3 and len(decktypes) == 1 and group[2] == decktypes[0] \
                and not (sub and len(meta.getSub(decktypes[0])) > 0):
            continue
        matches = meta.getAggregateMatches(False, decktypes, False, group[2:])
        winp = mwp(matches)
        win, loss, draw = record(matches)
        count = win+loss+draw
        if winp is None:
            winp = float('NaN')
        row = [ group[1], '{0}-{1}-{2}'.format(win, loss, draw), winp ]
        if nmatches:
            row.append(count)
        if alternateMeta:
            altMatches = alternateMeta.getAggregateMatches(False, decktypes,
                    False, group[2:])
            altWinp = mwp(altMatches)
            altWin, altLoss, altDraw = record(altMatches)
            altCount = altWin + altLoss + altDraw
            row.append('{0}-{1}-{2}'.format(altWin, altLoss, altDraw))
            row.append(altWinp)
            if nmatches:
                row.append(altCount)
        table.addRecord(*row)
        # If we're also doing subarchetypes, and this is a single deck, figure
        # out and go through the subarchetypes.
        if sub and len(group) == 3:
            main = group[1]
            subnames = meta.getSub(main)
            if len(subnames) > 1:
                for subname in subnames:
                    matches = meta.getAggregateMatches(False, decktypes, True,
                            [(main, subname)])
                    winp = mwp(matches)
                    if winp is None:
                        winp = float('NaN')
                    win, loss, draw = record(matches)
                    count = win+loss+draw
                    row = [1, subname, '{0}-{1}-{2}'.format(win, loss, draw), winp]
                    if nmatches:
                        row.append(count)
                    if alternateMeta:
                        matches = alternateMeta.getAggregateMatches(False,
                                decktypes, True, [(main, subname)])
                        winp = mwp(matches)
                        win, loss, draw = record(matches)
                        count = win+loss+draw
                        row.append('{0}-{1}-{2}'.format(win, loss, draw))
                        row.append(winp)
                        if nmatches:
                            row.append(count)
                    table.addRecordLevel(*row)

    return table

def getAllMatchups(decktypes, meta, alternateMeta, altLabel,
        groups, players, sub=False):
    """Get information about all pairwise matchups within a set of decks.
    decktypes: a list of deck names to consider
    meta: a Metagame to get matches from.
    alternateMeta: a Metagame to get another sample of matches from,
        or None to only report one result for each matchup (useful for current +
        historical data).
    altLabel: what to call the alternate metagame
    groups: list of groups, where a group is a list of the form
        [ groupname deckname1 deckname2 ... ] -- also get matchups involving
        these groups.
    players: if empty, include all players; otherwise, include only listed
        players
    sub: if true, also break down subarchetypes
    """
    decks = meta.getDecks(decktypes)
    field = getFieldP(players=players)[0](decks)
    winpercent = getMWP()[0](decks)

    # Create a Table, figure out what columns we need
    table = Table()
    table.setTitle('Matchups')
    table.addField(Field('deck1', fieldName='Deck 1', align='<'))
    table.addField(Field('sub1', fieldName='Sub-archetype 1', align='<'))
    table.addField(Field('deck2', fieldName='vs. Deck 2', align='<'))
    table.addField(Field('sub2', fieldName='Sub-archetype 2', align='<'))
    table.addField(Field('win', fieldName='Matches Won', align='^'))
    table.addField(Field('loss', fieldName='Matches Lost', align='^'))
    table.addField(Field('draw', fieldName='Matches Drawn', align='^'))
    table.addField(Field('mwp', fieldName='Match Win %', type='percent'))
    if alternateMeta:
        table.addField(Field('alt_win',
            fieldName='{0} Matches Won'.format(altLabel), align='^'))
        table.addField(Field('alt_loss',
            fieldName='{0} Matches Lost'.format(altLabel), align='^'))
        table.addField(Field('alt_draw',
            fieldName='{0} Matches Drawn'.format(altLabel), align='^'))
        table.addField(Field('alt_mwp',
            fieldName='{0} Match Win %'.format(altLabel), type='percent'))

    # Combine decks and groups into one list, where each group is then a list of
    # the form [ percent, name, deck1, deck2, ... ]
    decks = [ [meta.getCount(deck), deck, deck]
            for deck in decktypes ]
    groups = [ [meta.getTotal(groups[name]), name] + groups[name]
            for name in groups ]
    decks.sort(key=itemgetter(2))
    decks.sort(key=itemgetter(1))
    decks.sort(key=itemgetter(0), reverse=True)
    groups.sort(key=itemgetter(1))
    allgroups = decks + sorted(groups, reverse=True)

    def stats(matches):
        win, loss, draw = record(matches)
        winp = mwp(matches)
        winp = float('NaN') if winp is None else winp
        return [ win, loss, draw, winp ]
    def combinedStats(s1, d1, s2, d2):
        matches = meta.getAggregateMatches(s1, d1, s2, d2)
        l = stats(matches)
        if alternateMeta:
            altMatches = alternateMeta.getAggregateMatches(s1, d1, s2, d2)
            l = l + stats(altMatches)
        return l
    def relevantSubtypes(group):
        if sub and len(group1) == 3 and len(meta.getSub(group[1])) > 1:
            return meta.getSub(group[1])
        else:
            return []

    # Get matchups between groups
    for group1 in allgroups:
        main1 = group1[1]
        decks1 = group1[2:]
        for group2 in allgroups:
            main2 = group2[1]
            decks2 = group2[2:]
            # Any vs. Any
            results = combinedStats(False, decks1, False, decks2)
            row = [ main1, "", main2, "" ] + results
            table.addRecord(*row)
            # Optionally, check the pairwise subarchetypes.
            subnames1 = relevantSubtypes(group1)
            subnames2 = relevantSubtypes(group2)
            for sub1 in subnames1:
                # Sub vs. Any
                results = combinedStats(True, [(main1, sub1)], False, decks2)
                row = [ main1, sub1, main2, ""  ] + results
                table.addRecordLevel(1, *row)
                for sub2 in subnames2:
                    # Sub vs. Sub
                    results = combinedStats(True, [(main1, sub1)],
                            True, [(main2, sub2)])
                    row = [ main1, sub1, main2, sub2 ] + results
                    table.addRecordLevel(2, *row)
            for sub2 in subnames2:
                # Any vs. Sub
                results = combinedStats(False, decks1, True, [(main2, sub2)])
                row = [ main1, "", main2, sub2 ] + results
                table.addRecordLevel(1, *row)
    return table

def explain(deckname, meta, historicalMeta, order):
    """Try to explain a deck's EV and win percentage in the metagame. Identify
    those matchups which contribute to its wins/losses the most.
    deckname: Explain this deck.
    meta: Explain it's performance/EV in this metagame.
    historicalMeta: Use this metagame for matchups for EV calculation.
    order: What stat to order by: w, l, ev, evneg, winp, or lossp."""
    decks = meta.getDecks([deckname])
    poffield = getFieldP()[0](decks)
    winpercent = getMWP()[0](decks)
    ev = getEV(historicalMeta)[0](decks)
    nmatches = meta.getNumMatches(deckname)
    # If win% starts at .5, each win adds this much and each loss subtracts:
    indmatch = .5/nmatches
    data = []
    for decktype in meta.archetypes:
        field = float(meta.getPercent(decktype))
        matches = meta.getSingleMatches(deckname, None, decktype, None)
        win, loss, draw = record(matches)
        winp = mwp(matches)
        hmatches = historicalMeta.getSingleMatches(deckname, None, decktype, None)
        hwin, hloss, hdraw = record(hmatches)
        hwinp = mwp(hmatches)
        evcont = None
        if hwinp is not None:
            hwinp = float(hwinp)
            evcont = (hwinp - .5) * field
        else:
            evcont = 0.0
        mwpcont = None
        winpcont = 0.0
        if winp is not None:
            winpcont = (win - loss) * indmatch
        data.append([decktype, field, win, loss, draw, winp, hwinp, evcont, winpcont])

    data.sort()
    if order=='w':
        data.sort(key=itemgetter(2), reverse=True)
    elif order=='l':
        data.sort(key=itemgetter(3), reverse=True)
    elif order=='ev':
        data.sort(key=itemgetter(7), reverse=True)
    elif order=='evneg':
        data.sort(key=itemgetter(7))
    elif order=='winp':
        data.sort(key=itemgetter(8), reverse=True)
    elif order=='lossp':
        data.sort(key=itemgetter(8))

    # Create a Table, figure out what columns we need
    table = Table()
    table.setTitle('{0} -- {1:.2f}% of field, won {2:.2f}% of matches, EV = {3:.2f}%'.\
            format(deckname, poffield*100.0, winpercent*100.0, ev*100.0))
    table.addField(Field('otherdeck', fieldName='Deck', align='<'))
    table.addField(Field('record', fieldName='Record', align='^'))
    table.addField(Field('mwp', fieldName='Win %', type='percent'))
    table.addField(Field('hmwp', fieldName='Historical Win %', type='percent'))
    table.addField(Field('field', fieldName='% of Field', type='percent'))
    table.addField(Field('evcont', fieldName='EV Contribution', type='percent'))
    table.addField(Field('winpcont', fieldName='Win % Contribution', type='percent'))

    # Fill the Table.
    for deck, field, win, loss, draw, winp, hwinp, evcont, winpcont in data:
        table.addRecord(deck, '{0}-{1}-{2}'.format(win, loss, draw), winp,
                hwinp, field, evcont, winpcont)

    return table

def getHistory(tournaments, context, outputs=[], top=[], percentTop=[],
        penetration=[], conversion=[], decktypes=[], players=[], topX=0):
    """Return a table of individual tournament appearances. Include player name,
    deck name, tournament information, and specified performance metrics.
    tournaments: List of tournaments to look at
    context: List of tournaments to draw matchup data from
    outputs: List of strings which correspond to statistics to include
             (see getStats for a list, note that they will only be applied to
             *individual* decks, so some stats may be less than interesting,
             e.g. %TopX can only be 0 or 100).
    top: List of numbers: include stats of the form "# of Top X"
    percentTop: List of numbers: include stats of the form "% of Top X"
    penetration: List of numbers: include stats of the form "% which made Top X"
    conversion: List of numbers: include stats of the form "% with at least X wins"
    decktypes: list of strings representing archetype names
    players: Player names -- restrict the field to these players
    topX: single number; only report finishis within the top X"""
    astats = getStats(tournaments, context, outputs=outputs, top=top,
            percentTop=percentTop, penetration=penetration,
            conversion=conversion,
            players=players)
    # Get the full list of appearances/finishes, and calculate any stats we need
    data = {}
    deckIDs = []
    # Transform player names into a regexp, where we only require the beginning
    # to match
    pattern = ''
    for i in range(len(players)):
        pattern += '|' + players[i]
    regexp = re.compile(pattern[1:], re.IGNORECASE)
    print(decktypes)
    for tourney in tournaments:
        for deck in tourney.decks:
            if topX > 0 and (deck.place is None or deck.place > topX):
                continue
            if decktypes and deck.archetype not in decktypes:
                continue
            if players:
                m = regexp.match(deck.player)
                if m is None:
                    continue
            deckIDs.append(deck.id)
            row = [ deck.player ]
            for key, func in astats:
                f, name, datatype = func
                row.append(f([deck]))
            row = row + [ tourney.date, tourney.name, deck.archetype ]
            data[deck.id] = (deck, row)
    # Sort data, if we want
    deckIDs.sort(key=lambda x: data[x][0].place, reverse=False)
    deckIDs.sort(key=lambda x: data[x][0].tournament.date, reverse=False)
    deckIDs.sort(key=lambda x: data[x][0].player, reverse=False)
    # Collect in a table and return
    table = Table()
#    table.addField(Field('player', fieldName='Player', align='<'))
#    table.addField(Field('archetype', fieldName='Deck', align='<'))
#    table.addField(Field('event', fieldName='Event', align='<'))
#    table.addField(Field('date', fieldName='Date', align='<'))

    table.addField(Field('player', fieldName='Player', align='<'))
    for key, func in astats:
        f, name, datatype = func
        table.addField(Field(key, type=datatype, fieldName=name))
    table.addField(Field('date', fieldName='Date', align='<'))
    table.addField(Field('event', fieldName='Event', align='<'))
    table.addField(Field('archetype', fieldName='Deck', align='<'))

    for deckID in deckIDs:
        deck, row = data[deckID]
        table.addRecord(*row)
    return table
