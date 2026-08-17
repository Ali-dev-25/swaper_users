from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from core.engine import fast_swap_username
from database.db_manager import check_subscription
from config import API_ID, API_HASH

router = Router()

class SwapWizard(StatesGroup):
    acc1_phone = State()
    acc1_code = State()
    acc1_2fa = State()
    acc2_phone = State()
    acc2_code = State()
    acc2_2fa = State()
    target_username = State()

active_clients = {}

@router.callback_query(F.data == "start_swap_wizard")
async def start_wizard(callback: CallbackQuery, state: FSMContext):
    if not await check_subscription(callback.from_user.id):
        return await callback.message.edit_text(
            "⚠️ لا تملك اشتراكاً نشطاً. اشترك للبدء:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 شراء اشتراك", callback_data="open_payment_menu")
            ]])
        )
    await state.set_state(SwapWizard.acc1_phone)
    await callback.message.edit_text("📍 **الخطوة (1/3) - الحساب الأول (المتنازل):**\nأرسل رقم الهاتف مع مفتاح الدولة الدولي (مثال: `+966500000000`).")

@router.message(SwapWizard.acc1_phone)
async def process_acc1_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_clients[f"{message.from_user.id}_1"] = client
        await state.update_data(phone1=phone, phone_hash1=sent_code.phone_code_hash)
        await state.set_state(SwapWizard.acc1_code)
        await message.answer("📩 أرسل كود التحقق الواصل لحسابك (مثال: `1 2 3 4 5`):")
    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ خطأ: {str(e)}")

@router.message(SwapWizard.acc1_code)
async def process_acc1_code(message: Message, state: FSMContext):
    code = message.text.replace(" ", "").strip()
    data = await state.get_data()
    client: TelegramClient = active_clients.get(f"{message.from_user.id}_1")
    await message.delete()
    try:
        await client.sign_in(phone=data['phone1'], code=code, phone_code_hash=data['phone_hash1'])
        await state.update_data(session1=client.session.save())
        await client.disconnect()
        del active_clients[f"{message.from_user.id}_1"]
        await state.set_state(SwapWizard.acc2_phone)
        await message.answer("✅ تم توثيق الحساب الأول!\n\n📍 **الخطوة (2/3) - الحساب الثاني (المستلم):**\nأرسل رقم الهاتف الدولي:")
    except SessionPasswordNeededError:
        await state.set_state(SwapWizard.acc1_2fa)
        await message.answer("🔐 الحساب محمي بالتحقق بخطوتين (2FA)، أرسل كلمة المرور:")
    except Exception as e:
        await message.answer(f"❌ خطأ: {str(e)}")

@router.message(SwapWizard.acc1_2fa)
async def process_acc1_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    client: TelegramClient = active_clients.get(f"{message.from_user.id}_1")
    await message.delete()
    try:
        await client.sign_in(password=password)
        await state.update_data(session1=client.session.save())
        await client.disconnect()
        del active_clients[f"{message.from_user.id}_1"]
        await state.set_state(SwapWizard.acc2_phone)
        await message.answer("✅ تم التوثيق!\n\n📍 **الخطوة (2/3) - الحساب الثاني:** أرسل رقم الهاتف:")
    except Exception as e:
        await message.answer(f"❌ كلمة المرور غير صحيحة: {str(e)}")

@router.message(SwapWizard.acc2_phone)
async def process_acc2_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_clients[f"{message.from_user.id}_2"] = client
        await state.update_data(phone2=phone, phone_hash2=sent_code.phone_code_hash)
        await state.set_state(SwapWizard.acc2_code)
        await message.answer("📩 أرسل كود التحقق للحساب الثاني:")
    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ خطأ: {str(e)}")

@router.message(SwapWizard.acc2_code)
async def process_acc2_code(message: Message, state: FSMContext):
    code = message.text.replace(" ", "").strip()
    data = await state.get_data()
    client: TelegramClient = active_clients.get(f"{message.from_user.id}_2")
    await message.delete()
    try:
        await client.sign_in(phone=data['phone2'], code=code, phone_code_hash=data['phone_hash2'])
        await state.update_data(session2=client.session.save())
        await client.disconnect()
        del active_clients[f"{message.from_user.id}_2"]
        await state.set_state(SwapWizard.target_username)
        await message.answer("✅ تم توثيق الحسابين بنجاح!\n\n📍 **الخطوة (3/3):** أرسل اليوزر المطلوب نقله (مثال: `@username`):")
    except SessionPasswordNeededError:
        await state.set_state(SwapWizard.acc2_2fa)
        await message.answer("🔐 الحساب محمي بـ 2FA، أرسل كلمة المرور:")
    except Exception as e:
        await message.answer(f"❌ خطأ: {str(e)}")

@router.message(SwapWizard.acc2_2fa)
async def process_acc2_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    client: TelegramClient = active_clients.get(f"{message.from_user.id}_2")
    await message.delete()
    try:
        await client.sign_in(password=password)
        await state.update_data(session2=client.session.save())
        await client.disconnect()
        del active_clients[f"{message.from_user.id}_2"]
        await state.set_state(SwapWizard.target_username)
        await message.answer("✅ تم التوثيق!\n\n📍 **الخطوة (3/3):** أرسل اليوزر المطلوب نقله:")
    except Exception as e:
        await message.answer(f"❌ كلمة المرور خاطئة: {str(e)}")

@router.message(SwapWizard.target_username)
async def execute_wizard_swap(message: Message, state: FSMContext):
    target_user = message.text.strip()
    data = await state.get_data()
    status_msg = await message.answer("⚡️ **جاري فحص الحسابين وتنفيذ التبديل الفوري...**")
    
    result = await fast_swap_username(
        api_id=API_ID,
        api_hash=API_HASH,
        session_str_old=data['session1'],
        session_str_new=data['session2'],
        target_username=target_user
    )
    await state.clear()
    
    if result["status"]:
        await status_msg.edit_text(
            f"🎉 **تم نقل اليوزر بنجاح!**\n\n"
            f"🔹 اليوزر: `{result['username']}`\n"
            f"⚡️ زمن النقل: `{result['latency_ms']} ms`\n"
            f"🛡 تم إتلاف الجلسات من السيرفر فوراً."
        )
    else:
        await status_msg.edit_text(f"❌ **فشلت العملية:**\n{result['error']}")