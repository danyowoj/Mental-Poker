"""
Модуль для оценки покерных рук по правилам Техасского Холдема.
Реализует определение силы комбинаций и сравнение рук.
"""


class Card:
    """Класс представляющий игральную карту"""

    def __init__(self, rank, suit):
        """
        rank: достоинство карты (2-14, где 11=J, 12=Q, 13=K, 14=A)
        suit: масть (0=пики, 1=червы, 2=бубны, 3=трефы)
        """
        self.rank = rank
        self.suit = suit

    def __str__(self):
        ranks = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        suits = {0: '♠', 1: '♥', 2: '♦', 3: '♣'}
        rank_str = ranks.get(self.rank, str(self.rank))
        return f"{rank_str}{suits[self.suit]}"

    def __repr__(self):
        return self.__str__()


class HandEvaluator:
    """Класс для оценки силы покерной руки"""

    # Константы для типов комбинаций
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9

    @staticmethod
    def evaluate_hand(cards):
        """
        Оценивает силу руки из 7 карт (2 карты игрока + 5 общих)
        Возвращает кортеж (сила_комбинации, ранги_для_сравнения)
        """
        if len(cards) != 7:
            raise ValueError("Должно быть 7 карт для оценки")

        # Сортируем карты по достоинству
        cards.sort(key=lambda x: x.rank, reverse=True)

        # Проверяем комбинации от самой сильной к самой слабой
        result = HandEvaluator._check_straight_flush(cards)
        if result: return result

        result = HandEvaluator._check_four_of_a_kind(cards)
        if result: return result

        result = HandEvaluator._check_full_house(cards)
        if result: return result

        result = HandEvaluator._check_flush(cards)
        if result: return result

        result = HandEvaluator._check_straight(cards)
        if result: return result

        result = HandEvaluator._check_three_of_a_kind(cards)
        if result: return result

        result = HandEvaluator._check_two_pair(cards)
        if result: return result

        result = HandEvaluator._check_pair(cards)
        if result: return result

        return HandEvaluator._check_high_card(cards)

    @staticmethod
    def _check_straight_flush(cards):
        """Проверка на стрит-флеш и флеш-рояль"""
        # Группируем карты по мастям
        suits = {}
        for card in cards:
            if card.suit not in suits:
                suits[card.suit] = []
            suits[card.suit].append(card)

        # Ищем флеш (5+ карт одной масти)
        for suit, suited_cards in suits.items():
            if len(suited_cards) >= 5:
                # Сортируем по достоинству
                suited_cards.sort(key=lambda x: x.rank, reverse=True)

                # Проверяем на стрит внутри флеша
                straight_flush = HandEvaluator._find_straight(suited_cards)
                if straight_flush:
                    # Проверяем на флеш-рояль (A, K, Q, J, 10)
                    if straight_flush[0].rank == 14 and straight_flush[4].rank == 10:
                        return (HandEvaluator.ROYAL_FLUSH, [])
                    return (HandEvaluator.STRAIGHT_FLUSH, [straight_flush[0].rank])
        return None

    @staticmethod
    def _check_four_of_a_kind(cards):
        """Проверка на каре (4 карты одного достоинства)"""
        ranks = {}
        for card in cards:
            if card.rank not in ranks:
                ranks[card.rank] = []
            ranks[card.rank].append(card)

        for rank, cards_list in ranks.items():
            if len(cards_list) == 4:
                # Находим кикер (самую старшую карту кроме каре)
                kicker = max(card.rank for card in cards if card.rank != rank)
                return (HandEvaluator.FOUR_OF_A_KIND, [rank, kicker])
        return None

    @staticmethod
    def _check_full_house(cards):
        """Проверка на фулл-хаус (сет + пара)"""
        ranks = {}
        for card in cards:
            if card.rank not in ranks:
                ranks[card.rank] = []
            ranks[card.rank].append(card)

        # Ищем сет (3 карты одного достоинства)
        three_of_a_kind = None
        for rank, cards_list in sorted(ranks.items(), key=lambda x: x[0], reverse=True):
            if len(cards_list) >= 3:
                if three_of_a_kind is None or rank > three_of_a_kind:
                    three_of_a_kind = rank

        if three_of_a_kind is None:
            return None

        # Ищем пару (отличную от сета)
        pair = None
        for rank, cards_list in sorted(ranks.items(), key=lambda x: x[0], reverse=True):
            if rank != three_of_a_kind and len(cards_list) >= 2:
                if pair is None or rank > pair:
                    pair = rank

        if pair is not None:
            return (HandEvaluator.FULL_HOUSE, [three_of_a_kind, pair])

        return None

    @staticmethod
    def _check_flush(cards):
        """Проверка на флеш (5 карт одной масти)"""
        suits = {}
        for card in cards:
            if card.suit not in suits:
                suits[card.suit] = []
            suits[card.suit].append(card)

        for suit, suited_cards in suits.items():
            if len(suited_cards) >= 5:
                # Берем 5 старших карт флеша
                suited_cards.sort(key=lambda x: x.rank, reverse=True)
                top_ranks = [card.rank for card in suited_cards[:5]]
                return (HandEvaluator.FLUSH, top_ranks)
        return None

    @staticmethod
    def _check_straight(cards):
        """Проверка на стрит (5 последовательных карт)"""
        straight = HandEvaluator._find_straight(cards)
        if straight:
            return (HandEvaluator.STRAIGHT, [straight[0].rank])
        return None

    @staticmethod
    def _find_straight(cards):
        """Находит стрит в наборе карт"""
        # Убираем дубликаты по достоинству и сортируем
        unique_cards = []
        seen_ranks = set()
        for card in sorted(cards, key=lambda x: x.rank, reverse=True):
            if card.rank not in seen_ranks:
                unique_cards.append(card)
                seen_ranks.add(card.rank)

        # Проверяем последовательности из 5 карт
        for i in range(len(unique_cards) - 4):
            if all(unique_cards[i + j].rank == unique_cards[i].rank - j for j in range(5)):
                return unique_cards[i:i + 5]

        # Проверяем特殊情况: A,2,3,4,5
        low_straight_ranks = {14, 2, 3, 4, 5}
        if low_straight_ranks.issubset(seen_ranks):
            low_straight_cards = [card for card in unique_cards if card.rank in low_straight_ranks]
            low_straight_cards.sort(key=lambda x: x.rank, reverse=True)
            # Переупорядочиваем чтобы 5 была старшей картой
            return [card for card in low_straight_cards if card.rank != 14] + \
                [card for card in low_straight_cards if card.rank == 14]

        return None

    @staticmethod
    def _check_three_of_a_kind(cards):
        """Проверка на сет (3 карты одного достоинства)"""
        ranks = {}
        for card in cards:
            if card.rank not in ranks:
                ranks[card.rank] = []
            ranks[card.rank].append(card)

        for rank, cards_list in sorted(ranks.items(), key=lambda x: x[0], reverse=True):
            if len(cards_list) == 3:
                # Находим два кикера
                kickers = sorted([card.rank for card in cards if card.rank != rank], reverse=True)[:2]
                return (HandEvaluator.THREE_OF_A_KIND, [rank] + kickers)
        return None

    @staticmethod
    def _check_two_pair(cards):
        """Проверка на две пары"""
        ranks = {}
        for card in cards:
            if card.rank not in ranks:
                ranks[card.rank] = []
            ranks[card.rank].append(card)

        pairs = []
        for rank, cards_list in sorted(ranks.items(), key=lambda x: x[0], reverse=True):
            if len(cards_list) == 2:
                pairs.append(rank)
                if len(pairs) == 2:
                    # Находим кикер
                    kicker = max(card.rank for card in cards if card.rank not in pairs)
                    return (HandEvaluator.TWO_PAIR, pairs + [kicker])
        return None

    @staticmethod
    def _check_pair(cards):
        """Проверка на пару"""
        ranks = {}
        for card in cards:
            if card.rank not in ranks:
                ranks[card.rank] = []
            ranks[card.rank].append(card)

        for rank, cards_list in sorted(ranks.items(), key=lambda x: x[0], reverse=True):
            if len(cards_list) == 2:
                # Находим три кикера
                kickers = sorted([card.rank for card in cards if card.rank != rank], reverse=True)[:3]
                return (HandEvaluator.PAIR, [rank] + kickers)
        return None

    @staticmethod
    def _check_high_card(cards):
        """Старшая карта"""
        sorted_ranks = sorted([card.rank for card in cards], reverse=True)[:5]
        return (HandEvaluator.HIGH_CARD, sorted_ranks)

    @staticmethod
    def compare_hands(hand1, hand2):
        """
        Сравнивает две руки и возвращает:
         1 если hand1 сильнее
        -1 если hand2 сильнее
         0 если ничья
        """
        score1 = HandEvaluator.evaluate_hand(hand1)
        score2 = HandEvaluator.evaluate_hand(hand2)

        # Сравниваем тип комбинации
        if score1[0] > score2[0]:
            return 1
        elif score1[0] < score2[0]:
            return -1

        # Если тип комбинации одинаковый, сравниваем по рангам
        for r1, r2 in zip(score1[1], score2[1]):
            if r1 > r2:
                return 1
            elif r1 < r2:
                return -1

        return 0


