from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_echo = os.getenv("ENV", "production").lower() != "production"

engine = create_engine(
    DATABASE_URL,
    echo=_echo,
    pool_pre_ping=True,   # test connection before use — detects stale SSL connections
    pool_recycle=300,     # recycle idle connections after 5 minutes
)


def get_database():
    with Session(engine) as session:
        yield session
