#!/usr/bin/env python

from metatools.database import *
from metatools.deck import *

import sys
import curses
from random import shuffle

top = 0
left = 0
bottom = 36
right = 100

colW = 20
exH = 5
handH = 8

rowW = right - left - (2 * colW)
colH = bottom - top
playW = rowW
playH = colH - exH - handH

class Zone(object):

    def __init__(self, x, y, width, height, name):
        """Initialize a zone with certain location, size, and name."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        self.contents = []
        self.firstCard = 0
        self.selected = 0
        self.focused = False

    def draw(self, win, colormap):
        """Draw the zone on the screen."""
        self.win = win
        for i in range(1, self.width):
            self.win.addch(self.y, i + self.x, '-')
            self.win.addch(self.y + self.height, i + self.x, '-')
        for i in range(1, self.height):
            self.win.addch(i + self.y, self.x, '|')
            self.win.addch(i + self.y, self.x + self.width, '|')
        self.win.addch(self.y, self.x, '+');
        self.win.addch(self.y + self.height, self.x, '+');
        self.win.addch(self.y, self.x + self.width, '+');
        self.win.addch(self.y + self.height, self.x + self.width, '+');

        sizeOfZone = len(self.contents)
        header = self.name + " (" + str(sizeOfZone) + ")"
        self.win.addstr(self.y, self.x + 2, header)

        # Get all the displayable card names.
        numCards = self.height - 1
        startPos = 0
        sizeOfZone = len(self.contents)

        # For every line in the displayed window,
        # print the name of a card or whitespace.
        # Indicate the currently selected card.
        for i in range(startPos, numCards):
            index = i + self.firstCard - startPos
            cardName = ""
            theCard = None
            if index < sizeOfZone:
                theCard = self.contents[index]
                cardName = theCard.getName()
            cardName = "  %-28s " % (cardName)
            for j in range(1, self.width):
                self.win.addch(self.y + i + 1, self.x + j, ' ')
            if theCard:
                if theCard.getHidden() == False and theCard.cost:
                    cardName =  cardName + '{' + theCard.cost + '}'
                self.win.addnstr(self.y + i + 1, self.x + 2, cardName,
                        self.width - 1, colormap[theCard.getColor()])
            if self.focused and i == self.selected - self.firstCard:
                self.win.addch(self.y + i + 1, self.x + 2, '*')

        # Draw arrows indicating vertical scroll if necessary.
        if self.firstCard + numCards < sizeOfZone:
            self.win.addstr(self.y + self.height - 1, self.x + 1, 'v')
        else:
            self.win.addstr(self.y + self.height - 1, self.x + 1, ' ')
        if self.firstCard > 0:
            self.win.addstr(self.y + 1, self.x + 1, '^')
        else:
            self.win.addstr(self.y + 1, self.x + 1, ' ')

    def add(self, lst):
        """Add a list to this zone's list."""
        self.contents += lst

    def append(self, item):
        """Append an item to this zone's list."""
        self.contents.append(item)

    def prepend(self, item):
        """Prepend an item to this zone's list."""
        self.contents.insert(0, item)

    def shuffle(self):
        """Shuffle this zone's list."""
        shuffle(self.contents)
        return self.contents

    def getContents(self):
        """Get this zone's contents."""
        return self.contents

    def handle(self, key):
        """Handle a keypress. ."""
        # Move down
        if key == ord('j'):
            self.selected += 1
            if self.selected >= len(self.contents):
                self.selected -= 1
            if (self.selected + 1) >= (self.firstCard + self.height):
                self.firstCard += 1

        # Move up
        elif key == ord('k'):
            if self.selected > 0:
                self.selected -= 1
            if self.firstCard > self.selected:
                self.firstCard -= 1

        # Tap or untap
        elif key == ord('t'):
            if self.selected >= 0 and self.selected < len(self.contents):
                self.contents[self.selected].toggleTapped()
        # Tap or untap all
        elif key == ord('T'):
            self.apply(Card.toggleTapped)
        # untap all
        elif key == ord('u'):
            self.apply(lambda x: x.setTapped(False))

        # Hide or reveal
        elif key == ord('v'):
            if self.selected >= 0 and self.selected < len(self.contents):
                self.contents[self.selected].toggleHidden()
        # Hide or reveal all
        elif key == ord('V'):
            self.apply(Card.toggleHidden)

    def popSelected(self):
        """Remove and return the selected card.."""
        item = False
        length = len(self.contents)
        if self.selected < length:
            item = self.contents.pop(self.selected)
            length -= 1
        if self.selected >= len(self.contents) and self.selected > 0:
            self.selected -= 1
        return item

    def setFocused(self, focus):
        """Set whether the zone is focused.."""
        self.focused = focus

    def getFocused(self):
        """Return whether the zone is focused.."""
        return self.focused

    def apply(self, fn):
        for card in self.contents:
            fn(card)

