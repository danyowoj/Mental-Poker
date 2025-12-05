"""
Графический клиент для ментального покера RSA (с исправленным отображением карт)
"""

import asyncio
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PokerClientGUI')


class PokerClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎲 Ментальный покер RSA")
        self.root.geometry("1200x750")

        # Иконка (если есть)
        try:
            self.root.iconbitmap('poker.ico')
        except:
            pass

        # Переменные состояния
        self.reader = None
        self.writer = None
        self.player_id = None
        self.game_id = None
        self.connected = False
        self.my_turn = False
        self.my_cards = []
        self.community_cards = []
        self.common_n = None
        self.e = None
        self.d = None
        self.chips = 1000
        self.pot = 0
        self.current_bet = 0
        self.player_order = []

        # Переменные для отображения статуса
        self.connection_status = tk.StringVar(value="🔴 Не подключено")

        # Шрифты
        self.card_font = ("Courier", 16, "bold")
        self.title_font = ("Arial", 12, "bold")
        self.info_font = ("Arial", 10)

        # Цвета
        self.colors = {
            'spade': "#000080",      # Темно-синий для пик
            'club': "#000080",       # Темно-синий для треф
            'heart': "#FF0000",      # Красный для черв
            'diamond': "#FF0000",    # Красный для бубен
            'background': "#f0f0f0",
            'frame_bg': "#ffffff",
            'active': "#4CAF50",
            'inactive': "#cccccc",
            'error': "#ff4444",
            'success': "#44ff44"
        }

        # Создаем интерфейс
        self.create_widgets()

        # Поток для асинхронных операций
        self.loop = None
        self.thread = None

    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Основной контейнер
        main_container = ttk.Frame(self.root, padding="5")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка расширения
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Верхняя панель: подключение
        connection_frame = ttk.LabelFrame(main_container, text="Подключение к серверу", padding="10")
        connection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Поля для ввода
        ttk.Label(connection_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.host_entry = ttk.Entry(connection_frame, width=20)
        self.host_entry.insert(0, "localhost")
        self.host_entry.grid(row=0, column=1, padx=(0, 10))

        ttk.Label(connection_frame, text="Порт:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.port_entry = ttk.Entry(connection_frame, width=10)
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=0, column=3, padx=(0, 10))

        # Кнопки подключения
        self.connect_btn = ttk.Button(
            connection_frame,
            text="Подключиться",
            command=self.connect_to_server,
            style="Accent.TButton"
        )
        self.connect_btn.grid(row=0, column=4, padx=(0, 10))

        self.disconnect_btn = ttk.Button(
            connection_frame,
            text="Отключиться",
            command=self.disconnect_from_server,
            state=tk.DISABLED
        )
        self.disconnect_btn.grid(row=0, column=5)

        # Статус подключения
        ttk.Label(connection_frame, text="Статус:").grid(row=0, column=6, padx=(20, 5))
        self.status_label = ttk.Label(connection_frame, textvariable=self.connection_status)
        self.status_label.grid(row=0, column=7)

        # Основная область - создаем фрейм для разделения на левую и правую части
        main_game_frame = ttk.Frame(main_container)
        main_game_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_game_frame.columnconfigure(0, weight=1)  # Левая колонка (1/3)
        main_game_frame.columnconfigure(1, weight=2)  # Правая колонка (2/3)
        main_game_frame.rowconfigure(0, weight=1)

        # Левая колонка (1/3 ширины) - карты и информация
        left_frame = ttk.Frame(main_game_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)

        # Карты игрока
        player_frame = ttk.LabelFrame(left_frame, text="Ваши карты", padding="10")
        player_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        player_frame.columnconfigure(0, weight=1)

        # Контейнер для карт игрока - ИСПРАВЛЕНО: используем Frame вместо создания метки
        self.player_cards_container = ttk.Frame(player_frame)
        self.player_cards_container.grid(row=0, column=0, pady=10, sticky=(tk.W, tk.E))

        # Общие карты
        community_frame = ttk.LabelFrame(left_frame, text="Карты на столе", padding="10")
        community_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        community_frame.columnconfigure(0, weight=1)

        # Контейнер для общих карт - ИСПРАВЛЕНО: используем Frame
        self.community_cards_container = ttk.Frame(community_frame)
        self.community_cards_container.grid(row=0, column=0, pady=10, sticky=(tk.W, tk.E))

        # Информация об игре
        info_frame = ttk.LabelFrame(left_frame, text="Информация об игре", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(1, weight=1)

        # Таблица информации
        info_rows = [
            ("ID игрока:", "player_id_display", "Не подключен"),
            ("ID игры:", "game_id_display", "Нет"),
            ("Ваши фишки:", "chips_display", "1000"),
            ("Банк:", "pot_display", "0"),
            ("Текущая ставка:", "bet_display", "0"),
            ("Очередь хода:", "turn_display", "Ожидание..."),
            ("Ключ RSA (e):", "e_display", "Не сгенерирован"),
        ]

        for i, (label_text, attr_name, default_value) in enumerate(info_rows):
            ttk.Label(info_frame, text=label_text, font=self.info_font).grid(
                row=i, column=0, sticky=tk.W, pady=3, padx=(0, 10)
            )
            label = ttk.Label(info_frame, text=default_value, font=self.info_font)
            label.grid(row=i, column=1, sticky=tk.W, pady=3)
            setattr(self, attr_name, label)

        # Особый стиль для метки хода
        self.turn_display.config(foreground="red")

        # Правая колонка (2/3 ширины) - действия и управление
        right_frame = ttk.Frame(main_game_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)

        # Создаем Notebook для правой колонки
        right_notebook = ttk.Notebook(right_frame)
        right_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Вкладка 1: Действия
        actions_tab = ttk.Frame(right_notebook, padding="10")
        right_notebook.add(actions_tab, text="🎮 Действия")
        self.setup_actions_tab(actions_tab)

        # Вкладка 2: Управление игрой
        game_control_tab = ttk.Frame(right_notebook, padding="10")
        right_notebook.add(game_control_tab, text="⚙️ Управление")
        self.setup_game_control_tab(game_control_tab)

        # Вкладка 3: Чат
        chat_tab = ttk.Frame(right_notebook, padding="10")
        right_notebook.add(chat_tab, text="💬 Чат")
        self.setup_chat_tab(chat_tab)

        # Нижняя панель: лог
        log_frame = ttk.LabelFrame(main_container, text="Лог событий", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def setup_actions_tab(self, parent):
        """Настройка вкладки действий"""
        parent.columnconfigure(0, weight=1)

        # Поле для ставки
        bet_frame = ttk.LabelFrame(parent, text="Ставка", padding="10")
        bet_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(bet_frame, text="Сумма:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.bet_amount = ttk.Entry(bet_frame, width=15, state=tk.DISABLED)
        self.bet_amount.grid(row=0, column=1, padx=(0, 10), sticky=tk.W)

        # Кнопки действий
        actions_grid = ttk.LabelFrame(parent, text="Игровые действия", padding="10")
        actions_grid.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Создаем сетку 3x2 для кнопок
        actions = [
            ("Fold", self.fold, 0, 0),
            ("Check", self.check, 0, 1),
            ("Call", self.call, 0, 2),
            ("Bet", self.bet, 1, 0),
            ("Raise", self.raise_bet, 1, 1),
            ("All-in", self.allin, 1, 2),
        ]

        for text, command, row, col in actions:
            btn = ttk.Button(
                actions_grid,
                text=text,
                command=command,
                width=10
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky=tk.EW)
            setattr(self, f"{text.lower().replace('-', '_')}_btn", btn)

        # Равномерное распределение кнопок
        for i in range(3):
            actions_grid.columnconfigure(i, weight=1)

        # Индикатор хода
        turn_frame = ttk.LabelFrame(parent, text="Статус хода", padding="10")
        turn_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        self.turn_indicator = ttk.Label(
            turn_frame,
            text="⏳ Ожидайте своего хода",
            font=("Arial", 12),
            foreground="red"
        )
        self.turn_indicator.pack(pady=5)

    def setup_game_control_tab(self, parent):
        """Настройка вкладки управления игрой"""
        parent.columnconfigure(0, weight=1)

        # Создание/присоединение к игре
        game_frame = ttk.LabelFrame(parent, text="Управление игрой", padding="10")
        game_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.create_game_btn = ttk.Button(
            game_frame,
            text="Создать новую игру",
            command=self.create_game,
            state=tk.DISABLED,
            width=20
        )
        self.create_game_btn.pack(fill=tk.X, pady=(0, 10))

        join_frame = ttk.Frame(game_frame)
        join_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(join_frame, text="ID игры:").pack(side=tk.LEFT, padx=(0, 5))
        self.game_id_entry = ttk.Entry(join_frame)
        self.game_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.join_game_btn = ttk.Button(
            join_frame,
            text="Присоединиться",
            command=self.join_game,
            state=tk.DISABLED,
            width=15
        )
        self.join_game_btn.pack(side=tk.RIGHT)

        self.ready_btn = ttk.Button(
            game_frame,
            text="✅ Готов к игре",
            command=self.send_ready,
            state=tk.DISABLED
        )
        self.ready_btn.pack(fill=tk.X)

        # Ключи RSA
        keys_frame = ttk.LabelFrame(parent, text="Криптография RSA", padding="10")
        keys_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        key_info = [
            ("Общий модуль (n):", "n_display", "Не получен"),
            ("Ваш открытый ключ (e):", "e_value_display", "Не сгенерирован"),
            ("Ваш закрытый ключ (d):", "d_value_display", "Секретно"),
        ]

        for i, (label_text, attr_name, default_value) in enumerate(key_info):
            ttk.Label(keys_frame, text=label_text).grid(
                row=i, column=0, sticky=tk.W, pady=3, padx=(0, 10)
            )
            label = ttk.Label(keys_frame, text=default_value, font=("Courier", 9))
            label.grid(row=i, column=1, sticky=tk.W, pady=3)
            setattr(self, attr_name, label)

        self.generate_keys_btn = ttk.Button(
            keys_frame,
            text="🔑 Сгенерировать ключи RSA",
            command=self.generate_keys,
            state=tk.DISABLED
        )
        self.generate_keys_btn.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.EW)

        # Управление соединением
        control_frame = ttk.LabelFrame(parent, text="Управление", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        ttk.Button(control_frame, text="🔄 Обновить ключи", command=self.update_keys).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="📡 Проверить соединение", command=self.ping).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="🧹 Очистить лог", command=self.clear_log).pack(fill=tk.X)

    def setup_chat_tab(self, parent):
        """Настройка вкладки чата"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Отображение чата
        self.chat_display = scrolledtext.ScrolledText(parent, height=20, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))

        # Поле ввода
        chat_input_frame = ttk.Frame(parent)
        chat_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.chat_input = ttk.Entry(chat_input_frame)
        self.chat_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.chat_input.bind('<Return>', lambda e: self.send_chat())

        ttk.Button(chat_input_frame, text="Отправить", command=self.send_chat).grid(row=0, column=1)

        # Настройка расширения
        chat_input_frame.columnconfigure(0, weight=1)

    def create_card_widget(self, parent, card_text):
        """Создает виджет карты с правильным цветом"""
        # Определяем цвет карты
        if '♠' in card_text or '♣' in card_text:
            color = self.colors['spade']
        else:
            color = self.colors['heart']

        # Создаем фрейм для карты с рамкой
        card_frame = tk.Frame(parent, bg='white', relief='raised', borderwidth=2)

        # Метка с картой
        card_label = tk.Label(
            card_frame,
            text=card_text,
            font=self.card_font,
            fg=color,
            bg='white',
            padx=10,
            pady=5
        )
        card_label.pack()

        return card_frame

    def display_cards(self, container, cards, default_text):
        """Отображает карты в контейнере или текст по умолчанию"""
        # Очищаем контейнер
        for widget in container.winfo_children():
            widget.destroy()

        if not cards:
            # Показываем текст по умолчанию
            label = ttk.Label(container, text=default_text, font=("Arial", 12))
            label.pack(pady=20)
            return

        # Создаем фрейм для карт
        cards_frame = ttk.Frame(container)
        cards_frame.pack()

        # Отображаем каждую карту
        for card in cards:
            card_widget = self.create_card_widget(cards_frame, card)
            card_widget.pack(side=tk.LEFT, padx=5)

    def update_display(self):
        """Обновление отображения состояния - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # Обновляем статус подключения
        if self.connected:
            self.connection_status.set("🟢 Подключено")
            self.status_label.configure(foreground="green")
        else:
            self.connection_status.set("🔴 Не подключено")
            self.status_label.configure(foreground="red")

        # Обновляем информацию об игре
        self.player_id_display.configure(text=self.player_id or "Не подключен")
        self.game_id_display.configure(text=self.game_id or "Нет")
        self.chips_display.configure(text=str(self.chips))
        self.pot_display.configure(text=str(self.pot))
        self.bet_display.configure(text=str(self.current_bet))

        # Обновляем ключи RSA
        n_display = f"{str(self.common_n)[:20]}..." if self.common_n else "Не получен"
        self.n_display.configure(text=n_display)
        self.e_display.configure(text=str(self.e) if self.e else "Не сгенерирован")
        self.e_value_display.configure(text=str(self.e) if self.e else "Не сгенерирован")
        self.d_value_display.configure(text="Секретно" if self.d else "Не сгенерирован")

        # Обновляем очередь хода
        if self.my_turn:
            self.turn_display.configure(text="СЕЙЧАС ВАШ ХОД!", foreground="green")
            self.turn_indicator.configure(text="✅ СЕЙЧАС ВАШ ХОД!", foreground="green")
            self.enable_action_buttons()
            self.bet_amount.configure(state=tk.NORMAL)
        else:
            self.turn_display.configure(text="Ожидание хода...", foreground="red")
            self.turn_indicator.configure(text="⏳ Ожидайте своего хода", foreground="red")
            self.disable_action_buttons()
            self.bet_amount.configure(state=tk.DISABLED)

        # ОБНОВЛЯЕМ ОТОБРАЖЕНИЕ КАРТ - ИСПРАВЛЕНО
        self.display_cards(
            self.player_cards_container,
            self.my_cards,
            "🃏 Карты еще не разданы"
        )

        self.display_cards(
            self.community_cards_container,
            self.community_cards,
            "🃏 Общие карты еще не открыты"
        )

    def enable_action_buttons(self):
        """Включение кнопок действий"""
        self.fold_btn.configure(state=tk.NORMAL)

        if self.current_bet > 0:
            self.check_btn.configure(state=tk.DISABLED)
            self.call_btn.configure(state=tk.NORMAL)
            self.bet_btn.configure(state=tk.DISABLED)
            self.raise_btn.configure(state=tk.NORMAL)
        else:
            self.check_btn.configure(state=tk.NORMAL)
            self.call_btn.configure(state=tk.DISABLED)
            self.bet_btn.configure(state=tk.NORMAL)
            self.raise_btn.configure(state=tk.DISABLED)

        self.all_in_btn.configure(state=tk.NORMAL)

    def disable_action_buttons(self):
        """Отключение кнопок действий"""
        for btn in [self.fold_btn, self.check_btn, self.call_btn,
                   self.bet_btn, self.raise_btn, self.all_in_btn]:
            btn.configure(state=tk.DISABLED)

    def log(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def chat(self, sender, message):
        """Добавление сообщения в чат"""
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        self.chat_display.see(tk.END)

    # === Сетевые операции ===

    def connect_to_server(self):
        """Подключение к серверу"""
        host = self.host_entry.get()
        port = self.port_entry.get()

        if not port.isdigit():
            messagebox.showerror("Ошибка", "Порт должен быть числом")
            return

        def connect_async():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            try:
                self.loop.run_until_complete(self.async_connect(host, int(port)))
                self.loop.run_until_complete(self.listen_for_messages())
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Ошибка подключения: {e}"))
                self.root.after(0, lambda: self.update_connection_status(False))

        self.thread = threading.Thread(target=connect_async, daemon=True)
        self.thread.start()

    async def async_connect(self, host, port):
        """Асинхронное подключение"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True

            self.root.after(0, lambda: self.log("✅ Подключение к серверу установлено"))
            self.root.after(0, lambda: self.update_connection_status(True))

        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Ошибка подключения: {e}"))
            self.root.after(0, lambda: self.update_connection_status(False))

    def update_connection_status(self, connected):
        """Обновление статуса подключения"""
        self.connected = connected

        if connected:
            self.connect_btn.configure(state=tk.DISABLED)
            self.disconnect_btn.configure(state=tk.NORMAL)
            self.generate_keys_btn.configure(state=tk.NORMAL)
            self.create_game_btn.configure(state=tk.NORMAL)
            self.join_game_btn.configure(state=tk.NORMAL)
        else:
            self.connect_btn.configure(state=tk.NORMAL)
            self.disconnect_btn.configure(state=tk.DISABLED)
            self.generate_keys_btn.configure(state=tk.DISABLED)
            self.create_game_btn.configure(state=tk.DISABLED)
            self.join_game_btn.configure(state=tk.DISABLED)
            self.ready_btn.configure(state=tk.DISABLED)

        self.update_display()

    def disconnect_from_server(self):
        """Отключение от сервера"""
        if self.writer:
            self.writer.close()

        self.connected = False
        self.update_connection_status(False)
        self.log("🔌 Соединение с сервером разорвано")

    # === Обработка сообщений ===

    async def listen_for_messages(self):
        """Прослушивание входящих сообщений"""
        while self.connected:
            try:
                data = await self.reader.readline()
                if not data:
                    break

                message = json.loads(data.decode())
                await self.handle_message(message)

            except Exception as e:
                self.log(f"Ошибка чтения: {e}")
                break

        self.connected = False
        self.update_connection_status(False)
        self.log("🔌 Соединение с сервером разорвано")

    async def handle_message(self, message):
        """Обработка входящего сообщения"""
        msg_type = message.get('type')

        if msg_type == 'welcome':
            self.player_id = message.get('player_id')
            self.common_n = message.get('common_n')
            self.root.after(0, lambda: self.log(f"🎉 {message.get('message')}"))
            self.root.after(0, self.update_display)

        elif msg_type == 'keys_accepted':
            self.e = int(message.get('e'))
            self.d = int(message.get('d'))
            self.root.after(0, lambda: self.log(f"🔑 {message.get('message')}"))
            self.root.after(0, self.update_display)

        elif msg_type == 'game_created':
            self.game_id = message.get('game_id')
            self.root.after(0, lambda: self.log(f"🎮 {message.get('message')}"))
            self.root.after(0, lambda: self.ready_btn.configure(state=tk.NORMAL))
            self.root.after(0, self.update_display)

        elif msg_type == 'game_joined':
            self.game_id = message.get('game_id')
            players = message.get('players', [])
            self.root.after(0, lambda: self.log(f"✅ {message.get('message')}"))
            self.root.after(0, lambda: self.log(f"👥 Игроки: {', '.join(players)}"))
            self.root.after(0, lambda: self.ready_btn.configure(state=tk.NORMAL))
            self.root.after(0, self.update_display)

        elif msg_type == 'player_joined':
            player_id = message.get('player_id')
            self.root.after(0, lambda: self.log(f"👤 Игрок {player_id} присоединился"))

        elif msg_type == 'player_ready':
            player_id = message.get('player_id')
            ready_count = message.get('ready_players', 0)
            total_players = message.get('total_players', 0)
            self.root.after(0, lambda: self.log(f"✅ {player_id} готов ({ready_count}/{total_players})"))

        elif msg_type == 'game_started':
            self.game_id = message.get('game_id')
            self.my_cards = message.get('your_cards', [])
            self.chips = message.get('chips', 1000)
            self.player_order = message.get('player_order', [])

            self.root.after(0, lambda: self.log("\n" + "="*50))
            self.root.after(0, lambda: self.log("🎲 ИГРА НАЧАЛАСЬ!"))
            self.root.after(0, lambda: self.log(f"🃏 Ваши карты: {', '.join(self.my_cards)}"))
            self.root.after(0, lambda: self.log(f"💰 Ваши фишки: {self.chips}"))
            self.root.after(0, lambda: self.log("="*50))

            self.root.after(0, self.update_display)

        elif msg_type == 'game_state_update':
            self.chips = message.get('chips', self.chips)
            self.pot = message.get('pot', self.pot)
            self.current_bet = message.get('current_bet', self.current_bet)
            self.community_cards = message.get('community_cards', self.community_cards)

            self.root.after(0, self.update_display)

        elif msg_type == 'player_action':
            player_id = message.get('player_id')
            action = message.get('action')
            amount = message.get('amount', 0)

            action_text = f"{action}"
            if amount > 0:
                action_text += f" {amount}"

            self.root.after(0, lambda: self.log(f"🎮 {player_id}: {action_text}"))

        elif msg_type == 'phase_changed':
            phase = message.get('phase')
            self.community_cards = message.get('community_cards', [])

            self.root.after(0, lambda: self.log(f"🔄 {message.get('message')}"))
            self.root.after(0, self.update_display)

        elif msg_type == 'your_turn':
            self.my_turn = True
            self.root.after(0, lambda: self.log(f"🎯 {message.get('message')}"))
            self.root.after(0, self.update_display)

        elif msg_type == 'game_result':
            winners = message.get('winners', [])
            pot = message.get('pot', 0)
            player_combinations = message.get('player_combinations', {})
            player_cards = message.get('player_cards', {})

            self.root.after(0, lambda: self.log("\n🏁 " + message.get('message')))
            self.root.after(0, lambda: self.log(f"🏦 Банк: {pot}"))

            # Показываем окно с результатами
            result_text = "Результаты игры:\n\n"
            for player_id, cards in player_cards.items():
                combination = player_combinations.get(player_id, "Неизвестно")
                if player_id == self.player_id:
                    result_text += f"Вы ({player_id}): {', '.join(cards)} - {combination}\n"
                else:
                    result_text += f"{player_id}: {', '.join(cards)} - {combination}\n"

            if self.player_id in winners:
                messagebox.showinfo("🎉 ПОБЕДА!", result_text + f"\nВы выиграли {pot} фишек!")
            else:
                messagebox.showinfo("😔 ПОРАЖЕНИЕ", result_text + "\nВы проиграли. Попробуйте еще раз!")

            self.my_turn = False
            self.root.after(0, self.update_display)

        elif msg_type == 'game_can_restart':
            self.root.after(0, lambda: self.log(f"🔄 {message.get('message')}"))
            self.root.after(0, lambda: self.ready_btn.configure(state=tk.NORMAL))

        elif msg_type == 'chat_message':
            player_id = message.get('player_id')
            text = message.get('text')
            self.root.after(0, lambda: self.chat(player_id, text))

        elif msg_type == 'error':
            self.root.after(0, lambda: self.log(f"❌ Ошибка: {message.get('message')}"))

        else:
            self.root.after(0, lambda: self.log(f"📨 Неизвестное сообщение: {message}"))

    # === Действия игрока ===

    async def send_message(self, message):
        """Отправка сообщения на сервер"""
        if not self.connected or not self.writer:
            self.log("❌ Нет подключения к серверу")
            return

        try:
            data = json.dumps(message).encode() + b'\n'
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            self.log(f"❌ Ошибка отправки: {e}")
            self.connected = False

    def generate_keys(self):
        """Генерация ключей RSA"""
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(self.exchange_keys(), self.loop)

    async def exchange_keys(self):
        """Обмен ключами с сервером"""
        await self.send_message({
            'type': 'exchange_keys'
        })

    def create_game(self):
        """Создание новой игры"""
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.send_message({'type': 'create_game'}),
                self.loop
            )

    def join_game(self):
        """Присоединение к игре"""
        game_id = self.game_id_entry.get().strip()
        if not game_id:
            messagebox.showwarning("Внимание", "Введите ID игры")
            return

        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.send_message({
                    'type': 'join_game',
                    'game_id': game_id
                }),
                self.loop
            )

    def send_ready(self):
        """Отправка готовности"""
        if not self.game_id:
            messagebox.showwarning("Внимание", "Сначала присоединитесь к игре")
            return

        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.send_message({
                    'type': 'player_ready',
                    'game_id': self.game_id
                }),
                self.loop
            )

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
            asyncio.run_coroutine_threadsafe(
                self.send_message({
                    'type': 'player_action',
                    'game_id': self.game_id,
                    'action': action,
                    'amount': amount
                }),
                self.loop
            )

    def fold(self):
        """Сброс карт"""
        self.send_action('fold')

    def check(self):
        """Пропуск хода"""
        self.send_action('check')

    def call(self):
        """Принятие ставки"""
        self.send_action('call')

    def bet(self):
        """Ставка"""
        try:
            amount = int(self.bet_amount.get())
            if amount <= 0:
                raise ValueError
            if amount > self.chips:
                messagebox.showwarning("Внимание", "Недостаточно фишек")
                return
            self.send_action('bet', amount)
            self.bet_amount.delete(0, tk.END)
        except ValueError:
            messagebox.showwarning("Внимание", "Введите корректную сумму")

    def raise_bet(self):
        """Повышение ставки"""
        try:
            amount = int(self.bet_amount.get())
            if amount <= self.current_bet:
                messagebox.showwarning("Внимание", f"Повышение должно быть больше {self.current_bet}")
                return
            if amount > self.chips:
                messagebox.showwarning("Внимание", "Недостаточно фишек")
                return
            self.send_action('raise', amount)
            self.bet_amount.delete(0, tk.END)
        except ValueError:
            messagebox.showwarning("Внимание", "Введите корректную сумму")

    def allin(self):
        """All-in (ставка всеми фишками)"""
        self.send_action('bet', self.chips)

    def send_chat(self):
        """Отправка сообщения в чат"""
        text = self.chat_input.get().strip()
        if not text:
            return

        if self.loop and self.connected:
            message = {
                'type': 'chat_message',
                'text': text
            }

            if self.game_id:
                message['game_id'] = self.game_id

            asyncio.run_coroutine_threadsafe(
                self.send_message(message),
                self.loop
            )

        self.chat_input.delete(0, tk.END)

    # === Вспомогательные методы ===

    def update_keys(self):
        """Обновление ключей RSA"""
        self.generate_keys()

    def ping(self):
        """Проверка соединения"""
        if self.loop and self.connected:
            asyncio.run_coroutine_threadsafe(
                self.send_message({'type': 'ping'}),
                self.loop
            )

    def clear_log(self):
        """Очистка лога"""
        self.log_text.delete(1.0, tk.END)

    def run(self):
        """Запуск GUI"""
        self.root.mainloop()


def main():
    """Точка входа"""
    client = PokerClientGUI()
    client.run()


if __name__ == "__main__":
    main()
