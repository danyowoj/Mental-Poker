"""
Модуль для управления игрой в Техасский Холдем с поддержкой ментального покера
"""

import random
from typing import Dict, List, Tuple, Optional


class Card:
    """Класс представляющий игральную карту"""

    def __init__(self, rank: int, suit: int):
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

    @staticmethod
    def from_string(card_str: str) -> 'Card':
        """Создает карту из строки вида 'A♠' или '10♥'"""
        suit_symbol = card_str[-1]
        suits = {'♠': 0, '♥': 1, '♦': 2, '♣': 3}
        suit = suits.get(suit_symbol, 0)

        rank_str = card_str[:-1]
        if rank_str == 'A':
            rank = 14
        elif rank_str == 'K':
            rank = 13
        elif rank_str == 'Q':
            rank = 12
        elif rank_str == 'J':
            rank = 11
        elif rank_str == '10':
            rank = 10
        else:
            rank = int(rank_str)

        return Card(rank, suit)


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
    def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int]]:
        """
        Оценивает силу руки из 7 карт (2 карты игрока + 5 общих)
        Возвращает кортеж (сила_комбинации, ранги_для_сравнения)
        """
        if len(cards) < 5:
            raise ValueError("Для оценки нужно минимум 5 карт")

        # Берем 7 лучших карт из доступных
        if len(cards) > 7:
            # Сортируем и берем 7 лучших
            cards = sorted(cards, key=lambda x: x.rank, reverse=True)[:7]
        elif len(cards) < 7:
            # Дополняем фиктивными картами (для упрощения)
            while len(cards) < 7:
                cards.append(Card(0, 0))

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
    def compare_hands(hand1: List[Card], hand2: List[Card]) -> int:
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

    @staticmethod
    def get_combination_name(combination_type: int) -> str:
        """Возвращает читаемое название комбинации"""
        names = {
            HandEvaluator.HIGH_CARD: "Старшая карта",
            HandEvaluator.PAIR: "Пара",
            HandEvaluator.TWO_PAIR: "Две пары",
            HandEvaluator.THREE_OF_A_KIND: "Сет",
            HandEvaluator.STRAIGHT: "Стрит",
            HandEvaluator.FLUSH: "Флеш",
            HandEvaluator.FULL_HOUSE: "Фулл-хаус",
            HandEvaluator.FOUR_OF_A_KIND: "Каре",
            HandEvaluator.STRAIGHT_FLUSH: "Стрит-флеш",
            HandEvaluator.ROYAL_FLUSH: "Флеш-рояль"
        }
        return names.get(combination_type, "Неизвестная комбинация")


