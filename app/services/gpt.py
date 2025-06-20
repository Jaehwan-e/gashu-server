from app.services.redis_session import delete_session, init_session, get_session, update_session

import openai
from dotenv import load_dotenv
load_dotenv()


def extract_locations_from_text(user_id: str, user_message: str) -> dict:
    session = get_session(user_id)

    system_prompt = """
너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야.
    출발지와 목적지는 대화의 흐름에 따라 사용자가 언급한 장소를 의미해.
    만약 사용자가 출발지나 목적지를 언급하지 않았다면, 해당 값은 null로 설정해줘.
    예를 들어, 사용자가 "청주에서 청주대까지 가는 버스를 알려줘"라고 말하면,
    출발지는 "청주", 목적지는 "청주대"가 될 거야.
    만약 사용자가 "청주에서 어디로 가야할지 모르겠어"
    라고 말하면, 출발지는 "청주", 목적지는 null이 될 거야.
    """.strip()
    prompt = f"""
사용자와의 대화 기록을 통해 대화의 흐름과 사용자의 의도를 파악해 현재 상태를 주어진 상태 중 하나로 분류하고, 
사용자 메시지에서 출발지와 목적지를 찾아 반환해줘. 문장에 출발지나 목적지가 없으면 null로 설정해.
반환 형식은 다음과 같은 JSON 형식이어야 해.

대화 기록: {session.get("message_history", [])}
사용자 메시지: "{user_message}"

출력 형식:
{{
    "state": "set_dest" 또는 "set_dep" 또는 "init" 또는 "main",
    "departure": "출발지명 또는 null",
    "destination": "목적지명 또는 null"
}}
    """.strip()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        # 응답에서 JSON 파싱
        content = response["choices"][0]["message"]["content"]
        result = eval(content) if isinstance(content, str) else content
        return result

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return {"departure": None, "destination": None}
