from re import compile
from random import shuffle
from sqlalchemy import orm

class Card(object):
    """Class represents a single copy of a card and keeps track of that card's state."""

    def __init__(self, cn, cost=None, text=None, power=None, toughness=None,
            loyalty=None):
        """Create a new card with a given name."""
        self.name = cn
        self.hidden = True
        self.tapped = False
        self.note = ""
        self.power = power
        self.toughness = toughness
        self.cost = cost
        self.text = text

    def toggleHidden(self):
        """Reveal or hide the card."""
        if (self.hidden):
            self.hidden = False
        else:
            self.hidden = True

    def setHidden(self, h):
        """Reveal or hide the card."""
        self.hidden = h

    def getHidden(self):
        """Returns whether the card is hidden."""
        return self.hidden

    def getName(self):
        """Get the name, unless the card is hidden."""
        if self.hidden:
            name = "(Unknown)"
        else:
            name = self.name
        if self.tapped:
            name = name + " {T}"
        return name

    def getColor(self):
        """Get the card's color, C for colorless, or M for multicolored."""
        if self.cost is None or self.hidden:
            return 'C'
        colors = ''
        for c in 'WUBRG':
            if c in self.cost:
                colors = colors + c
        if len(colors) == 1:
            return colors
        elif len(colors) > 1:
            return 'M'
        else:
            return 'C'

    def toggleTapped(self):
        """Toggle whether the card is tapped."""
        if self.tapped:
            self.tapped = False
        else:
            self.tapped = True

    def setTapped(self, t):
        """Set whether the card is tapped."""
        self.tapped = t

    def getTapped(self):
        """Get the card's tapped status."""
        return self.tapped

    def setNote(self, n):
        """Set a note for the card.."""
        self.note = n

    def getNote(self):
        """Get the note."""
        return self.note

class Deck(object):
    """Represents a deck that was played in a tournament.

    Overall model:

    deck = {
        maindeck: { "Tarmogoyf": 4, "Brainstorm": 4, ... },
        sideboard: { "Tormod's Crypt": 0, ... },
        points: 18,
        player: "John Doe",
        archetype: "Counter-Top",
        subarchetype: "Natural Order"
    }
    """ 

    def __init__(self, place=None, player=None,
            tournament=None, record=None, points=None,
            archetype="Unknown", subarchetype=""):
        self.initialize()
        self.place = place
        self.player = player
        self.tournament = tournament
        self.record = record
        self.points = points
        self.archetype = archetype
        self.subarchetype = subarchetype
        self.matches = []
        self.slots = []

    @staticmethod
    def fromFile(fn):
        d = Deck()
        d.readFile(fn)
        return d

    @orm.reconstructor
    def initialize(self):
        """Perform some initializations which are necessary to
        function."""
        self.maindeck = {}
        self.sideboard = {}
        self.library = []

    def getMatches(self):
        return matches

    def loadContents(self):
        """Go to the database and, if we have the decklist, load it."""
        for slot in self.slots:
            self.addMain(slot.cardname, slot.main)
            self.addSide(slot.cardname, slot.side)

    def __repr__(self):
        if self.subarchetype:
            return "<Deck({0}: {1}, {2})>".format(self.player, self.archetype, self.subarchetype)
        else:
            return "<Deck({0}: {1})>".format(self.player, self.archetype)

    def readFile(self, fn):
        """Read in the contents of the Deck as a decklist.
        The file should follow the following format:
            <number> <name>
            ...
            [Ss]ide<...>
            <number> <name>
            ...
        fn: Filename of the decklist."""
        self.readLines([ line for line in open(fn) ])

    def readLines(self, lines):
        """Read in the contents of the Deck as a list of strings. Each
        string beginning with a number, followed by whitespace, followed
        by any name, will add that number of the named card to the deck.
        If a line begins "[Ss]ide", then every card after that is added
        to the sideboard, rather than the maindeck."""
        re = compile(r'^(\d+)[^\s]*\s+(.*)$')
        r2 = compile(r'^[sS]ide')
        sideboard = 0
        for line in lines:
            m = re.match(line)
            if m:
                count = m.group(1)
                card = m.group(2)
                for i in range(0,int(count)):
                    if sideboard:
                        self.addSide(card)
                    else:
                        self.addMain(card)
            else:
                m2 = r2.match(line)
                if m2:
                    sideboard = 1

    def __iter__(self):
        """Returns an iterator over the maindeck."""
        self.iterator = iter(self.maindeck)

    def __next__(self):
        """Get the next card in the maindeck."""
        return self.iterator.next()
    
    def addMain(self, card, n=1):
        """Add cards to the maindeck.
        card: The card name (string)
        n: How many to add (int)"""
        if n == 0:
            return
        self.maindeck[card] = max((self.maindeck.get(card, 0) + n), 0)
        for i in range(n):
            self.library.append(Card(card))

    def addSide(self, card, n=1):
        """Add cards to the sideboard.
        card: The card name (string)
        n: How many to add (int)"""
        if n == 0:
            return
        self.sideboard[card] = max((self.sideboard.get(card, 0) + n), 0)

    def removeMain(self, card, n=1):
        """Remove cards from the maindeck.
        card: The card name
        n: How many to remove"""
        self.addMain(card, -n)
        indices = sorted(filter(lambda i: self.library[i].name == card,
                range(len(self.library))), reverse=True)
        for i in range(min(n, len(indices))):
            self.library.pop(i)

    def removeSide(self, card, n=1):
        """Remove cards from the sideboard.
        card: The card name
        n: How many to remove"""
        self.addSide(card, -n)

    def setMain(self, main):
        """Specify the maindeck explicitly.
        main: A dict of the form { cardname: count, ...  }"""
        self.maindeck = main
        for c in main:
            for i in range(main[c]):
                self.library.append(Card(c))

    def setSide(self, side):
        """Specify the maindeck explicitly.
        main: A dict of the form { cardname: count, ...  }"""
        self.sideboard = side

    def setPlace(self, place):
        self.place = place
    def setPlayer(self, player):
        self.player = player
    def setTournament(self, tournament):
        self.tournament = tournament
    def setTiebreakers(self, tb):
        self.tiebreakers = tb
    def setPoints(self, points):
        self.points = points
    def setRecord(self, record):
        self.record = record
    def setArchetype(self, archetype):
        self.archetype = archetype
    def setSubarchetype(self, subarchetype):
        self.subarchetype = subarchetype

    def getMain(self):
        return self.maindeck
    def getSide(self):
        return self.sideboard
    def getPlace(self):
        return self.place
    def getPlayer(self):
        return self.player
    def getTournament(self):
        return self.tournament
    def getTiebreakers(self):
        return self.tiebreakers
    def getPoints(self):
        return self.points
    def getRecord(self):
        return self.record
    def getArchetype(self):
        return self.archetype
    def getSubarchetype(self):
        return self.subarchetype

    def printList(self):
        """Output the decklist in human-readable form."""
        if self.place:
            print("%s (%s -- %d)" % (self.archetype, self.player, self.place))
        else:
            print("%s (%s)" % (self.archetype, self.player))
        if len(self.maindeck) > 0:
            print
            for card in self.maindeck:
                print("%dx %s" % (self.maindeck[card], card))
            if len(self.sideboard) > 0:
                print()
                print("Sideboard")
                for card in self.sideboard:
                    print("%dx %s" % (self.sideboard[card], card))
            print

    def count(self):
        return len(self.library)

