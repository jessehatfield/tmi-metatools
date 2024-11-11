from metatools.database import *
from metatools.util import *
from metatools.meta import ObservedMeta, PairedMeta

from itertools import product

#-----------------------------------------------------------------------
# Statistics for a group of decks. Each function is a generator
# function, optionally taking in arguments to provide background
# information or refine queries. The result is a tuple containing:
# 1. a function which takes a collection of decks and returns a statistic.
# 2. a displayable name of the statistic
# 3. a string describing the type of data: 'int', 'float', 'percent'
#-----------------------------------------------------------------------

def getN():
    """Get total appearances for a list of decks."""
    return (len, '# in Field', 'int')

def getFieldP(tournaments=None, players=[], known=None):
    """Get percentage of field for a list of decks.

    tournaments: Tournaments to calculate the percentage for. If
        omitted, use all tournaments to which any of the decks belong.
    players: Players to calculate the percentage of. If omitted, use the
        entire field for each tournament."""
    n = 0
    if tournaments:
        n = sum(( t.getNumPlayers(players=players) for t in tournaments ))
    if known:
        obs = ObservedMeta(tournaments)
        n -= obs.getCount('Unknown')
    def fieldp(decks):
        tlist = tournaments
        total = n
        if not tlist:
            tlist = { d.tournament for d in decks }
            total = sum(( t.getNumPlayers(players=players) for t in tlist ))
        if known:
            if all((d.archetype == 'Unknown' for d in decks)):
                return float('NaN')
        count = len(decks)
        if total > 0:
            return float(count)/total
        else:
            return float('NaN')
    if known:
        return (fieldp, '% of Known', 'percent')
    return (fieldp, '% of Field', 'percent')

def getMWP(interval=None, exclude_mirrors=False, known=False, ub=None, lb=None):
    """Get match win percentage for a list of decks."""
    name = 'Win %'
    if interval:
        name = 'Win % ({0:.0f}%-{1:.0f}%)'.format(interval[0]*100, interval[1]*100)
    if exclude_mirrors:
        name = '{0} vs. Other'.format(name)
    if known:
        name = '{0} vs. Known'.format(name)
    if lb:
        name += f' ({lb*100}% lower bound)'
    elif ub:
        name += f' ({ub*100}% upper bound)'
    def matchwin(decks):
        matches = [ m for d in decks for m in d.getMatches() ]
        if exclude_mirrors:
            matches = [ m for d in decks for m in d.getMatches() if m.deck2 not in decks ]
        if known:
            matches = [ m for m in matches if m.deck2.archetype != 'Unknown' ]
        if interval:
            records = [ (mwp(d.getMatches()), d) for d in decks if d.getMatches() ]
            records.sort()
            minMWP = int(interval[0] * len(records))
            maxMWP = int(interval[1] * len(records))
            selected = records[minMWP:maxMWP]
            matches = [ m for r in selected for m in r[1].matches ]
        if matches:
            if lb:
                return float(mwp_ci(matches, lb)[0])
            elif ub:
                return float(mwp_ci(matches, ub)[1])
            else:
                return float(mwp(matches))
        else:
            return float('NaN')
    return (matchwin, name, 'percent')

def getRecord(i=None, known=False):
    """Get match record for a list of decks.
    
    index: Which part of the record to return -- 0 for wins, 1 for
        losses, 2 for draws. If not given, default to returning a tuple
        of all three."""
    name = 'Record'
    if i is not None:
        name = ('Wins', 'Losses', 'Draws')[i]
    def matchrecord(decks):
        matches = [ m for d in decks for m in d.getMatches() ]
        if known:
            matches = [ m for d in decks for m in d.getMatches() if m.deck2.archetype != 'Unknown' ]
        r = record(matches)
        if i is None:
            return r
        else:
            return r[i]
    return (matchrecord, name, 'int')

def getMatchTotal(exclude_mirrors=False, known=False):
    """Get total number of matches for a list of decks.
    """
    record = getRecord(known=known)[0]
    def matches(decks):
        total = 0
        if exclude_mirrors:
            for d in decks:
                for m in d.getMatches():
                    if m.deck2 not in decks:
                        total += 1
        else:
            for x in record(decks):
                if x:
                    total += x
        return total
    name = 'Matches'
    if exclude_mirrors:
        name = 'Matches (other)'
    if known:
        name = 'Matches vs. Known'
    return (matches, name, 'int')

