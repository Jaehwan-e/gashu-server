import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.redis_session import delete_session, init_session, get_session, update_session, get_slot, set_slot

from app.services.apis import search_address_by_keyword, geocode_address

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."

def update_user_history(user_id, message):
    """히스토리 업데이트 헬퍼 함수"""
    for key in ["message_history", "history_set_dep_step"]:
        history = get_slot(user_id, key)
        history.append({"role": "assistant", "content": message})
        set_slot(user_id, key, history)

def handle_set_dep(user_id: str, user_message: str) -> dict:
    set_slot(user_id, "history_set_dep_step", get_slot(user_id, "history_set_dep_step") + [{"role": "user", "content": user_message}])

    while get_slot(user_id, "state") == "set_dep":
        sub_state = get_slot(user_id, "sub_state")
        session = get_session(user_id)

        if sub_state == "main":
            prompt = f"""
사용자와의 자연스러운 대화를 통해 출발지를 설정할 거야.
먼저, 사용자의 현재 위치에서 출발할 것인지 아니면 다른 출발지를 설정할 것인지 물어봐야 해. 현재 위치에서 출발할 것이라면 use_gps=True로 설정하고, 다른 출발지를 설정할 것이라면 use_gps=False로 설정해.
출발지를 따로 설정할 것이라면 주어진 출발지 검색 결과가 있다면 참고해 사용자와의 대화를 통해 원하는 하나의 출발지를 결정해 반환해야 해.
사용자에게 대화 형식의 자연스러운 응답을 생성해.
반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
추가적인 설명, 주석, 코드 블럭 없이 딱 JSON만 출력해.

사용자 메시지: "{user_message}"
출발지 검색 결과: {session.get("dep_search_results", [])}

출력 형식:
{{
    "message": "사용자에게 보여줄 메시지",
    "dep": "사용자가 선택한 출발지명 또는 null",
    "dep_address": "사용자가 선택한 출발지 주소 또는 null"
    "use_gps": true 또는 false
}}""".strip()

            try:
                messages = (
                    [{"role": "system", "content": SYSTEM_PROMPT}]
                    + session.get("message_history", [])
                    + [{"role": "user", "content": prompt}]
                )
                session["message_history"] = session.get("message_history", []) + [{"role": "user", "content": user_message}]
                update_session(user_id, session)  # 변경된 히스토리 반영

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.0,
                )
                content = response.choices[0].message.content
                print(f"set_dep에서 GPT 응답: {content}")

                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    print("JSON 파싱 실패")
                    result = {"message": "죄송해요, 다시 한 번 말씀해 주세요.", "dep": None, "dep_address": None}

                update_user_history(user_id, result["message"])
                if result.get("use_gps", False):
                    set_slot(user_id, "dep_coord", session.get("user_gps", []))

                if result["dep"] and result["dep_address"]:
                    set_slot(user_id, "dep_name", result["dep"])
                    set_slot(user_id, "dep_address", result["dep_address"])
                    set_slot(user_id, "sub_state", "coord")
                    continue  # 좌표 변환 단계로 이동

                return {"message": result["message"]}

            except Exception as e:
                print(f"GPT 호출 중 에러: {e}")
                return {"message": "죄송해요, 내부 오류가 발생했어요."}

        elif sub_state == "search":
            requested_dep = get_slot(user_id, "requested_dep")
            if requested_dep == "현재 위치":
                # 현재 위치에서 출발하는 경우
                coord = get_slot(user_id, "user_gps")
                if coord:
                    set_slot(user_id, "dep_coord", coord)
                    continue
                
            search_result = search_address_by_keyword(requested_dep)

            if not search_result:
                message = "죄송해요, 해당 출발지를 찾을 수 없어요. 다른 장소나 주소를 말씀해 주세요."
                update_user_history(user_id, message)
                set_slot(user_id, "sub_state", "main")
                return {"message": message}

            set_slot(user_id, "dep_search_results", search_result)

            if len(search_result) == 1:
                result = search_result[0]
                message = f"검색된 출발지는 '{result['name']}' ({result['address']})입니다. 이 주소가 맞나요?"
            else:
                message = "여러 개의 출발지가 검색되었어요. 원하는 출발지를 선택해 주세요:\n"
                message += "\n".join(
                    f"{idx+1}번. {r['name']} ({r['address']})" for idx, r in enumerate(search_result)
                )

            update_user_history(user_id, message)
            return {"message": message}

        elif sub_state == "coord":
            dep_address = get_slot(user_id, "dep_address")
            if dep_address:
                coord = geocode_address(dep_address)
                if coord:
                    set_slot(user_id, "dep_coord", coord)
                    set_slot(user_id, "state", "main")
                    set_slot(user_id, "sub_state", "main")
                    set_slot(user_id, "enable_main", True)
                    import app.handlers.main as main_handler
                    return main_handler.handle_main(user_id, user_message)
                    
                else:
                    message = "좌표를 찾을 수 없어요. 출발지를 다시 알려주세요."
                    update_user_history(user_id, message)
                    return {"message": message}
            else:
                print("출발지 주소가 없습니다. 출발지를 알려주세요.")
                set_slot(user_id, "state", "error")

    return {"message": "set_dep 함수 비정상 종료: 출발지 설정이 완료되지 않았습니다."}
