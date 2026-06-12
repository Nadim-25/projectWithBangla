import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel
import sqlmodel.sql.sqltypes
from alembic import context
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Import ALL your models here so Alembic can detect them
from user.model import User
from chatbot.model import Chat, Message, Document, Test

# Alembic Config object
config = context.config

# Inject DB URL from environment
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the metadata Alembic uses for autogenerate
target_metadata = SQLModel.metadata


# ✅ Tables managed manually via pgAdmin — Alembic will ignore these
def exclude_tables(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in [
        "embeddings",
    ]:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=exclude_tables,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:                    # ✅ THIS WAS MISSING
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=exclude_tables,
            compare_type=True,            # ✅ detect column type changes
            compare_server_default=True,  # ✅ detect default value changes
        )
        with context.begin_transaction():
            context.run_migrations()


# ✅ This decides which function runs
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()



# # alembic/env.py
# import os
# from logging.config import fileConfig

# from sqlalchemy import engine_from_config, pool
# from sqlmodel import SQLModel
# import sqlmodel.sql.sqltypes
# from alembic import context
# from dotenv import load_dotenv

# # Load .env
# load_dotenv()

# # Import ALL your models here so Alembic can detect them
# from user.model import User  # Add more models as you create them
# from chatbot.model import Chat, Message, Document, Test

# # Alembic Config object
# config = context.config

# # Inject DB URL from environment
# config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# # Setup logging
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# # This is the metadata Alembic uses for autogenerate
# target_metadata = SQLModel.metadata

# # alembic/env.py

# def run_migrations_offline() -> None:
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#         include_object=exclude_tables,  # ✅ add here too
#     )
#     with context.begin_transaction():
#         context.run_migrations()


# # ✅ Add this function — list all manually managed tables here
# def exclude_tables(object, name, type_, reflected, compare_to):
#     if type_ == "table" and name in [
#         "embeddings",  # managed manually via pgAdmin SQL
#     ]:
#         return False
#     return True