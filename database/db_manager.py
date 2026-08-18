import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "swapper.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'user',
                sub_start_date TIMESTAMP,
                sub_end_date TIMESTAMP,
                swap_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def check_subscription(user_id: int) -> dict:
    """
    فحص منطقي دقيق لحالة الاشتراك:
    يُرجع:
    - is_active: (True / False)
    - days_left: عدد الأيام المتبقية
    - end_date: تاريخ الانتهاء بصيغة مقروءة
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT sub_end_date FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return {"is_active": False, "days_left": 0, "end_date": "غير مشترك"}
            
            try:
                end_dt = datetime.fromisoformat(row[0])
                now = datetime.now()
                if end_dt > now:
                    remaining = end_dt - now
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    return {
                        "is_active": True,
                        "days_left": days,
                        "hours_left": hours,
                        "end_date": end_dt.strftime("%Y-%m-%d %H:%M")
                    }
                else:
                    return {"is_active": False, "days_left": 0, "end_date": "منتهي"}
            except Exception:
                return {"is_active": False, "days_left": 0, "end_date": "غير صالح"}

async def add_subscription(user_id: int, days: int = 30):
    """
    تفعيل أو تمديد الاشتراك منطقياً:
    إذا كان الاشتراك نشطاً، يتم إضافة الـ 30 يوماً فوق التاريخ القديم وليس من اليوم.
    """
    now = datetime.now()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT sub_end_date FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
            # إذا كان لديه اشتراك ساري، نبدأ الحساب من تاريخ انتهائه
            if row and row[0]:
                try:
                    current_end = datetime.fromisoformat(row[0])
                    if current_end > now:
                        new_end = current_end + timedelta(days=days)
                    else:
                        new_end = now + timedelta(days=days)
                except Exception:
                    new_end = now + timedelta(days=days)
            else:
                new_end = now + timedelta(days=days)

        await db.execute("""
            INSERT INTO users (user_id, sub_start_date, sub_end_date) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET sub_end_date = ?
        """, (user_id, now.isoformat(), new_end.isoformat(), new_end.isoformat()))
        await db.commit()

async def increment_swap_count(user_id: int):
    """تسجيل عدد العمليات المنفذة للإحصائيات"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET swap_count = swap_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
