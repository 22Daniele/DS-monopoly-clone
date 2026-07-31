import sys
import pygame
from remote.bank_user import MonopolyUser


def main():
    if len(sys.argv) < 4:
        print("ERROR: Missing parameters.")
        print("Corrected usage: monopoly-client <SERVER_IP> <PORT> <NICKNAME>")
        sys.exit(1)

    host = sys.argv[1]

    try:
        port = int(sys.argv[2])
    except ValueError:
        print("ERROR: The port must be an integer.")
        sys.exit(1)

    nickname = sys.argv[3]

    pygame.init()
    print(f"Starting MonopolyClient...")
    print(f"Trying connection to: {host}:{port}...")

    try:
        client_app = MonopolyUser(nickname, (host, port))
        client_app.run()
    except Exception as e:
        print(f"Client's fatal error: {e}")
    finally:
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()