import streamlit as st
import pandas as pd
import requests
import os
from streamlit_autorefresh import st_autorefresh

# CONFIG
WAQI_TOKEN = "28cdb5ed98eb5696e644208c3d0d69272a1be092"
WAQI_URL = f"https://api.waqi.info/feed/delhi/?token={WAQI_TOKEN}"

st.set_page_config(
    page_title="Ward-wise AQI Dashboard",
    layout="wide"
)

# UTIL FUNCTIONS
def ensure_aqi_history(wards_df, filename="aqi_history.csv"):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        rows = []
        for w in wards_df["ward_no"].unique():
            rows.append({
                "ward_no": w,
                "day1": 150,
                "day2": 155,
                "day3": 160,
                "day4": 165,
                "day5": 170
            })
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False)
        return df

    try:
        df = pd.read_csv(filename)
        required = {"ward_no","day1","day2","day3","day4","day5"}
        if not required.issubset(df.columns):
            raise ValueError
        return df
    except:
        os.remove(filename)
        return ensure_aqi_history(wards_df, filename)

# ================= LOAD DATA =================
wards_df = pd.read_csv("wards.csv")

if "history_df" not in st.session_state:
    st.session_state.history_df = ensure_aqi_history(wards_df)

# ================= AQI FUNCTIONS =================
def fetch_real_aqi():
    try:
        r = requests.get(WAQI_URL, timeout=10, verify=False)
        data = r.json()
        if data.get("status") != "ok":
            return None
        return data["data"]["aqi"]
    except:
        return None

def predict_aqi(ward_no):
    df = st.session_state.history_df
    row = df[df["ward_no"] == ward_no].iloc[0]
    return int(row[["day3","day4","day5"]].mean())

def update_history(ward_no, aqi):
    df = st.session_state.history_df
    idx = df[df["ward_no"] == ward_no].index[0]
    df.loc[idx, ["day1","day2","day3","day4"]] = \
        df.loc[idx, ["day2","day3","day4","day5"]].values
    df.loc[idx, "day5"] = aqi
    df.to_csv("aqi_history.csv", index=False)
    st.session_state.history_df = df

def aqi_category(aqi):
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"

def govt_advice(aqi):
    if aqi > 300:
        return "GRAP-IV, construction ban, traffic restrictions"
    elif aqi > 200:
        return "Traffic control, water sprinkling"
    else:
        return "Normal monitoring"

def public_advice(aqi):
    if aqi > 300:
        return "Stay indoors, use N95 masks"
    elif aqi > 200:
        return "Reduce outdoor activity"
    else:
        return "Normal activity allowed"

# ================= TITLE =================
st.title("🌫️ Ward-wise AQI Dashboard")
st.caption("Real-time AQI using WAQI (CPCB aggregated data)")

# 🔝 AQI RESULT PLACEHOLDER (TOP)
result_container = st.empty()

# =================================================
# 🎛️ LEFT SIDEBAR CONTROLS
# =================================================
st.sidebar.title("🎛️ Controls")

zone = st.sidebar.selectbox(
    "Select Zone",
    wards_df["zone"].unique()
)

zone_wards = wards_df[wards_df["zone"] == zone]

ward_name = st.sidebar.selectbox(
    "Select Ward",
    zone_wards["ward_name"]
)

ward_no = zone_wards[
    zone_wards["ward_name"] == ward_name
]["ward_no"].values[0]

get_data = st.sidebar.button("Get AQI Data")

# =================================================
# 🎯 FETCH AQI → SHOW AT TOP
# =================================================
if get_data:

    aqi = fetch_real_aqi()
    if aqi is None:
        with result_container.container():
            st.error("Failed to fetch AQI")
        st.stop()

    update_history(ward_no, aqi)
    predicted = predict_aqi(ward_no)

    with result_container.container():
        st.success("AQI fetched successfully")

        c1, c2 = st.columns(2)
        c1.metric("Current AQI", aqi)
        c2.metric("Predicted AQI", predicted)

        st.write("📍 Zone:", zone)
        st.write("🏘️ Ward:", ward_name)
        st.write("📊 Category:", aqi_category(aqi))

        st.subheader("🏛️ Government Advisory")
        st.info(govt_advice(aqi))

        st.subheader("👨‍👩‍👧 Public Advisory")
        st.warning(public_advice(aqi))

# =================================================
# 🔄 AUTO REFRESH RANKINGS EVERY 15 SECONDS
# =================================================
st_autorefresh(interval=15 * 1000, key="ranking_refresh")

# =================================================
# 🔝 RANKINGS (ALWAYS LIVE)
# =================================================
df = st.session_state.history_df.copy()
df["avg_aqi"] = df[["day1","day2","day3","day4","day5"]].mean(axis=1)
df = df.merge(wards_df, on="ward_no")

st.subheader("🏘️ Ward Pollution Ranking")

r1, r2 = st.columns(2)

with r1:
    st.markdown("### 🔴 Top 10 Most Polluted Wards")
    st.dataframe(
        df.sort_values("avg_aqi", ascending=False)
        [["ward_name","zone","avg_aqi"]].head(10),
        use_container_width=True
    )

with r2:
    st.markdown("### 🟢 Top 10 Least Polluted Wards")
    st.dataframe(
        df.sort_values("avg_aqi", ascending=True)
        [["ward_name","zone","avg_aqi"]].head(10),
        use_container_width=True
    )

st.subheader("📍 Zone Pollution Ranking")

zone_avg = df.groupby("zone")["avg_aqi"].mean().reset_index()

z1, z2 = st.columns(2)

with z1:
    st.markdown("### 🔴 Top 10 Most Polluted Zones")
    st.dataframe(
        zone_avg.sort_values("avg_aqi", ascending=False).head(10),
        use_container_width=True
    )

with z2:
    st.markdown("### 🟢 Top 10 Least Polluted Zones")
    st.dataframe(
        zone_avg.sort_values("avg_aqi", ascending=True).head(10),
        use_container_width=True
    )

