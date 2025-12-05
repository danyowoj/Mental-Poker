"""
Реализация ментального покера на основе RSA с общим модулем (исправленная версия)
"""

import random
import math
import sympy
from typing import Dict, List, Tuple, Optional


class RSAPoker:
    """Класс для ментального покера с общим модулем RSA"""

    def __init__(self, n_bits=1024):
        self.n = None          # Общий модуль
        self.phi_n = None      # φ(n) = (p-1)*(q-1)
        self.players_keys = {} # {player_id: {'e': e, 'd': d}}
        self.card_mapping = {} # Отображение чисел на карты
        self.card_numbers = [] # Числовое представление карт

    def generate_common_modulus(self) -> int:
        """Генерация общего модуля RSA n = p * q"""
        print("[RSA] Генерация общего модуля RSA...")

        p = sympy.randprime(2**511, 2**512)  # ~512 бит
        q = sympy.randprime(2**511, 2**512)  # ~512 бит

        self.n = p * q
        self.phi_n = (p - 1) * (q - 1)

        print(f"[RSA] Модуль сгенерирован: {self.n.bit_length()} бит")
        return self.n

    def set_common_modulus(self, n: int, phi_n: Optional[int] = None):
        """Установка общего модуля (для клиентов)"""
        self.n = n
        self.phi_n = phi_n

    def generate_player_keys(self, player_id: str) -> Tuple[int, int]:
        """
        Генерация уникальной пары ключей для игрока
        Возвращает (e, d)
        """
        if not self.n or not self.phi_n:
            raise ValueError("Общий модуль не установлен")

        # Генерируем уникальную экспоненту e для игрока
        e_candidates = [3, 5, 17, 257, 65537]
        random.shuffle(e_candidates)

        for e in e_candidates:
            if math.gcd(e, self.phi_n) == 1:
                try:
                    d = sympy.mod_inverse(e, self.phi_n)
                    self.players_keys[player_id] = {'e': e, 'd': d}
                    print(f"[RSA] Игрок {player_id}: e={e}, d={d}")
                    return e, d
                except Exception:
                    continue

        # Если стандартные не подошли, ищем случайное
        e = random.randint(3, min(65537, self.phi_n - 1))
        while math.gcd(e, self.phi_n) != 1:
            e = random.randint(3, min(65537, self.phi_n - 1))

        d = sympy.mod_inverse(e, self.phi_n)
        self.players_keys[player_id] = {'e': e, 'd': d}

        return e, d

    def prepare_cards(self) -> List[int]:
        """Подготавливает числовое представление карт (52 карты)"""
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

        cards = []
        for suit in suits:
            for rank in ranks:
                cards.append(f"{rank}{suit}")

        # Преобразуем карты в числа
        self.card_mapping = {}
        self.card_numbers = []

        # Используем простые числа для представления карт
        prime = 2
        while len(self.card_numbers) < 52:
            if sympy.isprime(prime) and math.gcd(prime, self.n) == 1:
                card_idx = len(self.card_numbers)
                if card_idx < len(cards):
                    self.card_mapping[prime] = cards[card_idx]
                self.card_numbers.append(prime)
            prime += 1

        print(f"[RSA] Подготовлено {len(self.card_numbers)} числовых карт")
        return self.card_numbers

    def get_card_from_number(self, number: int) -> str:
        """Получение карты по числу"""
        return self.card_mapping.get(number, f"??({number})")

    def encrypt_card(self, card_number: int, e: int) -> int:
        """Шифрование карты: C = M^e mod n"""
        if card_number >= self.n:
            raise ValueError(f"Число карты {card_number} >= n={self.n}")
        return pow(card_number, e, self.n)

    def decrypt_card(self, encrypted_card: int, d: int) -> int:
        """Расшифрование карты: M = C^d mod n"""
        return pow(encrypted_card, d, self.n)

    def shuffle_and_encrypt_deck(self, player_order: List[str]) -> List[int]:
        """
        Ментальное шифрование колоды всеми игроками
        Каждый игрок шифрует и перемешивает
        """
        if not self.card_numbers:
            self.prepare_cards()

        current_deck = self.card_numbers.copy()
        random.shuffle(current_deck)

        for player_id in player_order:
            if player_id in self.players_keys:
                e = self.players_keys[player_id]['e']
                current_deck = [self.encrypt_card(card, e) for card in current_deck]
                random.shuffle(current_deck)

        print(f"[RSA] Колода зашифрована {len(player_order)} игроками")
        return current_deck

    def decrypt_for_player(self, encrypted_card: int, player_id: str,
                          player_order: List[str]) -> str:
        """
        Расшифрование карты для конкретного игрока
        Ключевое исправление: карта должна быть полностью расшифрована
        всеми игроками, включая текущего
        """
        if player_id not in self.players_keys:
            raise ValueError(f"Игрок {player_id} не найден")

        # ВАЖНОЕ ИСПРАВЛЕНИЕ:
        # Карта должна быть полностью расшифрована всеми игроками
        # в обратном порядке, включая текущего игрока

        # Определяем обратный порядок
        reverse_order = list(reversed(player_order))

        # Начинаем с зашифрованной карты
        card_value = encrypted_card

        # Расшифровываем всеми игроками в обратном порядке
        for current_player in reverse_order:
            if current_player in self.players_keys:
                d = self.players_keys[current_player]['d']
                card_value = self.decrypt_card(card_value, d)

        # Теперь карта полностью расшифрована
        card = self.get_card_from_number(card_value)
        return card

    def verify_encryption(self, player_order: List[str]) -> bool:
        """Проверка корректности шифрования/расшифрования"""
        if len(self.card_numbers) < 2:
            return False

        test_card = self.card_numbers[0]

        # Шифруем всеми игроками
        encrypted = test_card
        for player_id in player_order:
            if player_id in self.players_keys:
                e = self.players_keys[player_id]['e']
                encrypted = self.encrypt_card(encrypted, e)

        # Расшифровываем в обратном порядке
        decrypted = encrypted
        for player_id in reversed(player_order):
            if player_id in self.players_keys:
                d = self.players_keys[player_id]['d']
                decrypted = self.decrypt_card(decrypted, d)

        result = (test_card == decrypted)
        print(f"[RSA] Проверка шифрования: {'✅ УСПЕХ' if result else '❌ ОШИБКА'}")
        return result
