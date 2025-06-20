import redis
r = redis.Redis(decode_responses=True)

def handle_main(user_id, user_input):
    src = r.get(f"user:{user_id}:src")
    dest = r.get(f"user:{user_id}:dest")

    if not src or not dest:
        return "출발지나 목적지 정보가 부족합니다. 처음부터 다시 시작해 주세요."

    return f"{src}에서 {dest}까지 가는 버스를 안내해드릴게요. 🚌"
