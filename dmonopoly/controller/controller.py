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
                self._handle_join(player)
                log = "è entrato in partita."
            case PlayerEvent.QUIT:
                self._handle_quit(player)
                log = "ha abbandonato la partita."
            case PlayerEvent.READY:
                self._handle_ready(player)
                log = "è pronto"
            case PlayerEvent.BUY:
                prop = int(data.get("property", ""))
                self._handle_buy(player, prop)
                log = f"ha comprato la proprietà {prop}."
            case PlayerEvent.BUILD:
                prop = int(data.get("property", ""))
                qty = data.get("quantity", 0)
                self._handle_build(player, prop, qty)
                log = f"ha costruito {qty} case su {prop}."
            case PlayerEvent.ROLL:
                dice_result = self._handle_roll(player)
                log = f"ha tirato i dadi e ha fatto {dice_result}."
            case PlayerEvent.END_TURN:
                self._handle_end_turn()
                log = "ha terminato il turno."
        return self._create_event_update_state(f"Player {player}: {log}")

    def _create_event_update_state(self, event: str):
        state = self._game.get_state()
        state["last_event"] = event
        return state

    def _handle_join(self, nickname: str):
        self._game.add_player(nickname)

    def _handle_quit(self, nickname: str):
        self._game.remove_player(nickname)

    def _handle_build(self, nickname: str, property_idx: int, quantity):
        self._game.build_houses(nickname, property_idx, quantity)

    def _handle_roll(self, nickname: str):
        return self._game.roll_dice(nickname)

    def _handle_end_turn(self):
        self._game.next_turn()

    def _handle_buy(self, nickname: str, property_idx: int):
        self._game.buy_property(nickname, property_idx)

    def _handle_ready(self, nickname: str):
        self._game.player_ready(nickname)


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