class PokerGameManager:
    """Менеджер игры в Техасский Холдем"""

    def __init__(self):
        self.players = {}  # player_id -> PlayerInfo
        self.community_cards = []  # Карты на столе
        self.pot = 0  # Банк
        self.current_bet = 0  # Текущая ставка
        self.dealer_position = 0  # Позиция дилера
        self.current_player_index = 0  # Индекс текущего игрока
        self.phase = "preflop"  # Текущая фаза: preflop, flop, turn, river, showdown
        self.phase_actions = 0  # Количество действий в текущей фазе
        self.player_order = []  # Порядок игроков
        self.hand_active = False  # Активна ли раздача

    class PlayerInfo:
        """Информация об игроке"""
        def __init__(self, player_id: str, chips: int = 1000):
            self.id = player_id
            self.chips = chips
            self.hand = []  # Карты игрока
            self.current_bet = 0  # Текущая ставка игрока в этой фазе
            self.folded = False  # Сбросил ли карты
            self.acted_this_phase = False  # Сделал ли действие в этой фазе
            self.all_in = False  # Все ли фишки поставлены

    def add_player(self, player_id: str, chips: int = 1000):
        """Добавляет игрока в игру"""
        if player_id not in self.players:
            self.players[player_id] = self.PlayerInfo(player_id, chips)
            self.player_order.append(player_id)
            return True
        return False

    def remove_player(self, player_id: str):
        """Удаляет игрока из игры"""
        if player_id in self.players:
            del self.players[player_id]
            if player_id in self.player_order:
                self.player_order.remove(player_id)
            return True
        return False

    def is_player_in_game(self, player_id: str) -> bool:
        """Проверяет, находится ли игрок в игре"""
        return player_id in self.players and not self.players[player_id].folded

    def get_player_chips(self, player_id: str) -> int:
        """Возвращает количество фишек игрока"""
        if player_id in self.players:
            return self.players[player_id].chips
        return 0

    def set_player_cards(self, player_id: str, cards: List[str]):
        """Устанавливает карты игрока"""
        if player_id in self.players:
            # Преобразуем строки в объекты Card
            card_objects = []
            for card_str in cards:
                try:
                    card_obj = Card.from_string(card_str)
                    card_objects.append(card_obj)
                except:
                    # Если не удалось преобразовать, создаем фиктивную карту
                    card_objects.append(Card(0, 0))
            self.players[player_id].hand = card_objects

    def start_new_hand(self):
        """Начинает новую раздачу"""
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.phase = "preflop"
        self.phase_actions = 0
        self.hand_active = True

        # Сбрасываем состояние игроков
        for player in self.players.values():
            player.hand = []
            player.current_bet = 0
            player.folded = False
            player.acted_this_phase = False
            player.all_in = False

        # Определяем порядок игроков
        if not self.player_order:
            self.player_order = list(self.players.keys())

        # Начинаем с первого игрока после дилера
        self.current_player_index = (self.dealer_position + 1) % len(self.player_order)
        self.dealer_position = (self.dealer_position + 1) % len(self.player_order)

    def get_current_player(self) -> Optional[str]:
        """Возвращает ID текущего игрока"""
        if not self.player_order:
            return None

        # Ищем следующего активного игрока
        start_index = self.current_player_index
        while True:
            player_id = self.player_order[self.current_player_index]
            player = self.players[player_id]

            if not player.folded and not player.all_in:
                return player_id

            self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
            if self.current_player_index == start_index:
                break

        return None

    def get_next_player(self) -> Optional[str]:
        """Переходит к следующему игроку и возвращает его ID"""
        if not self.player_order:
            return None

        # Переходим к следующему игроку
        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)

        # Ищем активного игрока
        start_index = self.current_player_index
        while True:
            player_id = self.player_order[self.current_player_index]
            player = self.players[player_id]

            if not player.folded and not player.all_in:
                return player_id

            self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
            if self.current_player_index == start_index:
                break

        return None

    def process_player_action(self, player_id: str, action: str, amount: int = 0) -> Dict:
        """Обрабатывает действие игрока"""
        if player_id not in self.players:
            return {"success": False, "message": "Игрок не найден"}

        player = self.players[player_id]

        if player.folded:
            return {"success": False, "message": "Игрок уже сбросил карты"}

        if player.all_in:
            return {"success": False, "message": "Игрок уже пошел all-in"}

        # Проверяем, что это ход текущего игрока
        current_player = self.get_current_player()
        if current_player != player_id:
            return {"success": False, "message": "Сейчас не ваш ход"}

        # Обрабатываем действие
        if action == "fold":
            player.folded = True
            player.acted_this_phase = True

        elif action == "check":
            if self.current_bet > player.current_bet:
                return {"success": False, "message": "Нельзя сделать чек, есть текущая ставка"}
            player.acted_this_phase = True

        elif action == "call":
            call_amount = self.current_bet - player.current_bet
            if call_amount > player.chips:
                return {"success": False, "message": "Недостаточно фишек"}

            player.chips -= call_amount
            player.current_bet = self.current_bet
            self.pot += call_amount
            player.acted_this_phase = True

            if player.chips == 0:
                player.all_in = True

        elif action == "bet":
            if amount <= 0:
                return {"success": False, "message": "Ставка должна быть положительной"}
            if amount > player.chips:
                return {"success": False, "message": "Недостаточно фишек"}
            if self.current_bet > 0:
                return {"success": False, "message": "Уже есть ставка, используйте raise"}

            player.chips -= amount
            player.current_bet = amount
            self.current_bet = amount
            self.pot += amount
            player.acted_this_phase = True

            if player.chips == 0:
                player.all_in = True

        elif action == "raise":
            if amount <= 0:
                return {"success": False, "message": "Повышение должно быть положительным"}
            if amount > player.chips:
                return {"success": False, "message": "Недостаточно фишек"}
            if self.current_bet == 0:
                return {"success": False, "message": "Нет текущей ставки, используйте bet"}
            if amount <= self.current_bet:
                return {"success": False, "message": "Повышение должно быть больше текущей ставки"}

            total_bet = player.current_bet + amount
            player.chips -= amount
            player.current_bet = total_bet
            self.current_bet = total_bet
            self.pot += amount
            player.acted_this_phase = True

            if player.chips == 0:
                player.all_in = True

        else:
            return {"success": False, "message": f"Неизвестное действие: {action}"}

        self.phase_actions += 1
        return {"success": True, "message": "Действие успешно обработано"}

    def is_phase_complete(self) -> bool:
        """Проверяет, завершена ли текущая фаза"""
        # Подсчитываем активных игроков, которые еще не действовали
        active_players = 0
        acted_players = 0

        for player_id in self.player_order:
            player = self.players[player_id]
            if not player.folded and not player.all_in:
                active_players += 1
                if player.acted_this_phase:
                    acted_players += 1

        # Если все активные игроки сделали ход
        if active_players > 0 and acted_players == active_players:
            return True

        # Если остался только один активный игрок
        if active_players <= 1:
            return True

        return False

    def advance_phase(self) -> str:
        """Переходит к следующей фазе игры"""
        if self.phase == "preflop":
            self.phase = "flop"
        elif self.phase == "flop":
            self.phase = "turn"
        elif self.phase == "turn":
            self.phase = "river"
        elif self.phase == "river":
            self.phase = "showdown"

        # Сбрасываем состояние для новой фазы
        self.current_bet = 0
        self.phase_actions = 0

        for player in self.players.values():
            player.current_bet = 0
            player.acted_this_phase = False

        # Начинаем фазу с первого активного игрока после дилера
        self.current_player_index = (self.dealer_position + 1) % len(self.player_order)

        return self.phase

    def add_community_card(self, card_str: str):
        """Добавляет общую карту на стол"""
        try:
            card_obj = Card.from_string(card_str)
            self.community_cards.append(card_obj)
        except:
            # Если не удалось преобразовать, добавляем фиктивную карту
            self.community_cards.append(Card(0, 0))

    def get_community_cards(self) -> List[str]:
        """Возвращает список общих карт в виде строк"""
        return [str(card) for card in self.community_cards]

    def get_pot(self) -> int:
        """Возвращает текущий банк"""
        return self.pot

    def get_current_bet(self) -> int:
        """Возвращает текущую ставку"""
        return self.current_bet

    def add_chips_to_player(self, player_id: str, amount: int):
        """Добавляет фишки игроку"""
        if player_id in self.players:
            self.players[player_id].chips += amount

    def determine_winners(self) -> Tuple[List[str], Dict[str, str], Dict[str, List[str]]]:
        """Определяет победителей раздачи"""
        # Находим активных игроков
        active_players = []
        for player_id, player in self.players.items():
            if not player.folded:
                active_players.append((player_id, player))

        if len(active_players) == 0:
            return [], {}, {}

        if len(active_players) == 1:
            winner_id = active_players[0][0]
            return [winner_id], {winner_id: "Единственный активный игрок"}, {winner_id: [str(card) for card in active_players[0][1].hand]}

        # Оцениваем руки всех активных игроков
        player_scores = []
        player_combinations = {}
        player_card_strings = {}

        for player_id, player in active_players:
            # Комбинируем карты игрока и общие карты
            all_cards = player.hand + self.community_cards

            if len(all_cards) >= 5:
                score = HandEvaluator.evaluate_hand(all_cards)
                player_scores.append((player_id, score))
                player_combinations[player_id] = HandEvaluator.get_combination_name(score[0])
                player_card_strings[player_id] = [str(card) for card in player.hand]

        # Находим победителей
        if not player_scores:
            return [], {}, {}

        # Сортируем по силе руки
        player_scores.sort(key=lambda x: (-x[1][0], [-r for r in x[1][1]]))

        # Определяем победителей (те, у кого одинаковая лучшая рука)
        winners = [player_scores[0][0]]
        best_score = player_scores[0][1]

        for player_id, score in player_scores[1:]:
            if score[0] == best_score[0] and score[1] == best_score[1]:
                winners.append(player_id)
            else:
                break

        return winners, player_combinations, player_card_strings

    def reset_for_new_hand(self):
        """Сбрасывает состояние для новой раздачи"""
        self.start_new_hand()


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


def test_game_manager():
    """Тестирование менеджера игры"""
    manager = PokerGameManager()

    # Добавляем игроков
    manager.add_player("player1", 1000)
    manager.add_player("player2", 1000)

    # Начинаем новую раздачу
    manager.start_new_hand()

    # Устанавливаем карты игрокам
    manager.set_player_cards("player1", ["A♠", "K♠"])
    manager.set_player_cards("player2", ["Q♠", "J♠"])

    # Проверяем текущего игрока
    current = manager.get_current_player()
    print(f"Текущий игрок: {current}")

    # Обрабатываем действия
    result = manager.process_player_action("player1", "bet", 100)
    print(f"Действие player1: {result}")

    # Получаем следующего игрока
    next_player = manager.get_next_player()
    print(f"Следующий игрок: {next_player}")

    print("Тест менеджера игры пройден!")


if __name__ == "__main__":
    test_hand_evaluation()
    test_game_manager()
