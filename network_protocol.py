"""
Упрощенный протокол для ментального покера
"""

import json
from enum import Enum

class MessageType(Enum):
    # Системные
    WELCOME = "welcome"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

    # Управление игрой
    CREATE_GAME = "create_game"
    GAME_CREATED = "game_created"
    JOIN_GAME = "join_game"
    GAME_JOINED = "game_joined"
    PLAYER_READY = "player_ready"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    GAME_CAN_START = "game_can_start"

    # Игровой процесс
    GAME_STARTED = "game_started"
    GAME_STATE = "game_state"
    PLAYER_ACTION = "player_action"

    # Чат
    CHAT_MESSAGE = "chat_message"

def create_message(msg_type, **kwargs):
    """Создание сообщения"""
    message = {'type': msg_type.value if isinstance(msg_type, Enum) else msg_type}
    message.update(kwargs)
    return message

def message_to_json(message):
    """Преобразование сообщения в JSON"""
    return json.dumps(message)

def json_to_message(json_str):
    """Преобразование JSON в сообщение"""
    return json.loads(json_str)
