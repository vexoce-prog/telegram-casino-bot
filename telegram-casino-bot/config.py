# ===== НАСТРОЙКИ БОТА =====

# Токен бота от @BotFather
BOT_TOKEN = "8621868518:AAFgMsfvi_2WuzTZSC8f5Zz8G3j_eUzUEog"

# ID администраторов (можно несколько)
ADMIN_IDS = [8529412206]

# ===== ЭКОНОМИКА =====
START_BALANCE = 1000          # Начальный баланс
DAILY_BONUS = 500             # Ежедневный бонус
MIN_BET = 10                  # Минимальная ставка
MAX_BET = 1_000_000           # Максимальная ставка

# ===== УРОВНИ =====
XP_PER_GAME = 10              # Опыт за игру
XP_PER_WIN = 25               # Доп. опыт за победу
LEVEL_BASE_XP = 100           # Базовый опыт для уровня
LEVEL_XP_MULTIPLIER = 1.5     # Множитель опыта на уровень

# ===== ИГРЫ =====
# Мины
MINES_FIELD_SIZE = 5
MINES_MIN = 1
MINES_MAX = 5

# Башня
TOWER_HEIGHTS = [5, 8, 12]

# Слоты
SLOTS_SYMBOLS = ["🍒", "🍋", "🔔", "💎", "7️⃣", "🍀"]

# Краш
CRASH_TICK_SECONDS = 1.5

# Русская рулетка
ROULETTE_CHAMBERS = 6

# Гонки
RACE_CARS = ["🚗", "🏎️", "🚙", "🚕", "🏍️"]

# ===== МАГАЗИН =====
SHOP_ITEMS = {
    "vip": {"name": "👑 VIP-статус", "price": 50000, "description": "Увеличенные бонусы и привилегии", "type": "status", "duration_days": 30},
    "insurance": {"name": "🛡️ Страховка", "price": 5000, "description": "Возврат 50% при проигрыше (1 игра)", "type": "consumable"},
    "title_king": {"name": "👑 Титул: Король", "price": 25000, "description": "Титул в профиле", "type": "title"},
    "title_legend": {"name": "⭐ Титул: Легенда", "price": 100000, "description": "Титул в профиле", "type": "title"},
    "title_shark": {"name": "🦈 Титул: Акула", "price": 50000, "description": "Титул в профиле", "type": "title"},
    "avatar_fire": {"name": "🔥 Аватар: Огонь", "price": 10000, "description": "Аватар в профиле", "type": "avatar"},
    "avatar_star": {"name": "⭐ Аватар: Звезда", "price": 10000, "description": "Аватар в профиле", "type": "avatar"},
    "avatar_diamond": {"name": "💎 Аватар: Бриллиант", "price": 30000, "description": "Аватар в профиле", "type": "avatar"},
    "xp_boost": {"name": "📈 Буст опыта x2", "price": 15000, "description": "Двойной опыт на 24 часа", "type": "booster", "duration_hours": 24},
    "income_boost": {"name": "💰 Буст дохода x2", "price": 20000, "description": "Двойной доход от бизнеса на 24 часа", "type": "booster", "duration_hours": 24},
}

# ===== КЕЙСЫ =====
CASES = {
    "common": {"name": "📦 Обычный кейс", "price": 1000, "rewards": [(500, 30), (1000, 25), (2000, 20), (5000, 15), (10000, 8), (25000, 2)]},
    "rare": {"name": "💜 Редкий кейс", "price": 5000, "rewards": [(3000, 25), (5000, 25), (10000, 20), (25000, 15), (50000, 10), (100000, 5)]},
    "legendary": {"name": "🌟 Легендарный кейс", "price": 25000, "rewards": [(15000, 25), (25000, 25), (50000, 20), (100000, 15), (250000, 10), (500000, 5)]},
}

# ===== БИЗНЕСЫ =====
BUSINESSES = {
    "kiosk": {"name": "🏪 Киоск", "price": 5000, "income": 100, "interval_hours": 1, "max_level": 10, "upgrade_cost": 2500},
    "cafe": {"name": "☕ Кафе", "price": 25000, "income": 500, "interval_hours": 2, "max_level": 10, "upgrade_cost": 12500},
    "shop": {"name": "🏬 Магазин", "price": 100000, "income": 2000, "interval_hours": 3, "max_level": 10, "upgrade_cost": 50000},
    "factory": {"name": "🏭 Завод", "price": 500000, "income": 10000, "interval_hours": 4, "max_level": 10, "upgrade_cost": 250000},
    "bank": {"name": "🏦 Банк", "price": 2000000, "income": 50000, "interval_hours": 6, "max_level": 10, "upgrade_cost": 1000000},
}

# ===== ДОСТИЖЕНИЯ =====
ACHIEVEMENTS = {
    "first_win": {"name": "🏆 Первая победа", "description": "Выиграть первую игру", "reward": 500},
    "games_10": {"name": "🎮 Игрок", "description": "Сыграть 10 игр", "reward": 1000},
    "games_100": {"name": "🎯 Опытный", "description": "Сыграть 100 игр", "reward": 5000},
    "games_1000": {"name": "💪 Ветеран", "description": "Сыграть 1000 игр", "reward": 25000},
    "win_streak_5": {"name": "🔥 Серия побед", "description": "Выиграть 5 игр подряд", "reward": 3000},
    "win_streak_10": {"name": "⚡ Непобедимый", "description": "Выиграть 10 игр подряд", "reward": 10000},
    "millionaire": {"name": "💰 Миллионер", "description": "Накопить 1.000.000 монет", "reward": 50000},
    "big_win": {"name": "💎 Крупный выигрыш", "description": "Выиграть 100.000 за одну игру", "reward": 10000},
    "all_games": {"name": "🎪 Всезнайка", "description": "Сыграть во все игры", "reward": 5000},
    "level_10": {"name": "📊 Уровень 10", "description": "Достигнуть 10 уровня", "reward": 10000},
    "level_50": {"name": "🌟 Уровень 50", "description": "Достигнуть 50 уровня", "reward": 50000},
}

# ===== РЕЙТИНГ =====
RANKS = [
    (0, "🆕 Новичок"),
    (1000, "🎮 Игрок"),
    (5000, "⚔️ Боец"),
    (15000, "🛡️ Воин"),
    (35000, "🏅 Мастер"),
    (75000, "👑 Чемпион"),
    (150000, "💎 Элита"),
    (300000, "🌟 Легенда"),
]

# ===== ЛОТЕРЕЯ =====
LOTTERY_TICKET_PRICE = 100
LOTTERY_DRAW_HOUR = 21  # Час розыгрыша (UTC)

# ===== ПРЕСТИЖ =====
PRESTIGE_MIN_LEVEL = 50
PRESTIGE_BONUS_PER_LEVEL = 0.02  # +2% к выигрышам за каждый престиж

# ===== ФОРМАТИРОВАНИЕ =====
def fmt(number):
    """Форматирование чисел с разделителями"""
    return f"{number:,.0f}".replace(",", ".")
