from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import os
from datetime import datetime


app = FastAPI()
templates = Jinja2Templates(directory="templates")

MESSAGES_FILE = "messages.json"


class Message(BaseModel):
    username: str
    text: str
    time: str = datetime.now().strftime("%H:%M:%S") # нужно добавить дату (сегодня/вчера/неделю назад и т.д)

def load_messages():
    if not os.path.exists(MESSAGES_FILE): # что значит эта команда?
        return []
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f) # что делает эта команда

def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2) # что делает эта команда?

@app.get("/", response_class=HTMLResponse) # почему здесь "/" и что такое response_class=HTMLResponse и зачем оно здесь?
def get_chat(request: Request): # почему здесь такой параметр
    return templates.TemplateResponse(request, "chat.html")

# @app.get("/", response_class=HTMLResponse)
# def get_chat(request: Request):
#     return templates.TemplateResponse(name="test.html", request=request)

@app.post("/send")
def send_message(username: str=Form(...), text: str=Form(...)): # почему здесь точки Form(...)?
    messages = load_messages()
    new_message = {
        "username": username,
        "text": text,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    messages.append(new_message)
    save_messages(messages)
    return {"status": "ok"}


@app.get("/messages") # что такое /messages?
def get_messages():
    return load_messages()