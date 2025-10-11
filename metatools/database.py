from sqlalchemy import schema, types, orm
from sqlalchemy.engine import create_engine
from sqlalchemy.sql import select, func
from sqlalchemy.sql.expression import and_, or_, asc, text

from metatools.config import config
from metatools.deck import Deck, Card, Slot
from metatools.match import Match
from metatools.tournament import Tournament

engine = create_engine(config['database']['connection'], echo=False)
param = config['database']['param']
#print(f"Connecting to DB: {config['database']['connection']}")
metadata = schema.MetaData()
metadata.bind = engine
sm = orm.sessionmaker(bind=engine, autoflush=False, autocommit=False,
        expire_on_commit=True)
session = orm.scoped_session(sm)

cards = schema.Table('Card', metadata,
        schema.Column('CARD_NAME', types.String, primary_key=True),
        schema.Column('COST', types.String),
        schema.Column('TEXT', types.String),
        schema.Column('EDITIONS', types.String),
        schema.Column('POWER', types.String),
        schema.Column('TOUGHNESS', types.String),
        schema.Column('LOYALTY', types.String),
        schema.Column('HANDCHANGE', types.String),
        schema.Column('LIFECHANGE', types.Integer))

tournamentTable = schema.Table('Tournament', metadata,
        schema.Column('T_ID', types.Integer, primary_key=True),
        schema.Column('T_NAME', types.String),
        schema.Column('PLAYERS', types.Integer),
        schema.Column('CITY', types.String),
        schema.Column('STATE', types.String),
        schema.Column('COUNTRY', types.String),
        schema.Column('T_DATE', types.Date),
        schema.Column('FORMAT', types.String),
        schema.Column('SOURCE', types.String))

deckTable = schema.Table('Deck', metadata,
        schema.Column('DECK_ID', types.Integer, primary_key=True),
        schema.Column('T_ID', types.Integer,
            schema.ForeignKey('Tournament.T_ID')),
        schema.Column('PLAYER_NAME', types.String),
        schema.Column('DECK_NAME', types.String),
        schema.Column('PLACE', types.Integer),
        schema.Column('SPLIT', types.String),
        schema.Column('ORIGINAL', types.String),
        schema.Column('QUALIFIER', types.String),
        schema.Column('RECORD', types.String),
        schema.Column('POINTS', types.Integer))

contents = schema.Table('Contents', metadata,
        schema.Column('CARD_NAME', types.String,
            schema.ForeignKey('Card.CARD_NAME')),
        schema.Column('DECK_ID', types.Integer,
            schema.ForeignKey('Deck.DECK_ID')),
        schema.Column('NUM_MAIN', types.Integer),
        schema.Column('NUM_SIDE', types.Integer))

matches = schema.Table('MatchesSCG', metadata,
        schema.Column('MATCH_ID', types.Integer, primary_key=True),
        schema.Column('T_ID', types.Integer,
            schema.ForeignKey('Tournament.T_ID')),
        schema.Column('DECK_ID', types.Integer,
            schema.ForeignKey('Deck.DECK_ID')),
        schema.Column('DECK_2', types.Integer,
            schema.ForeignKey('Deck.DECK_ID')),
        schema.Column('DECK_NAME', types.String),
        schema.Column('DECK_NAME_2', types.String),
        schema.Column('QUALIFIER', types.String),
        schema.Column('QUALIFIER_2', types.String),
        schema.Column('WIN', types.Integer),
        schema.Column('LOSS', types.Integer),
        schema.Column('DRAW', types.Integer),
        schema.Column('MATCH_WIN', types.Integer),
        schema.Column('MATCH_LOSS', types.Integer),
        schema.Column('MATCH_DRAW', types.Integer),
        schema.Column('ROUND', types.String),
        schema.Column('TABLE_NUM', types.Integer))

rawMatches = schema.Table('Matches', metadata,
        schema.Column('MATCH_ID', types.Integer, primary_key=True),
        schema.Column('T_ID', types.Integer,
            schema.ForeignKey('Tournament.T_ID')),
        schema.Column('DECK_1', types.Integer,
            schema.ForeignKey('Deck.DECK_ID')),
        schema.Column('DECK_2', types.Integer,
            schema.ForeignKey('Deck.DECK_ID')),
        schema.Column('WIN', types.Integer),
        schema.Column('LOSS', types.Integer),
        schema.Column('DRAW', types.Integer),
        schema.Column('ROUND', types.String),
        schema.Column('TABLE_NUM', types.Integer))

