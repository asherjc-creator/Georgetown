import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Georgetown Inn Revenue Portal",
    page_icon="🏨",
    layout="wide"
)

# --------------------------------------------------
# STYLE
# --------------------------------------------------

st.markdown("""
<style>
.main {background-color:#f4f6f8;}
.metric-card {
    background:white;
    padding:20px;
    border-radius:10px;
    box-shadow:0px 2px 5px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def scrape_booking_rate(hotel_name):

    search_query = f"{hotel_name} Washington DC"
    url = f"https://www.booking.com/searchresults.html?ss={search_query.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")

        price = soup.find("span", {"data-testid": "price-and-discounted-price"})

        if price:
            return price.text
        else:
            return "Hidden"

    except:
        return "N/A"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data(ttl=600)
def load_data():

    # -------------------------
    # Competitor Rates
    # -------------------------

    try:

        comp = pd.read_csv("competitor_rates.csv")

        comp["Date"] = pd.to_datetime(comp["Date"])
        comp["Rate"] = pd.to_numeric(comp["Rate"], errors="coerce")

        comp = comp.dropna()

    except:

        hotels = [
            "Four Seasons DC",
            "Ritz Carlton Georgetown",
            "Rosewood DC",
            "Fairmont DC",
            "Park Hyatt DC"
        ]

        dates = pd.date_range(datetime.today(), periods=30)

        rows = []

        for hotel in hotels:
            for d in dates:
                rows.append({
                    "Hotel": hotel,
                    "Date": d,
                    "Rate": np.random.randint(220, 480)
                })

        comp = pd.DataFrame(rows)

    # -------------------------
    # Events
    # -------------------------

    try:

        events = pd.read_csv("events_dc.csv")

        events["Date"] = pd.to_datetime(events["Date"])

    except:

        events = pd.DataFrame({
            "Date":[
                "2026-03-20",
                "2026-04-05",
                "2026-07-04"
            ],
            "Event":[
                "Cherry Blossom Festival",
                "Marathon Weekend",
                "Independence Day"
            ],
            "Impact_Level":[
                "High",
                "Medium",
                "High"
            ]
        })

        events["Date"] = pd.to_datetime(events["Date"])

    # -------------------------
    # Internal Hotel Data
    # -------------------------

    try:

        df = pd.read_csv("georgetown_inn_data.csv")

        df["Date"] = pd.to_datetime(df["Date"])

    except:

        dates = pd.date_range(datetime.today(), periods=60)

        df = pd.DataFrame({
            "Date":dates,
            "Occupancy":np.random.randint(65,95,len(dates)),
            "ADR":np.random.randint(180,320,len(dates))
        })

        df["Revenue"] = df["Occupancy"] * df["ADR"]

    return comp, events, df


comp, events, hotel = load_data()

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("🏨 Georgetown Inn Revenue Intelligence Dashboard")

st.write("AI assisted pricing insights for Washington DC hotel market")

# --------------------------------------------------
# KPI METRICS
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

avg_occ = round(hotel["Occupancy"].mean(),1)
avg_adr = round(hotel["ADR"].mean(),0)
avg_rev = round(hotel["Revenue"].mean(),0)

with col1:
    st.metric("Average Occupancy", f"{avg_occ}%")

with col2:
    st.metric("Average ADR", f"${avg_adr}")

with col3:
    st.metric("Average Daily Revenue", f"${avg_rev}")

# --------------------------------------------------
# OCCUPANCY TREND
# --------------------------------------------------

st.subheader("Occupancy Trend")

fig_occ = px.line(
    hotel,
    x="Date",
    y="Occupancy",
    markers=True
)

st.plotly_chart(fig_occ, use_container_width=True)

# --------------------------------------------------
# ADR TREND
# --------------------------------------------------

st.subheader("ADR Trend")

fig_adr = px.line(
    hotel,
    x="Date",
    y="ADR",
    markers=True
)

st.plotly_chart(fig_adr, use_container_width=True)

# --------------------------------------------------
# COMPETITOR RATE COMPARISON
# --------------------------------------------------

st.subheader("Competitor Rate Comparison")

fig_comp = px.line(
    comp,
    x="Date",
    y="Rate",
    color="Hotel"
)

st.plotly_chart(fig_comp, use_container_width=True)

# --------------------------------------------------
# EVENT DEMAND IMPACT
# --------------------------------------------------

st.subheader("Upcoming Demand Events")

impact_colors = {
    "High":"🔴",
    "Medium":"🟡",
    "Low":"🟢"
}

for _, row in events.iterrows():

    st.markdown(
        f"{impact_colors.get(row['Impact_Level'],'⚪')} "
        f"**{row['Event']}** — {row['Date'].date()} "
        f"({row['Impact_Level']} Impact)"
    )

# --------------------------------------------------
# REVENUE FORECAST
# --------------------------------------------------

st.subheader("Revenue Forecast")

hotel["Forecast"] = hotel["Revenue"].rolling(7).mean()

fig_forecast = go.Figure()

fig_forecast.add_trace(
    go.Scatter(
        x=hotel["Date"],
        y=hotel["Revenue"],
        name="Actual Revenue"
    )
)

fig_forecast.add_trace(
    go.Scatter(
        x=hotel["Date"],
        y=hotel["Forecast"],
        name="Forecast",
        line=dict(dash="dash")
    )
)

st.plotly_chart(fig_forecast, use_container_width=True)

# --------------------------------------------------
# RATE RECOMMENDATION ENGINE
# --------------------------------------------------

st.subheader("AI Rate Recommendation")

latest_occ = hotel["Occupancy"].iloc[-1]
latest_adr = hotel["ADR"].iloc[-1]

if latest_occ > 90:
    recommendation = latest_adr * 1.15
elif latest_occ > 80:
    recommendation = latest_adr * 1.08
elif latest_occ > 70:
    recommendation = latest_adr * 1.02
else:
    recommendation = latest_adr * 0.95

st.success(f"Recommended ADR: **${round(recommendation)}**")

# --------------------------------------------------
# COMPETITOR MAP
# --------------------------------------------------

st.subheader("Georgetown Competitor Map")

dc_map = folium.Map(
    location=[38.9072, -77.0369],
    zoom_start=13
)

competitors = [
    ("Four Seasons DC",38.9047,-77.0537),
    ("Ritz Carlton Georgetown",38.9101,-77.0608),
    ("Rosewood DC",38.9104,-77.0580),
    ("Park Hyatt DC",38.9108,-77.0437)
]

heat_data = []

for name, lat, lon in competitors:

    folium.Marker(
        location=[lat,lon],
        popup=name,
        icon=folium.Icon(color="blue")
    ).add_to(dc_map)

    heat_data.append([lat,lon])

HeatMap(heat_data).add_to(dc_map)

st_folium(dc_map, width=700)

# --------------------------------------------------
# LIVE COMPETITOR RATE CHECK
# --------------------------------------------------

st.subheader("Live Rate Check")

hotel_name = st.text_input("Enter competitor hotel")

if st.button("Check Live Rate"):

    rate = scrape_booking_rate(hotel_name)

    st.info(f"Latest Rate: {rate}")
