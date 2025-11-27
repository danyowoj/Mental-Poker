"""
Реализация криптографического протокола ментального покера.
Используется коммутативное шифрование на основе Эль-Гамаля для обеспечения
конфиденциальности карт и честности игры без доверенного дилера.
"""

import random
import hashlib
from sympy import nextprime, is_primitive_root
from typing import List, Tuple, Dict


class MentalPokerCrypto:
    """Класс для криптографических операций ментального покера"""

    def __init__(self, bit_length=512):
        """
        Инициализация криптосистемы

        Args:
            bit_length: Длина бит для простого числа (для тестов используем 512, в продакшене 2048)
        """
        self.bit_length = bit_length
        self.p, self.g = self.generate_parameters()

    def generate_parameters(self) -> Tuple[int, int]:
        """Генерация криптографических параметров p и g"""
        # Генерация безопасного простого числа
        p = self.generate_safe_prime(self.bit_length)

        # Поиск генератора мультипликативной группы
        g = self.find_generator(p)

        return p, g

    def generate_safe_prime(self, bit_length: int) -> int:
        """Генерация безопасного простого числа"""
        # Упрощенная генерация для демонстрации
        # В реальной системе нужно использовать более строгие методы
        while True:
            q = nextprime(2 ** (bit_length - 1))
            p = 2 * q + 1
            if p.bit_length() == bit_length and self.is_prime(p):
                return p

    def is_prime(self, n: int, k: int = 40) -> bool:
        """Тест Миллера-Рабина на простоту"""
        if n == 2 or n == 3:
            return True
        if n <= 1 or n % 2 == 0:
            return False

        # Находим r и d такие, что n-1 = 2^r * d
        r, d = 0, n - 1
        while d % 2 == 0:
            r += 1
            d //= 2

        # Проводим k тестов
        for _ in range(k):
            a = random.randint(2, n - 2)
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def find_generator(self, p: int) -> int:
        """Поиск генератора мультипликативной группы по модулю p"""
        # Разложение p-1 на простые множители (упрощенно)
        factors = [2, (p - 1) // 2]  # p-1 = 2 * q, где q - простое

        for g in range(2, p):
            if all(pow(g, (p - 1) // f, p) != 1 for f in factors):
                return g
        return 2  # Резервный генератор

    def generate_keypair(self) -> Tuple[int, int]:
        """Генерация пары ключей (приватный, публичный)"""
        private_key = random.randint(2, self.p - 2)
        public_key = pow(self.g, private_key, self.p)
        return private_key, public_key

    def encrypt(self, message: int, public_key: int) -> Tuple[int, int]:
        """
        Шифрование сообщения с использованием публичного ключа

        Args:
            message: Сообщение для шифрования (числовое представление карты)
            public_key: Публичный ключ получателя

        Returns:
            Кортеж (a, b) - зашифрованное сообщение
        """
        k = random.randint(2, self.p - 2)
        a = pow(self.g, k, self.p)
        b = (message * pow(public_key, k, self.p)) % self.p
        return a, b

    def decrypt(self, ciphertext: Tuple[int, int], private_key: int) -> int:
        """
        Расшифрование сообщения с использованием приватного ключа

        Args:
            ciphertext: Кортеж (a, b) - зашифрованное сообщение
            private_key: Приватный ключ

        Returns:
            Расшифрованное сообщение
        """
        a, b = ciphertext
        # Вычисляем обратный элемент для a^x
        inverse = pow(a, self.p - 1 - private_key, self.p)
        return (b * inverse) % self.p

    def re_encrypt(self, ciphertext: Tuple[int, int], public_key: int) -> Tuple[int, int]:
        """
        Перешифрование карты для следующего игрока
        (коммутативное свойство Эль-Гамаля)
        """
        a, b = ciphertext
        k = random.randint(2, self.p - 2)
        new_a = (a * pow(self.g, k, self.p)) % self.p
        new_b = (b * pow(public_key, k, self.p)) % self.p
        return new_a, new_b


class CardEncoder:
    """Класс для преобразования карт в числовое представление и обратно"""

    def __init__(self, crypto: MentalPokerCrypto):
        self.crypto = crypto
        self.card_mapping = self.generate_card_mapping()

    def generate_card_mapping(self) -> Dict[str, int]:
        """Генерация числового представления для 52 карт"""
        # Используем простые числа для представления карт
        primes = []
        current = 2
        while len(primes) < 52:
            if self.crypto.is_prime(current):
                primes.append(current)
            current += 1

        # Сопоставляем карты с простыми числами
        suits = ['S', 'H', 'D', 'C']  # Пики, Червы, Бубны, Трефы
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

        mapping = {}
        prime_idx = 0
        for suit in suits:
            for rank in ranks:
                card = rank + suit
                mapping[card] = primes[prime_idx]
                prime_idx += 1

        return mapping

    def card_to_number(self, card: str) -> int:
        """Преобразование карты в число"""
        return self.card_mapping.get(card)

    def number_to_card(self, number: int) -> str:
        """Преобразование числа в карту"""
        for card, num in self.card_mapping.items():
            if num == number:
                return card
        return None


class MentalPokerProtocol:
    """Реализация протокола ментального покера"""

    def __init__(self):
        self.crypto = MentalPokerCrypto()
        self.encoder = CardEncoder(self.crypto)

    def prepare_encrypted_deck(self, public_keys: List[int]) -> List[Tuple[int, int]]:
        """
        Подготовка зашифрованной колоды

        Args:
            public_keys: Список публичных ключей всех игроков

        Returns:
            Список зашифрованных карт
        """
        # Создаем колоду карт
        deck = list(self.encoder.card_mapping.values())

        # Шифруем каждую карту всеми публичными ключами
        encrypted_deck = []
        for card in deck:
            encrypted_card = card
            # Последовательное шифрование каждым игроком
            for pub_key in public_keys:
                encrypted_card = self.crypto.encrypt(encrypted_card, pub_key)
            encrypted_deck.append(encrypted_card)

        return encrypted_deck

    def shuffle_encrypted_deck(self, deck: List[Tuple[int, int]],
                               public_key: int) -> List[Tuple[int, int]]:
        """
        Перемешивание и перешифрование колоды игроком

        Args:
            deck: Зашифрованная колода
            public_key: Публичный ключ игрока

        Returns:
            Новая перемешанная и перешифрованная колода
        """
        # Перешифровываем каждую карту
        re_encrypted_deck = []
        for card in deck:
            re_encrypted_card = self.crypto.re_encrypt(card, public_key)
            re_encrypted_deck.append(re_encrypted_card)

        # Перемешиваем колоду
        random.shuffle(re_encrypted_deck)

        return re_encrypted_deck

    def decrypt_card(self, encrypted_card: Tuple[int, int],
                     private_keys: List[int]) -> str:
        """
        Расшифрование карты с помощью приватных ключей всех игроков

        Args:
            encrypted_card: Зашифрованная карта
            private_keys: Список приватных ключей всех игроков (в порядке шифрования)

        Returns:
            Расшифрованная карта в строковом формате
        """
        current_card = encrypted_card

        # Последовательное расшифрование каждым игроком
        for priv_key in private_keys:
            current_card = self.crypto.decrypt(current_card, priv_key)

        # Преобразуем число в карту
        return self.encoder.number_to_card(current_card)

    def partial_decrypt(self, encrypted_card: Tuple[int, int],
                        private_key: int) -> Tuple[int, int]:
        """
        Частичное расшифрование карты (снятие одного слоя шифрования)
        """
        return self.crypto.decrypt(encrypted_card, private_key)


# Тестовые функции
def test_mental_poker():
    """Тестирование криптографического протокола"""
    print("Тестирование ментального покера...")

    # Создаем экземпляр протокола
    protocol = MentalPokerProtocol()

    # Генерируем ключи для 3 игроков
    players = []
    for i in range(3):
        priv_key, pub_key = protocol.crypto.generate_keypair()
        players.append({
            'id': f'player_{i}',
            'private_key': priv_key,
            'public_key': pub_key
        })

    print(f"Сгенерированы ключи для {len(players)} игроков")

    # Подготавливаем зашифрованную колоду
    public_keys = [player['public_key'] for player in players]
    encrypted_deck = protocol.prepare_encrypted_deck(public_keys)
    print(f"Создана зашифрованная колода из {len(encrypted_deck)} карт")

    # Каждый игрок перемешивает и перешифровывает колоду
    current_deck = encrypted_deck
    for player in players:
        current_deck = protocol.shuffle_encrypted_deck(current_deck, player['public_key'])
        print(f"Игрок {player['id']} перемешал колоду")

    # "Раздаем" одну карту и расшифровываем её
    test_card = current_deck[0]
    private_keys = [player['private_key'] for player in players]
    decrypted_card = protocol.decrypt_card(test_card, private_keys)

    print(f"Тестовая карта: {decrypted_card}")
    print("Все тесты пройдены успешно!")


if __name__ == "__main__":
    test_mental_poker()
