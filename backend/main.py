from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from sqlalchemy import text
from user.router import user_router
from upload.router import upload_router
from chatbot.processchunk import process_router
from chatbot.chatrouter import chat_router
from utils.database import engine
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all SQLModel-managed tables (users, chat, message, document, etc.)
    SQLModel.metadata.create_all(engine)

    # Enable pgvector extension and create embeddings table
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id          SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES document(id) ON DELETE CASCADE,
                    content     TEXT NOT NULL,
                    embedding   vector(1536),
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            # IVFFlat index — skip silently if table is empty (needs data first)
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS embeddings_embedding_cosine_idx
                    ON embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
            except Exception as e:
                print(f"[startup] Skipping IVFFlat index (will create after data is added): {e}")
            conn.commit()
    except Exception as e:
        print(f"[startup] pgvector setup warning: {e}")
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add production frontend URL from env (set on Render after Vercel deploy)
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def homePage():
    return "Home Page"


app.include_router(user_router, prefix="/user")
app.include_router(upload_router, prefix="/upload")
app.include_router(process_router, prefix="/process")
app.include_router(chat_router)
