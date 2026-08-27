import requests
from datetime import date as _date

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_forecast(latitude, longitude, days=7):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Tokyo",
        "forecast_days": days,
    }
    res = requests.get(FORECAST_URL, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()["daily"]
    days_list = []
    for i, d in enumerate(data["time"]):
        days_list.append({
            "date": d,
            "temp_max": data["temperature_2m_max"][i],
            "temp_min": data["temperature_2m_min"][i],
            "precipitation": data["precipitation_sum"][i],
            "rain_prob": data["precipitation_probability_max"][i],
        })
    return days_list


def fetch_day_conditions(latitude, longitude, target_date, start_time=None, end_time=None):
    days_diff = (target_date - _date.today()).days
    url = FORECAST_URL if -7 <= days_diff <= 15 else ARCHIVE_URL
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "Asia/Tokyo",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    }
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()["hourly"]

    if start_time and end_time:
        start_hour, end_hour = start_time.hour, end_time.hour
    else:
        start_hour, end_hour = 0, 23

    temps, hums = [], []
    for i, t in enumerate(data["time"]):
        hour = int(t[11:13])
        if start_hour <= hour <= end_hour:
            if data["temperature_2m"][i] is not None:
                temps.append(data["temperature_2m"][i])
            if data["relative_humidity_2m"][i] is not None:
                hums.append(data["relative_humidity_2m"][i])

    max_temp = max(temps) if temps else None
    max_humidity = max(hums) if hums else None
    return max_temp, max_humidity


def build_advice(days_list):
    advice = []

    dry_days = [d for d in days_list[:3] if d["precipitation"] is not None and d["precipitation"] < 1]
    if len(dry_days) == 3:
        advice.append("向こう3日間はまとまった雨の予報がありません。土の乾き具合を見て水やりを検討してください。")

    frost_days = [d for d in days_list if d["temp_min"] is not None and d["temp_min"] <= 3]
    if frost_days:
        dates = "、".join(d["date"] for d in frost_days)
        advice.append(f"{dates} は最低気温が低く霜のおそれがあります。苗の防寒・べたがけ等を検討してください。")

    hot_days = [d for d in days_list if d["temp_max"] is not None and d["temp_max"] >= 32]
    if hot_days:
        dates = "、".join(d["date"] for d in hot_days)
        advice.append(f"{dates} は気温が高くなる予報です。朝夕の水やりや遮光を検討してください。")

    heavy_rain_days = [d for d in days_list if d["precipitation"] is not None and d["precipitation"] >= 30]
    if heavy_rain_days:
        dates = "、".join(d["date"] for d in heavy_rain_days)
        advice.append(f"{dates} は大雨の予報です。排水対策と、農薬散布はこの前後を避けることを検討してください。")

    if not advice:
        advice.append("向こう1週間で特に注意すべき天候は予報されていません。")

    return advice


def build_weed_advice(weed_records, forecast):
    if not weed_records:
        return ["雑草の状態がまだ記録されていません。作業記録で「雑草の状態」を入力すると、ここにアドバイスが表示されます。"]

    advice = []
    level_order = {"なし": 0, "少ない": 1, "普通": 2, "多い": 3}
    latest = weed_records[0]
    latest_score = level_order.get(latest.weed_level, 0)

    if latest_score >= 3:
        advice.append(f"{latest.work_date.strftime('%Y/%m/%d')}時点で雑草が「多い」状態です。早めの除草・除草剤散布を検討してください。")
    elif latest_score == 2:
        advice.append(f"{latest.work_date.strftime('%Y/%m/%d')}時点で雑草は「普通」の状態です。今後の増加に注意してください。")

    if len(weed_records) >= 2:
        prev_score = level_order.get(weed_records[1].weed_level, 0)
        if latest_score > prev_score:
            advice.append("前回の記録より雑草が増加傾向です。")

    if forecast:
        dry_days = [d for d in forecast[:3] if d["precipitation"] is not None and d["precipitation"] < 1]
        if len(dry_days) == 3 and latest_score >= 2:
            advice.append("向こう3日間は雨が少ない予報です。散布後に雨で流れにくく、除草剤散布に適したタイミングです。")
        rain_soon = [d for d in forecast[:2] if d["precipitation"] is not None and d["precipitation"] >= 5]
        if rain_soon:
            advice.append("近日中にまとまった雨の予報があります。散布する場合は雨の前後を避けてください。")

    if not advice:
        advice.append("現時点で特に注意すべき雑草の状態ではありません。")

    return advice
