import aiohttp
import asyncio
import time
import re

TIKTOK_UPDATE_URL = "https://www.tiktok.com/api/user/profile/update/"
TIKTOK_CHECK_URL = "https://www.tiktok.com/api/user/detail/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*"
}

async def check_account_status(session_id: str) -> dict:
    """فحص صلاحية الحساب وقدرته على تغيير اليوزر قبل البدء"""
    cookies = {"sessionid": session_id}
    async with aiohttp.ClientSession(cookies=cookies, headers=HEADERS) as session:
        try:
            async with session.get(TIKTOK_CHECK_URL, timeout=6) as response:
                if response.status != 200:
                    return {"valid": False, "error": "تعذر الاتصال بسيرفر تيك توك"}
                data = await response.json()
                user_info = data.get("userInfo", {}).get("user", {})
                if not user_info:
                    return {"valid": False, "error": "كود الجلسة (sessionid) غير صالح أو منتهي الصلاحية"}
                
                return {
                    "valid": True,
                    "username": user_info.get("uniqueId", ""),
                    "nickname": user_info.get("nickname", "")
                }
        except Exception as e:
            return {"valid": False, "error": f"خطأ اتصال: {str(e)}"}

async def update_username(session_id: str, new_username: str) -> dict:
    """إرسال طلب التغيير لتيك توك مع توكن CSRF"""
    cookies = {"sessionid": session_id}
    data = {"unique_id": new_username}
    
    async with aiohttp.ClientSession(cookies=cookies, headers=HEADERS) as session:
        try:
            async with session.post(TIKTOK_UPDATE_URL, data=data, timeout=6) as response:
                res_json = await response.json()
                return res_json
        except Exception as e:
            return {"status_code": -1, "error": str(e)}

async def fast_swap_tiktok(session_old: str, session_new: str, target_username: str) -> dict:
    target_username = target_username.lstrip('@')
    temp_release_user = f"user_{int(time.time())}"

    # -------------------------------------------------------------
    # 1. مرحلة الفحص المسبق وحماية الحسابات (Pre-Flight Safety Check)
    # -------------------------------------------------------------
    acc1_check, acc2_check = await asyncio.gather(
        check_account_status(session_old),
        check_account_status(session_new)
    )

    if not acc1_check["valid"]:
        return {"status": False, "error": f"الحساب الأول: {acc1_check['error']}"}

    if not acc2_check["valid"]:
        return {"status": False, "error": f"الحساب الثاني: {acc2_check['error']}"}

    # التأكد من أن الحساب الأول يملك اليوزر فعلياً
    if acc1_check["username"].lower() != target_username.lower():
        return {
            "status": False, 
            "error": f"الحساب الأول لا يملك اليوزر @{target_username} (اليوزر الحالي له هو: @{acc1_check['username']})"
        }

    # -------------------------------------------------------------
    # 2. مرحلة النقل المتزامن السريع
    # -------------------------------------------------------------
    start_time = time.perf_counter()

    # تفريغ اليوزر من الحساب الأول
    res_release = await update_username(session_old, temp_release_user)
    if res_release.get("status_code") != 0:
        return {
            "status": False,
            "error": f"فشل تفريغ اليوزر من الحساب الأول: {res_release.get('status_msg', 'خطأ في تيك توك')}"
        }

    # حجز اليوزر في الحساب الثاني فوراً
    res_claim = await update_username(session_new, target_username)
    execution_time = (time.perf_counter() - start_time) * 1000

    # -------------------------------------------------------------
    # 3. التحقق النهائي من النجاح
    # -------------------------------------------------------------
    if res_claim.get("status_code") == 0:
        return {
            "status": True,
            "latency_ms": round(execution_time, 2),
            "username": f"@{target_username}",
            "old_acc_temp": temp_release_user
        }
    else:
        err_msg = res_claim.get("status_msg") or "فشل حجز اليوزر في الحساب الثاني (قد يكون الحساب مقيداً بمهلة 30 يوم)"
        return {
            "status": False,
            "error": err_msg
        }
