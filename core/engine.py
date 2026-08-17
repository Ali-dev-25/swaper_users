import asyncio
import time
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateUsernameRequest
from telethon.errors import FloodWaitError, UsernameOccupiedError

async def fast_swap_username(
    api_id: int,
    api_hash: str,
    session_str_old: str,
    session_str_new: str,
    target_username: str
) -> dict:
    target_username = target_username.lstrip('@')
    
    client_old = TelegramClient(StringSession(session_str_old), api_id, api_hash)
    client_new = TelegramClient(StringSession(session_str_new), api_id, api_hash)

    try:
        await asyncio.gather(
            client_old.connect(),
            client_new.connect()
        )

        if not await client_old.is_user_authorized() or not await client_new.is_user_authorized():
            return {"status": False, "error": "إحدى الجلسات غير صالحة أو منتهية."}

        start_time = time.perf_counter()

        # الخطوة 1: تفريغ اليوزر من الحساب القديم
        await client_old(UpdateUsernameRequest(username=""))

        # الخطوة 2: حجز اليوزر في الحساب الجديد فوراً
        await client_new(UpdateUsernameRequest(username=target_username))

        execution_time = (time.perf_counter() - start_time) * 1000

        return {
            "status": True,
            "latency_ms": round(execution_time, 2),
            "username": f"@{target_username}"
        }

    except UsernameOccupiedError:
        return {"status": False, "error": "تم قنص اليوزر من طرف خارجي أو أنه محجوز!"}
    except FloodWaitError as e:
        return {"status": False, "error": f"حظر مؤقت من تيليجرام لمدة {e.seconds} ثانية."}
    except Exception as e:
        return {"status": False, "error": f"خطأ غير متوقع: {str(e)}"}

    finally:
        await asyncio.gather(
            client_old.disconnect(),
            client_new.disconnect(),
            return_exceptions=True
        )
        del client_old
        del client_new