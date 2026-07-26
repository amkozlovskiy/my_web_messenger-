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

# Статусы пользователей (в памяти, при перезапуске сервера сбрасываюся)
user_statuses = {}  # {username: datetime}


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


@app.get("/dialogs")
def get_dialogs(user: str = ""):
    """Возвращает список диалогов для пользователя с последним сообщением"""
    if not user:
        return {"dialogs": []}

    messages = load_messages()
    dialogs = {}  # {собеседник: последнее_сообщение}

    for msg in messages:
        # Если сообщение от пользователя или ему адресовано
        if msg["from"] == user or msg["to"] == user:
            # Определяем собеседника
            other = msg["to"] if msg["from"] == user else msg["from"]
            # Пропускаем пустые имена
            if not other or other == user:
                continue

            # Сохраняем последнее сообщение (по времени)
            # Так как сообщения в списке хронологические, последнее — это самое новое
            if other not in dialogs:
                dialogs[other] = msg
            else:
                # Если это сообщение новее, чем сохранённое — обновляем
                # (используем сравнение дат/времени, если нужно, но поскольку список упорядочен, можно просто перезаписать)
                dialogs[other] = msg

    # Превращаем в список и сортируем по времени (последние сверху)
    result = []
    for other, msg in dialogs.items():
        # Определяем, прочитано ли последнее сообщение (если оно от другого пользователя)
        is_unread = (msg["from"] == other and not msg.get("read", False))
        result.append({
            "user": other,
            "last_message": {
                "text": msg["text"][:50] + ("..." if len(msg["text"]) > 50 else ""),
                "time": msg["time"],
                "date": msg["date"],
                "from": msg["from"]
            },
            "unread": is_unread
        })

    # Сортируем по дате (последние сверху)
    result.sort(key=lambda x: x["last_message"]["date"] + " " + x["last_message"]["time"], reverse=True)

    return {"dialogs": result}

@app.post("/update_status")
def update_status(username: str=Form(...)):
    """Обновляет время последнего действия пользователя"""
    from datetime import datetime
    user_statuses[username] = datetime.now()
    return {"status": "ok"}


@app.get("/statuses")
def get_statuses():
    """Возвращает статусы всех пользователей"""
    from datetime import datetime, timedelta
    now = datetime.now()
    result = {}
    for user, last_seen, in user_statuses.items():
        diff = now - last_seen
        if diff.total_seconds() < 30:
            result[user] = "online"
        elif diff.total_seconds() < 300: # 5 минут
            result[user] = f"был {diff.second // 60} мин назад"
        else:
            result[user] = "offline"
    return result
