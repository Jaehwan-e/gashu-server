import pymysql
import os
from dotenv import load_dotenv
load_dotenv()

# MySQL 연결 설정
mysql_conn = pymysql.connect(
    host=os.getenv("DATABASE_HOST"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD"),
    database=os.getenv("DATABASE_NAME"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor  # dict 형태 반환
)

def find_nearest_station_nodeid(lat: float, lon: float) -> str:
    """
    특정 좌표에 가장 가까운 STATION 테이블의 nodeid 반환
    """
    with mysql_conn.cursor() as cursor:
        query = """
            SELECT nodeid
            FROM STATION
            ORDER BY POW(gpslati - %s, 2) + POW(gpslong - %s, 2)
            LIMIT 1;
        """
        cursor.execute(query, (lat, lon))
        result = cursor.fetchone()
        return result["nodeid"] if result else None

def get_user_dep_history(user_id: str) -> list:
    # 데이터베이스 연결 후 사용자 출발지 히스토리 불러와 반환
    return ["청주 엔포드호텔", "오송역"]

def get_user_dest_history(user_id: str) -> list:
    # 데이터베이스 연결 후 사용자 목적지 히스토리 불러와 반환
    return ["청주대", "서원대"]