# Подробный план реализации проекта "Ментальный покер"

## 1. Анализ требований и проектирование

### 1.1 Функциональные требования
- ✅ Поддержка произвольного числа игроков (2-10)
- ✅ Поддержка стандартной колоды из 52 карт
- ✅ Реализация протокола ментального покера
- ✅ Графический интерфейс для игроков
- ✅ Клиент-серверная архитектура
- ✅ Поддержка правил Техасского Холдема
- ✅ Система чата между игроками
- ✅ Механизм ставок и управления игрой
- ✅ Возможность аудита и проверки честности

### 1.2 Нефункциональные требования
- ✅ Безопасность: криптографическая защита карт
- ✅ Производительность: поддержка реального времени
- ✅ Масштабируемость: произвольное число игроков
- ✅ Надежность: обработка отключений клиентов
- ✅ Юзабилити: интуитивный интерфейс

## 2. Архитектурное проектирование

### 2.1 Системная архитектура
```
┌─────────┐    ┌────────────┐    ┌─────────┐
│ Клиент 1│◄──►│   Сервер   │◄──►│ Клиент N│
└─────────┘    └────────────┘    └─────────┘
     │               │                 │
     └───┐       ┌───┴───┐       ┌─────┘
         │       │       │       │
     ┌───┴───┐ ┌─┴─┐ ┌───┴───┐ ┌─┴─┐
     │  GUI  │ │СУБД│ │Протокол│ │...│
     └───────┘ └───┘ └───────┘ └───┘
```

### 2.2 Компонентная архитектура

#### Серверные компоненты:
- **GameServer** - основной сервер
- **SessionManager** - управление игровыми сессиями
- **PlayerManager** - управление игроками
- **CryptoValidator** - проверка криптографических операций
- **MessageRouter** - маршрутизация сообщений

#### Клиентские компоненты:
- **PokerClient** - сетевой клиент
- **GameGUI** - графический интерфейс
- **CryptoEngine** - криптографические операции
- **DeckManager** - управление колодой

## 3. Детальная реализация по этапам

### Этап 1: Базовая инфраструктура

#### 3.1.1 Настройка проекта и структуры
```python
# Структура проекта
mental_poker/
├── docs/                    # Документация
├── server/                  # Серверная часть
│   ├── core/               # Основные модули
│   ├── protocols/          # Игровые протоколы
│   ├── crypto/             # Криптография
│   └── tests/              # Тесты сервера
├── client/                 # Клиентская часть
│   ├── gui/               # Графический интерфейс
│   ├── network/           # Сетевое взаимодействие
│   ├── crypto/            # Криптография клиента
│   └── tests/             # Тесты клиента
├── shared/                 # Общие модули
│   ├── protocol/          # Сетевой протокол
│   ├── crypto/            # Общие крипто-функции
│   └── constants/         # Константы
└── deployment/            # Деплоймент
```

#### 3.1.2 Базовый сетевой протокол
```python
# shared/protocol/message_types.py
from enum import Enum

class MessageType(Enum):
    # Управление соединением
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    
    # Управление игрой
    CREATE_SESSION = "create_session"
    JOIN_SESSION = "join_session"
    LEAVE_SESSION = "leave_session"
    START_GAME = "start_game"
    
    # Ментальный покер
    INIT_DECK = "init_deck"
    ENCRYPT_DECK = "encrypt_deck"
    SELECT_CARD = "select_card"
    PARTIAL_DECRYPT = "partial_decrypt"
    
    # Игровой процесс
    BET = "bet"
    FOLD = "fold"
    CHECK = "check"
    RAISE = "raise"
    
    # Чат
    CHAT_MESSAGE = "chat_message"
    
    # Аудит
    VERIFY_GAME = "verify_game"
```

### Этап 2: Криптографический движок

#### 3.2.1 Реализация базовых криптографических примитивов
```python
# shared/crypto/mental_poker.py
import random
import math
from sympy import isprime, mod_inverse
from shared.crypto.primes import generate_large_prime

class MentalPokerCrypto:
    def __init__(self, prime_bits=1024):
        self.p = generate_large_prime(prime_bits)
        self.prime_bits = prime_bits
    
    def generate_key_pair(self):
        """Генерация пары ключей для игрока"""
        while True:
            c = random.randint(2, self.p - 2)
            if math.gcd(c, self.p - 1) == 1:
                d = mod_inverse(c, self.p - 1)
                return {'encrypt_key': c, 'decrypt_key': d}
    
    def encrypt_card(self, card, key):
        """Шифрование карты"""
        return pow(card, key, self.p)
    
    def decrypt_card(self, encrypted_card, key):
        """Расшифрование карты"""
        return pow(encrypted_card, key, self.p)
    
    def create_deck(self, num_cards=52):
        """Создание колоды уникальных карт"""
        deck = []
        used = set()
        
        while len(deck) < num_cards:
            card = random.randint(2, self.p - 1)
            if card not in used:
                deck.append(card)
                used.add(card)
        
        return deck
```

