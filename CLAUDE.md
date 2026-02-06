# CLAUDE.md

此檔案為 Claude Code (claude.ai/code) 在本專案中工作時的指引文件。

## 專案概述

財富導航 (Wealth Navigator) — LINE Bot 財務健康評估工具。Bot 透過 8 題 VIP 財務壓力測試，將用戶評分為三個等級（紅/黃/綠燈區），並提供個人化理財建議。用戶資料透過 Google Sheets 做為輕量 CRM 持久化儲存。

## 常用指令

### 開發環境

```bash
source venv/bin/activate          # 啟動虛擬環境
pip install -r requirements.txt   # 安裝依賴套件
python app.py                     # 啟動開發伺服器（0.0.0.0:8080）
gunicorn app:app --bind 0.0.0.0:8080  # 正式環境伺服器
```

### 本地測試

使用 ngrok 建立隧道，再將 LINE webhook URL 設定為 `<ngrok_url>/callback`。健康檢查端點為 `/health`。

### 部署

部署於 **Zeabur** 雲端平台。推送至 `main` 分支即自動部署。

## 架構

```text
app.py（Flask 伺服器、LINE webhook 處理器、Flex Message 建構器）
  ├── config.py            — 從環境變數載入 LINE_CHANNEL_SECRET / LINE_CHANNEL_ACCESS_TOKEN
  ├── stress_test.py       — 測驗狀態機、記憶體內 session、計分邏輯
  │     └── questions.py   — 8 題測驗資料，橫跨 4 個分類
  ├── user_registration.py — 用戶註冊流程封裝（僅需姓名）
  └── google_sheets.py     — Google Sheets CRM：用戶資料與測驗結果持久化
```

**資料流**：LINE webhook → Flask `/callback` → `WebhookHandler` 分派至事件處理器（`handle_follow`、`handle_text_message`、`handle_postback`）→ 商業邏輯模組 → Google Sheets 持久化。

### 狀態管理

- **暫態**：測驗進度儲存於記憶體 dict（`stress_test.py` 中的 `user_sessions`），重啟後遺失。
- **持久態**：用戶註冊與測驗結果儲存於 Google Sheets（透過 `google_sheets.py`）。

### LINE Flex Messages

所有互動式 UI 皆使用 LINE Flex Messages 在 `app.py` 中建構。主要建構函式：

- `create_question_flex()` — 測驗題目卡片
- `create_multiple_continue_flex()` — 多選題，含 toggle 切換行為
- `create_result_flex()` — 評分結果顯示，附 PDF 連結

### 測驗計分

- 5–15 分：🔴 紅燈區（財務裸奔期）
- 16–28 分：🟡 黃燈區（財富焦慮期）
- 29–42 分：🟢 綠燈區（財富方舟期）

## 環境變數

| 變數 | 必要 | 說明 |
| --- | --- | --- |
| `LINE_CHANNEL_SECRET` | 是 | LINE Bot channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | 是 | LINE Bot access token |
| `GOOGLE_CREDENTIALS` | 否 | Google 服務帳號憑證的 JSON 字串（若未設定，會退而使用 `google_credentials.json` 檔案） |

## 主要依賴套件

- **Flask** — 網頁框架
- **line-bot-sdk v3** — LINE Messaging API（`linebot.v3.messaging`、`linebot.v3.webhooks`）
- **gspread + google-auth** — Google Sheets API
- **gunicorn** — 正式環境 WSGI 伺服器

## Google Sheets CRM

試算表欄位：Line ID、姓名、註冊時間、測驗分數、測驗等級、測驗時間、客戶狀態、備註。時區為台灣時間（UTC+8）。

## 品牌色彩

- 已選取項目：`#FFE153`（黃色）
- 主要按鈕：`#408080`（青色）
- 背景：`#F5F5F5`、邊框：`#DDDDDD`

## 語言慣例

Bot 介面、面向用戶的文字與 commit 訊息使用**繁體中文**。程式碼變數名稱與註解使用英文。
