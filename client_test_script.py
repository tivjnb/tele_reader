from telethon import TelegramClient
from telethon.events import NewMessage
import asyncio
from telethon.tl.types import User, Channel, Chat


async def main():
    api_id = 25517210
    api_hash = "1c349f3c3a54c464dabef9f2738e837a"

    client = TelegramClient('79268403751', api_id, api_hash)
    async with client:
        @client.on(NewMessage)
        async def new_message(event):
            message = event.message
            # Получаем информацию о сообщении
            sender = await message.get_sender()
            chat = await message.get_chat()
            date = message.date
            text = message.text

            # Проверяем, является ли сообщение ответом на другое сообщение
            reply_msg = None
            if message.reply_to_msg_id:
                reply_msg = await client.get_messages(chat, ids=message.reply_to_msg_id)

            # Выводим информацию о сообщении
            print("Дата:", date)
            print("Отправитель:", sender)
            print("Чат:", chat)
            print("Текст сообщения:", text)
            if reply_msg:
                print("Это ответ на сообщение:", reply_msg.text)
            print("-----------------------------")
        await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
