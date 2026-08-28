import uuid

from checkpoint.checkpoint import *
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
            print("[SYSTEM] Checkpoint found! Restoring game...")
            self._game, self._player_tokens = backup_game
            self._reconnect_timer = threading.Timer(30.0, self._on_reconnect_timeout)
            self._reconnect_timer.start()
            print("[SYSTEM] Timer started: waiting disconnected players for 30 seconds...")
        else:
            print("[SYSTEM] No checkpoint found. Creating a new game...")
            self._game = Monopoly()
            self._player_tokens = {}
        self._controller = ServerController(self._game)
        self._server = Server(port, self.on_new_connection)
        self._peers: set[Connection] = set()
        self._connection_to_nickname = {}


    def on_message_received(self, event, payload, connection, error):
        if event == 'message':
            data = json.loads(payload)
            if data.get("type") == "ping":
                try:
                    connection.send(json.dumps({"type": "pong"}))
                except OSError:
                    pass
                return
            player_event = PlayerEvent(data["type"])
            if player_event == PlayerEvent.JOIN:
                nickname = data["payload"]["nickname"]
                token = data["payload"].get("token", "")
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
                    self._player_tokens[nickname] = token
                else:
                    expected_token = self._player_tokens.get(nickname)
                    if expected_token and expected_token != token:
                        print(f"[SYSTEM] Access denied fo '{nickname}'! Wrong token.")
                        self._reject_connection(connection, "Reconnection failed: Token not valid!")
                        return
                    print(f"[SYSTEM] Authentication succeeded for '{nickname}'.")
                self._connection_to_nickname[connection] = nickname
            self._update_save_and_broadcast(player_event, data["payload"])
            if self._game.status == "PLAYING" and self._reconnect_timer:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
                print("[SYSTEM] All the player are back. Reconnection timer cancelled.")
        elif event in ('close', 'error'):
            print(f"[NETWORK] connection lost: {error}")
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
                print(f"Server listening on port {address[1]} at {', '.join(local_ips())}")
            case 'connect':
                print(f"Open ingoing connection from: {address}")
                connection.callback = self.on_message_received
                self._peers.add(connection)
                self._send_state(connection, serialize(self._game))
            case 'stop':
                print(f"Stop listening for new connections")
            case 'error':
                print(error)

    def run(self):
        print("Server started. Waiting for clients...")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Closing server...")
        finally:
            self._server.close()

    def _send_state(self, connection, state):
        connection.send(state)

    def _send_all(self, state):
        for connection in list(self._peers):
            self._send_state(connection, state)

    def _handle_player_disconnection(self, connection):
        if connection in self._peers:
            self._peers.remove(connection)
        nickname = self._connection_to_nickname.pop(connection, None)
        if nickname:
            self._update_save_and_broadcast(PlayerEvent.DISCONNECTION, {"nickname": nickname})
            if self._game.status != "CLOSED":
                if self._reconnect_timer:
                    self._reconnect_timer.cancel()
                timeout_duration = 90.0 if len(self._peers) == 0 else 30.0
                self._reconnect_timer = threading.Timer(timeout_duration, self._on_reconnect_timeout)
                self._reconnect_timer.start()
                print(f"[SYSTEM] Reconnection timer of {timeout_duration} seconds started...")
        self._check_auto_shutdown()

    def _on_reconnect_timeout(self):
        if self._game.running():
            return
        print("[SYSTEM] Time's up! The player has not reconnected. Game continues without him.")
        self._reconnect_timer = None
        self._update_save_and_broadcast(PlayerEvent.RECONNECTION_TIMEOUT, {})
        self._check_auto_shutdown()

    def _check_auto_shutdown(self):
        if self._game.status == "CLOSED" and len(self._peers) == 0:
            print("[SYSTEM] Game ended and all clients disconnected. Automatically closing the server...")
            self._running = False

    def _update_save_and_broadcast(self, event: PlayerEvent, payload: dict):
        new_state_json = self._controller.handle_event(event, payload)
        if self._game.status == "CLOSED":
            delete_checkpoint()
        else:
            save_checkpoint(self._game, self._player_tokens)
        self._send_all(new_state_json)

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
        self._token = self._get_or_create_token()
        self._last_ping_time = time.time()

    def on_network_message(self, event, payload, connection, error):
        if event == 'message':
            state_dict = json.loads(payload)
            if state_dict.get("type") == "pong":
                return
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
                print(f"[CLIENT] Connection lost. Starting reconnection attempts...")
                self._reconnecting = True
                self._reconnect_start_time = time.time()
                if not self._client.closed:
                    self._client.close()
                self._controller.handle_update_state({"status": "SERVER_DOWN"})

    def run(self):
        self._send_join()
        while self._running:
            current_time = time.time()
            if not self._reconnecting and not self._client.closed:
                if current_time - self._last_ping_time > 2.0:
                    self._last_ping_time = current_time
                    try:
                        self._client.send(json.dumps({"type": "ping"}))
                    except OSError:
                        pass
            if self._reconnecting:
                passed_time = current_time - self._reconnect_start_time
                if passed_time > self._MAX_RECONNECT_TIME:
                    print(f"[CLIENT] Timeout reached ({self._MAX_RECONNECT_TIME}s). The server is still offline. Closing...")
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
            "payload": {"nickname": self._nickname,
            "token": self._token}
        }
        self._client.send(json.dumps(joining_event))

    def stop(self):
        if not self._running:
            return
        print("Closing client...")
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
        print(f"[CLIENT] Reconnection attempt to {self._address}...")
        try:
            self._client = Client(self._address, self.on_network_message)
            self._send_join()
            self._reconnecting = False
        except Exception as e:
            print(f"[CLIENT] Server is still unreachable.")

    def _get_or_create_token(self):
        tokens_dir = "tokens"
        token_file = os.path.join(tokens_dir, f"{self._nickname}_token.txt")
        if not os.path.exists(tokens_dir):
            os.makedirs(tokens_dir)
        if os.path.exists(token_file):
            with open(token_file, "r") as f:
                return f.read().strip()
        new_token = str(uuid.uuid4())
        with open(token_file, "w") as f:
            f.write(new_token)
        return new_token