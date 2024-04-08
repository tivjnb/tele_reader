from telethon import TelegramClient
from telethon.events import NewMessage
from quart import Quart, render_template, request, redirect, url_for
import asyncio

app = Quart(__name__)

api_id = 25517210
api_hash = "1c349f3c3a54c464dabef9f2738e837a"

target_message = "It's time to STOP!"


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
                    f.write(str(event.message.message) + "   " + str(event.message.date) + '  ' + str(event.message) + '\n')
                    print('1')
            await self.client.run_until_disconnected()

    async def end(self):
        await self.client.disconnect()

    async def get_chat_list(self):
        async with self.client:
            dialogs = self.client.iter_dialogs()
            dialog_titles = [x.title async for x in dialogs]
        return dialog_titles



'''
@client.on(NewMessage)
async def handle_new_message(event):
    global is_started
    with open('log.txt', 'a') as f:
        f.write(str(event.message.message)+"   "+str(event.message.date) + '  ' + str(event.message)+'\n')
        print('1')
    if target_message in event.message.message:
        print("Целевое сообщение получено. Завершение скрипта.")
        await client.disconnect()  # Отключение клиента
        is_started = False
'''


async def reader(phone):
    read_client = TelegramClient(phone, api_id, api_hash)
    async with read_client:
        @read_client.on(NewMessage)
        async def handle_new_message(event):
            with open('log.txt', 'a') as f:
                f.write(f"{event.message.message} | {event.message.date}\n")
                print('1')
            if target_message in event.message.message:
                print("Целевое сообщение получено. Завершение скрипта.")
                await read_client.disconnect()
        await read_client.run_until_disconnected()

'''
# Запуск клиента
@app.route('/users/<user_name>')
async def user_page(user_name):
    global is_started
    a = request.args.get("action")
    match a:
        case 'ON':
            asyncio.create_task(starter())
            is_started = True
        case 'OFF':
            client.disconnect()
            is_started = False

    print(a)
    return await render_template('user_info.html', user_name=user_name, is_active=is_started)

'''


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
            print(p_c_h)

            target_url = url_for('code', phone=phone, code_hash=p_c_h)
            await s_client.disconnect()
            return redirect(target_url)
    return "Unsupported method"


@app.route('/code', methods=['GET', 'POST'])
async def code():

    if request.method == 'GET':
        phone = request.args.get('phone')
        code_hash = request.args.get('code_hash')
        print(code_hash)
        return await render_template('get_code.html', phone=phone, code_hash=code_hash)

    if request.method == 'POST':
        form = await request.form
        pass_code = form.get('code')
        phone = form.get('phone')
        code_hash = form.get('code_hash')
        print(code_hash,phone,code)

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


@app.route('/stop')
async def stop():

    return "task stoped"

if __name__ == "__main__":
    app.run(debug=False)
