from sqlmodel import create_engine, Session
from sqlalchemy import event
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_echo = os.getenv("ENV", "production").lower() != "production"

engine = create_engine(DATABASE_URL, echo=_echo)


@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    from pgvector.psycopg2 import register_vector
    register_vector(dbapi_connection)


def get_database():
    with Session(engine) as session:
        yield session
