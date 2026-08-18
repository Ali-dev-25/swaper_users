import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db_manager import init_db, add_subscription, check_subscription
from bot.handlers import tiktok_swap, payment
from config import BOT_TOKEN, ADMIN_ID

# سيرفر ويب داخلي لإبقاء السيرفر حياً
async def health_check(request):
    return web.Response(text="Bot is running smoothly!", status=200)

async def start_dummy_server():
    port = int(os.getenv("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await start_dummy_server()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    def build_main_menu(sub_info: dict):
        if sub_info["is_active"]:
            status_text = (
                f"✅ **نشط (VIP)**\n"
                f"⏳ **المتبقي:** {sub_info['days_left']} يوم و {sub_info.get('hours_left', 0)} ساعة\n"
                f"📅 **ينتهي في:** `{sub_info['end_date']}`\n"
                f"⚡️ **العمليات:** غير محدودة"
            )
            buttons = [
                [InlineKeyboardButton(text="⚡️ بدء تبديل يوزر تيك توك", callback_data="start_swap_wizard")],
                [InlineKeyboardButton(text="💳 تمديد الاشتراك", callback_data="open_payment_menu")],
                [InlineKeyboardButton(text="📖 شرح استخراج الكوكيز", callback_data="show_cookie_guide")]
            ]
        else:
            status_text = "❌ **غير مشترك (أو انتهى الاشتراك)**"
            buttons = [
                [InlineKeyboardButton(text="💳 شراء اشتراك جديد", callback_data="open_payment_menu")],
                [InlineKeyboardButton(text="📖 شرح استخراج الكوكيز", callback_data="show_cookie_guide")]
            ]

        return (
            f"👋 **مرحباً بك في بوت التبديل الفوري لحسابات تيك توك** ⚡️\n\n"
            f"📌 **حالة اشتراكك:**\n{status_text}\n\n"
            f"🛡 **الأمان:** تشفير كامل وتدمير فوري لكود الجلسة بعد النقل.",
            InlineKeyboardMarkup(inline_keyboard=buttons)
        )

    @dp.message(CommandStart())
    async def start_cmd(message: Message, state: FSMContext):
        await state.clear()
        sub_info = await check_subscription(message.from_user.id)
        text, kb = build_main_menu(sub_info)
        await message.answer(text, reply_markup=kb)

    @dp.callback_query(F.data == "back_home")
    async def back_home(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        sub_info = await check_subscription(callback.from_user.id)
        text, kb = build_main_menu(sub_info)
        await callback.message.edit_text(text, reply_markup=kb)

    # أمر الأدمن لتفعيل اشتراك وتحديد عدد الأيام: /grant 12345678 30
    @dp.message(Command("grant"), F.from_user.id == ADMIN_ID)
    async def grant_manual(message: Message):
        try:
            args = message.text.split()
            target_id = int(args[1])
            days = int(args[2]) if len(args) > 2 else 30
            await add_subscription(target_id, days=days)
            await message.answer(f"✅ تم تفعيل/تمديد الاشتراك لمدة {days} يوماً للمستخدم: `{target_id}`")
        except Exception as e:
            await message.answer("⚠️ الصيغة: `/grant USER_ID DAYS`\nمثال: `/grant 5739511727 30`")

    dp.include_router(tiktok_swap.router)
    dp.include_router(payment.router)

    print("🚀 البوت شغال الآن بالمنطق الكامل...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
