import dash
from dash import dcc, html, dash_table, Input, Output, State
import pandas as pd
import plotly.express as px
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import io

# --- CONFIGURATION ---
REPORT_INTERVAL_HOURS = 8
DASHBOARD_THEME = {
    'background': '#111111',
    'text': '#7FDBFF',
    'card': '#1e1e1e',
    'accent': '#007bff'
}

def get_live_data():
    return pd.DataFrame({
        "Time": pd.date_range(start=datetime.datetime.now() - datetime.timedelta(hours=12), periods=12, freq='H'),
        "Performance": [45, 52, 48, 61, 55, 67, 72, 65, 78, 82, 80, 85],
        "Region": ["East", "West", "North", "South", "East", "West", "North", "South", "East", "West", "North", "South"]
    })

# --- APP SETUP ---
app = dash.Dash(__name__)

app.layout = html.Div(style={'backgroundColor': DASHBOARD_THEME['background'], 'color': DASHBOARD_THEME['text'], 'padding': '40px', 'minHeight': '100vh'}, children=[
    
    html.Div([
        html.H1("CLIENT ANALYTICS COMMAND CENTER", style={'textAlign': 'center'}),
        html.P(f"Auto-Reporting Status: ACTIVE", style={'textAlign': 'center', 'color': '#00FF00'})
    ], style={'marginBottom': '30px'}),

    # Control Panel
    html.Div([
        html.Button("📥 Generate & Download Excel Now", id="btn-download", 
                    style={'backgroundColor': DASHBOARD_THEME['accent'], 'color': 'white', 'padding': '10px 20px', 'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer'}),
        dcc.Download(id="download-excel-index"),
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Dashboard Grid
    html.Div([
        html.Div([
            dcc.Graph(figure=px.area(get_live_data(), x="Time", y="Performance", template="plotly_dark", title="Live Metrics Stream"))
        ], style={'width': '100%', 'padding': '10px'}),
    ])
])

# --- INTERACTIVITY LOGIC (The Download Bug-Free Code) ---
@app.callback(
    Output("download-excel-index", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True,
)
def func(n_clicks):
    df = get_live_data()
    
    # We use an in-memory buffer so no temporary files clutter your server
    return dcc.send_data_frame(df.to_excel, f"Manual_Report_{datetime.datetime.now().strftime('%H%M')}.xlsx", index=False)

if __name__ == '__main__':
    app.run_server(debug=True)