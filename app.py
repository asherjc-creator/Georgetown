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
            fmt = '%m/%d/%y' if yr == 2025 else '%m/%d/%Y'
            temp_df['IDS_DATE'] = pd.to_datetime(temp_df['IDS_DATE'], format=fmt, errors='coerce')
            temp_df['Year'] = yr
            
            for col in ['RoomRev', 'OccPercent', 'ADR', 'RevPAR']:
                if col in temp_df.columns and temp_df[col].dtype == object:
                    temp_df[col] = temp_df[col].astype(str).str.replace(',', '').str.replace('%', '').astype(float)
            all_dfs.append(temp_df)
        except Exception as e:
            print(f"File error {file}: {e}")

    df = pd.concat(all_dfs, ignore_index=True).dropna(subset=['IDS_DATE'])
    df['Month'] = df['IDS_DATE'].dt.month
    df['MonthName'] = df['IDS_DATE'].dt.strftime('%b')
    df['DayOfWeek'] = df['IDS_DATE'].dt.dayofweek
    
    # GOPPAR Logic (Arlington Benchmarks)
    TOTAL_ROOMS = 47
    CPOR, FIXED_MONTHLY = 32.00, 38000
    df['GOP'] = df['RoomRev'] - ((df['Occupied'] * CPOR) + ((FIXED_MONTHLY * 12) / 365))
    df['GOPPAR'] = df['GOP'] / TOTAL_ROOMS
    
    # Predictive Regression
    train_df = df[df['Year'] < 2025].copy()
    if not train_df.empty:
        model = LinearRegression().fit(train_df[['Month', 'DayOfWeek']], train_df['Occupied'])
        df['Predicted_Occupancy'] = model.predict(df[['Month', 'DayOfWeek']])
    
    return df

df = load_and_process_data()

# ==========================================
# 2. DASHBOARD LAYOUT
# ==========================================
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server # Required for cloud deployment

app.layout = dbc.Container([
    html.Div([
        html.H1("🏨 Arlington Hotel Performance", className="text-primary mt-4"),
        html.P("47-Room Inventory | GOPPAR & Predictive Demand", className="lead"),
    ], className="text-center mb-5"),

    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Cumulative GOP"), dbc.CardBody([html.H3(f"${df['GOP'].sum():,.0f}", className="text-success")])]), width=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Avg GOPPAR"), dbc.CardBody([html.H3(f"${df['GOPPAR'].mean():.2f}", className="text-info")])]), width=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Historical Demand"), dbc.CardBody([html.H3(f"{df['Occupied'].mean():.1f} Rms", className="text-warning")])]), width=3),
        dbc.Col(dbc.Card([dbc.CardHeader("Efficiency"), dbc.CardBody([html.H3(f"{(df['Occupied'].sum()/df['Rooms'].sum()*100):.1f}%", className="text-danger")])]), width=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([html.H5("Monthly GOPPAR Trend"), dcc.Graph(id='goppar-chart')], width=6),
        dbc.Col([html.H5("Actual vs Predicted Demand"), dcc.Graph(id='predictive-chart')], width=6),
    ], className="mb-4"),

    dbc.Row([dbc.Col([html.H5("Supply (47) vs. Demand Sold"), dcc.Graph(id='supply-demand-chart')], width=12)]),

    html.Div([
        html.Label("Year Select:"),
        dcc.Dropdown(id='year-dropdown', options=[{'label': str(y), 'value': y} for y in [2022, 2023, 2024, 2025]], value=2025, clearable=False)
    ], className="mt-4 mb-5 p-3 bg-light"),
], fluid=True)

# ==========================================
# 3. CALLBACKS & LAUNCH FIX
# ==========================================
@app.callback(
    [Output('goppar-chart', 'figure'), Output('predictive-chart', 'figure'), Output('supply-demand-chart', 'figure')],
    [Input('year-dropdown', 'value')]
)
def update_charts(selected_year):
    f_df = df[df['Year'] == selected_year].copy()
    m_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    
    g_df = f_df.groupby('MonthName')['GOPPAR'].mean().reset_index()
    g_df['MonthName'] = pd.Categorical(g_df['MonthName'], categories=m_order, ordered=True)
    fig_gop = px.bar(g_df.sort_values('MonthName'), x='MonthName', y='GOPPAR', color='GOPPAR', color_continuous_scale='GnBu')

    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=f_df['IDS_DATE'], y=f_df['Occupied'], name='Actual', line=dict(color='#2c3e50')))
    fig_pred.add_trace(go.Scatter(x=f_df['IDS_DATE'], y=f_df['Predicted_Occupancy'], name='Model', line=dict(color='#e74c3c', dash='dash')))

    fig_supply = go.Figure()
    fig_supply.add_trace(go.Scatter(x=f_df['IDS_DATE'], y=[47]*len(f_df), name='Supply', fill='tonexty', line=dict(color='lightgray')))
    fig_supply.add_trace(go.Scatter(x=f_df['IDS_DATE'], y=f_df['Occupied'], name='Sold', fill='tozeroy', line=dict(color='#18bc9c')))
    fig_supply.update_layout(yaxis_range=[0, 50])

    return fig_gop, fig_pred, fig_supply

if __name__ == '__main__':
    # CRITICAL: Disable reloader and debug to avoid Signal Errors on Streamlit Cloud
    app.run(host='0.0.0.0', port=8050, debug=False, use_reloader=False)
