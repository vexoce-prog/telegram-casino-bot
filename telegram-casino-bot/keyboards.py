from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
         InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("🎮 Игры", callback_data="games_menu"),
         InlineKeyboardButton("🎁 Бонусы", callback_data="bonus_menu")],
        [InlineKeyboardButton("🏆 Топ", callback_data="top_menu"),
         InlineKeyboardButton("🏪 Магазин", callback_data="shop_menu")],
        [InlineKeyboardButton("💼 Бизнес", callback_data="business_menu"),
         InlineKeyboardButton("📦 Кейсы", callback_data="cases_menu")],
        [InlineKeyboardButton("👥 Социальное", callback_data="social_menu"),
         InlineKeyboardButton("🎖️ Достижения", callback_data="achievements_menu")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats_menu"),
         InlineKeyboardButton("🎫 Промокод", callback_data="promo_enter")],
    ])


def games_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💣 Мины", callback_data="game_mines"),
         InlineKeyboardButton("🏗️ Башня", callback_data="game_tower")],
        [InlineKeyboardButton("🎰 Слоты", callback_data="game_slots"),
         InlineKeyboardButton("🪙 Орёл/Решка", callback_data="game_coin")],
        [InlineKeyboardButton("🎲 Кости", callback_data="game_dice"),
         InlineKeyboardButton("🃏 Блэкджек", callback_data="game_bj")],
        [InlineKeyboardButton("💥 Краш", callback_data="game_crash"),
         InlineKeyboardButton("🔫 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton("🏁 Гонки", callback_data="game_race")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ])


def bonus_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Ежедневный бонус", callback_data="daily_bonus")],
        [InlineKeyboardButton("🎡 Колесо фортуны", callback_data="wheel")],
        [InlineKeyboardButton("🎟️ Лотерея", callback_data="lottery_menu")],
        [InlineKeyboardButton("🔥 Челленджи", callback_data="challenges_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ])


def top_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 По балансу", callback_data="top_balance")],
        [InlineKeyboardButton("🎮 По играм", callback_data="top_games")],
        [InlineKeyboardButton("📊 По уровню", callback_data="top_level")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ])


def social_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Друзья", callback_data="friends_list"),
         InlineKeyboardButton("📨 Заявки", callback_data="friend_requests")],
        [InlineKeyboardButton("🏰 Клан", callback_data="clan_menu"),
         InlineKeyboardButton("⚔️ Дуэли", callback_data="duels_menu")],
        [InlineKeyboardButton("🏆 Турнир", callback_data="tournament_menu"),
         InlineKeyboardButton("🏪 Рынок", callback_data="market_menu")],
        [InlineKeyboardButton("💼 Инвестиции", callback_data="invest_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ])


def shop_menu_kb():
    from config import SHOP_ITEMS
    buttons = []
    for item_id, item in SHOP_ITEMS.items():
        from config import fmt
        buttons.append([InlineKeyboardButton(
            f"{item['name']} — {fmt(item['price'])} 💰",
            callback_data=f"buy_{item_id}"
        )])
    buttons.append([InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def cases_menu_kb():
    from config import CASES, fmt
    buttons = []
    for case_id, case in CASES.items():
        buttons.append([InlineKeyboardButton(
            f"{case['name']} — {fmt(case['price'])} 💰",
            callback_data=f"case_{case_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def business_menu_kb(user_businesses):
    from config import BUSINESSES, fmt
    owned = {b["business_id"] for b in user_businesses}
    buttons = []
    for biz_id, biz in BUSINESSES.items():
        if biz_id in owned:
            buttons.append([InlineKeyboardButton(f"✅ {biz['name']} (управление)", callback_data=f"biz_{biz_id}")])
        else:
            buttons.append([InlineKeyboardButton(f"{biz['name']} — {fmt(biz['price'])} 💰", callback_data=f"buybiz_{biz_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def bet_kb(game, presets=None):
    if presets is None:
        presets = [100, 500, 1000, 5000, 10000]
    from config import fmt
    buttons = []
    row = []
    for p in presets:
        row.append(InlineKeyboardButton(fmt(p), callback_data=f"{game}_bet_{p}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="games_menu")])
    return InlineKeyboardMarkup(buttons)


def mines_count_kb(bet):
    buttons = []
    row = []
    for i in range(1, 6):
        row.append(InlineKeyboardButton(f"💣 {i}", callback_data=f"mines_start_{bet}_{i}"))
    buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def mines_field_kb(field_state, opened, game_id):
    buttons = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            if idx in opened:
                if field_state[idx]:
                    row.append(InlineKeyboardButton("💣", callback_data="noop"))
                else:
                    row.append(InlineKeyboardButton("💎", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"mines_open_{game_id}_{idx}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("💰 Забрать", callback_data=f"mines_cashout_{game_id}")])
    return InlineKeyboardMarkup(buttons)


def mines_revealed_kb(field_state, opened):
    buttons = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            if field_state[idx]:
                row.append(InlineKeyboardButton("💣", callback_data="noop"))
            elif idx in opened:
                row.append(InlineKeyboardButton("💎", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("✅", callback_data="noop"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def tower_floor_kb(floor, cells, game_id):
    buttons = []
    row = []
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for i in range(cells):
        row.append(InlineKeyboardButton(emojis[i], callback_data=f"tower_pick_{game_id}_{floor}_{i}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton("💰 Забрать", callback_data=f"tower_cashout_{game_id}")])
    return InlineKeyboardMarkup(buttons)


def tower_heights_kb(bet):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("5 этажей", callback_data=f"tower_start_{bet}_5"),
         InlineKeyboardButton("8 этажей", callback_data=f"tower_start_{bet}_8"),
         InlineKeyboardButton("12 этажей", callback_data=f"tower_start_{bet}_12")],
    ])


def coinflip_kb(bet):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🦅 Орёл", callback_data=f"coin_pick_{bet}_орёл"),
         InlineKeyboardButton("🪙 Решка", callback_data=f"coin_pick_{bet}_решка")],
    ])


def bj_action_kb(game_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 Ещё", callback_data=f"bj_hit_{game_id}"),
         InlineKeyboardButton("✋ Стоп", callback_data=f"bj_stand_{game_id}")],
    ])


def race_pick_kb(bet):
    from config import RACE_CARS
    buttons = []
    for i, car in enumerate(RACE_CARS):
        buttons.append(InlineKeyboardButton(car, callback_data=f"race_pick_{bet}_{i}"))
    return InlineKeyboardMarkup([buttons])


def back_kb(target="main_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=target)]])


def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("💰 +10.000", callback_data="admin_give10k"),
         InlineKeyboardButton("💸 -5.000", callback_data="admin_take5k")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton("🎫 Создать промо", callback_data="admin_promo")],
        [InlineKeyboardButton("🏆 Создать турнир", callback_data="admin_tournament"),
         InlineKeyboardButton("🔥 Создать челлендж", callback_data="admin_challenge")],
        [InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Разбан", callback_data="admin_unban")],
    ])
