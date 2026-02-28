import os
import time
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import date

APWRIMS_URL = "https://apwrims.ap.gov.in/mis/reservoir/summary/summaryTable"

AP_NAME = "Nagarjuna Sagar Major"
LAT, LON = 16.52, 79.32   # Nagarjuna Sagar coords


def fetch_ns_level_storage():
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(APWRIMS_URL)
    time.sleep(5)
    html = driver.page_source
    driver.quit()

    tables = pd.read_html(html)
    df = tables[2]

    # flatten headers
    df.columns = [
        " | ".join([str(c) for c in col if str(c) != "nan"]).strip()
        for col in df.columns
    ]

    name_col    = "Reservoir | Reservoir"
    level_col   = "Reservoir Level Information & Capacity Details | Current Level (feet)"
    storage_col = "Reservoir Level Information & Capacity Details | Current Storage (T.M.C.)"

    row = df[df[name_col] == AP_NAME]
    if row.empty:
        raise ValueError("Nagarjuna Sagar row not found")

    level_today = float(row[level_col].iloc[0])
    raw_storage = str(row[storage_col].iloc[0])       # e.g. '275.81  (88.39 % )'
    storage_today = float(raw_storage.split()[0])

    return level_today, storage_today


def get_today_weather(lat, lon):
    today = date.today().isoformat()
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
        f"&start_date={today}&end_date={today}&timezone=auto"
    )
    r = requests.get(url)
    r.raise_for_status()
    d = r.json()
    rain = float(d["daily"]["precipitation_sum"][0])
    tmax = float(d["daily"]["temperature_2m_max"][0])
    tmin = float(d["daily"]["temperature_2m_min"][0])
    return rain, tmax, tmin


def build_full_features(level_today, storage_today, rain_today, tmax_today, tmin_today):
    today = pd.Timestamp.today().normalize()

    df = pd.DataFrame([{
        "date": today,
        "storage": storage_today,
        "water_level": level_today,
        "rain_mm": rain_today,
        "temp_max_c": tmax_today,
        "temp_min_c": tmin_today,
    }])

    # if you have past data for NS, you can concat it here before feature engineering

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["dayofyear"] = df["date"].dt.dayofyear
    df["is_monsoon"] = df["month"].between(6, 10).astype(int)
    df["temp_mean_c"] = (df["temp_max_c"] + df["temp_min_c"]) / 2
    df["is_rainy_day"] = (df["rain_mm"] > 0).astype(int)
    df["rain_3d_sum"] = df["rain_mm"].rolling(3, min_periods=1).sum()
    df["rain_7d_sum"] = df["rain_mm"].rolling(7, min_periods=1).sum()
    df["water_level_lag1"] = df["water_level"].shift(1)
    df["water_level_lag3"] = df["water_level"].shift(3)
    df["water_level_lag7"] = df["water_level"].shift(7)
    df["storage_lag1"] = df["storage"].shift(1)
    df["storage_lag3"] = df["storage"].shift(3)
    df["storage_lag7"] = df["storage"].shift(7)
    df["rain_mm_lag1"] = df["rain_mm"].shift(1)
    df["rain_mm_lag3"] = df["rain_mm"].shift(3)
    df["rain_mm_lag7"] = df["rain_mm"].shift(7)
    df["water_level_change_1d"] = df["water_level"] - df["water_level_lag1"]
    df["water_level_change_3d"] = df["water_level"] - df["water_level_lag3"]

    return df.iloc[-1]


if __name__ == "__main__":
    level_today, storage_today = fetch_ns_level_storage()
    rain_today, tmax_today, tmin_today = get_today_weather(LAT, LON)

    row = build_full_features(level_today, storage_today,
                              rain_today, tmax_today, tmin_today)

    # print all feature values clearly
    for col in [
        "date","storage","water_level","rain_mm","temp_max_c","temp_min_c",
        "year","month","dayofyear","is_monsoon","temp_mean_c","is_rainy_day",
        "rain_3d_sum","rain_7d_sum",
        "water_level_lag1","water_level_lag3","water_level_lag7",
        "storage_lag1","storage_lag3","storage_lag7",
        "rain_mm_lag1","rain_mm_lag3","rain_mm_lag7",
        "water_level_change_1d","water_level_change_3d"
    ]:
        print(f"{col}: {row[col]}")
