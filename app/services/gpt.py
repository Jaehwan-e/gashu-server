from app.services.redis_session import delete_session, init_session, get_session, update_session

from openai import OpenAI
import os
import json

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------------------------------------------------------
# 대화 기록 test 데이터 삭제할 것
def classify_state(user_id: str, user_message: str) -> dict:
    session = get_session(user_id)
    prompt = f"""
사용자와의 대화 기록을 기반으로 대화 흐름과 사용자의 의도를 파악한 뒤, 다음 항목들을 판단하여 JSON 형식으로 반환해줘:

1. 현재 상태를 "set_dep", "set_dest", "main", "error" 중 하나로 분류해줘.
    - "set_dep": 사용자가 출발지를 설정하는 단계
    - "set_dest": 사용자가 목적지를 설정하는 단계
    - "main": 출발지와 목적지가 결정된 상태로 버스 정보를 안내하는 단계
    - "error": 사용자의 메시지가 버스 정보 안내와 무관한 경우
2. 사용자 메시지에서 **출발지(dep)**와 **목적지(dest)**를 추출해줘. 문장에 명시되지 않았다면 null로 설정해.
3. assistant가 출발지/목적지의 **선택지를 제공하거나 확인을 요청했고**, 사용자 메시지가 **제공한 내용 중에 응답하는 형태(선택/확인)**라면,
   - 출발지인 경우: "requires_dep_coord": true
   - 목적지인 경우: "requires_dest_coord": true
4. 사용자의 메시지가 **버스 정보 안내와 무관한 일반적인 발화**(예: 잡담, 다른 주제)라면 "error": true로 설정해. 
   그 외에는 false로 설정해.

아래 JSON 형식 외의 **어떠한 설명, 주석, 코드블럭(예: ```)도 포함하지 마.** 반드시 JSON 객체로 시작하고 끝나야 해.

사용자 메시지: "{user_message}"

출력 형식 예시:
{{
  "state": "set_dest" 또는 "set_dep" 또는 "main" 또는 "error",
  "dep": "출발지명 또는 null",
  "dest": "목적지명 또는 null",
  "requires_dep_coord": true 또는 false,
  "requires_dest_coord": true 또는 false,
  "error": true 또는 false
}}
""".strip()
    
    messages=[{
        "role": "system", "content": "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."
        }] + session.get("message_history", []) + [{"role": "user", "content": prompt}]
    session["message_history"] = session.get("message_history", []) + [{"role": "user", "content": user_message}]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "너는 대화의 흐름을 이해하고 사용자의 입력에서 출발지와 목적지를 추출해서 JSON 형태로 반환하는 도우미야."}
            ] + session.get("message_history", []) + [
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        print(f"classify_state... GPT 응답: {content}")
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            print("JSON 파싱 실패")
            result = {"state": "main", "sub_state": "main", "dep": None, "dest": None}


        # 결과에 따른 세션 값 업데이트
        if result.get("dep", False):
            session["requested_dep"] = result["dep"]
            session["state"] = "set_dep"
            session["sub_state"] = "search"
            if result.get("requires_dep_coord", False):
                session["requires_dep_coord"] = True
                session["sub_state"] = "coord"
        if result.get("dest", False):
            session["requested_dest"] = result["dest"]
            session["state"] = "set_dest"
            session["sub_state"] = "search"
            if result.get("requires_dest_coord", False):
                session["requires_dest_coord"] = True
                session["sub_state"] = "coord"
        if result.get("error", False):
            session["error_flag"] = True
            session["state"] = "error"
        session['state'] = result.get("state", session["state"])

        # 레디스 세션 업데이트
        update_session(user_id, session)

        return result

    except Exception as e:
        print(f"gpt api 호출 중 에러: {e}")
        return {"departure": None, "destination": None}
