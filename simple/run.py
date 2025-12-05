"""
Скрипт запуска системы ментального покера RSA (исправленная версия)
"""

import subprocess
import sys
import os
import platform


def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверка зависимостей...")

    dependencies = [
        ('cryptography', 'cryptography'),
        ('sympy', 'sympy'),
    ]

    all_installed = True
    for name, package in dependencies:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} не установлен")
            all_installed = False

    if not all_installed:
        print("\n⚠️  Установите недостающие зависимости:")
        print("pip install cryptography sympy")
        return False

    print("\n✅ Все зависимости установлены!")
    return True


def run_server():
    """Запуск сервера"""
    print("\n🚀 Запуск сервера ментального покера...")
    print("   Порт: 8888")
    print("   Ожидание подключений клиентов...")
    print("-" * 50)

    # Проверяем существование файла
    if not os.path.exists("server.py"):
        print("❌ Файл server.py не найден!")
        return

    subprocess.run([sys.executable, "server.py"])


def run_client():
    """Запуск графического клиента"""
    print("\n🎮 Запуск графического клиента...")
    print("   Подключение к localhost:8888")
    print("   Для тестирования запустите несколько клиентов")
    print("-" * 50)

    # Проверяем существование файла
    if not os.path.exists("poker_gui.py"):
        print("❌ Файл poker_gui.py не найден!")
        return

    subprocess.run([sys.executable, "poker_gui.py"])


def show_instructions():
    """Показать инструкции"""
    print("\n📖 ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ")
    print("=" * 60)

    print("\n🎯 КАК ИГРАТЬ:")
    print("1. Запустите сервер (пункт 1)")
    print("2. Запустите первый клиент (пункт 2)")
    print("3. Запустите второй клиент (или больше)")
    print("4. В каждом клиенте:")
    print("   • Нажмите 'Подключиться'")
    print("   • Нажмите 'Сгенерировать ключи'")
    print("   • Создайте игру или присоединитесь к существующей")
    print("   • Нажмите 'Готов к игре'")
    print("5. Когда все готовы, игра начнется автоматически")

    print("\n🔐 ПРИНЦИП РАБОТЫ МЕНТАЛЬНОГО ПОКЕРА:")
    print("• Сервер генерирует общий модуль RSA n")
    print("• Каждый игрок получает свою пару ключей (e, d)")
    print("• Карты представляются числами от 2 до n")
    print("• Все игроки последовательно шифруют колоду")
    print("• Каждый игрок видит только свои карты")
    print("• Сервер не знает карт игроков")

    print("\n🎮 УПРАВЛЕНИЕ В ИГРЕ:")
    print("• Fold - сбросить карты")
    print("• Check - пропустить ход (если нет ставки)")
    print("• Call - принять текущую ставку")
    print("• Bet - сделать ставку")
    print("• Raise - повысить ставку")
    print("• All-in - поставить все фишки")

    input("\nНажмите Enter для продолжения...")


def check_files():
    """Проверка наличия необходимых файлов"""
    print("📂 Проверка файлов проекта...")

    required_files = [
        'server.py',
        'poker_gui.py',
        'rsa_poker.py',
        'poker_rules.py',
    ]

    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)

    if missing_files:
        print(f"\n⚠️  Отсутствуют файлы: {', '.join(missing_files)}")
        return False

    print("\n✅ Все необходимые файлы присутствуют!")
    return True


def main():
    """Главное меню"""
    print("\n" + "=" * 60)
    print("🎲 СИСТЕМА МЕНТАЛЬНОГО ПОКЕРА RSA")
    print(f"📟 Операционная система: {platform.system()} {platform.release()}")
    print("=" * 60)

    if not check_files():
        print("\n❌ Не все необходимые файлы найдены!")
        input("Нажмите Enter для выхода...")
        return

    if not check_dependencies():
        print("\n❌ Пожалуйста, установите зависимости и перезапустите программу")
        input("Нажмите Enter для выхода...")
        return

    while True:
        print("\n" + "=" * 60)
        print("ГЛАВНОЕ МЕНЮ")
        print("=" * 60)
        print("1. 🚀 Запустить сервер")
        print("2. 🎮 Запустить графический клиент")
        print("3. 📖 Инструкция по использованию")
        print("4. 🚪 Выход")
        print("=" * 60)

        choice = input("\nВыберите действие (1-4): ").strip()

        if choice == '1':
            run_server()
        elif choice == '2':
            run_client()
        elif choice == '3':
            show_instructions()
        elif choice == '4':
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("Нажмите Enter для выхода...")
