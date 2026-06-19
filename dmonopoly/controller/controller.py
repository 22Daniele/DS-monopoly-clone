from enum import Enum
import pygame
from model.monopoly import Monopoly
from view.monopoly_view import MonopolyView

class PlayerEvent(Enum):
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
        log = ""
        player = data.get("nickname", "Sconosciuto")
        match event:
            case PlayerEvent.JOIN:
                log = self._handle_join(player)
            case PlayerEvent.QUIT:
                log = self._handle_quit(player)
            case PlayerEvent.READY:
                log = self._handle_ready(player)
            case PlayerEvent.BUY:
                log = self._handle_buy(player)
            case PlayerEvent.BUILD:
                log = self._handle_build(player)
            case PlayerEvent.ROLL:
                log = self._handle_roll(player)
            case PlayerEvent.END_TURN:
                log = self._handle_end_turn()
        return self._create_event_update_state(f"Player {player}: {log}")

    def _create_event_update_state(self, event: str):
        state = self._game.get_state()
        state["last_event"] = event
        return state

    def _handle_join(self, nickname: str):
        return self._game.add_player(nickname)

    def _handle_quit(self, nickname: str):
        return self._game.remove_player(nickname)

    def _handle_build(self, nickname: str):
        return self._game.build_houses(nickname)

    def _handle_roll(self, nickname: str):
        return self._game.roll_dice(nickname)

    def _handle_end_turn(self):
        return self._game.next_turn()

    def _handle_buy(self, nickname: str):
        return self._game.buy_property(nickname)

    def _handle_ready(self, nickname: str):
        return self._game.player_ready(nickname)


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


