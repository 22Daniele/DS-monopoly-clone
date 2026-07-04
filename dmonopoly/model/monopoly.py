import os
import token
from random import Random, choice
import json

class Space:
    def __init__(self, name: str):
        self.name = name

class ActionSpace(Space):
    def __init__(self, name: str):
        super().__init__(name)

class PropertySpace(Space):
    def __init__(self, name: str, price: int):
        super().__init__(name)
        self.price = price
        self.owner = ""
        self.houses = 0

    def assign(self, owner: str):
        self.owner = owner

    def remove_owner(self):
        self.owner = ""

    def build_house(self):
        if self.houses == 5:
            return False
        self.houses += 1
        return True

class Board:

    def __init__(self, spaces_path = None):
        if spaces_path is None:
            base_dir = os.path.dirname(__file__)
            spaces_path = os.path.join(base_dir, "board_spaces.json")
        self._random = Random()
        self.spaces = []
        self.property_indexes = []
        self._build_board(spaces_path)

    def _build_board(self, spaces_path: str):
        with open(spaces_path) as f:
            spaces = json.load(f)
        for i, space in enumerate(spaces):
            if space["type"] == "property":
                self.spaces.append(PropertySpace(space["name"], space["price"]))
                self.property_indexes.append(i)
            else:
                self.spaces.append(ActionSpace(space["name"].lower()))

    def get_random_properties(self, n: int):
        return self._random.sample(self.property_indexes, n)

    def is_property(self, property_idx: int):
        return property_idx in self.property_indexes

    def get_property_owner(self, property_idx: int):
        if not self.is_property(property_idx):
            return ""
        property_space: PropertySpace = self.get_space(property_idx)
        return property_space.owner

    def get_space(self, idx: int):
        return self.spaces[idx]


class Player:

    def __init__(self, nickname: str, token: str = ""):
        self.bankruptcy = False
        self.nickname = nickname
        self.token = token
        self.position = 0
        self.balance = 5000
        self.properties = []
        self._random = Random()

    def roll(self):
        dice = self._random.randint(2, 12)
        self.position = (self.position + dice) % 40
        return self.position, dice

    def add_property(self, property_idx):
        self.properties.append(property_idx)

    def pay(self, amount: int):
        if self.can_afford(amount):
            self.balance -= amount
        else:
            self._set_bankruptcy()
        return not self.bankruptcy

    def buy_property(self, property_idx: int, amount: int):
        self.pay(amount)
        self.add_property(property_idx)

    def get_paid(self, amount: int):
        self.balance += amount

    def can_afford(self, amount: int):
        return amount <= self.balance

    def _set_bankruptcy(self):
        self.bankruptcy = True
        self.balance = 0

    def get_properties(self):
        return self.properties

    def disconnect(self):
        self._set_bankruptcy()


