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
     Input("manual-code-input", "n_submit")], 
    [State("manual-code-input", "value")], 
    prevent_initial_call=True
)
def handle_check_action(n_check, n_checkin, n_checkin_all, n_sub, code_val):
    ctx = dash.callback_context
    if not ctx.triggered: return dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 1. Check Logic (Manual or Scan)
    if trigger_id == "btn-check-code" or trigger_id == "manual-code-input":
        return process_scan_or_manual(code_val)

    # 2. Check-In Individual Ticket
    if "btn-checkin" in trigger_id and "btn-checkin-all" not in trigger_id:
        import json
        t_id = json.loads(trigger_id)
        return process_checkin(t_id['code'])

    # 3. Check-In ALL Valid
    if "btn-checkin-all" in trigger_id:
        import json
        t_id = json.loads(trigger_id)
        return process_checkin_all(t_id['session'])

    return dash.no_update

def process_scan_or_manual(code_val):
    code = code_val.strip().upper() if code_val else ""
    if len(code) > 6: # Handle URL paste
        if "id=" in code:
            code = code.split("id=")[1][:6]
    return render_scan_result(code)

def process_checkin(target_code):
    ticket = AccessCode.query.filter_by(code=target_code).first()
    if ticket:
        ticket.scanned_at = datetime.now()
        db.session.commit()
        return render_scan_result(target_code)
    return dash.no_update

def process_checkin_all(session_id):
    session = CheckoutSession.query.get(session_id)
    if session:
        for t in session.access_codes:
            if t.is_valid and not t.scanned_at:
                t.scanned_at = datetime.now()
        db.session.commit()
        
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
                window.html5QrCode.stop().then(() => {
                    console.log("Stopped existing scanner");
                }).catch(err => {});
            }
            
            const html5QrCode = new Html5Qrcode("reader");
            window.html5QrCode = html5QrCode;
            window.lastScanTime = 0; // Initialize cooldown
            
            const config = { fps: 10, qrbox: { width: 250, height: 250 } };
            
            html5QrCode.start({ facingMode: "environment" }, config, (decodedText, decodedResult) => {
                // Success Callback
                const now = Date.now();
                if (now - window.lastScanTime < 5000) {
                     console.log("Ignored scan due to cooldown");
                     return;
                }
                
                window.lastScanTime = now;
                console.log(`Code matched = ${decodedText}`, decodedResult);
                
                // Use last 6 chars only
                let finalCode = decodedText;
                if (finalCode.length > 6) {
                    finalCode = finalCode.slice(-6);
                }
                
                // Set value using property descriptor to support React
                const input = document.getElementById("manual-code-input");
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(input, finalCode);
                
                // Dispatch input event for Dash/React to pick it up
                input.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Click the button
                document.getElementById("btn-check-code").click();
                
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
