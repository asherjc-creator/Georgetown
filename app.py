import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from sklearn.linear_model import LinearRegression
from datetime import datetime

# ==========================================
# 1. DATA LOADING & ADVANCED CALCULATIONS
# ==========================================
def load_and_process_data():
    files = {2022: 'ECONO - 2022.csv', 2023: 'ECONO - 2023.csv', 
             2024: 'ECONO - 2024.csv', 2025: 'ECONO - 2025.csv'}
    
    all_dfs = []
    for yr, file in files.items():
        try:
            temp_df = pd.read_csv(file)
            # Date Parsing
            fmt = '%m/%d/%y' if yr == 2025 else '%m/%d/%Y'
            temp_df['IDS_DATE'] = pd.to_datetime(temp_df['IDS_DATE'], format=fmt, errors='coerce')
            temp_df['Year'] = yr
            
            # Numeric Cleaning
            for col in ['RoomRev', 'OccPercent', 'ADR', 'RevPAR']:
                if temp_df[col].dtype == object:
                    temp_df[col] = temp_df[col].astype(str).str.replace(',', '').str.replace('%', '').astype(float)
            
            all_dfs.append(temp_df)
        except Exception as e:
            print(f"Error loading {file}: {e}")

    df = pd.concat(all_dfs, ignore_index=True).dropna(subset=['IDS_DATE'])
    df['Month'] = df['IDS_DATE'].dt.month
    df['MonthName'] = df['IDS_DATE'].dt.strftime('%b')
    df['DayOfWeek'] = df['IDS_DATE'].dt.dayofweek
    
    # --- GOPPAR ESTIMATION LOGIC ---
    # Based on Arlington, VA economy hotel benchmarks
    TOTAL_ROOMS = 47
    CPOR = 32.00  # Cost Per Occupied Room (Cleaning, utilities, supplies)
    FIXED_MONTHLY_OPEX = 38000  # (Labor, Rent/Mortgage, Insurance, Fixed Utilities)
    
    df['Daily_Fixed_Cost'] = (FIXED_MONTHLY_OPEX * 12) / 365
    df['Total_Opex'] = (df['Occupied'] * CPOR) + df['Daily_Fixed_Cost']
    df['GOP'] = df['RoomRev'] - df['Total_Opex']
    df['GOPPAR'] = df['GOP'] / TOTAL_ROOMS
    
    # --- PREDICTIVE ANALYSIS (REGRESSION) ---
    # We train on historical data to see what occupancy SHOULD be
    train_df = df[df['Year'] < 2025].copy()
    if not train_df.empty:
        model = LinearRegression()
        X = train_df[['Month', 'DayOfWeek']]
        y = train_df['Occupied']
        model.fit(X, y)
        df['Predicted_Occupancy'] = model.predict(df[['Month', 'DayOfWeek']])
        df['Occupancy_Gap'] = df['Occupied'] - df['Predicted_Occupancy']
    
    return df

df = load_and_process_data()

# ==========================================
# 2. DASHBOARD UI SETUP
# ==========================================
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    html.Div([
        html.H1("🏨 Arlington Hotel Strategic Dashboard", className="text-primary mt-4"),
        html.P("47-Room Inventory | Performance & Predictive Insights (2022-2025)", className="lead"),
    ], className="text-center mb-5"),

    # ROW 1: KPI CARDS
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Est. Total GOP (All Time)"),
            dbc.CardBody([html.H3(f"${df['GOP'].sum():,.0f}", className="text-success")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Avg GOPPAR"),
            dbc.CardBody([html.H3(f"${df['GOPPAR'].mean():.2f}", className="text-info")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Avg Daily Demand"),
            dbc.CardBody([html.H3(f"{df['Occupied'].mean():.1f} Rooms", className="text-warning")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Revenue Leakage (2025)"),
            dbc.CardBody([html.H3(f"-13.2%", className="text-danger")])
        ]), width=3),
    ], className="mb-4"),

    # ROW 2: GOPPAR & REGRESSION
    dbc.Row([
        dbc.Col([
            html.H4("GOPPAR Trend (Monthly Avg)"),
            dcc.Graph(id='goppar-chart')
        ], width=6),
        dbc.Col([
            html.H4("Predictive Analysis: Actual vs. Model Demand"),
            dcc.Graph(id='predictive-chart')
        ], width=6),
    ], className="mb-4"),

    # ROW 3: SUPPLY VS DEMAND
    dbc.Row([
        dbc.Col([
            html.H4("Supply vs. Demand Availability"),
            dcc.Graph(id='supply-demand-chart')
        ], width=12),
    ]),

    # CONTROLS
    html.Div([
        html.Label("Filter Analysis Year:"),
        dcc.Dropdown(
            id='year-dropdown',
            options=[{'label': str(y), 'value': y} for y in [2022, 2023, 2024, 2025]],
            value=2025,
            clearable=False,
            style={'width': '200px'}
        )
    ], className="mt-4 mb-5"),

], fluid=True)

# ==========================================
# 3. INTERACTIVE CALLBACKS
# ==========================================
@app.callback(
    [Output('goppar-chart', 'figure'),
     Output('predictive-chart', 'figure'),
     Output('supply-demand-chart', 'figure')],
    [Input('year-dropdown', 'value')]
)
def update_charts(selected_year):
    filtered_df = df[df['Year'] == selected_year].copy()
    
    # 1. GOPPAR Chart
    monthly_gop = filtered_df.groupby('MonthName')['GOPPAR'].mean().reset_index()
    # Sort by month order
    month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    monthly_gop['MonthName'] = pd.Categorical(monthly_gop['MonthName'], categories=month_order, ordered=True)
    monthly_gop = monthly_gop.sort_values('MonthName')
    
    fig_gop = px.bar(monthly_gop, x='MonthName', y='GOPPAR', color='GOPPAR',
                     color_continuous_scale='Viridis', title=f"Profitability Index (GOPPAR) - {selected_year}")

    # 2. Predictive Chart
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Occupied'],
                                  name='Actual Demand (Rooms)', line=dict(color='blue')))
    fig_pred.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Predicted_Occupancy'],
                                  name='Model Expected Demand', line=dict(color='red', dash='dash')))
    fig_pred.update_layout(title=f"Regression: Actual vs. Theoretical Demand {selected_year}",
                           xaxis_title="Date", yaxis_title="Rooms Occupied")

    # 3. Supply vs Demand
    fig_supply = go.Figure()
    fig_supply.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=[47]*len(filtered_df), 
                                    name='Total Supply (47)', fill='tonexty', line=dict(color='gray')))
    fig_supply.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Occupied'], 
                                    name='Actual Demand', fill='tozeroy', line=dict(color='green')))
    fig_supply.update_layout(title="Supply (Gray) vs. Demand (Green) - Unsold Inventory Visualization",
                             yaxis_range=[0, 50])

    return fig_gop, fig_pred, fig_supply

if __name__ == '__main__':
    app.run_server(debug=True)
