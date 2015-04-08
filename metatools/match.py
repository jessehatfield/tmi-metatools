from sqlalchemy import orm

class Match(object):
    """A match played between two Decks at a particular Tournament."""

    def __init__(self, deck1, deck2, win, loss, draw=0, round=None):
        self.deck1 = deck1
        self.deck2 = deck2
        self.game_win = win
        self.game_loss = loss
        self.game_draw = draw
        self.round = round
        self.tournament = deck1.tournament
        self.initialize()

    @orm.reconstructor
    def initialize(self):
        self.win, self.loss, self.draw = (0, 0, 0)
        if self.game_win > self.game_loss:
            self.win = 1
        elif self.game_loss > self.game_win:
            self.loss = 1
        else:
            self.draw = 1

    def __repr__(self):
        return '<Match({0} {1}-{2}-{3} vs. {4})>'.format(self.deck1.archetype,
            self.game_win, self.game_loss, self.game_draw, self.deck2.archetype)
