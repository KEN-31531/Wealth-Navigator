<!-- 此檔案記錄本專案使用的開發工具與技術棧 -->

# 財富導航 - 開發工具紀錄

## 專案檔案結構

```text
財富導航/
├── app.py           # 主程式
├── config.py        # 配置
├── questions.py     # 題目
├── stress_test.py   # 測試邏輯
├── requirements.txt # 依賴
├── .env             # 環境變數
└── venv/            # 虛擬環境
```

## 程式語言與框架

- **Python 3.13**
- **Flask** - Web 框架

## LINE Bot 相關

- **LINE Messaging API** - Line 官方訊息 API
- **line-bot-sdk v3** - Python SDK
- **Flex Message** - 互動式卡片訊息

## 部署平台

- **Zeabur** - 雲端部署平台

## 本地開發測試

- **ngrok** - 本地隧道工具，讓 LINE webhook 可連接本地伺服器
  - Authtoken 設定檔位置：`~/Library/Application Support/ngrok/ngrok.yml`
  - 啟動指令：`ngrok http 8080`
  - 管理介面：`http://127.0.0.1:4040`

## 開發輔助

- **Claude Code** - AI 輔助開發工具

## 其他

- **python-dotenv** - 環境變數管理
- **gunicorn** - 生產環境 WSGI 伺服器
