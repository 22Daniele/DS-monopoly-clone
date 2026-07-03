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
    print(f"  AVVIO MONOPOLY SERVER (PORTA {args.port})")
    print(f"=======================================\n")

    try:
        server_app = MonopolyBank(args.port)
        server_app.run()
    except KeyboardInterrupt:
        print("\n[SISTEMA] Interruzione manuale (Ctrl+C). Arresto in corso...")
    except Exception as e:
        print(f"[ERRORE FATALE] Il server ha crashato: {e}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()