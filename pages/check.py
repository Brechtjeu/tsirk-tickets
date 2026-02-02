import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_bootstrap_components as dbc
from datetime import datetime
from db import db, AccessCode, CheckoutSession

dash.register_page(__name__, path='/check')

CHECK_PASSWORD = "tsirk-scanner-2026"

layout = html.Div([
    dbc.Container([
        html.H1("Ticket Scanner Entrance", className="text-center my-4 text-white"),
        
        # Login
        html.Div(id="check-login-section", children=[
             dbc.Row([
                dbc.Col([
                    dbc.Input(id="check-password-input", type="password", placeholder="Access Code", className="mb-2"),
                    dbc.Button("Login", id="check-login-btn", color="success", className="w-100"),
                ], width=12, md=4)
            ], justify="center")
        ]),

        # Scanner Interface
        html.Div(id="scanner-interface", style={'display': 'none'}, children=[
            # Camera Section
            dbc.Row([
                dbc.Col([
                    html.Div(id="reader", style={'width': '100%', 'maxWidth': '500px', 'margin': '0 auto'}),
                    dbc.Button("Start/Stop Camera", id="btn-toggle-camera", color="info", className="mt-2 w-100 mb-4"),
                ], width=12, md=6),
                
                # Manual Input
                dbc.Col([
                     dbc.Card([
                        dbc.CardBody([
                            html.H5("Manual Entry", className="card-title text-dark"),
                            dbc.Input(id="manual-code-input", placeholder="6-char Code", className="mb-2 text-dark"),
                            dbc.Button("Check Code", id="btn-check-code", color="primary", className="w-100"),
                        ])
                    ]),
                ], width=12, md=6)
            ]),
            
            html.Hr(className="bg-white"),
            
            # Results Area
            html.Div(id="scan-result-area"),
            html.Div(id="dummy-output", style={'display': 'none'}) # For client side callback side effects
        ])
    ], className="py-4")
])

# Login Callback
@callback(
    [Output("check-login-section", "style"),
     Output("scanner-interface", "style")],
    [Input("check-login-btn", "n_clicks")],
    [State("check-password-input", "value")]
)
def check_login(n, password):
    if not n: return {'display': 'block'}, {'display': 'none'}
    if password == CHECK_PASSWORD:
        return {'display': 'none'}, {'display': 'block'}
    return dash.no_update, dash.no_update

# Check Code Logic
@callback(
    Output("scan-result-area", "children"),
    [Input("btn-check-code", "n_clicks"),
     Input({"type": "btn-checkin", "code": ALL}, "n_clicks"),
     Input({"type": "btn-checkin-all", "session": ALL}, "n_clicks"),
     Input("manual-code-input", "n_submit")], # Allow Enter key
    [State("manual-code-input", "value"),
     State("scan-result-area", "children")], 
    prevent_initial_call=True
)
def handle_check_action(n_check, n_checkin, n_checkin_all, n_sub, code_val, current_children):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 1. Check Logic (Manual or Scan)
    # Scan is handled via filling the input and clicking the button via JS, so logic is same
    if trigger_id == "btn-check-code" or trigger_id == "manual-code-input":
        code = code_val.strip().upper() if code_val else ""
        if len(code) > 6: # Handle URL paste
            if "id=" in code:
                code = code.split("id=")[1][:6]
        
        return render_scan_result(code)

    # 2. Check-In Individual Ticket
    if "btn-checkin" in trigger_id and "btn-checkin-all" not in trigger_id:
        # Parse code from dict ID
        import json
        t_id = json.loads(trigger_id)
        target_code = t_id['code']
        
        ticket = AccessCode.query.filter_by(code=target_code).first()
        if ticket:
            ticket.scanned_at = datetime.now()
            db.session.commit()
            
            # Refresh the view for the SAME group (find the session)
            # Find any ticket from the group -> get session -> refresh
            return render_scan_result(target_code) # Rerender will show updated status

    # 3. Check-In ALL Valid
    if "btn-checkin-all" in trigger_id:
        import json
        t_id = json.loads(trigger_id)
        session_id = t_id['session'] # This is db ID
        
        session = CheckoutSession.query.get(session_id)
        if session:
            for t in session.access_codes:
                if t.is_valid and not t.scanned_at:
                    t.scanned_at = datetime.now()
            db.session.commit()
            
            # Refresh view. Use first code from session to trigger render
            if session.access_codes:
                return render_scan_result(session.access_codes[0].code)

    return dash.no_update

