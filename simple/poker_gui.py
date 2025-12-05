"""
Графический клиент для ментального покера RSA (исправленная версия)
"""

import asyncio
import json
import logging
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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
        self.root.geometry("1000x700")

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

        # Стили
        self.setup_styles()

        # Создаем интерфейс
        self.create_widgets()

        # Поток для асинхронных операций
        self.loop = None
        self.thread = None

    def setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')

        # Настраиваем стили кнопок
        style.configure('Accent.TButton',
                       background='#3498db',
                       foreground='white',
                       font=('Arial', 10, 'bold'))

    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Основной контейнер
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка расширения
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

        # Верхняя панель: подключение
        connection_frame = ttk.LabelFrame(main_container, text="Подключение к серверу", padding="10")
        connection_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Поля для ввода
        ttk.Label(connection_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.host_entry = ttk.Entry(connection_frame, width=15)
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

        # Основная область
        notebook = ttk.Notebook(main_container)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Вкладка 1: Игра
        game_tab = ttk.Frame(notebook, padding="10")
        notebook.add(game_tab, text="🎮 Игра")
        self.setup_game_tab(game_tab)

        # Вкладка 2: Управление
        control_tab = ttk.Frame(notebook, padding="10")
        notebook.add(control_tab, text="⚙️ Управление")
        self.setup_control_tab(control_tab)

        # Вкладка 3: О программе
        about_tab = ttk.Frame(notebook, padding="10")
        notebook.add(about_tab, text="ℹ️ О программе")
        self.setup_about_tab(about_tab)

        # Нижняя панель: лог
        log_frame = ttk.LabelFrame(main_container, text="Лог событий", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def setup_game_tab(self, parent):
        """Настройка вкладки игры"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Левая панель: карты
        left_panel = ttk.Frame(parent)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Карты игрока
        player_frame = ttk.LabelFrame(left_panel, text="Ваши карты", padding="10")
        player_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        player_frame.columnconfigure(0, weight=1)

        self.player_cards_label = ttk.Label(
            player_frame,
            text="🃏 Карты еще не разданы",
            font=("Arial", 16),
            anchor=tk.CENTER
        )
        self.player_cards_label.grid(row=0, column=0, pady=20)

        # Общие карты
        community_frame = ttk.LabelFrame(left_panel, text="Карты на столе", padding="10")
        community_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        community_frame.columnconfigure(0, weight=1)

        self.community_cards_label = ttk.Label(
            community_frame,
            text="🃏 Общие карты еще не открыты",
            font=("Arial", 14),
            anchor=tk.CENTER
        )
        self.community_cards_label.grid(row=0, column=0, pady=10)

        # Информация об игре
        info_frame = ttk.LabelFrame(left_panel, text="Информация об игре", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        info_grid = ttk.Frame(info_frame)
        info_grid.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # Сетка информации
        ttk.Label(info_grid, text="ID игрока:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.player_id_display = ttk.Label(info_grid, text="Не подключен")
        self.player_id_display.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(info_grid, text="ID игры:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.game_id_display = ttk.Label(info_grid, text="Нет")
        self.game_id_display.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(info_grid, text="Ваши фишки:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.chips_display = ttk.Label(info_grid, text="1000")
        self.chips_display.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(info_grid, text="Банк:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.pot_display = ttk.Label(info_grid, text="0")
        self.pot_display.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(info_grid, text="Текущая ставка:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.bet_display = ttk.Label(info_grid, text="0")
        self.bet_display.grid(row=4, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(info_grid, text="Очередь хода:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.turn_display = ttk.Label(info_grid, text="Ожидание...", foreground="red")
        self.turn_display.grid(row=5, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # Правая панель: действия
        right_panel = ttk.Frame(parent)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)

        # Действия в игре
        actions_frame = ttk.LabelFrame(right_panel, text="Действия", padding="10")
        actions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        # Поле для ставки
        bet_frame = ttk.Frame(actions_frame)
        bet_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(bet_frame, text="Сумма:").pack(side=tk.LEFT, padx=(0, 5))
        self.bet_amount = ttk.Entry(bet_frame, width=15, state=tk.DISABLED)
        self.bet_amount.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопки действий
        self.fold_btn = ttk.Button(actions_frame, text="Fold", command=self.fold, state=tk.DISABLED)
        self.fold_btn.grid(row=1, column=0, padx=5, pady=5, sticky=tk.EW)

        self.check_btn = ttk.Button(actions_frame, text="Check", command=self.check, state=tk.DISABLED)
        self.check_btn.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        self.call_btn = ttk.Button(actions_frame, text="Call", command=self.call, state=tk.DISABLED)
        self.call_btn.grid(row=1, column=2, padx=5, pady=5, sticky=tk.EW)

        self.bet_btn = ttk.Button(actions_frame, text="Bet", command=self.bet, state=tk.DISABLED)
        self.bet_btn.grid(row=2, column=0, padx=5, pady=5, sticky=tk.EW)

        self.raise_btn = ttk.Button(actions_frame, text="Raise", command=self.raise_bet, state=tk.DISABLED)
        self.raise_btn.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)

        self.allin_btn = ttk.Button(actions_frame, text="All-in", command=self.allin, state=tk.DISABLED)
        self.allin_btn.grid(row=2, column=2, padx=5, pady=5, sticky=tk.EW)

        # Управление игрой
        game_control_frame = ttk.LabelFrame(right_panel, text="Управление игрой", padding="10")
        game_control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))

        self.create_game_btn = ttk.Button(
            game_control_frame,
            text="Создать игру",
            command=self.create_game,
            state=tk.DISABLED
        )
        self.create_game_btn.pack(fill=tk.X, pady=(0, 5))

        join_frame = ttk.Frame(game_control_frame)
        join_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(join_frame, text="ID игры:").pack(side=tk.LEFT, padx=(0, 5))
        self.game_id_entry = ttk.Entry(join_frame)
        self.game_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.join_game_btn = ttk.Button(
            join_frame,
            text="Присоединиться",
            command=self.join_game,
            state=tk.DISABLED
        )
        self.join_game_btn.pack(side=tk.RIGHT)

        self.ready_btn = ttk.Button(
            game_control_frame,
            text="Готов к игре",
            command=self.send_ready,
            state=tk.DISABLED
        )
        self.ready_btn.pack(fill=tk.X)

        # Чат
        chat_frame = ttk.LabelFrame(right_panel, text="Чат", padding="10")
        chat_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=10, wrap=tk.WORD)
        self.chat_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.chat_input = ttk.Entry(chat_input_frame)
        self.chat_input.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.chat_input.bind('<Return>', lambda e: self.send_chat())

        ttk.Button(chat_input_frame, text="Отправить", command=self.send_chat).grid(row=0, column=1)

    def setup_control_tab(self, parent):
        """Настройка вкладки управления"""
        parent.columnconfigure(0, weight=1)

        # Ключи RSA
        keys_frame = ttk.LabelFrame(parent, text="Ключи RSA", padding="10")
        keys_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(keys_frame, text="Общий модуль (n):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.n_display = ttk.Label(keys_frame, text="Не получен")
        self.n_display.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(keys_frame, text="Открытый ключ (e):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.e_display = ttk.Label(keys_frame, text="Не сгенерирован")
        self.e_display.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(keys_frame, text="Закрытый ключ (d):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.d_display = ttk.Label(keys_frame, text="Секретно")
        self.d_display.grid(row=2, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        self.generate_keys_btn = ttk.Button(
            keys_frame,
            text="Сгенерировать ключи",
            command=self.generate_keys,
            state=tk.DISABLED
        )
        self.generate_keys_btn.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.EW)

        # Статистика
        stats_frame = ttk.LabelFrame(parent, text="Статистика", padding="10")
        stats_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(stats_frame, text="Подключенные игроки:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.players_display = ttk.Label(stats_frame, text="0")
        self.players_display.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        ttk.Label(stats_frame, text="Активные игры:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.games_display = ttk.Label(stats_frame, text="0")
        self.games_display.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(10, 0))

        # Управление
        control_frame = ttk.LabelFrame(parent, text="Управление", padding="10")
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        ttk.Button(control_frame, text="Обновить ключи", command=self.update_keys).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Проверить соединение", command=self.ping).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(control_frame, text="Очистить лог", command=self.clear_log).pack(fill=tk.X)

    def setup_about_tab(self, parent):
        """Настройка вкладки о программе"""
        parent.columnconfigure(0, weight=1)

        about_text = """
🎲 МЕНТАЛЬНЫЙ ПОКЕР С RSA

Версия: 1.0.0

🔐 КРИПТОГРАФИЧЕСКАЯ ОСНОВА:
Алгоритм ментального покера позволяет играть в покер
по интернету без доверенного сервера, который знает
карты игроков.

📋 ОСНОВНЫЕ ПРИНЦИПЫ:
1. Сервер генерирует общий модуль RSA n = p * q
2. Каждый игрок генерирует свою пару ключей (e_i, d_i)
3. Карты представляются числами M_j, где 1 < M_j < n
4. Все игроки последовательно шифруют колоду
5. Каждый игрок расшифровывает свои карты в обратном порядке

⚡ ПРЕИМУЩЕСТВА:
• Сервер не знает карт игроков
• Колода честно перемешана всеми игроками
• Невозможно подменить карты
• Полная прозрачность процесса

👨‍💻 РАЗРАБОТЧИКИ:
Учебный проект по криптографии
Группа: Крипто-2024

📞 ПОДДЕРЖКА:
По вопросам и предложениям обращайтесь
к преподавателю курса.
"""

        about_label = ttk.Label(parent, text=about_text, justify=tk.LEFT, font=("Arial", 10))
        about_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        ttk.Separator(parent, orient='horizontal').grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(parent, text="© 2024 Ментальный покер RSA. Все права защищены.",
                 font=("Arial", 8), foreground="gray").grid(row=2, column=0)

    def update_display(self):
        """Обновление отображения состояния"""
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
        self.n_display.configure(text=f"{str(self.common_n)[:20]}..." if self.common_n else "Не получен")
        self.e_display.configure(text=str(self.e) if self.e else "Не сгенерирован")

        # Обновляем очередь хода
        if self.my_turn:
            self.turn_display.configure(text="СЕЙЧАС ВАШ ХОД!", foreground="green")
            self.enable_action_buttons()
            self.bet_amount.configure(state=tk.NORMAL)
        else:
            self.turn_display.configure(text="Ожидание хода...", foreground="red")
            self.disable_action_buttons()
            self.bet_amount.configure(state=tk.DISABLED)

        # Обновляем отображение карт
        self.update_cards_display()

    def update_cards_display(self):
        """Обновление отображения карт"""
        # Карты игрока
        if self.my_cards:
            cards_text = ""
            for card in self.my_cards:
                # Определяем цвет карты
                if '♠' in card or '♣' in card:
                    color = "#000080"  # Темно-синий
                else:
                    color = "#FF0000"  # Красный

                cards_text += f"[{card}] "

            self.player_cards_label.configure(text=cards_text.strip())
        else:
            self.player_cards_label.configure(text="🃏 Карты еще не разданы")

        # Общие карты
        if self.community_cards:
            cards_text = ""
            for card in self.community_cards:
                if '♠' in card or '♣' in card:
                    color = "#000080"
                else:
                    color = "#FF0000"
                cards_text += f"[{card}] "

            self.community_cards_label.configure(text=cards_text.strip())
        else:
            self.community_cards_label.configure(text="🃏 Общие карты еще не открыты")

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

        self.allin_btn.configure(state=tk.NORMAL)

    def disable_action_buttons(self):
        """Отключение кнопок действий"""
        for btn in [self.fold_btn, self.check_btn, self.call_btn,
                   self.bet_btn, self.raise_btn, self.allin_btn]:
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

            self.root.after(0, lambda: self.log("\n🏁 " + message.get('message')))
            self.root.after(0, lambda: self.log(f"🏦 Банк: {pot}"))

            if self.player_id in winners:
                messagebox.showinfo("Результат", "🎉 Поздравляем! Вы победили!")
            else:
                messagebox.showinfo("Результат", "😔 Вы проиграли. Попробуйте еще раз!")

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
