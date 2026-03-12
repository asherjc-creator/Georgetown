import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from datetime import timedelta
from PIL import Image
import base64
from io import BytesIO

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Georgetown Inn Revenue Portal",
    layout="wide",
    page_icon="🏨"
)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_image_base64(image_path):
    try:
        img = Image.open(image_path)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    except:
        return ""

# --------------------------------------------------
# STYLE
# --------------------------------------------------

st.markdown("""
<style>
.main {background-color:#f5f7f9;}
.stMetric {
background:white;
padding:15px;
border-radius:10px;
box-shadow:2px 2px 5px rgba(0,0,0,0.05);
}
.event-card{
padding:10px;
border-left:5px solid #ff4b4b;
background:white;
margin-bottom:8px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    df = pd.read_csv("georgetown_inn_data.csv")
    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Core hotel metrics
    df["ADR"] = df["Room_Revenue"] / df["Rooms_Sold"]
    df["Occupancy"] = df["Rooms_Sold"] / df["Total_Rooms"]
    df["RevPAR"] = df["Room_Revenue"] / df["Total_Rooms"]

    # Market benchmarking
    df["MPI"] = (df["Occupancy"] / df["Market_Occ"]) * 100
    df["RGI"] = (df["RevPAR"] / (df["Market_ADR"] * df["Market_Occ"])) * 100

    # Clean Comp Data
    comp = pd.read_csv("competitor_rates.csv")
    comp = comp[comp["Date"] != "Date"]  # Remove duplicate headers
    comp["Date"] = pd.to_datetime(comp["Date"])
    comp["Rate"] = pd.to_numeric(comp["Rate"], errors="coerce")

    # Fallback for Events
    try:
        events = pd.read_csv("events_dc.csv")
        events["Date"] = pd.to_datetime(events["Date"])
    except FileNotFoundError:
        events = pd.DataFrame([
            {"Date": "2026-04-10", "Event": "Cherry Blossom Festival", "Impact_Level": "High"},
            {"Date": "2026-07-04", "Event": "Independence Day", "Impact_Level": "High"}
        ])
        events["Date"] = pd.to_datetime(events["Date"])

    return df, comp, events


df, comp, events = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    profile = get_image_base64("asher_picture.png")

    if profile:
        st.markdown(
            f'<img src="{profile}" style="border-radius:50%;width:140px;display:block;margin:auto;">',
            unsafe_allow_html=True
        )

    st.markdown("<h3 style='text-align:center;'>Asher Jannu</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Revenue Analyst</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("[View GitHub Repo](https://github.com/asherjc-creator/georgetown-revenue-dashboard)")
    st.markdown("---")

    # Safe Date Input Logic
    date_val = st.date_input(
        "Select Date Range",
        [df["Date"].min(), df["Date"].max()]
    )
    
    if isinstance(date_val, list) and len(date_val) == 2:
        start_date, end_date = date_val
    else:
        start_date = end_date = date_val[0] if isinstance(date_val, list) else date_val

# --------------------------------------------------
# FILTER DATA
# --------------------------------------------------

filtered = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy() # Use copy to avoid SettingWithCopy warning on Pickup curve

comp_filtered = comp[
    (comp["Date"].dt.date >= start_date) &
    (comp["Date"].dt.date <= end_date)
]

# --------------------------------------------------
# HEADER
# --------------------------------------------------

logo = get_image_base64("logo.png")

if logo:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:20px;">
        <img src="{logo}" width="120">
        <h1>Georgetown Inn Revenue Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)
else:
    st.title("🏨 Georgetown Inn Revenue Dashboard")

# --------------------------------------------------
# KPI METRICS
# --------------------------------------------------

c1, c2, c3, c4 = st.columns(4)

c1.metric("ADR", f"${filtered['ADR'].mean():.2f}")
c2.metric("Occupancy", f"{filtered['Occupancy'].mean()*100:.1f}%")
c3.metric("RevPAR", f"${filtered['RevPAR'].mean():.2f}")
c4.metric("RGI", f"{filtered['RGI'].mean():.1f}")

# --------------------------------------------------
# CHARTS ROW 1
# --------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    st.subheader("Revenue & RevPAR Trend")
    fig_rev = px.line(filtered, x="Date", y=["Room_Revenue","RevPAR"])
    st.plotly_chart(fig_rev, use_container_width=True)

with col2:
    st.subheader("Booking Pickup Curve")
    filtered["Pickup"] = filtered["Rooms_Sold"].diff()
    fig_pickup = px.bar(filtered, x="Date", y="Pickup")
    st.plotly_chart(fig_pickup, use_container_width=True)

# --------------------------------------------------
# CHARTS ROW 2
# --------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.subheader("Market Benchmark Performance")
    fig_index = px.line(filtered, x="Date", y=["MPI","RGI"])
    st.plotly_chart(fig_index, use_container_width=True)

with col4:
    st.subheader("Competitor Rate Comparison")
    fig_comp = px.line(comp_filtered, x="Date", y="Rate", color="Hotel")
    st.plotly_chart(fig_comp, use_container_width=True)

# --------------------------------------------------
# 90 DAY FORECAST
# --------------------------------------------------
st.markdown("---")
st.subheader("📈 90 Day ADR Forecast")

last_date = df["Date"].max()
future_dates = pd.date_range(last_date + timedelta(days=1), periods=90)

market_rates = comp.groupby("Date")["Rate"].mean()

forecast = pd.DataFrame({"Date": future_dates})

# Updated pandas syntax (ffill replaces method='ffill')
forecast["Market_Trend"] = market_rates.reindex(future_dates).ffill().values

forecast = forecast.merge(events, on="Date", how="left")
forecast["Impact_Level"] = forecast["Impact_Level"].fillna("None")
forecast["Event"] = forecast["Event"].fillna("No Major Event")

event_multipliers = {
    "High": 1.25,
    "Medium": 1.1,
    "Low": 1.05,
    "None": 1.0
}

forecast["Predicted_ADR"] = forecast.apply(
    lambda x: x["Market_Trend"] * event_multipliers.get(x["Impact_Level"], 1.0),
    axis=1
)

fig_forecast = go.Figure()
fig_forecast.add_trace(go.Scatter(x=forecast["Date"], y=forecast["Predicted_ADR"], name="Predicted ADR", line=dict(color="green")))
fig_forecast.add_trace(go.Scatter(x=forecast["Date"], y=forecast["Market_Trend"], name="Market Baseline", line=dict(dash="dash", color="gray")))
st.plotly_chart(fig_forecast, use_container_width=True)

# --------------------------------------------------
# MAPS & PRICING
# --------------------------------------------------
st.markdown("---")
mcol1, mcol2 = st.columns(2)

with mcol1:
    st.subheader("📍 Competitive Landscape")
    m = folium.Map(location=[38.9055,-77.0620], zoom_start=14)
    folium.Marker([38.9055,-77.0620], popup="Georgetown Inn", icon=folium.Icon(color="blue")).add_to(m)
    
    competitors = [
        ("Four Seasons DC",[38.9052,-77.0581]),
        ("Rosewood DC",[38.9045,-77.0625]),
        ("Ritz Carlton Georgetown",[38.9031,-77.0615])
    ]
    for name,loc in competitors:
        folium.CircleMarker(location=loc, radius=8, popup=name, color="red", fill=True).add_to(m)
    
    st_folium(m, width="100%", height=350)

with mcol2:
    st.subheader("🔥 Geographic Demand Heatmap")
    m2 = folium.Map(location=[38.9055,-77.0620], zoom_start=4)
    heat_data = df[["Lat","Lon"]].dropna().values.tolist()
    HeatMap(heat_data).add_to(m2)
    st_folium(m2, width="100%", height=350)

# --------------------------------------------------
# BOTTOM ROW
# --------------------------------------------------
st.markdown("---")
bcol1, bcol2 = st.columns(2)

with bcol1:
    st.subheader("🤖 AI Pricing Recommendation")
    latest_occ = df["Occupancy"].iloc[-1]
    latest_adr = df["ADR"].iloc[-1]

    if latest_occ > 0.90:
        suggested = latest_adr * 1.15
        st.success(f"High demand detected. Suggested ADR: **${suggested:.0f}**")
    elif latest_occ > 0.75:
        suggested = latest_adr * 1.05
        st.info(f"Moderate demand. Suggested ADR: **${suggested:.0f}**")
    else:
        suggested = latest_adr * 0.92
        st.warning(f"Low demand. Suggested ADR: **${suggested:.0f}**")

with bcol2:
    st.subheader("🚩 Upcoming High Impact Events")
    # Make sure we only show future events
    upcoming = events[events["Date"] > pd.Timestamp.now()].sort_values("Date").head(5)
    
    if upcoming.empty:
        st.write("No major upcoming events logged.")
    else:
        for _,row in upcoming.iterrows():
            st.markdown(f"""
            <div class="event-card">
            <b>{row['Date'].strftime('%b %d, %Y')}</b> — {row['Event']}<br>
            Impact: {row['Impact_Level']}
            </div>
            """, unsafe_allow_html=True)
