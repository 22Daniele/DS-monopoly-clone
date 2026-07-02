import os
import time
from model.serializer_deserializer import *

CHECKPOINT_DIR = "checkpointing"
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "autosave.json")
EXPIRATION_CHECKPOINT_TIMEOUT = 90.0

def save_checkpoint(game):
    """Serializza il gioco e lo salva su file."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            f.write(serialize(game))
    except IOError as e:
        print(f"[CHECKPOINT] Errore durante il salvataggio: {e}")

def load_checkpoint():
    """Se esiste il file, lo legge e lo deserializza. Altrimenti restituisce None."""
    if os.path.exists(CHECKPOINT_FILE):
        file_timestamp = os.path.getmtime(CHECKPOINT_FILE)
        current_time = time.time()
        age_in_seconds = current_time - file_timestamp
        if age_in_seconds > EXPIRATION_CHECKPOINT_TIMEOUT:
            print(f"[CHECKPOINT] Trovato un backup scaduto (vecchio di {int(age_in_seconds)}s). Eliminazione...")
            delete_checkpoint()
            return None

        try:
            with open(CHECKPOINT_FILE, "r") as f:
                game = deserialize(f.read())
                game.status = "PAUSED"
                game.waiting_for = {player.nickname for player in game.players if not player.bankruptcy}
                game.last_event = "Server riavviato. In attesa del rientro di tutti i giocatori..."
                return game
        except Exception as e:
            print(f"[CHECKPOINT] Impossibile caricare il backup: {e}")
            delete_checkpoint()
    return None

def delete_checkpoint():
    """Elimina il salvataggio a fine partita."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)