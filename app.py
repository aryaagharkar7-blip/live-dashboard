import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from supabase import create_client, Client
import pandas as pd
import plotly.graph_objects as go
import os  # IMPORTANT: Needed to read keys from Render

# --- CONFIGURATION (SECURE VERSION) ---
# We now pull these from Render's "Environment" tab instead of writing them here
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
                suppress_callback_exceptions=True)

# IMPORTANT: This line allows Render (Gunicorn) to "see" your app
server = app.server 

# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Interval(id='interval-sync', interval=5000, n_intervals=0),

    dbc.Container(id='main-container', children=[
        
        # 1. LOGIN SCREEN
        html.Div(id='login-screen', children=[
            dbc.Card([
                dbc.CardBody([
                    html.H3("TITAN-1 AUTH", className="text-center mb-4", style={'color': '#58a6ff'}),
                    dbc.Label("Email"),
                    dbc.Input(id="email-field", type="email", placeholder="Enter email", className="mb-3"),
                    dbc.Label("Password"),
                    dbc.InputGroup([
                        dbc.Input(id="pass-field", type="password", placeholder="Password"),
                        dbc.Button(html.I(className="bi bi-eye-slash", id="pw-icon"), id="btn-show-pw", color="secondary", outline=True),
                    ], className="mb-3"),
                    dbc.Button("SIGN IN", id="btn-login", color="primary", className="w-100 mb-2"),
                    html.Div(id="status-msg", className="text-center mt-3")
                ])
            ], style={"maxWidth": "420px", "margin": "80px auto", "backgroundColor": "#161b22", "border": "1px solid #30363d"})
        ]),

        # 2. DASHBOARD SCREEN
        html.Div(id='dashboard-screen', style={'display': 'none'}, children=[
            dbc.NavbarSimple(
                brand="TITAN-1 PLC DATA MONITOR", color="primary", dark=True, className="mb-4",
                children=[
                    dbc.NavItem(dbc.NavLink(id="user-display", disabled=True)),
                    dbc.Button("LOGOUT", id="btn-logout", color="danger", size="sm", className="ms-2")
                ]
            ),
            dbc.Container([
                # Alert Area
                html.Div(id="alert-container"),

                dbc.Row([
                    dbc.Col(html.H2("Live Machine Telemetry"), width=8),
                    dbc.Col(dbc.Button([html.I(className="bi bi-download me-2"), "Export CSV"], 
                                      id="btn-export", color="success", outline=True), width=4, className="text-end"),
                    dcc.Download(id="download-csv"),
                ], className="mb-4 align-items-center"),

                # Live Metric Cards
                dbc.Row(id='live-metrics-grid', className="g-4"),
                
                html.Hr(className="my-5", style={'borderColor': '#30363d'}),
                
                # Temperature Trend Graph
                html.H3("Real-Time Temperature Trend", className="mb-3"),
                dcc.Graph(id='live-update-graph', config={'displayModeBar': False}),
                
                html.Div(className="mt-5 text-center", children=[
                    html.Small("Status: Online | Table: plc_data", className="text-muted")
                ])
            ])
        ])
    ])
], style={'backgroundColor': '#0d1117', 'minHeight': '100vh', 'color': 'white'})

# --- CALLBACKS ---

# 1. Toggle Password
@app.callback(
    [Output("pass-field", "type"), Output("pw-icon", "className")],
    [Input("btn-show-pw", "n_clicks")],
    [State("pass-field", "type")],
    prevent_initial_call=True
)
def toggle_pw(n, current):
    return ("text", "bi bi-eye") if current == "password" else ("password", "bi bi-eye-slash")

