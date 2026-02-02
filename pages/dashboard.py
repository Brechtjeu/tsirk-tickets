import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime
from collections import defaultdict
from db import db, CheckoutSession, AccessCode

dash.register_page(__name__, path='/dashboard')

# Simple password configuration
DASHBOARD_PASSWORD = "tsirk-admin-2026" 

layout = html.Div([
    dbc.Container([
        html.H1("Ticket Sales Dashboard", className="text-center my-4", style={'color': 'var(--accent-gold)'}),
        
        # Login Section
        html.Div(id="login-section", children=[
            dbc.Row([
                dbc.Col([
                    dbc.Input(id="password-input", type="password", placeholder="Enter Password", className="mb-2"),
                    dbc.Button("Login", id="login-btn", color="primary", className="w-100"),
                    html.Div(id="login-error", className="text-danger mt-2")
                ], width=12, md=4)
            ], justify="center")
        ]),

        # Dashboard Section (Hidden by default)
        html.Div(id="dashboard-content", style={'display': 'none'}, children=[
            # Summary Cards
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H4("Total Revenue", className="card-title"),
                        html.H2(id="total-revenue", className="text-success")
                    ])
                ], className="mb-4"), width=12, md=6),
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H4("Total Tickets Sold", className="card-title"),
                        html.H2(id="total-tickets", className="text-primary")
                    ])
                ], className="mb-4"), width=12, md=6),
            ]),

            # Ticket Activation Section
            dbc.Row([
                dbc.Col([
                     dbc.Card([
                        dbc.CardHeader("Manual Ticket Activation (UitPas)"),
                        dbc.CardBody([
                            dbc.Input(id="ticket-code-input", placeholder="Enter Ticket Code", className="mb-2"),
                            dbc.Button("Toggle Validity", id="btn-toggle-valid", color="warning", className="mb-2"),
                            html.Div(id="ticket-status-output", className="text-info")
                        ])
                    ], className="mb-4")
                ], width=12, md=6),
                 dbc.Col([
                     dbc.Card([
                        dbc.CardHeader("Invalid UitPas Tickets (Action Required)"),
                        dbc.CardBody(html.Div(id="invalid-tickets-list"))
                    ], className="mb-4")
                ], width=12, md=6),
            ]),

            # Charts
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Sales Over Time"),
                        dbc.CardBody(dcc.Graph(id="sales-over-time-chart"))
                    ])
                ], width=12, lg=8, className="mb-4"),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Ticket Types"),
                        dbc.CardBody(dcc.Graph(id="ticket-types-chart"))
                    ])
                ], width=12, lg=4, className="mb-4"),
            ]),

             dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Sales by Show"),
                        dbc.CardBody(dcc.Graph(id="sales-by-show-chart"))
                    ])
                ], width=12, className="mb-4"),
            ]),
            
            # Refresh Button / Interval
            dbc.Button("Refresh Data", id="refresh-btn", color="secondary", size="sm", className="mb-4"),
            dcc.Interval(id="auto-refresh", interval=60*1000, n_intervals=0) # Auto refresh every 60s
        ])
    ])
])

@callback(
    [Output("login-section", "style"),
     Output("dashboard-content", "style"),
     Output("login-error", "children")],
    [Input("login-btn", "n_clicks")],
    [State("password-input", "value")]
)
def login(n_clicks, password):
    if not n_clicks:
        return {'display': 'block'}, {'display': 'none'}, ""
    
    if password == DASHBOARD_PASSWORD:
        return {'display': 'none'}, {'display': 'block'}, ""
    else:
        return {'display': 'block'}, {'display': 'none'}, "Incorrect Password"

@callback(
    Output("ticket-status-output", "children"),
    Input("btn-toggle-valid", "n_clicks"),
    State("ticket-code-input", "value"),
    prevent_initial_call=True
)
def toggle_validity(n_clicks, code):
    if not code: return "Please enter a code"
    
    ticket = AccessCode.query.filter_by(code=code).first()
    if not ticket:
        return f"Ticket {code} not found."
    
    ticket.is_valid = not ticket.is_valid
    db.session.commit()
    
    status = "VALID" if ticket.is_valid else "INVALID"
    return f"Ticket {code} is now {status}."

