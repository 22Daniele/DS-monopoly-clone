from random import Random
import json

class Space:
    def __init__(self, name: str):
        self._name = name

    def get_state(self):
        return {"name": self._name}

class ActionSpace(Space):
    def __init__(self, name: str, type: str):
        super().__init__(name)
        self._type = type

class PropertySpace(Space):
    def __init__(self, name: str, price: int):
        super().__init__(name)
        self._name = name
        self._price = price
        self._owner = ""
        self._houses = 0

    def assign(self, owner: str):
        self._owner = owner

    def remove_owner(self):
        self._owner = ""

    def get_price(self):
        return self._price

    def build_house(self, n: int):
        if self._houses == 4 and n == 1:
            self._houses += n
            return True
        if self._houses + n > 4:
            return False
        self._houses += n
        return True

    def get_owner(self):
        return self._owner

    def get_state(self):
        return {
            "name": self._name,
            "owner": self._owner,
            "houses": self._houses,
        }

class Board:

    def __init__(self, spaces_path = "/Users/daniele/PycharmProjects/DS-monopoly-clone/dmonopoly/model/board_spaces.json"):
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

    def is_property(self, property_idx: int):
        return property_idx in self._property_indexes

    def get_property_owner(self, property_idx: int):
        if not self.is_property(property_idx):
            return ""
        return self.get_space(property_idx).get_owner()

    def get_space(self, idx: int):
        return self._spaces[idx]

    def get_state(self):
        return {
            "spaces": [s.get_state() for s in self._spaces],
        }


class Player:

    def __init__(self, nickname: str):
        self._bankruptcy = False
        self._nickname = nickname
        self._position = 0
        self._balance = 500
        self._properties = []
        self._random = Random()

    def get_nickname(self):
        return self._nickname

    def roll(self):
        dice = self._random.randint(2, 12)
        self._position = (self._position + dice) % 36
        return self._position, dice

    def add_property(self, property_idx):
        self._properties.append(property_idx)

    def pay(self, amount: int):
        if self.can_afford(amount):
            self._balance -= amount
        else:
            self._set_bankruptcy()
        return not self._bankruptcy

    def buy_property(self, property_idx: int, amount: int):
        self.pay(amount)
        self.add_property(property_idx)

    def get_paid(self, amount: int):
        self._balance += amount

    def can_afford(self, amount: int):
        return amount <= self._balance

    def get_state(self):
        return {
            "nickname": self._nickname,
            "position": self._position,
            "balance": self._balance,
            "properties": self._properties,
            "bankruptcy": self._bankruptcy,
        }

    def _set_bankruptcy(self):
        self._bankruptcy = True
        self._balance = 0

    def get_properties(self):
        return self._properties


class Monopoly:
    STARTING_PROPERTIES = 0
    def __init__(self):
        self._board = Board()
        self._turn: int | None = None
        self._status = "LOBBY"
        self._players: list[Player] = []
        self._has_rolled = False

    def add_player(self, nickname: str):
        player = Player(nickname)
        self._players.append(player)

    def remove_player(self, nickname: str):
        player = self._get_player(nickname)
        if player:
            self._players.remove(player)

    def start(self):
        self._turn = 0
        self._assign_random_properties()
        self._status = "PLAYING"

    def running(self):
        return self._status != "CLOSED"

    def next_turn(self):
        self._turn = (self._turn + 1) % len(self._players)
        self._has_rolled = False

    def build_houses(self, nickname: str, property_idx: int, n: int):
        owner = self._board.get_property_owner(property_idx)
        if nickname != owner:
            return False
        return self._board.get_space(property_idx).build_house(n)

    def buy_property(self, nickname, property_idx):
        price = self._board.get_space(property_idx).get_price()
        player = self._get_player(nickname)
        if player:
            player.buy_property(property_idx, price)
            self._board.get_space(property_idx).assign(player.get_nickname())

    def roll_dice(self, nickname: str):
        player = self._get_player(nickname)
        if player and not self._has_rolled:
            new_position, dice = player.roll()
            self._has_rolled = True
            self._space_action(new_position, player)
            return dice
        return 0

    def get_state(self):
        return {
            "status": self._status,
            "players": [p.get_state() for p in self._players],
            "turn": self._players[self._turn].get_nickname() if self._turn is not None else None,
            "allowed_actions": self._get_allowed_actions(),
            "board": self._board.get_state()
        }

    def _get_player(self, nickname: str):
        for player in self._players:
            if player.get_nickname() == nickname:
                return player
        return None

    def _space_action(self, position: int, player: Player):
        if self._board.is_property(position):
            owner = self._board.get_property_owner(position)
            if not owner:
                pass #can purchase
            elif owner != player.get_nickname():
                amount = self._board.get_space(position).get_price()
                owner = self._get_player(owner)
                if owner:
                    owner.get_paid(amount)
                if not player.pay(amount):
                    for prop_idx in player.get_properties():
                        self._board.get_space(prop_idx).remove_owner()
        else:
            pass #if chest, if chance, if jail, ecc...

    def _assign_random_properties(self):
        shuffled = self._board.get_random_properties(len(self._players) * self.STARTING_PROPERTIES)
        for player in self._players:
            for j in range(Monopoly.STARTING_PROPERTIES):
                prop_idx = shuffled.pop(0)
                prop = self._board.get_space(prop_idx)
                prop.assign(player.get_nickname())
                player.add_property(prop_idx)

    def _get_allowed_actions(self):
        allowed_actions = []
        if self._status != "PLAYING" or self._turn is None:
            return allowed_actions
        current_player = self._players[self._turn]
        if not self._has_rolled:
            allowed_actions.append("roll")
        else:
            allowed_actions.append("end_turn")
            if len(current_player.get_properties()) > 0:
                allowed_actions.append("BUILD")
            pos = current_player.get_state()["position"]
            if self._board.is_property(pos):
                owner = self._board.get_property_owner(pos)
                if not owner:
                    price = self._board.get_space(pos).get_price()
                    if current_player.can_afford(price):
                        allowed_actions.append("BUY")
        return allowed_actions