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
    使用維基文庫官方 API 搜尋並抓取詩詞內容，
    有效解決傳統 BeautifulSoup 爬蟲因網頁排版不一而抓不準的問題。
    """
    headers = {"User-Agent": "PoemBot/1.0 (Personal Line Bot)"}

    # 1. 先透過 MediaWiki API 進行搜尋，找出最正確的頁面標題
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

        # 取得最相關的第一筆標題
        best_title = search_results[0]["title"]

        # 2. 取得該頁面的完整 HTML 內容來解析內文與消歧義
        page_url = f"https://zh.wikisource.org/wiki/{best_title}"
        response = requests.get(page_url, headers=headers, timeout=5)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            main_output = soup.find("div", class_="mw-parser-output")

            # 檢查是否為「消歧義頁面」（例如有多個朝代或作者同名）
            catlinks = soup.find("div", id="catlinks")
            is_disambig = catlinks and (
                "消歧義" in catlinks.get_text() or "消歧义" in catlinks.get_text()
            )

            if is_disambig and main_output:
                li_tags = main_output.find_all("li")
                author_list = []
                for li in li_tags:
                    if "sisitem" in li.get("class", []):
                        continue
                    text = li.get_text().strip()
                    if text and "消歧義" not in text and "消歧义" not in text:
                        author_list.append(text)

                if author_list:
                    authors_str = "\n".join(author_list)
                    return f"《{s2t.convert(poem_name)}》有多個版本，請輸入「詩名(作者)」精確查詢：\n\n{s2t.convert(authors_str)}"

            # 3. 抓取正文內容（移除不必要的排版區塊）
            if main_output:
                for unwanted in main_output.find_all(
                    ["table", "ul", "div"], class_=["navbox", "ambox", "toc"]
                ):
                    unwanted.decompose()

                # 萃取內文段落
                paragraphs = main_output.find_all(["p", "div"], class_=["poem", "text"])
                if not paragraphs:
                    # 如果沒有特定標籤，直接抓取主區塊文字
                    raw_text = main_output.get_text()
                else:
                    raw_text = "\n".join([p.get_text() for p in paragraphs])

                # 清理多餘空白行
                clean_lines = [
                    line.strip() for line in raw_text.split("\n") if line.strip()
                ]
                content_body = "\n".join(
                    clean_lines[:30]
                )  # 限制長度避免超過 LINE 訊息限制

                if content_body:
                    return (
                        f"《{s2t.convert(best_title)}》\n\n{s2t.convert(content_body)}"
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
