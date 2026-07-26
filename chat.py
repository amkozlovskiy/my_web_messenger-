from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
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

class EditData(BaseModel):
    new_text: str

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
        username: str = Form(...),
        text: str = Form(...),
        to: str = Form(...)
):
    messages = load_messages()
    now = datetime.now()
    new_message = {
        "from": username,
        "to": to,
        "text": text,
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "edited": False,
        "read": False
    }
    messages.append(new_message)
    save_messages(messages)
    return {"status": "ok"}


@app.get("/messages")
def get_messages(user: str = "", other: str = ""):
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
    return messages


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


@app.put("/messages/read")
def mark_as_read(user: str = "", other: str = ""):
    """Отмечает все сообщения от other к user как прочитанные"""
    if not user or not other:
        return {"status": "error", "message": "Не указаны пользователи"}

    messages = load_messages()
    updated = 0
    for msg in messages:
        if msg["from"] == other and msg["to"] == user and not msg.get("read", False):
            msg["read"] = True
            updated += 1
    save_messages(messages)
    return {"status": "ok", "updated": updated}

@app.put("/messages/{index}")
def edit_message(index: int, edit_data: EditData, user: str=""):
    """Редактирует сообщение по индексу (только если это
    сообщение пользователя)"""
    messages = load_messages()
    if index < 0 or index >= len(messages):
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    msg = messages[index]
    # Проверяем, что сообщение принадлежит пользователю
    if user and msg["from"] != user:
        raise HTTPException(status_code=403, detail="Нельзя редактировать чужое сообщение")

    # Редактируем текст
    messages[index]["text"] = edit_data.new_text
    #Добавляем метку, что сообщение отредактировано
    messages[index]["edited"] = True
    save_messages(messages)
    return {"status": "ok"}


@app.get("/unread_count")
def get_unread_count(user: str = ""):
    """Возвращает количество непрочитанных сообщений для пользователя"""
    messages = load_messages()
    if not user:
        return {"total": 0, "by_user": {}}

    unread_by_user = {}
    total = 0
    for msg in messages:
        # Если сообщение адресовано текущему пользователю и не от него
        if msg["to"] == user and msg["from"] != user and not msg.get("read", False):
            total += 1
            unread_by_user[msg["from"]] = unread_by_user.get(msg["from"], 0) + 1

    return {"total": total, "by_user": unread_by_user}


@app.get("/last_message_id")
def get_last_message_id():
    """Возвращает ID последнего сообщения (для проверки новых)"""
    messages = load_messages()
    if not messages:
        return {"last_id": 0}
    # Используем индекс последнего сообщения как ID
    return {"last_id": len(messages) - 1}


@app.delete("/messages/{index}")
def delete_message(index: int, user: str = ""):
    """Удаляет сообщение по индексу (только если оно принадлежит пользователю)"""
    messages = load_messages()
    if index < 0 or index >= len(messages):
        raise HTTPException(status_code=404, detail="Сообщение не найдено")

    msg = messages[index]
    if user and msg["from"] != user:
        raise HTTPException(status_code=403, detail="Нельзя удалять чужое сообщение")

    # Удаляем сообщение из списка
    deleted_msg = messages.pop(index)
    save_messages(messages)
    return {"status": "ok", "deleted": deleted_msg}