class PokerGame:
    """Класс управления игрой в покер"""

    def __init__(self):
        self.players = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.dealer_position = 0
        self.game_phase = "preflop"  # preflop, flop, turn, river, showdown

    def add_player(self, player_id, chips=1000):
        """Добавляет игрока в игру"""
        self.players.append({
            'id': player_id,
            'chips': chips,
            'hand': [],
            'folded': False,
            'bet': 0
        })

    def deal_cards(self, deck):
        """Раздает карты игрокам и на стол"""
        # Раздаем по 2 карты каждому игроку
        for player in self.players:
            if len(deck) >= 2:
                player['hand'] = [deck.pop(), deck.pop()]

        # Раздаем 5 карт на стол (будем открывать по фазам)
        if len(deck) >= 5:
            self.community_cards = [deck.pop() for _ in range(5)]

    def get_winner(self):
        """Определяет победителя на основе лучшей комбинации"""
        active_players = [p for p in self.players if not p['folded']]

        if len(active_players) == 1:
            return [active_players[0]]  # Все кроме одного сбросили карты

        # Сравниваем комбинации всех активных игроков
        best_players = [active_players[0]]
        best_score = HandEvaluator.evaluate_hand(
            active_players[0]['hand'] + self.community_cards
        )

        for player in active_players[1:]:
            player_cards = player['hand'] + self.community_cards
            player_score = HandEvaluator.evaluate_hand(player_cards)

            comparison = HandEvaluator.compare_hands(
                active_players[0]['hand'] + self.community_cards,
                player_cards
            )

            if comparison == -1:  # Текущий игрок сильнее
                best_players = [player]
                best_score = player_score
            elif comparison == 0:  # Ничья
                best_players.append(player)

        return best_players


