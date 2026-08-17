from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("أدخل API_ID: "))
API_HASH = input("أدخل API_HASH: ")

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n✅ كود الجلسة (Session String) الخاص بحسابك هو:")
    print("=" * 60)
    print(client.session.save())
    print("=" * 60)