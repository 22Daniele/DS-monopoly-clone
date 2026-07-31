from enum import Enum
import pygame
from checkpoint.checkpoint import *
from model.monopoly import Monopoly
from model.serializer_deserializer import serialize
from view.monopoly_view import MonopolyView

class PlayerEvent(Enum):
    RECONNECTION_TIMEOUT = "reconnection_timeout"
    DISCONNECTION = "disconnection"
    READY = "ready"
    JOIN = "join"
    QUIT = "quit"
    BUY = "buy"
    ROLL = "roll"
    BUILD = "build"
    END_TURN = "end_turn"

class ServerController:
    def __init__(self, game: Monopoly):
        self._game = game

    def handle_event(self, event: PlayerEvent, data: dict):
        player = data.get("nickname", "SISTEM")
        match event:
            case PlayerEvent.JOIN:
                self._handle_join(data)
            case PlayerEvent.QUIT:
                self._handle_quit(player)
            case PlayerEvent.READY:
                self._handle_ready(player)
            case PlayerEvent.BUY:
                self._handle_buy(player)
            case PlayerEvent.BUILD:
                self._handle_build(player)
            case PlayerEvent.ROLL:
                self._handle_roll(player)
            case PlayerEvent.END_TURN:
                self._handle_end_turn()
            case PlayerEvent.DISCONNECTION:
                self._handle_disconnection(player)
            case PlayerEvent.RECONNECTION_TIMEOUT:
                self._handle_reconnection_timeout()
        return serialize(self._game)

    def _handle_join(self, payload: dict):
        nickname = payload.get("nickname")
        if nickname in self._game.disconnected_players():
            self._game.reconnect_player(nickname)
        else:
            self._game.add_player(nickname)

    def _handle_quit(self, nickname: str):
        self._game.remove_player(nickname)

    def _handle_build(self, nickname: str):
        self._game.build_houses(nickname)

    def _handle_roll(self, nickname: str):
        self._game.roll_dice(nickname)

    def _handle_end_turn(self):
        self._game.next_turn()

    def _handle_buy(self, nickname: str):
        self._game.buy_property(nickname)

    def _handle_ready(self, nickname: str):
        self._game.player_ready(nickname)

    def _handle_disconnection(self, nickname: str):
        self._game.player_disconnection(nickname)

    def _handle_reconnection_timeout(self):
        self._game.reconnection_timeout()


class ClientController:
    def __init__(self, view: MonopolyView):
        self._view = view

    def handle_update_state(self, new_state: dict):
        self._view.set_game_state(new_state)

    def handle_input(self, event, nickname: str):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos, nickname)
        return None

    def _handle_click(self, pos, nickname: str):
        button_pressed = self._view.get_button(pos)
        if button_pressed == "ready":
            return {"type": "ready", "payload": {"nickname": nickname}}
        if button_pressed == "roll":
            return {"type": "roll", "payload": {"nickname": nickname}}
        elif button_pressed == "buy":
            return {"type": "buy", "payload": {"nickname": nickname}}
        elif button_pressed == "build":
            return {"type": "build", "payload": {"nickname": nickname}}
        elif button_pressed == "end_turn":
            return {"type": "end_turn", "payload": {"nickname": nickname}}
        return None


