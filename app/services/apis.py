import os
from datetime import datetime
import requests
from dotenv import load_dotenv
load_dotenv()

from app.services.db import find_nearest_station_nodeid



def geocode_address(address: str) -> tuple:
    """
    주소 문자열을 위경도로 변환 (지오코딩)
    반환값: (lon, lat)
    """
    API_URL = "https://dapi.kakao.com/v2/local/search/address.json"
    API_KEY = os.getenv("KAKAO_API_KEY")

    headers = {
        "Authorization": f"KakaoAK {API_KEY}"
    }

    params = {
        "query": address
    }

    try:
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        documents = data.get("documents", [])
        if not documents:
            print("주소를 찾을 수 없음")
            return None

        first = documents[0]
        lon = float(first["x"])
        lat = float(first["y"])
        return (lon, lat)

    except Exception as e:
        print("실패:", e)
        return None



def search_address_by_keyword(keyword: str) -> list:
    """
    키워드로 주소 후보 목록 검색 (카카오 API 사용)
    반환값: [{'name': 장소명, 'address': 전체주소}, ...]
    """
    if not keyword:
        return []

    API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
    API_KEY = os.getenv("KAKAO_API_KEY")

    headers = {
        "Authorization": f"KakaoAK {API_KEY}"
    }

    params = {
        "query": keyword,
        "size": 1
    }

    try:
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        result = []
        for doc in data.get("documents", []):
            result.append({
                "name": doc.get("place_name"),
                "address": doc.get("road_address_name") or doc.get("address_name")
            })

        return result

    except Exception as e:
        print("주소 검색 오류:", e)
        return []


def fetch_bus_directions(dep_coord: tuple, dest_coord: tuple) -> list:
    def parse_all_itineraries_for_llm(api_response: dict) -> list:
        """
        SK 대중교통 API 응답에서 모든 경로(itinerary)를 정제하여 LLM 입력용 리스트로 반환.
        - 모든 시간 단위는 '분' 단위로 통일
        - bus_routes: station_list, 좌표 제외, start_nodeid 포함
        - walk_segments: 출발→정류장, 환승, 정류장→도착지 도보 구간 정보 포함
        """
        results = []
        itineraries = api_response.get("metaData", {}).get("plan", {}).get("itineraries", [])

        for itinerary in itineraries:
            try:
                total_time_min = itinerary.get("totalTime", 0) // 60
                fare = itinerary.get("fare", {}).get("regular", {}).get("totalFare", 0)
                transfer_count = itinerary.get("transferCount", 0)

                total_walk_time_min = 0
                bus_routes = []
                walk_segments = []

                legs = itinerary.get("legs", [])
                for i, leg in enumerate(legs):
                    mode = leg.get("mode")

                    if mode == "WALK":
                        distance = leg.get("distance", 0)
                        time_min = leg.get("sectionTime", 0) // 60
                        total_walk_time_min += time_min

                        prev_mode = legs[i - 1]["mode"] if i > 0 else None
                        next_mode = legs[i + 1]["mode"] if i + 1 < len(legs) else None

                        if prev_mode is None and next_mode == "BUS":
                            walk_type = "start_to_station"
                        elif prev_mode == "BUS" and next_mode == "BUS":
                            walk_type = "transfer"
                        elif next_mode is None and prev_mode == "BUS":
                            walk_type = "station_to_dest"
                        else:
                            walk_type = "unknown"

                        walk_segments.append({
                            "type": walk_type,
                            "distance": distance,
                            "time": time_min,
                            "start_name": leg.get("start", {}).get("name"),
                            "end_name": leg.get("end", {}).get("name")
                        })

                    elif mode == "BUS":
                        route_name = leg.get("route", "알 수 없음")
                        station_list = leg.get("passStopList", {}).get("stationList", [])
                        if not station_list:
                            continue

                        start_station = station_list[0]
                        end_station = station_list[-1]
                        start_lat = float(start_station["lat"])
                        start_lon = float(start_station["lon"])
                        nodeid = find_nearest_station_nodeid(start_lat, start_lon)

                        bus_routes.append({
                            "route_name": route_name,
                            "start_station": start_station["stationName"],
                            "end_station": end_station["stationName"],
                            "start_nodeid": nodeid
                        })

                if not bus_routes:
                    continue

                results.append({
                    "total_time": total_time_min,
                    "fare": fare,
                    "transfer_count": transfer_count,
                    "total_walk_time": total_walk_time_min,
                    "bus_routes": bus_routes,
                    "walk_segments": walk_segments
                })

            except Exception as e:
                print(f"❌ itinerary 파싱 실패: {e}")
                continue

        return results

    """
    출발지-목적지 좌표를 이용한 경로 탐색
    반환값: 경로 정보 배열(시간, 거리, 경유지 등)
    """
    url = "https://apis.openapi.sk.com/transit/routes/"

    now = datetime.now()
    search_dttm = now.strftime("%Y%m%d%H%M")  # 현재 시각을 'YYYYMMDDHHMM' 형식으로

    payload = {
        "startX": str(dep_coord[0]),
        "startY": str(dep_coord[1]),
        "endX": str(dest_coord[0]),
        "endY": str(dest_coord[1]),
        "lang": 0,
        "format": "json",
        "count": 10,
        "searchDttm": search_dttm
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "appKey": os.getenv("SK_OPENAPI_APPKEY")
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        try:
            api_response = response.json()
            parsed_results = parse_all_itineraries_for_llm(api_response)
            if not parsed_results:
                print("❌ 유효한 경로 정보가 없습니다.")
                return []
            return parsed_results
        except Exception as e:
            print(f"❌ JSON 디코딩 실패: {e}")
            return []
    else:
        print(f"❌ 요청 실패: status code {response.status_code}")
        return []


def fetch_realtime_bus_info(node_id: str, route_id: str) -> list:
    """
    버스 노선 ID 기준 실시간 위치, 도착 정보 조회
    반환값: 각 도착 예정 버스 정보 리스트
           [
             {
                "routeno": "105",
                "nodenm": "복대가경시장",
                "arrprevstationcnt": 12,
                "arrtime": 798
             },
             ...
           ]
    """
    API_URL = "http://apis.data.go.kr/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList"

    params = {
        'serviceKey' : os.getenv("DATA_GO_KEY"), 
        'pageNo': '1', 
        'numOfRows': '10', 
        '_type': 'json', 
        'cityCode': '33010', 
        'nodeId': node_id,
        'routeId': route_id
    }

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("response", {}).get("header", {}).get("resultCode") != "00":
            print("❌ API 응답 오류:", data)
            return []

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            print("❌ 해당 노선의 버스 정보가 없습니다.")
            return []

        result = []
        for item in items:
            result.append({
                "routeno": str(item.get("routeno")),
                "nodenm": item.get("nodenm"),
                "arrprevstationcnt": item.get("arrprevstationcnt"),
                "arrtime": item.get("arrtime")
            })

        return result

    except Exception as e:
        print(f"❌ 실시간 버스 정보 조회 실패: {e}")
        return []

