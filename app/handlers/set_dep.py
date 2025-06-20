from app.states import STATE_MAIN
import redis

r = redis.Redis(decode_responses=True)

def handle_set_dep(user_id, user_input):
    r.set(f"user:{user_id}:src", user_input)
    r.set(f"user:{user_id}:state", STATE_MAIN)
    return f"출발지를 '{user_input}'로 설정했습니다. 경로 안내를 시작합니다."
