import sys
import pygame
from remote.bank_user import MonopolyUser


def main():
    if len(sys.argv) < 4:
        print("ERRORE: Parametri mancanti.")
        print("Uso corretto: monopoly-client <IP_SERVER> <PORTA> <NICKNAME>")
        sys.exit(1)

    host = sys.argv[1]

    try:
        port = int(sys.argv[2])
    except ValueError:
        print("ERRORE: La porta deve essere un numero intero.")
        sys.exit(1)

    nickname = sys.argv[3]

    pygame.init()
    print(f"Avvio di MonopolyClient...")
    print(f"Tentativo di connessione a: {host}:{port}...")

    try:
        client_app = MonopolyUser(nickname, (host, port))
        client_app.run()
    except Exception as e:
        print(f"Errore fatale del client: {e}")
    finally:
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()