def render_scan_result(code):
    ticket = AccessCode.query.filter_by(code=code).first()
    
    if not ticket:
        return dbc.Alert(f"Ticket code '{code}' not found!", color="danger")
    
    # Get Siblings
    session = ticket.checkout_session
    siblings = session.access_codes
    
    # Build UI
    # Header: Scanned Ticket
    
    scanned_status = "VALID"
    color = "success"
    if not ticket.is_valid:
        scanned_status = "INVALID (Payment/UitPas)"
        color = "danger"
    elif ticket.scanned_at:
        scanned_status = f"USED at {ticket.scanned_at.strftime('%H:%M')}"
        color = "warning"
        
    main_card = dbc.Card([
        dbc.CardHeader(html.H4(f"Scanned: {ticket.code}", className="mb-0")),
        dbc.CardBody([
            html.H2(scanned_status, className=f"text-{color}"),
            html.H5(ticket.type),
            html.P(f"UiTPAS: {ticket.uitpas_number}" if ticket.uitpas_number else ""),
            # Allow checkin if valid & not used
            dbc.Button("CHECK IN THIS TICKET", id={"type": "btn-checkin", "code": ticket.code}, 
                       color="success", size="lg", className="w-100 mt-2",
                       disabled=(not ticket.is_valid or ticket.scanned_at is not None))
        ])
    ], color=color, inverse=False, style={'borderWidth': '4px'})
    
    # Sibling List
    rows = []
    valid_count = 0
    for sib in siblings:
        s_status = "Valid"
        s_color = "text-success"
        btn_disabled = False
        
        if not sib.is_valid:
            s_status = "Invalid"
            s_color = "text-danger"
            btn_disabled = True
        elif sib.scanned_at:
            s_status = "Used"
            s_color = "text-warning"
            btn_disabled = True
        else:
            valid_count += 1
            
        rows.append(html.Tr([
            html.Td(sib.code, className="fw-bold"),
            html.Td(sib.type),
            html.Td(s_status, className=s_color),
            html.Td(dbc.Button("Check In", id={"type": "btn-checkin", "code": sib.code}, 
                               size="sm", color="success", disabled=btn_disabled))
        ]))
        
    sibling_table = dbc.Table([
        html.Thead(html.Tr([html.Th("Code"), html.Th("Type"), html.Th("Status"), html.Th("Action")])),
        html.Tbody(rows)
    ], striped=True, bordered=True, hover=True, className="mt-3 bg-white")
    
    group_actions = []
    if valid_count > 0:
        group_actions.append(
            dbc.Button(f"CHECK IN ALL {valid_count} VALID TICKETS", 
                       id={"type": "btn-checkin-all", "session": session.id},
                       color="primary", size="lg", className="w-100 my-3")
        )
    
    return html.Div([
        main_card,
        html.H4("Booking Group", className="mt-4 text-white"),
        html.P(f"Order: {session.email}", className="text-white-50"),
        *group_actions,
        sibling_table
    ])

# Client-Side Scanner Logic
dash.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            if (window.html5QrCode) {
                // Stop if running
                window.html5QrCode.stop().then(() => {
                    console.log("Stopped existing scanner");
                }).catch(err => {
                    // Ignore stop error
                });
            }
            
            const html5QrCode = new Html5Qrcode("reader");
            window.html5QrCode = html5QrCode;
            
            const config = { fps: 10, qrbox: { width: 250, height: 250 } };
            
            html5QrCode.start({ facingMode: "environment" }, config, (decodedText, decodedResult) => {
                // Success
                console.log(`Code matched = ${decodedText}`, decodedResult);
                
                // Set value to input and click check
                document.getElementById("manual-code-input").value = decodedText;
                document.getElementById("btn-check-code").click();
                
                // Optional: Stop on success? Maybe keep running for group?
                // html5QrCode.stop();
            }, (errorMessage) => {
                // parse error, ignore
            })
            .catch(err => {
                console.error("Error starting scanner", err);
            });
        }
        return "";
    }
    """,
    Output("dummy-output", "children"),
    Input("btn-toggle-camera", "n_clicks"),
    prevent_initial_call=True
)