class DBDeck(Deck):
    def getMatches(self):
        if len(self.matches) > 0:
            return self.matches
        else:
            return self.rmatches + [ m.reverse() for m in self.rmatchesReverse ]
class DBTournament(Tournament):
    pass
class DBMatch(Match):
    pass
class RawMatch(Match):
    pass
class DBCard(object):
    pass

orm.mapper(DBCard, cards, properties = {
    'name': cards.c.CARD_NAME,
    'cost': cards.c.COST,
    'text': cards.c.TEXT,
    'editions': cards.c.EDITIONS,
    'power': cards.c.POWER,
    'toughness': cards.c.TOUGHNESS,
    'loyalty': cards.c.LOYALTY,
    'handchange': cards.c.HANDCHANGE,
    'lifechange': cards.c.LIFECHANGE
})
orm.mapper(DBTournament, tournamentTable, properties= {
    'decks': orm.relationship(DBDeck, backref='tournament'),
    'id': tournamentTable.c.T_ID,
    'name': tournamentTable.c.T_NAME,
    'numPlayers': tournamentTable.c.PLAYERS,
    'city': tournamentTable.c.CITY,
    'state': tournamentTable.c.STATE,
    'country': tournamentTable.c.COUNTRY,
    'date': tournamentTable.c.T_DATE,
    'format': tournamentTable.c.FORMAT,
    'source': tournamentTable.c.SOURCE
})
orm.mapper(DBDeck, deckTable, properties = {
    'slots': orm.relation(Slot, backref='deck'),
    'id': deckTable.c.DECK_ID,
    'player': deckTable.c.PLAYER_NAME,
    'place': deckTable.c.PLACE,
    'archetype': deckTable.c.DECK_NAME,
    'subarchetype': deckTable.c.QUALIFIER,
    'original': deckTable.c.ORIGINAL,
    'record': deckTable.c.RECORD,
    'points': deckTable.c.POINTS,
    'split' : deckTable.c.SPLIT
})
orm.mapper(Slot, contents, primary_key = [ contents.c.DECK_ID,
    contents.c.CARD_NAME ], properties = {
    'card': orm.relation(DBCard),
    'cardname': contents.c.CARD_NAME,
    'main': contents.c.NUM_MAIN,
    'side': contents.c.NUM_SIDE
})
orm.mapper(DBMatch, matches, properties={
    'deck1': orm.relation(DBDeck, backref='matches',
        primaryjoin=matches.c.DECK_ID==deckTable.c.DECK_ID),
    'deck2': orm.relation(DBDeck, backref='matchesReverse',
        primaryjoin=matches.c.DECK_2==deckTable.c.DECK_ID),
    'tournament': orm.relation(DBTournament, backref='matches'),
    'deck_name': matches.c.DECK_NAME,
    'deck_name_2': matches.c.DECK_NAME_2,
    'sub_1': matches.c.QUALIFIER,
    'sub_2': matches.c.QUALIFIER_2,
    'id': matches.c.MATCH_ID,
    'game_win': matches.c.WIN,
    'game_loss': matches.c.LOSS,
    'game_draw': matches.c.DRAW,
    'match_win': matches.c.MATCH_WIN,
    'match_loss': matches.c.MATCH_LOSS,
    'match_draw': matches.c.MATCH_DRAW,
    'round': matches.c.ROUND,
    'table': matches.c.TABLE_NUM
})
orm.mapper(RawMatch, rawMatches, properties={
    'deck1': orm.relation(DBDeck, backref='rmatches',
        primaryjoin=rawMatches.c.DECK_1==deckTable.c.DECK_ID),
    'deck2': orm.relation(DBDeck, backref='rmatchesReverse',
        primaryjoin=rawMatches.c.DECK_2==deckTable.c.DECK_ID),
    'tournament': orm.relation(DBTournament, backref='rmatches'),
    'id': rawMatches.c.MATCH_ID,
    'game_win': rawMatches.c.WIN,
    'game_loss': rawMatches.c.LOSS,
    'game_draw': rawMatches.c.DRAW,
    'round': rawMatches.c.ROUND,
    'table': rawMatches.c.TABLE_NUM
})

