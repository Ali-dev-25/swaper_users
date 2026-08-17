import aiohttp
import asyncio
import time

TIKTOK_UPDATE_URL = "https://www.tiktok.com/api/user/profile/update/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*"
}

async def update_tiktok_username(session_id: str, new_username: str) -> dict:
    """إرسال طلب تغيير يوزر تيك توك عبر كوكيز الجلسة"""
    cookies = {"sessionid": session_id}
    data = {"unique_id": new_username}
    
    async with aiohttp.ClientSession(cookies=cookies, headers=HEADERS) as session:
        try:
            async with session.post(TIKTOK_UPDATE_URL, data=data, timeout=5) as response:
                res_json = await response.json()
                return res_json
        except Exception as e:
            return {"status_code": -1, "error": str(e)}

async def fast_swap_tiktok(session_old: str, session_new: str, target_username: str) -> dict:
    """
    محرك التبديل الفوري لتيك توك:
    1. تفريغ اليوزر من الحساب القديم (إعطاؤه يوزر عشوائي مؤقت).
    2. تثبيت اليوزر المستهدف فوراً في الحساب الجديد.
    """
    target_username = target_username.lstrip('@')
    # يوزر عشوائي مؤقت لتفريغ اليوزر المستهدف
    temp_release_user = f"user_{int(time.time())}"

    start_time = time.perf_counter()

    # الخطوة 1: تفريغ اليوزر من الحساب القديم
    res_release = await update_tiktok_username(session_old, temp_release_user)
    
    # الخطوة 2: حجز اليوزر في الحساب الجديد فوراً دون انتظار
    res_claim = await update_tiktok_username(session_new, target_username)

    execution_time = (time.perf_counter() - start_time) * 1000  # بالملي ثانية

    # فحص نتيجة الحجز
    if res_claim.get("status_code") == 0:
        return {
            "status": True,
            "latency_ms": round(execution_time, 2),
            "username": f"@{target_username}"
        }
    else:
        err_msg = res_claim.get("status_msg") or res_claim.get("error") or "فشل تثبيت اليوزر (قد يكون محجوزاً أو تم تغيير اليوزر خلال 30 يوم)"
        return {
            "status": False,
            "error": err_msg
        }