class Monopoly:
    STARTING_PROPERTIES = 5
    def __init__(self):
        self.waiting_for = set()
        self.players_ready = set()
        self.board = Board()
        self.turn: int | None = None
        self.status = "LOBBY"
        self.players: list[Player] = []
        self.has_rolled = False
        self.alive_players = 0
        self.last_event = "Waiting for players..."

        self.chance_cards = [
            "Tax on luxury: pay 150",
            "You win a prize: earn 100",
            "Speeding fine: pay 50",
            "Unexpected inheritance: earn 200"
        ]
        self.community_chest_cards = [
            "Bank error: earn 200",
            "Medical expenses: pay 100",
            "Go back to START! earn 200"
        ]

    def add_player(self, nickname: str, token: str = ""):
        player = Player(nickname, token)
        self.players.append(player)
        self.last_event = f"{nickname} joined the game"

    def get_player_token(self, nickname: str):
        player = self._get_player(nickname)
        return player.token if player else ""

    def remove_player(self, nickname: str):
        player = self._get_player(nickname)
        if player:
            for prop_idx in player.get_properties():
                self.board.get_space(prop_idx).remove_owner()
            if self.turn is not None:
                idx = self.players.index(player)
                if idx < self.turn:
                    self.turn -= 1
                elif idx == self.turn:
                    self.has_rolled = False
            self.players.remove(player)
            self.alive_players -= 1
            if self.turn is not None:
                if self.players and self.turn >= len(self.players):
                    self.turn = 0
            if self.alive_players <= 1:
                self._end()
                self.last_event = f"{nickname} quit. Not enough players. Game ended!"
            else:
                self.last_event = f"{nickname} quit the game"
        else:
            self.last_event = "error: no player found"

    def player_ready(self, nickname):
        self.players_ready.add(nickname)
        if len(self.players_ready) >= 2 and len(self.players_ready) == len(self.players):
            self.start()
            self.last_event = f"{nickname} is ready.\nEveryone is ready!\nGame start."
        else:
            self.last_event = f"{nickname} is ready"

    def start(self):
        self.turn = 0
        self._assign_random_properties()
        self.alive_players = len(self.players)
        self.status = "PLAYING"

    def running(self):
        return self.status == "PLAYING"

    def next_turn(self):
        self.turn = (self.turn + 1) % len(self.players)
        self.has_rolled = False
        self.last_event = f"{self.current_turn_nickname}: end turn"

    def build_houses(self, nickname: str):
        property_idx = self._get_player(nickname).position
        owner = self.board.get_property_owner(property_idx)
        if nickname != owner:
            self.last_event = "can't build on someone else properties"
            return
        player = self._get_player(nickname)
        space: PropertySpace = self.board.get_space(property_idx)
        if space.build_house():
            player.pay(50)
            self.last_event = f"{nickname} build the {space.houses}th house on {space.name}"
        else:
            self.last_event = "can't build more than 5 houses"

    def buy_property(self, nickname):
        player = self._get_player(nickname)
        if player:
            property_idx = player.position
            space = self.board.get_space(property_idx)
            price = space.price
            player.buy_property(property_idx, price)
            self.board.get_space(property_idx).assign(player.nickname)
            self.last_event = f"bought {space.name} by {player.nickname}"
        else:
            self.last_event = "error: no player found"

    def roll_dice(self, nickname: str):
        player = self._get_player(nickname)
        if player and not self.has_rolled:
            new_position, dice = player.roll()
            self.has_rolled = True
            log = self._space_action(new_position, player)
            self.last_event = f"rolled dices and got {dice}. " + log
        else:
            self.last_event = "error: player cannot roll dice"

    def _get_player(self, nickname: str):
        for player in self.players:
            if player.nickname == nickname:
                return player
        return None

    def _space_action(self, position: int, player: Player):
        if self.board.is_property(position):
            owner_nickname = self.board.get_property_owner(position)
            if not owner_nickname:
                return "property can be bought"
            elif owner_nickname != player.nickname:
                log = ""
                space: PropertySpace = self.board.get_space(position)
                amount = space.price
                rent = space.houses * amount
                amount = amount + rent
                owner = self._get_player(owner_nickname)
                if owner:
                    owner.get_paid(amount)
                    log += f" {owner_nickname} got paid {amount}"
                if not player.pay(amount):
                    log = self._player_bankruptcy(log, player)
                else:
                    log += f" {player.nickname} paid {amount}"
                return log
            return f" {player.nickname} is on his own property"
        else:
            space: ActionSpace = self.board.get_space(position)
            return self._execute_action_space(space, player)

    def _player_bankruptcy(self, log: str, player: Player) -> str:
        for prop_idx in player.get_properties():
            self.board.get_space(prop_idx).remove_owner()
        self.alive_players -= 1
        log += f" {player.nickname} lost"
        if self.alive_players == 1:
            self._end()
            log += f" game ended"
        return log

    def _assign_random_properties(self):
        shuffled = self.board.get_random_properties(len(self.players) * self.STARTING_PROPERTIES)
        for player in self.players:
            for j in range(Monopoly.STARTING_PROPERTIES):
                prop_idx = shuffled.pop(0)
                prop = self.board.get_space(prop_idx)
                prop.assign(player.nickname)
                player.add_property(prop_idx)

    @property
    def allowed_actions(self):
        allowed_actions = []
        if self.status != "PLAYING" or self.turn is None:
            return allowed_actions
        current_player = self.players[self.turn]
        if not self.has_rolled:
            allowed_actions.append("roll")
        else:
            allowed_actions.append("end_turn")
            if current_player.position in current_player.get_properties():
                if current_player.can_afford(50):
                    allowed_actions.append("build")
            pos = current_player.position
            if self.board.is_property(pos):
                owner = self.board.get_property_owner(pos)
                if not owner:
                    space: PropertySpace = self.board.get_space(pos)
                    price = space.price
                    if current_player.can_afford(price):
                        allowed_actions.append("buy")
        return allowed_actions

    @property
    def current_turn_nickname(self):
        if self.turn is not None and self.status == "PLAYING":
            return self.players[self.turn].nickname
        return None

    def _end(self):
        self.status = "CLOSED"

    def player_disconnection(self, nickname):
        if not self._get_player(nickname):
            return
        if self.status == "PLAYING":
            self.status = "PAUSED"
        self.waiting_for.add(nickname)
        self.last_event = f"disconnected {nickname}. Trying to reconnect..."

    def disconnected_players(self):
        return self.waiting_for

    def reconnection_timeout(self):
        for nickname in list(self.waiting_for):
            self.remove_player(nickname)
        self.waiting_for.clear()
        if self.alive_players > 1:
            self.last_event = self._restart_game()

    def reconnect_player(self, nickname):
        self.waiting_for.remove(nickname)
        if not self.disconnected_players():
            self.last_event = f"reconnected player {nickname}. " + self._restart_game()
        else:
            self.last_event = f"reconnected player: {nickname}. Waiting other disconnected players to reconnect..."

    def _restart_game(self):
        if self.turn is None:
            self.status = "LOBBY"
        else:
            self.status = "PLAYING"
        return "game restarted"

    def _execute_action_space(self, space: ActionSpace, player: Player):
        match space.name:
            case "start":
                return f"{player.nickname} is on START!"
            case "income tax":
                tax = 200
                if not player.pay(tax):
                    return self._player_bankruptcy("", player)
                return f"{player.nickname} paid {tax} for income tax."
            case "national insurance":
                tax = 150
                if not player.pay(tax):
                    return self._player_bankruptcy("", player)
                return f"{player.nickname} paid {tax} for national insurance."
            case "chance":
                card = choice(self.chance_cards)
                log = f"Chance! '{card}'."
                if "pay 150" in card:
                    if not player.pay(150):
                        return self._player_bankruptcy("", player)
                elif "pay 50" in card:
                    if not player.pay(50):
                        return self._player_bankruptcy("", player)
                elif "earn 100" in card:
                    player.get_paid(100)
                elif "earn 200" in card:
                    player.get_paid(200)
                return log
            case "community chest":
                card = choice(self.community_chest_cards)
                log = f"Community chest! '{card}'."
                if "pay 100" in card:
                    if not player.pay(100):
                        return self._player_bankruptcy("", player)
                elif "earn 200" in card:
                    player.get_paid(200)
                elif "START!" in card:
                    player.position = 0
                    player.get_paid(200)
                    log += " (+200)."
                return log
            case "go to jail":
                player.position = 10
                return f" {player.nickname} goes to jail!."
            case "jail" | "free parking":
                return f"{player.nickname} on {space.name}."
            case "rail station":
                price = 300
                if not player.pay(price):
                    return self._player_bankruptcy("", player)
                return f"{player.nickname} paid {price} for the train ticket."
            case "electric company":
                price = 150
                if not player.pay(price):
                    return self._player_bankruptcy("", player)
                return f"{player.nickname} paid {price} on electric company."
            case "water works":
                price = 150
                if not player.pay(price):
                    return self._player_bankruptcy("", player)
                return f"{player.nickname} paid {price} on water works."
            case _:
                return f"{space.name} non yet implemented."