#    def save(self, conn, tid, verbose=False):
#        """Save the deck to the database as belonging to the particular
#        Tournament.
#        conn: MySQLdb connection
#        tid: ID of a Tournament
#        verbose: True to print when finished (default False)"""
#        cursor = conn.cursor()
#        insert = """INSERT INTO Deck
#        (T_ID, PLAYER_NAME, DECK_NAME, QUALIFIER, PLACE, RECORD, POINTS)
#        VALUES (%s, %s, %s, %s, %s, %s)"""
#        record = "NULL"
#        if self.record:
#            record = str(self.record)
#        points = "NULL"
#        if self.points:
#            points = int(self.points)
#        cursor.execute(insert, (int(tid), self.player, self.archetype, self.subarchetype, self.place, record, points))
#        did = conn.insert_id()
#        for card in self.sideboard:
#            if card not in self.maindeck:
#                self.maindeck[card] = 0
#        for card in self.maindeck:
#            numMain = self.maindeck[card]
#            numSide = self.sideboard.get(card, 0)
#            cursor.execute("""INSERT INTO Contents (DECK_ID, CARD_NAME, NUM_MAIN,
#                    NUM_SIDE) VALUES (%s, %s, %s, %s)""", (did, card,
#                        numMain, numSide))
#        cursor.close()
#        if verbose:
#            print("Inserted deck %s" % (did))

    def shuffle(self):
        """Randomize the contents of the deck."""
        shuffle(self.library)

    def drawHand(self, n):
        """Draw a hand of n cards from the deck.
        Returns the first n cards, given the current order."""
        return self.library[0:n]

    def printHand(self, n):
        """Draw and print a hand of n cards.
        Prints the first n cards, given the current order."""
        cols = 3
        rows = n / cols
        for i in range(n):
            if i % cols == 0:
                print
            print("%25s " % (self.library[i].name)),
        print()