#### 3.2.2 Протокол ментального покера для N игроков
```python
# server/protocols/poker_protocol.py
class MentalPokerProtocol:
    def __init__(self, num_players, crypto_engine):
        self.num_players = num_players
        self.crypto = crypto_engine
        self.players_keys = []
        self.encrypted_deck = None
    
    def setup_players(self, players_keys):
        """Инициализация ключей игроков"""
        self.players_keys = players_keys
    
    def collective_encrypt_deck(self, deck):
        """Коллективное шифрование колоды всеми игроками"""
        encrypted_deck = deck.copy()
        
        for player_keys in self.players_keys:
            # Каждый игрок шифрует всю колоду
            encrypted_deck = [self.crypto.encrypt_card(card, player_keys['encrypt_key']) 
                            for card in encrypted_deck]
            # И перемешивает
            random.shuffle(encrypted_deck)
        
        self.encrypted_deck = encrypted_deck
        return encrypted_deck
    
    def deal_private_card(self, player_index):
        """Раздача приватной карты игроку"""
        if not self.encrypted_deck:
            raise ValueError("Deck not encrypted")
        
        # Выбираем карту из колоды
        card_index = random.randint(0, len(self.encrypted_deck) - 1)
        encrypted_card = self.encrypted_deck.pop(card_index)
        
        # Все игроки кроме целевого частично расшифровывают
        for i, keys in enumerate(self.players_keys):
            if i != player_index:
                encrypted_card = self.crypto.decrypt_card(encrypted_card, keys['decrypt_key'])
        
        # Целевой игрок полностью расшифровывает
        final_card = self.crypto.decrypt_card(encrypted_card, 
                                            self.players_keys[player_index]['decrypt_key'])
        
        return final_card
    
    def deal_community_card(self):
        """Раздача общественной карты"""
        if not self.encrypted_deck:
            raise ValueError("Deck not encrypted")
        
        card_index = random.randint(0, len(self.encrypted_deck) - 1)
        encrypted_card = self.encrypted_deck.pop(card_index)
        
        # Все игроки расшифровывают
        for keys in self.players_keys:
            encrypted_card = self.crypto.decrypt_card(encrypted_card, keys['decrypt_key'])
        
        return encrypted_card
```

### Этап 3: Серверная часть

#### 3.3.1 Основной сервер
```python
# server/core/game_server.py
import asyncio
import json
import logging
from typing import Dict, List, Set
from server.core.session_manager import SessionManager
from server.core.player_manager import PlayerManager

class PokerGameServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.sessions = SessionManager()
        self.players = PlayerManager()
        self.logger = logging.getLogger('PokerServer')
        
    async def start_server(self):
        """Запуск сервера"""
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        addr = server.sockets[0].getsockname()
        self.logger.info(f'Serving on {addr}')
        
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """Обработка подключения клиента"""
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                    
                message = json.loads(data.decode())
                await self.process_message(writer, message)
                
        except Exception as e:
            self.logger.error(f"Client error: {e}")
        finally:
            writer.close()
    
    async def process_message(self, writer, message):
        """Обработка сообщений от клиента"""
        msg_type = message.get('type')
        
        if msg_type == 'register':
            await self.handle_register(writer, message)
        elif msg_type == 'create_session':
            await self.handle_create_session(writer, message)
        elif msg_type == 'join_session':
            await self.handle_join_session(writer, message)
        # ... обработка других типов сообщений
```

#### 3.3.2 Управление игровыми сессиями
```python
# server/core/session_manager.py
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.session_counter = 0
    
    def create_session(self, creator_id, session_name, max_players=10):
        """Создание новой игровой сессии"""
        session_id = f"session_{self.session_counter}"
        self.session_counter += 1
        
        session = GameSession(session_id, session_name, creator_id, max_players)
        self.sessions[session_id] = session
        
        return session_id
    
    def join_session(self, session_id, player_id):
        """Присоединение игрока к сессии"""
        if session_id in self.sessions:
            return self.sessions[session_id].add_player(player_id)
        return False
    
    def get_available_sessions(self):
        """Получение списка доступных сессий"""
        return [session.get_info() for session in self.sessions.values() 
                if not session.is_full() and not session.is_started()]
```

