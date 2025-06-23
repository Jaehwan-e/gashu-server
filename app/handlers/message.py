from app.services.apis import search_address_by_keyword, fetch_bus_directions, fetch_realtime_bus_info, fetch_realtime_node_info

from openai import OpenAI
import os
import json

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def processing_message(user_id: str, user_message: str, user_lon: str, user_lat: str) -> dict:
    prompt = f"""
사용자 요청을 다음 세 가지 중 하나로 분류하고, 메시지에서 목적지를 추출해 JSON 형식으로 반환해줘:
- specific_bus_info: **특정 목적지**에 가는 **특정 번호**의 버스 정보 요청
- general_bus_info: **특정 목적지**에 가는 버스 정보(경로) 요청
- null: 1, 2에 해당하지 않는 모든 경우
반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
아래 JSON 형식 외의 **어떠한 설명, 주석, 코드블럭(예: ```)도 포함하지 마.** 반드시 JSON 객체로 시작하고 끝나야 해.

사용자 메시지: "{user_message}"

출력 형식 예시:
{{
    "request_type": "specific_bus_info" 또는 "general_bus_info" 또는 "null",
    "dest": "목적지 또는 null",
    "bus_no": "버스 번호 또는 null",
}}
""".strip()
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "사용자 요청의 타입을 분류하고, 메시지에서 목적지를 추출해 JSON 형식으로 반환하는 도우미야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        print(f"user 요청: {user_message}")
        print(f"gpt 응답: {content}")
        
        try:
            result = json.loads(content)

        except json.JSONDecodeError:
            print("JSON 파싱 실패")
            result = {
                "message": "죄송해요, 서버에 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
                "error": "GPT 응답 JSON 파싱 실패"
            }

        request_type = result.get("request_type")
        dest = result.get("dest", None)
        searched_dest = search_address_by_keyword(dest)
        if not searched_dest:
            return {"message": "죄송해요, 말씀하신 목적지를 찾을 수 없어요. 다시 시도해주세요."}
        dep_coord = (user_lon, user_lat)
        dest_coord = (searched_dest[0].get("lon"), searched_dest[0].get("lat"))
        dest_name = searched_dest[0].get("name")
        bus_no = result.get("bus_no", None)

        if request_type == "specific_bus_info":
            directions = fetch_bus_directions(dep_coord, dest_coord)
            if not directions:
                message = f"죄송해요, {searched_dest[0].get('name')}에 가는 {bus_no}번 버스의 정보를 찾을 수 없어요. 잠시 후 다시 시도해주세요."
                return {"message": message}
            
            specific_bus_info_prompt = f"""
다음 경로 정보에 사용자가 요청한 버스 노선(route_name) 정보가 있는지 확인하고 있다면 버스의 노선아이디(routeid)와 출발 정류장 아이디(start_nodeid)를 찾아 반환해. 없다면 null로 설정해.

사용자 요청 버스 번호: {bus_no}
경로 정보: {directions}

반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
아래 JSON 형식 외의 **어떠한 설명, 주석, 코드블럭(예: ```)도 포함하지 마.** 반드시 JSON 객체로 시작하고 끝나야 해.
출력 형식:
{{
    "routeid": "버스 노선 아이디 또는 null"
    "start_nodeid": "출발 정류장 아이디 또는 null"
}}
""".strip()
            print("특정 버스 정보 요청 프롬프트:", specific_bus_info_prompt)
            messages = [
                {"role": "system", "content": "버스 노선 아이디를 추출하는 도우미야."},
                {"role": "user", "content": specific_bus_info_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.0,
            )
            content = response.choices[0].message.content
            print(f"특정 버스 정보 요청 gpt응답: {content}")

            result = json.loads(content)
            routeid = result.get("routeid", None)
            nodeid = result.get("start_nodeid", None)
            if not nodeid:
                message = f"죄송해요, {searched_dest[0].get('name')}에 가는 {bus_no}번 버스의 노선 정보를 찾을 수 없어요. 다시 시도해주세요."
                return {"message": message}
            print(f"추출된 버스 노선 아이디: {routeid}, 시작 정류장 아이디: {nodeid}")
            # 실시간 버스 정보 가져오기
            realtime_node_info = fetch_realtime_node_info(nodeid)
            if not realtime_node_info:
                message = f"죄송해요, {searched_dest[0].get('name')}에 가는 {bus_no}번 버스의 출발 정류장 정보를 찾을 수 없어요. 다시 시도해주세요."
                return {"message": message}
            
            realtime_bus_info_prompt = f"""
다음 실시간 버스 정보를 분석해 사용자가 요청한 버스 노선정보가 존재한다면 is_exist를 true로 설정하고, 다음과 같은 형식의 message를 생성해줘. 
사용자가 요청한 버스 노선정보가 존재하지 않는다면 is_exist를 false로 설정해.

예시 message: "<dest_name>에 가는 <bus_no>번 버스가 <nodenm> 정류장에 <arrival_time> 뒤에 도착해요. <arrprevstationcnt> 정거장 남았어요."

실시간 버스 정보: {realtime_node_info}
사용자 요청 노선 번호: {bus_no}
목적지 이름: {dest_name}

반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
아래 JSON 형식 외의 **어떠한 설명, 주석, 코드블럭(예: ```)도 포함하지 마.** 반드시 JSON 객체로 시작하고 끝나야 해.
출력 형식:
{{
    "is_exist": true 또는 false,
    "message": "사용자에게 보여줄 메시지 또는 null"
}}
"""
            print("실시간 버스 정보 요청 프롬프트:", realtime_bus_info_prompt)
            messages = [
                {"role": "system", "content": "실시간 버스 정보를 분석하는 도우미야."},
                {"role": "user", "content": realtime_bus_info_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.0,
            )
            content = response.choices[0].message.content
            print(f"실시간 버스 정보 요청 gpt응답: {content}")
            result = json.loads(content)
            is_exist = result.get("is_exist")
            message = result.get("message")
            if is_exist:
                return {"message": message}
            else:
                return {"message": f"요청하신 {bus_no}번 버스 정보가 없습니다. 다른 버스를 시도해 주세요."}

        elif request_type == "general_bus_info":
            directions = fetch_bus_directions(dep_coord, dest_coord)
            if not directions:
                message = f"죄송해요, {searched_dest[0].get('name')}에 가는 경로를 찾을 수 없어요. 다시 시도해주세요."
                return {"message": message}
            general_bus_info_prompt = f"""
다음 경로 정보를 간략한 대화 형식의 안내하는 메시지를 줄바꿈 없이, 값이 0인 정보는 제외하고 안내하며, 특수문자 사용 없이 한 줄로 생성해줘.
경로 정보: {directions[0]}

반환 형식은 반드시 다음과 같은 JSON만 포함해야 하고, 문자열이 아닌 JSON 객체 자체로 시작하고 끝나야 해.
아래 JSON 형식 외의 **어떠한 설명, 주석, 코드블럭(예: ```)도 포함하지 마.** 반드시 JSON 객체로 시작하고 끝나야 해.
출력 형식:
{{
    "message": "사용자에게 보여줄 메시지"
}}
""".strip()
            print("일반 버스 정보 요청 프롬프트:", general_bus_info_prompt)
            messages = [
                {"role": "system", "content": "너는 버스 경로를 친절하게 안내하는 도우미야."},
                {"role": "user", "content": general_bus_info_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.0,
            )
            content = response.choices[0].message.content
            print(f"일반 버스 정보 요청 gpt응답: {content}")
            result = json.loads(content)
            message = result.get("message", None)

            if message:
                return {"message": message}
            else:
                return  {"message": "죄송해요, 버스 경로 정보를 생성하는 데 문제가 발생했어요. 다시 시도해주세요."}

        elif request_type == "null":
            return {"message": "목적지와 버스 번호, 또는 목적지를 말씀해 주세요."}

        else:
            return


    except Exception as e:
        print(f"gpt api 호출 중 에러: {e}")
        return {
            "message": "죄송해요, 서버에 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
            "error": "GPT API 호출 중 에러"
        }
    