# 2. Auth Flow
@app.callback(
    [Output("login-screen", "style"), Output("dashboard-screen", "style"), 
     Output("status-msg", "children"), Output("user-display", "children")],
    [Input("btn-login", "n_clicks"), Input("btn-logout", "n_clicks")],
    [State("email-field", "value"), State("pass-field", "value")],
    prevent_initial_call=True
)
def handle_auth(login_n, logout_n, email, password):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        if trigger == "btn-login":
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            return {'display': 'none'}, {'display': 'block'}, "", f"User: {email}"
        if trigger == "btn-logout":
            supabase.auth.sign_out()
            return {'display': 'block'}, {'display': 'none'}, "Logged out.", ""
    except Exception as e:
        return dash.no_update, dash.no_update, html.Span("Login Failed", style={'color': '#ff7b72'}), dash.no_update

# 3. Refresh Cards & Alerts
@app.callback(
    [Output('live-metrics-grid', 'children'), Output('alert-container', 'children')],
    [Input('interval-sync', 'n_intervals')],
    [State('dashboard-screen', 'style')]
)
def refresh_dashboard(n, dash_style):
    if not dash_style or dash_style.get('display') == 'none':
        return dash.no_update, dash.no_update
    try:
        res = supabase.table("plc_data").select("*").order("created_at", desc=True).limit(6).execute()
        data = res.data
        if not data: return dbc.Col("No data found."), None

        cards = []
        alerts = []
        for row in data:
            temp = row.get('temperature', 0)
            status = str(row.get('status', 'running')).lower()
            m_id = row.get('machine_id', 'Unknown')
            
            # Critical Alert Logic (90 degrees threshold)
            if temp >= 90:
                alerts.append(dbc.Alert(f"CRITICAL: {m_id} is at {temp}°C!", color="danger", dismissable=True, is_open=True, className="mb-2"))

            color = "#f85149" if "overheating" in status else "#3fb950"
            cards.append(dbc.Col(md=4, children=[
                dbc.Card([
                    dbc.CardHeader(f"Unit: {m_id}"),
                    dbc.CardBody([
                        html.H2(f"{temp}°C", style={'color': color}),
                        html.P(f"STATUS: {status.upper()}", className="mb-0 fw-bold"),
                        html.Small(f"Time: {row.get('created_at')[11:19]}", className="text-muted")
                    ])
                ], style={'backgroundColor': '#161b22', 'border': f'1px solid {color}'})
            ]))
        return cards, alerts
    except:
        return dash.no_update, dash.no_update

# 4. Refresh Graph
@app.callback(
    Output('live-update-graph', 'figure'),
    [Input('interval-sync', 'n_intervals')],
    [State('dashboard-screen', 'style')]
)
def update_graph(n, dash_style):
    if not dash_style or dash_style.get('display') == 'none':
        return dash.no_update
    try:
        res = supabase.table("plc_data").select("created_at, temperature").order("created_at", desc=True).limit(50).execute()
        df = pd.DataFrame(res.data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df.sort_values('created_at', inplace=True)
        fig = go.Figure(data=[go.Scatter(x=df['created_at'], y=df['temperature'], mode='lines+markers', line=dict(color='#58a6ff'))])
        fig.update_layout(template='plotly_dark', paper_bgcolor='#0d1117', plot_bgcolor='#0d1117', margin=dict(l=40, r=20, t=20, b=40))
        return fig
    except: return go.Figure()

# 5. Export CSV with Formatted Time
@app.callback(
    Output("download-csv", "data"),
    Input("btn-export", "n_clicks"),
    prevent_initial_call=True
)
def export_csv(n):
    res = supabase.table("plc_data").select("*").order("created_at", desc=True).execute()
    df = pd.DataFrame(res.data)
    
    # Format the Time for Excel
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['Date'] = df['created_at'].dt.date
    df['Time'] = df['created_at'].dt.time
    
    # Remove unnecessary columns for the final report
    final_df = df[['machine_id', 'temperature', 'status', 'Date', 'Time']]
    
    return dcc.send_data_frame(final_df.to_csv, "titan1_plc_report.csv", index=False)

if __name__ == '__main__':
    # Local test command. Render will use gunicorn instead.
    app.run_server(debug=False, host='0.0.0.0', port=8050)
