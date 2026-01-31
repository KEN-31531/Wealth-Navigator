"""用戶註冊管理（使用 Google Sheets 持久化）"""

from google_sheets import (
    start_registration_persistent,
    get_registration_state_persistent,
    update_registration_name,
    complete_registration_persistent,
    get_user_name,
)


def is_user_registered(user_id):
    """檢查用戶是否已完成註冊"""
    state = get_registration_state_persistent(user_id)
    return state == "completed"


def is_user_in_registration(user_id):
    """檢查用戶是否正在註冊中"""
    state = get_registration_state_persistent(user_id)
    return state == "waiting_name"


def start_registration(user_id):
    """開始註冊流程"""
    result = start_registration_persistent(user_id)
    if result == "already_registered":
        return "already_registered"
    return "waiting_name"


def get_registration_state(user_id):
    """取得註冊狀態"""
    return get_registration_state_persistent(user_id)


def process_registration(user_id, message):
    """處理註冊輸入"""
    state = get_registration_state_persistent(user_id)
    if not state or state == "completed":
        return None, None

    if state == "waiting_name":
        # 儲存姓名並直接完成註冊
        name = message.strip()
        if update_registration_name(user_id, name):
            # 直接完成註冊（不需要匯款碼）
            result = complete_registration_persistent(user_id, "")
            if result:
                return "completed", {"name": name}
        return None, None

    return None, None


def get_user_info(user_id):
    """取得用戶資料"""
    from google_sheets import get_user_by_id
    return get_user_by_id(user_id)
