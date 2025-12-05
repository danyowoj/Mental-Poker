"""
Сервер ментального покера с RSA (исправленная версия)
"""

import asyncio
import json
import random
import logging
import math
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('PokerServer')

from rsa_poker import RSAPoker
from poker_rules import PokerGameManager, Card, HandEvaluator


class PokerServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.games = {}
        self.players = {}
        self.game_counter = 0

        # Генерация общего модуля RSA для ментального покера
        self.poker_crypto = RSAPoker()
        self.common_n = self.poker_crypto.generate_common_modulus()

        logger.info(f"Сервер инициализирован. Модуль RSA: {self.common_n}")
        print(f"\n{'=' * 60}")
        print("🎲 СЕРВЕР МЕНТАЛЬНОГО ПОКЕРА RSA")
        print(f"{'=' * 60}")
        print(f"📍 Адрес: {self.host}:{self.port}")
        print(f"🔐 Модуль RSA: {self.common_n}")
        print(f"📏 Размер: {self.common_n.bit_length()} бит")
        print(f"{'=' * 60}")

    async def start(self):
        """Запуск сервера"""
        try:
            server = await asyncio.start_server(
                self.handle_client, self.host, self.port
            )

            addr = server.sockets[0].getsockname()
            logger.info(f'🚀 Сервер запущен на {addr}')
            print("✅ Сервер запущен. Ожидание подключений...")

            async with server:
                await server.serve_forever()

        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            print(f"❌ Ошибка запуска сервера: {e}")
            raise

    async def handle_client(self, reader, writer):
        """Обработка нового клиентского подключения"""
        client_addr = writer.get_extra_info('peername')
        player_id = f"Игрок_{random.randint(1000, 9999)}"

        logger.info(f'🔗 Новое подключение от {client_addr} как {player_id}')
        print(f'👤 Новый игрок: {player_id}')

        # Сохраняем информацию о подключении
        self.players[player_id] = {
            'reader': reader,
            'writer': writer,
            'address': client_addr,
            'keys': None,
            'game_id': None,
            'connected': True
        }

        try:
            # Отправляем приветственное сообщение с общим модулем
            await self.send_to_player(player_id, {
                'type': 'welcome',
                'player_id': player_id,
                'common_n': str(self.common_n),
                'message': f'Добро пожаловать! Ваш ID: {player_id}'
            })

            # Обрабатываем сообщения от клиента
            async for message in self.read_messages(reader):
                if message:
                    await self.process_message(player_id, message)

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

                buffer += data.decode('utf-8', errors='ignore')

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(f"Невалидный JSON: {line[:100]}")

            except Exception as e:
                logger.error(f"Ошибка чтения: {e}")
                break

    async def process_message(self, player_id, message):
        """Обработка входящего сообщения"""
        try:
            msg_type = message.get('type')

            if msg_type == 'exchange_keys':
                await self.handle_exchange_keys(player_id, message)
            elif msg_type == 'create_game':
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
                logger.warning(f"Неизвестный тип сообщения: {msg_type}")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await self.send_error(player_id, f"Ошибка обработки: {str(e)}")

    async def handle_exchange_keys(self, player_id, message):
        """Обработка обмена ключами RSA"""
        try:
            # Генерируем уникальные ключи для игрока
            e, d = self.poker_crypto.generate_player_keys(player_id)

            self.players[player_id]['keys'] = {'e': e, 'd': d}

            logger.info(f"🔑 Игрок {player_id} получил ключи: e={e}")

            # Отправляем подтверждение
            await self.send_to_player(player_id, {
                'type': 'keys_accepted',
                'message': 'Ключи RSA приняты',
                'e': str(e),
                'd': str(d)
            })

        except Exception as e:
            await self.send_error(player_id, f"Ошибка генерации ключей: {str(e)}")

    async def handle_create_game(self, player_id, message):
        """Создание новой игры"""
        # Проверяем, что у игрока есть ключи
        if not self.players[player_id]['keys']:
            await self.send_error(player_id, "Сначала обменяйтесь ключами RSA")
            return

        self.game_counter += 1
        game_id = f"game_{self.game_counter}"

        # Создаем новую игру
        self.games[game_id] = {
            'id': game_id,
            'players': [player_id],
            'host': player_id,
            'status': 'waiting',
            'ready_players': set(),
            'game_manager': PokerGameManager(),
            'encrypted_deck': [],
            'player_order': [],
            'current_phase': 'waiting',
            'created_at': datetime.now().isoformat()
        }

        # Инициализируем игровую логику
        game = self.games[game_id]
        game_manager = game['game_manager']
        game_manager.add_player(player_id, chips=1000)

        # Добавляем игрока в текущую игру
        self.players[player_id]['game_id'] = game_id

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

        if len(game['players']) >= 6:
            await self.send_error(player_id, "Игра заполнена")
            return

        # Проверяем ключи
        if not self.players[player_id]['keys']:
            await self.send_error(player_id, "Сначала обменяйтесь ключами RSA")
            return

        # Добавляем игрока в игру
        game['players'].append(player_id)
        self.players[player_id]['game_id'] = game_id

        # Добавляем в игровую логику
        game['game_manager'].add_player(player_id, chips=1000)

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
            'ready_players': list(game['ready_players']),
            'total_players': len(game['players'])
        })

        logger.info(f"✅ Игрок {player_id} готов к игре")

        # Если все готовы и есть минимум 2 игрока, начинаем игру
        if (len(game['ready_players']) == len(game['players']) and
                len(game['players']) >= 2):
            await self.start_game(game_id)

    async def start_game(self, game_id: str):
        """Начало игры с ментальным покером - исправленная версия"""
        game = self.games[game_id]
        game['status'] = 'playing'
        game['current_phase'] = 'preflop'

        logger.info(f"🎲 Начало игры {game_id} с ментальным покером")

        # Добавляем ключи всех игроков в криптосистему
        for player_id in game['players']:
            player_info = self.players[player_id]
            if player_info.get('keys'):
                e = player_info['keys']['e']
                d = player_info['keys']['d']
                self.poker_crypto.players_keys[player_id] = {'e': e, 'd': d}

        # Подготавливаем числовое представление карт
        deck_numbers = self.poker_crypto.prepare_cards()
        logger.info(f"Подготовлено {len(deck_numbers)} числовых карт")

        # Определяем порядок игроков для шифрования
        game['player_order'] = game['players'].copy()
        random.shuffle(game['player_order'])
        logger.info(f"Порядок шифрования: {game['player_order']}")

        # Шифруем колоду всеми игроками
        encrypted_deck = self.poker_crypto.shuffle_and_encrypt_deck(game['player_order'])
        game['encrypted_deck'] = encrypted_deck.copy()

        # Перемешиваем зашифрованную колоду еще раз
        random.shuffle(game['encrypted_deck'])
        logger.info(f"Зашифрованная колода: {len(game['encrypted_deck'])} карт")

        # Инициализируем игровую логику
        game_manager = game['game_manager']
        game_manager.start_new_hand()

        # Раздаем карты игрокам
        player_cards = {}

        # Раздаем по 2 карты каждому игроку
        for i in range(2):
            for player_id in game['players']:
                if game['encrypted_deck']:
                    # Берем зашифрованную карту из колоды
                    encrypted_card = game['encrypted_deck'].pop(0)

                    # Расшифровываем карту для игрока (исправленный метод)
                    try:
                        card = self.poker_crypto.decrypt_for_player(
                            encrypted_card, player_id, game['player_order']
                        )

                        if card and card != f"??({encrypted_card})":
                            if player_id not in player_cards:
                                player_cards[player_id] = []

                            player_cards[player_id].append(card)

                            # Добавляем карту в игровую логику
                            game_manager.set_player_cards(player_id, player_cards[player_id])

                            logger.info(f"Игрок {player_id} получил карту: {card}")
                        else:
                            # Если карта не распознана, создаем фиктивную
                            if player_id not in player_cards:
                                player_cards[player_id] = []
                            player_cards[player_id].append("??")
                            logger.warning(f"Не удалось расшифровать карту для {player_id}")

                    except Exception as e:
                        logger.error(f"Ошибка расшифрования карты для {player_id}: {e}")
                        if player_id not in player_cards:
                            player_cards[player_id] = []
                        player_cards[player_id].append("??")

        # Отправляем игрокам их карты
        for player_id in game['players']:
            await self.send_to_player(player_id, {
                'type': 'game_started',
                'game_id': game_id,
                'your_cards': player_cards.get(player_id, []),
                'players': game['players'],
                'chips': game_manager.get_player_chips(player_id),
                'player_order': game['player_order'],
                'message': 'Игра началась! Вам разданы карты.'
            })

        # Обновляем состояние игры
        await self.broadcast_game_state(game_id)

        # Определяем первого игрока
        current_player = game_manager.get_current_player()
        if current_player:
            await self.send_to_player(current_player, {
                'type': 'your_turn',
                'message': 'Сейчас ваш ход!'
            })

        print(f'🎲 Игра {game_id} началась с {len(game["players"])} игроками')

    async def handle_player_action(self, player_id, message):
        """Обработка действия игрока"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, "Игра не найдена")
            return

        game = self.games[game_id]
        game_manager = game['game_manager']

        if not game_manager.is_player_in_game(player_id):
            await self.send_error(player_id, "Вы не в этой игре")
            return

        # Проверяем, что сейчас ход этого игрока
        current_player = game_manager.get_current_player()
        if player_id != current_player:
            await self.send_error(player_id, "Сейчас не ваш ход")
            return

        action = message.get('action')
        amount = message.get('amount', 0)

        # Обрабатываем действие через игровую логику
        try:
            result = game_manager.process_player_action(player_id, action, amount)

            if not result.get('success', False):
                await self.send_error(player_id, result.get('message', 'Неизвестная ошибка'))
                return
        except Exception as e:
            await self.send_error(player_id, f"Ошибка обработки действия: {str(e)}")
            return

        # Пересылаем действие всем игрокам в игре
        await self.broadcast_to_game(game_id, {
            'type': 'player_action',
            'player_id': player_id,
            'action': action,
            'amount': amount,
            'pot': game_manager.get_pot(),
            'current_bet': game_manager.get_current_bet()
        })

        # Обновляем состояние игры
        await self.broadcast_game_state(game_id)

        logger.info(f"🎮 Игрок {player_id} сделал ход: {action} {amount if amount > 0 else ''}")

        # Проверяем, нужно ли переходить к следующей фазе
        if game_manager.is_phase_complete():
            await self.advance_game_phase(game_id)
        else:
            # Переходим к следующему игроку
            next_player = game_manager.get_next_player()
            if next_player:
                await self.send_to_player(next_player, {
                    'type': 'your_turn',
                    'message': 'Сейчас ваш ход!'
                })

    async def advance_game_phase(self, game_id: str):
        """Переход к следующей фазе игры - исправленная версия"""
        game = self.games[game_id]
        game_manager = game['game_manager']

        next_phase = game_manager.advance_phase()

        if next_phase == 'showdown':
            await self.end_game(game_id)
            return

        # Если есть общие карты для раскрытия
        if game['encrypted_deck'] and next_phase in ['flop', 'turn', 'river']:
            cards_to_reveal = 3 if next_phase == 'flop' else 1

            new_community_cards = []
            for i in range(cards_to_reveal):
                if game['encrypted_deck']:
                    encrypted_card = game['encrypted_deck'].pop(0)

                    # Исправление: расшифровываем карту первым игроком
                    if game['players']:
                        player_id = game['players'][0]
                        try:
                            card = self.poker_crypto.decrypt_for_player(
                                encrypted_card, player_id, game['player_order']
                            )
                            if card and card != f"??({encrypted_card})":
                                new_community_cards.append(card)
                                # Добавляем карту в игровую логику
                                game_manager.add_community_card(card)
                                logger.info(f"Открыта карта: {card}")
                            else:
                                logger.warning(f"Не удалось расшифровать общую карту")
                        except Exception as e:
                            logger.error(f"Ошибка расшифрования общей карты: {e}")

        game['current_phase'] = next_phase

        await self.broadcast_to_game(game_id, {
            'type': 'phase_changed',
            'phase': next_phase,
            'community_cards': game_manager.get_community_cards(),
            'message': f'Фаза изменена: {next_phase}'
        })

        await self.broadcast_game_state(game_id)

        next_player = game_manager.get_next_player()
        if next_player:
            await self.send_to_player(next_player, {
                'type': 'your_turn',
                'message': 'Сейчас ваш ход!'
            })

        logger.info(f"🔄 Игра {game_id} перешла к фазе: {next_phase}")

    async def end_game(self, game_id):
        """Завершение игры с определением победителя"""
        game = self.games[game_id]
        game_manager = game['game_manager']

        # Определяем победителей
        winners, player_combinations, player_cards = game_manager.determine_winners()

        # Распределяем банк
        pot = game_manager.get_pot()
        if winners:
            split_pot = pot // len(winners)
            remainder = pot % len(winners)

            for i, winner in enumerate(winners):
                amount = split_pot + (1 if i < remainder else 0)
                game_manager.add_chips_to_player(winner, amount)

        # Формируем сообщение о результатах
        if len(winners) == 0:
            winner_message = "Все игроки сбросили карты - победителя нет"
        elif len(winners) == 1:
            winner_message = f"Победитель: {winners[0]}"
        else:
            winner_message = f"Ничья между: {', '.join(winners)}"

        # Отправляем результаты игры
        await self.broadcast_to_game(game_id, {
            'type': 'game_result',
            'winners': winners,
            'pot': pot,
            'player_combinations': player_combinations,
            'player_cards': player_cards,
            'message': f'Игра завершена! {winner_message}'
        })

        # Сбрасываем состояние игры для новой раздачи
        game['status'] = 'waiting'
        game['current_phase'] = 'waiting'
        game['ready_players'] = set()
        game['encrypted_deck'] = []
        game['player_order'] = []
        game_manager.reset_for_new_hand()

        logger.info(f"🏁 Игра {game_id} завершена. {winner_message}")

        # Уведомляем о возможности начать новую игру
        await self.broadcast_to_game(game_id, {
            'type': 'game_can_restart',
            'message': 'Игра завершена! Вы можете начать новую.'
        })

    async def handle_chat_message(self, player_id, message):
        """Обработка сообщения в чат"""
        text = message.get('text', '')
        game_id = message.get('game_id')

        if game_id and game_id in self.games:
            # Отправляем сообщение всем игрокам в игре
            for p_id in self.games[game_id]['players']:
                if p_id != player_id:  # Не отправляем себе
                    await self.send_to_player(p_id, {
                        'type': 'chat_message',
                        'player_id': player_id,
                        'text': text
                    })
        else:
            # Глобальный чат (всем подключенным игрокам)
            for p_id, p_data in self.players.items():
                if p_id != player_id and p_data['connected']:
                    await self.send_to_player(p_id, {
                        'type': 'chat_message',
                        'player_id': player_id,
                        'text': text
                    })

    async def broadcast_game_state(self, game_id):
        """Отправка текущего состояния игры всем игрокам"""
        if game_id not in self.games:
            return

        game = self.games[game_id]
        game_manager = game['game_manager']

        for player_id in game['players']:
            chips = game_manager.get_player_chips(player_id)
            await self.send_to_player(player_id, {
                'type': 'game_state_update',
                'chips': chips,
                'pot': game_manager.get_pot(),
                'current_bet': game_manager.get_current_bet(),
                'community_cards': game_manager.get_community_cards()
            })

    async def send_to_player(self, player_id, message):
        """Отправка сообщения конкретному игроку"""
        if player_id in self.players and self.players[player_id]['connected']:
            try:
                writer = self.players[player_id]['writer']
                data = json.dumps(message, ensure_ascii=False).encode() + b'\n'
                writer.write(data)
                await writer.drain()
            except Exception as e:
                logger.error(f"Ошибка отправки игроку {player_id}: {e}")
                self.players[player_id]['connected'] = False

    async def broadcast_to_game(self, game_id, message, exclude_player=None):
        """Отправка сообщения всем игрокам в игре"""
        if game_id in self.games:
            game = self.games[game_id]
            for player_id in game['players']:
                if player_id != exclude_player:
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
            # Отмечаем как отключенного
            self.players[player_id]['connected'] = False

            # Удаляем игрока из всех игр
            for game_id, game in list(self.games.items()):
                if player_id in game['players']:
                    game['players'].remove(player_id)
                    game['ready_players'].discard(player_id)

                    # Уведомляем остальных игроков
                    await self.broadcast_to_game(game_id, {
                        'type': 'player_left',
                        'player_id': player_id,
                        'players': game['players'],
                        'message': f'{player_id} покинул игру'
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
    print("Запуск сервера ментального покера с RSA...")
    asyncio.run(main())
