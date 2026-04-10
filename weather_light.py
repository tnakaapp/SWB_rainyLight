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
DEVICE_ID_AM = os.environ["SWITCHBOT_DEVICE_ID_AM"]  # 午前用ライト
DEVICE_ID_PM = os.environ["SWITCHBOT_DEVICE_ID_PM"]  # 午後用ライト
CITY_ID = os.environ["WEATHER_CITY_ID"]  # 例: "130010"（東京）

# --- 天気予報API ---
def get_rain_probability(city_id: str) -> tuple[int, int]:
    url = f"https://weather.tsukumijima.net/api/forecast/city/{city_id}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    # forecasts 0:今日 1:明日 2:明後日
    forecasts = data["forecasts"][0]["chanceOfRain"]

    def avg_rain(keys: list[str]) -> int:
        values = []
        for key in keys:
            val = forecasts.get(key, "0%").replace("%", "")
            # テスト用: 各時間帯の降水確率表示
            print(key + ": " + val + "%")
            if val.lstrip("-").isdigit():
                values.append(int(val))
        return int(sum(values) / len(values)) if values else 0

    rain_am = avg_rain(["T00_06", "T06_12"])  # 午前平均
    rain_pm = avg_rain(["T12_18", "T18_24"])  # 午後平均

    return rain_am, rain_pm


# --- SwitchBot認証ヘッダー生成 ---
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


# --- コマンド送信 ---
def send_command(device_id: str, command: dict):
    url = f"https://api.switch-bot.com/v1.1/devices/{device_id}/commands"
    headers = build_headers(SWITCHBOT_TOKEN, SWITCHBOT_SECRET)
    res = requests.post(url, headers=headers, json=command)
    res.raise_for_status()
    return res.json()


# --- ライト制御 ---
def control_light(device_id: str, rain: int, label: str):
    send_command(device_id, {
        "command": "turnOn",
        "parameter": "default",
        "commandType": "command"
    })

    brightness = "15"
    # r = round(255 * (1 - rain / 100))
    # g = round(255 * (1 - rain / 100))
    # b = 255
    # color = f"{r}:{g}:{b}"
    colorTemperature = 0    

    if rain >= 80:
        color = "0:0:255"  # 降水確率80%以上
    elif rain > 60:
        color = "25:25:255"  # 降水確率61-79%
    elif rain > 40:
        color = "50:50:200"  # 降水確率41-59%
    elif rain > 20:
        color = "100:100:255"  # 降水確率21-39%
    elif rain > 0:
        color = "255:255:255"  # 降水確率1-19%
    else:
        color = "255:131:51"  # 降水確率0%
        # colorTemperature = 2700   
    
    print(f"{label}（{rain}%）→ {color} で点灯")

    send_command(device_id, {
        "command": "setColor",
        "parameter": color,
        "commandType": "command"
    })
    send_command(device_id, {
        "command": "setBrightness",
        "parameter": brightness,
        "commandType": "command"
    })
    # send_command(device_id, {
    #     "command": "setColorTemperature",
    #     "parameter": colorTemperature,
    #     "commandType": "command"
    # })


# --- メイン処理 ---
def main():
    rain_am, rain_pm = get_rain_probability(CITY_ID)
    print(f"午前の降水確率: {rain_am}% / 午後の降水確率: {rain_pm}%")

    control_light(DEVICE_ID_AM, rain_am, "午前")
    control_light(DEVICE_ID_PM, rain_pm, "午後")


if __name__ == "__main__":
    main()