# Тестовые функции
def test_hand_evaluation():
    """Тестирование системы оценки рук"""

    # Тест флеш-рояля
    royal_flush = [
        Card(14, 0), Card(13, 0), Card(12, 0), Card(11, 0), Card(10, 0),
        Card(2, 1), Card(3, 2)  # Лишние карты
    ]
    score = HandEvaluator.evaluate_hand(royal_flush)
    print(f"Royal Flush: {score}")
    assert score[0] == HandEvaluator.ROYAL_FLUSH

    # Тест каре
    four_of_a_kind = [
        Card(8, 0), Card(8, 1), Card(8, 2), Card(8, 3),
        Card(5, 0), Card(6, 1), Card(7, 2)
    ]
    score = HandEvaluator.evaluate_hand(four_of_a_kind)
    print(f"Four of a Kind: {score}")
    assert score[0] == HandEvaluator.FOUR_OF_A_KIND

    # Тест фулл-хауса
    full_house = [
        Card(9, 0), Card(9, 1), Card(9, 2),
        Card(5, 0), Card(5, 1),
        Card(2, 3), Card(3, 0)
    ]
    score = HandEvaluator.evaluate_hand(full_house)
    print(f"Full House: {score}")
    assert score[0] == HandEvaluator.FULL_HOUSE

    print("Все тесты пройдены!")


if __name__ == "__main__":
    test_hand_evaluation()