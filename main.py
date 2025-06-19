import os
import logging
from flask import Flask, jsonify
import requests

app = Flask(__name__)

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
GROUP_ID = os.environ.get('LINE_GROUP_ID')
ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')

# 啟動時檢查環境變數
if not GROUP_ID or not ACCESS_TOKEN:
    logger.error("請設定 LINE_GROUP_ID 與 LINE_ACCESS_TOKEN 環境變數。")
    raise RuntimeError("缺少必要的 LINE Bot 設定！")

def check_mrt_status() -> str:
    """
    實際部署時可改為查詢 TDX API。
    """
    return "🚨 這是一則來自 Cloud Run 的 LINE Bot 測試訊息！！"

def send_line_message(message: str) -> bool:
    """
    發送訊息到 LINE 群組。成功回傳 True，失敗回傳 False。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    data = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        response = requests.post(LINE_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info("LINE 訊息已送出")
        return True
    except requests.RequestException as e:
        logger.error(f"LINE 訊息發送失敗: {e}")
        return False

@app.route("/", methods=["GET"])
def run_check():
    msg = check_mrt_status()
    if msg:
        success = send_line_message(msg)
        if success:
            return jsonify({"status": "success", "message": msg}), 200
        else:
            return jsonify({"status": "error", "message": "LINE 訊息發送失敗"}), 500
    return jsonify({"status": "ok", "message": "一切正常"}), 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
