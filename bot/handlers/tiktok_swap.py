import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.tiktok_engine import fast_swap_tiktok
from database.db_manager import check_subscription, increment_swap_count

router = Router()

class TikTokSwapFlow(StatesGroup):
    session1 = State()
    session2 = State()
    target_username = State()

# رابط فيديو الشرح (يمكنك تغييره إلى رابط الفيديو الخاص بك أو رفعه على يوتيوب)
VIDEO_TUTORIAL_URL = "https://youtu.be/3cJ9ilss03I?si=9CfnBMd4TMksyvLi"  # ضع هنا رابط فيديو الشرح

COOKIE_GUIDE_TEXT = (
    "📖 **دليل استخراج كوكيز تيك توك (Session ID):**\n\n"
    "💻 **من الكمبيوتر (Google Chrome):**\n"
    "1. افتح موقع [tiktok.com](https://www.tiktok.com) وسجل دخولك.\n"
    "2. اضغط بزر الفأرة الأيمن ⬅️ **Inspect (فحص)**.\n"
    "3. اختر تبويب **Network** ثم اضغط على أي طلب من القائمة.\n"
    "4. انزل إلى قسم **Request Headers** وانسخ سطر **Cookie** بالكامل وأرسله هنا للبوت.\n\n"
    "📱 **من الجوال:**\n"
    "عبر متصفح **Kiwi Browser** وتثبيت إضافة **Cookie-Editor** ونسخ `sessionid`.\n\n"
    "🎥 **شاهد فيديو الشرح العملي بالضغط على الزر أدناه 👇**"
)

# دالة ذكية لاستخراج الـ sessionid تلقائياً مهما كان شكل النص المرسل
def extract_session_id(raw_text: str) -> str:
    raw_text = raw_text.strip()
    # إذا قام بنسخ كامل سطر الكوكيز مثل الفيديو
    match = re.search(r'sessionid=([^;]+)', raw_text)
    if match:
        return match.group(1).strip()
    # إذا أرسل الـ sessionid لوحده مباشرة
    return raw_text

def get_help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 مشاهدة فيديو الشرح", url=VIDEO_TUTORIAL_URL)],
        [InlineKeyboardButton(text="📖 قراءة الدليل النصي", callback_data="show_cookie_guide")]
    ])

# -------------------------------------------------------------
# عرض الدليل
# -------------------------------------------------------------
@router.callback_query(F.data == "show_cookie_guide")
async def show_guide(callback: CallbackQuery):
    await callback.message.answer(
        COOKIE_GUIDE_TEXT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎥 مشاهدة فيديو الشرح", url=VIDEO_TUTORIAL_URL)]
        ]),
        disable_web_page_preview=True
    )
    await callback.answer()

# -------------------------------------------------------------
# مسار التبديل الفوري
# -------------------------------------------------------------
@router.callback_query(F.data == "start_swap_wizard")
async def start_tiktok_wizard(callback: CallbackQuery, state: FSMContext):
    sub_info = await check_subscription(callback.from_user.id)
    if not sub_info["is_active"]:
        return await callback.message.edit_text(
            "⚠️ لا تملك اشتراكاً نشطاً في البوت. اشترك للبدء:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 شراء / تجديد الاشتراك", callback_data="open_payment_menu")
            ]])
        )
    
    await state.set_state(TikTokSwapFlow.session1)
    await callback.message.edit_text(
        "📍 **الخطوة (1/3) - الحساب الأول (المتنازل عن اليوزر):**\n\n"
        "أرسل كود الـ **`sessionid`** أو سطر الكوكيز كاملاً للحساب الأول.",
        reply_markup=get_help_kb()
    )

@router.message(TikTokSwapFlow.session1)
async def process_tt_session1(message: Message, state: FSMContext):
    # استخراج الجلسة بذكاء
    session1 = extract_session_id(message.text)
    await state.update_data(session1=session1)
    await message.delete()
    
    await state.set_state(TikTokSwapFlow.session2)
    await message.answer(
        "✅ تم حفظ جلسة الحساب الأول بنجاح (وحُذفت للسرية).\n\n"
        "📍 **الخطوة (2/3) - الحساب الثاني (المستلم لليوزر):**\n"
        "أرسل الآن كود الـ **`sessionid`** أو كوكيز الحساب الثاني:",
        reply_markup=get_help_kb()
    )

@router.message(TikTokSwapFlow.session2)
async def process_tt_session2(message: Message, state: FSMContext):
    session2 = extract_session_id(message.text)
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
    
    status_msg = await message.answer("⚡️ **جاري فحص الحسابين وتنفيذ نقل اليوزر فوراً...**")
    
    result = await fast_swap_tiktok(
        session_old=data['session1'],
        session_new=data['session2'],
        target_username=target_user
    )
    
    await state.clear()
    
    if result["status"]:
        await increment_swap_count(message.from_user.id)
        await status_msg.edit_text(
            f"🎉 **تم نقل يوزر تيك توك بنجاح تام!**\n\n"
            f"🔹 اليوزر: `@{target_user}`\n"
            f"⚡️ زمن النقل: `{result['latency_ms']} ms`\n"
            f"🛡 تم إتلاف بيانات الجلسات من الذاكرة بالكامل."
        )
    else:
        await status_msg.edit_text(f"❌ **فشلت العملية:**\n{result['error']}")
