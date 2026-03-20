import sqlite3
import time
import json
from config import START_BALANCE, ACHIEVEMENTS

DB_FILE = "casino.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        balance INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        total_games INTEGER DEFAULT 0,
        total_wins INTEGER DEFAULT 0,
        total_wagered INTEGER DEFAULT 0,
        total_won INTEGER DEFAULT 0,
        win_streak INTEGER DEFAULT 0,
        max_win_streak INTEGER DEFAULT 0,
        last_daily REAL DEFAULT 0,
        last_wheel REAL DEFAULT 0,
        vip_until REAL DEFAULT 0,
        title TEXT DEFAULT '',
        avatar TEXT DEFAULT '',
        prestige INTEGER DEFAULT 0,
        rating_points INTEGER DEFAULT 0,
        created_at REAL DEFAULT 0,
        banned INTEGER DEFAULT 0,
        muted_until REAL DEFAULT 0,
        games_played_types TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_id TEXT,
        quantity INTEGER DEFAULT 1,
        purchased_at REAL DEFAULT 0,
        expires_at REAL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id TEXT,
        unlocked_at REAL DEFAULT 0,
        PRIMARY KEY (user_id, achievement_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS businesses (
        user_id INTEGER,
        business_id TEXT,
        level INTEGER DEFAULT 1,
        last_collect REAL DEFAULT 0,
        purchased_at REAL DEFAULT 0,
        PRIMARY KEY (user_id, business_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS game_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game_type TEXT,
        bet INTEGER,
        result TEXT,
        profit INTEGER,
        multiplier REAL DEFAULT 0,
        played_at REAL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER,
        friend_id INTEGER,
        added_at REAL DEFAULT 0,
        PRIMARY KEY (user_id, friend_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS friend_requests (
        from_id INTEGER,
        to_id INTEGER,
        sent_at REAL DEFAULT 0,
        PRIMARY KEY (from_id, to_id)
    );

    CREATE TABLE IF NOT EXISTS clans (
        clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        leader_id INTEGER,
        description TEXT DEFAULT '',
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0,
        created_at REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS clan_members (
        user_id INTEGER PRIMARY KEY,
        clan_id INTEGER,
        role TEXT DEFAULT 'member',
        joined_at REAL DEFAULT 0,
        FOREIGN KEY (clan_id) REFERENCES clans(clan_id)
    );

    CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        reward INTEGER DEFAULT 0,
        max_uses INTEGER DEFAULT 1,
        uses INTEGER DEFAULT 0,
        created_by INTEGER DEFAULT 0,
        expires_at REAL DEFAULT 0,
        created_at REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS promo_uses (
        code TEXT,
        user_id INTEGER,
        used_at REAL DEFAULT 0,
        PRIMARY KEY (code, user_id)
    );

    CREATE TABLE IF NOT EXISTS lottery_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        draw_date TEXT,
        purchased_at REAL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS lottery_draws (
        draw_date TEXT PRIMARY KEY,
        winner_id INTEGER DEFAULT 0,
        prize INTEGER DEFAULT 0,
        total_tickets INTEGER DEFAULT 0,
        drawn_at REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS duels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenger_id INTEGER,
        opponent_id INTEGER,
        bet INTEGER,
        winner_id INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT 0,
        finished_at REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        game_type TEXT,
        target INTEGER,
        reward INTEGER,
        starts_at REAL DEFAULT 0,
        ends_at REAL DEFAULT 0,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS challenge_progress (
        user_id INTEGER,
        challenge_id INTEGER,
        progress INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, challenge_id)
    );

    CREATE TABLE IF NOT EXISTS market_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        item_id TEXT,
        price INTEGER,
        listed_at REAL DEFAULT 0,
        sold INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        rate REAL,
        invested_at REAL DEFAULT 0,
        matures_at REAL DEFAULT 0,
        collected INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        game_type TEXT,
        entry_fee INTEGER DEFAULT 0,
        prize_pool INTEGER DEFAULT 0,
        status TEXT DEFAULT 'registration',
        starts_at REAL DEFAULT 0,
        ends_at REAL DEFAULT 0,
        created_at REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS tournament_participants (
        tournament_id INTEGER,
        user_id INTEGER,
        score INTEGER DEFAULT 0,
        PRIMARY KEY (tournament_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS crafting_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_item TEXT,
        ingredients TEXT,
        cost INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()


# ===== ПОЛЬЗОВАТЕЛИ =====

def get_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def create_user(user_id, username="", first_name=""):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, balance, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, first_name, START_BALANCE, time.time())
    )
    conn.commit()
    conn.close()


def ensure_user(user_id, username="", first_name=""):
    user = get_user(user_id)
    if not user:
        create_user(user_id, username, first_name)
        return get_user(user_id)
    # Update name
    conn = get_db()
    conn.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (username, first_name, user_id))
    conn.commit()
    conn.close()
    return get_user(user_id)


def update_balance(user_id, amount):
    conn = get_db()
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def set_balance(user_id, amount):
    conn = get_db()
    conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def get_balance(user_id):
    user = get_user(user_id)
    return user["balance"] if user else 0


def add_xp(user_id, amount):
    from config import LEVEL_BASE_XP, LEVEL_XP_MULTIPLIER
    conn = get_db()
    user = conn.execute("SELECT level, xp FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False, 0

    # Check for XP boost
    now = time.time()
    boost = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id='xp_boost' AND expires_at > ?",
        (user_id, now)
    ).fetchone()
    if boost:
        amount *= 2

    new_xp = user["xp"] + amount
    level = user["level"]
    leveled_up = False
    while True:
        needed = int(LEVEL_BASE_XP * (LEVEL_XP_MULTIPLIER ** (level - 1)))
        if new_xp >= needed:
            new_xp -= needed
            level += 1
            leveled_up = True
        else:
            break
    conn.execute("UPDATE users SET xp=?, level=? WHERE user_id=?", (new_xp, level, user_id))
    conn.commit()
    conn.close()
    return leveled_up, level


def record_game(user_id, game_type, bet, won, profit, multiplier=0):
    conn = get_db()
    result = "win" if won else "loss"
    conn.execute(
        "INSERT INTO game_history (user_id, game_type, bet, result, profit, multiplier, played_at) VALUES (?,?,?,?,?,?,?)",
        (user_id, game_type, bet, result, profit, multiplier, time.time())
    )
    if won:
        conn.execute(
            "UPDATE users SET total_games=total_games+1, total_wins=total_wins+1, total_wagered=total_wagered+?, total_won=total_won+?, win_streak=win_streak+1 WHERE user_id=?",
            (bet, profit, user_id)
        )
        conn.execute(
            "UPDATE users SET max_win_streak = MAX(max_win_streak, win_streak) WHERE user_id=?",
            (user_id,)
        )
    else:
        conn.execute(
            "UPDATE users SET total_games=total_games+1, total_wagered=total_wagered+?, win_streak=0 WHERE user_id=?",
            (bet, user_id)
        )

    # Update games_played_types
    user = conn.execute("SELECT games_played_types FROM users WHERE user_id=?", (user_id,)).fetchone()
    types = json.loads(user["games_played_types"]) if user else {}
    types[game_type] = types.get(game_type, 0) + 1
    conn.execute("UPDATE users SET games_played_types=? WHERE user_id=?", (json.dumps(types), user_id))

    conn.commit()
    conn.close()


def update_daily(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET last_daily=? WHERE user_id=?", (time.time(), user_id))
    conn.commit()
    conn.close()


def update_wheel(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET last_wheel=? WHERE user_id=?", (time.time(), user_id))
    conn.commit()
    conn.close()


# ===== ТОПЫ =====

def get_top_balance(limit=100):
    conn = get_db()
    rows = conn.execute("SELECT * FROM users WHERE banned=0 ORDER BY balance DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_top_games(limit=100):
    conn = get_db()
    rows = conn.execute("SELECT * FROM users WHERE banned=0 ORDER BY total_games DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_top_level(limit=100):
    conn = get_db()
    rows = conn.execute("SELECT * FROM users WHERE banned=0 ORDER BY level DESC, xp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


# ===== ДОСТИЖЕНИЯ =====

def get_user_achievements(user_id):
    conn = get_db()
    rows = conn.execute("SELECT achievement_id FROM achievements WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r["achievement_id"] for r in rows]


def unlock_achievement(user_id, achievement_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM achievements WHERE user_id=? AND achievement_id=?", (user_id, achievement_id)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT INTO achievements (user_id, achievement_id, unlocked_at) VALUES (?,?,?)",
                 (user_id, achievement_id, time.time()))
    reward = ACHIEVEMENTS.get(achievement_id, {}).get("reward", 0)
    if reward:
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (reward, user_id))
    conn.commit()
    conn.close()
    return True


def check_achievements(user_id):
    user = get_user(user_id)
    if not user:
        return []
    unlocked = get_user_achievements(user_id)
    new_achievements = []

    checks = {
        "first_win": user["total_wins"] >= 1,
        "games_10": user["total_games"] >= 10,
        "games_100": user["total_games"] >= 100,
        "games_1000": user["total_games"] >= 1000,
        "win_streak_5": user["max_win_streak"] >= 5,
        "win_streak_10": user["max_win_streak"] >= 10,
        "millionaire": user["balance"] >= 1_000_000,
        "level_10": user["level"] >= 10,
        "level_50": user["level"] >= 50,
    }

    types = json.loads(user["games_played_types"])
    all_game_types = {"mines", "tower", "slots", "coinflip", "dice", "blackjack", "crash", "roulette", "race"}
    if all_game_types.issubset(set(types.keys())):
        checks["all_games"] = True

    for ach_id, condition in checks.items():
        if condition and ach_id not in unlocked:
            if unlock_achievement(user_id, ach_id):
                new_achievements.append(ach_id)

    return new_achievements


# ===== ИНВЕНТАРЬ =====

def add_item(user_id, item_id, expires_at=0):
    conn = get_db()
    existing = conn.execute("SELECT * FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
    if existing and expires_at == 0:
        conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (existing["id"],))
    else:
        conn.execute("INSERT INTO inventory (user_id, item_id, quantity, purchased_at, expires_at) VALUES (?,?,1,?,?)",
                     (user_id, item_id, time.time(), expires_at))
    conn.commit()
    conn.close()


def get_inventory(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM inventory WHERE user_id=? AND (expires_at=0 OR expires_at>?)",
                        (user_id, time.time())).fetchall()
    conn.close()
    return rows


def has_item(user_id, item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=? AND quantity>0 AND (expires_at=0 OR expires_at>?)",
        (user_id, item_id, time.time())
    ).fetchone()
    conn.close()
    return row is not None


def use_item(user_id, item_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=? AND quantity>0 AND (expires_at=0 OR expires_at>?) ORDER BY expires_at ASC LIMIT 1",
        (user_id, item_id, time.time())
    ).fetchone()
    if not row:
        conn.close()
        return False
    if row["quantity"] > 1:
        conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))
    else:
        conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()
    return True


# ===== БИЗНЕСЫ =====

def get_user_businesses(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return rows


def buy_business(user_id, business_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO businesses (user_id, business_id, level, last_collect, purchased_at) VALUES (?,?,1,?,?)",
                 (user_id, business_id, time.time(), time.time()))
    conn.commit()
    conn.close()


def upgrade_business(user_id, business_id):
    conn = get_db()
    conn.execute("UPDATE businesses SET level=level+1 WHERE user_id=? AND business_id=?", (user_id, business_id))
    conn.commit()
    conn.close()


def collect_business(user_id, business_id):
    conn = get_db()
    conn.execute("UPDATE businesses SET last_collect=? WHERE user_id=? AND business_id=?",
                 (time.time(), user_id, business_id))
    conn.commit()
    conn.close()


# ===== ДРУЗЬЯ =====

def send_friend_request(from_id, to_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM friends WHERE user_id=? AND friend_id=?", (from_id, to_id)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT OR IGNORE INTO friend_requests (from_id, to_id, sent_at) VALUES (?,?,?)",
                 (from_id, to_id, time.time()))
    conn.commit()
    conn.close()
    return True


def accept_friend(from_id, to_id):
    conn = get_db()
    conn.execute("DELETE FROM friend_requests WHERE from_id=? AND to_id=?", (from_id, to_id))
    conn.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, added_at) VALUES (?,?,?)", (from_id, to_id, time.time()))
    conn.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, added_at) VALUES (?,?,?)", (to_id, from_id, time.time()))
    conn.commit()
    conn.close()


def get_friends(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT u.* FROM friends f JOIN users u ON f.friend_id=u.user_id WHERE f.user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_friend_requests(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT u.* FROM friend_requests fr JOIN users u ON fr.from_id=u.user_id WHERE fr.to_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


# ===== КЛАНЫ =====

def create_clan(name, leader_id, description=""):
    conn = get_db()
    try:
        c = conn.execute("INSERT INTO clans (name, leader_id, description, created_at) VALUES (?,?,?,?)",
                         (name, leader_id, description, time.time()))
        clan_id = c.lastrowid
        conn.execute("INSERT INTO clan_members (user_id, clan_id, role, joined_at) VALUES (?,?,'leader',?)",
                     (leader_id, clan_id, time.time()))
        conn.commit()
        conn.close()
        return clan_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_clan(clan_id):
    conn = get_db()
    clan = conn.execute("SELECT * FROM clans WHERE clan_id=?", (clan_id,)).fetchone()
    conn.close()
    return clan


def get_user_clan(user_id):
    conn = get_db()
    member = conn.execute("SELECT * FROM clan_members WHERE user_id=?", (user_id,)).fetchone()
    if not member:
        conn.close()
        return None, None
    clan = conn.execute("SELECT * FROM clans WHERE clan_id=?", (member["clan_id"],)).fetchone()
    conn.close()
    return clan, member


def join_clan(user_id, clan_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO clan_members (user_id, clan_id, role, joined_at) VALUES (?,?,'member',?)",
                 (user_id, clan_id, time.time()))
    conn.commit()
    conn.close()


def leave_clan(user_id):
    conn = get_db()
    conn.execute("DELETE FROM clan_members WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_clan_members(clan_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT u.*, cm.role FROM clan_members cm JOIN users u ON cm.user_id=u.user_id WHERE cm.clan_id=?",
        (clan_id,)
    ).fetchall()
    conn.close()
    return rows


# ===== ПРОМОКОДЫ =====

def create_promo(code, reward, max_uses, created_by, expires_at=0):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO promocodes (code, reward, max_uses, uses, created_by, expires_at, created_at) VALUES (?,?,?,0,?,?,?)",
            (code, reward, max_uses, created_by, expires_at, time.time())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def use_promo(code, user_id):
    conn = get_db()
    promo = conn.execute("SELECT * FROM promocodes WHERE code=?", (code,)).fetchone()
    if not promo:
        conn.close()
        return None, "Промокод не найден"
    if promo["expires_at"] > 0 and time.time() > promo["expires_at"]:
        conn.close()
        return None, "Промокод истёк"
    if promo["uses"] >= promo["max_uses"]:
        conn.close()
        return None, "Промокод исчерпан"
    used = conn.execute("SELECT * FROM promo_uses WHERE code=? AND user_id=?", (code, user_id)).fetchone()
    if used:
        conn.close()
        return None, "Вы уже использовали этот промокод"
    conn.execute("UPDATE promocodes SET uses=uses+1 WHERE code=?", (code,))
    conn.execute("INSERT INTO promo_uses (code, user_id, used_at) VALUES (?,?,?)", (code, user_id, time.time()))
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (promo["reward"], user_id))
    conn.commit()
    reward = promo["reward"]
    conn.close()
    return reward, "OK"


# ===== ЛОТЕРЕЯ =====

def buy_lottery_ticket(user_id, draw_date):
    conn = get_db()
    conn.execute("INSERT INTO lottery_tickets (user_id, draw_date, purchased_at) VALUES (?,?,?)",
                 (user_id, draw_date, time.time()))
    conn.commit()
    conn.close()


def get_lottery_tickets(draw_date):
    conn = get_db()
    rows = conn.execute("SELECT * FROM lottery_tickets WHERE draw_date=?", (draw_date,)).fetchall()
    conn.close()
    return rows


def get_user_lottery_tickets(user_id, draw_date):
    conn = get_db()
    rows = conn.execute("SELECT * FROM lottery_tickets WHERE user_id=? AND draw_date=?", (user_id, draw_date)).fetchall()
    conn.close()
    return rows


# ===== ДУЭЛИ =====

def create_duel(challenger_id, bet):
    conn = get_db()
    c = conn.execute("INSERT INTO duels (challenger_id, bet, status, created_at) VALUES (?,?,'pending',?)",
                     (challenger_id, bet, time.time()))
    duel_id = c.lastrowid
    conn.commit()
    conn.close()
    return duel_id


def accept_duel(duel_id, opponent_id):
    conn = get_db()
    conn.execute("UPDATE duels SET opponent_id=?, status='active' WHERE id=? AND status='pending'",
                 (opponent_id, duel_id))
    conn.commit()
    conn.close()


def finish_duel(duel_id, winner_id):
    conn = get_db()
    conn.execute("UPDATE duels SET winner_id=?, status='finished', finished_at=? WHERE id=?",
                 (winner_id, time.time(), duel_id))
    conn.commit()
    conn.close()


def get_pending_duels():
    conn = get_db()
    rows = conn.execute("SELECT * FROM duels WHERE status='pending'").fetchall()
    conn.close()
    return rows


# ===== ИНВЕСТИЦИИ =====

def create_investment(user_id, amount, rate, duration_hours):
    conn = get_db()
    now = time.time()
    conn.execute(
        "INSERT INTO investments (user_id, amount, rate, invested_at, matures_at) VALUES (?,?,?,?,?)",
        (user_id, amount, rate, now, now + duration_hours * 3600)
    )
    conn.commit()
    conn.close()


def get_investments(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM investments WHERE user_id=? AND collected=0", (user_id,)).fetchall()
    conn.close()
    return rows


def collect_investment(inv_id, user_id):
    conn = get_db()
    inv = conn.execute("SELECT * FROM investments WHERE id=? AND user_id=? AND collected=0", (inv_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return 0
    if time.time() < inv["matures_at"]:
        conn.close()
        return -1
    payout = int(inv["amount"] * (1 + inv["rate"]))
    conn.execute("UPDATE investments SET collected=1 WHERE id=?", (inv_id,))
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (payout, user_id))
    conn.commit()
    conn.close()
    return payout


# ===== ТУРНИРЫ =====

def get_active_tournament():
    conn = get_db()
    t = conn.execute("SELECT * FROM tournaments WHERE status IN ('registration','active') ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return t


def join_tournament(tournament_id, user_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO tournament_participants (tournament_id, user_id, score) VALUES (?,?,0)",
                 (tournament_id, user_id))
    conn.commit()
    conn.close()


def update_tournament_score(tournament_id, user_id, score_add):
    conn = get_db()
    conn.execute("UPDATE tournament_participants SET score=score+? WHERE tournament_id=? AND user_id=?",
                 (score_add, tournament_id, user_id))
    conn.commit()
    conn.close()


def get_tournament_leaderboard(tournament_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        "SELECT tp.*, u.first_name, u.username FROM tournament_participants tp JOIN users u ON tp.user_id=u.user_id WHERE tp.tournament_id=? ORDER BY tp.score DESC LIMIT ?",
        (tournament_id, limit)
    ).fetchall()
    conn.close()
    return rows


# ===== ЧЕЛЛЕНДЖИ =====

def get_active_challenges():
    conn = get_db()
    now = time.time()
    rows = conn.execute("SELECT * FROM challenges WHERE active=1 AND starts_at<=? AND ends_at>=?", (now, now)).fetchall()
    conn.close()
    return rows


def update_challenge_progress(user_id, game_type):
    conn = get_db()
    challenges = get_active_challenges()
    completed = []
    for ch in challenges:
        if ch["game_type"] != game_type and ch["game_type"] != "any":
            continue
        prog = conn.execute("SELECT * FROM challenge_progress WHERE user_id=? AND challenge_id=?",
                            (user_id, ch["id"])).fetchone()
        if prog and prog["completed"]:
            continue
        if not prog:
            conn.execute("INSERT INTO challenge_progress (user_id, challenge_id, progress, completed) VALUES (?,?,1,0)",
                         (user_id, ch["id"]))
        else:
            conn.execute("UPDATE challenge_progress SET progress=progress+1 WHERE user_id=? AND challenge_id=?",
                         (user_id, ch["id"]))
        prog = conn.execute("SELECT * FROM challenge_progress WHERE user_id=? AND challenge_id=?",
                            (user_id, ch["id"])).fetchone()
        if prog["progress"] >= ch["target"]:
            conn.execute("UPDATE challenge_progress SET completed=1 WHERE user_id=? AND challenge_id=?",
                         (user_id, ch["id"]))
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (ch["reward"], user_id))
            completed.append(ch)
    conn.commit()
    conn.close()
    return completed


# ===== РЫНОК =====

def list_on_market(seller_id, item_id, price):
    conn = get_db()
    conn.execute("INSERT INTO market_listings (seller_id, item_id, price, listed_at) VALUES (?,?,?,?)",
                 (seller_id, item_id, price, time.time()))
    conn.commit()
    conn.close()


def get_market_listings():
    conn = get_db()
    rows = conn.execute("SELECT ml.*, u.first_name FROM market_listings ml JOIN users u ON ml.seller_id=u.user_id WHERE ml.sold=0 ORDER BY ml.listed_at DESC LIMIT 50").fetchall()
    conn.close()
    return rows


def buy_from_market(listing_id, buyer_id):
    conn = get_db()
    listing = conn.execute("SELECT * FROM market_listings WHERE id=? AND sold=0", (listing_id,)).fetchone()
    if not listing:
        conn.close()
        return None
    conn.execute("UPDATE market_listings SET sold=1 WHERE id=?", (listing_id,))
    conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (listing["price"], buyer_id))
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (listing["price"], listing["seller_id"]))
    add_item(buyer_id, listing["item_id"])
    conn.commit()
    conn.close()
    return listing


# ===== АДМИН =====

def get_all_users(limit=50):
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY balance DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_stats():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    total_games = conn.execute("SELECT SUM(total_games) as c FROM users").fetchone()["c"] or 0
    total_balance = conn.execute("SELECT SUM(balance) as c FROM users").fetchone()["c"] or 0
    conn.close()
    return {"total_users": total_users, "total_games": total_games, "total_balance": total_balance}


def ban_user(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def mute_user(user_id, until):
    conn = get_db()
    conn.execute("UPDATE users SET muted_until=? WHERE user_id=?", (until, user_id))
    conn.commit()
    conn.close()


def set_prestige(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET prestige=prestige+1, level=1, xp=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_rank(rating_points):
    from config import RANKS
    rank_name = RANKS[0][1]
    for threshold, name in RANKS:
        if rating_points >= threshold:
            rank_name = name
    return rank_name


def update_rating(user_id, points):
    conn = get_db()
    conn.execute("UPDATE users SET rating_points=MAX(0, rating_points+?) WHERE user_id=?", (points, user_id))
    conn.commit()
    conn.close()
