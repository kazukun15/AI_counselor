import streamlit as st
import requests
import re
import random
from streamlit_chat import message  # streamlit-chat のメッセージ表示用関数

# ------------------------
# ページ設定
# ------------------------
st.set_page_config(page_title="ぼくのともだち", layout="wide")
st.title("ぼくのともだち V2.2.1")

# ------------------------
# 背景画像の設定（インラインCSS）
# ------------------------
st.markdown(
    """
    <style>
    body {
        background-image: url("https://your-image-url.com/background.png");
        background-size: cover;
        background-attachment: fixed;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------
# ユーザーの名前入力（上部）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="ユーザー", key="user_name")

# ------------------------
# 定数／設定
# ------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
NAMES = ["ゆかり", "しんや", "みのる"]

# ------------------------
# 関数定義
# ------------------------

def analyze_question(question: str) -> int:
    score = 0
    keywords_emotional = ["困った", "悩み", "苦しい", "辛い"]
    keywords_logical = ["理由", "原因", "仕組み", "方法"]
    for word in keywords_emotional:
        if re.search(word, question):
            score += 1
    for word in keywords_logical:
        if re.search(word, question):
            score -= 1
    return score

def adjust_parameters(question: str) -> dict:
    score = analyze_question(question)
    params = {}
    params["ゆかり"] = {"style": "明るくはっちゃけた", "detail": "楽しい雰囲気で元気な回答"}
    if score > 0:
        params["しんや"] = {"style": "共感的", "detail": "心情を重視した解説"}
        params["みのる"] = {"style": "柔軟", "detail": "状況に合わせた多面的な視点"}
    else:
        params["しんや"] = {"style": "分析的", "detail": "データや事実を踏まえた説明"}
        params["みのる"] = {"style": "客観的", "detail": "中立的な視点からの考察"}
    return params

def remove_json_artifacts(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    pattern = r"'parts': \[\{'text':.*?\}\], 'role': 'model'"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned.strip()

def call_gemini_api(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        return f"エラー: リクエスト送信時に例外が発生しました -> {str(e)}"
    if response.status_code != 200:
        return f"エラー: ステータスコード {response.status_code} -> {response.text}"
    try:
        rjson = response.json()
        candidates = rjson.get("candidates", [])
        if not candidates:
            return "回答が見つかりませんでした。(candidatesが空)"
        candidate0 = candidates[0]
        content_val = candidate0.get("content", "")
        if isinstance(content_val, dict):
            parts = content_val.get("parts", [])
            content_str = " ".join([p.get("text", "") for p in parts])
        else:
            content_str = str(content_val)
        content_str = content_str.strip()
        if not content_str:
            return "回答が見つかりませんでした。(contentが空)"
        return remove_json_artifacts(content_str)
    except Exception as e:
        return f"エラー: レスポンス解析に失敗しました -> {str(e)}"

def generate_discussion(question: str, persona_params: dict) -> str:
    current_user = st.session_state.get("user_name", "ユーザー")
    prompt = f"【{current_user}さんの質問】\n{question}\n\n"
    for name, params in persona_params.items():
        prompt += f"{name}は【{params['style']}な視点】で、{params['detail']}。\n"
    prompt += (
        "\n上記情報を元に、3人が友達同士のように自然な会話をしてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def continue_discussion(additional_input: str, current_discussion: str) -> str:
    prompt = (
        "これまでの会話:\n" + current_discussion + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記を踏まえ、3人がさらに自然な会話を続けてください。\n"
        "出力形式は以下の通りです。\n"
        "ゆかり: 発言内容\n"
        "しんや: 発言内容\n"
        "みのる: 発言内容\n"
        "余計なJSON形式は入れず、自然な日本語の会話のみを出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は3人の会話内容です。\n" + discussion + "\n\n" +
        "この会話を踏まえて、質問に対するまとめ回答を生成してください。\n"
        "自然な日本語文で出力し、余計なJSON形式は不要です。"
    )
    return call_gemini_api(prompt)

def generate_new_character() -> tuple:
    candidates = [
        ("たけし", "冷静沈着で皮肉屋、どこか孤高な存在"),
        ("さとる", "率直かつ辛辣で、常に現実を鋭く指摘する"),
        ("りさ", "自由奔放で斬新なアイデアを持つ、ユニークな感性の持ち主"),
        ("けんじ", "クールで合理的、論理に基づいた意見を率直に述べる"),
        ("なおみ", "独創的で個性的、常識にとらわれず新たな視点を提供する")
    ]
    return random.choice(candidates)

def display_chat_log(chat_log: list):
    """
    chat_log の各メッセージを、各キャラクターのアバター画像を横に表示する形で、
    会話履歴エリアに表示します。会話は古いものが上、最新が下に表示され、
    最新の発言が入力バーの直上に表示されます。
    """
    # GitHubリポジトリ内の avatars フォルダ内の画像を参照（パスは相対パス）
    avatar_map = {
        "ユーザー": "avatars/user.png",
        "ゆかり": "avatars/yukari.png",
        "しんや": "avatars/shinya.png",
        "みのる": "avatars/minoru.png",
        "新キャラクター": "avatars/new_character.png"
    }
    style_map = {
        "ユーザー": {"bg": "#E0FFFF", "align": "right"},
        "ゆかり": {"bg": "#FFB6C1", "align": "left"},
        "しんや": {"bg": "#ADD8E6", "align": "left"},
        "みのる": {"bg": "#90EE90", "align": "left"},
        "新キャラクター": {"bg": "#FFFACD", "align": "left"}
    }
    for msg in chat_log:
        sender = msg["sender"]
        text = msg["message"]
        avatar = avatar_map.get(sender, "")
        style = style_map.get(sender, {"bg": "#F5F5F5", "align": "left"})
        if sender == "ユーザー":
            html_content = f"""
            <div style="display: flex; justify-content: flex-end; align-items: center; margin: 5px 0;">
                <div style="max-width: 70%; background-color: {style['bg']}; border: 1px solid #ddd; border-radius: 10px; padding: 8px; margin-right: 10px;">
                    {text}
                </div>
                <img src="{avatar}" style="width:40px; height:40px; border-radius:50%;">
            </div>
            """
        else:
            html_content = f"""
            <div style="display: flex; justify-content: flex-start; align-items: center; margin: 5px 0;">
                <img src="{avatar}" style="width:40px; height:40px; border-radius:50%; margin-right: 10px;">
                <div style="max-width: 70%; background-color: {style['bg']}; border: 1px solid #ddd; border-radius: 10px; padding: 8px;">
                    {sender}: {text}
                </div>
            </div>
            """
        st.markdown(html_content, unsafe_allow_html=True)

# ------------------------
# セッションステートの初期化
# ------------------------
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

# ------------------------
# 会話まとめボタン
# ------------------------
if st.button("会話をまとめる"):
    if st.session_state["chat_log"]:
        all_discussion = "\n".join([f'{msg["sender"]}: {msg["message"]}' for msg in st.session_state["chat_log"]])
        summary = generate_summary(all_discussion)
        st.session_state["summary"] = summary
        st.markdown("### まとめ回答\n" + "**まとめ:** " + summary)
    else:
        st.warning("まずは会話を開始してください。")

# ------------------------
# 上部：会話履歴表示エリア（スクロール可能）
# ------------------------
st.markdown(
    """
    <style>
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.header("会話履歴")
st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
if st.session_state["chat_log"]:
    display_chat_log(st.session_state["chat_log"])
else:
    st.markdown("<p style='color: gray;'>ここに会話が表示されます。</p>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------
# 下部：発言入力エリア（別枠）
# ------------------------
st.header("発言バー")
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=80, key="user_input")
    col1, col2 = st.columns(2)
    with col1:
        send_button = st.form_submit_button("送信")
    with col2:
        continue_button = st.form_submit_button("続きを話す")

if send_button:
    if user_input.strip():
        st.session_state["chat_log"].append({"sender": "ユーザー", "message": user_input})
        if len(st.session_state["chat_log"]) == 1:
            persona_params = adjust_parameters(user_input)
            discussion = generate_discussion(user_input, persona_params)
            for line in discussion.split("\n"):
                line = line.strip()
                if line:
                    parts = line.split(":", 1)
                    sender = parts[0]
                    message_text = parts[1].strip() if len(parts) > 1 else ""
                    st.session_state["chat_log"].append({"sender": sender, "message": message_text})
        else:
            new_discussion = continue_discussion(user_input, "\n".join(
                [f'{msg["sender"]}: {msg["message"]}' for msg in st.session_state["chat_log"] if msg["sender"] in NAMES]
            ))
            for line in new_discussion.split("\n"):
                line = line.strip()
                if line:
                    parts = line.split(":", 1)
                    sender = parts[0]
                    message_text = parts[1].strip() if len(parts) > 1 else ""
                    st.session_state["chat_log"].append({"sender": sender, "message": message_text})
    else:
        st.warning("発言を入力してください。")

if continue_button:
    if st.session_state["chat_log"]:
        default_input = "続きをお願いします。"
        new_discussion = continue_discussion(default_input, "\n".join(
            [f'{msg["sender"]}: {msg["message"]}' for msg in st.session_state["chat_log"] if msg["sender"] in NAMES]
        ))
        for line in new_discussion.split("\n"):
            line = line.strip()
            if line:
                parts = line.split(":", 1)
                sender = parts[0]
                message_text = parts[1].strip() if len(parts) > 1 else ""
                st.session_state["chat_log"].append({"sender": sender, "message": message_text})
    else:
        st.warning("まずは会話を開始してください。")
