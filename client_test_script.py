from telethon import TelegramClient
import asyncio
from telethon.tl.types import User, Channel, Chat


async def main():
    api_id = 25517210
    api_hash = "1c349f3c3a54c464dabef9f2738e837a"

    client = TelegramClient('79268403751', api_id, api_hash)
    async with client:
        dialogs = client.iter_dialogs()

        async for dialog in dialogs:
            chat_id = dialog.id
            chat_title = dialog.title
            chat_type = dialog.entity.__class__.__name__
            if chat_type == 'User':
                print(dialog)
                print(dialog.name)
                print("Chat ID:", chat_id)
                print("Chat Title:", chat_title)
                print("Chat Type:", chat_type)

if __name__ == '__main__':
    asyncio.run(main())
