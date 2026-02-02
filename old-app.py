import os
import random
from dash import Dash, html, dcc, callback, Output, Input, State, ALL, clientside_callback
import dash
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import json
from datetime import datetime
import stripe
from flask import Flask, jsonify, request, render_template
from threading import Thread
from time import sleep
from flask_sqlalchemy import SQLAlchemy
import uuid
from db import db, init_db, AccessCode, CheckoutSession  # Import the init_db function from db.py
from tickets import generate_ticket_image
from mail import send_email

# Define the app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], external_scripts = ['https://js.stripe.com/v3/'])
server = app.server
app.title = "Tickets Show 2025"

stripe_keys = {
    'secret_key': os.environ['STRIPE_SECRET_KEY'],
    'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY'],
}
stripe.api_key = stripe_keys['secret_key']

prijs_volw = 12
prijs_kind = 6

# Initialize the database
init_db(server)

# # Define the AccessCode model
# class AccessCode(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
#     used = db.Column(db.Boolean, default=False)
#     type = db.Column(db.String(16), nullable=False)

# # Define the CheckoutSession model
# class CheckoutSession(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     session_id = db.Column(db.String, unique=True, nullable=False)
#     completed = db.Column(db.Boolean, default=False)
#     access_codes = db.relationship('AccessCode', backref='checkout_session', lazy=True)

# # Create the database tables
# with app.server.app_context():
#     db.create_all()

def booking_layout():
    return [
        html.Div([
            html.Div([
                html.Div("Bestemming",className="card-title"),
                html.Div("GC Den Dries - Retie",className="card-text"),
                ], className="card-section"),
            ],
            className="card"
        ),
        html.Div([
            html.H1("Online uitverkocht!"),
            html.P("Onze online balie is uitverkocht! Je kan wel nog steeds een ticket kopen aan de checkin desk!", style={"marginBottom": "0"}),
        ]),
        # html.Div([
        #     html.Div([
        #         html.Div("Datum",className="card-title"),
        #         html.Div("17 Mei 2025",className="card-text"),
        #         ], className="card-section"),
        #     html.Div([
        #         html.Div("Return",className="card-title"),
        #         html.Div("One-way",className="card-text"),
        #         ], className="card-section"),
        #     ],
        #     className="card"
        # ),
        # html.Div([
        #     html.Div([
        #         html.Div(["Passagiers"],className="card-title"),
        #         html.Div([dmc.Button("-", id="min-volw",variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), html.Div(0, id="nb_volw", style={"display": "inline", "fontSize":"1.5rem"}), dmc.Button("+", id="plus-volw", variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), f"Volwassenen (€{prijs_volw})"],className="card-text"),
        #         html.Div([dmc.Button("-", id="min-kind",variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), html.Div(0, id="nb_kind", style={"display": "inline", "fontSize":"1.5rem"}), dmc.Button("+", id="plus-kind", variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), f"Kinderen -12 (€{prijs_kind})"],className="card-text"),
        #         html.Div([dmc.Button("-", id="min-vrijw",variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), html.Div(0, id="nb_vrijw", style={"display": "inline", "fontSize":"1.5rem"}), dmc.Button("+", id="plus-vrijw", variant="subtle", compact=True, style={"fontSize":"2.5rem", "padding":"none", "color":"#488741"}), f"Helper (€0)"],className="card-text"),
        #         ], className="card-section"),
        #     ],
        #     className="card"
        # ),
        # html.Div([
        #     html.Div([
        #         html.Div("Totaal",className="card-title"),
        #         html.Div("",id="totaal",className="card-text"),
        #         ], className="card-section"),
        #     ],
        #     className="card"
        # ),
        # dmc.Button("Afrekenen", id="btn-checkout", style={"backgroundColor":"#488741"}, size="xl", fullWidth=True),
        # html.Div(id="summary")
    ]



