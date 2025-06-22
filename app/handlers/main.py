from app.handlers.set_dep import handle_set_dep
from app.handlers.set_dest import handle_set_dest
from app.services.gpt import classify_state


def main(user_id, user_input):
    state = classify_state(user_id, user_input).get("state", "error")
    
    if state == "set_dest":
        return handle_set_dest(user_id, user_input)
    
    elif state == "set_dep":
        return handle_set_dep(user_id, user_input)
    
    elif state == "main":
        return handle_main(user_id, user_input)
    
    else:
        return {"message": "죄송하지만 버스 관련 정보만 안내해 드릴 수 있어요."}



def handle_main(user_id, user_message):
    """
    메인 핸들러 함수로 사용자의 메시지를 처리하고 상태에 따라 적절한 핸들러로 분기합니다.
    """
    print("Handling main message...")
    return {"message": "main 함수 비정상 종료."}