from app.handlers.set_dep import handle_set_dep
from app.handlers.set_dest import handle_set_dest
from app.services.gpt import classify_state

from app.services.redis_session import get_session, update_session, set_slot, get_slot
from app.services.apis import fetch_realtime_bus_info, fetch_bus_directions

import os
import json
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



def main(user_id, user_input):
    state = classify_state(user_id, user_input).get("state", "error")
    while True:
        if state == "set_dest":
            return handle_set_dest(user_id, user_input)
        
        elif state == "set_dep":
            return handle_set_dep(user_id, user_input)
        
        elif state == "main":
            return handle_main(user_id, user_input)
        
        else:
            return {"message": "죄송하지만 버스 관련 정보만 안내해 드릴 수 있어요."}



def handle_main(user_id, user_message):
    dep_coord = get_slot(user_id, "dep_coord")
    dest_coord = get_slot(user_id, "dest_coord")

    if not dest_coord:
        set_slot(user_id, "state", "set_dest")
        set_slot(user_id, "sub_state", "coord")

    elif not dep_coord:
        set_slot(user_id, "state", "set_dep")
        set_slot(user_id, "sub_state", "coord")

    else:
        route_info = get_slot(user_id, "route")
        if not route_info:
            route_info = fetch_bus_directions(dep_coord, dest_coord)
            set_slot(user_id, "route", route_info)
            if not route_info:
                message = "죄송해요, 해당 경로에 대한 버스 정보를 찾을 수 없어요. 출발지와 목적지를 다시 확인해 주세요."
                return {"message": message}
        
        else:
            # 이미 경로 정보가 있는 경우, llm을 통해 대화형식으로 경로를 안내하고, 원하는 버스 정보를 추출해 실시간 버스 정보를 가져옵니다.
            system_prompt = """
너는 버스 정보 안내 도우미야. 사용자와의 대화 기록과 경로 데이터를 참고해 자연스럽고 정확하게 실시간 버스 정보를 안내하는 역할을 수행해야 해.

- 최초 경로 안내는 최단시간의 경로를 요약해 주고, 추가적으로 도보이동이 적은 경로나 환승하지 않는 경로 등을 추천할 수 있어.
- 사용자의 요청이 실시간 버스 정보와 관련이 있다면, 메시지를 생성하지 않고 버스번호(routeno)와 출발 정류장ID(nodeid)를 반환해야 해.
- 실시간 요청이 아닌 경우, routeno와 nodeid는 절대 추출하지 말고 자연스러운 message만 생성해야 해.
- 항상 JSON 형식으로만 응답해야 하고, 설명이나 코드블럭은 포함하면 안 돼.
"""
            prompt = f"""
너는 버스 정보 안내 도우미야. 사용자와의 대화 기록을 참고해 자연스럽고 정확하게 버스 정보를 안내해야 해.

다음 조건을 반드시 지켜:

1. 사용자가 **실시간 버스 정보**를 요청한 경우:
    - 사용자에게 보여줄 메시지를 생성하지 마.
    - 대신, 주어진 경로 검색 결과(route_info)에서 해당하는 버스번호(routeno)와 출발 정류장 ID(start_nodeid)를 찾아 반환해.
    - 이 경우 message는 null이어야 하고, routeno와 nodeid는 실제 값으로 채워야 해.

2. 사용자가 실시간 정보를 요청하지 않은 경우:
    - 사용자와 자연스럽게 이어지는 안내 메시지를 message에 생성해.
    - 이 경우 routeno와 nodeid는 **반드시 null로 설정해야 해.** (값을 추출하지 마.)

출력 형식은 반드시 다음 JSON 구조를 그대로 따라야 해.
- 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
- **추가적인 설명, 주석, 코드 블럭, 따옴표 없는 텍스트 등은 절대 포함하지 마.**

경로 검색 결과: {route_info}

실시간 버스 정보 요청 여부: 사용자 발화에 따라 판단

출력 형식:
{{
  "message": "사용자에게 보여줄 메시지 또는 null",
  "routeno": "사용자가 선택한 버스번호 또는 null",
  "nodeid": "사용자가 선택한 정류장id 또는 null"
}}
""".strip()

            session = get_session(user_id)
            messages=[{
                "role": "system", "content": system_prompt
                }] + session.get("message_history", []) + [{"role": "user", "content": prompt}]
            session["message_history"] = session.get("message_history", []) + [{"role": "user", "content": user_message}]

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.0,
                )

                content = response.choices[0].message.content
                print(f"main_state... GPT 응답: {content}")
                
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    print("JSON 파싱 실패")
                    result = {"state": "main", "sub_state": "main", "dep": None, "dest": None}


                # 결과에 따른 세션 값 업데이트
                if result.get("routeno") and result.get("nodeid"):
                    # 실시간 버스 정보 요청인 경우
                    set_slot(user_id, "bus", get_slot(user_id, "bus", []) + [{"routeno": result["routeno"], "nodeid": result["nodeid"]}])

            except Exception as e:
                print(f"gpt api 호출 중 에러: {e}")
                return {"departure": None, "destination": None}



    return main(user_id, user_message)