import redis
import json
from typing import Optional, Any

# Redis 클라이언트 초기화
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# TTL 설정
SESSION_TTL = 60 * 60

# 세션 키 생성 함수
def get_session_key(session_id: str) -> str:
    return f"session:{session_id}"


# 세션 초기화 함수
def init_session(session_id: str) -> dict:
    key = get_session_key(session_id)
    
    session_slots = {
        "state": None,
        "sub_state": None,
        "route": None,
        "cache_dep": None,
        "cache_dest": None,
        "dest_name": None,
        "dest_coord": None,
        "dep_name": None,
        "dep_coord": None,
        "user_gps": [],
        "message_history": [],
        "history_main_step": [],
        "history_set_dest_step": [],
        "history_set_dep_step": [],
        "history_dest": [],
        "history_dep": [],
        "error_flag": False,
        "bus": {},
    }

    redis_client.set(key, json.dumps(session_slots), ex=SESSION_TTL)
    return session_slots


# 세션 가져오기 함수
def get_session(session_id: str) -> Optional[dict]:
    key = get_session_key(session_id)
    data = redis_client.get(key)
    return json.loads(data) if data else None


# 세션을 가져오거나 생성하는 함수
def get_or_create_session(session_id: str) -> dict:
    session = get_session(session_id)
    if session is not None:
        return session
    return init_session(session_id)


# 세션 업데이트 함수
def update_session(session_id: str, session_data: dict):
    key = get_session_key(session_id)
    redis_client.set(key, json.dumps(session_data), ex=SESSION_TTL)


# 세션 삭제 함수
def delete_session(session_id: str):
    key = get_session_key(session_id)
    redis_client.delete(key)





# 슬롯 가져오기 함수
def get_slot(session_id: str, key: str) -> Optional[Any]:
    session = get_session(session_id)
    return session.get(key) if session else None


# 슬롯 설정 함수
def set_slot(session_id: str, key: str, value: Any):
    session = get_or_create_session(session_id)
    session[key] = value
    update_session(session_id, session)


# 슬롯 삭제 함수
def delete_slot(session_id: str, key: str):
    session = get_session(session_id)
    if session and key in session:
        del session[key]
        update_session(session_id, session)


# 슬롯 초기화 함수
def clear_slots(session_id: str):
    update_session(session_id, init_session(session_id))
