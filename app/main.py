from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from app.handlers.init import handle_init
from app.services.gpt import classify_state

app = FastAPI(title="Gashu Server API")

class Message(BaseModel):
    user_id: str = '0001'
    user_message: Optional[str] = ''
    user_lon: Optional[float] = 127.43168
    user_lat: Optional[float] = 36.62544

@app.post("/init")
def initialize_user(msg: Message):
    print("Initializing user state...")
    print("controll by handlers.init => handle_init")
    return handle_init(msg.user_id, msg.user_message, msg.user_lon, msg.user_lat)

@app.post("/message")
def handle_message(msg: Message):
    return {}

@app.post("/test")
def test_endpoint(msg: Message):
    return classify_state(msg.user_id, msg.user_message)