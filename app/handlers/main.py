from app.handlers import set_dest
from app.services.gpt import classify_state


def handle_main(user_id, user_input):
    state = classify_state(user_id, user_input).get("state", "error")
    if state == "set_dest":
        return set_dest.handle_set_dest(user_id, user_input)
    
    elif state == "set_dep":
        # 출발지 설정 로직은 아직 구현되지 않았습니다.
        return {"message": "출발지 설정 기능은 아직 구현되지 않았습니다."}
    
    elif state == "main":
        # 메인 상태에서의 로직은 아직 구현되지 않았습니다.
        return {"message": "메인 상태에서의 기능은 아직 구현되지 않았습니다."}
    
    else:
        return {"message": "알 수 없는 오류입니다. 잠시 후 다시 시도해주세요."}


