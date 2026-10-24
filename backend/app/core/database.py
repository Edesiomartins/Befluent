from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
def make_engine(url=None):
    url=url or get_settings().database_url
    if url.startswith("sqlite"):
        # O SQLite local serializa escritas. Sem espera, duas requisições
        # seguidas (cronograma e sessão) derrubam a segunda com "database is locked".
        engine=create_engine(url, connect_args={"check_same_thread":False, "timeout":30}, pool_pre_ping=True)
        @event.listens_for(engine, "connect")
        def _sqlite_connect(dbapi_connection, _connection_record):
            # Autocommit no DBAPI: o BEGIN passa a ser o nosso, imediato.
            # Sem isso, duas requisições leem juntas e a segunda falha na hora
            # ao tentar virar escrita, sem respeitar o busy timeout.
            dbapi_connection.isolation_level = None
            cursor=dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        @event.listens_for(engine, "begin")
        def _sqlite_begin(connection):
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        return engine
    return create_engine(url, pool_pre_ping=True)
engine=make_engine()
SessionLocal=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
