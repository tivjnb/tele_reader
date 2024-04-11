from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.types import User
from quart import Quart, render_template, request, redirect, url_for
import asyncio
import asyncpg
import aiomysql

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
        self.db_type = None
        self.db_connection = None
        self.db_cursor = None

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

    async def __pg_connect(self, db_host, db_port, db_user, database, db_password):  # обернуть в собаку
        try:
            connection = await asyncpg.connect(
                user=db_user,
                password=db_password,
                database=database,
                host=db_host,
                port=db_port
            )
            self.db_connection = connection
            self.db_type = 'pgsql'

            await connection.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    data TIMESTAMP NOT NULL,
                    chat_name TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    message_text TEXT,
                    parent_message TEXT
                )
                ''')
            return True
        except Exception as e:
            print(e)
            return False

    async def __mysql_connect(self, db_host, db_port, db_user, database, db_password):
        try:
            connection = await aiomysql.connect(
                host='localhost',
                port=3306,
                user='user2',
                password='1234',
                db='my_sql_db'
            )
            cursor = await connection.cursor()
            self.db_type = 'mysql'
            self.db_connection = connection
            self.db_cursor = cursor
            await cursor.execute('''
                            CREATE TABLE IF NOT EXISTS messages (
                                id SERIAL PRIMARY KEY,
                                data DATETIME NOT NULL,
                                chat_name TEXT NOT NULL,
                                user_name TEXT NOT NULL,
                                message_text TEXT,
                                parent_message TEXT
                            )
                            ''')
            await connection.commit()
            return True
        except Exception as e:
            print(e)
            return False

    async def db_connector(self, db_type, db_host, db_port, db_user, database, db_password):
        if self.db_connection is not None:
            try:
                await self.db_connection.close()
            except Exception as e:
                print(e)
        if db_type == 'pgsql':
            await self.__pg_connect(db_host, db_port, db_user, database, db_password)
        elif db_type == 'mssql':
            pass
        elif db_type == 'mysql':
            await self.__mysql_connect(db_host, db_port, db_user, database, db_password)

    async def write_to_db(self, send_time, chat_name, sender_name, text):
        if self.db_type == 'pgsql':
            await self.db_connection.execute(f'''
            INSERT INTO messages (data, chat_name, user_name, message_text)
            VALUES ('{send_time}', '{chat_name}', '{sender_name}', '{text}')
            ''')
        elif self.db_type == 'mysql':
            await self.db_cursor.execute(f'''
            INSERT INTO messages (data, chat_name, user_name, message_text)
            VALUES ('{send_time}', '{chat_name}', '{sender_name}', '{text}')
            ''')
            await self.db_connection.commit()


    async def reader(self):  # надо наверное чаты по id смотреть, а не названию, но это потом
        async with self.client:
            @self.client.on(NewMessage)
            async def handle_new_message(event):
                chat = await event.get_chat()
                if isinstance(chat, User):
                    chat_title = ''
                    first_name = chat.first_name
                    last_name = chat.last_name
                    if (first_name is not None) and (last_name is not None):
                        chat_title = f"{first_name} {last_name}"
                    else:
                        chat_title += first_name if first_name is not None else ''
                        chat_title += last_name if last_name is not None else ''
                else:
                    chat_title = chat.title

                print(chat_title)
                if chat_title in self.chat_list.keys() and self.chat_list[chat_title]:
                    await self.write_to_db(
                        send_time=event.message.date,
                        chat_name=chat_title,
                        sender_name='pass',
                        text=event.message.text
                    )
                    with open('reader.log', 'a', encoding='utf8') as f:
                        f.write(f"{event.message.text} | "
                                f"{event.message.date} | "
                                f"{chat_title}\n")
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
        if not self.client.is_connected():
            await self.client.connect()
        dialogs = self.client.iter_dialogs()
        async for dialog in dialogs:
            title = dialog.title
            if title not in self.chat_list.keys():
                self.chat_list[title] = False
        return self.chat_list

    async def switch_chats(self, turn_on_list):
        for title in self.chat_list.keys():
            self.chat_list[title] = title in turn_on_list


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


@app.route('/main', methods=['GET', 'POST'])
async def main_page():
    phone = request.args.get('phone')
    action = request.args.get('action')
    if phone in MyClient.clients_list.keys():
        client: MyClient = MyClient.clients_list[phone]
    else:
        return "Что то с телефоном"

    if request.method == 'POST':
        form = await request.form
        if action == "connect_db":
            res = await client.db_connector(
                db_type=form.get('db_type'),
                db_host=form.get('host'),
                db_port=form.get('port'),
                db_user=form.get('user'),
                db_password=form.get('password'),
                database=form.get('database')
            )
        else:
            turn_on_list = [x[0] for x in form.items()]
            print(turn_on_list)
            await client.switch_chats(turn_on_list)
    chat_titles: dict = await client.get_chat_list()
    if action == "ON":
        asyncio.create_task(client.start())
        return await render_template(
            'chat_list.html',
            phone=phone,
            status='pass',
            message='Reader was started',
            chats=chat_titles
        )
    if action == "OFF":
        await client.ender()
        return await render_template(
            'chat_list.html',
            phone=phone, status='pass',
            message='Reader was ended',
            chats=chat_titles
        )
    return await render_template(
        'chat_list.html',
        phone=phone,
        status='pass',
        message='just look at chats',
        chats=chat_titles
    )


if __name__ == "__main__":
    app.run(debug=False)
