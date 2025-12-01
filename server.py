"""
Сервер ментального покера с криптографической защитой
"""

import asyncio
import json
import logging
import random
import traceback
from typing import Dict, List, Optional
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MentalPokerServer')

class CryptoUtils:
    """Криптографические утилиты для ментального покера"""

    @staticmethod
    def generate_rsa_keypair():
        """Генерация пары RSA ключей"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key

    @staticmethod
    def serialize_public_key(public_key):
        """Сериализация открытого ключа в строку"""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(pem).decode('utf-8')

    @staticmethod
    def deserialize_public_key(public_key_str):
        """Десериализация открытого ключа из строки"""
        pem = base64.b64decode(public_key_str.encode('utf-8'))
        public_key = serialization.load_pem_public_key(pem, backend=default_backend())
        return public_key

    @staticmethod
    def generate_aes_key():
        """Генерация AES ключа"""
        return os.urandom(32)  # 256-bit key

    @staticmethod
    def encrypt_aes(plaintext, key):
        """Шифрование AES-GCM"""
        iv = os.urandom(12)  # 96-bit IV для GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        return iv + encryptor.tag + ciphertext

    @staticmethod
    def decrypt_aes(ciphertext, key):
        """Расшифрование AES-GCM"""
        if len(ciphertext) < 28:
            raise ValueError("Неверный размер зашифрованных данных")

        iv = ciphertext[:12]
        tag = ciphertext[12:28]
        actual_ciphertext = ciphertext[28:]

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(actual_ciphertext) + decryptor.finalize()

    @staticmethod
    def encrypt_rsa(plaintext, public_key):
        """Шифрование RSA-OAEP"""
        ciphertext = public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext

    @staticmethod
    def decrypt_rsa(ciphertext, private_key):
        """Расшифрование RSA-OAEP"""
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext

class MentalPokerDeck:
    """Класс для управления зашифрованной колодой в ментальном покере"""

    def __init__(self):
        self.cards = []  # Список зашифрованных карт
        self.encryption_keys = []  # Ключи шифрования для каждой карты
        self.player_keys = {}  # Открытые ключи игроков
        self.deck_commitment = None  # Обязательство колоды для верификации
        self.card_mapping = {}  # Сопоставление: зашифрованная карта -> исходная карта

    def add_player_key(self, player_id, public_key):
        """Добавление открытого ключа игрока"""
        self.player_keys[player_id] = public_key

    def prepare_deck(self, standard_deck):
        """Подготовка зашифрованной колоды с сохранением маппинга"""
        self.cards = []
        self.encryption_keys = []
        self.card_mapping = {}

        for card in standard_deck:
            # Генерация симметричного ключа для карты
            aes_key = CryptoUtils.generate_aes_key()
            self.encryption_keys.append(aes_key)

            # Шифрование карты
            card_data = card.encode('utf-8')
            encrypted_card = CryptoUtils.encrypt_aes(card_data, aes_key)
            encrypted_card_str = base64.b64encode(encrypted_card).decode('utf-8')
            self.cards.append(encrypted_card_str)

            # Сохраняем маппинг для отладки и тестирования
            self.card_mapping[encrypted_card_str] = card

        # Создание обязательства колоды
        import json
        deck_hash = hashes.Hash(hashes.SHA256(), backend=default_backend())
        deck_hash.update(json.dumps(self.cards).encode('utf-8'))
        self.deck_commitment = base64.b64encode(deck_hash.finalize()).decode('utf-8')

        return self.cards

    def encrypt_keys_for_player(self, player_id, card_indices=None):
        """Шифрование ключей для конкретного игрока"""
        if player_id not in self.player_keys:
            raise ValueError(f"Ключ игрока {player_id} не найден")

        player_public_key = self.player_keys[player_id]
        encrypted_keys = []

        if card_indices is None:
            # Шифруем все ключи
            keys_to_encrypt = self.encryption_keys
        else:
            # Шифруем только указанные ключи
            keys_to_encrypt = [self.encryption_keys[i] for i in card_indices if i < len(self.encryption_keys)]

        for aes_key in keys_to_encrypt:
            # Шифрование AES ключа открытым ключом игрока
            encrypted_key = CryptoUtils.encrypt_rsa(aes_key, player_public_key)
            encrypted_keys.append(base64.b64encode(encrypted_key).decode('utf-8'))

        return encrypted_keys

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
            'address': client_addr,
            'public_key': None,
            'key_verified': False
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
            elif msg_type == 'exchange_public_key':
                await self.handle_exchange_public_key(player_id, message)
            elif msg_type == 'verify_deck':
                await self.handle_verify_deck(player_id, message)
            else:
                await self.send_error(player_id, f"Неизвестный тип сообщения: {msg_type}")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            traceback.print_exc()
            await self.send_error(player_id, f"Ошибка обработки: {str(e)}")

    async def handle_exchange_public_key(self, player_id, message):
        """Обработка обмена открытыми ключами"""
        public_key_str = message.get('public_key')

        if not public_key_str:
            await self.send_error(player_id, "Отсутствует открытый ключ")
            return

        try:
            # Сохраняем открытый ключ игрока
            public_key = CryptoUtils.deserialize_public_key(public_key_str)
            self.players[player_id]['public_key'] = public_key
            self.players[player_id]['key_verified'] = True

            logger.info(f"🔑 Игрок {player_id} предоставил открытый ключ")

            # Отправляем подтверждение
            await self.send_to_player(player_id, {
                'type': 'public_key_accepted',
                'message': 'Открытый ключ принят'
            })

        except Exception as e:
            logger.error(f"Ошибка обработки ключа игрока {player_id}: {e}")
            await self.send_error(player_id, f"Ошибка обработки ключа: {str(e)}")

    async def handle_verify_deck(self, player_id, message):
        """Обработка верификации колоды"""
        game_id = message.get('game_id')

        if game_id not in self.games:
            await self.send_error(player_id, "Игра не найдена")
            return

        game = self.games[game_id]

        if player_id not in game['players']:
            await self.send_error(player_id, "Вы не в этой игре")
            return

        # Отправляем информацию для верификации колоды
        await self.send_to_player(player_id, {
            'type': 'deck_verification',
            'deck_commitment': game['mental_deck'].deck_commitment,
            'encrypted_cards': game['mental_deck'].cards,
            'message': 'Информация для верификации колоды'
        })

    async def handle_create_game(self, player_id, message):
        """Создание новой игры с ментальным покером"""
        self.game_counter += 1
        game_id = f"game_{self.game_counter}"

        # Создаем новую игру с криптографической колодой
        self.games[game_id] = {
            'id': game_id,
            'players': [player_id],
            'host': player_id,
            'status': 'waiting',
            'ready_players': set(),
            'current_player_index': 0,
            'phase': 'waiting',
            'phase_actions': 0,
            'community_cards': [],
            'encrypted_community_cards': [],
            'pot': 0,
            'current_bet': 0,
            'player_data': {},
            'player_cards': {},
            'encrypted_player_cards': {},
            'deck': [],
            'original_deck': [],
            'mental_deck': MentalPokerDeck(),
            'keys_distributed': False
        }

        # Инициализируем данные игрока
        self.games[game_id]['player_data'][player_id] = {
            'chips': 1000,
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

        if len(game['players']) >= 6:
            await self.send_error(player_id, "Игра заполнена")
            return

        # Добавляем игрока в игру
        game['players'].append(player_id)

        # Инициализируем данные нового игрока
        game['player_data'][player_id] = {
            'chips': 1000,
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

        # Проверяем, что игрок предоставил открытый ключ
        if not self.players[player_id].get('key_verified', False):
            await self.send_error(player_id, "Сначала предоставьте открытый ключ")
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
            if game['current_bet'] > 0:
                await self.send_error(player_id, "Нельзя сделать чек, есть текущая ставка")
                return
            player_data['acted_this_phase'] = True
            game['phase_actions'] += 1

        elif action == 'call':
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

            if not game['player_data'][next_player]['folded']:
                break

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

        # Переходим к следующей фазе и раскрываем общие карты
        cards_to_reveal = 0
        if game['phase'] == 'preflop':
            game['phase'] = 'flop'
            cards_to_reveal = 3
        elif game['phase'] == 'flop':
            game['phase'] = 'turn'
            cards_to_reveal = 1
        elif game['phase'] == 'turn':
            game['phase'] = 'river'
            cards_to_reveal = 1
        elif game['phase'] == 'river':
            # Завершаем игру
            await self.end_game(game_id)
            return

        # Раскрываем общие карты
        if len(game['original_deck']) >= cards_to_reveal:
            new_community_cards = []
            encrypted_community_cards = []

            for i in range(cards_to_reveal):
                if game['original_deck']:
                    card = game['original_deck'].pop(0)
                    new_community_cards.append(card)

                if game['deck']:
                    encrypted_card = game['deck'].pop(0)
                    encrypted_community_cards.append(encrypted_card)
                    game['encrypted_community_cards'].append(encrypted_card)

            game['community_cards'].extend(new_community_cards)

        # Уведомляем о смене фазы
        await self.broadcast_to_game(game_id, {
            'type': 'phase_changed',
            'phase': game['phase'],
            'community_cards': game['community_cards'],
            'encrypted_community_cards': encrypted_community_cards,
            'message': f'Фаза изменена: {game["phase"]}'
        })

        # Обновляем состояние игры
        await self.broadcast_game_state(game_id)

        # Начинаем новую фазу с первого активного игрока
        game['current_player_index'] = 0
        await self.next_player(game_id)

        logger.info(f"🔄 Игра {game_id} перешла к фазе: {game['phase']}")

    async def end_game(self, game_id):
        """Завершение игры с определением победителя"""
        from poker_rules import HandEvaluator

        game = self.games[game_id]

        # Находим активных игроков (не сбросивших карты)
        active_players = [p for p in game['players'] if not game['player_data'][p]['folded']]

        if len(active_players) == 0:
            winner_message = "Все игроки сбросили карты - победителя нет"
            winners = []
            player_combinations = {}
        elif len(active_players) == 1:
            winner = active_players[0]
            game['player_data'][winner]['chips'] += game['pot']
            winner_message = f"Победитель: {winner} (единственный активный игрок)"
            winners = [winner]
            player_combinations = {winner: "Единственный активный игрок"}
        else:
            # Определяем победителя по силе комбинации
            best_players = []
            best_score = None
            player_combinations = {}

            # Оцениваем руки всех активных игроков
            for player_id in active_players:
                player_cards = [self._parse_card(card) for card in game['player_cards'][player_id]]
                community_cards = [self._parse_card(card) for card in game['community_cards']]
                all_cards = player_cards + community_cards

                score = HandEvaluator.evaluate_hand(all_cards)
                combination_name = self._get_combination_name(score[0])
                player_combinations[player_id] = combination_name

                if best_score is None:
                    best_score = score
                    best_players = [player_id]
                else:
                    # Сравниваем руки
                    best_player_cards = [self._parse_card(card) for card in game['player_cards'][best_players[0]]]
                    best_player_full = best_player_cards + [self._parse_card(card) for card in game['community_cards']]

                    # Создаем временные объекты для сравнения
                    comparison = HandEvaluator.compare_hands(best_player_full, all_cards)

                    if comparison == -1:  # Текущий игрок сильнее
                        best_score = score
                        best_players = [player_id]
                    elif comparison == 0:  # Ничья
                        best_players.append(player_id)

            winners = best_players

            # Делим банк между победителями
            if winners:
                split_pot = game['pot'] // len(winners)
                remainder = game['pot'] % len(winners)

                for i, winner in enumerate(winners):
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
            'player_cards': game['player_cards'],
            'message': f'Игра завершена! {winner_message}'
        })

        # Сбрасываем состояние игры для новой раздачи
        game['status'] = 'waiting'
        game['phase'] = 'waiting'
        game['ready_players'] = set()
        game['pot'] = 0
        game['current_bet'] = 0
        game['community_cards'] = []
        game['encrypted_community_cards'] = []
        game['phase_actions'] = 0
        game['player_cards'] = {}
        game['encrypted_player_cards'] = {}
        game['deck'] = []
        game['original_deck'] = []
        game['mental_deck'] = MentalPokerDeck()
        game['keys_distributed'] = False

        # Сбрасываем состояние игроков
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

        suit_symbol = card_str[-1]
        suits = {'♠': 0, '♥': 1, '♦': 2, '♣': 3}
        suit = suits.get(suit_symbol, 0)

        rank_str = card_str[:-1]
        if rank_str == 'A':
            rank = 14
        elif rank_str == 'K':
            rank = 13
        elif rank_str == 'Q':
            rank = 12
        elif rank_str == 'J':
            rank = 11
        elif rank_str == '10':
            rank = 10
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
            await self.broadcast_to_game(game_id, {
                'type': 'chat_message',
                'player_id': player_id,
                'text': text
            })
        else:
            await self.broadcast_to_all({
                'type': 'chat_message',
                'player_id': player_id,
                'text': text
            })

    async def start_game(self, game_id):
        """Начало игры"""
        # Создаем простую колоду карт
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

        standard_cards = []
        for suit in suits:
            for rank in ranks:
                standard_cards.append(f"{rank}{suit}")

        game = self.games[game_id]
        game['status'] = 'playing'
        game['phase'] = 'preflop'
        game['pot'] = 0
        game['current_bet'] = 0
        game['phase_actions'] = 0

        logger.info(f"🎲 Начало игры {game_id} с ментальным покером")

        # Перемешиваем стандартные карты
        random.shuffle(standard_cards)
        game['original_deck'] = standard_cards.copy()

        # Добавляем открытые ключи всех игроков в криптографическую колоду
        mental_deck = game['mental_deck']
        for player_id in game['players']:
            if self.players[player_id]['public_key']:
                mental_deck.add_player_key(player_id, self.players[player_id]['public_key'])

        # Подготавливаем зашифрованную колоду
        encrypted_cards = mental_deck.prepare_deck(standard_cards)
        game['deck'] = encrypted_cards.copy()

        # Перемешиваем зашифрованную колоду
        random.shuffle(game['deck'])

        # Сбрасываем состояние игроков
        for player_id in game['players']:
            game['player_data'][player_id]['current_bet'] = 0
            game['player_data'][player_id]['folded'] = False
            game['player_data'][player_id]['acted_this_phase'] = False

        # Раздаем карты игрокам
        player_encrypted_cards = {}
        player_open_cards = {}

        # Раздаем по 2 карты каждому игроку
        for i in range(2):
            for player_id in game['players']:
                if game['original_deck'] and game['deck']:
                    if player_id not in player_encrypted_cards:
                        player_encrypted_cards[player_id] = []
                        player_open_cards[player_id] = []

                    # Берем карту из оригинальной колоды
                    open_card = game['original_deck'].pop(0)
                    player_open_cards[player_id].append(open_card)

                    # Берем зашифрованную карту
                    encrypted_card = game['deck'].pop(0)
                    player_encrypted_cards[player_id].append(encrypted_card)

        game['encrypted_player_cards'] = player_encrypted_cards
        game['player_cards'] = player_open_cards

        # Отправляем игрокам их открытые и зашифрованные карты
        for player_id in game['players']:
            # Получаем ключи для карт игрока
            encrypted_keys = mental_deck.encrypt_keys_for_player(player_id)

            # Отправляем начальное состояние игры
            await self.send_to_player(player_id, {
                'type': 'game_started',
                'game_id': game_id,
                'your_cards': player_open_cards[player_id],
                'encrypted_cards': player_encrypted_cards[player_id],
                'encrypted_keys': encrypted_keys[:2],
                'community_cards': [],
                'players': game['players'],
                'chips': game['player_data'][player_id]['chips'],
                'deck_commitment': mental_deck.deck_commitment,
                'message': 'Игра началась! Ваши карты зашифрованы.'
            })

        # Уведомляем о начале игры
        await self.broadcast_to_game(game_id, {
            'type': 'game_state',
            'phase': 'preflop',
            'message': 'Игра началась! Фаза: Pre-flop'
        })

        # Уведомляем первого игрока о его ходе
        game['current_player_index'] = 0
        first_player = game['players'][0]
        await self.send_to_player(first_player, {
            'type': 'your_turn',
            'message': 'Сейчас ваш ход! Введите действие (fold, check, call, bet, raise)'
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
