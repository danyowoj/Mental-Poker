"""
Утилиты для работы с колодой карт
"""

import random
from poker_rules import Card


class Deck:
    """Класс для представления колоды карт"""

    def __init__(self):
        self.cards = []
        self.reset()

    def reset(self):
        """Создает новую перетасованную колоду из 52 карт"""
        self.cards = []
        for suit in range(4):  # 4 масти
            for rank in range(2, 15):  # Достоинства от 2 до 14 (Туз)
                self.cards.append(Card(rank, suit))
        self.shuffle()

    def shuffle(self):
        """Тасование колоды"""
        random.shuffle(self.cards)

    def deal(self, count=1):
        """Раздает указанное количество карт"""
        if len(self.cards) < count:
            raise ValueError("Недостаточно карт в колоде")
        return [self.cards.pop() for _ in range(count)]

    def __len__(self):
        return len(self.cards)


def create_standard_deck():
    """Создает стандартную колоду из 52 карт"""
    deck = Deck()
    return deck.cards


# Пример использования
if __name__ == "__main__":
    deck = Deck()
    print(f"Колода содержит {len(deck)} карт")

    # Раздадим несколько карт
    hand = deck.deal(2)
    print(f"Разданы карты: {hand}")
    print(f"Осталось в колоде: {len(deck)} карт")