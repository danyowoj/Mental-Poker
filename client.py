"""
Упрощенный клиент для ментального покера
"""

import asyncio
import json
import logging
import random
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PokerClient')

class PokerClient:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.player_id = None
        self.game_id = None
        self.connected = False

    async def connect(self):
        """Подключение к серверу"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            print("✅ Подключение к серверу установлено")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
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
                logger.error(f"Ошибка чтения: {e}")
                break

        self.connected = False
        print("🔌 Соединение с сервером разорвано")

    async def handle_message(self, message):
        """Обработка входящего сообщения"""
        msg_type = message.get('type')

        if msg_type == 'welcome':
            self.player_id = message.get('player_id')
            print(f"🎉 {message.get('message')}")

        elif msg_type == 'game_created':
            self.game_id = message.get('game_id')
            print(f"🎮 {message.get('message')}")

        elif msg_type == 'game_joined':
            self.game_id = message.get('game_id')
            players = message.get('players', [])
            print(f"✅ {message.get('message')}")
            print(f"👥 Игроки в игре: {', '.join(players)}")
            print("💡 Введите 'ready' чтобы отметить готовность")

        elif msg_type == 'player_joined':
            player_id = message.get('player_id')
            players = message.get('players', [])
            print(f"👤 Игрок {player_id} присоединился к игре")
            print(f"👥 Теперь игроков: {len(players)}")

        elif msg_type == 'player_left':
            player_id = message.get('player_id')
            players = message.get('players', [])
            print(f"👋 Игрок {player_id} вышел из игры")
            print(f"👥 Осталось игроков: {len(players)}")

        elif msg_type == 'player_ready':
            player_id = message.get('player_id')
            ready_players = message.get('ready_players', [])
            print(f"✅ Игрок {player_id} готов")
            print(f"🎯 Готовы: {len(ready_players)}/{len(ready_players) + 1}")  # Примерное количество

        elif msg_type == 'game_can_start':
            print(f"💡 {message.get('message')}")

        elif msg_type == 'game_started':
            self.game_id = message.get('game_id')
            your_cards = message.get('your_cards', [])
            players = message.get('players', [])

            print("\n" + "="*50)
            print("🎲 ИГРА НАЧАЛАСЬ!")
            print(f"👥 Игроки: {', '.join(players)}")
            print(f"🃏 Ваши карты: {', '.join(your_cards)}")
            print("="*50)

        elif msg_type == 'game_state':
            print(f"📊 {message.get('message')}")

        elif msg_type == 'player_action':
            player_id = message.get('player_id')
            action = message.get('action')
            amount = message.get('amount', 0)

            action_text = f"{action}"
            if amount > 0:
                action_text += f" {amount}"

            print(f"🎮 {player_id}: {action_text}")

        elif msg_type == 'chat_message':
            player_id = message.get('player_id')
            text = message.get('text')
            print(f"💬 {player_id}: {text}")

        elif msg_type == 'error':
            print(f"❌ Ошибка: {message.get('message')}")

        elif msg_type == 'pong':
            pass  # Игнорируем pong

        else:
            print(f"📨 Неизвестное сообщение: {message}")

    async def send_message(self, message):
        """Отправка сообщения на сервер"""
        if not self.connected or not self.writer:
            print("❌ Нет подключения к серверу")
            return False

        try:
            data = json.dumps(message).encode() + b'\n'
            self.writer.write(data)
            await self.writer.drain()
            return True
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            self.connected = False
            return False

    async def create_game(self):
        """Создание новой игры"""
        return await self.send_message({
            'type': 'create_game'
        })

    async def join_game(self, game_id):
        """Присоединение к существующей игре"""
        self.game_id = game_id
        return await self.send_message({
            'type': 'join_game',
            'game_id': game_id
        })

    async def send_ready(self):
        """Отправка готовности к игре"""
        if not self.game_id:
            print("❌ Сначала присоединитесь к игре")
            return False

        return await self.send_message({
            'type': 'player_ready',
            'game_id': self.game_id
        })

    async def send_action(self, action, amount=0):
        """Отправка игрового действия"""
        if not self.game_id:
            print("❌ Сначала присоединитесь к игре")
            return False

        return await self.send_message({
            'type': 'player_action',
            'game_id': self.game_id,
            'action': action,
            'amount': amount
        })

    async def send_chat(self, text):
        """Отправка сообщения в чат"""
        message = {
            'type': 'chat_message',
            'text': text
        }

        if self.game_id:
            message['game_id'] = self.game_id

        return await self.send_message(message)

    async def run_interactive(self):
        """Интерактивный режим клиента"""
        print("🎮 Клиент ментального покера")
        print("=" * 30)

        # Подключаемся к серверу
        if not await self.connect():
            return

        # Запускаем прослушивание сообщений в фоне
        asyncio.create_task(self.listen_for_messages())

        # Основной цикл взаимодействия
        while self.connected:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\nВведите команду (help для справки): "
                )

                command = user_input.strip().lower()

                if command == 'help':
                    self.show_help()

                elif command == 'create':
                    await self.create_game()

                elif command.startswith('join '):
                    game_id = command[5:].strip()
                    if game_id:
                        await self.join_game(game_id)
                    else:
                        print("❌ Укажите ID игры: join game_1")

                elif command == 'ready':
                    await self.send_ready()

                elif command.startswith('chat '):
                    text = command[5:].strip()
                    if text:
                        await self.send_chat(text)
                    else:
                        print("❌ Укажите текст сообщения")

                elif command in ['fold', 'check', 'call']:
                    await self.send_action(command)

                elif command.startswith('bet '):
                    try:
                        amount = int(command[4:].strip())
                        await self.send_action('bet', amount)
                    except ValueError:
                        print("❌ Укажите сумму ставки: bet 100")

                elif command.startswith('raise '):
                    try:
                        amount = int(command[6:].strip())
                        await self.send_action('raise', amount)
                    except ValueError:
                        print("❌ Укажите сумму повышения: raise 50")

                elif command == 'status':
                    print(f"👤 ID игрока: {self.player_id}")
                    print(f"🎮 ID игры: {self.game_id or 'Нет'}")
                    print(f"🔗 Подключен: {'Да' if self.connected else 'Нет'}")

                elif command in ['quit', 'exit']:
                    break

                elif command == 'ping':
                    await self.send_message({'type': 'ping'})

                else:
                    print("❌ Неизвестная команда. Введите 'help' для справки.")

            except (KeyboardInterrupt, EOFError):
                print("\n👋 Выход из игры...")
                break
            except Exception as e:
                print(f"❌ Ошибка: {e}")

        self.connected = False

    def show_help(self):
        """Показать справку по командам"""
        print("\n📖 Доступные команды:")
        print("  create          - Создать новую игру")
        print("  join <id>       - Присоединиться к игре (например: join game_1)")
        print("  ready           - Отметить готовность к игре")
        print("  chat <text>     - Отправить сообщение в чат")
        print("  fold            - Сбросить карты")
        print("  check           - Пропустить ход")
        print("  call            - Уравнять ставку")
        print("  bet <amount>    - Сделать ставку")
        print("  raise <amount>  - Поднять ставку")
        print("  status          - Показать статус")
        print("  ping            - Проверить соединение")
        print("  quit            - Выйти из игры")
        print("  help            - Показать эту справку")

async def main():
    """Точка входа для запуска клиента"""
    client = PokerClient()
    await client.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())
