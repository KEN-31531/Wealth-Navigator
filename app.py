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
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent, FollowEvent
from linebot.v3.exceptions import InvalidSignatureError

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
from user_registration import (
    is_user_registered,
    is_user_in_registration,
    start_registration,
    process_registration,
    get_registration_state,
)
from google_sheets import (
    update_test_result,
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


def create_button_box(label, data, use_postback=False):
    """建立單一按鈕框"""
    if use_postback:
        action = {
            "type": "postback",
            "label": label,
            "data": data
        }
    else:
        action = {
            "type": "message",
            "text": data
        }

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
        "action": action,
        "borderColor": "#DDDDDD",
        "borderWidth": "normal",
        "margin": "md"
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

    # 建立選項按鈕（多選題用 postback，單選題用 message）
    button_contents = []
    for opt in options:
        button_contents.append(create_button_box(opt["label"], opt["label"][0], use_postback=is_multiple))

    # 多選題加入「完成」按鈕（初始為灰色，選擇後才變色）
    if is_multiple:
        button_contents.append({
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "完成選擇",
                    "size": "md",
                    "color": "#999999",
                    "align": "center"
                }
            ],
            "backgroundColor": "#FFFFFF",
            "cornerRadius": "lg",
            "paddingAll": "lg",
            "margin": "xl",
            "borderColor": "#DDDDDD",
            "borderWidth": "normal",
            "action": {
                "type": "postback",
                "label": "完成選擇",
                "data": "complete_multiple"
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
                    "text": header_text,
                    "size": "md",
                    "color": "#333333",
                    "wrap": True,
                    "weight": "bold"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": button_contents,
                    "margin": "xl"
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
    """建立多選題繼續選擇的 Flex Message（已選項目會反色顯示）"""
    options = question["options"]

    # 建立選項按鈕（已選的反色顯示）
    button_contents = []
    for opt in options:
        value = opt.get("value", opt["label"])
        is_selected = value in selected

        if is_selected:
            # 已選擇：亮黃色背景 + 白字 + 打勾（點擊可取消選擇）
            button_contents.append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"✓ {opt['label']}",
                        "size": "md",
                        "color": "#FFFFFF",
                        "align": "center",
                        "wrap": True,
                        "weight": "bold"
                    }
                ],
                "backgroundColor": "#FFE153",
                "cornerRadius": "lg",
                "paddingAll": "lg",
                "action": {
                    "type": "postback",
                    "label": opt["label"],
                    "data": f"toggle:{opt['label'][0]}"
                },
                "margin": "md"
            })
        else:
            # 未選擇：白色背景
            button_contents.append(create_button_box(opt["label"], opt["label"][0], use_postback=True))

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
        "backgroundColor": "#408080",
        "cornerRadius": "lg",
        "paddingAll": "lg",
        "margin": "xl",
        "action": {
            "type": "postback",
            "label": "完成選擇",
            "data": "complete_multiple"
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
                    "text": question["question"],
                    "size": "md",
                    "color": "#333333",
                    "wrap": True,
                    "weight": "bold"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": button_contents,
                    "margin": "xl"
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
        level_color = "#FFE153"
        bg_color = "#FDF6E3"
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
            "text": "📊 VIP 財富健康體檢表結果",
            "size": "xl",
            "color": "#333333",
            "weight": "bold",
            "align": "center"
        },
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
            "paddingAll": "lg",
            "margin": "xl"
        },
        {
            "type": "text",
            "text": f"總分：{result['score']} / {result['max_score']} 分",
            "size": "md",
            "color": "#333333",
            "align": "center",
            "weight": "bold",
            "margin": "lg"
        },
        {
            "type": "separator",
            "color": "#DDDDDD",
            "margin": "xl"
        },
        {
            "type": "text",
            "text": "📋 診斷",
            "size": "md",
            "color": "#333333",
            "weight": "bold",
            "margin": "xl"
        },
        {
            "type": "text",
            "text": result['description'],
            "size": "sm",
            "color": "#666666",
            "wrap": True,
            "margin": "md"
        },
        {
            "type": "text",
            "text": "💡 專家建議",
            "size": "md",
            "color": "#333333",
            "weight": "bold",
            "margin": "xl"
        },
        {
            "type": "text",
            "text": result['suggestion'],
            "size": "sm",
            "color": "#666666",
            "wrap": True,
            "margin": "md"
        }
    ]

    # 加入用戶背景資訊
    if profile.get("Q5") or profile.get("Q7") or profile.get("Q8"):
        body_contents.append({
            "type": "separator",
            "color": "#DDDDDD",
            "margin": "xl"
        })

        if profile.get("Q5"):
            challenges = profile["Q5"]
            if isinstance(challenges, list) and challenges:
                body_contents.append({
                    "type": "text",
                    "text": f"📌 您的理財挑戰：{', '.join(challenges)}",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True,
                    "margin": "lg"
                })

        if profile.get("Q7"):
            body_contents.append({
                "type": "text",
                "text": f"📌 年度理財預算：{profile['Q7']}",
                "size": "sm",
                "color": "#666666",
                "wrap": True,
                "margin": "sm"
            })

        if profile.get("Q8"):
            body_contents.append({
                "type": "text",
                "text": f"📌 最想解決的問題：{profile['Q8']}",
                "size": "sm",
                "color": "#666666",
                "wrap": True,
                "margin": "sm"
            })

    # 加入查看完整解說按鈕（PDF）
    body_contents.append({
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "🎁 領取三招抗通膨秘笈",
                "size": "md",
                "color": "#FFFFFF",
                "align": "center",
                "weight": "bold"
            }
        ],
        "backgroundColor": "#408080",
        "cornerRadius": "lg",
        "paddingAll": "md",
        "margin": "xl",
        "action": {
            "type": "uri",
            "label": "領取三招抗通膨秘笈",
            "uri": "https://drive.google.com/file/d/1EJ3NQ0f_DLZX75RCLM3OQRAHx61L7jZM/view?usp=sharing"
        }
    })

    # 加入重新測試按鈕
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
        "margin": "md",
        "action": {
            "type": "message",
            "text": "VIP 財富健康體檢表"
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


@handler.add(FollowEvent)
def handle_follow(event):
    """處理用戶加入好友事件"""
    user_id = event.source.user_id

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 開始註冊流程
        result = start_registration(user_id)

        if result == "already_registered":
            # 已註冊用戶，顯示歡迎訊息
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="歡迎回來！\n\n"
                                 "請輸入「VIP 財富健康體檢表」開始測試。"
                        )
                    ]
                )
            )
        else:
            # 新用戶，開始註冊
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請輸入你的姓名：")
                    ]
                )
            )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 檢查是否在註冊流程中
        if is_user_in_registration(user_id):
            status, data = process_registration(user_id, user_message)

            if status == "completed":
                # 建立註冊完成 + 開始測試按鈕的 Flex Message
                flex_content = {
                    "type": "bubble",
                    "size": "kilo",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{data['name']}，歡迎加入！",
                                "size": "lg",
                                "color": "#333333",
                                "weight": "bold"
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "開始導航",
                                        "size": "md",
                                        "color": "#FFFFFF",
                                        "align": "center",
                                        "weight": "bold"
                                    }
                                ],
                                "backgroundColor": "#408080",
                                "cornerRadius": "lg",
                                "paddingAll": "lg",
                                "margin": "xl",
                                "action": {
                                    "type": "message",
                                    "text": "VIP 財富健康體檢表"
                                }
                            }
                        ],
                        "backgroundColor": "#F5F5F5",
                        "paddingAll": "xl"
                    }
                }

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            FlexMessage(
                                alt_text="註冊完成",
                                contents=FlexContainer.from_dict(flex_content)
                            )
                        ]
                    )
                )
                return

        # 檢查是否要開始測試
        if user_message in ["VIP 財富健康體檢表", "開始測試", "壓力測試", "測試"]:
            if is_user_in_test(user_id):
                cancel_test(user_id)

            question = start_test(user_id)

            intro_message = TextMessage(
                text="📋 VIP 財富健康體檢表\n\n"
                     "歡迎參加VIP 財富健康體檢表！\n"
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
                        messages=[TextMessage(text="已取消測試。如需重新開始，請輸入「VIP 財富健康體檢表」。")]
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
                # 更新 Google Sheets 測試結果
                update_test_result(user_id, data['score'], data['level'])

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_result_flex(data)]
                    )
                )
            return

        # 非指定訊息不回覆
        pass


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


@handler.add(PostbackEvent)
def handle_postback(event):
    """處理 postback 事件（多選題用）"""
    user_id = event.source.user_id
    postback_data = event.postback.data

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 檢查是否在測試中
        if not is_user_in_test(user_id):
            return

        # 處理「完成選擇」
        if postback_data == "complete_multiple":
            status, data = process_answer(user_id, "完成")

            if status == "need_selection":
                # 用戶還沒選擇任何選項，提示並重新顯示題目
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="請至少選擇一個選項"),
                            create_question_flex(data)
                        ]
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
                # 更新 Google Sheets 測試結果
                update_test_result(user_id, data['score'], data['level'])

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_result_flex(data)]
                    )
                )
            return

        # 處理選項選擇（toggle:A, toggle:B 等，或直接是 A, B, C, D）
        if postback_data.startswith("toggle:"):
            answer = postback_data.split(":")[1]
        else:
            answer = postback_data

        status, data = process_answer(user_id, answer)

        if status == "multiple_continue":
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[create_multiple_continue_flex(data["question"], data["selected"])]
                )
            )
        elif status == "invalid":
            current_question = get_current_question(user_id)
            selected = get_multiple_selections(user_id)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[create_multiple_continue_flex(current_question, selected)]
                )
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
