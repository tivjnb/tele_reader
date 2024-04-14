from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.types import User, Channel, Chat
from quart import Quart, render_template, request, redirect, url_for
import asyncio
from sqlalchemy import create_engine, text, Table, Column, Integer, String, DateTime, MetaData, insert, BigInteger

app = Quart(__name__)

api_id = 25517210
api_hash = "1c349f3c3a54c464dabef9f2738e837a"

metadata_obj = MetaData()
messages_table = Table(
    'messages',
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('data_time', DateTime, nullable=False),
    Column('chat_type', String(10), nullable=False),
    Column('chat_id', BigInteger, nullable=False),
    Column('chat_name', String(150), nullable=False),
    Column('message_id', BigInteger, nullable=False),
    Column('message_text', String(1000), nullable=False),
    Column('sender_type', String(10), nullable=False),
    Column('sender_name', String(150), nullable=False),
    Column('sender_id', BigInteger, nullable=False),
    Column('replied_to', BigInteger)
)


class MyClient:
    clients_list = dict()

    def __init__(self, phone):
        self.phone = phone
        self.client = TelegramClient(phone, api_id, api_hash)

        self.phone_code_hash = None
        self.reader_task = None

        self.chat_list = dict()

        self.databases = {'pgsql': None, 'mysql': None}

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

    def __engine_creator(self, db_url):  # обернуть в собаку
        try:
            engine = create_engine(
                url=db_url,
                echo=False
            )
            metadata_obj.create_all(engine)
            return engine
        except Exception as e:
            print(e)

    async def db_connector(self, db_type, db_host, db_port, db_user, db_name, db_password):
        engine = None
        if db_type == 'pgsql':
            db_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            engine = self.__engine_creator(db_url)

        if db_type == 'mysql':
            db_url = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            engine = self.__engine_creator(db_url)
        if engine is not None:
            self.databases[db_type] = engine

    async def db_disconnector(self, db_type):
        pass

    def __writer(self, engine, data_to_insert):
        with engine.connect() as conn:
            stmt = insert(messages_table).values(data_to_insert)
            conn.execute(stmt)
            conn.commit()

    def write_to_db(self, data_to_insert):
        for db in self.databases.values():
            if db is not None:
                self.__writer(db, data_to_insert)

    async def __first_last_to_name(self, first_name, last_name):
        name=''
        if first_name is not None and last_name is not None:
            name = f"{first_name} {last_name}"
        elif first_name is not None:
            name = first_name
        elif last_name is not None:
            name = last_name
        else:
            raise Exception("Empty name")
        return name

    async def reader(self):  # надо наверное чаты по id смотреть, а не названию, но это потом
        async with self.client:
            @self.client.on(NewMessage)
            async def new_message_reader(event):
                chat = await event.get_chat()
                chat_title = ''
                chat_type = ''
                if isinstance(chat, User):
                    chat_title = await self.__first_last_to_name(chat.first_name, chat.last_name)
                    chat_type = 'User'
                elif isinstance(chat, Chat):
                    chat_title = chat.title
                    chat_type = 'Chat'
                elif isinstance(chat, Channel):
                    chat_title = chat.title
                    chat_type = 'Channel'
                chat_id = chat.id
                print(chat_title)
                if chat_title in self.chat_list.keys() and self.chat_list[chat_title]:
                    message_id = event.message.id
                    sender = await event.get_sender()
                    if isinstance(sender, User):
                        sender_name = await self.__first_last_to_name(sender.first_name, sender.last_name)
                        sender_type = 'User'
                    elif isinstance(sender, Channel):
                        sender_name = sender.title
                        sender_type = 'Channel'
                    else:
                        raise Exception(sender)
                    sender_id = sender.id

                    data_to_insert = {
                        "data_time": f"{event.message.date}",
                        "chat_type": f"{chat_type}",
                        "chat_id": f"{chat_id}",
                        "chat_name": f"{chat_title}",
                        "message_id": f"{message_id}",
                        "message_text": f"{event.message.text}",
                        "sender_type": f"{sender_type}",
                        "sender_name": f"{sender_name}",
                        "sender_id": f"{sender_id}"
                    }
                    replied_to = event.message.reply_to_msg_id
                    if replied_to is not None:
                        data_to_insert["replied_to"] = replied_to
                    self.write_to_db(data_to_insert)
                    with open('reader.log', 'a', encoding='utf8') as f:
                        f.write(
                            f"_______________________________________\n"
                            f"Дата: {event.message.date}\n"
                            f"Тип чата: {chat_type}\n"
                            f"ID чата: {chat_id}\n"
                            f"Название чата: {chat_title}\n"
                            f"ID сообщения: {message_id}\n"
                            f"Текст сообщения: {event.message.text}\n"
                            f"Тип отправителя: {sender_type}\n"
                            f"ID отправителя: {sender_id}\n"
                            f"Имя отправителя: {sender_name}\n"
                            f"Ответ на: {event.message.reply_to_msg_id}\n"
                            )

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

    async def get_status(self):
        stratus = f'''
            PostgreSQL: {self.databases['pgsql'] is not None} \n
            MySQL: {self.databases['mysql'] is not None} \n
            Записывается: {self.client.is_connected() and self.reader_task is not None}
            '''
        return stratus


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
    message = 'Нет действий'
    if request.method == 'POST':
        form = await request.form
        if 'connect' in str(action):
            db_type = ''
            if action == "connect_pgsql":
                db_type = 'pgsql'
                message = "PosqtgreSQL подключен"
            elif action == "connect_mysql":
                db_type = 'mysql'
                message = "MySQL подключен"
            await client.db_connector(
                db_type=db_type,
                db_host=form.get('host'),
                db_port=form.get('port'),
                db_user=form.get('user'),
                db_password=form.get('password'),
                db_name=form.get('database')
            )
        else:
            turn_on_list = [x[0] for x in form.items()]
            message = f"Изменен список чатов. Новый список: {turn_on_list}"
            await client.switch_chats(turn_on_list)
    chat_titles: dict = await client.get_chat_list()

    if action == "ON":
        asyncio.create_task(client.start())
        message = "Начата запись сообщений"
    if action == "OFF":
        await client.ender()
        message = "Запись сообщений закончена"
    return await render_template(
        'chat_list.html',
        phone=phone,
        status=await client.get_status(),
        message=message,
        chats=chat_titles
    )


if __name__ == "__main__":
    app.run(debug=False)
