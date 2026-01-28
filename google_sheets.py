"""Google Sheets CRM 整合"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

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
            credentials = Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=scopes
            )
            _client = gspread.authorize(credentials)
            _sheet = _client.open_by_key(SPREADSHEET_ID).sheet1
        except Exception as e:
            print(f"Google Sheets 連線錯誤: {e}")
            return None

    return _sheet


def add_user_registration(user_id, name, payment_code):
    """新增用戶註冊資料"""
    sheet = get_sheet()
    if sheet is None:
        return False

    try:
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        row = [
            user_id,           # Line ID
            name,              # 姓名
            payment_code,      # 匯款後五碼
            now,               # 註冊時間
            "",                # 測試分數
            "",                # 測試等級
            "",                # 測試時間
            "待追蹤",          # 客戶狀態
            ""                 # 備註
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
        sheet.update_cell(row, 5, score)      # E 欄：測試分數
        sheet.update_cell(row, 6, level)      # F 欄：測試等級
        sheet.update_cell(row, 7, now)        # G 欄：測試時間
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
            "payment_code": row[2] if len(row) > 2 else "",
            "register_time": row[3] if len(row) > 3 else "",
            "score": row[4] if len(row) > 4 else "",
            "level": row[5] if len(row) > 5 else "",
            "test_time": row[6] if len(row) > 6 else "",
            "status": row[7] if len(row) > 7 else "",
            "note": row[8] if len(row) > 8 else ""
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
            payment_code = row[2] if len(row) > 2 else ""
            if payment_code and len(payment_code) == 5 and payment_code.isdigit():
                # 已完成註冊
                return "already_registered"
            # 未完成，繼續使用現有記錄
            return True

        # 新建記錄（只有 LINE ID）
        row = [
            user_id,    # Line ID
            "",         # 姓名（待填）
            "",         # 匯款後五碼（待填）
            "",         # 註冊時間（完成時填入）
            "",         # 測試分數
            "",         # 測試等級
            "",         # 測試時間
            "註冊中",   # 客戶狀態
            ""          # 備註
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
        payment_code = row[2] if len(row) > 2 else ""

        # 判斷狀態
        if payment_code and len(payment_code) == 5 and payment_code.isdigit():
            return "completed"
        elif name:
            return "waiting_payment_code"
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


def complete_registration_persistent(user_id, payment_code):
    """完成註冊（更新匯款後五碼和時間）"""
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

        # 更新匯款後五碼、註冊時間、狀態
        sheet.update_cell(cell.row, 3, payment_code)  # C 欄：匯款後五碼
        sheet.update_cell(cell.row, 4, now)           # D 欄：註冊時間
        sheet.update_cell(cell.row, 8, "待追蹤")      # H 欄：客戶狀態

        return {"name": name, "payment_code": payment_code}
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
