import json
import time

import pygame

from controller.controller import ClientController, ServerController, PlayerEvent
from model.monopoly import Monopoly
from remote import *
from view.monopoly_view import MonopolyView


class MonopolyBank:
    def __init__(self, port):
        self._running = True
        self._game = Monopoly()
        self._controller = ServerController(self._game)
        self._server = Server(port, self.on_new_connection)
        self._peers: set[Connection] = set()

    def on_message_received(self, event, payload, connection, error):
        if event == 'message':
            data = json.loads(payload)
            #deserializza l'evento in eventPlayer
            player_event = PlayerEvent(data["type"])
            self._send_all(self._controller.handle_event(player_event, data["payload"]))

    def on_new_connection(self, event, connection, address, error):
        match event:
            case 'listen':
                print(f"Server listening on port {address[0]} at {', '.join(local_ips())}")
            case 'connect':
                print(f"Open ingoing connection from: {address}")
                connection.callback = self.on_message_received
                self._peers.add(connection)
                #aggiungi player al game
                #self._controller.handle_event(event, connection)
                self._send_state(connection, self._game.get_state())
            case 'stop':
                print(f"Stop listening for new connections")
            case 'error':
                print(error)
                #self._send_all(error)

    def run(self):
        print("Server in esecuzione. In attesa di client...")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Chiusura del server in corso...")
        finally:
            self._server.close()

    def _send_state(self, connection, state: dict):
        connection.send(json.dumps(state))

    def _send_all(self, state: dict):
        for connection in self._peers:
            self._send_state(connection, state)


class MonopolyUser:
    def __init__(self, nickname: str, address):
        self._nickname = nickname
        self._running = True
        self._view = MonopolyView()
        self._controller = ClientController(self._view)
        self._client = Client(address, self.on_network_message)

    def on_network_message(self, event, payload, connection, error):
        if event == 'message':
            state_dict = json.loads(payload)
            self._controller.handle_update_state(state_dict)
        elif event in ('close', 'error'):
            print(f"Connessione col server persa: {error}")
            self.stop()

    def run(self):
        joining_event = {
            "type": "join",
            "payload": {"nickname": self._nickname}
        }
        self._client.send(json.dumps(joining_event))
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                else:
                    action = self._controller.handle_input(event, self._nickname)
                    if action:
                        self._client.send(json.dumps(action))
            self._view.render(self._nickname)

    def stop(self):
        if not self._running:
            return
        print("Chiusura del client...")
        self._running = False
        if not self._client.closed:
            try:
                quit_msg = {
                    "type": "quit",
                    "payload": {"nickname": self._nickname}
                }
                self._client.send(json.dumps(quit_msg))
            except OSError:
                pass
        self._client.close()
        pygame.quit()