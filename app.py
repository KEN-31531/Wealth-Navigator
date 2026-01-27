from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import json

from config import LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN
from stress_test import (
    start_test,
    process_answer,
    is_user_in_test,
    is_multiple_choice_question,
    get_multiple_selections,
    cancel_test,
    get_current_question,
)

app = Flask(__name__)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@app.route("/health", methods=["GET"])
def health_check():
    return "OK"


def create_button_box(label, text_to_send):
    """建立單一按鈕框"""
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "md",
                "color": "#333333",
                "align": "center",
                "wrap": True
            }
        ],
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "lg",
        "paddingAll": "lg",
        "action": {
            "type": "message",
            "text": text_to_send
        },
        "borderColor": "#DDDDDD",
        "borderWidth": "normal"
    }


def create_question_flex(question, show_part=False):
    """建立問題的 Flex Message"""
    options = question["options"]
    is_multiple = question.get("type") == "multiple"

    # 建立標題
    header_text = ""
    if show_part:
        header_text = f"【{question['part']}】\n\n"
    header_text += question["question"]

    # 建立選項按鈕
    button_contents = []
    for opt in options:
        button_contents.append(create_button_box(opt["label"], opt["label"][0]))
        button_contents.append({"type": "spacer", "size": "md"})

    # 多選題加入「完成」按鈕
    if is_multiple:
        button_contents.append({
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "✓ 完成選擇",
                    "size": "md",
                    "color": "#FFFFFF",
                    "align": "center",
                    "weight": "bold"
                }
            ],
            "backgroundColor": "#06C755",
            "cornerRadius": "lg",
            "paddingAll": "lg",
            "action": {
                "type": "message",
                "text": "完成"
            }
        })

    # 移除最後的 spacer
    if button_contents and button_contents[-1].get("type") == "spacer":
        button_contents.pop()

    flex_content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": header_text,
                    "size": "md",
                    "color": "#333333",
                    "wrap": True,
                    "weight": "bold"
                },
                {"type": "spacer", "size": "xl"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": button_contents,
                    "spacing": "md"
                }
            ],
            "backgroundColor": "#F5F5F5",
            "paddingAll": "xl"
        }
    }

    return FlexMessage(
        alt_text=question["question"],
        contents=FlexContainer.from_dict(flex_content)
    )


def create_multiple_continue_flex(question, selected):
    """建立多選題繼續選擇的 Flex Message"""
    selected_text = "、".join(selected)
    options = question["options"]

    # 建立選項按鈕
    button_contents = []
    for opt in options:
        button_contents.append(create_button_box(opt["label"], opt["label"][0]))
        button_contents.append({"type": "spacer", "size": "md"})

    # 加入「完成」按鈕
    button_contents.append({
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "✓ 完成選擇",
                "size": "md",
                "color": "#FFFFFF",
                "align": "center",
                "weight": "bold"
            }
        ],
        "backgroundColor": "#06C755",
        "cornerRadius": "lg",
        "paddingAll": "lg",
        "action": {
            "type": "message",
            "text": "完成"
        }
    })

    flex_content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"已選擇：{selected_text}",
                    "size": "md",
                    "color": "#06C755",
                    "wrap": True,
                    "weight": "bold"
                },
                {"type": "spacer", "size": "md"},
                {
                    "type": "text",
                    "text": "還要選擇其他選項嗎？選完請按「完成選擇」",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True
                },
                {"type": "spacer", "size": "xl"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": button_contents,
                    "spacing": "md"
                }
            ],
            "backgroundColor": "#F5F5F5",
            "paddingAll": "xl"
        }
    }

    return FlexMessage(
        alt_text="請繼續選擇或按完成",
        contents=FlexContainer.from_dict(flex_content)
    )


