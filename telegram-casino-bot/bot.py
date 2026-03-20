import logging
import time
import random
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import *
import database as db
import games
import keyboards as kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище активных игр
active_games = {}
game_counter = 0

def next_game_id():
    global game_counter
    game_counter += 1
    return game_counter

def get_name(user):
    return user.first_name or user.username or str(user.id)

async def check_ban(user_id):
    u = db.get_user(user_id)
    return u and u["banned"]

# ===== КОМАНДЫ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await check_ban(user.id):
        return await update.message.reply_text("🚫 Вы заблокированы.")
    db.ensure_user(user.id, user.username or "", get_name(user))
    await update.message.reply_text(
        f"🎰 *Добро пожаловать в Казино!*\n\n"
        f"Привет, {get_name(user)}!\n"
        f"Твой начальный баланс: *{fmt(START_BALANCE)}* 💰\n\n"
        f"Выбери действие:",
        parse_mode="Markdown",
        reply_markup=kb.main_menu_kb()
    )

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await check_ban(user.id):
        return
    db.ensure_user(user.id, user.username or "", get_name(user))
    await update.message.reply_text("📋 *Главное меню:*", parse_mode="Markdown", reply_markup=kb.main_menu_kb())

# ===== ПРОФИЛЬ / БАЛАНС =====

async def show_profile(query, user_id):
    u = db.get_user(user_id)
    if not u:
        return await query.edit_message_text("Профиль не найден.")
    rank = db.get_rank(u["rating_points"])
    xp_needed = int(LEVEL_BASE_XP * (LEVEL_XP_MULTIPLIER ** (u["level"] - 1)))
    title = u["title"] if u["title"] else "—"
    avatar = u["avatar"] if u["avatar"] else "👤"
    prestige_txt = f"⭐ Престиж: {u['prestige']}\n" if u["prestige"] > 0 else ""
    winrate = round(u["total_wins"] / max(u["total_games"], 1) * 100, 1)

    text = (
        f"{avatar} *Профиль*\n\n"
        f"📛 Имя: {u['first_name']}\n"
        f"🏷️ Титул: {title}\n"
        f"🎖️ Звание: {rank}\n"
        f"{prestige_txt}"
        f"📊 Уровень: {u['level']} ({u['xp']}/{xp_needed} XP)\n"
        f"💰 Баланс: {fmt(u['balance'])}\n"
        f"🎮 Игр: {fmt(u['total_games'])} (побед: {fmt(u['total_wins'])} — {winrate}%)\n"
        f"🔥 Макс. серия: {u['max_win_streak']}\n"
        f"📈 Рейтинг: {fmt(u['rating_points'])}\n"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())

async def show_balance(query, user_id):
    bal = db.get_balance(user_id)
    await query.edit_message_text(f"💰 Ваш баланс: *{fmt(bal)}* монет", parse_mode="Markdown", reply_markup=kb.back_kb())

# ===== ЕЖЕДНЕВНЫЙ БОНУС =====

async def daily_bonus(query, user_id):
    u = db.get_user(user_id)
    last = u["last_daily"]
    if time.time() - last < 86400:
        remaining = int(86400 - (time.time() - last))
        h, m = remaining // 3600, (remaining % 3600) // 60
        return await query.edit_message_text(
            f"⏳ Бонус уже получен!\nСледующий через: {h}ч {m}мин",
            reply_markup=kb.back_kb("bonus_menu")
        )
    bonus = DAILY_BONUS
    if u["vip_until"] > time.time():
        bonus = int(bonus * 1.5)
    db.update_balance(user_id, bonus)
    db.update_daily(user_id)
    await query.edit_message_text(
        f"🎁 Ежедневный бонус: *+{fmt(bonus)}* 💰",
        parse_mode="Markdown", reply_markup=kb.back_kb("bonus_menu")
    )

# ===== КОЛЕСО ФОРТУНЫ =====

async def wheel_spin(query, user_id):
    u = db.get_user(user_id)
    last = u["last_wheel"]
    if time.time() - last < 86400:
        remaining = int(86400 - (time.time() - last))
        h, m = remaining // 3600, (remaining % 3600) // 60
        return await query.edit_message_text(
            f"⏳ Колесо уже крутили!\nСледующее через: {h}ч {m}мин",
            reply_markup=kb.back_kb("bonus_menu")
        )
    prize = games.spin_wheel()
    db.update_balance(user_id, prize)
    db.update_wheel(user_id)
    if prize == 0:
        text = "🎡 Колесо фортуны...\n\n😢 Не повезло! Попробуйте завтра."
    else:
        text = f"🎡 Колесо фортуны...\n\n🎉 Выигрыш: *+{fmt(prize)}* 💰!"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("bonus_menu"))

# ===== ДОСТИЖЕНИЯ =====

async def show_achievements(query, user_id):
    unlocked = db.get_user_achievements(user_id)
    text = "🎖️ *Достижения:*\n\n"
    for ach_id, ach in ACHIEVEMENTS.items():
        check = "✅" if ach_id in unlocked else "❌"
        text += f"{check} {ach['name']}\n   {ach['description']} (+{fmt(ach['reward'])} 💰)\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())

async def notify_achievements(query, user_id):
    new = db.check_achievements(user_id)
    for ach_id in new:
        ach = ACHIEVEMENTS[ach_id]
        try:
            await query.message.reply_text(
                f"🏆 *Достижение разблокировано!*\n{ach['name']}\n+{fmt(ach['reward'])} 💰",
                parse_mode="Markdown"
            )
        except:
            pass

# ===== МАГАЗИН =====

async def buy_item(query, user_id, item_id):
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return await query.answer("Предмет не найден", show_alert=True)
    bal = db.get_balance(user_id)
    if bal < item["price"]:
        return await query.answer(f"Недостаточно монет! Нужно: {fmt(item['price'])}", show_alert=True)

    db.update_balance(user_id, -item["price"])
    expires = 0
    if item["type"] == "status" and "duration_days" in item:
        expires = time.time() + item["duration_days"] * 86400
        conn = db.get_db()
        conn.execute("UPDATE users SET vip_until=? WHERE user_id=?", (expires, user_id))
        conn.commit()
        conn.close()
    elif item["type"] == "title":
        conn = db.get_db()
        conn.execute("UPDATE users SET title=? WHERE user_id=?", (item["name"], user_id))
        conn.commit()
        conn.close()
    elif item["type"] == "avatar":
        emoji = item["name"].split()[0]
        conn = db.get_db()
        conn.execute("UPDATE users SET avatar=? WHERE user_id=?", (emoji, user_id))
        conn.commit()
        conn.close()
    elif item["type"] == "booster":
        expires = time.time() + item.get("duration_hours", 24) * 3600

    db.add_item(user_id, item_id, expires)
    await query.answer(f"✅ Куплено: {item['name']}", show_alert=True)
    await query.edit_message_text(
        f"✅ Вы купили: {item['name']}\n💰 Списано: {fmt(item['price'])}",
        reply_markup=kb.back_kb("shop_menu")
    )

# ===== ИНВЕНТАРЬ =====

async def show_inventory(query, user_id):
    items = db.get_inventory(user_id)
    if not items:
        return await query.edit_message_text("🎒 Инвентарь пуст", reply_markup=kb.back_kb("shop_menu"))
    text = "🎒 *Инвентарь:*\n\n"
    for item in items:
        info = SHOP_ITEMS.get(item["item_id"], {"name": item["item_id"]})
        exp = ""
        if item["expires_at"] > 0:
            remaining = int(item["expires_at"] - time.time())
            if remaining > 0:
                h = remaining // 3600
                exp = f" (осталось {h}ч)"
            else:
                exp = " (истёк)"
        text += f"• {info.get('name', item['item_id'])} x{item['quantity']}{exp}\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("shop_menu"))

# ===== КЕЙСЫ =====

