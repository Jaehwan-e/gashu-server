from app.services.redis_session import delete_session, init_session, get_session, update_session

from openai import OpenAI
import os
import json

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_state(user_id: str, user_message: str) -> dict:
    session = get_session(user_id)
    prompt = f"""
사용자와의 대화 기록을 통해 대화의 흐름과 사용자의 의도를 파악해 진행해야 할 상태를 주어진 상태 중 하나로 분류하고, 
사용자 메시지에서 출발지와 목적지를 찾아 반환해줘. 문장에 출발지나 목적지가 없으면 null로 설정해.
반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
추가적인 설명, 주석, 코드 블럭(```) 없이 딱 JSON만 출력해.

대화 기록: {session.get("message_history", [
    {"role": "user", "content": "710번 언제와"},
    {"role": "assistant", "content": "710번 버스는 5분 10초 뒤에 옵니다."},
])}
사용자 메시지: "{user_message}"

출력 형식:
{{
    "state": "목적지를 설정 또는 수정한다면 'set_dest", 출발지를 설정 또는 수정한다면 "set_dep", 나머지의 경우 "main",
    "sub_state": "state가 set_dest 또는 set_dep인 경우에 dep이나 dest가 채워졌다면 'search', 아니면'main'",
    "dep": "출발지명 또는 null",
    "dest": "목적지명 또는 null"
}}
    """.strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        print(f"GPT 응답: {content}")
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            print("❌ JSON 파싱 실패")
            result = {"state": "main", "sub_state": "main", "dep": None, "dest": None}
        return result

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return {"departure": None, "destination": None}
