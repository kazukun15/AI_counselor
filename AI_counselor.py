import streamlit as st
import requests
import re
import random

# ------------------------
# ページ設定（最初に実行）
# ------------------------
st.set_page_config(page_title="役場メンタルケア", layout="wide")

# ------------------------
# ユーザー情報入力（画面上部）
# ------------------------
user_name = st.text_input("あなたの名前を入力してください", value="役場職員", key="user_name")
consult_type = st.radio("相談タイプを選択してください", ("本人の相談", "他者の相談", "発達障害相談"), key="consult_type")

# ------------------------
# 定数／設定
# ------------------------
API_KEY = st.secrets["general"]["api_key"]
MODEL_NAME = "gemini-2.0-flash-001"  # 必要に応じて変更
ROLES = ["精神科医師", "カウンセラー", "メンタリスト", "内科医"]

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
    params = {}
    params["精神科医師"] = {"style": "専門的", "detail": "精神科のナレッジを基に的確な判断を下す"}
    params["カウンセラー"] = {"style": "共感的", "detail": "寄り添いながら優しくサポートする"}
    params["メンタリスト"] = {"style": "洞察力に富んだ", "detail": "多角的な心理学的視点から分析する"}
    params["内科医"] = {"style": "実直な", "detail": "身体面の不調や他の病気を慎重にチェックする"}
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

def generate_combined_answer(question: str, persona_params: dict) -> str:
    current_user = st.session_state.get("user_name", "ユーザー")
    consult_type = st.session_state.get("consult_type", "本人の相談")
    if consult_type == "発達障害相談":
        consult_info = ("この相談は大人の発達障害（例：ADHDなど）に関するものです。"
                        "信頼できる公的機関や学術論文を参照し、正確な情報に基づいた回答をお願いします。")
    elif consult_type == "他者の相談":
        consult_info = "この相談は、他者が抱える障害に関するものです。専門的な視点から客観的な判断をお願いします。"
    else:
        consult_info = "この相談は本人が抱える悩みに関するものです。"
        
    prompt = f"【{current_user}さんの質問】\n{question}\n\n{consult_info}\n"
    prompt += "以下は、4人の専門家の視点です：\n"
    for role, params in persona_params.items():
        prompt += f"{role}は【{params['style']}な視点】で、{params['detail']}。\n"
    prompt += (
        "\n上記の意見を統合し、相手の心に寄り添いながら、会話を広げ、"
        "必要に応じて最終診断を行うシンプルで分かりやすい回答を生成してください。\n"
        "回答は自然な日本語で出力してください。"
    )
    return call_gemini_api(prompt)

def continue_combined_answer(additional_input: str, current_discussion: str) -> str:
    prompt = (
        "これまでの会話の流れ:\n" + current_discussion + "\n\n" +
        "ユーザーの追加発言: " + additional_input + "\n\n" +
        "上記の流れを踏まえ、さらに相手に寄り添い、会話を広げながら、"
        "必要なら最終診断を行うシンプルな回答を生成してください。\n"
        "回答は自然な日本語で出力してください。"
    )
    return call_gemini_api(prompt)

def generate_summary(discussion: str) -> str:
    prompt = (
        "以下は4人の統合された会話内容です:\n" + discussion + "\n\n" +
        "この内容を踏まえて、役場職員のメンタルヘルスケアに関するまとめ回答を生成してください。\n"
        "自然な日本語文で出力し、余計なJSON形式は不要です。"
    )
    return call_gemini_api(prompt)

def display_conversation_history(history: list):
    """
    会話履歴を順番通りに上から下に表示します。
    ユーザー発言は「あなた」、システム回答は「回答」として表示します。
    """
    for item in history:
        if item["sender"] == "あなた":
            bubble_html = f"""
            <div style="
                background-color: #DCF8C6 !important;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 8px;
                margin: 5px 0;
                color: #000 !important;
                font-family: Arial, sans-serif !important;
            ">
                <strong>あなた</strong><br>
                {item["message"]}
            </div>
            """
        elif item["sender"] == "回答":
            bubble_html = f"""
            <div style="
                background-color: #FFFACD !important;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 8px;
                margin: 5px 0;
                color: #000 !important;
                font-family: Arial, sans-serif !important;
            ">
                <strong>回答</strong><br>
                {item["message"]}
            </div>
            """
        st.markdown(bubble_html, unsafe_allow_html=True)

# ------------------------
# Streamlit アプリ本体
# ------------------------

st.title("役場メンタルケア - 会話サポート")

# --- 上部：会話履歴表示エリア ---
st.header("会話履歴")
conversation_container = st.empty()

# --- 上部：まとめ回答ボタン ---
if st.button("会話をまとめる"):
    if st.session_state.get("conversation_history", []):
        summary = generate_summary("\n".join([f"{item['sender']}: {item['message']}" for item in st.session_state["conversation_history"]]))
        st.session_state["summary"] = summary
        st.markdown("### まとめ回答\n" + "**まとめ:** " + summary)
    else:
        st.warning("まずは会話を開始してください。")

# --- 下部：ユーザー入力エリア ---
st.header("メッセージ入力")
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area("新たな発言を入力してください", placeholder="ここに入力", height=100, key="user_input")
    submit_button = st.form_submit_button("送信")

if submit_button:
    if user_input.strip():
        # conversation_history をリストとして初期化
        if "conversation_history" not in st.session_state or not isinstance(st.session_state["conversation_history"], list):
            st.session_state["conversation_history"] = []
        # ユーザーの発言を追加
        st.session_state["conversation_history"].append({"sender": "あなた", "message": user_input})
        # 統合回答の生成
        persona_params = adjust_parameters(user_input)
        if len(st.session_state["conversation_history"]) == 1:
            combined_answer = generate_combined_answer(user_input, persona_params)
        else:
            context = "\n".join([f"{item['sender']}: {item['message']}" for item in st.session_state["conversation_history"]])
            combined_answer = continue_combined_answer(user_input, context)
        st.session_state["conversation_history"].append({"sender": "回答", "message": combined_answer})
        conversation_container.markdown("### 会話履歴")
        display_conversation_history(st.session_state["conversation_history"])
    else:
        st.warning("発言を入力してください。")