def layout():

    return html.Div([
        dcc.Store(id='store', data={'nb_volw': 0, 'nb_kind':0, 'nb_vrijw':0}),
        html.Img(src="/assets/img/banner2.jpeg", className="responsive-img"),
        dmc.SegmentedControl(
            id="segmented",
            value="vlucht",
            data=[
                {"value": "vlucht", "label": "Vlucht"},
                {"value": "parking", "label": "Parking"},
                {"value": "hotel", "label": "Hotel"},
            ],
            mb=10,
            radius=10,
        ),
        html.Div([
            *booking_layout(),
        ], id="content", style={"padding":"0px"}, className="content-container")
        
    ], className="grid-container")

app.layout = layout

app.clientside_callback(
    """
    function(n_clicks, data) {
        var stripe;
        fetch('https://tickets.tsirk.be/config')
            .then((result) => result.json())
            .then((data) => {
            // Initialize Stripe.js
            stripe = Stripe(data.publicKey);
            });
        // Get Checkout Session ID
        fetch('https://tickets.tsirk.be/create-checkout-session', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        })
            .then((result) => result.json())
            .then((data) => {
            console.log(data);
            // Redirect to Stripe Checkout
            return stripe.redirectToCheckout({ sessionId: data.sessionId });
            })
            .then((res) => {
            console.log(res);
            });
            }
    """,
    Output('summary', 'style'),
    Input('btn-checkout', 'n_clicks'),
    State('store', 'data'),
    prevent_initial_call=True
)

@callback(
    Output('content', 'children'),
    Input('segmented', 'value')
)
def update_content(segment_value):
    if segment_value == "vlucht":
        return booking_layout()
    elif segment_value == "parking":
        return html.Div([
            html.Div([
            html.H1("De Show"),
            html.P("GC Den Dries", style={"marginBottom": "0"}),
            html.A("Kerkhofstraat 37, 2470 Retie", href="https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=/maps/place//data%3D!4m2!3m1!1s0x47c6b57d215620bf:0xf742309090c94a17%3Fsa%3DX%26ved%3D1t:8290%26ictx%3D111&ved=2ahUKEwjJz5z726iMAxXk_7sIHXOtI8UQ4kB6BAgkEAM&usg=AOvVaw3ZWgBg_X5b2K151lG_7TAu", target="_blank")
            ]),
            html.Div([
            html.H1("Parking P1"),
            html.P("Parking Gemeentehuis Retie", style={"marginBottom": "0"}),
            html.A("Driesstraat, 2470 Retie", href="https://maps.app.goo.gl/xA5uSGErDLXDcLcDA", target="_blank")
            ]),
            html.Div([
            html.H1("Parking P2"),
            html.P("Parking Sporthal Boesdijkhof", style={"marginBottom": "0"}),
            html.A("Rodekruisplein, 2470 Retie", href="https://maps.app.goo.gl/i1sSjZG6Ku4Wscw69", target="_blank")
            ]),
            html.Br(),
            html.P("Er zijn ook nog enkele kleinere parkings in de omgeving met beperkte capaciteit."),
            html.Br(),
            html.Img(src="/assets/img/show25_parking.jpg", className="responsive-img"),
        ])
    elif segment_value == "hotel":
        return html.Div([
            html.H1("Sold Out"),
            html.P("Helaas! Ons hotel is volledig volgeboekt."),
            html.P("Gelukkig hoef je niets te missen want onze show duurt maar één dag. Waarschijnlijk ben je zelfs op tijd thuis om naar de finale van Eurosong te kunnen kijken.")
        ])
    else:
        raise PreventUpdate

