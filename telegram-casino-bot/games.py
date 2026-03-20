import random
import asyncio
from config import *

# ===== МИНЫ =====

def create_mines_field(num_mines):
    field = [False] * (MINES_FIELD_SIZE * MINES_FIELD_SIZE)
    mines_pos = random.sample(range(len(field)), num_mines)
    for p in mines_pos:
        field[p] = True
    return field, mines_pos


def mines_multiplier(opened, num_mines, total=25):
    safe = total - num_mines
    mult = 1.0
    for i in range(opened):
        mult *= (safe - i) / (total - i)
    if mult == 0:
        return 0
    return round(1 / mult, 2)


# ===== БАШНЯ =====

def tower_cells_per_floor(floor, height):
    if height <= 5:
        return 3
    elif height <= 8:
        return 3 if floor < height - 2 else 2
    else:
        return 4 if floor < 3 else 3 if floor < height - 2 else 2


def tower_multiplier(floor, height):
    mult = 1.0
    for f in range(floor):
        cells = tower_cells_per_floor(f, height)
        mult *= cells / (cells - 1)
    return round(mult, 2)


def create_tower(height):
    tower = []
    for f in range(height):
        cells = tower_cells_per_floor(f, height)
        safe = list(range(cells))
        bomb = random.choice(safe)
        tower.append({"cells": cells, "bomb": bomb})
    return tower


# ===== СЛОТЫ =====

def spin_slots():
    return [random.choice(SLOTS_SYMBOLS) for _ in range(3)]


def slots_payout(reels, bet):
    if reels[0] == reels[1] == reels[2]:
        sym = reels[0]
        if sym == "7️⃣":
            return bet * 10
        elif sym == "💎":
            return bet * 7
        elif sym == "🍀":
            return bet * 5
        else:
            return bet * 3
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        return int(bet * 1.5)
    return 0


# ===== ОРЁЛ И РЕШКА =====

def coinflip():
    return random.choice(["орёл", "решка"])


# ===== КОСТИ =====

def roll_dice():
    return random.randint(1, 6), random.randint(1, 6)


# ===== БЛЭКДЖЕК =====

CARD_VALUES = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10, "A": 11}
CARD_SUITS = ["♠️", "♥️", "♦️", "♣️"]
CARD_NAMES = list(CARD_VALUES.keys())


def new_deck():
    deck = [(name, suit) for name in CARD_NAMES for suit in CARD_SUITS]
    random.shuffle(deck)
    return deck


def hand_value(hand):
    total = sum(CARD_VALUES[c[0]] for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def card_str(card):
    return f"{card[0]}{card[1]}"


def hand_str(hand):
    return " ".join(card_str(c) for c in hand)


# ===== КРАШ =====

def generate_crash_point():
    r = random.random()
    if r < 0.01:
        return 1.0
    return round(1 / (1 - r) * 0.97, 2)


# ===== РУССКАЯ РУЛЕТКА =====

def russian_roulette():
    return random.randint(1, ROULETTE_CHAMBERS) == 1  # True = bang


# ===== ГОНКИ =====

def run_race():
    cars = list(RACE_CARS)
    random.shuffle(cars)
    return cars  # cars[0] = winner


# ===== КОЛЕСО ФОРТУНЫ =====

WHEEL_PRIZES = [
    (100, 20), (200, 18), (500, 15), (1000, 13),
    (2000, 10), (5000, 8), (10000, 6), (25000, 4),
    (50000, 3), (100000, 2), (0, 1)
]


def spin_wheel():
    total = sum(w for _, w in WHEEL_PRIZES)
    r = random.randint(1, total)
    cumulative = 0
    for prize, weight in WHEEL_PRIZES:
        cumulative += weight
        if r <= cumulative:
            return prize
    return WHEEL_PRIZES[0][0]
