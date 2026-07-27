from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
def make_engine(url=None):
    url=url or get_settings().database_url
    return create_engine(url, connect_args={"check_same_thread":False} if url.startswith("sqlite") else {}, pool_pre_ping=True)
engine=make_engine()
SessionLocal=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
