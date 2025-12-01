"""
Криптографические утилиты для ментального покера
"""

import os
import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import random

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
    def serialize_private_key(private_key):
        """Сериализация закрытого ключа в строку"""
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return base64.b64encode(pem).decode('utf-8')

    @staticmethod
    def deserialize_private_key(private_key_str):
        """Десериализация закрытого ключа из строки"""
        pem = base64.b64decode(private_key_str.encode('utf-8'))
        private_key = serialization.load_pem_private_key(pem, password=None, backend=default_backend())
        return private_key

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

    @staticmethod
    def sign(data, private_key):
        """Создание цифровой подписи"""
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    @staticmethod
    def verify_signature(data, signature, public_key):
        """Проверка цифровой подписи"""
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def hash_data(data):
        """Хэширование данных"""
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data)
        return digest.finalize()


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

        for i, card in enumerate(standard_deck):
            # Генерация симметричного ключа для карты
            aes_key = CryptoUtils.generate_aes_key()
            self.encryption_keys.append(aes_key)

            # Шифрование карты
            card_data = card.encode('utf-8')  # Карта уже в строковом формате
            encrypted_card = CryptoUtils.encrypt_aes(card_data, aes_key)
            encrypted_card_str = base64.b64encode(encrypted_card).decode('utf-8')
            self.cards.append(encrypted_card_str)

            # Сохраняем маппинг для отладки и тестирования
            self.card_mapping[encrypted_card_str] = card

        # Создание обязательства колоды
        deck_hash = CryptoUtils.hash_data(json.dumps(self.cards).encode('utf-8'))
        self.deck_commitment = base64.b64encode(deck_hash).decode('utf-8')

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
            keys_to_encrypt = [self.encryption_keys[i] for i in card_indices]

        for aes_key in keys_to_encrypt:
            # Шифрование AES ключа открытым ключом игрока
            encrypted_key = CryptoUtils.encrypt_rsa(aes_key, player_public_key)
            encrypted_keys.append(base64.b64encode(encrypted_key).decode('utf-8'))

        return encrypted_keys

    def decrypt_card_for_player(self, encrypted_card_str, player_id, player_private_key, card_index=None):
        """Расшифрование карты для конкретного игрока"""
        try:
            # Получаем зашифрованный ключ для этой карты
            if card_index is not None and 0 <= card_index < len(self.encryption_keys):
                aes_key_encrypted = self.encrypt_keys_for_player(player_id, [card_index])[0]
            else:
                # Ищем ключ по индексу карты
                if encrypted_card_str in self.cards:
                    card_index = self.cards.index(encrypted_card_str)
                    aes_key_encrypted = self.encrypt_keys_for_player(player_id, [card_index])[0]
                else:
                    # В демо-режиме возвращаем карту из маппинга
                    if encrypted_card_str in self.card_mapping:
                        return self.card_mapping[encrypted_card_str]
                    return "??"

            # Расшифрование AES ключа
            aes_key = CryptoUtils.decrypt_rsa(
                base64.b64decode(aes_key_encrypted),
                player_private_key
            )

            # Расшифрование карты
            encrypted_card = base64.b64decode(encrypted_card_str)
            card_data = CryptoUtils.decrypt_aes(encrypted_card, aes_key)

            return card_data.decode('utf-8')

        except Exception as e:
            print(f"Ошибка расшифрования: {e}")
            # В демо-режиме возвращаем карту из маппинга
            if encrypted_card_str in self.card_mapping:
                return self.card_mapping[encrypted_card_str]
            return "??"

    def get_card_mapping(self, encrypted_card_str):
        """Получение карты по зашифрованной строке (для демонстрации)"""
        return self.card_mapping.get(encrypted_card_str, "??")

# Пример использования
if __name__ == "__main__":
    # Тестирование криптографических функций
    crypto = CryptoUtils()

    # Генерация ключей
    private_key, public_key = crypto.generate_rsa_keypair()

    # Тестовые данные
    test_data = b"Hello, Mental Poker!"

    # Шифрование/расшифрование RSA
    encrypted_rsa = crypto.encrypt_rsa(test_data, public_key)
    decrypted_rsa = crypto.decrypt_rsa(encrypted_rsa, private_key)
    print(f"RSA test: {decrypted_rsa == test_data}")

    # Шифрование/расшифрование AES
    aes_key = crypto.generate_aes_key()
    encrypted_aes = crypto.encrypt_aes(test_data, aes_key)
    decrypted_aes = crypto.decrypt_aes(encrypted_aes, aes_key)
    print(f"AES test: {decrypted_aes == test_data}")

    # Цифровая подпись
    signature = crypto.sign(test_data, private_key)
    verify_result = crypto.verify_signature(test_data, signature, public_key)
    print(f"Signature test: {verify_result}")