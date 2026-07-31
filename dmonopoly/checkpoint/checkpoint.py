import time
from model.serializer_deserializer import *

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "checkpointing")
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "autosave.json")
EXPIRATION_CHECKPOINT_TIMEOUT = 90.0

def save_checkpoint(game, player_tokens):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    try:
        game_data = json.loads(serialize(game))

        data_to_save = {
            "game": game_data,
            "tokens": player_tokens
        }

        with open(CHECKPOINT_FILE, "w") as f:
            # json.dump scrive l'involucro formattato nel file
            json.dump(data_to_save, f)
    except IOError as e:
        print(f"[CHECKPOINT] An error occurred while saving the backup: {e}")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        file_timestamp = os.path.getmtime(CHECKPOINT_FILE)
        current_time = time.time()
        age_in_seconds = current_time - file_timestamp
        if age_in_seconds > EXPIRATION_CHECKPOINT_TIMEOUT:
            print(f"[CHECKPOINT] Found an expired backup (old by {int(age_in_seconds)}s). Eliminating it...")
            delete_checkpoint()
            return None
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                data = json.load(f)
                game_string = json.dumps(data["game"])
                game = deserialize(game_string)
                player_tokens = data.get("tokens", {})

                game.status = "PAUSED"
                game.waiting_for = {player.nickname for player in game.players if not player.bankruptcy}
                game.last_event = "Server restarted. Waiting for the players..."
                return game, player_tokens
        except Exception as e:
            print(f"[CHECKPOINT] An error occurred while loading the backup: {e}")
            delete_checkpoint()
    return None

def delete_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)