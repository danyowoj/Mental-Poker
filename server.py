"""
Упрощенный сервер для ментального покера с системой фишек и фазами игры
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
            traceback.print_exc()  # Добавим вывод полной трассировки
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
            'ready_players': set(),
            'current_player_index': 0,
            'phase': 'waiting',
            'phase_actions': 0,  # Счетчик действий в текущей фазе
            'community_cards': [],
            'pot': 0,
            'current_bet': 0,
            'player_data': {},  # Данные игроков: фишки, текущая ставка, статус
            'player_cards': {},  # Карты игроков
            'deck': []  # Колода карт
        }

        # Инициализируем данные игрока
        self.games[game_id]['player_data'][player_id] = {
            'chips': 1000,  # Начальные фишки
            'current_bet': 0,
            'folded': False,
            'acted_this_phase': False
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

        # Инициализируем данные нового игрока
        game['player_data'][player_id] = {
            'chips': 1000,  # Начальные фишки
            'current_bet': 0,
            'folded': False,
            'acted_this_phase': False
        }

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

    async def handle_player_action(self, player_id, message):
        """Обработка действия игрока"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, "Игра не найдена")
            return

        game = self.games[game_id]
        player_data = game['player_data'][player_id]

        # Проверяем, что сейчас ход этого игрока
        current_player = game['players'][game['current_player_index']]
        if player_id != current_player:
            await self.send_error(player_id, "Сейчас не ваш ход")
            return

        action = message.get('action')
        amount = message.get('amount', 0)

        # Обрабатываем действие
        if action == 'fold':
            player_data['folded'] = True
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        elif action == 'check':
            # Проверяем, можно ли сделать чек (текущая ставка = 0)
            if game['current_bet'] > 0:
                await self.send_error(player_id, "Нельзя сделать чек, есть текущая ставка")
                return
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        elif action == 'call':
            # Уравниваем текущую ставку
            call_amount = game['current_bet'] - player_data['current_bet']
            if call_amount > player_data['chips']:
                await self.send_error(player_id, "Недостаточно фишек")
                return

            player_data['chips'] -= call_amount
            player_data['current_bet'] = game['current_bet']
            game['pot'] += call_amount
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        elif action == 'bet':
            if amount <= 0:
                await self.send_error(player_id, "Ставка должна быть положительной")
                return
            if amount > player_data['chips']:
                await self.send_error(player_id, "Недостаточно фишек")
                return
            if game['current_bet'] > 0:
                await self.send_error(player_id, "Уже есть ставка, используйте raise")
                return

            player_data['chips'] -= amount
            player_data['current_bet'] = amount
            game['current_bet'] = amount
            game['pot'] += amount
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        elif action == 'raise':
            if amount <= 0:
                await self.send_error(player_id, "Повышение должно быть положительным")
                return
            if amount > player_data['chips']:
                await self.send_error(player_id, "Недостаточно фишек")
                return
            if game['current_bet'] == 0:
                await self.send_error(player_id, "Нет текущей ставки, используйте bet")
                return
            if amount <= game['current_bet']:
                await self.send_error(player_id, "Повышение должно быть больше текущей ставки")
                return

            total_bet = player_data['current_bet'] + amount
            player_data['chips'] -= amount
            player_data['current_bet'] = total_bet
            game['current_bet'] = total_bet
            game['pot'] += amount
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        else:
            await self.send_error(player_id, f"Неизвестное действие: {action}")
            return

        # Пересылаем действие всем игрокам в игре
        await self.broadcast_to_game(game_id, {
            'type': 'player_action',
            'player_id': player_id,
            'action': action,
            'amount': amount,
            'pot': game['pot'],
            'current_bet': game['current_bet']
        })

        # Обновляем состояние игроков
        await self.broadcast_game_state(game_id)

        logger.info(f"🎮 Игрок {player_id} сделал ход: {action} {amount if amount > 0 else ''}")

        # Проверяем, нужно ли переходить к следующей фазе
        active_players = [p for p in game['players'] if not game['player_data'][p]['folded']]
        if game['phase_actions'] >= len(active_players):
            # Все активные игроки сделали ход в этой фазе
            await self.advance_game_phase(game_id)
        else:
            # Переходим к следующему игроку
            await self.next_player(game_id)

    async def next_player(self, game_id):
        """Переход к следующему игроку"""
        game = self.games[game_id]

        # Находим следующего активного игрока
        start_index = game['current_player_index']
        while True:
            game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
            next_player = game['players'][game['current_player_index']]

            # Если игрок не сбросил карты, это следующий игрок
            if not game['player_data'][next_player]['folded']:
                break

            # Если мы прошли полный круг, выходим
            if game['current_player_index'] == start_index:
                break

        # Уведомляем следующего игрока о его ходе
        next_player = game['players'][game['current_player_index']]
        await self.send_to_player(next_player, {
            'type': 'your_turn',
            'message': 'Сейчас ваш ход! Введите действие (fold, check, call, bet, raise)'
        })

    async def advance_game_phase(self, game_id):
        """Переход к следующей фазе игры"""
        game = self.games[game_id]

        # Сбрасываем состояние фазовых действий
        game['phase_actions'] = 0
        game['current_bet'] = 0

        # Сбрасываем ставки игроков для новой фазы
        for player_id in game['players']:
            game['player_data'][player_id]['current_bet'] = 0
            game['player_data'][player_id]['acted_this_phase'] = False

        # Переходим к следующей фазе
        if game['phase'] == 'preflop':
            game['phase'] = 'flop'
            # Выкладываем 3 карты на флоп
            if len(game['deck']) >= 3:
                game['community_cards'] = [str(card) for card in game['deck'][:3]]
                game['deck'] = game['deck'][3:]

        elif game['phase'] == 'flop':
            game['phase'] = 'turn'
            # Выкладываем 4-ю карту
            if len(game['deck']) >= 1:
                game['community_cards'].append(str(game['deck'][0]))
                game['deck'] = game['deck'][1:]

        elif game['phase'] == 'turn':
            game['phase'] = 'river'
            # Выкладываем 5-ю карту
            if len(game['deck']) >= 1:
                game['community_cards'].append(str(game['deck'][0]))
                game['deck'] = game['deck'][1:]

        elif game['phase'] == 'river':
            # Завершаем игру
            await self.end_game(game_id)
            return

        # Уведомляем о смене фазы
        await self.broadcast_to_game(game_id, {
            'type': 'phase_changed',
            'phase': game['phase'],
            'community_cards': game['community_cards'],
            'message': f'Фаза изменена: {game["phase"]}'
        })

        # Обновляем состояние игры
        await self.broadcast_game_state(game_id)

        # Начинаем новую фазу с первого активного игрока
        game['current_player_index'] = 0
        await self.next_player(game_id)

        logger.info(f"🔄 Игра {game_id} перешла к фазе: {game['phase']}")

    async def end_game(self, game_id):
        """Завершение игры и определение победителя с использованием poker_rules"""
        from poker_rules import HandEvaluator

        game = self.games[game_id]

        # Находим активных игроков (не сбросивших карты)
        active_players = [p for p in game['players'] if not game['player_data'][p]['folded']]

        if len(active_players) == 0:
            # Все сбросили карты - победителя нет
            winner_message = "Все игроки сбросили карты - победителя нет"
            winners = []
            player_combinations = {}
        elif len(active_players) == 1:
            # Один активный игрок - он победитель
            winner = active_players[0]
            game['player_data'][winner]['chips'] += game['pot']
            winner_message = f"Победитель: {winner} (единственный активный игрок)"
            winners = [winner]

            # Получаем комбинацию победителя
            player_cards = game['player_cards'][winner]
            community_cards_objs = [self._parse_card(card_str) for card_str in game['community_cards']]
            all_cards = player_cards + community_cards_objs
            score = HandEvaluator.evaluate_hand(all_cards)
            combination_name = self._get_combination_name(score[0])
            player_combinations = {winner: combination_name}
        else:
            # Определяем победителя по силе комбинации с использованием poker_rules
            best_players = []
            best_score = None
            player_combinations = {}
            player_scores = {}

            # Оцениваем руки всех активных игроков
            for player_id in active_players:
                player_cards = game['player_cards'][player_id]
                community_cards_objs = [self._parse_card(card_str) for card_str in game['community_cards']]
                all_cards = player_cards + community_cards_objs

                score = HandEvaluator.evaluate_hand(all_cards)
                combination_name = self._get_combination_name(score[0])
                player_combinations[player_id] = combination_name
                player_scores[player_id] = score

                if best_score is None:
                    best_score = score
                    best_players = [player_id]
                else:
                    # Сравниваем с текущим лучшим игроком
                    best_player_cards = game['player_cards'][best_players[0]] + community_cards_objs
                    comparison = HandEvaluator.compare_hands(best_player_cards, all_cards)

                    if comparison == -1:  # Текущий игрок сильнее
                        best_score = score
                        best_players = [player_id]
                    elif comparison == 0:  # Ничья
                        best_players.append(player_id)

            winners = best_players

            # Делим банк между победителями
            if winners:
                split_pot = game['pot'] // len(winners)
                remainder = game['pot'] % len(winners)  # Остаток от деления

                for i, winner in enumerate(winners):
                    # Первый игрок получает остаток, чтобы общая сумма не изменилась
                    amount = split_pot + (1 if i < remainder else 0)
                    game['player_data'][winner]['chips'] += amount

                if len(winners) == 1:
                    winner_message = f"Победитель: {winners[0]}"
                else:
                    winner_message = f"Ничья между: {', '.join(winners)}"
            else:
                winner_message = "Победитель не определен"

        # Отправляем результаты игры
        await self.broadcast_to_game(game_id, {
            'type': 'game_result',
            'winners': winners,
            'pot': game['pot'],
            'player_combinations': player_combinations,
            'message': f'Игра завершена! {winner_message}'
        })

        # Сбрасываем состояние игры для новой раздачи
        game['status'] = 'waiting'
        game['phase'] = 'waiting'
        game['ready_players'] = set()
        game['pot'] = 0
        game['current_bet'] = 0
        game['community_cards'] = []
        game['phase_actions'] = 0
        game['player_cards'] = {}
        game['deck'] = []

        # Сбрасываем состояние игроков (но сохраняем фишки)
        for player_id in game['players']:
            game['player_data'][player_id]['current_bet'] = 0
            game['player_data'][player_id]['folded'] = False
            game['player_data'][player_id]['acted_this_phase'] = False

        logger.info(f"🏁 Игра {game_id} завершена. {winner_message}")

        # Уведомляем о возможности начать новую игру
        await self.broadcast_to_game(game_id, {
            'type': 'game_can_restart',
            'message': 'Игра завершена! Введите "ready" для новой раздачи'
        })

    def _parse_card(self, card_str):
        """Преобразует строковое представление карты в объект Card"""
        from poker_rules import Card

        # Определяем масть
        suit_symbol = card_str[-1]
        suits = {'♠': 0, '♥': 1, '♦': 2, '♣': 3}
        suit = suits.get(suit_symbol, 0)

        # Определяем достоинство
        rank_str = card_str[:-1]
        if rank_str == 'A':
            rank = 14
        elif rank_str == 'K':
            rank = 13
        elif rank_str == 'Q':
            rank = 12
        elif rank_str == 'J':
            rank = 11
        else:
            rank = int(rank_str)

        return Card(rank, suit)

    def _get_combination_name(self, combination_type):
        """Возвращает читаемое название комбинации"""
        from poker_rules import HandEvaluator

        names = {
            HandEvaluator.HIGH_CARD: "Старшая карта",
            HandEvaluator.PAIR: "Пара",
            HandEvaluator.TWO_PAIR: "Две пары",
            HandEvaluator.THREE_OF_A_KIND: "Сет",
            HandEvaluator.STRAIGHT: "Стрит",
            HandEvaluator.FLUSH: "Флеш",
            HandEvaluator.FULL_HOUSE: "Фулл-хаус",
            HandEvaluator.FOUR_OF_A_KIND: "Каре",
            HandEvaluator.STRAIGHT_FLUSH: "Стрит-флеш",
            HandEvaluator.ROYAL_FLUSH: "Флеш-рояль"
        }
        return names.get(combination_type, "Неизвестная комбинация")

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
        """Начало игры с использованием колоды из poker_rules"""
        from deck_utils import Deck

        game = self.games[game_id]
        game['status'] = 'playing'
        game['phase'] = 'preflop'
        game['pot'] = 0
        game['current_bet'] = 0
        game['phase_actions'] = 0

        logger.info(f"🎲 Начало игры {game_id}")

        # Создаем и тасуем колоду из deck_utils
        deck = Deck()
        game['deck'] = deck.cards

        # Сбрасываем состояние игроков
        for player_id in game['players']:
            game['player_data'][player_id]['current_bet'] = 0
            game['player_data'][player_id]['folded'] = False
            game['player_data'][player_id]['acted_this_phase'] = False

        # Раздаем карты
        player_cards = {}
        cards_dealt = 0
        for i in range(2):  # По 2 карты каждому игроку
            for player_id in game['players']:
                if len(game['deck']) > 0:
                    if player_id not in player_cards:
                        player_cards[player_id] = []
                    player_cards[player_id].append(game['deck'].pop(0))
                    cards_dealt += 1

        # Сохраняем карты игроков для определения победителя
        game['player_cards'] = player_cards

        # Инициализируем общие карты
        game['community_cards'] = []

        # Отправляем начальное состояние игры
        for player_id in game['players']:
            await self.send_to_player(player_id, {
                'type': 'game_started',
                'game_id': game_id,
                'your_cards': [str(card) for card in player_cards[player_id]],
                'community_cards': [],
                'players': game['players'],
                'chips': game['player_data'][player_id]['chips']
            })

        # Уведомляем первого игрока о его ходе
        game['current_player_index'] = 0
        first_player = game['players'][0]
        await self.send_to_player(first_player, {
            'type': 'your_turn',
            'message': 'Сейчас ваш ход! Введите действие (fold, check, call, bet, raise)'
        })

        await self.broadcast_to_game(game_id, {
            'type': 'game_state',
            'phase': 'preflop',
            'message': 'Игра началась! Фаза: Pre-flop'
        })

        print(f'🎲 Игра {game_id} началась с {len(game["players"])} игроками')

    async def broadcast_game_state(self, game_id):
        """Отправка текущего состояния игры всем игрокам"""
        game = self.games[game_id]

        for player_id in game['players']:
            player_data = game['player_data'][player_id]
            await self.send_to_player(player_id, {
                'type': 'game_state_update',
                'chips': player_data['chips'],
                'pot': game['pot'],
                'current_bet': game['current_bet'],
                'community_cards': game['community_cards']
            })

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
