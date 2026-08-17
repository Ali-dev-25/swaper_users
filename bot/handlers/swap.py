from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.engine import fast_swap_username
from database.db_manager import check_subscription

API_ID = 39360245      # يتم جلبه من my.telegram.org
API_HASH = "3703ecea7a48f62c1f1fa5ee97d5c9e1" # يتم جلبه من my.telegram.org

router = Router()

class SwapFlow(StatesGroup):
    waiting_for_session1 = State()
    waiting_for_session2 = State()
    waiting_for_target_username = State()

@router.callback_query(F.data == "start_swap")
async def start_swap_process(callback: CallbackQuery, state: FSMContext):
    is_active = await check_subscription(callback.from_user.id)
    if not is_active:
        return await callback.message.edit_text(
            "⚠️ عذراً، لا تملك اشتراكاً فعالاً في البوت.\nيرجى تجديد اشتراكك للبدء.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 شراء اشتراك", callback_data="buy_sub")
            ]])
        )
    
    await state.set_state(SwapFlow.waiting_for_session1)
    await callback.message.edit_text(
        "📍 **الخطوة (1/3):**\nأرسل الآن كود الجلسة (Session String) للحساب **الأول** (المتنازل عن اليوزر)."
    )

@router.message(SwapFlow.waiting_for_session1)
async def process_session1(message: Message, state: FSMContext):
    await state.update_data(session1=message.text.strip())
    # حذف الرسالة التي تحتوي على الجلسة لحماية بيانات العميل
    await message.delete()
    
    await state.set_state(SwapFlow.waiting_for_session2)
    await message.answer("✅ تم استلام الجلسة الأولى بنجاح (وحُذفت للسرية).\n\n📍 **الخطوة (2/3):**\nأرسل الآن كود الجلسة للحساب **الثاني** (المستلم لليوزر).")

@router.message(SwapFlow.waiting_for_session2)
async def process_session2(message: Message, state: FSMContext):
    await state.update_data(session2=message.text.strip())
    await message.delete()
    
    await state.set_state(SwapFlow.waiting_for_target_username)
    await message.answer("✅ تم استلام الجلسة الثانية.\n\n📍 **الخطوة (3/3):**\nأرسل اليوزر المراد نقله (مثال: @username).")

@router.message(SwapFlow.waiting_for_target_username)
async def process_execution(message: Message, state: FSMContext):
    target_user = message.text.strip()
    data = await state.get_data()
    
    status_msg = await message.answer("⚡️ جاري فحص الحسابين وتنفيذ النقل الفوري...")
    
    # استدعاء المحرك الفوري
    result = await fast_swap_username(
        api_id=API_ID,
        api_hash=API_HASH,
        session_str_old=data['session1'],
        session_str_new=data['session2'],
        target_username=target_user
    )
    
    # تنظيف الذاكرة ومسح الـ State فوراً
    await state.clear()
    
    if result["status"]:
        await status_msg.edit_text(
            f"🎉 **تم التبديل بنجاح تام!**\n\n"
            f"🔹 اليوزر: {result['username']}\n"
            f"⚡️ زمن التنفيذ: `{result['latency_ms']} ms`\n"
            f"🛡 تم إتلاف الجلسات من الذاكرة بالكامل."
        )
    else:
        await status_msg.edit_text(f"❌ **فشلت العملية:**\n{result['error']}")