@callback(
    Output('store', 'data'),
    [Output('plus-volw', 'n_clicks'),
     Output('min-volw', 'n_clicks'),
     Output('plus-kind', 'n_clicks'),
     Output('min-kind', 'n_clicks'),
     Output('plus-vrijw', 'n_clicks'),
     Output('min-vrijw', 'n_clicks')],
    [Input('plus-volw', 'n_clicks'),
     Input('min-volw', 'n_clicks'),
     Input('plus-kind', 'n_clicks'),
     Input('min-kind', 'n_clicks'),
     Input('plus-vrijw', 'n_clicks'),
     Input('min-vrijw', 'n_clicks')],
    State('store', 'data')
)
def update_passengers(plus_volw, min_volw, plus_kind, min_kind, plus_vrijw, min_vrijw, store_data):
    # Initialize the click counts to 0 if they are None
    plus_volw = plus_volw or 0
    min_volw = min_volw or 0
    plus_kind = plus_kind or 0
    min_kind = min_kind or 0
    plus_vrijw = plus_vrijw or 0
    min_vrijw = min_vrijw or 0

    # Update the data based on the button clicks
    store_data['nb_volw'] += plus_volw - min_volw
    store_data['nb_kind'] += plus_kind - min_kind
    store_data['nb_vrijw'] += plus_vrijw - min_vrijw

    # Ensure the counts are not negative
    store_data['nb_volw'] = max(store_data['nb_volw'], 0)
    store_data['nb_kind'] = max(store_data['nb_kind'], 0)
    store_data['nb_vrijw'] = max(store_data['nb_vrijw'], 0)

    return store_data, 0,0,0,0,0,0

@callback(
    [Output('nb_volw', 'children'),
     Output('nb_kind', 'children'),
     Output('nb_vrijw', 'children')],
    Input('store', 'data')
)
def display_passengers(store_data):
    # Display the updated number of passengers
    nb_volw = store_data['nb_volw']
    nb_kind = store_data['nb_kind']
    nb_vrijw = store_data['nb_vrijw']

    return nb_volw, nb_kind, nb_vrijw


@callback(
    Output("totaal", "children"),
    Input("store", "data")
)
def calculate_total(store_data):
    # Retrieve the number of adults and children from the store
    nb_volw = store_data.get("nb_volw", 0)
    nb_kind = store_data.get("nb_kind", 0)

    # Calculate the total price
    total_price = (nb_volw * prijs_volw) + (nb_kind * prijs_kind)
    print("Totaal", total_price)

    # Format the total price as a string
    return f"{total_price} Euro"



@server.route('/config')
def config():
    stripe_config = {'publicKey': stripe_keys['publishable_key']}
    return jsonify(stripe_config)

@server.route('/get_tickets')
def get_tickets():
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    with server.app_context():
        session = CheckoutSession.query.filter_by(session_id=session_id).first()
        access_codes = session.access_codes if session else []
        codes_list = [str(code.code) for code in access_codes]
    return jsonify({"codes": codes_list})

