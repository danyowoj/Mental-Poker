"""
Графический клиент ментального покера с криптографической поддержкой
"""

import asyncio
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PokerClientGUI')

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

class PokerClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ментальный покер")
        self.root.geometry("1200x800")

        # Переменные состояния
        self.reader = None
        self.writer = None
        self.player_id = None
        self.game_id = None
        self.connected = False
        self.my_turn = False
        self.my_cards = []
        self.encrypted_cards = []
        self.encrypted_keys = []
        self.private_key = None
        self.public_key = None
        self.community_cards = []
        self.chips = 1000
        self.pot = 0
        self.current_bet = 0

        # Создаем интерфейс
        self.create_widgets()

        # Поток для асинхронных операций
        self.loop = None
        self.thread = None

    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Основные фреймы
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка расширения колонок
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Фрейм подключения
        connection_frame = ttk.LabelFrame(main_frame, text="Подключение", padding="10")
        connection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(connection_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W)
        self.host_entry = ttk.Entry(connection_frame, width=15)
        self.host_entry.insert(0, "localhost")
        self.host_entry.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(connection_frame, text="Порт:").grid(row=0, column=2, sticky=tk.W)
        self.port_entry = ttk.Entry(connection_frame, width=10)
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=0, column=3, padx=(0, 10))

        self.connect_btn = ttk.Button(connection_frame, text="Подключиться", command=self.connect_to_server)
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))

        self.disconnect_btn = ttk.Button(connection_frame, text="Отключиться", command=self.disconnect_from_server, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=5)

        # Фрейм управления игрой
        game_frame = ttk.LabelFrame(main_frame, text="Управление игрой", padding="10")
        game_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.create_game_btn = ttk.Button(game_frame, text="Создать игру", command=self.create_game, state=tk.DISABLED)
        self.create_game_btn.grid(row=0, column=0, padx=(0, 10))

        ttk.Label(game_frame, text="ID игры:").grid(row=0, column=1, sticky=tk.W)
        self.game_id_entry = ttk.Entry(game_frame, width=20)
        self.game_id_entry.grid(row=0, column=2, padx=(0, 10))

        self.join_game_btn = ttk.Button(game_frame, text="Присоединиться", command=self.join_game, state=tk.DISABLED)
        self.join_game_btn.grid(row=0, column=3, padx=(0, 10))

        self.ready_btn = ttk.Button(game_frame, text="Готов", command=self.send_ready, state=tk.DISABLED)
        self.ready_btn.grid(row=0, column=4)

        # Основная область игры с прокруткой
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        # Создаем Canvas для прокрутки
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Размещаем Canvas и Scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Область игры внутри прокручиваемого фрейма
        game_area = ttk.Frame(scrollable_frame)
        game_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        game_area.columnconfigure(0, weight=2)
        game_area.columnconfigure(1, weight=1)
        game_area.rowconfigure(0, weight=1)

        # Левая панель - карты и информация
        left_panel = ttk.Frame(game_area)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Карты игрока
        player_cards_frame = ttk.LabelFrame(left_panel, text="Ваши карты", padding="10")
        player_cards_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        self.player_cards_container = ttk.Frame(player_cards_frame)
        self.player_cards_container.pack()

        self.player_cards_label = ttk.Label(self.player_cards_container, text="Не разданы", font=("Arial", 14))
        self.player_cards_label.pack()

        # Карты на столе
        community_cards_frame = ttk.LabelFrame(left_panel, text="Карты на столе", padding="10")
        community_cards_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        self.community_cards_container = ttk.Frame(community_cards_frame)
        self.community_cards_container.pack()

        self.community_cards_label = ttk.Label(self.community_cards_container, text="Нет карт", font=("Arial", 14))
        self.community_cards_label.pack()

        # Информация об игре
        info_frame = ttk.LabelFrame(left_panel, text="Информация об игре", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        info_frame.columnconfigure(1, weight=1)

        ttk.Label(info_frame, text="ID игрока:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.player_id_label = ttk.Label(info_frame, text="Не подключен")
        self.player_id_label.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="ID игры:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.game_id_label = ttk.Label(info_frame, text="Нет")
        self.game_id_label.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Ваши фишки:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.chips_label = ttk.Label(info_frame, text="1000")
        self.chips_label.grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Банк:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.pot_label = ttk.Label(info_frame, text="0")
        self.pot_label.grid(row=3, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Текущая ставка:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.current_bet_label = ttk.Label(info_frame, text="0")
        self.current_bet_label.grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Label(info_frame, text="Очередь хода:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.turn_label = ttk.Label(info_frame, text="Ожидание...", foreground="red")
        self.turn_label.grid(row=5, column=1, sticky=tk.W, pady=2)

        # Правая панель - кнопки действий, чат и лог
        right_panel = ttk.Frame(game_area)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=0)
        right_panel.rowconfigure(1, weight=1)
        right_panel.rowconfigure(2, weight=1)

        # Кнопки действий (в правой панели над чатом)
        actions_frame = ttk.LabelFrame(right_panel, text="Действия", padding="10")
        actions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        # Поле для ставки
        bet_frame = ttk.Frame(actions_frame)
        bet_frame.grid(row=0, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(bet_frame, text="Сумма ставки:").pack(side=tk.LEFT, padx=(0, 5))
        self.bet_amount_entry = ttk.Entry(bet_frame, width=10, state=tk.DISABLED)
        self.bet_amount_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопки действий в сетке
        self.fold_btn = ttk.Button(actions_frame, text="Fold", command=lambda: self.send_action('fold'), state=tk.DISABLED)
        self.fold_btn.grid(row=1, column=0, padx=5, pady=5)

        self.check_btn = ttk.Button(actions_frame, text="Check", command=lambda: self.send_action('check'), state=tk.DISABLED)
        self.check_btn.grid(row=1, column=1, padx=5, pady=5)

        self.call_btn = ttk.Button(actions_frame, text="Call", command=lambda: self.send_action('call'), state=tk.DISABLED)
        self.call_btn.grid(row=1, column=2, padx=5, pady=5)

        self.bet_btn = ttk.Button(actions_frame, text="Bet", command=self.make_bet, state=tk.DISABLED)
        self.bet_btn.grid(row=1, column=3, padx=5, pady=5)

        self.raise_btn = ttk.Button(actions_frame, text="Raise", command=self.make_raise, state=tk.DISABLED)
        self.raise_btn.grid(row=1, column=4, padx=5, pady=5)

        # Чат
        chat_frame = ttk.LabelFrame(right_panel, text="Чат", padding="10")
        chat_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_text = scrolledtext.ScrolledText(chat_frame, height=15, wrap=tk.WORD)
        self.chat_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.chat_entry.bind('<Return>', lambda event: self.send_chat())

        ttk.Button(chat_input_frame, text="Отправить", command=self.send_chat).grid(row=0, column=1)

        # Лог событий
        log_frame = ttk.LabelFrame(right_panel, text="Лог событий", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def update_card_display(self, cards, container, default_text):
        """Обновляет отображение карт с цветами"""
        # Очищаем контейнер
        for widget in container.winfo_children():
            widget.destroy()

        if not cards:
            label = ttk.Label(container, text=default_text, font=("Arial", 14))
            label.pack()
            return

        # Создаем фрейм для карт
        cards_frame = ttk.Frame(container)
        cards_frame.pack()

        for card in cards:
            # Определяем цвет карты
            if card.endswith('♠') or card.endswith('♣'):  # Пики и трефы - темно-синие
                color = "#000080"  # Темно-синий
            else:  # Червы и бубны - красные
                color = "#FF0000"  # Красный

            # Создаем метку с картой и цветом
            card_label = tk.Label(cards_frame, text=card, font=("Arial", 16, "bold"),
                                 foreground=color, background="white",
                                 relief="raised", borderwidth=2, padx=5, pady=5)
            card_label.pack(side=tk.LEFT, padx=2)

    def show_game_result(self, winners, pot, player_combinations, player_cards):
        """Показать окно с результатами игры"""
        result_window = tk.Toplevel(self.root)
        result_window.title("Результаты игры")
        result_window.geometry("600x400")
        result_window.transient(self.root)
        result_window.grab_set()

        # Основной фрейм
        main_frame = ttk.Frame(result_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        if self.player_id in winners:
            if len(winners) == 1:
                title = "🎉 ПОБЕДА!"
                subtitle = "Вы победили!"
            else:
                title = "🎉 НИЧЬЯ!"
                subtitle = "Вы в ничьей!"
        else:
            if len(winners) == 1:
                title = "😔 ПОРАЖЕНИЕ"
                subtitle = f"Победил игрок {winners[0]}"
            else:
                title = "😔 НИЧЬЯ"
                subtitle = f"Ничья между: {', '.join(winners)}"

        ttk.Label(main_frame, text=title, font=("Arial", 20, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text=subtitle, font=("Arial", 14)).pack(pady=(0, 20))

        # Информация о банке
        ttk.Label(main_frame, text=f"🏦 Банк: {pot}", font=("Arial", 12)).pack(pady=(0, 10))

        # Карты всех игроков с их комбинациями
        for player_id, cards in player_cards.items():
            player_frame = ttk.Frame(main_frame)
            player_frame.pack(fill=tk.X, pady=5)

            combination = player_combinations.get(player_id, "Неизвестно")

            if player_id == self.player_id:
                player_text = f"👤 Вы ({player_id}):"
                color = "green"
            else:
                player_text = f"👤 {player_id}:"
                color = "black"

            ttk.Label(player_frame, text=player_text, foreground=color,
                     font=("Arial", 10, "bold")).pack(anchor=tk.W)

            # Отображаем карты игрока с цветами
            cards_frame = ttk.Frame(player_frame)
            cards_frame.pack(anchor=tk.W, pady=2)

            for card in cards:
                if card.endswith('♠') or card.endswith('♣'):
                    card_color = "#000080"  # Темно-синий
                else:
                    card_color = "#FF0000"  # Красный

                card_label = tk.Label(cards_frame, text=card, font=("Arial", 12),
                                     foreground=card_color, background="white",
                                     relief="solid", borderwidth=1, padx=3, pady=2)
                card_label.pack(side=tk.LEFT, padx=1)

            ttk.Label(player_frame, text=f"Комбинация: {combination}",
                     foreground=color).pack(anchor=tk.W)

        # Кнопка закрытия
        ttk.Button(main_frame, text="Закрыть", command=result_window.destroy).pack(pady=(20, 0))

    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def chat_message(self, player_id, text):
        """Добавление сообщения в чат"""
        self.chat_text.insert(tk.END, f"{player_id}: {text}\n")
        self.chat_text.see(tk.END)

    def update_game_state(self):
        """Обновление информации об игре"""
        self.player_id_label.config(text=self.player_id or "Не подключен")
        self.game_id_label.config(text=self.game_id or "Нет")
        self.chips_label.config(text=str(self.chips))
        self.pot_label.config(text=str(self.pot))
        self.current_bet_label.config(text=str(self.current_bet))

        if self.my_turn:
            self.turn_label.config(text="СЕЙЧАС ВАШ ХОД!", foreground="green")
            self.bet_amount_entry.config(state=tk.NORMAL)
        else:
            self.turn_label.config(text="Ожидание хода...", foreground="red")
            self.bet_amount_entry.config(state=tk.DISABLED)

        # Обновление карт с цветами
        self.update_card_display(self.my_cards, self.player_cards_container, "Не разданы")
        self.update_card_display(self.community_cards, self.community_cards_container, "Нет карт")

        # Обновление состояния кнопок согласно правилам покера
        if self.my_turn and self.game_id:
            self.fold_btn.config(state=tk.NORMAL)

            # Если есть текущая ставка
            if self.current_bet > 0:
                # Нельзя делать check при наличии ставки
                self.check_btn.config(state=tk.DISABLED)
                self.call_btn.config(state=tk.NORMAL)
                self.bet_btn.config(state=tk.DISABLED)  # Нельзя сделать bet, только raise
                self.raise_btn.config(state=tk.NORMAL)
            else:
                # Если нет текущей ставки
                self.check_btn.config(state=tk.NORMAL)
                self.call_btn.config(state=tk.DISABLED)  # Нельзя call без ставки
                self.bet_btn.config(state=tk.NORMAL)
                self.raise_btn.config(state=tk.DISABLED)  # Нельзя raise без ставки
        else:
            self.fold_btn.config(state=tk.DISABLED)
            self.check_btn.config(state=tk.DISABLED)
            self.call_btn.config(state=tk.DISABLED)
            self.bet_btn.config(state=tk.DISABLED)
            self.raise_btn.config(state=tk.DISABLED)
            self.bet_amount_entry.config(state=tk.DISABLED)

    def connect_to_server(self):
        """Подключение к серверу"""
        host = self.host_entry.get()
        port = int(self.port_entry.get())

        # Запускаем асинхронное подключение в отдельном потоке
        def connect_async():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            try:
                self.loop.run_until_complete(self.async_connect(host, port))
                self.loop.run_until_complete(self.listen_for_messages())
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"❌ Ошибка: {e}"))

        self.thread = threading.Thread(target=connect_async, daemon=True)
        self.thread.start()

    async def async_connect(self, host, port):
        """Асинхронное подключение"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True

            # Генерация ключей
            self.private_key, self.public_key = CryptoUtils.generate_rsa_keypair()

            self.root.after(0, lambda: self.log_message("✅ Подключение к серверу установлено"))
            self.root.after(0, self.enable_game_controls)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка подключения: {e}"))

    def enable_game_controls(self):
        """Активация элементов управления игрой"""
        self.connect_btn.config(state=tk.DISABLED)
        self.disconnect_btn.config(state=tk.NORMAL)
        self.create_game_btn.config(state=tk.NORMAL)
        self.join_game_btn.config(state=tk.NORMAL)

    def disconnect_from_server(self):
        """Отключение от сервера"""
        if self.writer:
            self.writer.close()
            try:
                self.loop.run_until_complete(self.writer.wait_closed())
            except:
                pass

        self.connected = False
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.create_game_btn.config(state=tk.DISABLED)
        self.join_game_btn.config(state=tk.DISABLED)
        self.ready_btn.config(state=tk.DISABLED)

        self.log_message("🔌 Соединение с сервером разорвано")

    def create_game(self):
        """Создание новой игры"""
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.send_create_game(), self.loop)

    async def send_create_game(self):
        """Отправка запроса на создание игры"""
        await self.send_message({'type': 'create_game'})

    def join_game(self):
        """Присоединение к игре"""
        game_id = self.game_id_entry.get().strip()
        if not game_id:
            messagebox.showwarning("Внимание", "Введите ID игры")
            return

        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.send_join_game(game_id), self.loop)

    async def send_join_game(self, game_id):
        """Отправка запроса на присоединение к игре"""
        self.game_id = game_id
        await self.send_message({
            'type': 'join_game',
            'game_id': game_id
        })

    def send_ready(self):
        """Отправка готовности к игре"""
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.send_ready_message(), self.loop)

    async def send_ready_message(self):
        """Отправка сообщения о готовности"""
        if not self.game_id:
            self.root.after(0, lambda: messagebox.showwarning("Внимание", "Сначала присоединитесь к игре"))
            return

        await self.send_message({
            'type': 'player_ready',
            'game_id': self.game_id
        })

    def make_bet(self):
        """Сделать ставку"""
        try:
            amount = int(self.bet_amount_entry.get())
            if amount <= 0:
                raise ValueError
            if amount > self.chips:
                messagebox.showwarning("Внимание", "Недостаточно фишек")
                return
            self.send_action('bet', amount)
            self.bet_amount_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showwarning("Внимание", "Введите корректную сумму ставки")

    def make_raise(self):
        """Повысить ставку"""
        try:
            amount = int(self.bet_amount_entry.get())
            if amount <= 0:
                raise ValueError
            if amount > self.chips:
                messagebox.showwarning("Внимание", "Недостаточно фишек")
                return
            self.send_action('raise', amount)
            self.bet_amount_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showwarning("Внимание", "Введите корректную сумму повышения")

    def send_action(self, action, amount=0):
        """Отправка игрового действия"""
        if not self.game_id:
            messagebox.showwarning("Внимание", "Сначала присоединитесь к игре")
            return

        if not self.my_turn:
            messagebox.showwarning("Внимание", "Сейчас не ваш ход")
            return

        self.my_turn = False
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.send_action_message(action, amount), self.loop)

    async def send_action_message(self, action, amount):
        """Отправка сообщения с действием"""
        await self.send_message({
            'type': 'player_action',
            'game_id': self.game_id,
            'action': action,
            'amount': amount
        })

    def send_chat(self):
        """Отправка сообщения в чат"""
        text = self.chat_entry.get().strip()
        if not text:
            return

        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.send_chat_message(text), self.loop)
        self.chat_entry.delete(0, tk.END)

    async def send_chat_message(self, text):
        """Отправка сообщения чата"""
        message = {
            'type': 'chat_message',
            'text': text
        }

        if self.game_id:
            message['game_id'] = self.game_id

        await self.send_message(message)

    async def send_message(self, message):
        """Отправка сообщения на сервер"""
        if not self.connected or not self.writer:
            self.root.after(0, lambda: self.log_message("❌ Нет подключения к серверу"))
            return False

        try:
            data = json.dumps(message).encode() + b'\n'
            self.writer.write(data)
            await self.writer.drain()
            return True
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка отправки: {e}"))
            self.connected = False
            return False

    async def send_public_key(self):
        """Отправка открытого ключа на сервер"""
        if not self.public_key:
            self.root.after(0, lambda: self.log_message("❌ Открытый ключ не сгенерирован"))
            return False

        try:
            public_key_str = CryptoUtils.serialize_public_key(self.public_key)
            await self.send_message({
                'type': 'exchange_public_key',
                'public_key': public_key_str
            })
            return True
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка отправки открытого ключа: {e}"))
            return False

    async def listen_for_messages(self):
        """Прослушивание входящих сообщений от сервера"""
        buffer = ""
        while self.connected:
            try:
                data = await self.reader.read(1024)
                if not data:
                    break

                buffer += data.decode()

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        await self.handle_message(json.loads(line))

            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"Ошибка чтения: {e}"))
                break

        self.connected = False
        self.root.after(0, lambda: self.log_message("🔌 Соединение с сервером разорвано"))

    async def handle_message(self, message):
        """Обработка входящего сообщения"""
        msg_type = message.get('type')

        if msg_type == 'welcome':
            self.player_id = message.get('player_id')
            self.root.after(0, lambda: self.log_message(f"🎉 {message.get('message')}"))

            # Отправляем открытый ключ
            await self.send_public_key()

            self.root.after(0, self.update_game_state)

        elif msg_type == 'public_key_accepted':
            self.root.after(0, lambda: self.log_message(f"🔑 {message.get('message')}"))

        elif msg_type == 'game_created':
            self.game_id = message.get('game_id')
            self.root.after(0, lambda: self.log_message(f"🎮 {message.get('message')}"))
            # Активируем кнопку "Готов" при создании игры
            self.root.after(0, lambda: self.ready_btn.config(state=tk.NORMAL))
            self.root.after(0, self.update_game_state)

        elif msg_type == 'game_joined':
            self.game_id = message.get('game_id')
            players = message.get('players', [])
            self.root.after(0, lambda: self.log_message(f"✅ {message.get('message')}"))
            self.root.after(0, lambda: self.log_message(f"👥 Игроки в игре: {', '.join(players)}"))

            self.root.after(0, lambda: self.ready_btn.config(state=tk.NORMAL))
            self.root.after(0, self.update_game_state)

        elif msg_type == 'player_joined':
            player_id = message.get('player_id')
            players = message.get('players', [])
            self.root.after(0, lambda: self.log_message(f"👤 Игрок {player_id} присоединился к игре"))
            self.root.after(0, lambda: self.log_message(f"👥 Теперь игроков: {len(players)}"))

        elif msg_type == 'player_ready':
            player_id = message.get('player_id')
            ready_players = message.get('ready_players', [])
            total_players = message.get('total_players', 0)
            self.root.after(0, lambda: self.log_message(f"✅ Игрок {player_id} готов"))
            self.root.after(0, lambda: self.log_message(f"🎯 Готовы: {len(ready_players)}/{total_players}"))

        elif msg_type == 'game_can_start':
            self.root.after(0, lambda: self.log_message(f"💡 {message.get('message')}"))

        elif msg_type == 'game_started':
            self.game_id = message.get('game_id')
            self.my_cards = message.get('your_cards', [])
            self.encrypted_cards = message.get('encrypted_cards', [])
            self.encrypted_keys = message.get('encrypted_keys', [])
            self.community_cards = message.get('community_cards', [])
            players = message.get('players', [])
            self.chips = message.get('chips', 1000)
            self.pot = 0

            self.root.after(0, lambda: self.log_message("\n" + "="*50))
            self.root.after(0, lambda: self.log_message("🎲 ИГРА НАЧАЛАСЬ!"))
            self.root.after(0, lambda: self.log_message(f"👥 Игроки: {', '.join(players)}"))
            self.root.after(0, lambda: self.log_message(f"🃏 Ваши карты: {', '.join(self.my_cards)}"))
            self.root.after(0, lambda: self.log_message(f"💰 Ваши фишки: {self.chips}"))
            self.root.after(0, lambda: self.log_message("="*50))

            self.ready_btn.config(state=tk.DISABLED)
            self.root.after(0, self.update_game_state)

        elif msg_type == 'game_state_update':
            self.chips = message.get('chips', self.chips)
            self.pot = message.get('pot', self.pot)
            self.current_bet = message.get('current_bet', self.current_bet)
            self.community_cards = message.get('community_cards', self.community_cards)

            self.root.after(0, self.update_game_state)

        elif msg_type == 'player_action':
            player_id = message.get('player_id')
            action = message.get('action')
            amount = message.get('amount', 0)

            action_text = f"{action}"
            if amount > 0:
                action_text += f" {amount}"

            self.root.after(0, lambda: self.log_message(f"🎮 {player_id}: {action_text}"))

        elif msg_type == 'phase_changed':
            phase = message.get('phase')
            self.community_cards = message.get('community_cards', self.community_cards)

            self.root.after(0, lambda: self.log_message(f"\n🔄 {message.get('message')}"))
            if self.community_cards:
                self.root.after(0, lambda: self.log_message(f"🃏 Карты на столе: {', '.join(self.community_cards)}"))

            self.root.after(0, self.update_game_state)

        elif msg_type == 'your_turn':
            self.my_turn = True
            self.root.after(0, lambda: self.log_message(f"\n🎯 {message.get('message')}"))
            self.root.after(0, self.update_game_state)

        elif msg_type == 'game_result':
            winners = message.get('winners', [])
            pot = message.get('pot', 0)
            player_combinations = message.get('player_combinations', {})
            player_cards = message.get('player_cards', {})

            self.root.after(0, lambda: self.log_message(f"\n🏁 {message.get('message')}"))
            self.root.after(0, lambda: self.log_message(f"🏦 Банк: {pot}"))

            self.root.after(0, lambda: self.log_message("\n📋 Карты игроков:"))
            for player_id, cards in player_cards.items():
                combination = player_combinations.get(player_id, "Неизвестно")
                if player_id == self.player_id:
                    self.root.after(0, lambda pid=player_id, c=cards, comb=combination:
                                   self.log_message(f"  👤 Вы ({pid}): {', '.join(c)} - {comb}"))
                else:
                    self.root.after(0, lambda pid=player_id, c=cards, comb=combination:
                                   self.log_message(f"  👤 {pid}: {', '.join(c)} - {comb}"))

            # Показываем окно с результатами
            self.root.after(0, lambda: self.show_game_result(winners, pot, player_combinations, player_cards))

            self.my_turn = False
            self.root.after(0, self.update_game_state)

        elif msg_type == 'game_can_restart':
            self.root.after(0, lambda: self.log_message(f"💡 {message.get('message')}"))
            self.ready_btn.config(state=tk.NORMAL)

        elif msg_type == 'chat_message':
            player_id = message.get('player_id')
            text = message.get('text')
            self.root.after(0, lambda: self.chat_message(player_id, text))

        elif msg_type == 'error':
            self.root.after(0, lambda: self.log_message(f"❌ Ошибка: {message.get('message')}"))

        else:
            self.root.after(0, lambda: self.log_message(f"📨 Неизвестное сообщение: {message}"))

    def run(self):
        """Запуск GUI"""
        self.root.mainloop()

def main():
    """Точка входа для запуска GUI клиента"""
    client = PokerClientGUI()
    client.run()

if __name__ == "__main__":
    main()
