import redis

r = redis.Redis(decode_responses=True)

def handle_set_dest(user_id, user_input):
    r.set(f"user:{user_id}:dest", user_input)

    src = r.get(f"user:{user_id}:src")
    if not src:
        r.set(f"user:{user_id}:state", STATE_MODIFY_SRC)
        return f"좋습니다. '{user_input}'로 가는 길을 안내해드릴게요.\n출발지를 알려주세요."

    r.set(f"user:{user_id}:state", STATE_MAIN)
    return "경로를 계산 중입니다..."


# handlers/add_destination.py

import json
from openai import ChatCompletion
from app.services.redis_session import set_user_destination

def handle_set_dest(user_id: str, message: str) -> str:
    """
    목적지를 설정하는 핸들러.
    사용자 메시지에서 목적지를 추출하고, 좌표와 함께 세션에 저장한 뒤 사용자에게 확인 질문을 반환.
    LLM 호출과 응답 처리까지 모두 포함한다.
    """
    # 1. LLM 프롬프트 구성
    prompt = f"""
너는 버스 경로 안내 시스템의 목적지 추출 도우미야.
다음 사용자 메시지에서 '도착지'를 한 단어로 명확히 정리해줘.
예를 들어 "서울역에 가고 싶어요" → "서울역"
응답은 반드시 JSON 형식으로 해줘: {{ "place_name": "서울역" }}
사용자 메시지: "{message}"
"""

    # 2. GPT 호출
    try:
        response = ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content
        destination = json.loads(content)  # JSON 응답 파싱

    except Exception as e:
        return "죄송해요, 목적지를 파악하는 데 문제가 생겼어요. 다시 시도해 주세요."

    # 3. 목적지 유효성 확인
    if not destination or "place_name" not in destination:
        return "죄송해요, 목적지를 잘 이해하지 못했어요. 다시 말씀해 주시겠어요?"

    # 4. Redis에 저장
    set_user_destination(user_id, destination)

    # 5. 사용자 응답
    place_name = destination["place_name"]
    return f"{place_name}(으)로 가는 경로를 안내해 드릴까요?"