#### 3.3.3 Игровая сессия
```python
# server/core/game_session.py
class GameSession:
    def __init__(self, session_id, name, creator_id, max_players):
        self.session_id = session_id
        self.name = name
        self.creator_id = creator_id
        self.max_players = max_players
        self.players: List[str] = []
        self.game_state = GameState()
        self.poker_protocol = None
        
    def add_player(self, player_id):
        """Добавление игрока в сессию"""
        if len(self.players) < self.max_players and player_id not in self.players:
            self.players.append(player_id)
            return True
        return False
    
    def start_game(self):
        """Начало игры"""
        if len(self.players) < 2:
            return False
        
        # Инициализация протокола ментального покера
        self.poker_protocol = MentalPokerProtocol(len(self.players))
        
        # Генерация ключей для всех игроков
        player_keys = []
        for _ in self.players:
            player_keys.append(self.poker_protocol.crypto.generate_key_pair())
        
        self.poker_protocol.setup_players(player_keys)
        
        # Создание и шифрование колоды
        deck = self.poker_protocol.crypto.create_deck()
        encrypted_deck = self.poker_protocol.collective_encrypt_deck(deck)
        
        self.game_state.start_game(encrypted_deck)
        return True
    
    def deal_private_cards(self):
        """Раздача приватных карт"""
        private_cards = {}
        for i, player_id in enumerate(self.players):
            card1 = self.poker_protocol.deal_private_card(i)
            card2 = self.poker_protocol.deal_private_card(i)
            private_cards[player_id] = [card1, card2]
        
        return private_cards
    
    def deal_community_cards(self, num_cards=5):
        """Раздача общих карт"""
        community_cards = []
        for _ in range(num_cards):
            card = self.poker_protocol.deal_community_card()
            community_cards.append(card)
        
        return community_cards
```

### Этап 4: Клиентская часть

#### 3.4.1 Графический интерфейс
```python
# client/gui/main_window.py
import tkinter as tk
from tkinter import ttk
import asyncio

class PokerMainWindow:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.setup_window()
        self.create_connection_frame()
        self.create_lobby_frame()
        self.create_game_frame()
        self.create_chat_frame()
        
    def setup_window(self):
        self.root.title("Mental Poker - Texas Hold'em")
        self.root.geometry("1200x800")
        
        # Создание вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_connection_frame(self):
        """Фрейм подключения к серверу"""
        self.conn_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.conn_frame, text="Connection")
        
        # Элементы подключения
        ttk.Label(self.conn_frame, text="Server:").grid(row=0, column=0)
        self.server_entry = ttk.Entry(self.conn_frame)
        self.server_entry.insert(0, "localhost")
        self.server_entry.grid(row=0, column=1)
        
        ttk.Button(self.conn_frame, text="Connect", 
                  command=self.connect_to_server).grid(row=2, column=1)
    
    def create_game_frame(self):
        """Основной игровой фрейм"""
        self.game_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.game_frame, text="Game")
        
        # Область игрового стола
        self.table_canvas = tk.Canvas(self.game_frame, width=800, height=400, bg='darkgreen')
        self.table_canvas.pack(pady=20)
        
        # Отображение карт игрока
        self.player_cards_frame = ttk.Frame(self.game_frame)
        self.player_cards_frame.pack()
        
        # Кнопки действий
        self.create_action_buttons()
    
    def create_action_buttons(self):
        """Создание кнопок для игровых действий"""
        actions_frame = ttk.Frame(self.game_frame)
        actions_frame.pack(pady=10)
        
        ttk.Button(actions_frame, text="Fold", 
                  command=lambda: self.send_action('fold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Check", 
                  command=lambda: self.send_action('check')).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Call", 
                  command=lambda: self.send_action('call')).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Raise", 
                  command=lambda: self.send_action('raise')).pack(side=tk.LEFT, padx=5)
        
        self.bet_entry = ttk.Entry(actions_frame, width=8)
        self.bet_entry.pack(side=tk.LEFT, padx=5)
        self.bet_entry.insert(0, "50")
    
    def update_game_state(self, game_state):
        """Обновление игрового интерфейса"""
        # Очистка предыдущего состояния
        self.clear_table()
        
        # Отображение общих карт
        self.draw_community_cards(game_state.community_cards)
        
        # Отображение карт игрока
        self.draw_player_cards(game_state.player_cards)
        
        # Отображение информации о игроках
        self.draw_players_info(game_state.players)
    
    def draw_community_cards(self, cards):
        """Отрисовка общих карт на столе"""
        card_width = 80
        card_height = 120
        start_x = 400 - (len(cards) * card_width) // 2
        
        for i, card in enumerate(cards):
            x = start_x + i * card_width
            y = 200
            self.draw_card(x, y, card_width, card_height, card)
    
    def draw_player_cards(self, cards):
        """Отрисовка карт игрока"""
        for widget in self.player_cards_frame.winfo_children():
            widget.destroy()
        
        for card in cards:
            card_label = ttk.Label(self.player_cards_frame, text=self.card_to_text(card),
                                 relief='raised', padding=10)
            card_label.pack(side=tk.LEFT, padx=5)
```

