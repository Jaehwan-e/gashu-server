from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from app.handlers.init import handle_init
from app.services.gpt import classify_state

app = FastAPI(title="Gashu Server API")

class Message(BaseModel):
    user_id: str = '0001'
    user_message: str = ''
    user_lon: str = '127.43168'
    user_lat: str = '36.62544'

@app.post("/init")
def initialize_user(msg: Message):
    print("Initializing user state...")
    print("controll by handlers.init => handle_init")
    return handle_init(msg.user_id, msg.user_message, msg.user_lon, msg.user_lat)

@app.post("/message")
def handle_message(msg: Message):
    from app.handlers.message import processing_message
    return processing_message(msg.user_id, msg.user_message, msg.user_lon, msg.user_lat)

@app.post("/test/function")
def test_endpoint(msg: Message):
    return classify_state(msg.user_id, msg.user_message)


@app.post("/test/set_dest")
def test_session(msg: Message):
    from app.handlers.set_dest import handle_set_dest
    return handle_set_dest(msg.user_id, msg.user_message)


@app.post("/test/session")
def test_session(msg: Message):
    from app.services.redis_session import get_session
    return get_session(msg.user_id)

@app.post("/test/main")
def test_main(msg: Message):
    from app.handlers.main import main
    return main(msg.user_id, msg.user_message)