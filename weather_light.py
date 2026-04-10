import os
import time
import hmac
import hashlib
import base64
import uuid
import requests

# --- 環境変数から取得 ---
SWITCHBOT_TOKEN = os.environ["SWITCHBOT_TOKEN"]
SWITCHBOT_SECRET = os.environ["SWITCHBOT_SECRET"]
DEVICE_ID = os.environ["SWITCHBOT_DEVICE_ID"]
CITY_ID = os.environ["WEATHER_CITY_ID"]  # 例: "130010"（東京）

# --- 天気予報API ---
def get_rain_probability(city_id: str) -> int:
    url = f"https://weather.tsukumijima.net/api/forecast/city/{city_id}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    # 今日の12〜24時の降水確率を取得
    forecasts = data["forecasts"][0]["chanceOfRain"]
    rain_values = []
    for key in ["T12_18", "T18_24"]:
        val = forecasts.get(key, "0%").replace("%", "")
        if val.lstrip("-").isdigit():
            rain_values.append(int(val))

    return max(rain_values) if rain_values else 0


# --- SwitchBot API認証ヘッダー生成 ---
def build_headers(token: str, secret: str) -> dict:
    nonce = str(uuid.uuid4())
    t = str(int(time.time() * 1000))
    string_to_sign = token + t + nonce
    sign = base64.b64encode(
        hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Authorization": token,
        "sign": sign,
        "nonce": nonce,
        "t": t,
        "Content-Type": "application/json",
    }


# --- SwitchBotデバイスにコマンド送信 ---
def send_command(device_id: str, command: dict):
    url = f"https://api.switch-bot.com/v1.1/devices/{device_id}/commands"
    headers = build_headers(SWITCHBOT_TOKEN, SWITCHBOT_SECRET)
    res = requests.post(url, headers=headers, json=command)
    res.raise_for_status()
    return res.json()


# --- メイン処理 ---
def main():
    rain = get_rain_probability(CITY_ID)
    print(f"降水確率: {rain}%")

    # ライトをON
    send_command(DEVICE_ID, {"command": "turnOn", "parameter": "default", "commandType": "command"})

    if rain >= 50:
        # 青く点灯（R=0, G=0, B=255）
        send_command(DEVICE_ID, {
            "command": "setColor",
            "parameter": "0:0:255",
            "commandType": "command"
        })
        send_command(DEVICE_ID, {
            "command": "setBrightness",
            "parameter": "80",
            "commandType": "command"
        })
        print("雨予報あり → 青で点灯")
    else:
        # 通常の白
        send_command(DEVICE_ID, {
            "command": "setColor",
            "parameter": "255:255:255",
            "commandType": "command"
        })
        send_command(DEVICE_ID, {
            "command": "setBrightness",
            "parameter": "80",
            "commandType": "command"
        })
        print("雨予報なし → 白で点灯")


if __name__ == "__main__":
    main()
