from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_echo = os.getenv("ENV", "production").lower() != "production"

engine = create_engine(DATABASE_URL, echo=_echo)


def get_database():
    with Session(engine) as session:
        yield session
