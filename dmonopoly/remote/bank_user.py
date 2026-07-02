import json
import time
import pygame
from checkpoint.checkpoint import load_checkpoint
from controller.controller import ClientController, ServerController, PlayerEvent
from model.monopoly import Monopoly
from model.serializer_deserializer import serialize
from remote import *
from view.monopoly_view import MonopolyView


class MonopolyBank:
    def __init__(self, port):
        self._running = True
        backup_game = load_checkpoint()
        self._reconnect_timer = None
        if backup_game:
            print("[SISTEMA] Checkpoint trovato! Ripristino della partita in corso...")
            self._game = backup_game
            self._reconnect_timer = threading.Timer(30.0, self._on_reconnect_timeout)
            self._reconnect_timer.start()
            print("[SISTEMA] Avviato timer di recupero server: 30 secondi per il rientro di tutti i giocatori.")
        else:
            print("[SISTEMA] Nessun checkpoint trovato. Creo una nuova partita.")
            self._game = Monopoly()
        self._controller = ServerController(self._game)
        self._server = Server(port, self.on_new_connection)
        self._peers: set[Connection] = set()
        self._connection_to_nickname = {}

    def on_message_received(self, event, payload, connection, error):
        if event == 'message':
            data = json.loads(payload)
            player_event = PlayerEvent(data["type"])
            if player_event == PlayerEvent.JOIN:
                nickname = data["payload"]["nickname"]
                is_reconnection = nickname in self._game.disconnected_players()
                if not is_reconnection:
                    if self._game.status != "LOBBY":
                        self._reject_connection(connection, "Game already started!")
                        return
                    if len(self._game.players) >= 4:
                        self._reject_connection(connection, "The lobby is full!")
                        return
                    if nickname in self._connection_to_nickname.values():
                        self._reject_connection(connection, "Nickname already in use!")
                        return
                self._connection_to_nickname[connection] = nickname
            self._send_all(self._controller.handle_event(player_event, data["payload"]))
            if self._game.status == "PLAYING" and self._reconnect_timer:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
                print("[SISTEMA] Tutti i giocatori superstiti sono rientrati. Timer di recupero annullato.")
        elif event in ('close', 'error'):
            print(f"[RETE] connessione persa: {error}")
            self._handle_player_disconnection(connection)

    def _reject_connection(self, connection, msg):
        rejection_msg = {"status": "REJECTED", "last_event": msg}
        self._send_state(connection, json.dumps(rejection_msg))
        if connection in self._peers:
            self._peers.remove(connection)
        connection.close()

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
                self._send_state(connection, serialize(self._game))
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

    def _send_state(self, connection, state):
        connection.send(state)

    def _send_all(self, state):
        for connection in self._peers:
            self._send_state(connection, state)

    def _handle_player_disconnection(self, connection):
        if connection in self._peers:
            self._peers.remove(connection)
        nickname = self._connection_to_nickname.pop(connection, None)
        if nickname:
            self._send_all(self._controller.handle_event(PlayerEvent.DISCONNECTION, {"nickname": nickname}))
            if self._game.status != "CLOSED":
                if self._reconnect_timer:
                    self._reconnect_timer.cancel()
                self._reconnect_timer = threading.Timer(30.0, self._on_reconnect_timeout)
                self._reconnect_timer.start()
                print("[SISTEMA] Timer di riconnessione da 30 secondi avviato...")
        self._check_auto_shutdown()

    def _on_reconnect_timeout(self):
        if self._game.running():
            return
        print("[SISTEMA] Tempo scaduto! Il giocatore non è rientrato. Continuo la partita senza di lui.")
        self._reconnect_timer = None
        self._send_all(self._controller.handle_event(PlayerEvent.RECONNECTION_TIMEOUT, {}))
        self._check_auto_shutdown()

    def _check_auto_shutdown(self):
        if self._game.status == "CLOSED" and len(self._peers) == 0:
            print("[SISTEMA] Partita terminata e nessun client connesso. Chiusura automatica del server...")
            self._running = False

class MonopolyUser:
    def __init__(self, nickname: str, address):
        self._nickname = nickname
        self._address = address
        self._running = True
        self._view = MonopolyView()
        self._controller = ClientController(self._view)
        self._client = Client(address, self.on_network_message)
        self._reconnecting = False
        self._last_reconnect_attempt = 0.0
        self._RECONNECT_INTERVAL = 3.0
        self._reconnect_start_time = 0.0
        self._MAX_RECONNECT_TIME = 90.0
        self._rejected = False

    def on_network_message(self, event, payload, connection, error):
        if event == 'message':
            state_dict = json.loads(payload)
            if state_dict.get("status") == "REJECTED":
                self._rejected = True
                msg = state_dict.get("last_event")
                print(f"[CLIENT] error: {msg}")
                self.stop()
                return
            self._controller.handle_update_state(state_dict)
        elif event in ('close', 'error'):
            if self._rejected:
                return
            if not self._reconnecting:
                print(f"[CLIENT] Connessione persa. Inizio tentativi di riconnessione...")
                self._reconnecting = True
                self._reconnect_start_time = time.time()
                if not self._client.closed:
                    self._client.close()
                self._controller.handle_update_state({"status": "SERVER_DOWN"})

    def run(self):
        self._send_join()
        while self._running:
            current_time = time.time()
            if self._reconnecting:
                passed_time = current_time - self._reconnect_start_time
                if passed_time > self._MAX_RECONNECT_TIME:
                    print(f"[CLIENT] Timeout raggiunto ({self._MAX_RECONNECT_TIME}s). Il server non è tornato online. Chiusura.")
                    self.stop()
                    break
                if current_time - self._last_reconnect_attempt > self._RECONNECT_INTERVAL:
                    self._last_reconnect_attempt = current_time
                    self._attempt_reconnection()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                elif not self._reconnecting:
                    action = self._controller.handle_input(event, self._nickname)
                    if action:
                        self._client.send(json.dumps(action))
            self._view.render(self._nickname)

    def _send_join(self):
        joining_event = {
            "type": "join",
            "payload": {"nickname": self._nickname}
        }
        self._client.send(json.dumps(joining_event))

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

    def _attempt_reconnection(self):
        print(f"[CLIENT] Tentativo di connessione a {self._address}...")
        try:
            self._client = Client(self._address, self.on_network_message)
            self._send_join()
            self._reconnecting = False
        except Exception as e:
            print(f"[CLIENT] Server non ancora raggiungibile.")