import aiosqlite
from typing import Optional, List, Tuple
import time

DB_PATH = "slot.db"


async def init_db(db_path: str = DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                display_name TEXT,
                balance INTEGER NOT NULL,
                last_bonus_ts INTEGER NOT NULL DEFAULT 0,
                total_bet INTEGER NOT NULL DEFAULT 0,
                total_win INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.commit()


async def get_user(user_id: int, default_balance: int, display_name: Optional[str] = None, db_path: str = DB_PATH) -> dict:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return dict(row)
        # create
        await db.execute(
            "INSERT INTO users (user_id, display_name, balance) VALUES (?, ?, ?)",
            (user_id, display_name or "Player", default_balance),
        )
        await db.commit()
        return {
            "user_id": user_id,
            "display_name": display_name or "Player",
            "balance": default_balance,
            "last_bonus_ts": 0,
            "total_bet": 0,
            "total_win": 0,
        }


async def set_display_name(user_id: int, display_name: str, db_path: str = DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (display_name, user_id))
        await db.commit()


async def get_balance(user_id: int, default_balance: int, db_path: str = DB_PATH) -> int:
    user = await get_user(user_id, default_balance, db_path=db_path)
    return user["balance"]


async def update_balance(user_id: int, new_balance: int, db_path: str = DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        await db.commit()


async def record_spin(user_id: int, bet: int, win: int, db_path: str = DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE users SET total_bet = total_bet + ?, total_win = total_win + ? WHERE user_id = ?",
            (bet, win, user_id),
        )
        await db.commit()


async def can_claim_bonus(user_id: int, now_ts: Optional[int], cooldown_seconds: int, default_balance: int, db_path: str = DB_PATH) -> Tuple[bool, int]:
    user = await get_user(user_id, default_balance, db_path=db_path)
    last = user.get("last_bonus_ts", 0)
    now = now_ts or int(time.time())
    remaining = max(0, last + cooldown_seconds - now)
    return (remaining == 0), remaining


async def claim_bonus(user_id: int, amount: int, default_balance: int, db_path: str = DB_PATH) -> None:
    async with aiosqlite.connect(db_path) as db:
        # upsert if missing is handled by get_user before calling this
        user = await get_user(user_id, default_balance, db_path=db_path)
        new_balance = user["balance"] + amount
        now = int(time.time())
        await db.execute(
            "UPDATE users SET balance = ?, last_bonus_ts = ? WHERE user_id = ?",
            (new_balance, now, user_id),
        )
        await db.commit()


async def top_balances(limit: int = 10, db_path: str = DB_PATH) -> List[Tuple[str, int]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT display_name, balance FROM users ORDER BY balance DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [(r["display_name"] or "Player", r["balance"]) for r in rows]
