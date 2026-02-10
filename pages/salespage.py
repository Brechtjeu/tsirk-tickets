import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
import json
import copy
import os
from dotenv import load_dotenv
from db import get_sold_count

dash.register_page(__name__, path='/')

# Configuration
load_dotenv()
MAX_TICKETS = int(os.getenv('MAX_TICKETS_PER_SHOW', 250))

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
            
            html.Div(id={"type": "show-status", "show": show["id"]}, className="text-center mb-3 fw-bold"),
            
            # Inputs
            html.Label("GROTE UITVINDERS (>12j)", className="small"),
            create_counter_input(show["id"], "large"),
            
            html.Label("KLEINE UITVINDERS (-12j)", className="small"),
            create_counter_input(show["id"], "small"),
        ], className="show-card h-100"), 
        width=12, md=4, className="mb-4"
    )

layout = dbc.Container([
    dcc.Interval(id="status-interval", interval=10*1000, n_intervals=0), # Poll every 10s
    
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
    
    # UitPas Section
    html.Div([
        html.Hr(className="border-gold"),
        html.H3("UITPAS MET KANSENTARIEF", className="text-gold mb-3"),
        html.P(["Heb je een UiTPAS met kansentarief? Dan krijg je korting op je ticket. Opgelet: deze tickets zijn enkel geldig op vertoon van een geldige UiTPAS", html.B(" met kansentarief "), "aan de kassa."], className="text-white small mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Input(id="uitpas-input", placeholder="UiTPAS Nummer (13 cijfers)", type="text", maxLength=13, className="uitpas-input"),
            ], width=12, md=4, className="mb-2"),
            dbc.Col([
                dbc.RadioItems(
                    options=[
                        {"label": "Grote Uitvinder", "value": "large"},
                        {"label": "Kleine Uitvinder", "value": "small"},
                    ],
                    value="large",
                    id="uitpas-type-input",
                    inline=True,
                    className="text-white"
                ),
            ], width=12, md=4, className="mb-2 d-flex align-items-center"),
            dbc.Col([
                dbc.Button("Toevoegen", id="btn-add-uitpas", color="primary", className="w-100"),
            ], width=12, md=2, className="mb-2"),
        ], className="align-items-center"),
        html.Div(id="uitpas-error", className="text-danger mt-2"),
        html.Div(id="uitpas-list", className="mt-3"),
        dcc.Store(id="uitpas-store", data=[]), # Stores list of {number: '...', type: '...'}
    ], className="container pb-4"),


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
    ], className="container pb-5"),
    
    # Limit Reached Modal
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Dat ging snel!"), close_button=True),
            dbc.ModalBody("Deze show is helaas bijna uitverkocht of er zijn niet genoeg tickets meer beschikbaar voor jouw selectie.", id="limit-modal-body"),
            dbc.ModalFooter(
                dbc.Button("Sluiten", id="close-limit-modal", className="ms-auto", n_clicks=0)
            ),
        ],
        id="limit-modal",
        is_open=False,
    ),
])

# Callback: Update Status Text
@callback(
    Output({"type": "show-status", "show": MATCH}, "children"),
    [Input("status-interval", "n_intervals")]
)
def update_show_status(n):
    # This matches all, but we need context to know which one caused it? 
    # Actually, pattern match OUTPUT works if we match inputs.
    # But interval is unique. We need ALL output and loop?
    # Dash pattern matching: if Input is not matched, it calls for all? No.
    # We must use ALL outputs and single input.
    return dash.no_update

# Real callback for status updates (ALL)
@callback(
    Output({"type": "show-status", "show": ALL}, "children"),
    [Input("status-interval", "n_intervals")]
)
def update_all_show_statuses(n):
    outputs = []
    # Context order matches SHOWS order usually if rendered that way
    # But safe way is to iterate triggers? No, we just iterate SHOWS mapping.
    # We need to map outputs to IDs.
    # Since we create them in loop `for s in SHOWS`, the outputs list matches that order.
    
    for s in SHOWS:
        count = get_sold_count(s['id'])
        if count >= MAX_TICKETS:
            outputs.append(html.Span("UITVERKOCHT", className="text-danger border border-danger p-1 rounded"))
        elif count >= MAX_TICKETS - 10:
             outputs.append(html.Span(f"Nog slechts {MAX_TICKETS - count} tickets!", className="text-warning"))
        else:
            outputs.append("")
    return outputs