@server.route('/success')
def success():
    
    session_id = request.args.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    email = session.get("customer_details", {}).get("email", "Unknown")
    # with server.app_context():
    #     session = CheckoutSession.query.filter_by(session_id=session_id).first()
    #     access_codes = session.access_codes if session else []
    #     codes_list = "".join([f"<li><a href='https://tickets.tsirk.be/assets/tickets/{code.code}.jpeg' download><img src='https://tickets.tsirk.be/assets/tickets/{code.code}.jpeg' alt='Ticket {code.code}' style='max-width:100%; height:auto;'/></a></li>" for code in access_codes])

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Success</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 1200px;
                margin: 50px auto;
                background: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                display: none;
            }}
            h1 {{
                color: #4CAF50;
            }}
            p {{
                font-size: 1.2em;
                color: #333;
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                font-size: 1.1em;
                color: #555;
                margin: 5px 0;
            }}
            .loading {{
                font-size: 1.5em;
                color: #4CAF50;
                margin-top: 50px;
            }}
            .download-all {{
                margin-top: 20px;
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1em;
            }}
            .download-all:hover {{
                background-color: #45a049;
            }}
        </style>
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                const loading = document.getElementById("loading");
                const container = document.querySelector(".container");
                const ticketsList = document.getElementById("tickets-list");
                const sessionId = new URLSearchParams(window.location.search).get("session_id");
                const downloadAllButton = document.getElementById("download-all");

                setTimeout(() => {{
                    fetch(`/get_tickets?session_id=${{sessionId}}`)
                        .then(response => response.json())
                        .then(data => {{
                            ticketsList.innerHTML = data.codes.map(code => `
                                <li>
                                    <a href='https://tickets.tsirk.be/assets/tickets/${{code}}.jpeg' download>
                                        <img src='https://tickets.tsirk.be/assets/tickets/${{code}}.jpeg' alt='Ticket ${{code}}' style='max-width:100%; height:auto;' />
                                    </a>
                                </li>
                            `).join("");
                            loading.style.display = "none";
                            container.style.display = "block";

                            // Add functionality to download all tickets
                            downloadAllButton.addEventListener("click", () => {{
                                data.codes.forEach(code => {{
                                    const link = document.createElement("a");
                                    link.href = `https://tickets.tsirk.be/assets/tickets/${{code}}.jpeg`;
                                    link.download = `tsirk-ticket-${{code}}.jpeg`; // Set the desired filename
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);
                                }});
                            }});
                        }})
                        .catch(error => {{
                            console.error("Error fetching tickets:", error);
                            loading.textContent = "Er is een fout opgetreden bij het ophalen van je tickets.";
                        }});
                }}, 4000);
            }});
        </script>
    </head>
    <body>
        <div id="loading" class="loading">We drukken even jouw tickets. Dit kan enkele seconden duren...</div>
        <div class="container">
            <h1>Betaling Succesvol!</h1>
            <p>Bedankt voor je aankoop</br>Vergeet je tickets niet te downloaden met de knop hieronder!</p>
            <!--<p>Boeking email: <strong>{email}</strong></p>-->
            <button id="download-all" class="download-all">Download Jouw Tickets</button>
            <p>Jouw tickets:</p>
            <ul id="tickets-list"></ul>
        </div>
    </body>
    </html>
    """
@server.route('/access_codes_count', methods=['GET'])
def access_codes_count():
    with server.app_context():
        total_count = AccessCode.query.count()
        type_counts = db.session.query(
            AccessCode.type, db.func.count(AccessCode.type)
        ).group_by(AccessCode.type).all()

        type_counts_dict = {type_: count for type_, count in type_counts}

    return jsonify({
        "total": total_count,
        "counts_per_type": type_counts_dict
    })

@server.route('/checkin', methods=['GET', 'POST'])
def scan_ticket():
    if request.method == 'GET':
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>QR Code Scanner</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"></script>
            <style>
            body {
            font-family: Arial, sans-serif;
            text-align: center;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            }
            .container {
            margin: 20px auto;
            max-width: 600px;
            }
            button {
            margin: 10px;
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            }
            .blue-button {
            background-color: #007bff;
            color: white;
            }
            .green-button {
            background-color: #28a745;
            color: white;
            }
            .error-message {
            color: red;
            font-weight: bold;
            }
            </style>
        </head>
        <body>
            <div class="container">
            <h1>QR Code Scanner</h1>
            <div id="reader" style="width: 100%;"></div>
            <div id="result"></div>
            <button id="check-in-ticket" class="blue-button" style="display: none;">Check in dit ticket</button>
            <button id="check-in-all" class="green-button" style="display: none;">Check in alle tickets</button>
            </div>
            <script>
            const reader = new Html5Qrcode("reader");
            const resultDiv = document.getElementById("result");
            const checkInTicketButton = document.getElementById("check-in-ticket");
            const checkInAllButton = document.getElementById("check-in-all");
            let scannedCode = null;

            function onScanSuccess(decodedText) {
            scannedCode = decodedText.split("/").slice(-1);
            fetch(`/checkin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ code: scannedCode })
            })
            .then(response => response.json())
            .then(data => {
                if (data.is_valid === false) {
                resultDiv.innerHTML = "<p class='error-message'>Dit ticket is al ingecheckt</p>";
                resultDiv.innerHTML += `
                <h2>Tickets:</h2>
                <ul>
                    ${Object.entries(data.counts_per_type).map(([type, count]) => `<li>${type}: ${count}</li>`).join('')}
                </ul>
                `;
                checkInTicketButton.style.display = "none";
                checkInAllButton.style.display = "none";
                } else {
                resultDiv.innerHTML = `<p>Dit ticket is een ${data.type} ticket</p>`;
                resultDiv.innerHTML += `
                <h2>Tickets:</h2>
                <ul>
                    ${Object.entries(data.counts_per_type).map(([type, count]) => `<li>${type}: ${count}</li>`).join('')}
                </ul>
                `;
                checkInTicketButton.style.display = "inline-block";
                checkInAllButton.style.display = "inline-block";
                }
            })
            .catch(error => {
                console.error("Error fetching ticket data:", error);
                resultDiv.innerHTML = "<p>Er is een fout opgetreden bij het ophalen van de ticketinformatie.</p>";
            });
            }

            reader.start({ facingMode: "environment" }, { fps: 10, qrbox: 250 }, onScanSuccess);

            checkInTicketButton.addEventListener("click", () => {
            fetch(`/checkin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ code: scannedCode, action: "check_in_ticket" })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                location.reload();
            });
            });

            checkInAllButton.addEventListener("click", () => {
            fetch(`/checkin`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ code: scannedCode, action: "check_in_all" })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                location.reload();
            });
            });
            </script>
        </body>
        </html>
        """
    elif request.method == 'POST':
        data = request.get_json()
        code = data.get('code')[-1]
        action = data.get('action')
        # print(code, action)
        if not code and not action:
            return jsonify({"error": "Invalid request"}), 400

        # Extract the UUID from the scanned code (URL)
        uuid_code = code
        # print(uuid_code)

        with server.app_context():
            ticket = AccessCode.query.filter_by(code=uuid_code).first()
            # print(ticket)
            if not ticket:
                return jsonify({"error": "Ticket not found"}), 404
            if code and not action:
                with server.app_context():
                    ticket = AccessCode.query.filter_by(code=uuid_code).first()
                    if not ticket:
                        return jsonify({"error": "Ticket not found"}), 404
                    session = ticket.checkout_session
                    type_counts = db.session.query(
                        AccessCode.type, db.func.count(AccessCode.type)
                    ).filter_by(checkout_session=session, is_valid=True).group_by(AccessCode.type).all()
                    type_counts_dict = {type_: count for type_, count in type_counts}
                    return jsonify({"counts_per_type": type_counts_dict, "is_valid": ticket.is_valid, "type": ticket.type})
            if action == 'check_in_ticket':
                ticket.is_valid = False
                db.session.commit()
                return jsonify({"message": "Ticket successfully checked in"})
            elif action == 'check_in_all':
                session = ticket.checkout_session
                AccessCode.query.filter_by(checkout_session=session, is_valid=True).update({"is_valid": False})
                db.session.commit()
                return jsonify({"message": "All tickets in the session successfully checked in"})
            else:
                return jsonify({"error": "Invalid action"}), 400

    else:
        return jsonify({"error": "Invalid method"}), 405
