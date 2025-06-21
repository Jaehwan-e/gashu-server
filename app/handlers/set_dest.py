import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.redis_session import delete_session, init_session, get_session, update_session, get_slot, set_slot

from app.handlers.set_dep import handle_set_dep
from app.services.apis import search_address_by_keyword, geocode_address

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."


def update_user_history(user_id, message):
    """히스토리 업데이트 헬퍼 함수"""
    for key in ["message_history", "history_set_dest_step"]:
        history = get_slot(user_id, key)
        history.append({"role": "assistant", "content": message})
        set_slot(user_id, key, history)


def build_prompt(user_message, dest_results):
    """프롬프트 구성 함수"""
    return f"""
사용자와의 자연스러운 대화를 통해 목적지를 설정하는 단계에서
주어진 목적지 검색 결과가 있다면 참고해 사용자와의 대화를 통해 원하는 하나의 목적지를 결정해 반환해야 해.
사용자에게 대화 형식의 자연스러운 응답을 생성해.
반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
추가적인 설명, 주석, 코드 블럭 없이 딱 JSON만 출력해.

사용자 메시지: "{user_message}"
목적지 검색 결과: {dest_results}

출력 형식:
{{
    "message": "사용자에게 보여줄 메시지",
    "dest": "사용자가 선택한 목적지명 또는 null",
    "dest_address": "사용자가 선택한 목적지 주소 또는 null"
}}""".strip()


def handle_set_dest(user_id: str, user_message: str) -> str:
    set_slot(user_id, "history_set_dest_step", get_slot(user_id, "history_set_dest_step") + [{"role": "user", "content": user_message}])

    while get_slot(user_id, "state") == "set_dest":
        sub_state = get_slot(user_id, "sub_state")
        session = get_session(user_id)

        if sub_state == "main":
            prompt = build_prompt(user_message, session.get("dest_search_results", []))

            try:
                messages = (
                    [{"role": "system", "content": SYSTEM_PROMPT}]
                    + session.get("message_history", [])
                    + [{"role": "user", "content": prompt}]
                )
                session["message_history"] = session.get("message_history", []) + [{"role": "user", "content": user_message}]
                update_session(user_id, session)

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.0,
                )
                content = response.choices[0].message.content
                print(f"set_dest에서 GPT 응답: {content}")

                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    print("JSON 파싱 실패")
                    result = {"message": "죄송해요, 다시 한 번 말씀해 주세요.", "dest": None, "dest_address": None}

                update_user_history(user_id, result["message"])

                if result["dest"] and result["dest_address"]:
                    set_slot(user_id, "dest_name", result["dest"])
                    set_slot(user_id, "dest_address", result["dest_address"])
                    set_slot(user_id, "sub_state", "coord")
                    continue  # 좌표 변환 단계로

                return {"message": result["message"]}

            except Exception as e:
                print(f"GPT 호출 중 에러: {e}")
                return {"message": "죄송해요, 내부 오류가 발생했어요."}

        elif sub_state == "search":
            # 결과가 없다면 검색 시도
            requested_dest = get_slot(user_id, "requested_dest")
            search_result = search_address_by_keyword(requested_dest)

            if not search_result:
                message = "죄송해요, 해당 목적지를 찾을 수 없어요. 다른 장소나 주소를 말씀해 주세요."
                update_user_history(user_id, message)
                set_slot(user_id, "sub_state", "main")
                return {"message": message}

            set_slot(user_id, "dest_search_results", search_result)

            if search_result:
                if len(search_result) == 1:
                    result = search_result[0]
                    message = f"검색된 목적지는 '{result['name']}' ({result['address']})입니다. 이 주소가 맞나요?"
                else:
                    message = "여러 개의 목적지가 검색되었어요. 원하는 목적지를 선택해 주세요:\n"
                    message += "\n".join(
                        f"{idx+1}번. {r['name']} ({r['address']})" for idx, r in enumerate(search_result)
                    )
                
                update_user_history(user_id, message)
                return {"message": message}


        elif sub_state == "coord":
            # 좌표 변환 단계
            dest_address = get_slot(user_id, "dest_address")
            if dest_address:
                coord = geocode_address(dest_address)
                if coord:
                    set_slot(user_id, "dest_coord", coord)
                    set_slot(user_id, "state", "set_dep")

                    if get_slot(user_id, "requested_dep"):
                        set_slot(user_id, "sub_state", "search")
                    else:
                        message = "현재 위치에서 출발하시겠어요? 아니면 출발지를 알려주세요"
                        set_slot(user_id, "history_set_dep_step", get_slot(user_id, "history_set_dep_step") + [{"role": "assistant", "content": message}])
                        set_slot(user_id, "message_history", get_slot(user_id, "message_history") + [{"role": "assistant", "content": message}])
                        return {"message": message}

                else:
                    message = "좌표를 찾을 수 없어요. 주소를 다시 확인해 주세요."
                    update_user_history(user_id, message)
                    return {"message": message}
            else:
                print("좌표 변환 단계에서 주소가 없습니다.")
                set_slot(user_id, "state", "error")

    # 목적지 설정 완료 후 출발지 단계로
    return {"message": "set_dest 함수 비정상 종료: 목적지 설정이 완료되지 않았습니다."}