def tournamentQuery(tournaments=[], tids=[], format=None, name=None, source=None,
        min_date=None, max_date=None, min_players=None, max_players=None):
    """Build a query for tournaments.
    
    All options which are specified will be required to be true (unless
    tournaments or tids is specified, each of which overrides the
    others), e.g. return a conjunction of the tournaments defined by the
    options. To build a disjunction, call tournamentQuery multiple times
    and use query1.union(query2).
    
    tournaments: Specify Tournamen objects manually. Overrides all other options.
    tids: Specify tournament ids manually. Overrides all other options.
    format: Only return tournaments of a certain format.
    name: Only return tournaments matching a certain name.
    source: Only return tournaments from a certain source.
    min_date: Earliest possible date.
    max_date: Latest possible date.
    min_players: Smallest possible tournament.
    max_players: Largest possible tournament."""
    if tournaments:
        return tournamentQuery(tids=[t.id for t in tournaments])
    query = session.query(DBTournament).order_by(asc(DBTournament.date))
    if tids:
        return query.filter(DBTournament.id.in_(tids))
    if format:
        query = query.filter(DBTournament.format == format)
    if name:
        query = query.filter(DBTournament.name.like(name))
    if source:
        query = query.filter(DBTournament.source == source)
    if min_date:
        query = query.filter(DBTournament.date >= min_date)
    if max_date:
        query = query.filter(DBTournament.date <= max_date)
    if min_players:
        query = query.filter(DBTournament.numPlayers >= min_players)
    if max_players:
        query = query.filter(DBTournament.numPlayers <= max_players)
    return query

def deckQuery(decks=None, dids=[], tournaments=[], tquery=None, tids=[], players=[],
        min_place=None, max_place=None, archetypes=[], subarchetypes=[], deckTypes=[],
        exclude=[]):
    """Build a query for decks.
    
    All options which are specified will be required to be true (unless
    decks or dids is specified, each of which overrides the others),
    e.g. return a conjunction of the decks defined by the options. To
    build a disjunction, call deckQuery multiple times and use
    query1.union(query2). 

    decks: Specify DBDeck objects manually. Overrides all other options.
    dids: Specify deck IDs manually. Overrides all other options.
    tournaments: A list of DBTournament objects to select decks from.
    tquery: A query for tournaments to select decks from.
    tids: IDs of tournaments to select decks from.
    players: Player names.
    min_place: Minimum place in the tournament.
    max_place: Maximum place in the tournament.
    archetypes: Only return decks with one of these archetypes.
    subarchetypes: Only return decks with one of these subarchetypes.
    deckTypes: List of (archetype, subarchetype) tuples. Only return
        decks with matching types. (More specific than archetypes and
        subarchetypes, since it requires that each pair go together.)
    exclude: Don't include anything with an archetype in this list.
    """
    if decks:
        return deckQuery(dids=[d.id for d in decks])
    query = session.query(DBDeck)
    if dids:
        return query.filter(DBDeck.id.in_(dids))
    if tournaments:
        t_ids = [ t.id for t in tournaments ]
        query = query.filter(deckTable.c.T_ID.in_(t_ids))
    if tids:
        query = query.filter(deckTable.c.T_ID.in_(tids))
    if tquery:
        query = query.join(tquery.subquery())
    if players:
        p2 = [ func.upper(p) for p in players ]
        query = query.filter(func.upper(DBDeck.player).in_(p2))
    if min_place:
        query = query.filter(DBDeck.place >= min_place)
    if max_place:
        query = query.filter(DBDeck.place <= max_place)
    if archetypes:
        query = query.filter(DBDeck.archetype.in_(archetypes))
    if subarchetypes:
        query = query.filter(DBDeck.subarchetype.in_(subarchetypes))
    if deckTypes:
        clauses = []
        for main, sub in deckTypes:
            clauses.append(and_(DBDeck.archetype == main,
                DBDeck.subarchetype == sub))
        query = query.filter(or_(*clauses))
    if exclude:
        query = query.filter(not_(DBDeck.archetypes.in_(exclude)))
    return query

def slotQuery(decks=None, dids=[], dquery=None):
    """Build a query for slots, returning all slots for a list of decks,
    specified in three ways (provide only one argument):
    decks: A list of Deck objects.
    dids: A list of Deck IDs.
    dquery: A query which returns Decks."""
    query = session.query(Slot)
    if dquery:
        return query.join(dquery.subquery())
    elif decks:
        dids = [ deck.id for deck in decks ]
    return query.filter(DBDeck.id.in_(dids))

