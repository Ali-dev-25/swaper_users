import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db_manager import init_db, add_subscription, check_subscription
from bot.handlers import auth_wizard, payment
from config import BOT_TOKEN, ADMIN_ID

# -------------------------------------------------------------
# سيرفر ويب مصغر لفتح المنفذ وتخطي فحص Render (Port Binding)
# -------------------------------------------------------------
async def health_check(request):
    return web.Response(text="🚀 Telegram Swapper Bot is Alive and Running 24/7!", status=200)

async def start_dummy_server():
    port = int(os.getenv("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 تم فتح المنفذ بنجاح على Port: {port}")

# -------------------------------------------------------------
# تشغيل البوت الأساسي
# -------------------------------------------------------------
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    # 1. تشغيل خادم الويب المصغر لإرضاء Render
    await start_dummy_server()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    def get_main_menu(is_sub: bool):
        status_text = "✅ نشط" if is_sub else "❌ غير مشترك"
        return (
            f"👋 **مرحباً بك في بوت التبديل الفوري لليوزرات** ⚡️\n\n"
            f"📌 **حالة اشتراكك:** {status_text}\n"
            f"🛡 **الأمان:** تشفير كامل وتدمير فوري للجلسات بعد النقل.",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚡️ بدء تبديل يوزر", callback_data="start_swap_wizard")],
                [InlineKeyboardButton(text="💳 الاشتراك والأسعار", callback_data="open_payment_menu")]
            ])
        )

    @dp.message(CommandStart())
    async def start_cmd(message: Message):
        is_sub = await check_subscription(message.from_user.id)
        text, kb = get_main_menu(is_sub)
        await message.answer(text, reply_markup=kb)

    @dp.callback_query(F.data == "back_home")
    async def back_home(callback: CallbackQuery):
        is_sub = await check_subscription(callback.from_user.id)
        text, kb = get_main_menu(is_sub)
        await callback.message.edit_text(text, reply_markup=kb)

    @dp.message(Command("grant"), F.from_user.id == ADMIN_ID)
    async def grant_manual(message: Message):
        try:
            args = message.text.split()
            if len(args) > 1:
                target_id = int(args[1])
                await add_subscription(target_id, days=30)
                await message.answer(f"✅ تم تفعيل اشتراك 30 يوم للمعرف: `{target_id}`")
            else:
                await message.answer("⚠️ الصيغة: `/grant USER_ID`")
        except Exception as e:
            await message.answer(f"❌ خطأ: {str(e)}")

    # تضمين معالجات العمليات والدفع
    dp.include_router(auth_wizard.router)
    dp.include_router(payment.router)

    print("🚀 البوت قيد الاستماع ويعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