def getAvgPlace():
    """Get average place for a list of decks."""
    def avgplace(decks):
        n = sum((1 for d in decks if d.place))
        total = sum((d.place for d in decks if d.place ))
        if n == 0:
            return float('NaN')
        return float(total)/n
    return (avgplace, 'Avg. Place', 'float')

def getExactPlace():
    """Get average place for a list of decks."""
    def avgplace(decks):
        n = sum((1 for d in decks if d.place))
        total = sum((d.place for d in decks if d.place ))
        if n == 0:
            return float('NaN')
        return float(total)/n
    return (avgplace, 'Place', 'int')

def getPercentile():
    """Get average percentile for a list of decks."""
    def avgpercentile(decks):
        n = len(decks)
        percentiles = [ 1 - (float(d.place)/d.tournament.numPlayers) for d in decks if d.place ]
        total = sum(percentiles)
        return float(total)/n
    return (avgpercentile, 'Percentile', 'percent')

def getEV(context, tournaments=None, fromSub=False, smartSub=False,
        players=[], usePairings=False):
    """Get expected value for a list of decks.

    context: Metagame to be used for matchup data.
    tournaments: Tournaments to calculate the statistic for. If
        omitted, use all tournaments to which any of the decks belong.
    fromSub: Use the group members' subarchetypes to determine matchups.
    smartSub: Use the group members' subarchetypes if all members have
            the same archetype and subarchetype.
    players: Restrict calculations to these players.
    usePairings: Use the actual counts of each archetype the decks were paired against,
            rather than the overall field of the tournaments. 
    """
    alldecks = list(context.archetypes.keys())
    matchupsMain = context.getMultipleMatchups(alldecks, alldecks)
    if fromSub or smartSub:
        matchupsSub = context.getMultipleMatchups(alldecks, alldecks, True)
    def ev_func(decks):
        archetypesMain = {}
        archetypesBoth = {}
        for d in decks:
            main = d.archetype
            sub = d.subarchetype
            archetypesMain[main] = archetypesMain.get(main, 0) + 1
            archetypesBoth[(main, sub)] = archetypesBoth.get((main, sub), 0) + 1
        tlist = tournaments
        if not tlist:
            tlist = { d.tournament for d in decks }
        if usePairings:
            thisMeta = PairedMeta(decks, players=players)
        else:
            thisMeta = ObservedMeta(tlist, players=players)
        result = 0.0
        archetypes = archetypesMain
        matchups = matchupsMain
        fSub = fromSub
        if smartSub and len(archetypesBoth) == 1:
            fSub = True
        if fSub:
            archetypes = archetypesBoth
            matchups = matchupsSub
        for decktype in archetypes:
            n = archetypes[decktype]
            ev = 0.0
            for other in thisMeta.archetypes:
                p = thisMeta.getCount(other)/float(thisMeta.total)
                mwp = matchups.get(decktype, {}).get(other, .5)
                ev += p * float(mwp)
            result += ev * n / len(decks)
        return result
    oppType = 'Pairings' if usePairings else 'Field'
    return (ev_func, f'EV vs. {oppType}', 'percent')

def getTop(n):
    """Get the number of top n placings for a list of decks.
    n: Cutoff -- count decks placing n or better.
    """
    def top_func(decks):
        t = 0
        for d in decks:
            if d.place <= n:
                t += 1
        return t
    name = 'Top {0}'.format(n)
    return (top_func, name, 'int')

def getPercentTop(n, tournaments=None):
    """Get the percentage of the top n made up by these decks.
    n: Cutoff -- for example, if n=8 and 2 of the decks made top 8,
    return .25.
    tournaments: Tournaments to calculate the statistic for. If
        omitted, use all tournaments to which any of the decks belong.
    """
    countTop = getTop(n)[0]
    def p_top_func(decks):
        tlist = tournaments
        if not tlist:
            tlist = { d.tournament for d in decks }
        if not tlist:
            return 0.0
        return countTop(decks) / float(n*len(tlist))
    name = '% of Top {0}'.format(n)
    return (p_top_func, name, 'percent')

