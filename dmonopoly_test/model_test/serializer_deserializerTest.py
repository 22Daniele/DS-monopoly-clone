import pytest
from model.monopoly import Monopoly, Player, PropertySpace, ActionSpace
from model.serializer_deserializer import serialize, deserialize


def test_serialize_deserialize_player():
    """Testa la simmetria della serializzazione per un singolo Giocatore."""
    # Setup di un giocatore con statistiche modificate
    p1 = Player("Alice")
    p1.balance = 2500
    p1.position = 7
    p1.properties = [1, 3, 5]
    p1.bankruptcy = False

    # Round-trip: Serializza e poi Deserializza
    json_data = serialize(p1)
    p2 = deserialize(json_data)

    # Verifiche
    assert isinstance(json_data, str)
    assert p2.nickname == p1.nickname
    assert p2.balance == p1.balance
    assert p2.position == p1.position
    assert p2.properties == p1.properties
    assert p2.bankruptcy == p1.bankruptcy


def test_serialize_deserialize_spaces():
    """Testa la simmetria per le caselle del tabellone."""
    # Test PropertySpace
    prop1 = PropertySpace("Park Place", 350)
    prop1.assign("Bob")
    prop1.houses = 3

    prop2 = deserialize(serialize(prop1))
    assert prop2.name == prop1.name
    assert prop2.price == prop1.price
    assert prop2.owner == prop1.owner
    assert prop2.houses == prop1.houses

    # Test ActionSpace
    act1 = ActionSpace("chance")
    act2 = deserialize(serialize(act1))
    assert act2.name == act1.name


def test_serialize_deserialize_full_game():
    """Il sull'intero stato di gioco in esecuzione."""
    game1 = Monopoly()
    game1.add_player("Alice")
    game1.add_player("Bob")
    game1.player_ready("Alice")
    game1.player_ready("Bob")

    # Modifichiamo pesantemente lo stato per allontanarci dai valori di default
    game1.turn = 1
    game1.has_rolled = True
    game1.last_event = "Alice landed on Chance"
    game1.waiting_for.add("Charlie")  # Simuliamo un disconnesso

    # Assegniamo una proprietà in più e costruiamo case
    space = game1.board.get_space(1)
    space.assign("Bob")
    space.houses = 4
    game1.players[1].add_property(1)  # Bob è all'indice 1
    expected_bob_properties = list(game1.players[1].properties)

    # Eseguiamo il Round-trip
    json_string = serialize(game1)
    game2 = deserialize(json_string)

    # 1. Verifica degli attributi base del gioco
    assert game2.status == game1.status
    assert game2.turn == game1.turn
    assert game2.has_rolled == game1.has_rolled
    assert game2.last_event == game1.last_event
    assert game2.waiting_for == game1.waiting_for

    # 2. Verifica del mantenimento dei giocatori
    assert len(game2.players) == 2
    assert game2.players[1].nickname == "Bob"
    assert game2.players[1].properties == expected_bob_properties

    # 3. Verifica del deep-state del tabellone (Le case e i proprietari)
    space2 = game2.board.get_space(1)
    assert space2.owner == "Bob"
    assert space2.houses == 4

    # 4. Verifica delle proprietà calcolate (es. turn_nickname)
    assert game2.current_turn_nickname == "Bob"


def test_unsupported_serialization():
    """Verifica che il sistema sollevi un errore corretto se gli diamo un oggetto sconosciuto."""

    class UnknownClass:
        pass

    dummy = UnknownClass()

    with pytest.raises(NotImplementedError) as excinfo:
        serialize(dummy)

    assert "Serialization for UnknownClass is not implemented" in str(excinfo.value)


def test_unsupported_deserialization():
    """Verifica che il sistema sollevi un errore se il JSON ha un $type sconosciuto."""
    bad_json = '{"$type": "Ufo", "data": "123"}'

    with pytest.raises(NotImplementedError) as excinfo:
        deserialize(bad_json)

    assert "Deserialization for Ufo is not implemented" in str(excinfo.value)