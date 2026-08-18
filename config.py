import os
from dotenv import load_dotenv

load_dotenv()

# توكن البوت والآيدي الخاص بك (الأدمن)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8885795921:AAHomJzVOEVfW1ddhlSC6Et69NL8X9Td5kM")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5739511727"))

# بيانات التحويل المحلي والاشتراكات
STC_PAY_NUMBER = "0500000000"
BANK_IBAN = "SA0000000000000000000000"
PRICE_SAR = "120 ريال"
PRICE_STARS = 500
