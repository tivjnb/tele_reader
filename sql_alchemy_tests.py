from sqlalchemy import URL, create_engine, text, Table, Column, Integer, String, DATETIME, MetaData, insert

metadat_obj = MetaData()

workers_table = Table(
    'workers',
    metadat_obj,
    Column('id', Integer, primary_key=True),
    Column('user_name', String)
)

engine = create_engine(
    url=f"mssql+pymssql://user2:1234@DESKTOP-BJCKQAH/ms_sql_db",
    echo=True
)

with engine.connect() as conn:
    pass


def creator():
    engine.echo = False
    metadat_obj.create_all(engine)
    engine.echo = True

def insector():
    with engine.connect() as conn:
        stmt = insert(workers_table).values(
            [
                {"user_name": '123'},
                {"user_name": "311"}
            ]
        )
        conn.execute(stmt)
        conn.commit()


#creator()
#insector()