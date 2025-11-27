"""
Упрощенный сервер для ментального покера
"""

import asyncio
import json
import logging
import random
import traceback
from typing import Dict, List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PokerServer')

class PokerServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.games = {}
        self.players = {}
        self.game_counter = 0

    async def start(self):
        """Запуск сервера"""
        try:
            server = await asyncio.start_server(
                self.handle_client, self.host, self.port
            )

            addr = server.sockets[0].getsockname()
            logger.info(f'🚀 Сервер запущен на {addr}')
            print(f'✅ Сервер запущен на {self.host}:{self.port}')
            print('Ожидание подключений...')

            async with server:
                await server.serve_forever()

        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            print(f"❌ Ошибка запуска сервера: {e}")
            traceback.print_exc()

    async def handle_client(self, reader, writer):
        """Обработка нового клиентского подключения"""
        client_addr = writer.get_extra_info('peername')
        player_id = f"player_{random.randint(1000, 9999)}"

        logger.info(f'🔗 Новое подключение от {client_addr} как {player_id}')
        print(f'👤 Новый игрок: {player_id}')

        # Сохраняем информацию о подключении
        self.players[player_id] = {
            'reader': reader,
            'writer': writer,
            'address': client_addr
        }

        try:
            # Отправляем приветственное сообщение
            welcome_msg = {
                'type': 'welcome',
                'player_id': player_id,
                'message': f'Добро пожаловать! Ваш ID: {player_id}'
            }
            await self.send_to_player(player_id, welcome_msg)

            # Обрабатываем сообщения от клиента
            async for message in self.read_messages(reader):
                if message:
                    await self.process_message(player_id, message, writer)

        except Exception as e:
            logger.error(f"Ошибка обработки клиента {player_id}: {e}")
        finally:
            await self.disconnect_player(player_id)

    async def read_messages(self, reader):
        """Генератор для чтения сообщений от клиента"""
        buffer = ""
        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    break

                buffer += data.decode()

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(f"Невалидный JSON: {line}")

            except Exception as e:
                logger.error(f"Ошибка чтения: {e}")
                break

    async def process_message(self, player_id, message, writer):
        """Обработка входящего сообщения"""
        try:
            msg_type = message.get('type')

            if msg_type == 'create_game':
                await self.handle_create_game(player_id, message)
            elif msg_type == 'join_game':
                await self.handle_join_game(player_id, message)
            elif msg_type == 'player_ready':
                await self.handle_player_ready(player_id, message)
            elif msg_type == 'player_action':
                await self.handle_player_action(player_id, message)
            elif msg_type == 'chat_message':
                await self.handle_chat_message(player_id, message)
            elif msg_type == 'ping':
                await self.send_to_player(player_id, {'type': 'pong'})
            else:
                await self.send_error(player_id, f"Неизвестный тип сообщения: {msg_type}")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await self.send_error(player_id, f"Ошибка обработки: {str(e)}")

    async def handle_create_game(self, player_id, message):
        """Создание новой игры"""
        self.game_counter += 1
        game_id = f"game_{self.game_counter}"

        # Создаем новую игру
        self.games[game_id] = {
            'id': game_id,
            'players': [player_id],
            'host': player_id,
            'status': 'waiting',
            'ready_players': set()
        }

        logger.info(f"🎮 Создана игра {game_id} игроком {player_id}")

        # Отправляем подтверждение
        await self.send_to_player(player_id, {
            'type': 'game_created',
            'game_id': game_id,
            'message': f'Игра создана! ID: {game_id}'
        })

        print(f'🎮 Создана новая игра: {game_id}')

    async def handle_join_game(self, player_id, message):
        """Присоединение к игре"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, f"Игра {game_id} не найдена")
            return

        game = self.games[game_id]

        if player_id in game['players']:
            await self.send_error(player_id, "Вы уже в этой игре")
            return

        if len(game['players']) >= 6:  # Максимум 6 игроков
            await self.send_error(player_id, "Игра заполнена")
            return

        # Добавляем игрока в игру
        game['players'].append(player_id)

        logger.info(f"👥 Игрок {player_id} присоединился к игре {game_id}")

        # Отправляем подтверждение новому игроку
        await self.send_to_player(player_id, {
            'type': 'game_joined',
            'game_id': game_id,
            'players': game['players'],
            'message': f'Присоединились к игре {game_id}'
        })

        # Уведомляем других игроков
        await self.broadcast_to_game(game_id, {
            'type': 'player_joined',
            'player_id': player_id,
            'players': game['players']
        }, exclude_player=player_id)

        print(f'👥 Игрок {player_id} присоединился к игре {game_id}')

        # Если игроков достаточно, уведомляем о возможности начала
        if len(game['players']) >= 2:
            await self.broadcast_to_game(game_id, {
                'type': 'game_can_start',
                'message': 'Достаточно игроков для начала! Используйте команду ready'
            })

    async def handle_player_ready(self, player_id, message):
        """Обработка готовности игрока"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, "Игра не найдена")
            return

        game = self.games[game_id]

        if player_id not in game['players']:
            await self.send_error(player_id, "Вы не в этой игре")
            return

        # Отмечаем игрока как готового
        game['ready_players'].add(player_id)

        await self.broadcast_to_game(game_id, {
            'type': 'player_ready',
            'player_id': player_id,
            'ready_players': list(game['ready_players'])
        })

        logger.info(f"✅ Игрок {player_id} готов к игре")

        # Если все готовы, начинаем игру
        if len(game['ready_players']) == len(game['players']) and len(game['players']) >= 2:
            await self.start_game(game_id)

    async def handle_player_action(self, player_id, message):
        """Обработка действия игрока"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, "Игра не найдена")
            return

        # Пересылаем действие всем игрокам в игре
        await self.broadcast_to_game(game_id, {
            'type': 'player_action',
            'player_id': player_id,
            'action': message.get('action'),
            'amount': message.get('amount', 0)
        })

    async def handle_chat_message(self, player_id, message):
        """Обработка сообщения в чат"""
        game_id = message.get('game_id')
        text = message.get('text', '')

        if game_id and game_id in self.games:
            # Сообщение в игровой чат
            await self.broadcast_to_game(game_id, {
                'type': 'chat_message',
                'player_id': player_id,
                'text': text
            })
        else:
            # Глобальное сообщение
            await self.broadcast_to_all({
                'type': 'chat_message',
                'player_id': player_id,
                'text': text
            })

    async def start_game(self, game_id):
        """Начало игры"""
        game = self.games[game_id]
        game['status'] = 'playing'

        logger.info(f"🎲 Начало игры {game_id}")

        # Создаем простую колоду для демонстрации
        deck = self.create_deck()
        random.shuffle(deck)

        # Раздаем карты
        player_cards = {}
        for i, player_id in enumerate(game['players']):
            # По 2 карты каждому игроку
            player_cards[player_id] = deck[i*2:(i+1)*2]

        # 5 карт на стол
        community_cards = deck[len(game['players'])*2:len(game['players'])*2+5]

        # Отправляем начальное состояние игры
        for player_id in game['players']:
            await self.send_to_player(player_id, {
                'type': 'game_started',
                'game_id': game_id,
                'your_cards': player_cards[player_id],
                'community_cards': [],
                'players': game['players']
            })

        await self.broadcast_to_game(game_id, {
            'type': 'game_state',
            'phase': 'preflop',
            'message': 'Игра началась! Фаза: Pre-flop'
        })

        print(f'🎲 Игра {game_id} началась с {len(game["players"])} игроками')

    def create_deck(self):
        """Создание простой колоды карт для демонстрации"""
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

        deck = []
        for suit in suits:
            for rank in ranks:
                deck.append(f"{rank}{suit}")

        return deck

    async def send_to_player(self, player_id, message):
        """Отправка сообщения конкретному игроку"""
        if player_id in self.players:
            try:
                writer = self.players[player_id]['writer']
                data = json.dumps(message).encode() + b'\n'
                writer.write(data)
                await writer.drain()
            except Exception as e:
                logger.error(f"Ошибка отправки игроку {player_id}: {e}")

    async def broadcast_to_game(self, game_id, message, exclude_player=None):
        """Отправка сообщения всем игрокам в игре"""
        if game_id in self.games:
            game = self.games[game_id]
            for player_id in game['players']:
                if player_id != exclude_player:
                    await self.send_to_player(player_id, message)

    async def broadcast_to_all(self, message):
        """Отправка сообщения всем подключенным игрокам"""
        for player_id in self.players:
            await self.send_to_player(player_id, message)

    async def send_error(self, player_id, error_text):
        """Отправка сообщения об ошибке"""
        await self.send_to_player(player_id, {
            'type': 'error',
            'message': error_text
        })

    async def disconnect_player(self, player_id):
        """Обработка отключения игрока"""
        if player_id in self.players:
            # Удаляем игрока из всех игр
            for game_id, game in list(self.games.items()):
                if player_id in game['players']:
                    game['players'].remove(player_id)
                    game['ready_players'].discard(player_id)

                    # Уведомляем остальных игроков
                    await self.broadcast_to_game(game_id, {
                        'type': 'player_left',
                        'player_id': player_id,
                        'players': game['players']
                    })

                    logger.info(f"👋 Игрок {player_id} вышел из игры {game_id}")

                    # Если игра пустая, удаляем её
                    if not game['players']:
                        del self.games[game_id]
                        logger.info(f"🗑️ Игра {game_id} удалена")

            # Закрываем соединение
            try:
                writer = self.players[player_id]['writer']
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except Exception as e:
                logger.error(f"Ошибка закрытия соединения: {e}")

            # Удаляем игрока
            del self.players[player_id]
            logger.info(f"🔌 Игрок {player_id} отключен")

async def main():
    """Точка входа для запуска сервера"""
    server = PokerServer()
    await server.start()

if __name__ == "__main__":
    print("Запуск сервера ментального покера...")
    asyncio.run(main())