def create_result_flex(result):
    """建立測試結果的 Flex Message"""
    profile = result.get("profile", {})

    # 根據等級選擇顏色
    if "綠色" in result['level']:
        level_color = "#06C755"
        bg_color = "#E8F5E9"
    elif "黃色" in result['level']:
        level_color = "#FFB800"
        bg_color = "#FFF8E1"
    else:
        level_color = "#FF5555"
        bg_color = "#FFEBEE"

    # 建立內容
    body_contents = [
        {
            "type": "text",
            "text": "📊 財務壓力測試結果",
            "size": "xl",
            "color": "#333333",
            "weight": "bold",
            "align": "center"
        },
        {"type": "spacer", "size": "xl"},
        {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": result['level'],
                    "size": "lg",
                    "color": level_color,
                    "weight": "bold",
                    "align": "center",
                    "wrap": True
                }
            ],
            "backgroundColor": bg_color,
            "cornerRadius": "lg",
            "paddingAll": "lg"
        },
        {"type": "spacer", "size": "lg"},
        {
            "type": "text",
            "text": f"總分：{result['score']} / {result['max_score']} 分",
            "size": "md",
            "color": "#333333",
            "align": "center",
            "weight": "bold"
        },
        {"type": "spacer", "size": "xl"},
        {
            "type": "text",
            "text": "📋 診斷",
            "size": "md",
            "color": "#333333",
            "weight": "bold"
        },
        {
            "type": "text",
            "text": result['description'],
            "size": "sm",
            "color": "#666666",
            "wrap": True
        },
        {"type": "spacer", "size": "lg"},
        {
            "type": "text",
            "text": "💡 專家建議",
            "size": "md",
            "color": "#333333",
            "weight": "bold"
        },
        {
            "type": "text",
            "text": result['suggestion'],
            "size": "sm",
            "color": "#666666",
            "wrap": True
        }
    ]

    # 加入用戶背景資訊
    if profile.get("Q5") or profile.get("Q7") or profile.get("Q8"):
        body_contents.append({"type": "spacer", "size": "xl"})
        body_contents.append({
            "type": "separator",
            "color": "#DDDDDD"
        })
        body_contents.append({"type": "spacer", "size": "lg"})

        if profile.get("Q5"):
            challenges = profile["Q5"]
            if isinstance(challenges, list) and challenges:
                body_contents.append({
                    "type": "text",
                    "text": f"📌 您的理財挑戰：{', '.join(challenges)}",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True
                })

        if profile.get("Q7"):
            body_contents.append({
                "type": "text",
                "text": f"📌 年度理財預算：{profile['Q7']}",
                "size": "sm",
                "color": "#666666",
                "wrap": True
            })

        if profile.get("Q8"):
            body_contents.append({
                "type": "text",
                "text": f"📌 最想解決的問題：{profile['Q8']}",
                "size": "sm",
                "color": "#666666",
                "wrap": True
            })

    # 加入重新測試按鈕
    body_contents.append({"type": "spacer", "size": "xl"})
    body_contents.append({
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "🔄 重新測試",
                "size": "md",
                "color": "#333333",
                "align": "center"
            }
        ],
        "backgroundColor": "#FFFFFF",
        "cornerRadius": "lg",
        "paddingAll": "md",
        "action": {
            "type": "message",
            "text": "財務壓力測試"
        },
        "borderColor": "#DDDDDD",
        "borderWidth": "normal"
    })

    flex_content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "backgroundColor": "#F5F5F5",
            "paddingAll": "xl"
        }
    }

    return FlexMessage(
        alt_text=f"測試結果：{result['level']}",
        contents=FlexContainer.from_dict(flex_content)
    )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 檢查是否要開始測試
        if user_message in ["財務壓力測試", "開始測試", "壓力測試", "測試"]:
            if is_user_in_test(user_id):
                cancel_test(user_id)

            question = start_test(user_id)

            intro_message = TextMessage(
                text="📋 財務壓力測試\n\n"
                     "歡迎參加財務壓力測試！\n"
                     "本測試共 8 題，請根據您的實際狀況選擇最符合的答案。\n\n"
                     "完成後將為您分析財務健康狀況並提供專家建議。\n\n"
                     "讓我們開始吧！"
            )
            question_message = create_question_flex(question, show_part=True)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[intro_message, question_message]
                )
            )
            return

        # 檢查是否要取消測試
        if user_message in ["取消", "取消測試", "結束", "放棄"]:
            if is_user_in_test(user_id):
                cancel_test(user_id)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="已取消測試。如需重新開始，請輸入「財務壓力測試」。")]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="您目前沒有進行中的測試。")]
                    )
                )
            return

        # 檢查是否在測試中
        if is_user_in_test(user_id):
            status, data = process_answer(user_id, user_message)

            if status == "invalid":
                current_question = get_current_question(user_id)
                if is_multiple_choice_question(user_id):
                    selected = get_multiple_selections(user_id)
                    if selected:
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=[
                                    TextMessage(text="請選擇選項或按「完成選擇」。"),
                                    create_multiple_continue_flex(current_question, selected)
                                ]
                            )
                        )
                    else:
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=[
                                    TextMessage(text="請點選下方選項。"),
                                    create_question_flex(current_question)
                                ]
                            )
                        )
                else:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(text="請點選下方選項。"),
                                create_question_flex(current_question)
                            ]
                        )
                    )
            elif status == "multiple_continue":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_multiple_continue_flex(data["question"], data["selected"])]
                    )
                )
            elif status == "next":
                prev_index = user_sessions_get_prev_index(user_id)
                show_part = should_show_part(prev_index, data)

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_question_flex(data, show_part=show_part)]
                    )
                )
            elif status == "complete":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_result_flex(data)]
                    )
                )
            return

        # 預設回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text="歡迎使用財富導航！\n\n"
                             "請輸入「財務壓力測試」開始測試您的財務健康狀況。"
                    )
                ]
            )
        )


def user_sessions_get_prev_index(user_id):
    """取得上一題的索引"""
    from stress_test import user_sessions
    session = user_sessions.get(user_id)
    if session:
        return session["current_question"] - 1
    return -1


def should_show_part(prev_index, current_question):
    """判斷是否需要顯示 part 標題"""
    from questions import QUESTIONS
    if prev_index < 0:
        return True
    if prev_index >= len(QUESTIONS):
        return False
    prev_part = QUESTIONS[prev_index].get("part", "")
    current_part = current_question.get("part", "")
    return prev_part != current_part


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