@callback(
    [Output("total-revenue", "children"),
     Output("total-tickets", "children"),
     Output("sales-over-time-chart", "figure"),
     Output("ticket-types-chart", "figure"),
     Output("sales-by-show-chart", "figure"),
     Output("invalid-tickets-list", "children")],
    [Input("dashboard-content", "style"),
     Input("refresh-btn", "n_clicks"),
     Input("auto-refresh", "n_intervals"),
     Input("btn-toggle-valid", "n_clicks")] # Update list when valid toggled
)
def update_dashboard(style, n_clicks, n_intervals, n_toggle):
    if style and style.get('display') == 'none':
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Fetch Data
    sessions = CheckoutSession.query.filter_by(payment_status='paid').all()
    tickets = AccessCode.query.all() # Fetch all generated tickets

    # 1. Revenue
    total_cents = sum(s.amount_total for s in sessions if s.amount_total)
    total_rev = f"€{total_cents / 100:,.2f}"

    # 2. Total Tickets
    total_tix = len(tickets)

    # 3. Sales Over Time (Line Chart)
    # Group by Date and Hour
    sales_by_time = defaultdict(float)
    for s in sessions:
        if s.created_at and s.amount_total:
            # Group by hour
            time_str = s.created_at.strftime('%Y-%m-%d %H:00')
            sales_by_time[time_str] += (s.amount_total / 100)
    
    sorted_times = sorted(sales_by_time.keys())
    revenues = [sales_by_time[t] for t in sorted_times]

    fig_time = go.Figure(data=go.Scatter(x=sorted_times, y=revenues, mode='lines+markers', name='Revenue'))
    fig_time.update_layout(title="Revenue over Time (Hourly)", xaxis_title="Time", yaxis_title="Revenue (€)", template="plotly_white")

    # 4. Sales by Show (Bar Chart) & Ticket Types
    # Parse descriptions: "GROOT (>12j) - SHOW 1 (13u30)"
    show_counts = defaultdict(int)
    type_counts = defaultdict(int)

    for t in tickets:
        desc = t.type
        # Heuristic parsing based on known format
        if "SHOW 1" in desc: show = "Show 1 (Sat 13:30)"
        elif "SHOW 2" in desc: show = "Show 2 (Sat 18:30)"
        elif "SHOW 3" in desc: show = "Show 3 (Sun 10:00)"
        else: show = "Unknown"
        
        show_counts[show] += 1

        if "GROOT" in desc: type_counts["Adult"] += 1
        elif "KLEIN" in desc: type_counts["Child"] += 1
        else: type_counts["Other"] += 1

    # Show Chart
    shows = list(show_counts.keys())
    counts = [show_counts[s] for s in shows]
    fig_shows = go.Figure(data=[go.Bar(x=shows, y=counts, marker_color='#d4af37')])
    fig_shows.update_layout(title="Tickets Sold per Show", template="plotly_white")

    # Type Chart (Pie)
    fig_types = go.Figure(data=[go.Pie(labels=list(type_counts.keys()), values=list(type_counts.values()), hole=.3)])
    fig_types.update_layout(title="Ticket Distribution", template="plotly_white")

    # 5. Invalid Tickets List
    invalid_tickets = AccessCode.query.filter_by(is_valid=False).all()
    if not invalid_tickets:
        invalid_list = html.P("No invalid tickets found.", className="text-success")
    else:
        # Create Table
        rows = []
        for t in invalid_tickets:
            rows.append(html.Tr([
                html.Td(t.code),
                html.Td(t.uitpas_number or "-"),
                html.Td(t.type)
            ]))
        
        invalid_list = dbc.Table([
            html.Thead(html.Tr([html.Th("Code"), html.Th("UitPas"), html.Th("Desc")])),
            html.Tbody(rows)
        ], striped=True, bordered=True, hover=True, size="sm")

    return total_rev, str(total_tix), fig_time, fig_types, fig_shows, invalid_list
