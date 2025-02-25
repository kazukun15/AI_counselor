import streamlit as st
import requests
import re

# ------------------------
# ページ設定（最初に実行）
# ------------------------
st.set_page_config(page_title="役場メンタルケア - チャット", layout="wide")

# ------------------------
# ユーザー情報入力（画面上部に表示）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="役場職員", key="user_name")

# ------------------------
# 定数／設定
# ------------------------
# APIキーは .streamlit/secrets.toml に記述してください
# 例: [general] api_key = "YOUR_GEMINI_API_KEY"
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更

# ------------------------
# 会話履歴の初期化
# ------------------------
if "conversation_history" not in st.session_state:
    st.session_state["conversation_history"] = []

# ------------------------
# 関数定義
# ------------------------

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
            return "回答が見つかりませんでした。"
        candidate0 = candidates[0]
        content_val = candidate0.get("content", "")
        if isinstance(content_val, dict):
            parts = content_val.get("parts", [])
            content_str = " ".join([p.get("text", "") for p in parts])
        else:
            content_str = str(content_val)
        content_str = content_str.strip()
        if not content_str:
            return "回答が見つかりませんでした。"
        return remove_json_artifacts(content_str)
    except Exception as e:
        return f"エラー: レスポンス解析に失敗しました -> {str(e)}"

def generate_answer(user_message: str) -> str:
    # ここでは、ユーザーの発言を基に単純なプロンプトを作成し、回答を生成します。
    prompt = f"あなた: {user_message}\n回答:"
    return call_gemini_api(prompt)

def display_chat_bubble(sender: str, message: str):
    if sender == "あなた":
        bubble_html = f"""
        <div style="
            background-color: #DCF8C6;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
        ">
            <strong>{sender}</strong>: {message}
        </div>
        """
    else:  # sender == "回答"
        bubble_html = f"""
        <div style="
            background-color: #FFFACD;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            margin: 5px 0;
            color: #000;
            font-family: Arial, sans-serif;
        ">
            <strong>{sender}</strong>: {message}
        </div>
        """
    st.markdown(bubble_html, unsafe_allow_html=True)

def display_conversation_history(history: list):
    for item in history:
        display_chat_bubble(item["sender"], item["message"])

# ------------------------
# Streamlit アプリ本体
# ------------------------

st.header("会話履歴")
display_conversation_history(st.session_state["conversation_history"])

st.header("メッセージ入力")
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_input")
    submitted = st.form_submit_button("送信")

if submitted and user_message.strip():
    # ユーザーの発言を追加
    st.session_state["conversation_history"].append({"sender": "あなた", "message": user_message})
    # 回答を生成
    answer = generate_answer(user_message)
    st.session_state["conversation_history"].append({"sender": "回答", "message": answer})
    st.experimental_rerun()