#### 3.4.2 Сетевой клиент
```python
# client/network/poker_client.py
import asyncio
import json
import logging

class PokerClient:
    def __init__(self, gui):
        self.gui = gui
        self.reader = None
        self.writer = None
        self.connected = False
        self.player_id = None
        
    async def connect(self, host, port, player_name):
        """Подключение к серверу"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True
            
            # Регистрация на сервере
            await self.send_message({
                'type': 'register',
                'player_name': player_name
            })
            
            # Запуск обработки входящих сообщений
            asyncio.create_task(self.receive_messages())
            return True
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    async def send_message(self, message):
        """Отправка сообщения на сервер"""
        if self.connected and self.writer:
            data = json.dumps(message).encode()
            self.writer.write(data)
            await self.writer.drain()
    
    async def receive_messages(self):
        """Получение сообщений от сервера"""
        while self.connected:
            try:
                data = await self.reader.read(1024)
                if not data:
                    break
                    
                message = json.loads(data.decode())
                await self.handle_message(message)
                
            except Exception as e:
                logging.error(f"Receive error: {e}")
                break
        
        self.connected = False
```

### Этап 5: Интеграция и тестирование

#### 3.5.1 Интеграционные тесты
```python
# tests/integration/test_full_game.py
import pytest
import asyncio
from server.core.game_server import PokerGameServer
from client.network.poker_client import PokerClient

class TestFullGame:
    @pytest.fixture
    async def server(self):
        server = PokerGameServer()
        server_task = asyncio.create_task(server.start_server())
        yield server
        server_task.cancel()
    
    @pytest.fixture
    async def clients(self):
        clients = []
        for i in range(3):
            client = PokerClient()
            await client.connect('localhost', 8888, f'Player_{i}')
            clients.append(client)
        yield clients
        for client in clients:
            await client.disconnect()
    
    async def test_full_poker_game(self, server, clients):
        """Тест полной игры в покер"""
        # Создание сессии
        await clients[0].create_session("Test Game")
        
        # Присоединение других игроков
        for client in clients[1:]:
            await client.join_session(session_id)
        
        # Начало игры
        await clients[0].start_game()
        
        # Проверка раздачи карт
        for client in clients:
            assert len(client.private_cards) == 2
        
        # Проверка общих карт
        assert len(server.sessions[session_id].community_cards) == 5
        
        # Симуляция ставок
        await clients[0].make_bet(50)
        await clients[1].call_bet()
        await clients[2].fold()
```

#### 3.5.2 Тестирование безопасности
```python
# tests/security/test_mental_poker.py
class TestMentalPokerSecurity:
    def test_card_secrecy(self):
        """Тест конфиденциальности карт"""
        protocol = MentalPokerProtocol(4)
        
        # Имитация злоумышленника, пытающегося определить карты
        attacker_keys = protocol.crypto.generate_key_pair()
        
        # Проверка, что без всех ключей невозможно определить карты
        with pytest.raises(Exception):
            protocol.decrypt_card_without_all_keys(encrypted_card, attacker_keys)
    
    def test_protocol_verification(self):
        """Тест верификации протокола"""
        # После игры можно проверить корректность всех операций
        game_log = collect_game_log()
        verifier = GameVerifier(game_log)
        
        assert verifier.verify_deck_encryption()
        assert verifier.verify_card_distribution()
        assert verifier.verify_no_cheating()
```

### Этап 6: Деплоймент и документация

#### 3.6.1 Конфигурация деплоймента
```yaml
# deployment/docker-compose.yml
version: '3.8'
services:
  poker-server:
    build: ./server
    ports:
      - "8888:8888"
    environment:
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8888
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs

  poker-client:
    build: ./client
    environment:
      - SERVER_HOST=poker-server
      - SERVER_PORT=8888
    depends_on:
      - poker-server
```

#### 3.6.2 Документация
```
docs/
├── API.md                  # API сервера
├── PROTOCOL.md            # Протокол ментального покера
├── SECURITY.md            # Руководство по безопасности
├── USER_GUIDE.md          # Руководство пользователя
└── DEVELOPER_GUIDE.md     # Руководство разработчика
```

## 4. График реализации

| Этап | Основные задачи |
|-----|-----------------|
| Подготовка | Проектирование, настройка окружения |
| Криптография | Реализация протокола ментального покера |
| Сервер | Сетевой сервер, управление сессиями |
| Клиент | Графический интерфейс, сетевое взаимодействие |
| Интеграция | Тестирование, отладка |
| Финальная | Документация, деплоймент |