async def open_case(query, user_id, case_id):
    case = CASES.get(case_id)
    if not case:
        return await query.answer("Кейс не найден", show_alert=True)
    bal = db.get_balance(user_id)
    if bal < case["price"]:
        return await query.answer(f"Недостаточно монет! Нужно: {fmt(case['price'])}", show_alert=True)
    db.update_balance(user_id, -case["price"])
    rewards = case["rewards"]
    total_weight = sum(w for _, w in rewards)
    r = random.randint(1, total_weight)
    cum = 0
    prize = rewards[0][0]
    for amount, weight in rewards:
        cum += weight
        if r <= cum:
            prize = amount
            break
    db.update_balance(user_id, prize)
    profit = prize - case["price"]
    emoji = "🎉" if profit > 0 else "😢"
    await query.edit_message_text(
        f"📦 Открываем {case['name']}...\n\n{emoji} Выпало: *{fmt(prize)}* 💰\n"
        f"{'📈 Профит' if profit >= 0 else '📉 Убыток'}: {fmt(abs(profit))} 💰",
        parse_mode="Markdown", reply_markup=kb.back_kb("cases_menu")
    )

# ===== БИЗНЕС =====

async def show_business_menu(query, user_id):
    businesses = db.get_user_businesses(user_id)
    await query.edit_message_text("💼 *Бизнес:*", parse_mode="Markdown", reply_markup=kb.business_menu_kb(businesses))

async def buy_business(query, user_id, biz_id):
    biz = BUSINESSES.get(biz_id)
    if not biz:
        return await query.answer("Не найдено", show_alert=True)
    bal = db.get_balance(user_id)
    if bal < biz["price"]:
        return await query.answer(f"Нужно: {fmt(biz['price'])} 💰", show_alert=True)
    existing = db.get_user_businesses(user_id)
    if any(b["business_id"] == biz_id for b in existing):
        return await query.answer("Уже куплено!", show_alert=True)
    db.update_balance(user_id, -biz["price"])
    db.buy_business(user_id, biz_id)
    await query.answer(f"✅ Куплено: {biz['name']}", show_alert=True)
    await show_business_menu(query, user_id)

