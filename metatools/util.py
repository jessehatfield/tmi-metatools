"""Utility functions"""

from math import log
from operator import attrgetter
from datetime import timedelta, date, datetime
from fractions import *
from decimal import *

drawMult = Decimal(.5)  #How much a draw contributes to games/matches won
drawCount = 1  #How much a draw contributes to total games/matches

def getCounts(decks):
    types = {}
    for d in decks:
        decktype = d.archetype
        types[decktype] = types.get(decktype, 0) + 1
    return types.values()

# Match statistics

def record(matches):
    """Get the (win, loss, draw) record from a list of matches."""
    win = sum([ m.win for m in matches])
    loss = sum([ m.loss for m in matches])
    draw = sum([ m.draw for m in matches])
    return (win, loss, draw)

def mwp(matches, datatype=Decimal):
    """Get a match-win percentage from a list of matches."""
    win, loss, draw = record(matches)
    return mwp_record(win, loss, draw, datatype)

def mwp_record(win, loss, draw, datatype=Decimal):
    win = int(win)
    loss = int(loss)
    draw = int(draw)
    total = win+loss+(draw*drawCount)
    if total > 0:
        return datatype(win + (draw*drawMult)) / total
    else:
        return None

# Diversity measures

def entropy(values):
    """Information entropy.
    H = - sum [ p * log2(p) ]
    values is a list of numbers, each representing the number of
    items with a particular value."""
    if len(values) == 0:
        return float('NaN')
    total = float(sum(values))
    if total == 0:
        return 0.0
    p = [ value/total for value in values ]
    H = 0.0
    for i in range(len(p)):
        if p[i] > 0:
            H -= p[i] * log(p[i], 2)
    return H

def igr(values):
    """Information gain ratio"""
    if len(values) == 0:
        return float('NaN')
    total = float(sum(values))
    if total == 0:
        return None
    H = entropy(values)
    return H / log(total, 2)

def simpson(values):
    """Simpson's diversity index.
    D = 1 - sum [ n/N * (n-1)/(N-1) ]
      = 1 - sum [ (n(n-1)) / (N(N-1)) ]
      = 1 - ( sum [ n(n-1) ] / (N(N-1)) )
    , or the chance that two randomly
    chosen items will have different values.
    values is a list of numbers, each reperesenting the number of items
    with a particular value"""
    if len(values) == 0:
        return float('NaN')
    total = float(sum(values))
    if total <= 1:
        return 0.0
    denominator = total * (total-1)
    numerator = 0.0
    for value in values:
        numerator += value * (value-1.0)
    return 1.0 - (numerator/denominator)

def simpsonR(values):
    """Simpson's diversity index, with replacement.
    return simpson(values)
    D = 1 - sum [ n/N * n/N ]
      = 1 - sum [ (n*n)/(N*N) ]
      = 1 - sum [ n*n ] / N*N
    , or the chance that two items randomly chosen with replacement
    will have different values.
    values is a list of numbers, each reperesenting the number of items
    with a particular value"""
    if len(values) == 0:
        return float('NaN')
    total = float(sum(values))
    if total <= 0:
        return 0.0
    denominator = total * total
    numerator = 0.0
    for value in values:
        numerator += value * value
    return 1.0 - (numerator/denominator)

def infogainMatches(matches):
    """Calculate information gain (decrease in entropy), with respect to
    what archetype a deck is, upon learning the result of a match."""
    if len(matches) == 0:
        return float('NaN')
    before = [ m.deck1 for m in matches ]
    after = [ m.deck1 for m in matches if m.win == 1 ]
    gain = entropy(getCounts(before)) - entropy(getCounts(after))
    return gain

# Split a list of Tournaments into multiple lists