# @server.route('/scan', methods=['GET', 'POST'])
# def scan_ticket():
#     if request.method == 'GET':
#         return """
#         <!DOCTYPE html>
#         <html lang="en">
#         <head>
#             <meta charset="UTF-8">
#             <meta name="viewport" content="width=device-width, initial-scale=1.0">
#             <title>QR Code Scanner</title>
#             <script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"></script>
#             <style>
#                 body {
#                     font-family: Arial, sans-serif;
#                     text-align: center;
#                     margin: 0;
#                     padding: 0;
#                     background-color: #f4f4f4;
#                 }
#                 .container {
#                     margin: 20px auto;
#                     max-width: 600px;
#                 }
#                 button {
#                     margin: 10px;
#                     padding: 10px 20px;
#                     font-size: 16px;
#                     border: none;
#                     border-radius: 5px;
#                     cursor: pointer;
#                 }
#                 .blue-button {
#                     background-color: #007bff;
#                     color: white;
#                 }
#                 .green-button {
#                     background-color: #28a745;
#                     color: white;
#                 }
#             </style>
#         </head>
#         <body>
#             <div class="container">
#                 <h1>QR Code Scanner</h1>
#                 <div id="reader" style="width: 100%;"></div>
#                 <div id="result"></div>
#                 <button id="check-in-ticket" class="blue-button" style="display: none;">Check in dit ticket</button>
#                 <button id="check-in-all" class="green-button" style="display: none;">Check in alle tickets</button>
#             </div>
#             <script>
#                 const reader = new Html5Qrcode("reader");
#                 const resultDiv = document.getElementById("result");
#                 const checkInTicketButton = document.getElementById("check-in-ticket");
#                 const checkInAllButton = document.getElementById("check-in-all");
#                 let scannedCode = null;

