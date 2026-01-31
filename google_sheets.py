"""Google Sheets CRM 整合"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

# Google Sheets 設定
SPREADSHEET_ID = "1L9m-Vq1J9iN_daSJ-K1lLuObl5fkGW6ImWSUTSZUYMo"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "google_credentials.json")

# 初始化 Google Sheets 客戶端
_client = None
_sheet = None


def get_sheet():
    """取得 Google Sheet 工作表"""
    global _client, _sheet

    if _sheet is None:
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]

            # 優先使用環境變數，否則使用檔案
            google_creds_json = os.environ.get("GOOGLE_CREDENTIALS")
            if google_creds_json:
                creds_dict = json.loads(google_creds_json)
                credentials = Credentials.from_service_account_info(
                    creds_dict, scopes=scopes
                )
            else:
                credentials = Credentials.from_service_account_file(
                    CREDENTIALS_FILE, scopes=scopes
                )

            _client = gspread.authorize(credentials)
            _sheet = _client.open_by_key(SPREADSHEET_ID).sheet1
        except Exception as e:
            print(f"Google Sheets 連線錯誤: {e}")
            return None

    return _sheet


def add_user_registration(user_id, name):
    """新增用戶註冊資料"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        row = [
            user_id,           # A: Line ID
            name,              # B: 姓名
            now,               # C: 註冊時間
            "",                # D: 測試分數
            "",                # E: 測試等級
            "",                # F: 測試時間
            "待追蹤",          # G: 客戶狀態
            ""                 # H: 備註
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"寫入註冊資料錯誤: {e}")
        return False


def update_test_result(user_id, score, level):
    """更新用戶測試結果"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        # 找到用戶的列
        cell = sheet.find(user_id)
        if cell is None:
            return False

        row = cell.row
        now = datetime.now().strftime("%Y/%m/%d %H:%M")

        # 更新測試分數、等級、時間
        sheet.update_cell(row, 4, score)      # D 欄：測試分數
        sheet.update_cell(row, 5, level)      # E 欄：測試等級
        sheet.update_cell(row, 6, now)        # F 欄：測試時間
        return True
    except Exception as e:
        print(f"更新測試結果錯誤: {e}")
        return False


def get_user_by_id(user_id):
    """根據 Line ID 取得用戶資料"""
    sheet = get_sheet()
    if sheet is None:
        return None

    try:
        cell = sheet.find(user_id)
        if cell is None:
            return None

        row = sheet.row_values(cell.row)
        return {
            "user_id": row[0] if len(row) > 0 else "",
            "name": row[1] if len(row) > 1 else "",
            "register_time": row[2] if len(row) > 2 else "",
            "score": row[3] if len(row) > 3 else "",
            "level": row[4] if len(row) > 4 else "",
            "test_time": row[5] if len(row) > 5 else "",
            "status": row[6] if len(row) > 6 else "",
            "note": row[7] if len(row) > 7 else ""
        }
    except Exception as e:
        print(f"查詢用戶錯誤: {e}")
        return None


def is_user_exists(user_id):
    """檢查用戶是否已存在"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        cell = sheet.find(user_id)
        return cell is not None
    except Exception as e:
        print(f"檢查用戶錯誤: {e}")
        return False


# ===== 註冊狀態管理（持久化） =====

def start_registration_persistent(user_id):
    """開始註冊流程（寫入 Google Sheets）"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        # 檢查是否已存在
        cell = sheet.find(user_id)
        if cell is not None:
            # 已存在，檢查是否已完成註冊
            row = sheet.row_values(cell.row)
            register_time = row[2] if len(row) > 2 else ""
            if register_time:
                # 已完成註冊
                return "already_registered"
            # 未完成，繼續使用現有記錄
            return True

        # 新建記錄（只有 LINE ID）
        row = [
            user_id,    # A: Line ID
            "",         # B: 姓名（待填）
            "",         # C: 註冊時間（完成時填入）
            "",         # D: 測試分數
            "",         # E: 測試等級
            "",         # F: 測試時間
            "註冊中",   # G: 客戶狀態
            ""          # H: 備註
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        print(f"開始註冊錯誤: {e}")
        return False


def get_registration_state_persistent(user_id):
    """取得註冊狀態（從 Google Sheets）"""
    sheet = get_sheet()
    if sheet is None:
        return None

    try:
        cell = sheet.find(user_id)
        if cell is None:
            return None  # 不在註冊流程中

        row = sheet.row_values(cell.row)
        name = row[1] if len(row) > 1 else ""
        register_time = row[2] if len(row) > 2 else ""

        # 判斷狀態
        if register_time:
            return "completed"
        elif name:
            return "completed"  # 有姓名就算完成
        else:
            return "waiting_name"
    except Exception as e:
        print(f"取得註冊狀態錯誤: {e}")
        return None


def update_registration_name(user_id, name):
    """更新註冊姓名"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        cell = sheet.find(user_id)
        if cell is None:
            return False

        sheet.update_cell(cell.row, 2, name)  # B 欄：姓名
        return True
    except Exception as e:
        print(f"更新姓名錯誤: {e}")
        return False


def complete_registration_persistent(user_id, payment_code=None):
    """完成註冊（更新註冊時間）"""
    sheet = get_sheet()
    if sheet is None:
        return None

    try:
        cell = sheet.find(user_id)
        if cell is None:
            return None

        row = sheet.row_values(cell.row)
        name = row[1] if len(row) > 1 else ""
        now = datetime.now().strftime("%Y/%m/%d %H:%M")

        # 更新註冊時間、狀態
        sheet.update_cell(cell.row, 3, now)           # C 欄：註冊時間
        sheet.update_cell(cell.row, 7, "待追蹤")      # G 欄：客戶狀態

        return {"name": name}
    except Exception as e:
        print(f"完成註冊錯誤: {e}")
        return None


def get_user_name(user_id):
    """取得用戶姓名"""
    sheet = get_sheet()
    if sheet is None:
        return None

    try:
        cell = sheet.find(user_id)
        if cell is None:
            return None

        row = sheet.row_values(cell.row)
        return row[1] if len(row) > 1 else None
    except Exception as e:
        print(f"取得姓名錯誤: {e}")
        return None
