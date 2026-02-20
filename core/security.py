from core.config import AUTHORIZED_USER_ID

def is_authorized(user_id: int) -> bool:
    return str(user_id) == str(AUTHORIZED_USER_ID)