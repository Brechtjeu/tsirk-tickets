import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
import json

dash.register_page(__name__, path='/')

# Data Configuration
SHOWS = [
    {"id": "s1", "name": "SHOW 1", "date": "28/03/2026", "time": "13u30"},
    {"id": "s2", "name": "SHOW 2", "date": "28/03/2026", "time": "18u30"},
    {"id": "s3", "name": "SHOW 3", "date": "29/03/2026", "time": "10u00"},
]

PRICES = {
    "large": 8,
    "small": 6,
    "discount": 4
}

def create_counter_input(show_id, category):
    return html.Div([
        dbc.Button("-", id={"type": "btn-dec", "show": show_id, "category": category}, n_clicks=0, className="btn-counter btn-dec"),
        dcc.Input(
            id={"type": "ticket-input", "show": show_id, "category": category},
            type="number", min=0, step=1, value=0,
            className="form-control text-center input-counter"
        ),
        dbc.Button("+", id={"type": "btn-inc", "show": show_id, "category": category}, n_clicks=0, className="btn-counter btn-inc"),
    ], className="d-flex align-items-stretch justify-content-center mb-3 counter-group")

def create_show_card(show):
    return dbc.Col(
        html.Div([
            html.H3(show["name"], className="text-gold text-center"),
            html.H5([html.I(className="bi bi-calendar"), f" {show['date']}"], className="text-center"),
            html.H4(show['time'], className="text-center mb-4"),
            
            # Inputs
            html.Label("GROTE UITVINDERS (>12j)", className="small"),
            create_counter_input(show["id"], "large"),
            
            html.Label("KLEINE UITVINDERS (-12j)", className="small"),
            create_counter_input(show["id"], "small"),
        ], className="show-card h-100"), 
        width=12, md=4, className="mb-4"
    )

layout = dbc.Container([
    html.Div([
        html.H4("'T GETOUW - 28 EN 29 MAART 2026", className="text-center mb-4 text-white-50"),
    ]),

    # Pricing Info
    dbc.Row([
        dbc.Col([
            html.H5("GROTE UITVINDER", className="text-gold mb-1"),
            html.P("1 show: €8", className="text-white")
        ], width=12, md=4, className="text-center mb-3"),
        
        dbc.Col([
            html.H5("KLEINE UITVINDER (-12J)", className="text-gold mb-1"),
            html.P("1 show: €6", className="text-white")
        ], width=12, md=4, className="text-center mb-3"),
        
        dbc.Col([
            html.H5("EXTRA SHOWS", className="text-gold mb-1"),
            html.P("Alle uitvinders: €4", className="text-white")
        ], width=12, md=4, className="text-center mb-3"),
    ], className="mb-5 justify-content-center"),
    
    dbc.Row([create_show_card(s) for s in SHOWS], className="mb-5"),
    
    # Cart / Summary
    html.Div([
        html.Hr(className="border-gold"),
        dbc.Row([
            dbc.Col([
                html.H3("WINKELMANDJE", className="text-gold"),
                html.Div(id="cart-details"),
                html.H2(id="total-price", className="mt-3 text-white"),
            ], width=12, md=8),
            dbc.Col([
                dbc.Button("BESTELLEN & BETALEN", id="pay-btn", className="btn-gold btn-lg w-100 mt-4"),
                html.Div(id="pay-status", className="mt-2 text-center text-warning")
            ], width=12, md=4, className="d-flex flex-column justify-content-center")
        ])
    ], className="container pb-5")
])

# Callback 1: UI Inputs -> Update Store
@callback(
    Output("cart-store", "data"),
    [Input({"type": "ticket-input", "show": ALL, "category": ALL}, "value")],
    [State({"type": "ticket-input", "show": ALL, "category": ALL}, "id")]
)
def update_store(values, ids):
    # Store structure: {'s1': {'large': 0, 'small': 0}, ...}
    data = {s['id']: {'large': 0, 'small': 0} for s in SHOWS}
    
    for val, id_map in zip(values, ids):
        if val is None: val = 0
        show_id = id_map['show']
        cat = id_map['category']
        data[show_id][cat] = int(val)
        
    return data

# Callback 2: Store -> Update Price Display
@callback(
    [Output("cart-details", "children"),
     Output("total-price", "children")],
    [Input("cart-store", "data")]
)
def calculate_price_from_store(ticket_data):
    if not ticket_data:
        return html.P("Laden...", className="text-muted"), "€0"

    # Logic: Per-type chronological discount
    # We track the "max previous" attendees for each category separately.
    max_prev_large = 0
    max_prev_small = 0
    
    total_cost = 0
    line_items = []
    
    # Ensure chronological order
    show_ids = ['s1', 's2', 's3'] 
    
    for sid in show_ids:
        # Find the show object for name reference
        show = next((s for s in SHOWS if s['id'] == sid), None)
        if not show: continue
        
        s_data = ticket_data.get(sid, {'large': 0, 'small': 0})
        n_large = int(s_data.get('large', 0))
        n_small = int(s_data.get('small', 0))
        
        # Calculate Large
        disc_slots_large = max_prev_large
        n_large_disc = min(n_large, disc_slots_large)
        n_large_full = n_large - n_large_disc
        
        cost_large = (n_large_full * PRICES['large']) + (n_large_disc * PRICES['discount'])
        
        # Calculate Small
        disc_slots_small = max_prev_small
        n_small_disc = min(n_small, disc_slots_small)
        n_small_full = n_small - n_small_disc
        
        cost_small = (n_small_full * PRICES['small']) + (n_small_disc * PRICES['discount'])
        
        # Update Total
        total_cost += cost_large + cost_small
        
        # Update History (Max of previous or current)
        max_prev_large = max(max_prev_large, n_large)
        max_prev_small = max(max_prev_small, n_small)
        
        # Build String
        if n_large + n_small > 0:
            details = []
            if n_large_full > 0: details.append(f"{n_large_full}x Groot (€{n_large_full * PRICES['large']})")
            if n_large_disc > 0: details.append(f"{n_large_disc}x Groot (Korting: €{n_large_disc * PRICES['discount']})")
            if n_small_full > 0: details.append(f"{n_small_full}x Klein (€{n_small_full * PRICES['small']})")
            if n_small_disc > 0: details.append(f"{n_small_disc}x Klein (Korting: €{n_small_disc * PRICES['discount']})")
            
            line_items.append(html.P(f"{show['name']}: {', '.join(details)}"))

    if not line_items:
        line_items.append(html.P("Nog geen tickets geselecteerd.", className="text-muted"))

    return line_items, f"TOTAAL: €{total_cost}"

@callback(
    Output({"type": "ticket-input", "show": MATCH, "category": MATCH}, "value"),
    [Input({"type": "btn-dec", "show": MATCH, "category": MATCH}, "n_clicks"),
     Input({"type": "btn-inc", "show": MATCH, "category": MATCH}, "n_clicks")],
    [State({"type": "ticket-input", "show": MATCH, "category": MATCH}, "value")],
    prevent_initial_call=True
)
def update_input_value(n_dec, n_inc, current_val):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
        
    # parse the trigger to see which button was pressed
    trigger_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
    button_type = trigger_id['type']
    
    if current_val is None:
        current_val = 0
        
    if button_type == "btn-dec":
        return max(0, current_val - 1)
    elif button_type == "btn-inc":
        return current_val + 1
        
    return dash.no_update

@callback(
    Output("pay-status", "children"),
    Input("pay-btn", "n_clicks"),
    prevent_initial_call=True
)
def on_pay(n):
    return "Redirecting naar betaling... (Demo)"
