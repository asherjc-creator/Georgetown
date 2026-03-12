import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from datetime import timedelta
import base64
from io import BytesIO
from PIL import Image

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
# STYLING
# --------------------------------------------------

st.markdown("""
<style>
.main { background-color:#f5f7f9; }
.stMetric {
    background-color:white;
    padding:15px;
    border-radius:10px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
}
.event-card {
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

    comp = pd.read_csv("competitor_rates.csv")
    comp["Date"] = pd.to_datetime(comp["Date"])

    events = pd.read_csv("events_dc.csv")
    events["Date"] = pd.to_datetime(events["Date"])

    df = pd.read_csv("georgetown_inn_data.csv")
    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"])

    # Core Metrics
    df["ADR"] = df["Room_Revenue"] / df["Rooms_Sold"]
    df["Occupancy"] = df["Rooms_Sold"] / df["Total_Rooms"]
    df["RevPAR"] = df["Room_Revenue"] / df["Total_Rooms"]

    df["MPI"] = (df["Occupancy"] / df["Market_Occ"]) * 100
    df["RGI"] = (df["RevPAR"] / (df["Market_ADR"] * df["Market_Occ"])) * 100

    return df, comp, events


df, comp, events = load_data()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    pic = get_image_base64("asher_picture.png")

    if pic:
        st.markdown(
            f'<img src="{pic}" style="border-radius:50%;width:140px;">',
            unsafe_allow_html=True
        )

    st.markdown("### Asher Jannu")
    st.markdown("Revenue Analyst")

    st.markdown("---")

    st.markdown("[View Code on GitHub](https://github.com/asherjc-creator/georgetown-revenue-dashboard)")

    st.markdown("---")

    start_date, end_date = st.date_input(
        "Date Range",
        [df["Date"].min(), df["Date"].max()]
    )

# --------------------------------------------------
# FILTER DATA
# --------------------------------------------------

filtered = df[(df["Date"] >= pd.to_datetime(start_date)) &
              (df["Date"] <= pd.to_datetime(end_date))]

comp_filtered = comp[(comp["Date"] >= pd.to_datetime(start_date)) &
                     (comp["Date"] <= pd.to_datetime(end_date))]

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
# REVENUE TREND
# --------------------------------------------------

st.subheader("Revenue & RevPAR Trend")

fig = px.line(filtered, x="Date", y=["Room_Revenue","RevPAR"])
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# MARKET SHARE
# --------------------------------------------------

st.subheader("Market Penetration Index")

fig2 = px.bar(filtered, x="Date", y="MPI", color="MPI",
              color_continuous_scale="RdYlGn")

st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------
# COMPETITOR RATES
# --------------------------------------------------

st.subheader("Competitor Rate Comparison")

fig3 = px.line(comp_filtered, x="Date", y="Rate", color="Hotel")

st.plotly_chart(fig3, use_container_width=True)

# --------------------------------------------------
# 90 DAY FORECAST
# --------------------------------------------------

st.subheader("90 Day ADR Forecast")

last_date = df["Date"].max()

future_dates = pd.date_range(last_date + timedelta(days=1), periods=90)

avg_market = comp.groupby("Date")["Rate"].mean()

forecast = pd.DataFrame({"Date": future_dates})
forecast["Market_Trend"] = avg_market.reindex(future_dates).fillna(method="ffill").values

forecast = forecast.merge(events, on="Date", how="left")
forecast["Impact_Level"] = forecast["Impact_Level"].fillna("None")

multipliers = {"High":1.25,"Medium":1.1,"Low":1.05,"None":1}

forecast["Predicted_ADR"] = forecast.apply(
    lambda x: x["Market_Trend"] * multipliers[x["Impact_Level"]],
    axis=1
)

fig4 = go.Figure()

fig4.add_trace(go.Scatter(
    x=forecast["Date"],
    y=forecast["Predicted_ADR"],
    name="Predicted ADR"
))

fig4.add_trace(go.Scatter(
    x=forecast["Date"],
    y=forecast["Market_Trend"],
    name="Market Baseline",
    line=dict(dash="dash")
))

st.plotly_chart(fig4, use_container_width=True)

# --------------------------------------------------
# COMPETITOR MAP
# --------------------------------------------------

st.subheader("Competitive Landscape")

m = folium.Map(location=[38.9055,-77.0620], zoom_start=15)

folium.Marker(
    [38.9055,-77.0620],
    popup="Georgetown Inn",
    icon=folium.Icon(color="blue")
).add_to(m)

competitors = [
("Four Seasons DC",[38.9052,-77.0581]),
("Rosewood DC",[38.9045,-77.0625]),
("Ritz Carlton Georgetown",[38.9031,-77.0615])
]

for name,loc in competitors:
    folium.CircleMarker(location=loc,radius=8,popup=name,color="red",fill=True).add_to(m)

st_folium(m,width=700,height=400)

# --------------------------------------------------
# DEMAND HEATMAP
# --------------------------------------------------

st.subheader("Geographic Demand Heatmap")

m2 = folium.Map(location=[38.9055,-77.0620], zoom_start=4)

heat = df[["Lat","Lon"]].dropna().values.tolist()

HeatMap(heat).add_to(m2)

st_folium(m2,width=700,height=400)

# --------------------------------------------------
# AI PRICING ENGINE
# --------------------------------------------------

st.subheader("AI Pricing Recommendation")

latest_occ = df["Occupancy"].iloc[-1]
latest_adr = df["ADR"].iloc[-1]

if latest_occ > 0.9:
    suggested = latest_adr * 1.15
    st.success(f"High demand detected. Suggested ADR: ${suggested:.0f}")
elif latest_occ > 0.75:
    suggested = latest_adr * 1.05
    st.info(f"Moderate demand. Suggested ADR: ${suggested:.0f}")
else:
    suggested = latest_adr * 0.92
    st.warning(f"Low demand. Suggested ADR: ${suggested:.0f}")

# --------------------------------------------------
# UPCOMING EVENTS
# --------------------------------------------------

st.subheader("Upcoming High Impact Events")

upcoming = events[events["Date"] >= last_date].sort_values("Date").head(5)

for _,row in upcoming.iterrows():

    st.markdown(f"""
    <div class="event-card">
    <b>{row['Date'].strftime('%b %d')}</b> — {row['Event']}<br>
    Impact: {row['Impact_Level']}
    </div>
    """, unsafe_allow_html=True)
