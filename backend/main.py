from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.router import user_router
from upload.router import upload_router
from chatbot.processchunk import process_router
from chatbot.chatrouter import chat_router
import os

app = FastAPI()

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
