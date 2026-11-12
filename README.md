# 古詩詞 LINE Bot

這是一個以 Flask 建置的 LINE Messaging API 聊天機器人，可查詢古詩詞內容。

## 功能

- 對「靜夜思」及「登鸛雀樓」提供內建快速回覆測試。
- 其他文字會透過維基文庫搜尋詩詞；遇到同名版本時，會提示使用者以「詩名(作者)」精確查詢。
- 將回覆內容轉換為繁體中文，並限制擷取內容長度以符合 LINE 訊息需求。

## 環境需求

- Python 3
- LINE Messaging API Channel 的 Channel access token 與 Channel secret

## 安裝與本機執行

在專案目錄執行：

```bash
pip install -r requirements.txt
python app.py
```

程式預設會在 `http://localhost:5000` 啟動。LINE 平台需要能連線到公開的 HTTPS 網址；本機測試時可使用 HTTPS tunnel，並將 webhook URL 設定為：

```text
https://<公開網址>/callback
```

部署時，專案根目錄的 `Procfile` 使用 Gunicorn 啟動 Flask app：

```text
web: gunicorn app:app
```

部署平台需支援 Python、安裝 `requirements.txt` 中的套件，並將 LINE webhook URL 指向部署網址的 `/callback` 路徑。

## LINE 憑證安全

目前 `app.py` 將 Channel access token 與 Channel secret 直接寫在程式碼中。部署前請使用自己的憑證，並避免將含有真實憑證的檔案公開或提交到版本控制；若憑證已公開，請到 LINE Developers Console 撤銷並重新產生。

---

# LINE Bot for Classical Chinese Poetry

A LINE Messaging API chatbot built with Flask for searching classical Chinese poems.

## Features

- Provides built-in quick replies for “Quiet Night Thought” (靜夜思) and “Ascending Stork Tower” (登鸛雀樓).
- Searches Wikisource for other queries and asks users to specify `Poem title(Author)` when multiple versions are found.
- Converts returned content to Traditional Chinese and limits the extracted text to fit LINE message requirements.

## Requirements

- Python 3
- A LINE Messaging API channel access token and channel secret

## Install and run locally

Run these commands from the project directory:

```bash
pip install -r requirements.txt
python app.py
```

The app starts at `http://localhost:5000` by default. LINE must be able to reach a public HTTPS URL. For local testing, use an HTTPS tunnel and set the webhook URL to:

```text
https://<public-url>/callback
```

For deployment, the root-level `Procfile` starts the Flask app with Gunicorn:

```text
web: gunicorn app:app
```

Use a Python-compatible hosting platform that installs the packages in `requirements.txt`, and set the LINE webhook URL to the deployed app's `/callback` endpoint.

## Credential security

The current `app.py` contains the LINE channel access token and channel secret directly in the source code. Replace them with your own credentials before deployment, and do not publish or commit files containing real credentials. If credentials have been exposed, revoke and regenerate them in the LINE Developers Console.
