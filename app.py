from __future__ import annotations
import os

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from opencc import OpenCC
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# 初始化繁簡轉換器
s2t = OpenCC("s2t")  # 簡轉繁
t2s = OpenCC("t2s")  # 繁轉簡

# --- LINE 密鑰設定 ---
# 改從系統環境變數中讀取，如果沒有就用空字串
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN", "你的新Token")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "你的新Secret")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


def fetch_from_wikisource(poem_name):
    """
    使用維基文庫 API 搜尋，若有多筆結果會先提示使用者，
    並直接在下方顯示最相關的第一筆內容。
    """
    headers = {"User-Agent": "PoemBot/1.0 (Personal Line Bot)"}
    search_url = "https://zh.wikisource.org/w/api.php"

    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": poem_name,
        "format": "json",
        "utf8": 1,
    }

    try:
        res = requests.get(search_url, params=search_params, headers=headers, timeout=5)
        data = res.json()
        search_results = data.get("query", {}).get("search", [])

        if not search_results:
            return (
                f"找不到《{poem_name}》。請確認是否有錯別字，或嘗試輸入「詩名(作者)」"
            )

        # 檢查是否有超過一筆搜尋結果
        multiple_hint = ""
        if len(search_results) > 1:
            # 抓出前幾筆的標題讓使用者知道還有其他版本
            titles = [item["title"] for item in search_results[:3]]
            multiple_hint = (
                f"🔍 找到多筆相關內容（例如：{', '.join(titles)} 等），以下為您直接顯示第一筆：\n"
                + "—" * 15
                + "\n\n"
            )

        # 取得最相關的第一筆標題
        best_title = search_results[0]["title"]

        # 透過 parse API 取得頁面乾淨純文字
        parse_params = {
            "action": "parse",
            "page": best_title,
            "prop": "text",
            "format": "json",
            "utf8": 1,
        }
        parse_res = requests.get(
            search_url, params=parse_params, headers=headers, timeout=5
        )
        parse_data = parse_res.json()

        if "parse" not in parse_data:
            return f"暫時無法取得《{poem_name}》的內容。"

        html_content = parse_data["parse"]["text"]["*"]
        soup = BeautifulSoup(html_content, "html.parser")

        # 移除不需要的導航、表格等區塊
        for unwanted in soup.find_all(
            ["table", "ul", "div"], class_=["navbox", "ambox", "toc", "printfooter"]
        ):
            unwanted.decompose()

        # 萃取內文
        raw_text = soup.get_text()
        clean_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        content_body = "\n".join(clean_lines[:40])

        if content_body:
            return (
                multiple_hint
                + f"《{s2t.convert(best_title)}》\n\n{s2t.convert(content_body)}"
            )

    except Exception as e:
        print(f"Error fetching from wikisource: {e}")

    return f"暫時無法取得《{poem_name}》的內容，請稍後再試。"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        abort(400)
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()

    poems = {
        "靜夜思": "床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。",
        "登鸛雀樓": "白日依山盡，黃河入海流。欲窮千里目，更上一層樓。",
    }

    if user_msg in poems:
        reply_msg = f"【內建快速搜尋】\n《{user_msg}》：\n\n{poems[user_msg]}"
    else:
        reply_msg = fetch_from_wikisource(user_msg)

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