def matchQuery(tquery=None, d1query=None, d2query=None,
        tournaments=None, decks1=None, decks2=None):
    """Build a query for matches.
    
    tquery: Only get matches from tournaments this query finds.
    d1query: Only get matches where this query finds deck 1.
    d2query: Only get matches where this query finds deck 2.
    tournaments: Only get matches from these tournaments.
    decks1: Only get matches whose first deck is in this list.
    decks2: Only get matches whose second deck is in this list.
    """
    query = session.query(RawMatch)
    if tournaments:
        tquery = tournamentQuery(tournaments=tournaments)
    if tquery:
        query = query.join(tquery.subquery())
    if d1query:
        query = query.join((d1query.subquery(), RawMatch.deck1))
    if d2query:
        query = query.join((d2query.subquery(), RawMatch.deck2))
    if decks1:
        d1ids = [ d.id for d in decks1 ]
        query = query.filter(rawMatches.c.DECK_1.in_(d1ids))
    if decks2:
        d2ids = [ d.id for d in decks2 ]
        query = query.filter(rawMatches.c.DECK_2.in_(d2ids))
    return query

def matchQueryGrouped(tquery=None, d1query=None, d2query=None,
        tournaments=None, decks1=None, decks2=None, aggregate=[]):
    """Build a query for matches, grouped by archetype.

    tquery: Only get matches from tournaments this query finds.
    d1query: Only get matches where this query finds deck 1.
    d2query: Only get matches where this query finds deck 2.
    tournaments: Only get matches from these tournaments.
    decks1: Only get matches whose first deck is in this list.
    decks2: Only get matches whose second deck is in this list.
    aggregate: Collection of bools. Instead of returning matches, return match
        totals grouped by any combination of  archetype and subarchetype:
        (deck1, sub1, deck2, sub2), e.g. (True,False,True,False) to get
        counts broken down by archetype of both decks, but not by subarchetype.
    """
    query = session.query(DBMatch)
    if tournaments:
        tquery = tournamentQuery(tournaments=tournaments)
    if tquery:
        query = query.join(tquery.subquery())
    if d1query:
        query = query.join((d1query.subquery(), DBMatch.deck1))
    if d2query:
        query = query.join((d2query.subquery(), DBMatch.deck2))
    if decks1:
        d1ids = [ d.id for d in decks1 ]
        query = query.filter(matches.c.DECK_ID.in_(d1ids))
    if decks2:
        d2ids = [ d.id for d in decks2 ]
        query = query.filter(matches.c.DECK_2.in_(d2ids))
    if aggregate:
        options = ( DBMatch.deck_name, DBMatch.sub_1, DBMatch.deck_name_2,
            DBMatch.sub_2 )
        groupby = []
        for i in range(len(options)):
            if aggregate[i]:
              groupby.append(options[i])
        stats = [ func.sum(DBMatch.match_win), func.sum(DBMatch.match_loss),
            func.sum(DBMatch.match_draw) ]
        columns = groupby + stats
        query = query.from_self(*columns).group_by(*groupby)
    return query

def metaQuery(tquery=None, dquery=None, tournaments=None, decks=None,
        groupBySub=False):
    """Query for deck types. Return a list of types and counts.
    
    tquery: Only get decks from tournaments this query finds.
    dquery: Only get decks that are found by a particular query.
    tournaments: Only get decks from this list of tournaments.
    decks: Only get decks from this list of decks.
    groupBySub: Group by subarchetype (default: False).
    """
    query = session.query(DBDeck)
    if dquery:
        query = dquery
    if decks:
        query = query.union(deckQuery(decks=decks))
    if tquery:
        query = query.join(tquery.subquery())
    if tournaments:
        tids = [ t.id for t in tournaments ]
        query = query.filter(deckTable.c.T_ID.in_(tids))
    if groupBySub:
        query = query.from_self(DBDeck.archetype, DBDeck.subarchetype,
                func.count('*'))
        query = query.group_by(DBDeck.archetype, DBDeck.subarchetype)
    else:
        query = query.from_self(DBDeck.archetype, func.count('*'))
        query = query.group_by(DBDeck.archetype)
    return query

def queryResults(func):
    """Wrapper for a function that returns a query: the new
    function executes the query and returns the list of results."""
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs).all()
    wrapped.__doc__ = \
        """Wrapper for {0}, which takes the same arguments but returns
    actual objects rather than the underlying database query.

    Docstring for {0}:

    {1}""".format(func.__name__, func.__doc__)
    wrapped.__name__ = "{0}_wrapper".format(func.__name__)
    return wrapped

#getTournaments = queryResults(tournamentQuery)
#getSlots = queryResults(slotQuery)
#getMatches = queryResults(matchQuery)
#getDecks = queryResults(deckQuery)
#getMeta = queryResults(metaQuery)

def getTournaments(*args, **kwargs):
    return tournamentQuery(*args, **kwargs).all()