#                 function onScanSuccess(decodedText) {
#                     scannedCode = decodedText;
#                     fetch(`/scan?code=${encodeURIComponent(decodedText)}`)
#                         .then(response => response.json())
#                         .then(data => {
#                             resultDiv.innerHTML = `
#                                 <h2>Tickets:</h2>
#                                 <ul>
#                                     ${Object.entries(data.counts_per_type).map(([type, count]) => `<li>${type}: ${count}</li>`).join('')}
#                                 </ul>
#                             `;
#                             checkInTicketButton.style.display = "inline-block";
#                             checkInAllButton.style.display = "inline-block";
#                         })
#                         .catch(error => {
#                             console.error("Error fetching ticket data:", error);
#                             resultDiv.innerHTML = "<p>Er is een fout opgetreden bij het ophalen van de ticketinformatie.</p>";
#                         });
#                 }

#                 reader.start({ facingMode: "environment" }, { fps: 10, qrbox: 250 }, onScanSuccess);

#                 checkInTicketButton.addEventListener("click", () => {
#                     fetch(`/scan?code=${encodeURIComponent(scannedCode)}&action=check_in_ticket`, { method: "POST" })
#                         .then(response => response.json())
#                         .then(data => {
#                             alert(data.message);
#                             location.reload();
#                         });
#                 });

#                 checkInAllButton.addEventListener("click", () => {
#                     fetch(`/scan?code=${encodeURIComponent(scannedCode)}&action=check_in_all`, { method: "POST" })
#                         .then(response => response.json())
#                         .then(data => {
#                             alert(data.message);
#                             location.reload();
#                         });
#                 });
#             </script>
#         </body>
#         </html>
#         """
#     elif request.method == 'POST':
#         code = request.args.get('code')
#         action = request.args.get('action')
#         if not code or not action:
#             return jsonify({"error": "Invalid request"}), 400

#         with server.app_context():
#             ticket = AccessCode.query.filter_by(code=code, is_valid=True).first()
#             if not ticket:
#                 return jsonify({"error": "Ticket not found or already checked in"}), 404

#             if action == 'check_in_ticket':
#                 ticket.is_valid = False
#                 db.session.commit()
#                 return jsonify({"message": "Ticket successfully checked in"})
#             elif action == 'check_in_all':
#                 session = ticket.checkout_session
#                 AccessCode.query.filter_by(checkout_session=session, is_valid=True).update({"is_valid": False})
#                 db.session.commit()
#                 return jsonify({"message": "All tickets in the session successfully checked in"})
#             else:
#                 return jsonify({"error": "Invalid action"}), 400

#     else:
#         return jsonify({"error": "Invalid method"}), 405

