from questions import QUESTIONS, MAX_SCORE, MIN_SCORE

# 用戶測試狀態儲存
user_sessions = {}


def start_test(user_id):
    """開始新的測試，初始化用戶狀態"""
    user_sessions[user_id] = {
        "current_question": 0,
        "answers": [],
        "score": 0,
        "profile": {},  # 儲存非計分題的回答
        "multi_answers": []  # 多選題暫存
    }
    return get_current_question(user_id)


def get_current_question(user_id):
    """取得目前的題目"""
    session = user_sessions.get(user_id)
    if not session:
        return None

    question_index = session["current_question"]
    if question_index >= len(QUESTIONS):
        return None

    return QUESTIONS[question_index]


def process_answer(user_id, answer):
    """處理用戶回答，回傳下一題或測試結果"""
    session = user_sessions.get(user_id)
    if not session:
        return None, None

    current_question = QUESTIONS[session["current_question"]]
    question_type = current_question.get("type", "single")
    is_scored = current_question.get("scored", True)

    # 處理多選題的「完成選擇」
    if question_type == "multiple" and answer.strip() in ["完成", "完成選擇", "OK", "ok", "下一題", "好了", "確定"]:
        # 檢查是否至少選擇了一個選項
        if not session.get("multi_answers"):
            return "need_selection", current_question

        # 儲存多選答案到 profile
        question_key = f"Q{session['current_question'] + 1}"
        session["profile"][question_key] = session.get("multi_answers", [])
        session["answers"].append(session.get("multi_answers", []))
        session["multi_answers"] = []

        session["current_question"] += 1
        if session["current_question"] >= len(QUESTIONS):
            result = get_result(user_id)
            del user_sessions[user_id]
            return "complete", result
        return "next", get_current_question(user_id)

    # 解析答案 (A, B, C, D)
    answer_map = {"A": 0, "B": 1, "C": 2, "D": 3}
    answer_upper = answer.upper().strip()

    # 取得選項索引
    option_index = None
    if answer_upper in answer_map:
        option_index = answer_map[answer_upper]
    elif len(answer_upper) >= 1 and answer_upper[0] in answer_map:
        option_index = answer_map[answer_upper[0]]
    else:
        # 嘗試匹配完整選項文字
        for i, opt in enumerate(current_question["options"]):
            if answer in opt["label"]:
                option_index = i
                break

    if option_index is None:
        return "invalid", None

    # 檢查選項索引是否有效
    if option_index >= len(current_question["options"]):
        return "invalid", None

    selected_option = current_question["options"][option_index]

    # 處理多選題（支援 toggle：再點一次取消選擇）
    if question_type == "multiple":
        value = selected_option.get("value", selected_option["label"])
        if value in session["multi_answers"]:
            # 已選擇 -> 取消選擇
            session["multi_answers"].remove(value)
        else:
            # 未選擇 -> 加入選擇
            session["multi_answers"].append(value)

        return "multiple_continue", {
            "selected": session["multi_answers"],
            "question": current_question
        }

    # 處理單選題
    answer_key = answer_upper[0] if len(answer_upper) > 0 else answer
    session["answers"].append(answer_key)

    # 計分題加分
    if is_scored:
        session["score"] += selected_option.get("score", 0)
    else:
        # 非計分題記錄到 profile
        question_key = f"Q{session['current_question'] + 1}"
        session["profile"][question_key] = selected_option.get("value", selected_option["label"])

    session["current_question"] += 1

    # 檢查是否完成所有題目
    if session["current_question"] >= len(QUESTIONS):
        result = get_result(user_id)
        del user_sessions[user_id]
        return "complete", result

    return "next", get_current_question(user_id)


def get_result(user_id):
    """根據分數產生測試結果"""
    session = user_sessions.get(user_id)
    if not session:
        return None

    score = session["score"]
    profile = session.get("profile", {})

    # 評分等級（分數範圍 5-42）
    if score >= 29:
        level = "🟢【綠色穩健】財富方舟族"
        description = "您已經具備基礎的財富配置架構。"
        suggestion = "下一階段應關注「資產傳承」與「極致避險」，優化您的實體資產比例。"
    elif score >= 16:
        level = "🟡【黃色轉型】財富焦慮族"
        description = "您有一定的理財意識，但工具過於單一（可能只有存款或股票）。在動盪時期，您的資產波動會讓您睡不著覺。"
        suggestion = "建議導入「自動化配置工具」，平衡風險與收益。"
    else:
        level = "🔴【紅色警戒】財富裸奔族"
        description = "您的財富極度缺乏防火牆，一旦通膨加速或收入中斷，生活品質會迅速滑落。"
        suggestion = "您目前最需要的是建立「緊急防禦資產」，先學會鎖住財富價值。"

    return {
        "score": score,
        "max_score": MAX_SCORE,
        "level": level,
        "description": description,
        "suggestion": suggestion,
        "profile": profile
    }


def is_user_in_test(user_id):
    """檢查用戶是否正在進行測試"""
    return user_id in user_sessions


def is_multiple_choice_question(user_id):
    """檢查目前是否為多選題"""
    session = user_sessions.get(user_id)
    if not session:
        return False

    question_index = session["current_question"]
    if question_index >= len(QUESTIONS):
        return False

    return QUESTIONS[question_index].get("type") == "multiple"


def get_multiple_selections(user_id):
    """取得目前多選題已選擇的選項"""
    session = user_sessions.get(user_id)
    if not session:
        return []
    return session.get("multi_answers", [])


def cancel_test(user_id):
    """取消用戶的測試"""
    if user_id in user_sessions:
        del user_sessions[user_id]
        return True
    return False