# Callback: Add/Remove UitPas
@callback(
    [Output("uitpas-store", "data"),
     Output("uitpas-input", "value"),
     Output("uitpas-error", "children")],
    [Input("btn-add-uitpas", "n_clicks"),
     Input({"type": "btn-remove-uitpas", "index": ALL}, "n_clicks")],
    [State("uitpas-input", "value"),
     State("uitpas-type-input", "value"),
     State("uitpas-store", "data")],
    prevent_initial_call=True
)
def manage_uitpas(n_add, n_remove, number, ticket_type, current_data):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update, dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "btn-add-uitpas":
        if not number or len(number) != 13 or not number.isdigit():
            return dash.no_update, dash.no_update, "Ongeldig UiTPAS nummer (moet 13 cijfers zijn)"
        
        # Check duplicate
        if any(c['number'] == number for c in current_data):
              return dash.no_update, dash.no_update, "Dit nummer is al toegevoegd"

        new_data = current_data + [{"number": number, "type": ticket_type}]
        return new_data, "", ""
    
    elif "btn-remove-uitpas" in trigger_id:
        trigger_obj = json.loads(trigger_id)
        idx_to_remove = trigger_obj['index']
        
        if 0 <= idx_to_remove < len(current_data):
            new_data = [d for i, d in enumerate(current_data) if i != idx_to_remove]
            return new_data, dash.no_update, ""
            
    return dash.no_update, dash.no_update, ""

# Callback: Render UitPas List
@callback(
    Output("uitpas-list", "children"),
    Input("uitpas-store", "data")
)
def render_uitpas_list(data):
    if not data: return []
    
    items = []
    for i, card in enumerate(data):
        label_type = "Grote Uitvinder" if card['type'] == 'large' else "Kleine Uitvinder"
        items.append(dbc.Row([
            dbc.Col(f"{card['number']} - {label_type}", className="text-white"),
            dbc.Col(dbc.Button("Verwijder", id={"type": "btn-remove-uitpas", "index": i}, color="danger", size="sm"), width="auto")
        ], className="mb-2 align-items-center"))
    return items

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

@callback(
    [Output({"type": "ticket-input", "show": MATCH, "category": MATCH}, "value"),
     Output("limit-modal", "is_open"),
     Output("limit-modal-body", "children")],
    [Input({"type": "btn-dec", "show": MATCH, "category": MATCH}, "n_clicks"),
     Input({"type": "btn-inc", "show": MATCH, "category": MATCH}, "n_clicks"),
     Input("close-limit-modal", "n_clicks")],
    [State({"type": "ticket-input", "show": MATCH, "category": MATCH}, "value"),
     State({"type": "ticket-input", "show": MATCH, "category": MATCH}, "id")],
    prevent_initial_call=True
)
def update_input_value(n_dec, n_inc, n_close, current_val, id_map):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update, dash.no_update, dash.no_update
        
    trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Handle Modal Close
    if trigger_id_str == "close-limit-modal":
        return dash.no_update, False, dash.no_update
        
    trigger_id = json.loads(trigger_id_str)
    button_type = trigger_id['type']
    
    if current_val is None:
        current_val = 0
        
    if button_type == "btn-dec":
        return max(0, current_val - 1), dash.no_update, dash.no_update
        
    elif button_type == "btn-inc":
        # CHECK LIMIT
        show_id = id_map['show']
        sold_count = get_sold_count(show_id)
        
        # We need to know current tickets in cart for THIS show to calculate total requested?
        # Ideally yes, but here we only have the 'current_val' of THIS input.
        # But wait, we also have other category input for same show.
        # This callback is isolated (MATCH). It doesn't know about the OTHER input for the same show.
        # This is a limitation of MATCH.
        # However, we can be conservative: Check if sold_count >= MAX.
        # If sold_count + 1 (this increment) > MAX? 
        # But we don't know total requested in cart.
        
        # Simpler check: If sold_count >= MAX, we definitely can't add.
        if sold_count >= MAX_TICKETS:
             return dash.no_update, True, "Deze show is helaas uitverkocht."
             
        # Ideally we should check (sold + current items in cart + 1) > MAX.
        # Since we can't easily access the other input value here without ALL state...
        # Let's trust backend for the strict check, and here just prevent adding if strictly sold out.
        # OR: We can fetch cart-store?
        # But circular dependency risk if we output to input? No.
        # Let's just check current DB count.
             
        return current_val + 1, dash.no_update, dash.no_update
        
    return dash.no_update, dash.no_update, dash.no_update