def groupByWeek(tournaments, begin=None, end=None):
    """Seperate a list of Tournaments by week. Returns a list of lists
    of tournaments: one list for each week, from the week containing the
    first Tournament to the week containing the last. If there are no
    Tournaments for a given week, there will be an empty list."""
    tournies = sorted(tournaments, key=attrgetter("date"))
    # Start with the week of the first tournament, unless a begin date
    # was specified.
    year, week_n, day = tournies[0].date.isocalendar()
    if begin:
        begin = datetime.strptime(begin, '%Y-%m-%d')
        year, week_n, day = begin.isocalendar()
    if end:
        end = strptime('%Y-%m-%d')
    else:
        end = datetime.today()
    end_week = datetime.strptime('{0}-{1}-6'.format(year, week_n), '%Y-%W-%w').date()
    # Start with one sublist, for the first week.
    result = [[]]
    weeks = [ end_week - timedelta(6) ]
    for t in tournies:
        # Add sublists for successive weeks, until we catch up to t.date.
        while t.date > end_week:
            result.append([])
            end_week += timedelta(7)
            weeks.append(end_week - timedelta(6))
        # Then add t to the latest list (current week).
        result[-1].append(t)
    # Add empty lists until the end date.
    while end_week < end.date():
        result.append([])
        end_week += timedelta(7)
        weeks.append(end_week - timedelta(6))
    return result, weeks

def groupByMonth(tournaments, begin=None, end=None):
    """Seperate a list of Tournaments by month. Returns a list of lists
    of tournaments: one list for each month, from the month containing the
    first Tournament to the month containing the last. If there are no
    Tournaments for a given month, there will be an empty list."""
    tournies = sorted(tournaments, key=attrgetter("date"))
    # Start with the month of the start date, or the month of the first
    # tournament, if no start date is given.
    first = tournies[0]
    month, year = first.date.month, first.date.year
    if begin:
        begin = datetime.strptime(begin, '%Y-%m-%d')
        month, year = begin.month, begin.year
    if end:
        end = strptime('%Y-%m-%d')
    else:
        end = datetime.today()
    # Start with one sublist, for the first month.
    result = [[]]
    months = [date(year, month, 1)]
    for t in tournies:
        # Add sublists for successive weeks, until we catch up to t.date.
        while t.date.month > month or t.date.year > year:
            result.append([])
            month += 1
            if month > 12:
                month = 1
                year += 1
            months.append(date(year, month, 1))
        # Then add t to the latest list (current month).
        result[-1].append(t)
    # Add empty lists until the end.
    while month < end.month or year < end.year:
        result.append([])
        month += 1
        if month > 12:
            month = 1
            year += 1
        months.append(date(year, month, 1))
    return result, months

def groupByWindow(tournaments, window):
    """Move over a list of Tournaments by a sliding window. Returns a list
    of lists of tournaments: one list for each tournament starting with the nth,
    where each list contains the corresponding tournament and the previous (n-1)
    tournaments. Each tournament will appear in between one and n lists. There
    will be t-n+1 lists, where t is the number of tournaments.
    Returns a list of lists."""
    tournies = sorted(tournaments, key=attrgetter("date"))
    ngroups = len(tournies) - window + 1
    result = []
    for i in range(ngroups):
        result.append(tournies[i:window+i])
    return result

def jointProbability(decks):
    """Generate a function that computes the joint probability of observing
    all of the cards named, computed over the list of decks, and a set of card
    names that exist in those decks. Assume the following procedure: select a
    deck at random (uniformly), then select a random card from it."""
    # First, we need to map cards to decks, and get the number of cards in
    # each deck, so we can compute p(Card|Deck). These maps will be reused each
    # time.
    frequency = {}
    totals = {}
    allcards = set()
    for d in decks:
        frequency[d] = {}
        total = 0
        for s in d.slots:
            if s.cardname and s.main > 0:
                frequency[d][s.cardname] = s.main
                total += s.main
                allcards.add(s.cardname)
        totals[d] = total
    # With that data stored, we can define the function:
    def getJointProbability(cardnames):
        totalP = 0.0
        # Sum P(deck) + P(cards|deck) for each deck
        for deck in decks:
            if totals[deck] > 0:
                p = 1.0
                for cn in cardnames:
                    p *= frequency[deck].get(cn, 0) / float(totals[deck])
                totalP += p
        # Note that P(deck) = 1/|decks| for each decks
        return totalP / len(decks)
    return getJointProbability, allcards