async def manage_business(query, user_id, biz_id):
    biz = BUSINESSES.get(biz_id)
    businesses = db.get_user_businesses(user_id)
    owned = next((b for b in businesses if b["business_id"] == biz_id), None)
    if not owned:
        return await query.answer("У вас нет этого бизнеса", show_alert=True)

    income = biz["income"] * owned["level"]
    # Check income boost
    if db.has_item(user_id, "income_boost"):
        income *= 2
    interval = biz["interval_hours"] * 3600
    elapsed = time.time() - owned["last_collect"]
    ready = elapsed >= interval
    upgrade_cost = biz["upgrade_cost"] * owned["level"]

    status = "✅ Доход готов!" if ready else f"⏳ {int((interval - elapsed) // 60)} мин"
    text = (
        f"{biz['name']}\n\n"
        f"📊 Уровень: {owned['level']}/{biz['max_level']}\n"
        f"💰 Доход: {fmt(income)} / {biz['interval_hours']}ч\n"
        f"📦 Статус: {status}\n"
    )
    buttons = []
    if ready:
        buttons.append([InlineKeyboardButton("💰 Собрать доход", callback_data=f"biz_collect_{biz_id}")])
    if owned["level"] < biz["max_level"]:
        buttons.append([InlineKeyboardButton(f"⬆️ Улучшить ({fmt(upgrade_cost)} 💰)", callback_data=f"biz_upgrade_{biz_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="business_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def collect_business_income(query, user_id, biz_id):
    biz = BUSINESSES.get(biz_id)
    businesses = db.get_user_businesses(user_id)
    owned = next((b for b in businesses if b["business_id"] == biz_id), None)
    if not owned:
        return
    interval = biz["interval_hours"] * 3600
    if time.time() - owned["last_collect"] < interval:
        return await query.answer("⏳ Доход ещё не готов", show_alert=True)
    income = biz["income"] * owned["level"]
    if db.has_item(user_id, "income_boost"):
        income *= 2
    db.update_balance(user_id, income)
    db.collect_business(user_id, biz_id)
    await query.answer(f"💰 +{fmt(income)}", show_alert=True)
    await manage_business(query, user_id, biz_id)

async def upgrade_business_handler(query, user_id, biz_id):
    biz = BUSINESSES.get(biz_id)
    businesses = db.get_user_businesses(user_id)
    owned = next((b for b in businesses if b["business_id"] == biz_id), None)
    if not owned:
        return
    if owned["level"] >= biz["max_level"]:
        return await query.answer("Максимальный уровень!", show_alert=True)
    cost = biz["upgrade_cost"] * owned["level"]
    if db.get_balance(user_id) < cost:
        return await query.answer(f"Нужно: {fmt(cost)} 💰", show_alert=True)
    db.update_balance(user_id, -cost)
    db.upgrade_business(user_id, biz_id)
    await query.answer("⬆️ Улучшено!", show_alert=True)
    await manage_business(query, user_id, biz_id)

# ===== ИГРА: МИНЫ =====

async def start_mines_bet(query, user_id):
    await query.edit_message_text("💣 *Мины*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("mines"))

async def mines_set_bet(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer(f"Недостаточно монет!", show_alert=True)
    if bet < MIN_BET:
        return await query.answer(f"Мин. ставка: {fmt(MIN_BET)}", show_alert=True)
    await query.edit_message_text(
        f"💣 Ставка: *{fmt(bet)}* 💰\nВыберите кол-во мин:",
        parse_mode="Markdown", reply_markup=kb.mines_count_kb(bet)
    )

async def mines_start(query, user_id, bet, num_mines):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    field, mines_pos = games.create_mines_field(num_mines)
    gid = next_game_id()
    active_games[gid] = {
        "type": "mines", "user_id": user_id, "bet": bet,
        "field": field, "mines_pos": mines_pos, "opened": [],
        "num_mines": num_mines
    }
    mult = games.mines_multiplier(0, num_mines)
    await query.edit_message_text(
        f"💣 *Мины* | Ставка: {fmt(bet)} | Мин: {num_mines}\n"
        f"Множитель: x{mult} | Выигрыш: {fmt(int(bet * mult))}\n"
        f"Открывайте клетки!",
        parse_mode="Markdown", reply_markup=kb.mines_field_kb(field, [], gid)
    )

async def mines_open(query, user_id, gid, idx):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id:
        return await query.answer("Игра не найдена", show_alert=True)
    if idx in game["opened"]:
        return
    if game["field"][idx]:
        # BOOM
        game["opened"].append(idx)
        db.record_game(user_id, "mines", game["bet"], False, -game["bet"])
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -10)
        has_insurance = db.use_item(user_id, "insurance")
        refund = ""
        if has_insurance:
            r = game["bet"] // 2
            db.update_balance(user_id, r)
            refund = f"\n🛡️ Страховка: +{fmt(r)} 💰"
        text = f"💥 *БУМ!* Вы проиграли *{fmt(game['bet'])}* 💰{refund}"
        del active_games[gid]
        await query.edit_message_text(text, parse_mode="Markdown",
                                       reply_markup=kb.mines_revealed_kb(game["field"], game["opened"]))
        await notify_achievements(query, user_id)
    else:
        game["opened"].append(idx)
        mult = games.mines_multiplier(len(game["opened"]), game["num_mines"])
        safe_total = 25 - game["num_mines"]
        if len(game["opened"]) == safe_total:
            winnings = int(game["bet"] * mult)
            db.update_balance(user_id, winnings)
            db.record_game(user_id, "mines", game["bet"], True, winnings, mult)
            db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
            db.update_rating(user_id, 20)
            del active_games[gid]
            text = f"🎉 *ВСЕ КЛЕТКИ ОТКРЫТЫ!*\nx{mult} — Выигрыш: *{fmt(winnings)}* 💰"
            await query.edit_message_text(text, parse_mode="Markdown",
                                           reply_markup=kb.mines_revealed_kb(game["field"], game["opened"]))
            await notify_achievements(query, user_id)
        else:
            win = int(game["bet"] * mult)
            text = (f"💣 *Мины* | Ставка: {fmt(game['bet'])} | Мин: {game['num_mines']}\n"
                    f"Множитель: x{mult} | Выигрыш: {fmt(win)}\n"
                    f"Открыто: {len(game['opened'])}/{safe_total}")
            await query.edit_message_text(text, parse_mode="Markdown",
                                           reply_markup=kb.mines_field_kb(game["field"], game["opened"], gid))

async def mines_cashout(query, user_id, gid):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id:
        return await query.answer("Игра не найдена", show_alert=True)
    if not game["opened"]:
        return await query.answer("Откройте хотя бы одну клетку!", show_alert=True)
    mult = games.mines_multiplier(len(game["opened"]), game["num_mines"])
    winnings = int(game["bet"] * mult)
    db.update_balance(user_id, winnings)
    profit = winnings - game["bet"]
    db.record_game(user_id, "mines", game["bet"], True, winnings, mult)
    db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
    db.update_rating(user_id, 15)
    if profit >= 100000:
        db.check_achievements(user_id)  # big_win
    del active_games[gid]
    text = f"💰 *Забрали!*\nx{mult} — Выигрыш: *{fmt(winnings)}* 💰 (профит: +{fmt(profit)})"
    await query.edit_message_text(text, parse_mode="Markdown",
                                   reply_markup=kb.mines_revealed_kb(game["field"], game["opened"]))
    await notify_achievements(query, user_id)

# ===== ИГРА: БАШНЯ =====

async def start_tower_bet(query, user_id):
    await query.edit_message_text("🏗️ *Башня*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("tower"))

async def tower_set_bet(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    await query.edit_message_text(
        f"🏗️ Ставка: *{fmt(bet)}* 💰\nВыберите высоту:",
        parse_mode="Markdown", reply_markup=kb.tower_heights_kb(bet)
    )

async def tower_start(query, user_id, bet, height):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    tower = games.create_tower(height)
    gid = next_game_id()
    active_games[gid] = {
        "type": "tower", "user_id": user_id, "bet": bet,
        "tower": tower, "height": height, "floor": 0
    }
    cells = tower[0]["cells"]
    mult = games.tower_multiplier(1, height)
    text = f"🏗️ *Башня* | Ставка: {fmt(bet)} | Этажей: {height}\n\nЭтаж 1/{height} — выберите клетку:"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.tower_floor_kb(0, cells, gid))

async def tower_pick(query, user_id, gid, floor, pick):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id:
        return await query.answer("Игра не найдена", show_alert=True)
    if floor != game["floor"]:
        return
    tower_floor = game["tower"][floor]
    if pick == tower_floor["bomb"]:
        db.record_game(user_id, "tower", game["bet"], False, -game["bet"])
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -10)
        has_ins = db.use_item(user_id, "insurance")
        refund = ""
        if has_ins:
            r = game["bet"] // 2
            db.update_balance(user_id, r)
            refund = f"\n🛡️ Страховка: +{fmt(r)} 💰"
        del active_games[gid]
        text = f"💥 *Провал на этаже {floor + 1}!*\nПроиграно: *{fmt(game['bet'])}* 💰{refund}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
        await notify_achievements(query, user_id)
    else:
        game["floor"] = floor + 1
        if game["floor"] >= game["height"]:
            mult = games.tower_multiplier(game["height"], game["height"])
            winnings = int(game["bet"] * mult)
            db.update_balance(user_id, winnings)
            db.record_game(user_id, "tower", game["bet"], True, winnings, mult)
            db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
            db.update_rating(user_id, 25)
            del active_games[gid]
            text = f"🎉 *ВЕРШИНА!*\nx{mult} — Выигрыш: *{fmt(winnings)}* 💰"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
            await notify_achievements(query, user_id)
        else:
            f = game["floor"]
            cells = game["tower"][f]["cells"]
            mult = games.tower_multiplier(f + 1, game["height"])
            win = int(game["bet"] * mult)
            text = (f"🏗️ Этаж {f + 1}/{game['height']}\n"
                    f"Множитель: x{games.tower_multiplier(f, game['height'])} → x{mult}\n"
                    f"Выберите клетку:")
            await query.edit_message_text(text, parse_mode="Markdown",
                                           reply_markup=kb.tower_floor_kb(f, cells, gid))

async def tower_cashout(query, user_id, gid):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id:
        return await query.answer("Игра не найдена", show_alert=True)
    if game["floor"] == 0:
        return await query.answer("Пройдите хотя бы один этаж!", show_alert=True)
    mult = games.tower_multiplier(game["floor"], game["height"])
    winnings = int(game["bet"] * mult)
    db.update_balance(user_id, winnings)
    db.record_game(user_id, "tower", game["bet"], True, winnings, mult)
    db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
    db.update_rating(user_id, 15)
    del active_games[gid]
    text = f"💰 *Забрали на этаже {game['floor']}!*\nx{mult} — Выигрыш: *{fmt(winnings)}* 💰"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ИГРА: СЛОТЫ =====

async def start_slots_bet(query, user_id):
    await query.edit_message_text("🎰 *Слоты*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("slots"))

async def slots_play(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    reels = games.spin_slots()
    payout = games.slots_payout(reels, bet)
    display = " | ".join(reels)
    if payout > 0:
        db.update_balance(user_id, payout)
        profit = payout - bet
        mult = round(payout / bet, 1)
        db.record_game(user_id, "slots", bet, True, payout, mult)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 10)
        text = f"🎰 [ {display} ]\n\n🎉 *Выигрыш: {fmt(payout)}* 💰 (x{mult})"
    else:
        db.record_game(user_id, "slots", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        text = f"🎰 [ {display} ]\n\n😢 Не повезло! -{fmt(bet)} 💰"
    buttons = [
        [InlineKeyboardButton(f"🔄 Ещё ({fmt(bet)})", callback_data=f"slots_bet_{bet}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    await notify_achievements(query, user_id)

# ===== ИГРА: ОРЁЛ И РЕШКА =====

async def start_coin_bet(query, user_id):
    await query.edit_message_text("🪙 *Орёл и решка*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("coin"))

async def coin_set_bet(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    await query.edit_message_text(
        f"🪙 Ставка: *{fmt(bet)}* 💰\nВыберите сторону:",
        parse_mode="Markdown", reply_markup=kb.coinflip_kb(bet)
    )

async def coin_play(query, user_id, bet, choice):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    result = games.coinflip()
    won = result == choice
    if won:
        winnings = bet * 2
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "coinflip", bet, True, winnings, 2.0)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 8)
        emoji = "🦅" if result == "орёл" else "🪙"
        text = f"{emoji} Выпал: *{result}*\n\n🎉 Выигрыш: *{fmt(winnings)}* 💰!"
    else:
        db.record_game(user_id, "coinflip", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        emoji = "🦅" if result == "орёл" else "🪙"
        text = f"{emoji} Выпал: *{result}*\n\n😢 Проигрыш: *-{fmt(bet)}* 💰"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ИГРА: КОСТИ =====

async def start_dice_bet(query, user_id):
    await query.edit_message_text("🎲 *Кости*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("dice"))

async def dice_play(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    p1, p2 = games.roll_dice()
    b1, b2 = games.roll_dice()
    player_total = p1 + p2
    bot_total = b1 + b2
    text = f"🎲 Вы: {p1} + {p2} = *{player_total}*\n🤖 Бот: {b1} + {b2} = *{bot_total}*\n\n"
    if player_total > bot_total:
        winnings = bet * 2
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "dice", bet, True, winnings, 2.0)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 8)
        text += f"🎉 Победа! +{fmt(winnings)} 💰"
    elif player_total < bot_total:
        db.record_game(user_id, "dice", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        text += f"😢 Проигрыш! -{fmt(bet)} 💰"
    else:
        db.update_balance(user_id, bet)
        db.record_game(user_id, "dice", bet, False, 0)
        db.add_xp(user_id, XP_PER_GAME)
        text += "🤝 Ничья! Ставка возвращена."
    buttons = [
        [InlineKeyboardButton(f"🔄 Ещё ({fmt(bet)})", callback_data=f"dice_bet_{bet}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="games_menu")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    await notify_achievements(query, user_id)

# ===== ИГРА: БЛЭКДЖЕК =====

async def start_bj_bet(query, user_id):
    await query.edit_message_text("🃏 *Блэкджек (21)*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("bj"))

async def bj_start(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    deck = games.new_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    gid = next_game_id()
    active_games[gid] = {
        "type": "bj", "user_id": user_id, "bet": bet,
        "deck": deck, "player": player, "dealer": dealer
    }
    pv = games.hand_value(player)
    if pv == 21:
        return await bj_finish(query, user_id, gid, blackjack=True)
    text = (f"🃏 *Блэкджек*\n\n"
            f"Вы: {games.hand_str(player)} ({pv})\n"
            f"Дилер: {games.card_str(dealer[0])} 🂠")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.bj_action_kb(gid))

async def bj_hit(query, user_id, gid):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id:
        return
    game["player"].append(game["deck"].pop())
    pv = games.hand_value(game["player"])
    if pv > 21:
        return await bj_finish(query, user_id, gid)
    if pv == 21:
        return await bj_finish(query, user_id, gid)
    text = (f"🃏 *Блэкджек*\n\n"
            f"Вы: {games.hand_str(game['player'])} ({pv})\n"
            f"Дилер: {games.card_str(game['dealer'][0])} 🂠")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.bj_action_kb(gid))

async def bj_finish(query, user_id, gid, blackjack=False):
    game = active_games.get(gid)
    if not game:
        return
    player = game["player"]
    dealer = game["dealer"]
    deck = game["deck"]
    pv = games.hand_value(player)
    dv = games.hand_value(dealer)
    if pv <= 21:
        while dv < 17:
            dealer.append(deck.pop())
            dv = games.hand_value(dealer)
    text = (f"🃏 *Результат*\n\n"
            f"Вы: {games.hand_str(player)} ({pv})\n"
            f"Дилер: {games.hand_str(dealer)} ({dv})\n\n")
    bet = game["bet"]
    if pv > 21:
        db.record_game(user_id, "blackjack", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        text += f"💥 Перебор! -{fmt(bet)} 💰"
    elif blackjack:
        winnings = int(bet * 2.5)
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "blackjack", bet, True, winnings, 2.5)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 15)
        text += f"🎰 *БЛЭКДЖЕК!* +{fmt(winnings)} 💰"
    elif dv > 21:
        winnings = bet * 2
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "blackjack", bet, True, winnings, 2.0)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 10)
        text += f"🎉 Дилер перебрал! +{fmt(winnings)} 💰"
    elif pv > dv:
        winnings = bet * 2
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "blackjack", bet, True, winnings, 2.0)
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 10)
        text += f"🎉 Победа! +{fmt(winnings)} 💰"
    elif pv < dv:
        db.record_game(user_id, "blackjack", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        text += f"😢 Проигрыш! -{fmt(bet)} 💰"
    else:
        db.update_balance(user_id, bet)
        db.record_game(user_id, "blackjack", bet, False, 0)
        db.add_xp(user_id, XP_PER_GAME)
        text += "🤝 Ничья! Ставка возвращена."
    del active_games[gid]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ИГРА: КРАШ =====

async def start_crash_bet(query, user_id):
    await query.edit_message_text("💥 *Краш*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("crash"))

async def crash_start(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    crash_at = games.generate_crash_point()
    gid = next_game_id()
    active_games[gid] = {
        "type": "crash", "user_id": user_id, "bet": bet,
        "crash_at": crash_at, "current": 1.0, "cashed": False
    }
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 ЗАБРАТЬ", callback_data=f"crash_cashout_{gid}")],
    ])
    await query.edit_message_text(
        f"💥 *Краш* | Ставка: {fmt(bet)}\n\n📈 Множитель: x1.00\n💰 Выигрыш: {fmt(bet)}",
        parse_mode="Markdown", reply_markup=buttons
    )
    # Run crash game
    asyncio.create_task(crash_loop(query, gid))

async def crash_loop(query, gid):
    game = active_games.get(gid)
    if not game:
        return
    step = 0
    while gid in active_games and not active_games[gid]["cashed"]:
        await asyncio.sleep(CRASH_TICK_SECONDS)
        if gid not in active_games:
            return
        game = active_games[gid]
        step += 1
        game["current"] = round(1.0 + step * 0.15, 2)
        if game["current"] >= game["crash_at"]:
            # Crashed
            user_id = game["user_id"]
            bet = game["bet"]
            db.record_game(user_id, "crash", bet, False, -bet)
            db.add_xp(user_id, XP_PER_GAME)
            db.update_rating(user_id, -5)
            has_ins = db.use_item(user_id, "insurance")
            refund = ""
            if has_ins:
                r = bet // 2
                db.update_balance(user_id, r)
                refund = f"\n🛡️ Страховка: +{fmt(r)} 💰"
            del active_games[gid]
            try:
                await query.edit_message_text(
                    f"💥 *КРАШ на x{game['crash_at']}!*\n\n😢 Проигрыш: -{fmt(bet)} 💰{refund}",
                    parse_mode="Markdown", reply_markup=kb.back_kb("games_menu")
                )
            except:
                pass
            return
        win = int(game["bet"] * game["current"])
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💰 ЗАБРАТЬ x{game['current']}", callback_data=f"crash_cashout_{gid}")],
        ])
        try:
            await query.edit_message_text(
                f"💥 *Краш* | Ставка: {fmt(game['bet'])}\n\n📈 Множитель: x{game['current']}\n💰 Выигрыш: {fmt(win)}",
                parse_mode="Markdown", reply_markup=buttons
            )
        except:
            pass

async def crash_cashout(query, user_id, gid):
    game = active_games.get(gid)
    if not game or game["user_id"] != user_id or game["cashed"]:
        return await query.answer("Игра не найдена", show_alert=True)
    game["cashed"] = True
    mult = game["current"]
    winnings = int(game["bet"] * mult)
    db.update_balance(user_id, winnings)
    db.record_game(user_id, "crash", game["bet"], True, winnings, mult)
    db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
    db.update_rating(user_id, 10)
    del active_games[gid]
    text = f"💰 *Забрали на x{mult}!*\nВыигрыш: *{fmt(winnings)}* 💰\n(Краш был бы на x{game['crash_at']})"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ИГРА: РУССКАЯ РУЛЕТКА =====

async def start_roulette_bet(query, user_id):
    await query.edit_message_text("🔫 *Русская рулетка*\n1 патрон, 6 камер\nВыиграл = x6, проиграл = 💀\n\nВыберите ставку:",
                                   parse_mode="Markdown", reply_markup=kb.bet_kb("roulette"))

async def roulette_play(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    bang = games.russian_roulette()
    if bang:
        db.record_game(user_id, "roulette", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -10)
        text = f"🔫 *BANG!* 💀\n\nПроигрыш: -{fmt(bet)} 💰"
    else:
        winnings = bet * ROULETTE_CHAMBERS
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "roulette", bet, True, winnings, float(ROULETTE_CHAMBERS))
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 20)
        text = f"🔫 *Клик...* Пусто!\n\n🎉 Выигрыш: *{fmt(winnings)}* 💰 (x{ROULETTE_CHAMBERS})"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ИГРА: ГОНКИ =====

async def start_race_bet(query, user_id):
    await query.edit_message_text("🏁 *Гонки*\nВыберите ставку:", parse_mode="Markdown", reply_markup=kb.bet_kb("race"))

async def race_set_bet(query, user_id, bet):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    text = f"🏁 Ставка: *{fmt(bet)}* 💰\nВыберите машину:"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.race_pick_kb(bet))

async def race_play(query, user_id, bet, pick):
    bal = db.get_balance(user_id)
    if bal < bet:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -bet)
    results = games.run_race()
    winner = RACE_CARS[0]
    for i, car in enumerate(results):
        if car == RACE_CARS[pick]:
            player_pos = i + 1
    picked_car = RACE_CARS[pick]
    won = results[0] == picked_car
    race_display = "\n".join(f"{'🏆' if i == 0 else f'{i+1}.'} {car}" for i, car in enumerate(results))
    if won:
        winnings = bet * len(RACE_CARS)
        db.update_balance(user_id, winnings)
        db.record_game(user_id, "race", bet, True, winnings, float(len(RACE_CARS)))
        db.add_xp(user_id, XP_PER_GAME + XP_PER_WIN)
        db.update_rating(user_id, 15)
        text = f"🏁 *Результат гонки:*\n\n{race_display}\n\n🎉 Ваш {picked_car} победил! +{fmt(winnings)} 💰"
    else:
        db.record_game(user_id, "race", bet, False, -bet)
        db.add_xp(user_id, XP_PER_GAME)
        db.update_rating(user_id, -5)
        text = f"🏁 *Результат гонки:*\n\n{race_display}\n\n😢 Ваш {picked_car} не победил. -{fmt(bet)} 💰"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("games_menu"))
    await notify_achievements(query, user_id)

# ===== ТОПЫ =====

async def show_top(query, top_type):
    if top_type == "balance":
        rows = db.get_top_balance(20)
        title = "💰 Топ по балансу"
        fmt_row = lambda i, r: f"{i+1}. {r['first_name']} — {fmt(r['balance'])} 💰"
    elif top_type == "games":
        rows = db.get_top_games(20)
        title = "🎮 Топ по играм"
        fmt_row = lambda i, r: f"{i+1}. {r['first_name']} — {fmt(r['total_games'])} игр"
    else:
        rows = db.get_top_level(20)
        title = "📊 Топ по уровню"
        fmt_row = lambda i, r: f"{i+1}. {r['first_name']} — Ур.{r['level']}"
    text = f"🏆 *{title}:*\n\n"
    for i, r in enumerate(rows):
        text += fmt_row(i, r) + "\n"
    if not rows:
        text += "Пока пусто..."
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("top_menu"))

# ===== СТАТИСТИКА =====

async def show_stats(query, user_id):
    u = db.get_user(user_id)
    if not u:
        return
    conn = db.get_db()
    recent = conn.execute(
        "SELECT * FROM game_history WHERE user_id=? ORDER BY played_at DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    conn.close()
    winrate = round(u["total_wins"] / max(u["total_games"], 1) * 100, 1)
    net = u["total_won"] - u["total_wagered"]
    text = (
        f"📊 *Статистика*\n\n"
        f"🎮 Всего игр: {fmt(u['total_games'])}\n"
        f"✅ Побед: {fmt(u['total_wins'])} ({winrate}%)\n"
        f"💰 Поставлено: {fmt(u['total_wagered'])}\n"
        f"💎 Выиграно: {fmt(u['total_won'])}\n"
        f"📈 Чистый P/L: {'+' if net >= 0 else ''}{fmt(net)} 💰\n"
        f"🔥 Макс. серия: {u['max_win_streak']}\n\n"
        f"📜 *Последние игры:*\n"
    )
    for g in recent:
        emoji = "✅" if g["result"] == "win" else "❌"
        text += f"{emoji} {g['game_type']} — {fmt(abs(g['profit']))} 💰\n"
    if not recent:
        text += "Нет истории игр"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb())

# ===== ЛОТЕРЕЯ =====

async def lottery_menu(query, user_id):
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    tickets = db.get_user_lottery_tickets(user_id, today)
    all_tickets = db.get_lottery_tickets(today)
    prize_pool = len(all_tickets) * LOTTERY_TICKET_PRICE
    text = (
        f"🎟️ *Лотерея*\n\n"
        f"💰 Призовой фонд: {fmt(prize_pool)} 💰\n"
        f"🎫 Всего билетов: {len(all_tickets)}\n"
        f"📌 Ваших билетов: {len(tickets)}\n"
        f"🕐 Розыгрыш в {LOTTERY_DRAW_HOUR}:00 UTC\n\n"
        f"Билет: {fmt(LOTTERY_TICKET_PRICE)} 💰"
    )
    buttons = [
        [InlineKeyboardButton(f"🎫 Купить билет ({fmt(LOTTERY_TICKET_PRICE)})", callback_data="lottery_buy")],
        [InlineKeyboardButton("🔙 Назад", callback_data="bonus_menu")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def lottery_buy(query, user_id):
    from datetime import datetime
    bal = db.get_balance(user_id)
    if bal < LOTTERY_TICKET_PRICE:
        return await query.answer("Недостаточно монет!", show_alert=True)
    db.update_balance(user_id, -LOTTERY_TICKET_PRICE)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    db.buy_lottery_ticket(user_id, today)
    await query.answer("🎫 Билет куплен!", show_alert=True)
    await lottery_menu(query, user_id)

# ===== ДУЭЛИ =====

async def duels_menu(query, user_id):
    pending = db.get_pending_duels()
    text = "⚔️ *Дуэли*\n\nОткрытые дуэли:\n"
    buttons = []
    for d in pending[:10]:
        if d["challenger_id"] == user_id:
            continue
        text += f"• #{d['id']} — Ставка: {fmt(d['bet'])} 💰\n"
        buttons.append([InlineKeyboardButton(f"⚔️ Принять #{d['id']}", callback_data=f"duel_accept_{d['id']}")])
    if not pending:
        text += "Нет открытых дуэлей\n"
    text += "\nСоздать свою:"
    buttons.append([InlineKeyboardButton("⚔️ Создать дуэль", callback_data="duel_create")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="social_menu")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== ИНВЕСТИЦИИ =====

async def invest_menu(query, user_id):
    invs = db.get_investments(user_id)
    text = "💼 *Инвестиции*\n\n"
    buttons = []
    for inv in invs:
        remaining = int((inv["matures_at"] - time.time()) / 3600)
        status = f"⏳ {remaining}ч" if remaining > 0 else "✅ Готово"
        text += f"• #{inv['id']}: {fmt(inv['amount'])} 💰 ({int(inv['rate']*100)}%) — {status}\n"
        if remaining <= 0:
            buttons.append([InlineKeyboardButton(f"💰 Забрать #{inv['id']}", callback_data=f"invest_collect_{inv['id']}")])
    text += (
        "\n📈 *Доступные вклады:*\n"
        "• 24ч — 5% доход\n"
        "• 72ч — 20% доход\n"
        "• 168ч (7 дней) — 50% доход\n"
    )
    buttons.extend([
        [InlineKeyboardButton("24ч (5%)", callback_data="invest_new_24_5"),
         InlineKeyboardButton("72ч (20%)", callback_data="invest_new_72_20"),
         InlineKeyboardButton("7д (50%)", callback_data="invest_new_168_50")],
        [InlineKeyboardButton("🔙 Назад", callback_data="social_menu")]
    ])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== ДРУЗЬЯ =====

async def friends_list(query, user_id):
    friends = db.get_friends(user_id)
    text = "👥 *Друзья:*\n\n"
    for f in friends:
        text += f"• {f['first_name']} (Ур.{f['level']}, {fmt(f['balance'])} 💰)\n"
    if not friends:
        text += "Список пуст. Отправьте /addfriend ID чтобы добавить."
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("social_menu"))

async def friend_requests_list(query, user_id):
    reqs = db.get_friend_requests(user_id)
    text = "📨 *Заявки в друзья:*\n\n"
    buttons = []
    for r in reqs:
        text += f"• {r['first_name']} (ID: {r['user_id']})\n"
        buttons.append([InlineKeyboardButton(f"✅ Принять {r['first_name']}", callback_data=f"friend_accept_{r['user_id']}")])
    if not reqs:
        text += "Нет заявок"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="social_menu")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== КЛАН =====

async def clan_menu(query, user_id):
    clan, member = db.get_user_clan(user_id)
    if not clan:
        text = "🏰 *Клан*\n\nВы не состоите в клане.\nСоздайте: /createclan Название"
        buttons = [[InlineKeyboardButton("🔙 Назад", callback_data="social_menu")]]
    else:
        members = db.get_clan_members(clan["clan_id"])
        text = (
            f"🏰 *{clan['name']}*\n\n"
            f"📊 Уровень: {clan['level']}\n"
            f"👥 Участников: {len(members)}\n"
            f"💰 Казна: {fmt(clan['balance'])} 💰\n"
            f"🎖️ Ваша роль: {member['role']}\n\n"
            f"Участники:\n"
        )
        for m in members[:10]:
            text += f"• {m['first_name']} ({m['role']})\n"
        buttons = [
            [InlineKeyboardButton("❌ Покинуть клан", callback_data="clan_leave")],
            [InlineKeyboardButton("🔙 Назад", callback_data="social_menu")]
        ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== РЫНОК =====

async def market_menu(query, user_id):
    listings = db.get_market_listings()
    text = "🏪 *Рынок*\n\n"
    buttons = []
    for l in listings[:10]:
        item_info = SHOP_ITEMS.get(l["item_id"], {"name": l["item_id"]})
        text += f"• {item_info.get('name', l['item_id'])} — {fmt(l['price'])} 💰 (от {l['first_name']})\n"
        buttons.append([InlineKeyboardButton(f"🛒 Купить #{l['id']}", callback_data=f"market_buy_{l['id']}")])
    if not listings:
        text += "Рынок пуст"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="social_menu")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== ЧЕЛЛЕНДЖИ =====

async def challenges_menu(query, user_id):
    challenges = db.get_active_challenges()
    text = "🔥 *Челленджи*\n\n"
    conn = db.get_db()
    for ch in challenges:
        prog = conn.execute("SELECT * FROM challenge_progress WHERE user_id=? AND challenge_id=?",
                            (user_id, ch["id"])).fetchone()
        p = prog["progress"] if prog else 0
        done = "✅" if prog and prog["completed"] else f"({p}/{ch['target']})"
        text += f"• {ch['description']} {done}\n  Награда: {fmt(ch['reward'])} 💰\n"
    conn.close()
    if not challenges:
        text += "Нет активных челленджей"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("bonus_menu"))

# ===== ТУРНИРЫ =====

async def tournament_menu(query, user_id):
    t = db.get_active_tournament()
    if not t:
        text = "🏆 *Турниры*\n\nНет активных турниров"
        buttons = [[InlineKeyboardButton("🔙 Назад", callback_data="social_menu")]]
    else:
        lb = db.get_tournament_leaderboard(t["id"])
        text = (
            f"🏆 *{t['name']}*\n"
            f"🎮 Игра: {t['game_type']}\n"
            f"💰 Призовой фонд: {fmt(t['prize_pool'])} 💰\n"
            f"📊 Вход: {fmt(t['entry_fee'])} 💰\n\n"
            f"Таблица лидеров:\n"
        )
        for i, p in enumerate(lb):
            text += f"{i+1}. {p['first_name']} — {fmt(p['score'])} очков\n"
        buttons = [
            [InlineKeyboardButton("🎮 Участвовать", callback_data=f"tournament_join_{t['id']}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="social_menu")]
        ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ===== ПРЕСТИЖ =====

async def prestige_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = db.get_user(user_id)
    if not u:
        return
    if u["level"] < PRESTIGE_MIN_LEVEL:
        return await update.message.reply_text(f"Нужен уровень {PRESTIGE_MIN_LEVEL}+. Текущий: {u['level']}")
    db.set_prestige(user_id)
    bonus = int((u["prestige"] + 1) * PRESTIGE_BONUS_PER_LEVEL * 100)
    await update.message.reply_text(
        f"⭐ *Престиж {u['prestige'] + 1}!*\n"
        f"Уровень сброшен, бонус к выигрышам: +{bonus}%",
        parse_mode="Markdown"
    )

# ===== ПРОМОКОДЫ =====

async def promo_enter(query, user_id):
    await query.edit_message_text("🎫 Отправьте промокод командой:\n/promo КОД", reply_markup=kb.back_kb())

async def promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Использование: /promo КОД")
    code = context.args[0].upper()
    reward, msg = db.use_promo(code, user_id)
    if reward is None:
        return await update.message.reply_text(f"❌ {msg}")
    await update.message.reply_text(f"✅ Промокод активирован!\n+{fmt(reward)} 💰")

# ===== ДРУЗЬЯ КОМАНДЫ =====

async def addfriend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Использование: /addfriend ID")
    try:
        friend_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Некорректный ID")
    if friend_id == user_id:
        return await update.message.reply_text("Нельзя добавить себя!")
    target = db.get_user(friend_id)
    if not target:
        return await update.message.reply_text("Пользователь не найден")
    if db.send_friend_request(user_id, friend_id):
        await update.message.reply_text("📨 Заявка отправлена!")
        try:
            await context.bot.send_message(friend_id, f"📨 Вам пришла заявка в друзья от {get_name(update.effective_user)}!\nИспользуйте меню для принятия.")
        except:
            pass
    else:
        await update.message.reply_text("Вы уже друзья или заявка уже отправлена")

# ===== ПОДАРКИ =====

async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text("Использование: /gift ID сумма")
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("Некорректные данные")
    if amount <= 0 or target_id == user_id:
        return await update.message.reply_text("Некорректные данные")
    if db.get_balance(user_id) < amount:
        return await update.message.reply_text("Недостаточно монет!")
    target = db.get_user(target_id)
    if not target:
        return await update.message.reply_text("Пользователь не найден")
    db.update_balance(user_id, -amount)
    db.update_balance(target_id, amount)
    await update.message.reply_text(f"🎁 Вы отправили {fmt(amount)} 💰 пользователю {target['first_name']}!")
    try:
        await context.bot.send_message(target_id, f"🎁 Вы получили {fmt(amount)} 💰 от {get_name(update.effective_user)}!")
    except:
        pass

# ===== КЛАН КОМАНДЫ =====

async def createclan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Использование: /createclan Название")
    name = " ".join(context.args)
    clan, _ = db.get_user_clan(user_id)
    if clan:
        return await update.message.reply_text("Вы уже в клане!")
    cost = 50000
    if db.get_balance(user_id) < cost:
        return await update.message.reply_text(f"Нужно: {fmt(cost)} 💰")
    db.update_balance(user_id, -cost)
    clan_id = db.create_clan(name, user_id)
    if clan_id:
        await update.message.reply_text(f"🏰 Клан *{name}* создан!", parse_mode="Markdown")
    else:
        db.update_balance(user_id, cost)
        await update.message.reply_text("Клан с таким именем уже существует")

async def joinclan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Использование: /joinclan ID_клана")
    try:
        clan_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Некорректный ID")
    existing, _ = db.get_user_clan(user_id)
    if existing:
        return await update.message.reply_text("Вы уже в клане!")
    clan = db.get_clan(clan_id)
    if not clan:
        return await update.message.reply_text("Клан не найден")
    db.join_clan(user_id, clan_id)
    await update.message.reply_text(f"✅ Вы вступили в клан *{clan['name']}*!", parse_mode="Markdown")

# ===== АДМИН =====

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("⚙️ *Админ-панель:*", parse_mode="Markdown", reply_markup=kb.admin_kb())

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) < 2:
        return await update.message.reply_text("/give ID сумма")
    try:
        uid, amount = int(context.args[0]), int(context.args[1])
    except ValueError:
        return await update.message.reply_text("Некорректные данные")
    db.ensure_user(uid)
    db.update_balance(uid, amount)
    await update.message.reply_text(f"✅ +{fmt(amount)} 💰 → {uid}")

async def take_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) < 2:
        return await update.message.reply_text("/take ID сумма")
    try:
        uid, amount = int(context.args[0]), int(context.args[1])
    except ValueError:
        return await update.message.reply_text("Некорректные данные")
    db.update_balance(uid, -amount)
    await update.message.reply_text(f"✅ -{fmt(amount)} 💰 ← {uid}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        return await update.message.reply_text("/broadcast текст")
    text = " ".join(context.args)
    users = db.get_all_users(10000)
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u["user_id"], f"📢 {text}")
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Отправлено: {sent}/{len(users)}")

async def createpromo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) < 3:
        return await update.message.reply_text("/createpromo КОД сумма макс_активаций")
    code = context.args[0].upper()
    try:
        reward, max_uses = int(context.args[1]), int(context.args[2])
    except ValueError:
        return await update.message.reply_text("Некорректные данные")
    if db.create_promo(code, reward, max_uses, update.effective_user.id):
        await update.message.reply_text(f"✅ Промокод {code} создан!\n{fmt(reward)} 💰, {max_uses} активаций")
    else:
        await update.message.reply_text("Промокод уже существует")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        return await update.message.reply_text("/ban ID")
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    db.ban_user(uid)
    await update.message.reply_text(f"🚫 Пользователь {uid} заблокирован")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        return await update.message.reply_text("/unban ID")
    try:
        uid = int(context.args[0])
    except ValueError:
        return
    db.unban_user(uid)
    await update.message.reply_text(f"✅ Пользователь {uid} разблокирован")

# ===== ГРУППЫ =====

async def group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    user = update.effective_user
    user_id = user.id
    db.ensure_user(user_id, user.username or "", get_name(user))

    if text.startswith("!б"):
        bal = db.get_balance(user_id)
        await update.message.reply_text(f"💰 {get_name(user)}: {fmt(bal)} монет")

    elif text.startswith("!т"):
        rows = db.get_top_balance(5)
        msg = "🏆 *Топ-5:*\n"
        for i, r in enumerate(rows):
            msg += f"{i+1}. {r['first_name']} — {fmt(r['balance'])} 💰\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text.lower().startswith("мины "):
        parts = text.split()
        if len(parts) >= 2:
            try:
                bet = int(parts[1])
                num_mines = int(parts[2]) if len(parts) > 2 else 3
                num_mines = max(1, min(5, num_mines))
            except ValueError:
                return
            if db.get_balance(user_id) < bet or bet < MIN_BET:
                return await update.message.reply_text("Недостаточно монет или ставка слишком мала!")
            db.update_balance(user_id, -bet)
            field, mines_pos = games.create_mines_field(num_mines)
            gid = next_game_id()
            active_games[gid] = {
                "type": "mines", "user_id": user_id, "bet": bet,
                "field": field, "mines_pos": mines_pos, "opened": [],
                "num_mines": num_mines
            }
            await update.message.reply_text(
                f"💣 *Мины* | {get_name(user)} | Ставка: {fmt(bet)} | Мин: {num_mines}",
                parse_mode="Markdown",
                reply_markup=kb.mines_field_kb(field, [], gid)
            )

    elif text.lower().startswith("башня "):
        parts = text.split()
        if len(parts) >= 2:
            try:
                bet = int(parts[1])
                height = int(parts[2]) if len(parts) > 2 else 5
                if height not in TOWER_HEIGHTS:
                    height = 5
            except ValueError:
                return
            if db.get_balance(user_id) < bet or bet < MIN_BET:
                return await update.message.reply_text("Недостаточно монет или ставка слишком мала!")
            db.update_balance(user_id, -bet)
            tower = games.create_tower(height)
            gid = next_game_id()
            active_games[gid] = {
                "type": "tower", "user_id": user_id, "bet": bet,
                "tower": tower, "height": height, "floor": 0
            }
            cells = tower[0]["cells"]
            await update.message.reply_text(
                f"🏗️ *Башня* | {get_name(user)} | Ставка: {fmt(bet)} | Этажей: {height}\nЭтаж 1/{height}:",
                parse_mode="Markdown",
                reply_markup=kb.tower_floor_kb(0, cells, gid)
            )

# ===== CALLBACK HANDLER =====

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if await check_ban(user_id):
        return await query.edit_message_text("🚫 Вы заблокированы.")

    db.ensure_user(user_id, query.from_user.username or "", get_name(query.from_user))

    # Navigation
    if data == "main_menu":
        await query.edit_message_text("📋 *Главное меню:*", parse_mode="Markdown", reply_markup=kb.main_menu_kb())
    elif data == "profile":
        await show_profile(query, user_id)
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "games_menu":
        await query.edit_message_text("🎮 *Игры:*", parse_mode="Markdown", reply_markup=kb.games_menu_kb())
    elif data == "bonus_menu":
        await query.edit_message_text("🎁 *Бонусы:*", parse_mode="Markdown", reply_markup=kb.bonus_menu_kb())
    elif data == "top_menu":
        await query.edit_message_text("🏆 *Топ:*", parse_mode="Markdown", reply_markup=kb.top_menu_kb())
    elif data == "social_menu":
        await query.edit_message_text("👥 *Социальное:*", parse_mode="Markdown", reply_markup=kb.social_menu_kb())
    elif data == "shop_menu":
        await query.edit_message_text("🏪 *Магазин:*", parse_mode="Markdown", reply_markup=kb.shop_menu_kb())
    elif data == "cases_menu":
        await query.edit_message_text("📦 *Кейсы:*", parse_mode="Markdown", reply_markup=kb.cases_menu_kb())
    elif data == "stats_menu":
        await show_stats(query, user_id)
    elif data == "achievements_menu":
        await show_achievements(query, user_id)

    # Daily / Wheel
    elif data == "daily_bonus":
        await daily_bonus(query, user_id)
    elif data == "wheel":
        await wheel_spin(query, user_id)

    # Tops
    elif data.startswith("top_"):
        await show_top(query, data[4:])

    # Games - entry
    elif data == "game_mines":
        await start_mines_bet(query, user_id)
    elif data == "game_tower":
        await start_tower_bet(query, user_id)
    elif data == "game_slots":
        await start_slots_bet(query, user_id)
    elif data == "game_coin":
        await start_coin_bet(query, user_id)
    elif data == "game_dice":
        await start_dice_bet(query, user_id)
    elif data == "game_bj":
        await start_bj_bet(query, user_id)
    elif data == "game_crash":
        await start_crash_bet(query, user_id)
    elif data == "game_roulette":
        await start_roulette_bet(query, user_id)
    elif data == "game_race":
        await start_race_bet(query, user_id)

    # Mines
    elif data.startswith("mines_bet_"):
        await mines_set_bet(query, user_id, int(data.split("_")[2]))
    elif data.startswith("mines_start_"):
        parts = data.split("_")
        await mines_start(query, user_id, int(parts[2]), int(parts[3]))
    elif data.startswith("mines_open_"):
        parts = data.split("_")
        await mines_open(query, user_id, int(parts[2]), int(parts[3]))
    elif data.startswith("mines_cashout_"):
        await mines_cashout(query, user_id, int(data.split("_")[2]))

    # Tower
    elif data.startswith("tower_bet_"):
        await tower_set_bet(query, user_id, int(data.split("_")[2]))
    elif data.startswith("tower_start_"):
        parts = data.split("_")
        await tower_start(query, user_id, int(parts[2]), int(parts[3]))
    elif data.startswith("tower_pick_"):
        parts = data.split("_")
        await tower_pick(query, user_id, int(parts[2]), int(parts[3]), int(parts[4]))
    elif data.startswith("tower_cashout_"):
        await tower_cashout(query, user_id, int(data.split("_")[2]))

    # Slots
    elif data.startswith("slots_bet_"):
        await slots_play(query, user_id, int(data.split("_")[2]))

    # Coin
    elif data.startswith("coin_bet_"):
        await coin_set_bet(query, user_id, int(data.split("_")[2]))
    elif data.startswith("coin_pick_"):
        parts = data.split("_")
        await coin_play(query, user_id, int(parts[2]), parts[3])

    # Dice
    elif data.startswith("dice_bet_"):
        await dice_play(query, user_id, int(data.split("_")[2]))

    # Blackjack
    elif data.startswith("bj_bet_"):
        await bj_start(query, user_id, int(data.split("_")[2]))
    elif data.startswith("bj_hit_"):
        await bj_hit(query, user_id, int(data.split("_")[2]))
    elif data.startswith("bj_stand_"):
        await bj_finish(query, user_id, int(data.split("_")[2]))

    # Crash
    elif data.startswith("crash_bet_"):
        await crash_start(query, user_id, int(data.split("_")[2]))
    elif data.startswith("crash_cashout_"):
        await crash_cashout(query, user_id, int(data.split("_")[2]))

    # Roulette
    elif data.startswith("roulette_bet_"):
        await roulette_play(query, user_id, int(data.split("_")[2]))

    # Race
    elif data.startswith("race_bet_"):
        await race_set_bet(query, user_id, int(data.split("_")[2]))
    elif data.startswith("race_pick_"):
        parts = data.split("_")
        await race_play(query, user_id, int(parts[2]), int(parts[3]))

    # Shop
    elif data.startswith("buy_"):
        await buy_item(query, user_id, data[4:])
    elif data == "inventory":
        await show_inventory(query, user_id)

    # Cases
    elif data.startswith("case_"):
        await open_case(query, user_id, data[5:])

    # Business
    elif data == "business_menu":
        await show_business_menu(query, user_id)
    elif data.startswith("buybiz_"):
        await buy_business(query, user_id, data[7:])
    elif data.startswith("biz_collect_"):
        await collect_business_income(query, user_id, data[12:])
    elif data.startswith("biz_upgrade_"):
        await upgrade_business_handler(query, user_id, data[12:])
    elif data.startswith("biz_"):
        await manage_business(query, user_id, data[4:])

    # Social
    elif data == "friends_list":
        await friends_list(query, user_id)
    elif data == "friend_requests":
        await friend_requests_list(query, user_id)
    elif data.startswith("friend_accept_"):
        from_id = int(data.split("_")[2])
        db.accept_friend(from_id, user_id)
        await query.answer("✅ Друг добавлен!", show_alert=True)
        await friend_requests_list(query, user_id)
    elif data == "clan_menu":
        await clan_menu(query, user_id)
    elif data == "clan_leave":
        db.leave_clan(user_id)
        await query.answer("Вы покинули клан", show_alert=True)
        await clan_menu(query, user_id)
    elif data == "duels_menu":
        await duels_menu(query, user_id)
    elif data == "tournament_menu":
        await tournament_menu(query, user_id)
    elif data.startswith("tournament_join_"):
        t_id = int(data.split("_")[2])
        t = db.get_active_tournament()
        if t and t["entry_fee"] > 0:
            if db.get_balance(user_id) < t["entry_fee"]:
                return await query.answer("Недостаточно монет!", show_alert=True)
            db.update_balance(user_id, -t["entry_fee"])
        db.join_tournament(t_id, user_id)
        await query.answer("✅ Вы участвуете!", show_alert=True)
        await tournament_menu(query, user_id)
    elif data == "market_menu":
        await market_menu(query, user_id)
    elif data.startswith("market_buy_"):
        listing_id = int(data.split("_")[2])
        listing = db.buy_from_market(listing_id, user_id)
        if listing:
            await query.answer("✅ Куплено!", show_alert=True)
        else:
            await query.answer("Не удалось купить", show_alert=True)
        await market_menu(query, user_id)
    elif data == "invest_menu":
        await invest_menu(query, user_id)
    elif data.startswith("invest_new_"):
        parts = data.split("_")
        hours, rate = int(parts[2]), int(parts[3]) / 100
        amounts = [1000, 5000, 10000, 50000]
        buttons = []
        for a in amounts:
            buttons.append([InlineKeyboardButton(f"{fmt(a)} 💰", callback_data=f"invest_confirm_{hours}_{int(rate*100)}_{a}")])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="invest_menu")])
        await query.edit_message_text(f"💼 Вклад на {hours}ч ({int(rate*100)}%)\nВыберите сумму:",
                                       reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("invest_confirm_"):
        parts = data.split("_")
        hours, rate, amount = int(parts[2]), int(parts[3]) / 100, int(parts[4])
        if db.get_balance(user_id) < amount:
            return await query.answer("Недостаточно монет!", show_alert=True)
        db.update_balance(user_id, -amount)
        db.create_investment(user_id, amount, rate, hours)
        await query.answer(f"✅ Вложено {fmt(amount)} 💰", show_alert=True)
        await invest_menu(query, user_id)
    elif data.startswith("invest_collect_"):
        inv_id = int(data.split("_")[2])
        result = db.collect_investment(inv_id, user_id)
        if result == 0:
            await query.answer("Не найдено", show_alert=True)
        elif result == -1:
            await query.answer("Ещё не созрел!", show_alert=True)
        else:
            await query.answer(f"💰 +{fmt(result)} 💰", show_alert=True)
        await invest_menu(query, user_id)

    # Lottery
    elif data == "lottery_menu":
        await lottery_menu(query, user_id)
    elif data == "lottery_buy":
        await lottery_buy(query, user_id)

    # Challenges
    elif data == "challenges_menu":
        await challenges_menu(query, user_id)

    # Promo
    elif data == "promo_enter":
        await promo_enter(query, user_id)

    # Duel create
    elif data == "duel_create":
        presets = [500, 1000, 5000, 10000]
        buttons = [[InlineKeyboardButton(fmt(p), callback_data=f"duel_new_{p}") for p in presets]]
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="duels_menu")])
        await query.edit_message_text("⚔️ Выберите ставку для дуэли:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("duel_new_"):
        bet = int(data.split("_")[2])
        if db.get_balance(user_id) < bet:
            return await query.answer("Недостаточно монет!", show_alert=True)
        db.update_balance(user_id, -bet)
        duel_id = db.create_duel(user_id, bet)
        await query.edit_message_text(f"⚔️ Дуэль #{duel_id} создана!\nСтавка: {fmt(bet)} 💰\nОжидание соперника...",
                                       reply_markup=kb.back_kb("duels_menu"))
    elif data.startswith("duel_accept_"):
        duel_id = int(data.split("_")[2])
        conn = db.get_db()
        duel = conn.execute("SELECT * FROM duels WHERE id=? AND status='pending'", (duel_id,)).fetchone()
        conn.close()
        if not duel:
            return await query.answer("Дуэль не найдена", show_alert=True)
        if duel["challenger_id"] == user_id:
            return await query.answer("Нельзя принять свою дуэль!", show_alert=True)
        bet = duel["bet"]
        if db.get_balance(user_id) < bet:
            return await query.answer("Недостаточно монет!", show_alert=True)
        db.update_balance(user_id, -bet)
        db.accept_duel(duel_id, user_id)
        # Resolve
        winner = random.choice([duel["challenger_id"], user_id])
        loser = user_id if winner == duel["challenger_id"] else duel["challenger_id"]
        winnings = bet * 2
        db.update_balance(winner, winnings)
        db.finish_duel(duel_id, winner)
        db.update_rating(winner, 25)
        db.update_rating(loser, -15)
        winner_name = db.get_user(winner)["first_name"]
        await query.edit_message_text(
            f"⚔️ *Дуэль #{duel_id}*\n\n🏆 Победитель: {winner_name}\n💰 Приз: {fmt(winnings)} 💰",
            parse_mode="Markdown", reply_markup=kb.back_kb("duels_menu")
        )

    # Admin
    elif data == "admin_stats":
        if user_id not in ADMIN_IDS:
            return
        stats = db.get_stats()
        await query.edit_message_text(
            f"📊 *Статистика бота:*\n\n"
            f"👥 Пользователей: {fmt(stats['total_users'])}\n"
            f"🎮 Всего игр: {fmt(stats['total_games'])}\n"
            f"💰 Общий баланс: {fmt(stats['total_balance'])}",
            parse_mode="Markdown", reply_markup=kb.back_kb("main_menu")
        )
    elif data == "admin_users":
        if user_id not in ADMIN_IDS:
            return
        users = db.get_all_users(20)
        text = "👥 *Пользователи:*\n\n"
        for u in users:
            text += f"• {u['first_name']} (ID:{u['user_id']}) — {fmt(u['balance'])} 💰\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb.back_kb("main_menu"))
    elif data == "admin_give10k":
        if user_id not in ADMIN_IDS:
            return
        db.update_balance(user_id, 10000)
        await query.answer(f"✅ +10.000 💰", show_alert=True)
    elif data == "admin_take5k":
        if user_id not in ADMIN_IDS:
            return
        db.update_balance(user_id, -5000)
        await query.answer(f"✅ -5.000 💰", show_alert=True)

    elif data == "noop":
        pass


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("give", give_cmd))
    app.add_handler(CommandHandler("take", take_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("createpromo", createpromo_cmd))
    app.add_handler(CommandHandler("promo", promo_cmd))
    app.add_handler(CommandHandler("prestige", prestige_cmd))
    app.add_handler(CommandHandler("addfriend", addfriend_cmd))
    app.add_handler(CommandHandler("gift", gift_cmd))
    app.add_handler(CommandHandler("createclan", createclan_cmd))
    app.add_handler(CommandHandler("joinclan", joinclan_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Group messages
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, group_message))

    print("🎰 Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
