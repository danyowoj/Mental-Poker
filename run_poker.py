"""
Единый скрипт для запуска ментального покера
"""

import sys
import subprocess
import os


def run_server():
    """Запуск сервера"""
    print("🚀 Запуск сервера ментального покера...")
    subprocess.run([sys.executable, "server.py"])


def run_client():
    """Запуск клиента (консольный)"""
    print("🎮 Запуск консольного клиента ментального покера...")
    subprocess.run([sys.executable, "client.py"])


def run_gui_client():
    """Запуск GUI клиента"""
    print("🖥️  Запуск графического клиента ментального покера...")
    subprocess.run([sys.executable, "gui_client.py"])


def show_menu():
    """Показать меню выбора"""
    print("\n" + "=" * 50)
    print("🎲 СИСТЕМА МЕНТАЛЬНОГО ПОКЕРА")
    print("=" * 50)
    print("1. 🚀 Запустить сервер")
    print("2. 🎮 Запустить консольный клиент")
    print("3. 🖥️  Запустить графический клиент")
    print("4. 🔧 Проверить зависимости")
    print("5. 📖 Показать справку")
    print("6. 🚪 Выход")
    print("=" * 50)

    choice = input("\nВыберите действие (1-6): ").strip()

    if choice == '1':
        run_server()
    elif choice == '2':
        run_client()
    elif choice == '3':
        run_gui_client()
    elif choice == '4':
        check_dependencies()
    elif choice == '5':
        show_help()
    elif choice == '6':
        print("\n👋 До свидания!")
        sys.exit(0)
    else:
        print("❌ Неверный выбор. Попробуйте снова.")


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\n🔍 Проверка зависимостей...")

    dependencies = [
        ('cryptography', 'cryptography'),
    ]

    all_installed = True
    for name, package in dependencies:
        try:
            __import__(package)
            print(f"✅ {name} установлен")
        except ImportError:
            print(f"❌ {name} не установлен")
            all_installed = False

    if not all_installed:
        print("\n⚠️  Установите недостающие зависимости:")
        print("pip install cryptography")
    else:
        print("\n✅ Все зависимости установлены!")


def show_help():
    """Показать справку"""
    print("\n📖 СПРАВКА ПО СИСТЕМЕ МЕНТАЛЬНОГО ПОКЕРА")
    print("=" * 40)
    print("\n🔐 КРИПТОГРАФИЧЕСКАЯ ЗАЩИТА:")
    print("  • Карты шифруются двойным шифрованием")
    print("  • Используются RSA и AES алгоритмы")
    print("  • Никто не знает карт других игроков")
    print("  • Честность игры математически доказана")

    print("\n🎮 ГРАФИЧЕСКИЙ КЛИЕНТ:")
    print("  • Подключение: введите хост и порт, нажмите 'Подключиться'")
    print("  • Создание игры: нажмите 'Создать игру'")
    print("  • Присоединение: введите ID игры, нажмите 'Присоединиться'")
    print("  • Готовность: нажмите 'Готов'")
    print("  • Действия: Fold, Check, Call, Bet, Raise")
    print("  • Ставка: введите сумму в поле, нажмите Bet или Raise")
    print("  • Чат: введите сообщение, нажмите Enter или 'Отправить'")

    print("\n⚙️  ЗАПУСК:")
    print("  1. Запустите сервер (пункт 1)")
    print("  2. Запустите GUI клиенты (пункт 3)")
    print("  3. Минимум 2 игрока для начала игры")

    input("\nНажмите Enter для продолжения...")


def main():
    """Главная функция"""
    print("Загрузка системы ментального покера...")

    # Проверяем существование необходимых файлов
    required_files = [
        'server.py',
        'client.py',
        'crypto_utils.py',
        'poker_rules.py',
        'deck_utils.py'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print("❌ Отсутствуют необходимые файлы:")
        for file in missing_files:
            print(f"  - {file}")
        print("\n📥 Скачайте полную версию проекта с GitHub или создайте недостающие файлы.")
        sys.exit(1)

    # Основной цикл меню
    while True:
        try:
            show_menu()
        except KeyboardInterrupt:
            print("\n\n👋 Выход из программы...")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
