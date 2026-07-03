import sys
import pygame
from remote.bank_user import MonopolyUser

if __name__ == "__main__":
    # 1. Controllo degli argomenti da terminale
    if len(sys.argv) < 4:
        print("ERRORE: Parametri mancanti.")
        print("Uso corretto: python client_main.py <IP_SERVER> <PORTA> <NICKNAME>")
        print("Esempio: python client_main.py 192.168.1.5 5000 Daniele")
        sys.exit(1)

    host = sys.argv[1]

    try:
        port = int(sys.argv[2])
    except ValueError:
        print("ERRORE: La porta deve essere un numero intero.")
        sys.exit(1)

    nickname = sys.argv[3]

    # 2. Inizializzazione del motore grafico
    pygame.init()

    print(f"Avvio di MonopolyClient...")
    print(f"Giocatore: {nickname}")
    print(f"Tentativo di connessione a: {host}:{port}...")

    # 3. Creazione e avvio del Client
    try:
        client_app = MonopolyUser(nickname, (host, port))
        client_app.run()
    except Exception as e:
        print(f"Errore fatale del client: {e}")
    finally:
        # Assicura una chiusura pulita se qualcosa va storto fuori dal loop
        pygame.quit()
        sys.exit(0)