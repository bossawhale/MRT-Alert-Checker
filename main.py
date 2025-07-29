import os
import logging
import json
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LINE Bot 設定
LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
GROUP_ID = os.environ.get('LINE_GROUP_ID')
ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN')

# TDX 認證用的 Client ID / Secret
TDX_CLIENT_ID = os.environ.get('TDX_CLIENT_ID')
TDX_CLIENT_SECRET = os.environ.get('TDX_CLIENT_SECRET')

# 排程驗證用 Token
CRON_SECRET_TOKEN = os.environ.get('CRON_SECRET_TOKEN')

# 啟動時檢查環境變數
if not GROUP_ID or not ACCESS_TOKEN:
    logger.error("請設定 LINE_GROUP_ID 與 LINE_ACCESS_TOKEN 環境變數。")
    raise RuntimeError("缺少必要的 LINE Bot 設定！")

if not TDX_CLIENT_ID or not TDX_CLIENT_SECRET:
    logger.error("請設定 TDX_CLIENT_ID 與 TDX_CLIENT_SECRET 環境變數。")
    raise RuntimeError("缺少 TDX 認證資訊！")

# ----------- 取得 TDX Token -----------
def get_tdx_token():
    url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": TDX_CLIENT_ID,
        "client_secret": TDX_CLIENT_SECRET
    }

    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise ValueError("回應中未包含 access_token")
        return token
    except Exception as e:
        logger.error(f"[ERROR] 無法取得 TDX Token: {e}")
        return None

# ----------- 查詢捷運狀況 -----------
def check_mrt_status():
    token = get_tdx_token()
    if not token:
        return None

    url = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Alert/TRTC?$top=30&$format=JSON"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        alerts = data.get("Alerts", [])
        if not alerts:
            return None  # 無資料視為正常

        abnormal_messages = []
        for alert in alerts:
            if alert.get("Status") != 1:
                title = alert.get("Title", "異常")
                desc = alert.get("Description", "")
                reason = alert.get("Reason", "")
                effect = alert.get("Effect", "")
                abnormal_messages.append(f"🚇 {title}\n📄 {desc}\n📌 原因: {reason}\n⚠️ 影響: {effect}")

        if abnormal_messages:
            return "\n\n".join(abnormal_messages)
        return None  # 全部 status=1 視為正常

    except Exception as e:
        logger.error(f"[ERROR] 查詢 MRT API 時發生錯誤: {e}")
        return None

# ----------- 發送 LINE 訊息 -----------
def send_line_message(message: str) -> bool:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    data = {
        "to": GROUP_ID,
        "messages": [{"type": "text", "text": message}]
    }

    try:
        logger.info(f"送出的 LINE 訊息內容:\n{message}")
        response = requests.post(LINE_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        logger.info("LINE 訊息已送出")
        return True
    except requests.RequestException as e:
        logger.error(f"LINE 訊息發送失敗: {e}")
        try:
            logger.error(f"LINE 回應內容: {response.text}")
        except:
            pass
        return False

# ----------- 主執行入口 -----------
@app.route("/", methods=["GET"])
def run_check():
    # 驗證 Header Token
    token = request.headers.get("Authorization", "")
    if token != f"Bearer {CRON_SECRET_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    debug = request.args.get("debug") == "1"

    msg = check_mrt_status()
    if msg:
        success = send_line_message(msg)
        if success:
            return jsonify({"status": "success", "message": msg}), 200
        else:
            return jsonify({"status": "error", "message": "LINE 訊息發送失敗"}), 500
    elif debug:
        # 若無異常但有 debug query string，回傳 raw data
        token = get_tdx_token()
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            url = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Alert/TRTC?$top=30&$format=JSON"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                return jsonify(resp.json()), 200
            except Exception as e:
                return jsonify({"status": "error", "detail": str(e)}), 500

    return jsonify({"status": "ok", "message": "一切正常"}), 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