def getTopPenetration(n, tournaments=None):
    """Get the percentage of these decks which made the top n.
    n: Cutoff -- for example, if n=8 and 2 of 20 decks made top 8,
    return .1.
    """
    countTop = getTop(n)[0]
    def penetration_func(decks):
        if len(decks) == 0:
            return float('NaN')
        return float(countTop(decks)) / len(decks)
    name = 'Top {0} Pen.'.format(n)
    return (penetration_func, name, 'percent')

def getPercentWinning(n, tournaments=None):
    """Get the percentage of these decks which won at least a number of matches.
    n: Match win count threshold -- for example, if n=6 in an eight-round
        tournament, 2 of 20 decks had record 6-2, and one had 7-1, then return
        0.15.
    """
    def threshold_func(decks):
        if len(decks) == 0:
            return float('NaN')
        count = 0
        for deck in decks:
            if deck.getMatches() and record(deck.getMatches())[0] >= n:
                count += 1
        return float(count) / len(decks)
    name = 'Match Wins >= {0}'.format(n)
    return (threshold_func, name, 'percent')

def getDate(decks):
    """Get the date of the earliest tournament involved.""" 
    if len(decks) == 0:
        return None
    dates = [ d.tournament.date for d in decks ]
    dates.sort()
    return dates[0].strftime("%Y-%m-%d")

def getCardCopies(cardname, slots='both', reverse=False):
    """Get the number of copies of a particular card.
    cardname: The name of the card.
    slots: 'main', 'side', or 'both' -- which copies to count."""
    def copies_func(decks):
        total = 0
        for d in decks:
            for s in d.slots:
                if s.cardname and s.cardname == cardname:
                    if slots in ('main', 'both'):
                        total += s.main
                    if slots in ('side', 'both'):
                        total += s.side
        return total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '# {0}{1}'.format(cardname, temp)
    return (copies_func, name, 'int')

def getNumContaining(cardname, slots='both'):
    """Get the number of decks containing a particular card.
    cardname: The name of the card.
    slots: 'main', 'side', or 'both' -- where the card has to appear in
           order to count."""
    def containing_func(decks):
        total = 0
        for d in decks:
            for s in d.slots:
                if s.cardname and s.cardname == cardname:
                    if slots in ('main', 'both') and s.main > 0:
                        total += 1
                    elif slots in ('side', 'both') and s.side > 0:
                        total += 1
        return total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '# {0} Decks{1}'.format(cardname, temp)
    return (containing_func, name, 'int')

def getPCopies(cardname, slots='both'):
    """Get the percentage of a particular card.
    cardname: The name of the card.
    slots: 'main', 'side', or 'both' -- which copies to count."""
    copies_func = getCardCopies(cardname, slots=slots)[0]
    def p_copies_func(decks):
        total = 0.0
        for d in decks:
            for s in d.slots:
                if slots in ('main', 'both'):
                    total += s.main
                if slots in ('side', 'both'):
                    total += s.side
        n_card = copies_func(decks)
        if total == 0 or n_card == 0:
            return float('NaN')
        return n_card/total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '% {0}{1}'.format(cardname, temp)
    return (p_copies_func, name, 'percent')

def getPContaining(cardname, slots='both'):
    """Get the percentage of decks containing a particular card.
    cardname: The name of the card.
    slots: 'main', 'side', or 'both' -- where the card has to appear in
           order to count."""
    containing_func = getNumContaining(cardname, slots=slots)[0]
    def p_containing_func(decks):
        total = 0.0
        for d in decks:
            if len(d.slots) > 0:
                total += 1.0
        n_decks = containing_func(decks)
        if total == 0 or n_decks == 0:
            return float('NaN')
        return containing_func(decks)/total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '% {0} Decks{1}'.format(cardname, temp)
    return (p_containing_func, name, 'percent')

def getDeckDiversity(func=simpson):
    """Get the diversity of archetypes.
    func: Diversity function to use -- accepts a list of counts, returns
        a number."""
    def diversity(decks):
        return func(getCounts(decks))
    return diversity

