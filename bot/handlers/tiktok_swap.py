from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.tiktok_engine import fast_swap_tiktok
from database.db_manager import check_subscription

router = Router()

class TikTokSwapFlow(StatesGroup):
    session1 = State()
    session2 = State()
    target_username = State()

@router.callback_query(F.data == "start_swap_wizard")
async def start_tiktok_wizard(callback: CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        return await callback.message.edit_text(
            "⚠️ لا تملك اشتراكاً نشطاً في البوت. اشترك للبدء:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 شراء اشتراك", callback_data="open_payment_menu")
            ]])
        )
    
    await state.set_state(TikTokSwapFlow.session1)
    await callback.message.edit_text(
        "📍 **الخطوة (1/3) - الحساب الأول (المتنازل عن يوزر تيك توك):**\n\n"
        "أرسل كود الـ **`sessionid`** الخاص بالحساب الأول.\n\n"
        "*(يتم استخراجه من كوكيز المتصفح بعد فتح موقع tiktok.com)*"
    )

@router.message(TikTokSwapFlow.session1)
async def process_tt_session1(message: Message, state: FSMContext):
    session1 = message.text.strip()
    await state.update_data(session1=session1)
    await message.delete()  # حذف الرسالة للسرية
    
    await state.set_state(TikTokSwapFlow.session2)
    await message.answer(
        "✅ تم حفظ جلسة الحساب الأول (وحُذفت للسرية).\n\n"
        "📍 **الخطوة (2/3) - الحساب الثاني (المستلم ليوزر تيك توك):**\n"
        "أرسل كود الـ **`sessionid`** للحساب الثاني:"
    )

@router.message(TikTokSwapFlow.session2)
async def process_tt_session2(message: Message, state: FSMContext):
    session2 = message.text.strip()
    await state.update_data(session2=session2)
    await message.delete()
    
    await state.set_state(TikTokSwapFlow.target_username)
    await message.answer(
        "✅ تم حفظ الجلسة الثانية.\n\n"
        "📍 **الخطوة (3/3):**\n"
        "أرسل يوزر التيك توك المراد نقله الآن (مثال: `myuser`):"
    )

@router.message(TikTokSwapFlow.target_username)
async def process_tt_execute(message: Message, state: FSMContext):
    target_user = message.text.strip().lstrip('@')
    data = await state.get_data()
    
    status_msg = await message.answer("⚡️ **جاري فحص الحسابين وتنفيذ نقل يوزر تيك توك فوراً...**")
    
    # استدعاء محرك التيك توك
    result = await fast_swap_tiktok(
        session_old=data['session1'],
        session_new=data['session2'],
        target_username=target_user
    )
    
    await state.clear()
    
    if result["status"]:
        await status_msg.edit_text(
            f"🎉 **تم نقل يوزر تيك توك بنجاح تام!**\n\n"
            f"🔹 اليوزر: `@{target_user}`\n"
            f"⚡️ زمن النقل: `{result['latency_ms']} ms`\n"
            f"🛡 تم إتلاف بيانات الجلسات بالكامل."
        )
    else:
        await status_msg.edit_text(f"❌ **فشلت العملية:**\n{result['error']}")
