from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db_manager import add_subscription
from config import ADMIN_ID, STC_PAY_NUMBER, BANK_IBAN, PRICE_SAR, PRICE_STARS

router = Router()

class ManualPaymentFlow(StatesGroup):
    waiting_for_receipt = State()

@router.callback_query(F.data == "open_payment_menu")
async def show_payment_options(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐️ نجوم تيليجرام ({PRICE_STARS} نجمة - فوري)", callback_data="pay_stars")],
        [InlineKeyboardButton(text=f"🇸🇦 دفع محلي ({PRICE_SAR} - STC Pay / راجحي)", callback_data="pay_manual")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")]
    ])
    await callback.message.edit_text("💳 **اختر طريقة الاشتراك المناسبة:**", reply_markup=kb)

# مسار نجوم تيليجرام
@router.callback_query(F.data == "pay_stars")
async def send_stars_invoice(callback: CallbackQuery):
    prices = [LabeledPrice(label="اشتراك شهري في البوت", amount=PRICE_STARS)]
    await callback.message.answer_invoice(
        title="🌟 اشتراك شهري VIP",
        description="تبديل فوري وغير محدود لليوزرات لمدة 30 يوماً.",
        prices=prices,
        provider_token="",
        currency="XTR",
        payload="sub_stars_30d"
    )

@router.pre_checkout_query()
async def process_pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)

@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    await add_subscription(message.from_user.id, days=30)
    await message.answer("🎉 **تم استلام الدفع وتفعيل اشتراكك لمدة 30 يوماً بنجاح!**")

# مسار الدفع المحلي (STC Pay / بنك)
@router.callback_query(F.data == "pay_manual")
async def manual_stc_instructions(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualPaymentFlow.waiting_for_receipt)
    await callback.message.edit_text(
        f"🇸🇦 **بيانات التحويل المحلي:**\n\n"
        f"📱 **STC Pay:** `{STC_PAY_NUMBER}`\n"
        f"🏦 **IBAN:** `{BANK_IBAN}`\n"
        f"💰 **المبلغ:** {PRICE_SAR}\n\n"
        f"📸 **أرسل صورة إيصال التحويل هنا في المحادثة مباشرة:**"
    )

@router.message(ManualPaymentFlow.waiting_for_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user = message.from_user
    await state.clear()
    await message.answer("⏳ تم استلام الإيصال وجاري مراجعته من الإدارة.")
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ قبول وتفعيل", callback_data=f"adm_app_{user.id}"),
        InlineKeyboardButton(text="❌ رفض", callback_data=f"adm_rej_{user.id}")
    ]])
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=f"🔔 **طلب اشتراك جديد:**\n👤 {user.full_name} (@{user.username})\n🆔 `{user.id}`",
        reply_markup=admin_kb
    )

@router.callback_query(F.data.startswith("adm_app_"))
async def admin_approve(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.split("_")[2])
    await add_subscription(uid, days=30)
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 **تم القبول والتفعيل.**", reply_markup=None)
    await bot.send_message(chat_id=uid, text="🎉 **تم تفعيل اشتراكك بنجاح لمدة 30 يوماً!**")

@router.callback_query(F.data.startswith("adm_rej_"))
async def admin_reject(callback: CallbackQuery, bot: Bot):
    uid = int(callback.data.split("_")[2])
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **تم رفض الإيصال.**", reply_markup=None)
    await bot.send_message(chat_id=uid, text="❌ **تم رفض الإيصال من قبل الإدارة.** تواصل مع الدعم للمساعدة.")