from random import Random
import json

class Space:
    def __init__(self, name: str):
        self._name = name

class ActionSpace(Space):
    def __init__(self, name: str, type: str):
        super().__init__(name)
        self._type = type

class PropertySpace(Space):
    def __init__(self, name: str, price: int):
        super().__init__(name)
        self._name = name
        self._price = price
        self._owner = None
        self._houses = 0

    def assign(self, owner: str):
        self._owner = owner

    def price(self):
        return self._price

    def build_house(self, n: int):
        if self._houses == 4 and n == 1:
            self._houses += n
            return True
        if self._houses + n > 4:
            return False
        self._houses += n
        return True

class Board:

    def __init__(self, spaces_path = "board_spaces.json"):
        self._random = Random()
        self._spaces = []
        self._property_indexes = []
        self._build_board(spaces_path)

    def _build_board(self, spaces_path: str):
        with open(spaces_path) as f:
            spaces = json.load(f)
        for i, space in enumerate(spaces):
            if space["type"] == "property":
                self._spaces.append(PropertySpace(space["name"], space["price"]))
                self._property_indexes.append(i)
            else:
                self._spaces.append(ActionSpace(space["name"], space["type"]))

    def get_random_properties(self, n: int):
        return self._random.sample(self._property_indexes, n)

    def get_space(self, idx: int):
        return self._spaces[idx]


class Player:

    def __init__(self, nickname: str):
        self.nickname = nickname
        self._position = 0
        self._balance = 500
        self._properties = []
        self._random = Random()

    def roll(self):
        return self._random.randint(2, 12)

    def add_property(self, property_idx):
        self._properties.append(property_idx)

    def pay(self, amount: int):
        if self.can_afford(amount):
            self._balance -= amount

    def can_afford(self, amount: int):
        return amount <= self._balance


class Monopoly:
    STARTING_PROPERTIES = 4
    def __init__(self, board: Board):
        self._board = board
        self._turn = None
        self._players = []

    def add_player(self, player: Player):
        self._players.append(player)

    def remove_player(self, player: Player):
        self._players.remove(player)

    def start(self):
        self._turn = 0
        self._assign_random_properties()

    def _assign_random_properties(self):
        shuffled = self._board.get_random_properties(len(self._players) * self.STARTING_PROPERTIES)
        for player in self._players:
            for j in range(Monopoly.STARTING_PROPERTIES):
                prop_idx = shuffled.pop(0)
                prop = self._board.get_space(prop_idx)
                prop.assign(player.nickname)
                player.add_property(prop_idx)

    def next_turn(self):
        self._turn = (self._turn + 1) % len(self._players)
