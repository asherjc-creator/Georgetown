import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

# -----------------------------
# 1. FIXED DATA LOADING (Handles file changes & full date range)
# -----------------------------
@st.cache_data(ttl=600) # Automatically refresh every 10 mins
def load_all_data():
    # Helper to check if file exists and get its last modified time
    def get_mtime(f): return os.path.getmtime(f) if os.path.exists(f) else 0

    # 1. Load Competitor Rates
    comp = pd.read_csv("competitor_rates.csv")
    comp = comp[comp["Date"] != "Date"]
    comp["Date"] = pd.to_datetime(comp["Date"], errors='coerce')
    comp["Rate"] = pd.to_numeric(comp["Rate"], errors='coerce')
    comp = comp.dropna(subset=["Date", "Rate"])
    
    # 2. Load Internal Data (with Improved Dummy Logic)
    try:
        df = pd.read_csv("georgetown_inn_data.csv")
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    except FileNotFoundError:
        # Generate dummy data that matches the ENTIRE range of the competitor file
        date_range = pd.date_range(start=comp["Date"].min(), end=comp["Date"].max())
        df = pd.DataFrame({
            "Date": date_range,
            "Room_Revenue": np.random.randint(4000, 10000, len(date_range)),
            "Rooms_Sold": np.random.randint(15, 30, len(date_range)),
            "Total_Rooms": [30]*len(date_range),
            "Market_Occ": np.random.uniform(0.6, 0.9, len(date_range)),
            "Market_ADR": np.random.uniform(400, 700, len(date_range)),
            "Lat": [38.9055]*len(date_range), "Lon": [-77.0620]*len(date_range)
        })

    # Calculations
    df["ADR"] = df["Room_Revenue"] / df["Rooms_Sold"]
    df["Occupancy"] = df["Rooms_Sold"] / df["Total_Rooms"]
    df["RevPAR"] = df["Room_Revenue"] / df["Total_Rooms"]
    df["RGI"] = (df["RevPAR"] / (df["Market_ADR"] * df["Market_Occ"])) * 100
    df["MPI"] = (df["Occupancy"] / df["Market_Occ"]) * 100
    
    return df, comp

# -----------------------------
# 2. NEW: Booking.com Scraper (Simplified)
# -----------------------------
def scrape_booking_rates(hotel_name):
    """Note: This is a basic template. Booking.com often requires 
    browser automation (Selenium/Playwright) for consistent results."""
    url = f"https://www.booking.com/searchresults.html?ss={hotel_name.replace(' ', '+')}+Washington+DC"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        # Target the price element (selector changes frequently)
        price_tag = soup.find("span", {"data-testid": "price-and-discounted-price"})
        return price_tag.text if price_tag else "N/A"
    except:
        return "Blocked/Error"

# -----------------------------
# 3. DASHBOARD UI
# -----------------------------
df, comp = load_all_data()

with st.sidebar:
    st.header("Settings")
    # Dynamically set range based on the actual CSV data found
    date_range = st.date_input("Select Date Range", [df["Date"].min(), df["Date"].max()])
    
    if st.button("Scrape Live Booking.com Rates"):
        st.write("Fetching live rates...")
        rate = scrape_booking_rates("Four Seasons DC")
        st.success(f"Live Four Seasons Rate: {rate}")

# Filter data
if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
    filtered = df[mask]
    comp_filtered = comp[(comp["Date"] >= start_date) & (comp["Date"] <= end_date)]
    
    st.write(f"Showing results for {len(filtered)} days.")
    st.plotly_chart(px.line(comp_filtered, x="Date", y="Rate", color="Hotel"))
else:
    st.warning("Please select a start and end date.")
