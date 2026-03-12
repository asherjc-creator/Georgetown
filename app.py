import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# ======================
# 1. Load and Clean Data
# ======================
def load_data():
    years = [2022, 2023, 2024, 2025]
    dfs = []
    for yr in years:
        df = pd.read_csv(f'ECONO - {yr}.csv')
        # Parse dates (2025 uses %y, others %Y)
        if yr == 2025:
            df['IDS_DATE'] = pd.to_datetime(df['IDS_DATE'], format='%m/%d/%y')
        else:
            df['IDS_DATE'] = pd.to_datetime(df['IDS_DATE'], format='%m/%d/%Y')
        df['Year'] = yr
        # Clean numeric columns
        df['RoomRev'] = df['RoomRev'].astype(str).str.replace(',', '').astype(float)
        df['OccPercent'] = df['OccPercent'].astype(str).str.rstrip('%').astype(float)
        dfs.append(df)
    data = pd.concat(dfs, ignore_index=True)
    data['Month'] = data['IDS_DATE'].dt.month
    data['MonthName'] = data['IDS_DATE'].dt.strftime('%b')
    return data

df = load_data()

# ======================
# 2. Compute Yearly KPIs
# ======================
yearly = df.groupby('Year').agg(
    TotalRevenue=('RoomRev', 'sum'),
    AvgOcc=('OccPercent', 'mean'),
    AvgADR=('ADR', 'mean'),
    AvgRevPAR=('RevPAR', 'mean')
).round(2).reset_index()

# ======================
# 3. Monthly Aggregates
# ======================
monthly = df.groupby(['Year', 'Month', 'MonthName'])['RoomRev'].sum().reset_index()
month_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
monthly['MonthName'] = pd.Categorical(monthly['MonthName'], categories=month_order, ordered=True)

# ======================
# 4. Occupancy vs ADR Scatter
# ======================
scatter_df = df.groupby(['Year', 'MonthName']).agg(
    AvgOcc=('OccPercent', 'mean'),
    AvgADR=('ADR', 'mean')
).reset_index()

# ======================
# 5. Build Dash App
# ======================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1("🏨 Hotel Performance Dashboard (2022–2025)", className="text-center my-4"),

    # KPI Cards
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Total Revenue", className="card-title"),
                html.H2(f"${yearly['TotalRevenue'].sum():,.0f}", className="card-text text-primary")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Avg Occupancy", className="card-title"),
                html.H2(f"{yearly['AvgOcc'].mean():.1f}%", className="card-text text-success")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Avg ADR", className="card-title"),
                html.H2(f"${yearly['AvgADR'].mean():.2f}", className="card-text text-info")
            ])
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Avg RevPAR", className="card-title"),
                html.H2(f"${yearly['AvgRevPAR'].mean():.2f}", className="card-text text-warning")
            ])
        ]), width=3),
    ], className="mb-4"),

    # Yearly Bar Charts
    dbc.Row([
        dbc.Col(dcc.Graph(id='revenue-bar'), width=6),
        dbc.Col(dcc.Graph(id='occ-bar'), width=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='adr-bar'), width=6),
        dbc.Col(dcc.Graph(id='revpar-bar'), width=6),
    ]),

    html.Hr(),

    # Monthly Revenue Comparison
    html.H3("📅 Monthly Revenue Comparison", className="mt-4"),
    dbc.Row([
        dbc.Col([
            html.Label("Select Years:"),
            dcc.Dropdown(
                id='year-selector',
                options=[{'label': str(y), 'value': y} for y in [2022,2023,2024,2025]],
                value=[2024,2025],
                multi=True,
                clearable=False
            )
        ], width=4),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='monthly-revenue-line'), width=12),
    ]),

    # Occupancy vs ADR Scatter
    html.H3("📊 Occupancy vs ADR by Month", className="mt-4"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='occ-adr-scatter'), width=12),
    ]),

    # OTA Share Note
    dbc.Row([
        dbc.Col(html.Div(
            "ℹ️ Note: OTA share is approximately 84% (based on user input). Focus on direct booking strategies to reduce commission costs.",
            className="alert alert-info"
        ), width=12),
    ]),

], fluid=True)

# ======================
# Callbacks
# ======================
@app.callback(
    Output('revenue-bar', 'figure'),
    Output('occ-bar', 'figure'),
    Output('adr-bar', 'figure'),
    Output('revpar-bar', 'figure'),
    Input('year-selector', 'value')  # dummy trigger to keep charts static but interactive
)
def update_yearly_charts(_):
    # Revenue bar
    fig_rev = px.bar(yearly, x='Year', y='TotalRevenue', title='Total Revenue by Year',
                     labels={'TotalRevenue': 'Revenue ($)'}, text_auto='.2s')
    fig_rev.update_traces(marker_color='#2E86AB')

    # Occupancy bar
    fig_occ = px.bar(yearly, x='Year', y='AvgOcc', title='Average Occupancy by Year',
                     labels={'AvgOcc': 'Occupancy (%)'}, text_auto='.1f')
    fig_occ.update_traces(marker_color='#A23B72')

    # ADR bar
    fig_adr = px.bar(yearly, x='Year', y='AvgADR', title='Average Daily Rate (ADR) by Year',
                     labels={'AvgADR': 'ADR ($)'}, text_auto='.2f')
    fig_adr.update_traces(marker_color='#F18F01')

    # RevPAR bar
    fig_revpar = px.bar(yearly, x='Year', y='AvgRevPAR', title='Revenue per Available Room (RevPAR) by Year',
                        labels={'AvgRevPAR': 'RevPAR ($)'}, text_auto='.2f')
    fig_revpar.update_traces(marker_color='#C73E1D')

    return fig_rev, fig_occ, fig_adr, fig_revpar

@app.callback(
    Output('monthly-revenue-line', 'figure'),
    Input('year-selector', 'value')
)
def update_monthly_chart(selected_years):
    filtered = monthly[monthly['Year'].isin(selected_years)]
    fig = px.line(filtered, x='MonthName', y='RoomRev', color='Year', markers=True,
                  title='Monthly Revenue', labels={'RoomRev': 'Revenue ($)', 'MonthName': ''})
    fig.update_layout(xaxis={'categoryorder':'array', 'categoryarray':month_order})
    return fig

@app.callback(
    Output('occ-adr-scatter', 'figure'),
    Input('year-selector', 'value')
)
def update_scatter(_):
    fig = px.scatter(scatter_df, x='AvgOcc', y='AvgADR', color='Year', hover_data=['MonthName'],
                     title='Occupancy vs ADR by Month',
                     labels={'AvgOcc': 'Occupancy (%)', 'AvgADR': 'ADR ($)'})
    fig.add_hline(y=yearly['AvgADR'].mean(), line_dash="dash", line_color="grey",
                  annotation_text=f"Avg ADR {yearly['AvgADR'].mean():.2f}")
    fig.add_vline(x=yearly['AvgOcc'].mean(), line_dash="dash", line_color="grey",
                  annotation_text=f"Avg Occ {yearly['AvgOcc'].mean():.1f}%")
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