def getCardDiversity(func=simpson):
    """Get the diversity of card names.
    func: Diversity function to use -- accepts a list of counts, returns
        a number."""
    def diversity(decks):
        return func(getCardCounts(decks))
    return diversity

def getConditionalEntropy():
    """Get conditional entropy of card names given deck names."""
    def condEntropy(decks):
        if len(decks) == 0:
            return 0
        result = 0.0
        n = float(len(decks))
        archetypes, counts = getCountsByDeck(decks)
        for a in archetypes:
            if len(counts[a]) > 0:
                pA = len(archetypes[a]) / n
                hGivenA = entropy(counts[a])
                result += pA * hGivenA
        return result
    return condEntropy

def getJointEntropy(n=1):
    """Get joint entropy of N card names, assuming they must be chosen
    from the same deck (with replacement), and we select a deck at random
    from all decks whose cards we know."""
    def jointEntropy(initial_decks):
        # Exclude decks we don't have card data for:
        decks = [ d for d in initial_decks if len(d.slots) > 0 ]
        # This will be
        # 1) a function: card names -> joint probability; and
        # 2) a set of all card names
        jointP, allcards = jointProbability(decks)
        # To compute conditional entropy, we will need the joint entropy of
        # every combination of independently selected cards.
        jointH = 0
        sumP = 0
        for subset in product(allcards, repeat=n):
            p = jointP(subset)
            if p > 0:
                jointH -= p * log(p, 2)
            sumP += p
        return jointH
    return jointEntropy

def getCompoundEntropy(n=1):
    """Get conditional entropy of card name given a certain number of 
    other arbitrary number of other card names from the same deck."""
    # Use this rule:
    # H(X|Y,Z,...) = H(X, Y, Z, ...) - H(Y, Z, ...)
    jointGiven = getJointEntropy(n)
    jointAll = getJointEntropy(n+1)
    def condEntropy(decks):
        return jointAll(decks) - jointGiven(decks)
    return condEntropy

def getEntropyGivenDeck():
    """Get conditional entropy of card names given individual decks."""
    def condEntropy(initial_decks):
        # Exclude decks we don't have card data for:
        decks = [ d for d in initial_decks if len(d.slots) > 0 ]
        n = len(decks)
        if n == 0:
            return float('nan')
        result = 0.0
        for d in decks:
            hGivenD = entropy(getCardCounts([d]))
            if hGivenD:
                result += hGivenD
        result /= n
        return result
    return condEntropy

def getMutualInformation():
    """Get mutual information between card and archetype: I(C;A)."""
    # Note: I(C;A) = H(C) - H(C|A)
    #              = H(A) - H(A|C)
    ce = getConditionalEntropy()
    h = getCardDiversity(entropy)
    def mi(decks):
        if len(decks) == 0:
            return 0
        return h(decks) - ce(decks)
    return mi

def getSize(tournaments):
    """Get the combined size of all tournaments involved. (The same
    for every deck.)"""
    size = 0.0
    for t in tournaments:
        size += t.getNumPlayers()
    def size_func(decks):
        return size
    return (size_func, 'Field Size', 'int')

#-----------------------------------------------------------------------
# Statistics for a group of cards. Each function is a generator
# function, optionally taking in arguments to provide background
# information or refine queries. The result is a tuple containing:
# 1. a function which takes a card name and returns a statistic.
# 2. a displayable name of the statistic
# 3. a string describing the type of data: 'int', 'float', 'percent'
#-----------------------------------------------------------------------

def getCardCopies_card(decks, slots='both'):
    """Get the number of copies of a card among the decks.
    decks: The collection of decks.
    slots: 'main', 'side', or 'both' -- which copies to count."""
    def copies_func(cardname):
        total = 0
        for d in decks:
            for s in d.slots:
                if s.cardname and s.cardname == cardname:
                    if slots in ('main', 'both'):
                        total += s.main
                    if slots in ('side', 'both'):
                        total += s.side
        return total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '# of Copies{0}'.format(temp)
    return (copies_func, name, 'int')