# Callback 2: Store -> Update Price Display
@callback(
    [Output("cart-details", "children"),
     Output("total-price", "children")],
    [Input("cart-store", "data"),
     Input("uitpas-store", "data")]
)
def calculate_price_from_store(ticket_data, uitpas_cards):
    if not ticket_data:
        return html.P("Laden...", className="text-muted"), "€0"

    # Logic: Per-type chronological discount
    max_prev_large = 0
    max_prev_small = 0
    
    total_cost = 0
    line_items = []
    
    # Ensure chronological order
    show_ids = ['s1', 's2', 's3'] 
    
    for sid in show_ids:
        show = next((s for s in SHOWS if s['id'] == sid), None)
        if not show: continue
        
        s_data = ticket_data.get(sid, {'large': 0, 'small': 0})
        n_large = int(s_data.get('large', 0))
        n_small = int(s_data.get('small', 0))
        
        # 1. Apply UitPas Discounts First
        # Count how many UitCards of each type we have
        uitpas_large_count = sum(1 for c in uitpas_cards if c['type'] == 'large')
        uitpas_small_count = sum(1 for c in uitpas_cards if c['type'] == 'small')
        
        # Calculate UitPas tickets for this show
        n_large_uitpas = min(n_large, uitpas_large_count)
        n_small_uitpas = min(n_small, uitpas_small_count)
        
        # Remaining tickets for normal pricing flow
        rem_large = n_large - n_large_uitpas
        rem_small = n_small - n_small_uitpas
        
        # Cost for UitPas is 20% of full price (80% discount)
        cost_uitpas_large = n_large_uitpas * (PRICES['large'] * 0.2)
        cost_uitpas_small = n_small_uitpas * (PRICES['small'] * 0.2)
        
        # 2. Apply Normal Dynamic Pricing to REMAINING tickets
        # Calculate Large Remainder
        disc_slots_large = max_prev_large
        n_large_disc = min(rem_large, disc_slots_large)
        n_large_full = rem_large - n_large_disc
        
        cost_large_rem = (n_large_full * PRICES['large']) + (n_large_disc * PRICES['discount'])
        
        # Calculate Small Remainder
        disc_slots_small = max_prev_small
        n_small_disc = min(rem_small, disc_slots_small)
        n_small_full = rem_small - n_small_disc
        
        cost_small_rem = (n_small_full * PRICES['small']) + (n_small_disc * PRICES['discount'])
        
        # Update Total
        total_cost += cost_uitpas_large + cost_uitpas_small + cost_large_rem + cost_small_rem
        
        # Update History for next show
        max_prev_large = max(max_prev_large, n_large)
        max_prev_small = max(max_prev_small, n_small)
        
        # Build String
        if n_large + n_small > 0:
            details = []
            if n_large_uitpas > 0: details.append(f"{n_large_uitpas}x Groot (UitPas: €{PRICES['large']*0.2:.2f})")
            if n_large_full > 0: details.append(f"{n_large_full}x Groot (€{PRICES['large']})")
            if n_large_disc > 0: details.append(f"{n_large_disc}x Groot (Showkorting: €{PRICES['discount']})")
            
            if n_small_uitpas > 0: details.append(f"{n_small_uitpas}x Klein (UitPas: €{PRICES['small']*0.2:.2f})")
            if n_small_full > 0: details.append(f"{n_small_full}x Klein (€{PRICES['small']})")
            if n_small_disc > 0: details.append(f"{n_small_disc}x Klein (Showkorting: €{PRICES['discount']})")
            
            line_items.append(html.P(f"{show['name']}: {', '.join(details)}"))
    
    if not line_items:
        line_items.append(html.P("Nog geen tickets geselecteerd.", className="text-muted"))

    return line_items, f"TOTAAL: €{total_cost:,.2f}"


# Client-side callback for Payment
dash.clientside_callback(
    """
    function(n_clicks, cart_data, uitpas_data) {
        if (!n_clicks || n_clicks === 0) {
            return window.dash_clientside.no_update;
        }
        
        // Basic Validation: Check if cart is empty
        var hasItems = false;
        if (cart_data) {
            for (var show in cart_data) {
                if (cart_data[show].large > 0 || cart_data[show].small > 0) {
                    hasItems = true;
                    break;
                }
            }
        }
        
        if (!hasItems) {
            return "Winkelmandje is leeg!";
        }

        // Combine data
        var payload = {
            cart: cart_data,
            uitpas: uitpas_data || []
        };

        console.log("Initiating payment...", payload);
        
        fetch('/config')
            .then((result) => result.json())
            .then((data) => {
                const stripe = Stripe(data.publicKey);
                
                fetch('/create-checkout-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                })
                .then((result) => result.json())
                .then((session) => {
                    console.log("Session created:", session);
                    if (session.error) {
                         console.error(session.error);
                         return "Error: " + session.error;
                    }
                    return stripe.redirectToCheckout({ sessionId: session.sessionId });
                })
                .then((res) => {
                    if (res && res.error) {
                        console.error(res.error);
                    }
                })
                .catch((err) => {
                    console.error("Error:", err);
                });
            });
            
        return "Redirecting naar betaalpagina...";
    }
    """,
    Output("pay-status", "children"),
    Input("pay-btn", "n_clicks"),
    State("cart-store", "data"),
    State("uitpas-store", "data"),
    prevent_initial_call=True
)

