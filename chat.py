from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
# from pydantic import BaseModel
import json
import os
from datetime import datetime


app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
# MESSAGES_FILE = "messages.json"
MESSAGES_FILE = os.path.join(BASE_DIR, "message.json")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# оставим модель закомиченной для будующих улучшений
# class Message(BaseModel):
#     username: str
#     text: str
#     time: str = datetime.now().strftime("%H:%M:%S") # нужно добавить дату (сегодня/вчера/неделю назад и т.д)

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

@app.get("/", response_class=HTMLResponse)
def get_chat(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.post("/send")
def send_message(
        username: str=Form(...),
        text: str=Form(...),
        to: str = Form(...)
):
    messages = load_messages()
    now = datetime.now()
    new_message = {
        "from": username,
        "to": to,
        "text": text,
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d")
    }
    messages.append(new_message)
    save_messages(messages)
    return {"status": "ok"}


@app.get("/messages")
def get_messages(user: str="", other: str=""):
    """Возвращает сообщения между User и Other"""
    messages = load_messages()
    if user and other:
        # Фильтрируем только диалог между User и Other
        filtered = [
            msg for msg in messages
            if (msg["from"] == user and msg["to"] == other or
                (msg["from"] == other and msg["to"] == user))
        ]
        return filtered
    return


@app.get("/users")
def get_users():
    """Возвращает список всех, кто писал сообщения"""
    messages = load_messages()
    users = set()
    for msg in messages:
        users.add(msg["from"])
        users.add(msg["to"])
    # Убираем пустые имена
    users.discard("")
    return {"users": sorted(list(users))}