def getNumContaining_card(decks, slots='both'):
    """Get the number of decks containing a particular card.
    decks: The collection of decks.
    slots: 'main', 'side', or 'both' -- where the card has to appear in
           order to count."""
    def containing_func(cardname):
        total = 0
        for d in decks:
            for s in d.slots:
                if s.cardname and s.cardname == cardname:
                    if slots in ('main', 'both') and s.main > 0:
                        total += 1
                    elif slots in ('side', 'both') and s.side > 0:
                        total += 1
        return total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '# of Decks{0}'.format(temp)
    return (containing_func, name, 'int')

def getPCopies_card(decks, slots='both'):
    """Get the percentage of the card.
    decks: The collection of decks.
    slots: 'main', 'side', or 'both' -- which copies to count."""
    copies_func = getCardCopies_card(decks, slots=slots)[0]
    total = 0.0
    for d in decks:
        for s in d.slots:
            if slots in ('main', 'both'):
                total += s.main
            if slots in ('side', 'both'):
                total += s.side
    def p_copies_func(cardname):
        n_card = copies_func(cardname)
        if total == 0 or n_card == 0:
            return float('NaN')
        return n_card/total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '% of Cards{0}'.format(temp)
    return (p_copies_func, name, 'percent')

def getPContaining_card(decks, slots='both'):
    """Get the percentage of the decks that contain a card.
    decks: The collection of decks.
    slots: 'main', 'side', or 'both' -- where the card has to appear in
           order to count."""
    containing_func = getNumContaining_card(decks, slots=slots)[0]
    total = 0.0
    for d in decks:
        if len(d.slots) > 0:
            total += 1.0
    def p_containing_func(cardname):
        n_decks = containing_func(cardname)
        if total == 0 or n_decks == 0:
            return float('NaN')
        return containing_func(cardname)/total
    temp = ''
    if slots == 'main':
        temp = ' (Main)'
    elif slots == 'side':
        temp = ' (Side)'
    name = '% of Decks{0}'.format(temp)
    return (p_containing_func, name, 'percent')

def _getStat_card(decks, withcard, function, base_name, return_type):
    name = f'{base_name} With'
    if not withcard:
        name = f'{base_name} Without'
    def get_stat(cardname):
        decksWith = []
        decksWithout = []
        for d in decks:
            includes = False
            for s in d.slots:
                if s.cardname == cardname:
                    includes = True
                    break
            if includes:
                decksWith.append(d)
            else:
                decksWithout.append(d)
        if withcard:
            return function(decksWith)
        else:
            return function(decksWithout)
    return (get_stat, name, return_type)

def getMWP_card(decks, withcard=True):
    """Get the win percentage of decks containing or not containing a
    particular card."""
    return _getStat_card(decks, withcard, getMWP()[0], 'Win %', 'percent')

def getRecord_card(decks, withcard=True):
    """Get the total record of decks containing or not containing a
    particular card."""
    def get_record_str(decks):
        w, l, d = getRecord()[0](decks)
        return f'{w}-{l}-{d}'
    return _getStat_card(decks, withcard, get_record_str, 'Record', 'string')

def _includes_card(deck, cardname):
    for s in deck.slots:
        if s.cardname == cardname:
            return True
    return False

def _getStat_versus(decks, name, function, return_type):
    def get_stat(cardname):
        matches = []
        for d in decks:
            if _includes_card(d, cardname):
                matches.extend([m for m in d.getMatches() if not _includes_card(m.deck2, cardname)])
        return function(matches)
    return (get_stat, name, return_type)

def getMWP_versus(decks):
    """Get the win percentage of decks containing a card when matched against
    decks not containing the same card."""
    def mwp_versus(matches):
        if matches:
            return float(mwp(matches))
        else:
            return float('NaN')
    return _getStat_versus(decks, 'Win % vs. Without', mwp_versus, 'percent')

def getRecord_versus(decks):
    """Get the record percentage of decks containing a card when matched against
    decks not containing the same card."""
    def record_versus(matches):
        if matches:
            w, l, d = record(matches)
            return f'{w}-{l}-{d}'
        else:
            return '0-0-0'
    return _getStat_versus(decks, 'Record vs. Without', record_versus, 'string')
