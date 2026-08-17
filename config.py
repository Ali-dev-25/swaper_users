import os
from dotenv import load_dotenv

load_dotenv()

# البيانات الأساسية (يتم جلبها من البيئة أو وضعها مباشرة)
BOT_TOKEN = os.getenv("BOT_TOKEN","8885795921:AAHomJzVOEVfW1ddhlSC6Et69NL8X9Td5kM")
API_ID = int(os.getenv("API_ID", "39360245"))
API_HASH = os.getenv("API_HASH", "3703ecea7a48f62c1f1fa5ee97d5c9e1")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5739511727"))

# بيانات التحويل المحلي
STC_PAY_NUMBER = "0500000000"
BANK_IBAN = "SA0000000000000000000000"
PRICE_SAR = "120 ريال"
PRICE_STARS = 500