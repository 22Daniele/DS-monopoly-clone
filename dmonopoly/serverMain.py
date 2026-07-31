import argparse
import sys
from remote.bank_user import MonopolyBank


def main():
    # Gestione elegante degli argomenti da terminale
    parser = argparse.ArgumentParser(description="Avvia il Server (Banca) di Monopoly")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="La porta TCP su cui il server starà in ascolto (default: 8080)"
    )

    args = parser.parse_args()

    print(f"=======================================")
    print(f"  STARTING MONOPOLY SERVER (PORT {args.port})")
    print(f"=======================================\n")

    try:
        server_app = MonopolyBank(args.port)
        server_app.run()
    except KeyboardInterrupt:
        print("\n[SISTEM] Manual interruption (Ctrl+C). Closing...")
    except Exception as e:
        print(f"[FATAL ERROR] Server crushed: {e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()