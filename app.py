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
        self.client = TelegramClient(phone, api_id, api_hash)
        MyClient.clients_list[phone] = self

    async def start(self):
        async with self.client:
            @self.client.on(NewMessage)
            async def handle_new_message(event):
                with open('log.txt', 'a') as f:
                    f.write(f"{event.message.message} | {event.message.date}\n")
            await self.client.run_until_disconnected()

    async def end(self):
        await self.client.disconnect()

    async def get_chat_list(self):
        async with self.client:
            dialogs = self.client.iter_dialogs()
            dialog_titles = [x.title async for x in dialogs]
        return dialog_titles


@app.route('/phone', methods=['GET', 'POST'])
async def get_phone():
    if request.method == 'GET':
        return await render_template('phone_request.html')
    if request.method == 'POST':
        form = await request.form
        phone = form.get('phone_number')
        phone = phone.replace('+','')
        s_client = TelegramClient(phone, api_id, api_hash)
        await s_client.connect()
        if await s_client.is_user_authorized():
            target_url = url_for('main_page', phone=phone)
            await s_client.disconnect()
            return redirect(target_url)
        else:
            send_code = await s_client.send_code_request(phone=phone)
            p_c_h = send_code.phone_code_hash

            target_url = url_for('code', phone=phone, code_hash=p_c_h)
            await s_client.disconnect()
            return redirect(target_url)
    return "Unsupported method"


@app.route('/code', methods=['GET', 'POST'])
async def code():

    if request.method == 'GET':
        phone = request.args.get('phone')
        code_hash = request.args.get('code_hash')
        return await render_template('get_code.html', phone=phone, code_hash=code_hash)

    if request.method == 'POST':
        form = await request.form
        pass_code = form.get('code')
        phone = form.get('phone')
        code_hash = form.get('code_hash')

        client_code_func = TelegramClient(phone, api_id, api_hash)
        await client_code_func.connect()
        await client_code_func.sign_in(phone=phone, phone_code_hash=code_hash, code=pass_code)

        target_url = url_for('main_page', phone=phone)
        await client_code_func.disconnect()
        return redirect(target_url)


@app.route('/main')
async def main_page():
    phone = request.args.get('phone')
    action = request.args.get('action')
    client = MyClient(phone)
    chats = await client.get_chat_list()
    if action == "ON":
        asyncio.create_task(client.start())
        return await render_template('main.html', phone=phone, status='pass', message='Reader was started', chats=chats)
    if action == "OFF":
        client = MyClient.clients_list[phone]
        await client.end()
        return await render_template('main.html', phone=phone, status='pass', message='Reader was ended', chats=chats)
    return await render_template('main.html', phone=phone, status='pass', message='just look at chats', chats=chats)


if __name__ == "__main__":
    app.run(debug=False)
