from model.monopoly import *


class Serializer:
    primitives = [int, float, str, bool]
    containers = [list, tuple, set]

    def serialize(self, obj):
        return json.dumps(self._serialize(obj))

    def _serialize(self, obj):
        if obj is None:
            return None
        if any(isinstance(obj, primitive) for primitive in self.primitives):
            return self._serialize_primitive(obj)
        elif isinstance(obj, dict):
            return self._serialize_dict(obj)
        elif any(isinstance(obj, container) for container in self.containers):
            return self._serialize_iterable(obj)
        else:
            return self._serialize_any(obj)

    def _serialize_iterable(self, obj):
        return [self._serialize(item) for item in obj]

    def _serialize_dict(self, obj):
        return {key: self._serialize(value) for key, value in obj.items()}

    def _serialize_primitive(self, obj):
        return obj

    def _serialize_any(self, obj):
        for klass in type(obj).mro():
            method_name = f"_serialize_{klass.__name__.lower()}"
            if hasattr(self, method_name):
                return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Serialization for {type(obj).__name__} is not implemented")

    def _to_dict(self, obj, *attributes):
        data = {name : self._serialize(getattr(obj, name)) for name in attributes}
        data["$type"] = type(obj).__name__
        return data

    def _serialize_actionspace(self, space: ActionSpace):
        return self._to_dict(space, "name", "type")

    def _serialize_propertyspace(self, space: PropertySpace):
        return self._to_dict(space, "name", "price", "owner", "houses")

    def _serialize_board(self, board: Board):
        return self._to_dict(board, "spaces", "property_indexes")

    def _serialize_player(self, player: Player):
        return self._to_dict(player, "nickname", "position", "balance", "properties", "bankruptcy")

    def _serialize_monopoly(self, monopoly: Monopoly):
        return self._to_dict(
            monopoly,
            "status", "players", "waiting_for", "current_turn_nickname", "allowed_actions", "board",
            "turn", "players_ready", "has_rolled", "alive_players", "last_event"
        )

class Deserializer:
    def deserialize(self, input: str):
        return self._deserialize(json.loads(input))

    def _deserialize(self, obj):
        if isinstance(obj, dict):
            if "$type" in obj:
                return self._deserialize_any(obj)
            else:
                return {key: self._deserialize(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self._deserialize(item) for item in obj]
        return obj

    def _deserialize_any(self, obj):
        type_name = obj["$type"]
        method_name = f"_deserialize_{type_name.lower()}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Deserialization for {type_name} is not implemented")

    def _from_dict(self, obj: dict, *attributes):
        return [self._deserialize(obj[name]) for name in attributes]

    def _deserialize_actionspace(self, obj):
        return ActionSpace(*self._from_dict(obj, "name", "type"))

    def _deserialize_propertyspace(self, obj):
        space = PropertySpace(*self._from_dict(obj, "name", "price"))
        space.owner = self._deserialize(obj["owner"])
        space.houses = self._deserialize(obj["houses"])
        return space

    def _deserialize_board(self, obj):
        board = Board()
        board.spaces = self._deserialize(obj["spaces"])
        board.property_indexes = self._deserialize(obj["property_indexes"])
        return board

    def _deserialize_player(self, obj):
        player = Player(*self._from_dict(obj, "nickname"))
        player.bankruptcy = self._deserialize(obj["bankruptcy"])
        player.position = self._deserialize(obj["position"])
        player.balance = self._deserialize(obj["balance"])
        player.properties = self._deserialize(obj["properties"])
        return player

    def _deserialize_monopoly(self, obj):
        monopoly = Monopoly()
        monopoly.waiting_for = set(self._deserialize(obj["waiting_for"]))
        monopoly.players_ready = set(self._deserialize(obj["players_ready"]))
        monopoly.board = self._deserialize(obj["board"])
        monopoly.turn = self._deserialize(obj["turn"])
        monopoly.status = self._deserialize(obj["status"])
        monopoly.players = self._deserialize(obj["players"])
        monopoly.has_rolled = self._deserialize(obj["has_rolled"])
        monopoly.alive_players = self._deserialize(obj["alive_players"])
        monopoly.last_event = self._deserialize(obj["last_event"])
        return monopoly


DEFAULT_SERIALIZER = Serializer()
DEFAULT_DESERIALIZER = Deserializer()


def serialize(obj, serializer=DEFAULT_SERIALIZER):
    return serializer.serialize(obj)


def deserialize(input: str, deserializer=DEFAULT_DESERIALIZER):
    return deserializer.deserialize(input)
