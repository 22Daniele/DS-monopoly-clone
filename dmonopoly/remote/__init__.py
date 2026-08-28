import threading
import socket
import psutil
from datetime import datetime

def address(ip='0.0.0.0:0', port=None):
    ip = ip.strip()
    if ':' in ip:
        ip, p = ip.split(':')
        p = int(p)
        port = port or p
    if port is None:
        port = 0
    assert port in range(0, 65536), "Port number must be in the range 0-65535"
    assert isinstance(ip, str), "IP address must be a string"
    return ip, port


def message(text: str, sender: str, timestamp: datetime=None):
    if timestamp is None:
        timestamp = datetime.now()
    return f"[{timestamp.isoformat()}] {sender}:\n\t{text}"


def local_ips():
    for interface in psutil.net_if_addrs().values():
        for addr in interface:
            if addr.family == socket.AF_INET:
                    yield addr.address


class Connection:
    def __init__(self, socket: socket.socket, callback=None):
        self.__socket = socket
        self.local_address = self.__socket.getsockname()
        self.remote_address = self.__socket.getpeername()
        self.__notify_closed = False
        self.__callback = callback
        self.__receiver_thread = threading.Thread(target=self.__handle_incoming_messages, daemon=True)
        if self.__callback:
            self.__receiver_thread.start()

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)

    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__receiver_thread.start()

    @property
    def closed(self):
        return self.__socket._closed

    def send(self, message):
        if not isinstance(message, bytes):
            message = message.encode()
            message = int.to_bytes(len(message), 4, 'big') + message
        self.__socket.sendall(message)

    def receive(self):
        def rcvall(n):
            data = bytearray()
            while len(data) < n:
                packet = self.__socket.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            return bytes(data)
        length_bytes = rcvall(4)
        if not length_bytes:
            return None
        length = int.from_bytes(length_bytes, 'big')
        if length == 0:
            return None
        payload = rcvall(length)
        if not payload:
            return None
        return payload.decode('utf-8')

    def close(self):
        self.__socket.close()
        if not self.__notify_closed:
            self.__notify_closed = True
            self.on_event('close')


    def __handle_incoming_messages(self):
        try:
            self.__socket.settimeout(5.0)
            while not self.closed:
                message = self.receive()
                if message is None:
                    break
                self.on_event('message', message)
        except (socket.timeout, TimeoutError):
            self.on_event('error', error=TimeoutError("Network partition detected (timeout)"))
        except Exception as e:
            if self.closed and isinstance(e, OSError):
                return
            self.on_event('error', error=e)
        finally:
            self.close()

    def on_event(self, event: str, payload: str = None, connection: 'Connection' = None, error: Exception = None):
        if connection is None:
            connection = self
        self.callback(event, payload, connection, error)


class Client(Connection):
    def __init__(self, server_address, callback=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(address(port=0))
        sock.connect(address(*server_address))
        super().__init__(sock, callback)


class Server:
    def __init__(self, port, callback=None):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind(address(port=port))
        self.__listener_thread = threading.Thread(target=self.__handle_incoming_connections, daemon=True)
        self.__callback = callback
        if self.__callback:
            self.__listener_thread.start()

    @property
    def callback(self):
        return self.__callback or (lambda *_: None)

    @callback.setter
    def callback(self, value):
        if self.__callback:
            raise ValueError("Callback can only be set once")
        self.__callback = value
        if value:
            self.__listener_thread.start()

    def __handle_incoming_connections(self):
        self.__socket.listen(4)
        self.on_event('listen', address=self.__socket.getsockname())
        try:
            while not self.__socket._closed:
                socket, address = self.__socket.accept()
                connection = Connection(socket)
                self.on_event('connect', connection, address)
        except OSError:
            pass
        except ConnectionAbortedError as e:
            pass
        except Exception as e:
            self.on_event('error', error=e)
        finally:
            self.on_event('stop')

    def on_event(self, event: str, connection: Connection = None, address: tuple = None, error: Exception = None):
        self.callback(event, connection, address, error)

    def close(self):
        self.__socket.close()
