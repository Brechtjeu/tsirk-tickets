import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from urllib.parse import parse_qs
from db import CheckoutSession, AccessCode

dash.register_page(__name__, path='/success')

layout = dbc.Container([
    dcc.Interval(id='ticket-poller', interval=2000, n_intervals=0),
    dcc.Location(id='url', refresh=False),
    
    html.Div([
        html.H1("BETALING SUCCESVOL!", className="text-gold text-center mb-4"),
        html.P("Bedankt voor je aankoop. Tot op de show!", className="text-white text-center mb-4"),
        
        # Loading Indicator
        html.Div(id='loading-spinner', children=[
            dbc.Spinner(color="warning", type="grow"),
            html.P("Even geduld...", className="text-muted small mt-2")
        ], className="text-center mb-5"),
        
        # Ticket List Area
        html.Div(id='ticket-result', className="text-center"),
        
        dbc.Button("TERUG NAAR HOME", href="/", className="btn-gold mt-5")
    ], className="py-5")
], className="container mt-5")

@callback(
    [Output('ticket-result', 'children'),
     Output('loading-spinner', 'style'),
     Output('ticket-poller', 'disabled')],
    [Input('ticket-poller', 'n_intervals'),
     Input('url', 'search')]
)
def poll_for_tickets(n, search):
    if not search:
        return html.P("Geen sessie gevonden.", className="text-danger"), {'display': 'none'}, True
        
    try:
        # Parse query string: ?session_id=...
        query_params = parse_qs(search.lstrip('?'))
        session_id = query_params.get('session_id', [None])[0]
        
        if not session_id:
             return html.P("Geen geldig sessie ID.", className="text-danger"), {'display': 'none'}, True

        # Query DB
        session = CheckoutSession.query.filter_by(session_id=session_id).first()
        
        if not session:
             # Wait for webhook to Create session
             return dash.no_update, {'display': 'block'}, False
             
        access_codes = session.access_codes
        
        if not access_codes:
             # Session exists but tickets not ready (thread running)
             return dash.no_update, {'display': 'block'}, False
             
        # Tickets Ready!
        tickets_list = []
        for code in access_codes:
            # Assuming images are accessible at /assets/tickets/CODE.jpeg based on old-app
            # We need to make sure generate_ticket_image saves them there.
            # ticket.py saves to "assets/tickets/{id}.jpeg"
            tickets_list.append(
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"TICKET: {code.type}", className="text-primary"),
                        html.P(f"Code: {code.code}", className="text-muted"),
                        html.A(
                            dbc.Button("DOWNLOAD TICKET", className="btn-gold btn-sm"),
                            href=f"/assets/tickets/{code.code}.jpeg",
                            download=f"ticket_{code.code}.jpeg",
                            target="_blank" # open in new tab/download
                        )
                    ])
                ], className="mb-3 bg-light text-dark") # Light card for contrast or Dark? 
                # Let's match theme: Dark card
            )
            
        # Re-style cards for dark theme
        dark_tickets_list = []
        for code in access_codes:
             dark_tickets_list.append(
                html.Div([
                    html.Div([
                        html.H5(code.type, className="text-gold"),
                        html.P(code.code, className="h4 text-white font-monospace mb-3"),
                        html.A(
                            "DOWNLOAD TICKET",
                            href=f"/assets/tickets/{code.code}.jpeg",
                            download=f"tsirk_ticket_{code.code}.jpeg",
                            className="btn btn-gold w-100"
                        )
                    ], className="p-3 border border-warning rounded bg-dark-transparent")
                ], className="mb-3 col-12 col-md-6")
             )

        return dbc.Row(dark_tickets_list, className="justify-content-center"), {'display': 'none'}, True

    except Exception as e:
        return html.P(f"Er ging iets mis: {str(e)}", className="text-danger"), {'display': 'none'}, True