def getSlots(*args, **kwargs):
    return slotQuery(*args, **kwargs).all()
def getMatches(tquery=None, d1query=None, d2query=None,
        tournaments=None, decks1=None, decks2=None,
        oneway=True):
    forward = matchQuery(tquery, d1query, d2query, tournaments, decks1, decks2).all()
    if oneway:
        backward = []
    else:
        backward = matchQuery(tquery, d2query, d1query, tournaments, decks2, decks1).all()
    return set(forward + [ m.reverse() for m in backward ])
def getMatchesGrouped(*args, **kwargs):
    return matchQueryGrouped(*args, **kwargs).all()
def getDecks(*args, **kwargs):
    return deckQuery(*args, **kwargs).all()
def getMeta(*args, **kwargs):
    return metaQuery(*args, **kwargs).all()

def getCard(name):
    """Instantiate a new Card given its name."""
    query = session.query(DBCard).filter(DBCard.name == name)
    try:
        dbcard = query.one()
        return Card(name, dbcard.cost, dbcard.text, dbcard.power,
                dbcard.toughness, dbcard.loyalty)
    except:
        return Card(name)

def loadDeck(did):
    """Instantiate and return a Deck by loading it from the database via SQLAlchemy.
    did: Deck ID
    """
    return deckQuery(dids=[did]).one()

def loadTournament(tid):
    """Instantiate and return a DBTournament by loading it from the database via
    SQLAlchemy."""
    return tournamentQuery(tids=[tid]).one()

def loadMeta(*args):
    """Load a metagame for one or more tournaments."""
    tids = [ t.id for t in args ]
    return metaQuery(tquery=tournamentQuery(tids=tids))

def sql(string, *args):
    """ Execute raw SQL. Parameters are given by <param>."""
    return session.connection().execute(string, *args)

def inequals(items):
    """Generate a SQL condition of the form 'IN (a, b, c)' if there are
    multiple elements; '= x' if there is one; empty string if zero."""
    condition = ','.join([param] * len(items))
    if len(items) == 0:
        return ""
    elif len(items) == 1:
        return "= " + condition
    else:
        return "IN (" + condition + ")"

def getMatchTotals(tids, decks1, decks2, fromSub=False):
    if fromSub:
        result = sql("""select DECK_NAME, QUALIFIER, DECK_NAME_2,
            SUM(MATCH_WIN), SUM(MATCH_LOSS), SUM(MATCH_DRAW) from
            MatchesSCG where T_ID """ + inequals(tids)
            + """ and DECK_NAME """ + inequals(decks1)
            + """ and DECK_NAME_2 """ + inequals(decks2)
            + """ group by DECK_NAME, QUALIFIER, DECK_NAME_2""",
            *(tids + decks1 + decks2))
    else:
        result = sql("""select DECK_NAME, DECK_NAME_2, SUM(MATCH_WIN),
            SUM(MATCH_LOSS), SUM(MATCH_DRAW) from MatchesSCG where T_ID """
            + inequals(tids) + """ and DECK_NAME """
            + inequals(decks1) + """ and DECK_NAME_2 """ + inequals(decks2)
            + """ group by DECK_NAME, DECK_NAME_2""",
            *(tids + decks1 + decks2))
    return result

def getCardCounts(decks, side=False):
    dids = [ d.id for d in decks ]
    condition = inequals(dids)
    if condition:
        rp = sql("""SELECT CARD_NAME,SUM(NUM_MAIN) as N FROM Contents WHERE
                DECK_ID """ + condition + """ GROUP BY CARD_NAME HAVING N>0""",
                *dids)
        counts = [ float(row[1]) for row in rp ]
        return counts
    else:
        return []

def getCountsByDeck(decks, side=False):
    dids = [ d.id for d in decks ]
    archetypes = {}
    for d in decks:
        name = d.archetype
        if name not in archetypes:
            archetypes[name] = []
        archetypes[name].append(d)
    counts = {}
    for a in archetypes:
        counts[a] = getCardCounts(archetypes[a], side)
    return archetypes, counts


if __name__ == "__main__":
    tq = tournamentQuery(tids=[3896,4052])
    t = tq.all()
    dq = deckQuery(archetypes=['Reanimator', 'NO RUG'], tquery=tq)
    d = dq.all()
    td = [ x for x in t[1].decks if x.place <= 16 ]
    mq = matchQuery(decks1=d, tournaments=t)
    q = matchQueryGrouped(decks1=d, tournaments=t, aggregate=(True, False, True, False))
