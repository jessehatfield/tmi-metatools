class Tournament(object):
    """Represents a tournament.

    Overall model:

    tournament = {
        date: "2010-01-01",
        city: "X",
        state: "Y",
        country: "Z",
        name: "Awesome Tourney 123",
        decks: {
            1: {
                maindeck: { "Tarmogoyf": 4, "Brainstorm": 4, ... },
                sideboard: { "Tormod's Crypt": 0, ... },
                player: "John Doe",
                points: 18
                },
            2: { },
            ...
        }
    }
    """ 

    def __init__(self, name=None, date=None, city=None, state=None, country=None,
            format=None, numPlayers=0):
        """Instantiate a Tournament. All arguments are optional and will
        default to None or 0 if not specified."""
        self.name = name
        self.date = date
        self.city = city
        self.state = state
        self.country = country
        self.format = format
        self.decks = []
        self.numPlayers = numPlayers

    def __iter__(self):
        return iter(self.decks)

    def __repr__(self):
        return "<Tournament({0}, {1}, {2}: {3} players>".format(self.city,
                self.state, self.date, self.numPlayers)

    def setName(self, name):
        self.name = name
    def setDate(self, date):
        self.date = date
    def setCity(self, city):
        self.city = city
    def setState(self, state):
        self.state = state
    def setCountry(self, country):
        self.country = country
    def setFormat(self, format):
        self.format = format
    def setNumPlayers(self, numPlayers):
        self.numPlayers = numPlayers

    def addDeck(self, deck, place):
        deck.setPlace(place)
        self.decks.append(deck)

    def getName(self):
        return self.name
    def getDate(self):
        return self.date
    def getCity(self):
        return self.city
    def getState(self):
        return self.state
    def getCountry(self):
        return self.country
    def getFormat(self):
        return self.format
    def getDecks(self):
        return self.decks
    def getNumPlayers(self, players=None):
        """Get the number of players. If the stored number of players
        differs from the total number of decks, return the larger."""
        if players:
            count = 0
            for d in self.decks:
                if d.player and d.player in players:
                    count += 1
            return count
        return max(self.numPlayers, len(self.decks))

    def printResults(self):
        """Print full results."""
        print("%s (%s)" % (self.name, self.format))
        print("%s" % (self.date))
        print("%s, %s, %s" % (self.city, self.state, self.country))
        print
        for deck in self.decks:
            deck.printList()
