QUESTIONS = [
    # 第一部分：金錢安全感
    {
        "part": "第一部分：金錢安全感",
        "question": "Q1. 如果您現在停止工作，現有的存款在不改變生活品質的前提下，能支撐您多久？",
        "type": "single",
        "scored": True,
        "options": [
            {"label": "A. 3個月以內", "score": 1},
            {"label": "B. 6個月-1年", "score": 4},
            {"label": "C. 1年-3年", "score": 7},
            {"label": "D. 3年以上", "score": 10},
        ]
    },
    {
        "part": "第一部分：金錢安全感",
        "question": "Q2. 您是否發現，儘管薪水增加了，但每個月能存下來的購買力卻越來越少？",
        "type": "single",
        "scored": True,
        "options": [
            {"label": "A. 非常有感", "score": 1},
            {"label": "B. 偶爾覺得", "score": 4},
            {"label": "C. 沒感覺，覺得物價還好", "score": 6},
        ]
    },
    # 第二部分：風險防禦力
    {
        "part": "第二部分：風險防禦力",
        "question": "Q3. 若發生金融海嘯或地緣政治危機，您的資產中有多少比例是能「立刻變現」且「全球通用」的實體財富？",
        "type": "single",
        "scored": True,
        "options": [
            {"label": "A. 完全沒有", "score": 1},
            {"label": "B. 5%以下", "score": 4},
            {"label": "C. 5%-10%", "score": 7},
            {"label": "D. 10%以上", "score": 10},
        ]
    },
    {
        "part": "第二部分：風險防禦力",
        "question": "Q4. 當股市大幅震盪時，您的心理狀態通常是：",
        "type": "single",
        "scored": True,
        "options": [
            {"label": "A. 非常焦慮，想立刻賣掉", "score": 1},
            {"label": "B. 有點擔心，但觀望", "score": 4},
            {"label": "C. 很淡定，因為我有防禦性資產", "score": 6},
        ]
    },
    # 第三部分：理財慣性
    {
        "part": "第三部分：理財慣性",
        "question": "Q5. 關於理財，您目前面臨最大的挑戰是什麼？（可多選，選完請輸入「完成」）",
        "type": "multiple",
        "scored": False,
        "options": [
            {"label": "A. 工作太忙沒時間", "value": "工作太忙沒時間"},
            {"label": "B. 害怕虧損", "value": "害怕虧損"},
            {"label": "C. 不知道怎麼選標的", "value": "不知道怎麼選標的"},
            {"label": "D. 想要紀律存錢但失敗", "value": "想要紀律存錢但失敗"},
        ]
    },
    {
        "part": "第三部分：理財慣性",
        "question": "Q6. 您是否希望有一套系統，能幫您在「提供保障」的同時，也讓資金自動增值？",
        "type": "single",
        "scored": True,
        "options": [
            {"label": "A. 非常渴望", "score": 10},
            {"label": "B. 有興趣了解", "score": 6},
            {"label": "C. 目前不需要", "score": 1},
        ]
    },
    # 第四部分：基本背景
    {
        "part": "第四部分：基本背景",
        "question": "Q7. 您的年度理財預算（包含儲蓄與投資）大約落在：",
        "type": "single",
        "scored": False,
        "options": [
            {"label": "A. 10萬以下", "value": "10萬以下"},
            {"label": "B. 10-50萬", "value": "10-50萬"},
            {"label": "C. 50-100萬", "value": "50-100萬"},
            {"label": "D. 100萬以上", "value": "100萬以上"},
        ]
    },
    {
        "part": "第四部分：基本背景",
        "question": "Q8. 如果您能透過一個月的學習掌握一套「保值+增值」的配置法，您最希望解決的問題是？",
        "type": "single",
        "scored": False,
        "options": [
            {"label": "A. 讓資產不被通膨吃掉", "value": "讓資產不被通膨吃掉"},
            {"label": "B. 留一筆錢給下一代", "value": "留一筆錢給下一代"},
            {"label": "C. 建立穩定的被動收入", "value": "建立穩定的被動收入"},
        ]
    },
]

# 計分題：Q1(1-10) + Q2(1-6) + Q3(1-10) + Q4(1-6) + Q6(1-10) = 5-42 分
MAX_SCORE = 42
MIN_SCORE = 5
