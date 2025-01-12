#!/usr/bin/env python

import sys
import argparse
from operator import itemgetter
import pickle

from metatools.config import config, defaultEnd
from metatools.table import Table,Field
from metatools.dbmeta import DBMeta
from metatools.reports import *
from metatools.skill import *
from metatools.insert import *

# Wrapper functions to access the reports in reports.py via the command line.
# Each of these wrapper functions takes the following arguments:
# args: dictionary of command-line arguments
# decktypes: list of strings representing archetype names
# groups: dictionary where each key is a name and each value is a list
#         of decks to group together
# recentMeta: recent metagame, used for matchup data
# historicalMeta: historical metagame, used for matchup data
# tournies: a list of Tournaments for the relevant time period

def getListWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """Generate a table that just lists the selected decks. 
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return getList(decktypes, groups)

def getBreakdownWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    tournaments = [ tournies[-i] for i in args.get('tournaments', []) ]
    if 'all' in args and args['all']:
        tournaments = tournies
    return getBreakdown(tournaments, historicalMeta,
            args.get('outputs', ['field', 'n', 'avgplace', 'win', 'loss',
                'draw', 'mwp', 'mwpLowerBound', 'mwpUpperBound', 'ev']),
            args.get('top', []), args.get('percentTop', []),
            args.get('penetration', []), args.get('conversion', []),
            decktypes, groups, players, args.get('cards', []),
            args.get('sub', False))

def getTrendWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    groupBy = None
    if 'group_by_month' in args and args['group_by_month']:
        groupBy = "month"
    elif 'group_by_week' in args and args['group_by_week']:
        groupBy = "week"
    for required in ['outputs', 'card_count', 'containing', 'p_card',
            'p_containing', 'top', 'percentTop', 'penetration', 'conversion']:
        if required not in args:
            args[required] = []
    tstats = getTourneyStats(args['outputs'], args['card_count'],
            args['containing'], args['p_card'], args['p_containing'])
    # If skip, only include tournaments where we know some cards:
    if args['skip']:
        tournies = [ t for t in tournies if getCardCounts(t.decks) ]
    return getTrend(decktypes, tournies, historicalMeta,
            args['outputs'], args['top'], args['percentTop'],
            penetration=args['penetration'], conversion=args['conversion'],
            players=players, groupBy=groupBy, begin=args['begin'],
            end=args['end'], tstats=tstats, groups=groups,
            onlyTopX=args['restrict_top'], window=args['window'])

def getDiversityWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return getDiversity(tournies, args['function'], args['top'],
            args['infogain'],
            args['infogainmatch'], args['summary'])

def getCardInfoWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """Get information about the actual contents of the decks.
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return getCardInfo(recentMeta.tournaments, args['outputs'], args.get('top', None),
            args.get('plus_top', []), cards=args.get('cards', []))

def getMatchupsWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    conf: Confidence level -- if given, generate confidence intervals
    """
    label = args.get('label', None) or ','.join(args['deck'])
    alternate = historicalMeta
    if 'no_overall' in args and args['no_overall']:
        alternate = None
    return getMatchups(args['deck'], label, recentMeta, alternate,
            args.get('overall_title', 'Overall'), decktypes, groups,
            players, args.get('nmatches', False), args.get('sub', False),
            conf=args.get('conf', None))

def explainWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return explain(args['deck'], recentMeta, historicalMeta, args['order'])

def skillWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return skillDeck(decktypes, groups, historicalMeta, tournies,
        args['min_other'], args['min_deck'], args['min_all'], args['other'])

def getGridWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    alternate = historicalMeta
    if 'no_overall' in args and args['no_overall']:
        alternate = None
    return getAllMatchups(decktypes, recentMeta, alternate,
            args.get('overall_title', 'Overall'), groups,
            players, args.get('sub', False))

def getHistoryWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    """
    args: dictionary of command-line arguments
    decktypes: list of strings representing archetype names
    groups: dictionary where each key is a name and each value is a list
            of decks to group together (ignored in this case)
    recentMeta: recent metagame, used for matchup data
    historicalMeta: historical metagame, used for matchup data
    tournies: a list of Tournaments for the relevant time period
    players: Player names -- restrict the field to these players
    """
    return getHistory(historicalMeta.tournaments, historicalMeta,
            args.get('outputs', ['avgplace', 'win', 'loss', 'draw', 'mwp',
                'ev']),
            args.get('top', []), args.get('percentTop', []),
            args.get('penetration', []),
            args.get('conversion', []),
            decktypes,
            players,
            args.get('top_only', 0))

def insertWrapper(args, decktypes, groups, recentMeta, historicalMeta, tournies, players):
    return insertTournament(
            args['deckfile'],
            args['matchfile'],
            args['name'],
            args['format'],
            args['year'],
            args['month'],
            args['day'],
            args['city'],
            args['state'],
            args['country'],
            args['source'],
            args['game_counts'],
            args['dry_run'])


#------------------

def buildMeta(
        begin=config['defaults']['begin-date'],
        end=defaultEnd(),
        tournies=1,
        appearances=1,
        player_file=None,
        format='Legacy',
        source=None,
        exclude_unselected=False,
        exclude=[],
        include=[],
        include_all=False,
        field=0.05,
        fieldtotal=0,
        group=[],
        min_other=0,
        min_deck=0,
        min_all=0,
        other=False,
        **kwargs):
    """Take in various parameters to build a metagame history. Produces several
    structures which can be fed into the report functions or the functions
    above. Parameter names are the same as full argument names for tmi script."""

    # Fill in parameters:
    kwargs['begin'] = begin
    kwargs['end'] = end
    kwargs['tournies'] = tournies
    kwargs['appearances'] = appearances
    kwargs['player_file'] = player_file
    kwargs['format'] = format
    kwargs['source'] = source
    kwargs['exclude_unselected'] = exclude_unselected
    kwargs['exclude'] = exclude
    kwargs['include'] = include
    kwargs['include_all'] = include_all
    kwargs['field'] = field
    kwargs['fieldtotal'] = fieldtotal
    kwargs['group'] = group
    kwargs['min_other'] = min_other
    kwargs['min_deck'] = min_deck
    kwargs['min_all'] = min_all
    kwargs['other'] = other

    # First, determine whether we'll be restricting the field to a subset of
    # players.
    players = []
    if player_file:
        players = [ line.strip() for line in player_file.readlines() ]

    # Next, figure out which tournaments we'll be using for matchups and
    # other background information.
    tournaments = getTournaments(format=format, source=source,
            min_date=begin, max_date=end)
    historicalMeta = DBMeta(tournaments, players=players)

    # Then, get the overall metagame and individual metagames for recent
    # tournaments.
    recent = tournaments[-tournies:]
    metas = [ DBMeta((t,), players=players) for t in recent ]
    overallMeta = DBMeta(recent, players=players)

    # Then, figure out which decks and tournaments to actually report data
    # from, based on those metagames.

    toinclude = set()

    # 1. If include_all, include all decks in the historical meta. Overrides
    #    everything else.
    # 2. If exclude_unselected, don't automatically include any decks.
    # 3. If fieldtotal, include decks that are at least that percentage
    #    of the overall metagame.
    # 4. Otherwise, include decks that are at least <field> of at least
    #    <appearances> of the individual metagames.
    # 5. If this results in nothing but 'Unknown', just use an empty set.
    if include_all:
        toinclude = { decktype for decktype in historicalMeta.archetypes }
    elif not exclude_unselected:
        if fieldtotal > 0:
            minCount = overallMeta.total * fieldtotal
            for decktype in overallMeta.archetypes:
                if overallMeta.getCount(decktype) >= minCount:
                    toinclude.add(decktype)
        else:
            counts = {}
            for meta in metas:
                minCount = meta.total * field
                for decktype in meta.archetypes:
                    if meta.getCount(decktype) >= minCount:
                        counts[decktype] = counts.get(decktype, 0) + 1
                    if counts.get(decktype, 0) >= appearances:
                        toinclude.add(decktype)
        # Leave out any decks manually excluded.
        for decktype in exclude:
            toinclude.remove(decktype)
    # If this leaves us with nothing but Unknown, make that explicit.
    if len(toinclude.difference(set(['Unknown']))) == 0:
        toinclude = set()

    # Add any decks manually included.
    for decktype in include:
        toinclude.add(decktype)

    decktypes = list(toinclude)
    decktypes.sort()
    decktypes.sort(key=lambda s: overallMeta.getCount(s), reverse=True)

    groups = {}
    for g in group:
        name = g[0]
        members = g[1:]
        groups[name] = members

    return kwargs, decktypes, groups, overallMeta, historicalMeta, tournaments, players

# Programmatic interface.
def tmi(func, **kwargs):
    """Call the TMI script programmatically. Func is the string representing the
    report to generate ('breakdown', 'trend', etc.), while the remaining
    keyword arguments are the long forms of the command line arguments."""
    mapping = { 'breakdown': getBreakdownWrapper,
                'list': getListWrapper,
                'trend': getTrendWrapper,
                'cards': getCardInfoWrapper,
                'diversity': getDiversityWrapper,
                'matchups': getMatchupsWrapper,
                'history': getHistoryWrapper,
                'grid': getGridWrapper,
                'explain': explainWrapper,
                'skill': skillWrapper }
    data = buildMeta(**kwargs)
    function = mapping[func]
    return function(*data)

# Class to allow command line arguments which specify multiple lists.
class MultiListAction(argparse.Action):
    """An action that specifies a list, where multiple invocations
    specify more lists. It creates a two-dimensional list, or a list of
    lists."""
    def __call__(self, parser, namespace, values, option_string=None):
        multilist = getattr(namespace, self.dest)
        if multilist:
            multilist.append(values)
            setattr(namespace, self.dest, multilist)
        else:
            setattr(namespace, self.dest, [values,])
        return namespace

# Command line interface.
def main(arglist):
    p = argparse.ArgumentParser(description=\
            """Summarizes results from recent SCG Opens and other
            tournaments.""")
    p.add_argument('-b', '--begin', type=str,
            default=config['defaults']['begin-date'], help='\
            Earliest date to consider tournaments for matchups and include\
            tournaments in results.')
    p.add_argument('-D', '--end', type=str, default=defaultEnd(),
            help='Latest date to consider tournaments for matchups and\
            include tournaments in results.')
    p.add_argument('-t', '--tournies', type=int, default=1, help='Number of\
            tournaments to look back to determine which decks to use.')
    p.add_argument('-a', '--appearances', type=int, default=1, help='Number of\
            appearances above a certain threshold required to include a deck.')
    p.add_argument('-f', '--field', type=float, default=.05, help='Threshold for \
            counting an appearance -- proportion of field that constitutes a \
            significant showing.')
    p.add_argument('-F', '--fieldtotal', type=float, default=0.0, help='Threshold for \
            including a deck -- minimum proportion of field, after including all \
            tournaments. Will override -f.')
    p.add_argument('-g', '--group', nargs='+', action=MultiListAction, default=[], help='\
            Treat a list of decks as one deck. Can be used multiple times.\
            The first argument is the name of the group.')
    p.add_argument('-l', '--limit', type=int, help='Only print the top X\
            results.')
    p.add_argument('-o', '--output', type=str, default='table', help='\
            Specify output format:\
                table: human-readable table (default)\
                tab: tab-delimited table\
                csv: comma-delimited table\
                latex: latex document\
                pickle: serialized Table object')
    p.add_argument('-O', '--format', type=str, default='Legacy', help='\
            Tournament format to analyze.')
    p.add_argument('-p', '--player_file', type=argparse.FileType('r'),
            default=None, const=sys.stdin, nargs='?', help='File containing\
            a list of players to restrict calculations to. If no filename\
            is given, read from standard input.')
#    p.add_argument('-r', '--require_top', type=int, default=0, help='Ignore\
#            tournaments where the top r decks are not all known.')
    p.add_argument('-s', '--sub', action="store_true", help='Break down decks \
            by sub-archetype.')
    p.add_argument('-S', '--source', default=None, help='Data source \
            (by default, don\'t filter on source).')
    p.add_argument('-i', '--include', nargs='+', type=str, default=[], help='\
            Additional decks to include in analysis.')
    p.add_argument('-I', '--include_all', action="store_true", help='Include all\
            deck types (use wisely).')
    p.add_argument('-e', '--exclude', nargs='+', type=str, default=[], help='\
            Decks to exclude from analysis.')
    p.add_argument('-E', '--exclude_unselected', action="store_true", help='\
            Exclude all decks other than those explicitly provided.')
    p.add_argument('-r', '--round', type=int, default=1, help="Begin with \
            this round of each tournament. Archetype selection still uses \
            whole tournaments, but earlier rounds are ignored.")
    p.add_argument('-c', '--cards', nargs='+', type=str, default=[],
            help='Individual card names -- decks containing a given card will be \
            treated as an archetype/group (where decklists exist)')

    subp = p.add_subparsers(title='commands', help='Type of data to report. Required.',
            dest='option_name')

    breakdownp = subp.add_parser('breakdown', help='Show a breakdown for one or more tournaments.')
    breakdownp.add_argument('outputs', nargs='*', type=str, default=['field', 'n',
            'avgplace', 'win', 'loss', 'draw', 'mwp', 'mwpLowerBound', 'mwpUpperBound',
            'mwpo', 'ev', 'evPairings'],
            help='Statistics to output.')
    breakdownp.add_argument('-a', '--all', action="store_true",
            help='Break down all tournaments from the given time period.')
    breakdownp.add_argument('-p', '--percentTop', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "%% of the Top X."')
    breakdownp.add_argument('-P', '--penetration', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "%% of decks making Top X."')
    breakdownp.add_argument('-v', '--conversion', nargs='+', type=float, default=[], help='Add any number\
            of statistics of the form "%% of decks with at least X wins."')
    breakdownp.add_argument('-t', '--top', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "# of Top X placings."')
    breakdownp.add_argument('-T', '--tournaments', nargs='+', type=int, default=[1], help='\
            Break down the Nth most recent tournament(s).')
    breakdownp.set_defaults(func=getBreakdownWrapper)

    cardp = subp.add_parser('cards', help='Show statistics for individual cards.')
    cardp.add_argument('outputs', nargs='*', type=str, default=['decks',
            'pdecks', 'record', 'mwp', 'maincopies', 'sidecopies'],
            help='Statistics to output. Sort on these values, in order.')
    cardp.add_argument('-t', '--top', type=int, help='Only get stats for \
            the top X decks.')
    cardp.add_argument('-T', '--plus_top', type=int, nargs='+',
            help='Also get stats for top X decks, for each X provided.')
    cardp.set_defaults(func=getCardInfoWrapper)

    diversityp = subp.add_parser('diversity', help='Track tournament diversity over time.')
    diversityp.add_argument('-g', '--infogain', nargs='*', type=float,
            help='Print information gain for placing in the\
            top X%% -- the difference between the entropy for all\
            participants and the entropy for the top performers.\
            If option is given with no arguments, X = .5')
    diversityp.add_argument('-G', '--infogainmatch', action='store_true', help=\
            'Print information gain for a match win -- the difference\
            between the entropy for a match participant and the entropy for\
            a match winner.')
    diversityp.add_argument('-s', '--summary', action='store_true', help=\
            'Print diversity for the sum of recent tournaments as well as\
            for the sum of historical tournaments.')
    diversityp.add_argument('-t', '--top', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "Diversity of the Top X"')
    diversityp.add_argument('function', nargs='*', choices=('h', 'd', 'D', 'r', '-', []),
            help="Select diversity function: h for Entropy, d for " +\
            "Simpson's Diversity Index, or D for Simpson's Index with " +\
            "replacement.")
    diversityp.set_defaults(func=getDiversityWrapper)

    explainp = subp.add_parser('explain', help='Try to explain a deck\'s win\
            percentage and EV; highlight to archetypes that contribute the most to\
            both numbers.')
    explainp.add_argument('deck', type=str, help='Deck type to explain.')
    explainp.add_argument('order', type=str, default='w', nargs='?', help='Stat to \
            order by: w, l, ev, evneg, winp, or lossp.')
    explainp.set_defaults(func=explainWrapper)

    gridp = subp.add_parser('grid', help='Print a table of matchups between various decks.')
    gridp.add_argument('-O', '--overall_title', type=str, default='Overall',
            help='Alternate term for "Overall."')
    gridp.add_argument('--no_overall', action='store_true', help='Don\'t print \
            an overall column.')
    gridp.set_defaults(func=getGridWrapper)

    historyp = subp.add_parser('history', help='Get recent showings by particular decks and/or players.')
    historyp.add_argument('outputs', nargs='*', type=str, default=[ 'avgplace', 'percentile',
        'win', 'loss', 'draw', 'mwp' ],
            help='Statistics to output.')
    historyp.add_argument('-t', '--top_only', type=int, default=0, help='Restrict to appearances within the top X.')
    historyp.set_defaults(func=getHistoryWrapper)

    listp = subp.add_parser('list', help='Don\'t report statistics, but print a list of decks that would be analyzed.')
    listp.set_defaults(func=getListWrapper)

    matchp = subp.add_parser('matchups', help='Print matchups for a particular \
            deck or combination of decks.')
    matchp.add_argument('deck', nargs='+', type=str, help='Decks to report \
            combined matchups for.')
    matchp.add_argument('-c', '--conf', type=float, help='Generate confidence intervals \
            using this probability.')
    matchp.add_argument('-n', '--nmatches', action='store_true', help='Print the \
            number of matches.')
    matchp.add_argument('-l', '--label', help='Label to use for this group of decks.')
    matchp.add_argument('-o', '--overall', type=str, nargs=2, help='Date range for \
            overall matchups.')
    matchp.add_argument('-O', '--overall_title', type=str, default='Overall',
            help='Alternate term for "Overall."')
    matchp.add_argument('--no_overall', action='store_true', help='Don\'t print \
            an overall column.')
    matchp.set_defaults(func=getMatchupsWrapper)

    trendp = subp.add_parser('trend', help='Track various statistics over time.')
    trendp.add_argument('outputs', nargs='*', type=str, default=[],
            help='Statistics to output.')
    trendp.add_argument('-c', '--p_card', nargs='+', type=str, default=[], help='Add any number\
            of statistics of the form "%% of cards which are card X"')
    trendp.add_argument('-C', '--p_containing', nargs='+', type=str, default=[], help='Add any number\
            of statistics of the form "%% of decks containing card X"')
    trendp.add_argument('-g', '--group_by_month', action='store_true',
            help='Group tournaments by month.')
    trendp.add_argument('-G', '--group_by_week', action='store_true',
            help='Group tournaments by week.')
    trendp.add_argument('-n', '--card_count', nargs='+', type=str, default=[], help='Add any number\
            of statistics of the form "# of copies of card X"')
    trendp.add_argument('-N', '--containing', nargs='+', type=str, default=[], help='Add any number\
            of statistics of the form "# of decks containing card X"')
    trendp.add_argument('-p', '--percentTop', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "%% of the Top X."')
    trendp.add_argument('-P', '--penetration', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "%% of decks making Top X."')
    trendp.add_argument('-v', '--conversion', nargs='+', type=float, default=[], help='Add any number\
            of statistics of the form "%% of decks with at least X wins."')
    trendp.add_argument('-s', '--skip', action='store_true', default=False, help='Skip\
            tournaments for which we have zero card data.')
    trendp.add_argument('-t', '--top', nargs='+', type=int, default=[], help='Add any number\
            of statistics of the form "# of Top X placings."')
    trendp.add_argument('-T', '--restrict_top', type=int, default=0, help='Restrict analysis\
            to decks placing <= T.')
    trendp.add_argument('-w', '--window', type=int, default=1, help='Compute statistics\
            over an overlapping sliding window of the latest w tournaments.')
    trendp.set_defaults(func=getTrendWrapper)


    skillp = subp.add_parser('skill', help="Compare players' performances\
            with specific decks to their overall performances.")
    skillp.add_argument('-m', '--min_deck', type=int, default=0, help='\
            Minimum number of matches with the deck needed to include the \
            data point.')
    skillp.add_argument('-M', '--min_other', type=int, default=0, help='\
            Minimum number of matches with other decks needed to include the \
            data point.')
    skillp.add_argument('-n', '--min_all', type=int, default=0, help='\
            Minimum number of total matches needed to include the data point.')
    skillp.add_argument('-o', '--other', action='store_true', help='\
            Also report performance with other decks.')
    skillp.set_defaults(func=skillWrapper)

    insertp = subp.add_parser('insert', help='Insert a tournament from CSV files.')
    insertp.add_argument("deckfile", type=str)
    insertp.add_argument("matchfile", type=str)
    insertp.add_argument("name", type=str)
    insertp.add_argument("month", type=int)
    insertp.add_argument("day", type=int)
    insertp.add_argument("year", type=int)
    insertp.add_argument("city", type=str)
    insertp.add_argument("-s", "--state", type=str, default=None)
    insertp.add_argument("-c", "--country", type=str, default=None)
    insertp.add_argument("-f", "--format", type=str, default="Legacy")
    insertp.add_argument("-g", "--game_counts", action="store_true",
            help="Results are broken down by game count; expects one column " +
                    "each for win/loss/draw. Otherwise, expects a result " +
                    "with strings such as 'Won 2-1'.")
    insertp.add_argument("-o", "--source", type=str, default="?",
            help="String representing the source of the data, often the " +
            "organizer.")
    insertp.add_argument("-d", "--dry_run", action="store_true",
            help="Perform a dry run: parse the data, but don't commit " +
                "anything to the database")
    insertp.set_defaults(func=insertWrapper)

    # Still to implement:
    # test main options -s, -r
    # work on skill functions
    # commands grid, history

    args = p.parse_args(arglist)
    if args.option_name is None:
        p.print_help();
        sys.exit(1)

    # Build the metagame descriptions.
    data = buildMeta(**vars(args))

    # Call the appropriate function to generate the output (or process input).
    table = args.func(*data)

    # If data was generated, figure out how to output the data.
    if (table):
        if args.output == 'tab':
            table.printDelim('\t')
        elif args.output == 'csv':
            table.printDelim(',')
        elif args.output == 'latex':
            table.printLatex()
        elif args.output == 'pickle':
            print(pickle.dumps(table))
        else:
            if args.limit:
                table.printTable(limit=args.limit)
            else:
                table.printTable()
    return table

if __name__ == '__main__':
    main(sys.argv[1:])
