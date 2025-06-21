import os
import requests
from dotenv import load_dotenv
load_dotenv()



def geocode_address(address: str) -> tuple:
    """
    주소 문자열을 위경도로 변환 (지오코딩)
    반환값: (lon, lat)
    """
    API_URL = "https://api.example.com/geocode"
    API_KEY = os.getenv("GEOCODE_API_KEY")

    params = {
    }

    return (127.45278,36.63197)  # 예시 좌표, 실제 API 호출로 대체 필요



def search_address_by_keyword(keyword: str) -> list:
    """
    키워드로 주소 후보 목록 검색
    반환값: 주소 리스트
    """
    API_URL = "https://api.example.com/search_address"
    API_KEY = os.getenv("")

    params = {
    }
    if keyword == '집':
        return []

    return [
        {"name": "Sample Place", "address": "123 Sample St, City, Country"},
        {"name": "Another Place", "address": "456 Another Rd, City, Country"}
    ]



def fetch_bus_directions(dep_coord: tuple, dest_coord: tuple) -> list:
    """
    출발지-목적지 좌표를 이용한 경로 탐색
    반환값: 경로 정보 배열(시간, 거리, 경유지 등)
    """
    API_URL = "https://api.example.com/find_route"
    API_KEY = os.getenv("")

    params = {
        
    }
    
    return []



def fetch_realtime_bus_info(route_id: str) -> list:
    """
    버스 노선 ID 기준 실시간 위치, 도착 정보 조회
    반환값: 버스 위치, 도착 시간 등
    """
    API_URL = "https://api.example.com/realtime_bus"
    API_KEY = os.getenv("BUS_SERVICE_KEY")

    params = {
        
    }

    return []

