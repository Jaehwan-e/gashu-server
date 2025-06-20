def get_user_dep_history(user_id: str) -> list:
    # 데이터베이스 연결 후 사용자 출발지 히스토리 불러와 반환
    return ["청주 엔포드호텔", "오송역"]

def get_user_dest_history(user_id: str) -> list:
    # 데이터베이스 연결 후 사용자 목적지 히스토리 불러와 반환
    return ["청주대", "서원대"]