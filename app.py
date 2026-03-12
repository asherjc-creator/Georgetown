import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from sklearn.linear_model import LinearRegression

# ==========================================
# 1. DATA PROCESSING & ADVANCED METRICS
# ==========================================
def load_and_process_data():
    files = {
        2022: 'ECONO - 2022.csv', 
        2023: 'ECONO - 2023.csv', 
        2024: 'ECONO - 2024.csv', 
        2025: 'ECONO - 2025.csv'
    }
    
    all_dfs = []
    for yr, file in files.items():
        try:
            temp_df = pd.read_csv(file)
            # Standardize Dates
            fmt = '%m/%d/%y' if yr == 2025 else '%m/%d/%Y'
            temp_df['IDS_DATE'] = pd.to_datetime(temp_df['IDS_DATE'], format=fmt, errors='coerce')
            temp_df['Year'] = yr
            
            # Numeric Cleaning (Removing commas and percentage signs)
            for col in ['RoomRev', 'OccPercent', 'ADR', 'RevPAR']:
                if col in temp_df.columns and temp_df[col].dtype == object:
                    temp_df[col] = temp_df[col].astype(str).str.replace(',', '').str.replace('%', '').astype(float)
            
            all_dfs.append(temp_df)
        except Exception as e:
            print(f"Skipping {file} due to error: {e}")

    df = pd.concat(all_dfs, ignore_index=True).dropna(subset=['IDS_DATE'])
    df['Month'] = df['IDS_DATE'].dt.month
    df['MonthName'] = df['IDS_DATE'].dt.strftime('%b')
    df['DayOfWeek'] = df['IDS_DATE'].dt.dayofweek
    
    # --- GOPPAR CALCULATION (Arlington Benchmarks) ---
    TOTAL_ROOMS = 47
    CPOR = 32.00  # Cost Per Occupied Room (Cleaning, utilities)
    FIXED_MONTHLY_OPEX = 38000  # Staff, Rent, Taxes
    
    df['Daily_Fixed_Cost'] = (FIXED_MONTHLY_OPEX * 12) / 365
    df['Total_Opex'] = (df['Occupied'] * CPOR) + df['Daily_Fixed_Cost']
    df['GOP'] = df['RoomRev'] - df['Total_Opex']
    df['GOPPAR'] = df['GOP'] / TOTAL_ROOMS
    
    # --- PREDICTIVE REGRESSION (Demand Analysis) ---
    # Training the model on 2022-2024 data to predict 2025 expectations
    train_df = df[df['Year'] < 2025].copy()
    if not train_df.empty:
        model = LinearRegression()
        X = train_df[['Month', 'DayOfWeek']]
        y = train_df['Occupied']
        model.fit(X, y)
        df['Predicted_Occupancy'] = model.predict(df[['Month', 'DayOfWeek']])
    
    return df

df = load_and_process_data()

# ==========================================
# 2. DASHBOARD LAYOUT (UI)
# ==========================================
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    html.Header([
        html.H1("🏨 Arlington Hotel: Performance & Predictive Analysis", className="text-primary mt-4"),
        html.P("47-Room Inventory | GOPPAR & Demand Forecasting", className="lead"),
    ], className="text-center mb-5"),

    # KPI TOP ROW
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Cumulative GOP"),
            dbc.CardBody([html.H3(f"${df['GOP'].sum():,.0f}", className="text-success")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Avg GOPPAR"),
            dbc.CardBody([html.H3(f"${df['GOPPAR'].mean():.2f}", className="text-info")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Historical Avg Demand"),
            dbc.CardBody([html.H3(f"{df['Occupied'].mean():.1f} Rooms", className="text-warning")])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Efficiency Score"),
            dbc.CardBody([html.H3(f"{(df['Occupied'].sum()/df['Rooms'].sum()*100):.1f}%", className="text-danger")])
        ]), width=3),
    ], className="mb-4"),

    # ANALYSIS ROW
    dbc.Row([
        dbc.Col([
            html.H5("Profitability Index (GOPPAR by Month)"),
            dcc.Graph(id='goppar-chart')
        ], width=6),
        dbc.Col([
            html.H5("Regression: Actual vs. Predictive Demand"),
            dcc.Graph(id='predictive-chart')
        ], width=6),
    ], className="mb-4"),

    # FULL WIDTH SUPPLY VS DEMAND
    dbc.Row([
        dbc.Col([
            html.H5("Supply vs. Demand Availability (Unsold Inventory)"),
            dcc.Graph(id='supply-demand-chart')
        ], width=12),
    ]),

    # INTERACTIVE CONTROLS
    dbc.Row([
        dbc.Col([
            html.Label("Switch Analysis Year:"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(y), 'value': y} for y in [2022, 2023, 2024, 2025]],
                value=2025,
                clearable=False
            )
        ], width=3),
    ], className="mt-4 mb-5 p-4 bg-light rounded"),

], fluid=True)

# ==========================================
# 3. CHART CALLBACKS
# ==========================================
@app.callback(
    [Output('goppar-chart', 'figure'),
     Output('predictive-chart', 'figure'),
     Output('supply-demand-chart', 'figure')],
    [Input('year-dropdown', 'value')]
)
def update_charts(selected_year):
    filtered_df = df[df['Year'] == selected_year].copy()
    month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    
    # 1. GOPPAR
    monthly_gop = filtered_df.groupby('MonthName')['GOPPAR'].mean().reset_index()
    monthly_gop['MonthName'] = pd.Categorical(monthly_gop['MonthName'], categories=month_order, ordered=True)
    monthly_gop = monthly_gop.sort_values('MonthName')
    fig_gop = px.bar(monthly_gop, x='MonthName', y='GOPPAR', color='GOPPAR', color_continuous_scale='GnBu')

    # 2. Predictive Line
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Occupied'], name='Actual Occupied', line=dict(color='#2c3e50')))
    fig_pred.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Predicted_Occupancy'], name='Model Prediction', line=dict(color='#e74c3c', dash='dash')))
    fig_pred.update_layout(xaxis_title="Timeline", yaxis_title="Rooms")

    # 3. Supply vs Demand
    fig_supply = go.Figure()
    fig_supply.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=[47]*len(filtered_df), name='Total Supply (47)', fill='tonexty', line=dict(color='lightgray')))
    fig_supply.add_trace(go.Scatter(x=filtered_df['IDS_DATE'], y=filtered_df['Occupied'], name='Inventory Sold', fill='tozeroy', line=dict(color='#18bc9c')))
    fig_supply.update_layout(yaxis_range=[0, 50], showlegend=True)

    return fig_gop, fig_pred, fig_supply

# ==========================================
# 4. SERVER LAUNCH (Fixed for Dash 2.11+)
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)
