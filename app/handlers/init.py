from app.services.redis_session import delete_session, init_session, get_session, update_session
from app.services.db import get_user_dep_history, get_user_dest_history 


def handle_init(user_id, user_message, user_lon=127.43168, user_lat=36.62544):

    # 기존 세션 제거 및 초기화
    delete_session(user_id)
    init_session(user_id)

    # 사용자 히스토리 불러오기
    dep_history = get_user_dep_history(user_id)
    dest_history = get_user_dest_history(user_id)

    # 세션 불러와서 히스토리 반영
    session = get_session(user_id)
    session["history_dep"] = dep_history or []
    session["history_dest"] = dest_history or []

    # 사용자 GPS 위치도 설정
    session["user_gps"] = [user_lon, user_lat]

    # 상태 => 목적지 설정 단계
    session["state"] = "set_dest"
    session["sub_state"] = "main"

    # 초기화 메시지
    message = f'안녕하세요. 오늘은 어디에 가시겠어요? 이전에는 {", ".join(dest_history)}에 갔어요'
    # --------------------------------참고 후 삭제--------------------------------------
    # 사용자 메시지 추가  
    session["history_set_dest_step"] = session.get("history_set_dest_step", []) + [{"role": "user", "content": message}]
    #-------------------------------------------------------------------------------------

    # 세션 갱신
    print('Updating session with user history and GPS location...')
    print(session)
    update_session(user_id, session)

    # 반환
    return {
        "message": message
    }