class Game(object):
    """Represents a game.."""

    def __init__(self, fn):
        """Create a new game. Load the deck from the given filename."""
        self.deck = Deck.fromFile(fn)
        self.newgame()

    def newgame(self):
        """Start the game."""
        self.graveyard = Zone(left, top, colW, colH, "Graveyard")
        self.exiled = Zone(left + colW, top, rowW, exH, "Exiled")
        self.battlefield = Zone(left + colW, top + exH, rowW, playH, "Battlefield")
        self.library = Zone(left + colW + playW, top, colW, bottom - top, "Library")
        self.hand = Zone(left + colW, top + exH + playH, rowW, handH, "Hand")

        self.focused = self.hand
        self.setFocus(self.hand)

        dbcards = [ getCard(c.name) for c in self.deck.library ]
        #dbcards = [ Card(c.name) for c in self.deck.library ]
        self.library.add(dbcards)
        self.shuffleLibrary()

        self.handsize = 7
        self.drawHand(self.handsize)

    def mulligan(self):
        """Take a mulligan."""
        self.handsize -= 1
        if (self.handsize > 0):
            for i in range(len(self.hand.getContents())):
                theCard = self.hand.getContents().pop(0)
                theCard.setHidden(True)
                self.library.append(theCard)
            self.shuffleLibrary()
            self.drawHand(self.handsize)

    def drawHand(self, num):
        """Draw a hand of X cards."""
        if num <= len(self.library.getContents()):
            for i in range(num):
                card = self.library.getContents().pop(0)
                card.setHidden(False)
                self.hand.append(card)

    def printhand(self):
        """Print the current hand."""
        n = len(self.hand.getContents())
        cols = 3
        rows = n / cols
        for i in range(n):
            if i % cols == 0:
                print
            print("%18s " % (self.hand.getContents()[i].getName()))
        print

    def draw(self, win, colormap):
        """Draw the current game state."""
        self.graveyard.draw(win, colormap)
        self.exiled.draw(win, colormap)
        self.battlefield.draw(win, colormap)
        self.library.draw(win, colormap)
        self.hand.draw(win, colormap)

    def shuffleLibrary(self):
        """Shuffle the library, and make sure that all cards in it are
        hidden."""
        self.library.shuffle()
        self.library.apply(lambda x: x.setHidden(True))

    def handle(self, key):
        """Handle a keypress."""
        # s : Shuffle the library
        if key == ord('s'):
            self.shuffleLibrary()

        # d : draw a card
        elif key == ord('d'):
            self.drawHand(1)

        # l : focus on library
        elif key == ord('l'):
            self.setFocus(self.library)
        # h : focus on hand
        elif key == ord('h'):
            self.setFocus(self.hand)
        # f : focus on battlefield
        elif key == ord('f'):
            self.setFocus(self.battlefield)
        # f : focus on graveyard
        elif key == ord('g'):
            self.setFocus(self.graveyard)
        # f : focus on exiled
        elif key == ord('e'):
            self.setFocus(self.exiled)

        # p : play the selected card
        elif key == ord('p'):
            theCard = self.focused.popSelected()
            if theCard:
                self.battlefield.append(theCard)
        # p : play the selected card to the top of the field
        elif key == ord('P'):
            theCard = self.focused.popSelected()
            if theCard:
                self.battlefield.prepend(theCard)
        # y : send the selected card to the graveyard
        elif key == ord('y'):
            theCard = self.focused.popSelected()
            if theCard:
                self.graveyard.append(theCard)
        # y : send the selected card to the bottom of the graveyard
        elif key == ord('Y'):
            theCard = self.focused.popSelected()
            if theCard:
                self.graveyard.prepend(theCard)
        # x : send the selected card to the exiled zone
        elif key == ord('x'):
            theCard = self.focused.popSelected()
            if theCard:
                self.exiled.append(theCard)
        # x : send the selected card to the top of the exiled zone
        elif key == ord('X'):
            theCard = self.focused.popSelected()
            if theCard:
                self.exiled.prepend(theCard)
        # x : send the selected card to the library
        elif key == ord('i'):
            theCard = self.focused.popSelected()
            if theCard:
                self.library.prepend(theCard)
        # x : send the selected card to the bottom of the library
        elif key == ord('I'):
            theCard = self.focused.popSelected()
            if theCard:
                self.library.append(theCard)
        # x : send the selected card to the hand
        elif key == ord('a'):
            theCard = self.focused.popSelected()
            if theCard:
                self.hand.append(theCard)
        # x : send the selected card to the top of the hand
        elif key == ord('A'):
            theCard = self.focused.popSelected()
            if theCard:
                self.hand.prepend(theCard)

        # m : Take a mulligan
        elif key == ord('m'):
            self.mulligan()

        # n : Start a new game
        elif key == ord('n'):
            self.newgame()

        # u : Untap everything.
        elif key == ord('u'):
            for zone in [self.graveyard, self.exiled, self.battlefield, self.library, self.hand]:
                zone.handle(key)

        else:
            self.focused.handle(key)

    def setFocus(self, zone):
        """Focus on a particular zone."""
        self.focused.setFocused(False)
        self.focused = zone
        self.focused.setFocused(True)


if __name__ == "__main__":
    filename = sys.argv[1]
    g = Game(filename)

    stdscr = curses.initscr()

    curses.start_color();
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)

    colormap = { 'W': curses.color_pair(0) | curses.A_BOLD,
                 'U': curses.color_pair(1) | curses.A_BOLD,
                 'B': curses.color_pair(2) | curses.A_DIM,
                 'R': curses.color_pair(3),
                 'G': curses.color_pair(4),
                 'M': curses.color_pair(5),
                 'C': curses.color_pair(6) }

    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)

    win = curses.newwin(bottom+2, right+2, 0, 0)
    g.draw(win, colormap)
    stdscr.refresh()

    x = 100
    while x != ord('q'):
        x = win.getch(5,5)
        g.handle(x)
        g.draw(win, colormap)
        stdscr.refresh()

    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()
