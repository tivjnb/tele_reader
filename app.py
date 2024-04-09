from telethon import TelegramClient
from telethon.events import NewMessage
from quart import Quart, render_template, request, redirect, url_for
import asyncio

app = Quart(__name__)

api_id = 25517210
api_hash = "1c349f3c3a54c464dabef9f2738e837a"


class MyClient:
    clients_list = dict()

    def __init__(self, phone):
        self.phone = phone
        self.client = TelegramClient(phone, api_id, api_hash)

        self.phone_code_hash = None
        self.reader_task = None

        self.chat_list = dict()

        MyClient.clients_list[phone] = self
        print("New client was initialized")

    async def is_authorized(self):
        if not self.client.is_connected():
            await self.client.connect()
        if await self.client.is_user_authorized():
            return True
        else:
            return False

    async def send_code(self):
        if not self.client.is_connected():
            await self.client.connect()
        send_code = await self.client.send_code_request(phone=self.phone)
        self.phone_code_hash = send_code.phone_code_hash

    async def sing_in(self, code):
        if not self.client.is_connected():
            await self.client.connect()
        await self.client.sign_in(phone=self.phone, phone_code_hash=self.phone_code_hash, code=code)

    async def reader(self):  # надо наверное чаты по id смотреть, а не названию, но это потом
        async with self.client:
            @self.client.on(NewMessage)
            async def handle_new_message(event):
                chat = event.chat.title

                with open('reader.log', 'a', encoding='utf8') as f:
                    f.write(f"{event.message.text} | "
                            f"{event.message.date} | "
                            f"{chat}\n")
            await self.client.run_until_disconnected()

            print('end')

    async def start(self):  # Можно будет добавить st_time, чтобы отсеивать сообщения после выключения
        if self.reader_task is None:
            self.reader_task = asyncio.create_task(self.reader())
        if not self.client.is_connected():
            await self.client.connect()

    async def ender(self):
        if self.client.is_connected():
            await self.client.disconnect()

    async def get_chat_list(self):
        async with self.client:
            dialogs = self.client.iter_dialogs()
            chat_list = [dialog.title async for dialog in dialogs]
            return chat_list


@app.route('/', methods=['GET', 'POST'])
async def get_phone():
    if request.method == 'GET':
        return await render_template('phone_request.html')

    if request.method == 'POST':
        form = await request.form
        phone = form.get('phone_number')
        phone = phone.replace('+', '')  # временная мера нужная из-за того, что + странно передается

        if phone not in MyClient.clients_list.keys():
            MyClient(phone)
        client: MyClient = MyClient.clients_list[phone]

        if await client.is_authorized():
            target_url = url_for('main_page', phone=phone)
            return redirect(target_url)
        else:
            await client.send_code()
            target_url = url_for('get_code', phone=phone)
            return redirect(target_url)
    return "Unsupported method"


@app.route('/code', methods=['GET', 'POST'])
async def get_code():

    if request.method == 'GET':
        phone = request.args.get('phone')
        return await render_template('get_code.html', phone=phone)

    if request.method == 'POST':
        form = await request.form
        pass_code = form.get('code')
        phone = form.get('phone')
        if phone in MyClient.clients_list.keys():
            client: MyClient = MyClient.clients_list[phone]
        else:
            return "Что то с номером"

        await client.sing_in(pass_code)

        target_url = url_for('main_page', phone=phone)
        return redirect(target_url)


@app.route('/main')
async def main_page():
    phone = request.args.get('phone')
    action = request.args.get('action')
    if phone in MyClient.clients_list.keys():
        client = MyClient.clients_list[phone]
    else:
        return "Что то с телефоном"

    chat_titles: dict = await client.get_chat_list()
    if action == "ON":
        asyncio.create_task(client.start())
        return await render_template(
            'main.html',
            phone=phone,
            status='pass',
            message='Reader was started',
            chats=chat_titles
        )
    if action == "OFF":
        await client.ender()
        return await render_template(
            'main.html',
            phone=phone, status='pass',
            message='Reader was ended',
            chats=chat_titles
        )
    return await render_template(
        'main.html',
        phone=phone,
        status='pass',
        message='just look at chats',
        chats=chat_titles
    )


if __name__ == "__main__":
    app.run(debug=False)
