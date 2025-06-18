from flask import Flask, request
import requests
import os

app = Flask(__name__)

LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
GROUP_ID = os.environ.get('LINE_GROUP_ID')
ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')

def check_mrt_status():
    # 測試用訊息，實際部署後可替換為 TDX 查詢結果
    return "🚨 這是一則來自 Cloud Run 的 LINE Bot 測試訊息！"

def send_line_message(message):
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        data = {
            "to": GROUP_ID,
            "messages": [{"type": "text", "text": message}]
        }
        response = requests.post(LINE_API_URL, headers=headers, json=data)
        response.raise_for_status()
        print("[INFO] LINE 訊息已送出")
    except requests.RequestException as e:
        print(f"[ERROR] LINE 訊息發送失敗: {e}")

@app.route("/")
def run_check():
    msg = check_mrt_status()
    if msg:
        send_line_message(msg)
        return f"✅ 發送提醒訊息：{msg}", 200
    return "✅ 一切正常", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
