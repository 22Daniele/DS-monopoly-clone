import pytest
from unittest.mock import patch
from model.monopoly import Monopoly

@pytest.fixture
def started_game():
    game = Monopoly()
    game.add_player("Alice")
    game.add_player("Bob")
    game.player_ready("Alice")
    game.player_ready("Bob")
    return game


def test_game_initialization(started_game: Monopoly):
    """Testa che il gioco si avvii correttamente con le statistiche giuste."""
    assert started_game.status == "PLAYING"
    assert started_game.alive_players == 2
    assert started_game.turn == 0
    assert started_game.current_turn_nickname == "Alice"

    alice = started_game._get_player("Alice")
    assert alice.balance == 5000
    assert len(alice.get_properties()) == Monopoly.STARTING_PROPERTIES

def test_lobby_start_conditions():
    """Testa che il gioco non parta con meno di 2 giocatori."""
    game = Monopoly()
    game.add_player("Alice")

    # Alice clicca ready, ma è da sola
    game.player_ready("Alice")

    assert game.status == "LOBBY"

    game.add_player("Bob")
    game.player_ready("Bob")

    assert game.status == "PLAYING"

def test_turn_enforcement(started_game: Monopoly):
    """Testa che un giocatore non possa agire fuori dal suo turno."""
    started_game.roll_dice("Bob")
    assert started_game.has_rolled == False
    assert "error" in started_game.last_event.lower()

def test_roll_and_allowed_actions(started_game: Monopoly):
    """Testa il flusso di un turno (tiro e fine turno)."""
    assert "roll" in started_game.allowed_actions
    assert "end_turn" not in started_game.allowed_actions
    started_game.roll_dice("Alice")
    assert started_game.has_rolled == True
    assert "roll" not in started_game.allowed_actions
    assert "end_turn" in started_game.allowed_actions
    started_game.next_turn("Alice")
    assert started_game.current_turn_nickname == "Bob"
    assert started_game.has_rolled == False

def test_buy_property_and_rent(started_game: Monopoly):
    """Testa l'acquisto di una proprietà e il pagamento dell'affitto usando dadi truccati."""
    alice = started_game._get_player("Alice")
    bob = started_game._get_player("Bob")

    # Sostituiamo il generatore random di Alice e Bob
    # con una funzione finta che restituisce sempre 1, non importa quali parametri riceva.
    alice._random.randint = lambda a, b: 1
    bob._random.randint = lambda a, b: 1

    # Rimuoviamo le proprietà casuali iniziali per avere un test pulito
    alice.properties.clear()
    bob.properties.clear()
    space = started_game.board.get_space(1)
    space.remove_owner()

    # Turno 1: Alice tira.
    # Il dado varrà 1, quindi si sposterà correttamente sulla casella 1.
    started_game.roll_dice("Alice")
    initial_balance = alice.balance

    assert "buy" in started_game.allowed_actions
    started_game.buy_property("Alice")

    assert alice.balance == initial_balance - space.price
    assert started_game.board.get_property_owner(1) == "Alice"

    started_game.next_turn("Alice")

    # Turno 2: Bob tira e finisce sulla proprietà di Alice (casella 1)
    bob_initial_balance = bob.balance
    alice_balance_before_rent = alice.balance

    started_game.roll_dice("Bob")

    # Bob deve aver pagato l'affitto ad Alice
    assert bob.balance == bob_initial_balance - space.price
    assert alice.balance == alice_balance_before_rent + space.price

def test_build_houses(started_game: Monopoly):
    """Testa la logica di costruzione delle case."""
    alice = started_game._get_player("Alice")

    # Setup: Alice possiede la casella 1 e si trova lì
    space = started_game.board.get_space(1)
    space.assign("Alice")
    alice.properties.append(1)
    alice.position = 1

    # Forza lo stato in modo che Alice possa costruire (ha già tirato i dadi)
    started_game.has_rolled = True
    initial_balance = alice.balance

    assert "build" in started_game.allowed_actions

    # Costruiamo la prima casa
    started_game.build_houses("Alice")

    assert space.houses == 1
    assert alice.balance == initial_balance - 50
    assert "Alice build the 1th house" in started_game.last_event

    # Costruiamo altre 4 case per arrivare al limite
    for _ in range(4):
        started_game.build_houses("Alice")

    assert space.houses == 5

    # Proviamo a costruire la sesta casa (dovrebbe fallire)
    started_game.build_houses("Alice")
    assert space.houses == 5
    assert "can't build more than 5 houses" in started_game.last_event

def test_action_spaces(started_game: Monopoly):
    """Testa gli effetti delle caselle speciali come Tasse e Prigione."""
    alice = started_game._get_player("Alice")

    # Test 1: Income Tax (Tassa di reddito)
    tax_index = 4

    alice.position = tax_index
    initial_balance = alice.balance

    # Eseguiamo l'azione della casella
    log = started_game._space_action(tax_index, alice)

    assert alice.balance == initial_balance - 200
    assert "paid 200 for income tax" in log

    # Test 2: Go to Jail (Vai in prigione)
    jail_index = 30

    alice.position = jail_index
    log = started_game._space_action(jail_index, alice)

    assert alice.position == 10
    assert "goes to jail" in log

def test_bankruptcy_and_win(started_game: Monopoly):
    """Testa l'eliminazione di un giocatore e la chiusura della partita."""
    bob = started_game._get_player("Bob")

    # Mandiamo Bob in bancarotta forzatamente
    bob.balance = 0
    bob.pay(100)  # Cerca di pagare ma non ha soldi

    assert bob.bankruptcy == True

    # Simula la fine causata dalla bancarotta
    started_game._player_bankruptcy("Bob lost", bob)

    assert started_game.alive_players == 1
    assert started_game.status == "CLOSED"

def test_remove_player_turn_shift():
    """Testa la liberazione delle proprietà e l'aggiustamento dei turni quando qualcuno quitta."""
    game = Monopoly()
    for p in ["Alice", "Bob", "Charlie"]:
        game.add_player(p)
        game.player_ready(p)

    # Assegniamo manualmente la casella 1 a Bob per vedere se viene liberata
    bob = game._get_player("Bob")
    space = game.board.get_space(1)
    space.assign("Bob")
    bob.properties.append(1)

    # Passiamo il turno ad Alice, ora tocca a Bob (indice 1)
    game.next_turn("Alice")
    assert game.current_turn_nickname == "Bob"

    # Bob abbandona la partita durante il suo turno!
    game.remove_player("Bob")

    assert len(game.players) == 2
    assert space.owner == ""

    # L'indice del turno (1) ora deve puntare a Charlie, non andare fuori scala
    assert game.turn == 1
    assert game.current_turn_nickname == "Charlie"

def test_disconnection_and_reconnection(started_game: Monopoly):
    """Testa che il gioco vada in pausa se un giocatore si disconnette e riprenda alla riconnessione."""
    started_game.player_disconnection("Bob")

    assert started_game.status == "PAUSED"
    assert "Bob" in started_game.disconnected_players()

    started_game.reconnect_player("Bob")

    assert started_game.status == "PLAYING"
    assert "Bob" not in started_game.disconnected_players()

