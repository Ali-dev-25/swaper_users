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

# نص دليل استخراج الكوكيز
COOKIE_GUIDE_TEXT = (
    "📖 **دليل استخراج كود الجلسة (sessionid) من تيك توك:**\n\n"
    "💻 **أولاً: من جهاز الكمبيوتر (الأسهل):**\n"
    "1. افتح المتصفح وادخل على [tiktok.com](https://www.tiktok.com) وسجل دخولك.\n"
    "2. اضغط بزر الفأرة الأيمن في أي مكان ثم اختر **Inspect (فحص)** أو اضغط `F12`.\n"
    "3. من الشريط العلوي اختر **Application** (أو **Storage**).\n"
    "4. من القائمة الجانبية اضغط على **Cookies** ثم اضغط على رابط تيك توك.\n"
    "5. ابحث عن اسم الكوكي: **`sessionid`** وانسخ القيمة الطويلة أمامه.\n\n"
    "📱 **ثانياً: من الجوال (الهاتف):**\n"
    "1. افتح متصفح يدعم الإضافات (مثل **Kiwi Browser** للأندرويد).\n"
    "2. ثبت إضافة **Cookie-Editor** من متجر إضافات كروم.\n"
    "3. افتح موقع تيك توك وسجل دخولك، ثم اضغط على الإضافة وانسخ قيمة **`sessionid`**.\n\n"
    "🛡 **تنبيه أمان:** كود الجلسة يُستخدم لمرة واحدة فقط لتغيير اليوزر ويتم حذفه وإتلافه من السيرفر فوراً."
)

# زر المساعدة السريعة
def get_help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ كيف أستخرج كود الجلسة (sessionid)؟", callback_data="show_cookie_guide")]
    ])

# -------------------------------------------------------------
# عرض دليل استخراج الكوكيز
# -------------------------------------------------------------
@router.callback_query(F.data == "show_cookie_guide")
async def show_guide(callback: CallbackQuery):
    await callback.message.answer(
        COOKIE_GUIDE_TEXT,
        disable_web_page_preview=True
    )
    await callback.answer()

# -------------------------------------------------------------
# مسار التبديل خطوة بخطوة
# -------------------------------------------------------------
@router.callback_query(F.data == "start_swap_wizard")
async def start_tiktok_wizard(callback: CallbackQuery, state: FSMContext):
    sub_info = await check_subscription(callback.from_user.id)
    if not sub_info["is_active"]:
        return await callback.message.edit_text(
            "⚠️ **عذراً، لا تملك اشتراكاً نشطاً أو انتهت مدته.**\nيرجى تجديد الاشتراك للمتابعة:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 شراء / تجديد الاشتراك", callback_data="open_payment_menu")
            ]])
        )
    
    await state.set_state(TikTokSwapFlow.session1)
    await callback.message.edit_text(
        "📍 **الخطوة (1/3) - الحساب الأول (المتنازل عن اليوزر):**\n\n"
        "أرسل كود الـ **`sessionid`** الخاص بالحساب الأول.",
        reply_markup=get_help_kb()
    )

@router.message(TikTokSwapFlow.session1)
async def process_tt_session1(message: Message, state: FSMContext):
    session1 = message.text.strip()
    await state.update_data(session1=session1)
    await message.delete()
    
    await state.set_state(TikTokSwapFlow.session2)
    await message.answer(
        "✅ تم حفظ جلسة الحساب الأول (وحُذفت للسرية).\n\n"
        "📍 **الخطوة (2/3) - الحساب الثاني (المستلم لليوزر):**\n"
        "أرسل الآن كود الـ **`sessionid`** للحساب الثاني:",
        reply_markup=get_help_kb()
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
        "أرسل يوزر التيك توك المراد نقله الآن (مثال: `myuser` أو `@myuser`):"
    )

@router.message(TikTokSwapFlow.target_username)
async def process_tt_execute(message: Message, state: FSMContext):
    target_user = message.text.strip().lstrip('@')
    data = await state.get_data()
    
    status_msg = await message.answer("⚡️ **جاري فحص الحسابين وتنفيذ التبديل الفوري...**")
    
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
            f"🛡 تم إتلاف بيانات الجلسات من الذاكرة بالكامل."
        )
    else:
        await status_msg.edit_text(f"❌ **فشلت العملية:**\n{result['error']}")