def fullfill_order(data, event):
    # Fulfill the order
    if event["type"] == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]
        session = stripe.checkout.Session.retrieve(session_id)
        line_items = stripe.checkout.Session.list_line_items(session_id)
        email = event["data"]["object"].get("customer_details", {}).get("email")  # Get email
        print("Session ID:", session_id)
        # Create a new CheckoutSession in the database
        with server.app_context():
            from db import CheckoutSession  # Import the CheckoutSession model
            new_session = CheckoutSession(
                session_id=session_id,
                status=event["data"]["object"]["status"],
                type=event["type"],
                payment_status=event["data"]["object"]["payment_status"],
                email=email,
            )
            db.session.add(new_session)
            db.session.commit()


        for item in line_items["data"]:
            description = item["description"]
            unit_amount = item["price"]["unit_amount"]
            quantity = item["quantity"]

            # Create "quantity" number of access codes
            with server.app_context():
                checkout_session = CheckoutSession.query.filter_by(session_id=session_id).first()
                if checkout_session:
                    for _ in range(quantity):
                        code = str(uuid.uuid4())
                        access_code = AccessCode(
                            code=code,
                            is_valid=True,
                            type=description,
                            checkout_session=checkout_session
                        )
                        db.session.add(access_code)
                        db.session.commit()
                        generate_ticket_image(code)
            print(f"Description: {description}, Unit Amount: {unit_amount}, Quantity: {quantity}")
        # Send an email with the download link
        send_email(f"https://tickets.tsirk.be/success?session_id={session_id}", email, email)
    print("payment_status", event["data"]["object"]["payment_status"])
    print("status", event["data"]["object"]["status"])
    print("type", event["type"])
    sleep(2)


@server.route('/success-hook', methods=['POST'])
def success_hook():
    # print("hooked")
    data = request.get_json()
    # print("hook", data)

    # with open(f'./hook_input_{datetime.now().strftime("%Y%m%d%H%M%S")}.json', 'w') as f:
    #     json.dump(data, f)


    try:
        event = stripe.Event.construct_from(
        data, stripe.api_key
        )
    except ValueError as e:
        # Invalid payload
        print(invalid, e)
        return "", 400

    # Process the data as needed
    thread = Thread(target=fullfill_order, args=(data,event))
    thread.start()
    # print("exit")
    return '', 200

@server.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    domain_url = 'https://tickets.tsirk.be'
    print(request.data) 

    data = json.loads(request.data)

    line_items = []

    if data["nb_volw"] > 0 :
        line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Volwassen Ticket',
                    },
                    'unit_amount': round(float(prijs_volw) * 100),
                },
                'quantity': data["nb_volw"],
            })
    if data["nb_kind"] > 0:
        line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Kinder Ticket',
                    },
                    'unit_amount': round(float(prijs_kind) * 100),
                },
                'quantity': data["nb_kind"],
            })
    if data["nb_vrijw"] > 0:
        line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Vrijwilliger Ticket',
                    },
                    'unit_amount': 0,
                },
                'quantity': data["nb_vrijw"],
            })

    print(line_items)
            
        

    try:
        # create new checkout session
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + '/success?session_id={CHECKOUT_SESSION_ID}',
            # cancel_url=domain_url + '/canceled',
            cancel_url=domain_url,
            payment_method_types=["bancontact"],
            mode='payment',
            line_items=line_items
        )

# card, acss_debit, affirm, afterpay_clearpay, alipay, au_becs_debit, bacs_debit, bancontact, blik, boleto, cashapp, customer_balance, eps, fpx, giropay, grabpay, ideal, klarna, konbini, link, multibanco, oxxo, p24, pay_by_bank, paynow, paypal, pix, promptpay, sepa_debit, sofort, swish, us_bank_account, wechat_pay, revolut_pay, mobilepay, zip, amazon_pay, alma, twint, kr_card, naver_pay, kakao_pay, payco, or samsung_pay"

        return jsonify({'sessionId': checkout_session['id']})
    except Exception as e:
        return jsonify(error=str(e)), 403

    
# Run the app
if __name__ == "__main__":
    app.run_server(debug=False, host='0.0.0.0', port=5000)
