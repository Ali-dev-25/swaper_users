import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "swapper.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                sub_end_date TIMESTAMP,
                swap_balance INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def check_subscription(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT sub_end_date, swap_balance FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            sub_end, balance = row
            if sub_end and datetime.fromisoformat(sub_end) > datetime.now():
                return True
            return balance > 0

async def add_subscription(user_id: int, days: int = 30):
    end_date = datetime.now() + timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, sub_end_date) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET sub_end_date = ?
        """, (user_id, end_date.isoformat(), end_date.isoformat()))
        await db.commit()