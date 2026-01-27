from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
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


def create_question_message(question, show_part=False):
    """建立帶有 Quick Reply 的問題訊息"""
    options = question["options"]
    is_multiple = question.get("type") == "multiple"

    # 建立 Quick Reply 按鈕
    quick_reply_items = []
    for opt in options:
        quick_reply_items.append(
            QuickReplyItem(
                action=MessageAction(
                    label=opt["label"][:20],  # Quick Reply label 上限 20 字元
                    text=opt["label"][0]  # 只發送 A, B, C, D
                )
            )
        )

    # 多選題加入「完成」按鈕
    if is_multiple:
        quick_reply_items.append(
            QuickReplyItem(
                action=MessageAction(label="✓ 完成", text="完成")
            )
        )

    # 組合題目文字
    question_text = ""
    if show_part:
        question_text = f"【{question['part']}】\n\n"
    question_text += question["question"]

    # 顯示選項
    question_text += "\n"
    for opt in options:
        question_text += f"\n{opt['label']}"

    return TextMessage(
        text=question_text,
        quick_reply=QuickReply(items=quick_reply_items)
    )


def create_multiple_continue_message(question, selected):
    """建立多選題繼續選擇的訊息"""
    selected_text = "、".join(selected)

    quick_reply_items = []
    for opt in question["options"]:
        quick_reply_items.append(
            QuickReplyItem(
                action=MessageAction(
                    label=opt["label"][:20],
                    text=opt["label"][0]
                )
            )
        )
    quick_reply_items.append(
        QuickReplyItem(
            action=MessageAction(label="✓ 完成", text="完成")
        )
    )

    return TextMessage(
        text=f"已選擇：{selected_text}\n\n還要選擇其他選項嗎？選完請按「完成」",
        quick_reply=QuickReply(items=quick_reply_items)
    )


def create_result_message(result):
    """建立測試結果訊息"""
    # 用戶背景資訊
    profile = result.get("profile", {})
    profile_text = ""

    if profile.get("Q5"):
        challenges = profile["Q5"]
        if isinstance(challenges, list) and challenges:
            profile_text += f"\n📌 您的理財挑戰：{', '.join(challenges)}"

    if profile.get("Q7"):
        profile_text += f"\n📌 年度理財預算：{profile['Q7']}"

    if profile.get("Q8"):
        profile_text += f"\n📌 最想解決的問題：{profile['Q8']}"

    message = f"""📊 財務壓力測試結果

{result['level']}

總分：{result['score']} / {result['max_score']} 分

📋 診斷：
{result['description']}

💡 專家建議：
{result['suggestion']}{profile_text}

---
感謝您完成測試！如需再次測試，請輸入「財務壓力測試」。"""

    return TextMessage(text=message)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 檢查是否要開始測試
        if user_message in ["財務壓力測試", "開始測試", "壓力測試", "測試"]:
            # 如果已在測試中，先取消
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
            question_message = create_question_message(question, show_part=True)

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
                                    TextMessage(text="請選擇 A、B、C、D 或輸入「完成」。"),
                                    create_multiple_continue_message(current_question, selected)
                                ]
                            )
                        )
                    else:
                        line_bot_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=event.reply_token,
                                messages=[
                                    TextMessage(text="請選擇 A、B、C 或 D。"),
                                    create_question_message(current_question)
                                ]
                            )
                        )
                else:
                    num_options = len(current_question["options"])
                    valid_options = ["A", "B", "C", "D"][:num_options]
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(text=f"請選擇 {', '.join(valid_options)} 其中一個選項。"),
                                create_question_message(current_question)
                            ]
                        )
                    )
            elif status == "multiple_continue":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_multiple_continue_message(data["question"], data["selected"])]
                    )
                )
            elif status == "next":
                # 檢查是否換了新的 part
                current_q = get_current_question(user_id)
                prev_index = user_sessions_get_prev_index(user_id)
                show_part = should_show_part(prev_index, data)

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_question_message(data, show_part=show_part)]
                    )
                )
            elif status == "complete":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[create_result_message(data)]
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
