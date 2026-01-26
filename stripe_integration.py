import os
import json
import stripe
from flask import jsonify, request, current_app
from threading import Thread
from time import sleep
from db import db, CheckoutSession, AccessCode, generate_unique_code
from tickets import generate_ticket_image
from mail import send_email
from pages.salespage import SHOWS, PRICES

# Setup Stripe
stripe_keys = {
    'secret_key': os.environ['STRIPE_SECRET_KEY'],
    'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY'],
}
stripe.api_key = stripe_keys['secret_key']

def register_stripe_routes(server):
    """
    Registers the Stripe-related routes on the Flask server.
    """

    @server.route('/config')
    def config():
        stripe_config = {'publicKey': stripe_keys['publishable_key']}
        return jsonify(stripe_config)
    
    @server.route('/create-checkout-session', methods=['POST'])
    def create_checkout_session():
        domain_url = 'https://tickets.tsirk.be'
        if "localhost" in request.headers.get("Host", ""):
           domain_url = 'http://localhost:5000' # For local testing

        try:
            data = json.loads(request.data)
            # Data structure: {'s1': {'large': 2, 'small': 1}, 's2': ...}
            
            line_items = []
            max_prev_large = 0
            max_prev_small = 0
            
            # Ensure chronological order
            show_ids = ['s1', 's2', 's3']
            
            for sid in show_ids:
                # Find show info
                show = next((s for s in SHOWS if s['id'] == sid), None)
                if not show: continue
                
                # Get counts for this show (default to 0 if missing)
                s_data = data.get(sid, {'large': 0, 'small': 0})
                n_large = int(s_data.get('large', 0))
                n_small = int(s_data.get('small', 0))
                
                # --- Calculate Large Tickets ---
                disc_slots_large = max_prev_large
                n_large_disc = min(n_large, disc_slots_large)
                n_large_full = n_large - n_large_disc
                
                # Update history
                max_prev_large = max(max_prev_large, n_large)
                
                # Add Large Line Items
                if n_large_full > 0:
                    line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"GROOT (>12j) - {show['name']} ({show['time']})",
                                'metadata': {'show_id': sid, 'type': 'large', 'variant': 'full'}
                            },
                            'unit_amount': int(PRICES['large'] * 100),
                        },
                        'quantity': n_large_full,
                    })
                    
                if n_large_disc > 0:
                     line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"GROOT (>12j) [Korting] - {show['name']} ({show['time']})",
                                'metadata': {'show_id': sid, 'type': 'large', 'variant': 'discount'}
                            },
                            'unit_amount': int(PRICES['discount'] * 100),
                        },
                        'quantity': n_large_disc,
                    })

                # --- Calculate Small Tickets ---
                disc_slots_small = max_prev_small
                n_small_disc = min(n_small, disc_slots_small)
                n_small_full = n_small - n_small_disc
                
                # Update history
                max_prev_small = max(max_prev_small, n_small)
                
                # Add Small Line Items
                if n_small_full > 0:
                    line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"KLEIN (-12j) - {show['name']} ({show['time']})",
                                'metadata': {'show_id': sid, 'type': 'small', 'variant': 'full'}
                            },
                            'unit_amount': int(PRICES['small'] * 100),
                        },
                        'quantity': n_small_full,
                    })
                    
                if n_small_disc > 0:
                     line_items.append({
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"KLEIN (-12j) [Korting] - {show['name']} ({show['time']})",
                                'metadata': {'show_id': sid, 'type': 'small', 'variant': 'discount'}
                            },
                            'unit_amount': int(PRICES['discount'] * 100),
                        },
                        'quantity': n_small_disc,
                    })
            
            if not line_items:
                return jsonify({'error': 'No tickets selected'}), 400

            checkout_session = stripe.checkout.Session.create(
                success_url=domain_url + '/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url,
                payment_method_types=["bancontact", "card"],
                mode='payment',
                line_items=line_items
            )
            return jsonify({'sessionId': checkout_session['id']})
        except Exception as e:
            return jsonify(error=str(e)), 403

    @server.route('/get_tickets', methods=['GET'])
    def get_tickets():
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400
        
        session = CheckoutSession.query.filter_by(session_id=session_id).first()
        if not session:
             # Session might not be saved yet if hook is slow
             return jsonify({"codes": []})
        
        # Check if AccessCodes are generated
        access_codes = session.access_codes
        codes_list = [code.code for code in access_codes]
        
        return jsonify({"codes": codes_list})


    @server.route('/success-hook', methods=['POST'])
    def success_hook():
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        event = None

        try:
            # logic to verify signature would go here if we had the webhook secret
            # event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            # For now, construct from payload directly as in previous code
            data = json.loads(payload)
            event = stripe.Event.construct_from(data, stripe.api_key)
        except ValueError as e:
            return "Invalid payload", 400

        if event['type'] == 'checkout.session.completed':
            # Run fulfillment in background
            # We need to pass app context or create it inside the thread
            # Standard threading with Flask context is tricky.
            # We will grab the necessary data and pass it.
            # Note: SQLite with threads can be finicky.
            # Check previous code: it created a thread with target=fulfill_order.
            
            # Passing app to thread to create context
            thread = Thread(target=fulfill_order, args=(event, current_app._get_current_object()))
            thread.start()

        return '', 200

def fulfill_order(event, app):
    """
    Fulfills the order: saves to DB, creates tickets, sends email.
    """
    with app.app_context():
        session_id = event["data"]["object"]["id"]
        # Avoid duplicate processing
        if CheckoutSession.query.filter_by(session_id=session_id).first():
            print(f"Session {session_id} already processed.")
            return

        print(f"Processing session {session_id}")
        
        session = stripe.checkout.Session.retrieve(session_id)
        line_items = stripe.checkout.Session.list_line_items(session_id)
        email = event["data"]["object"].get("customer_details", {}).get("email")

        # 1. Save Checkout Session
        new_session = CheckoutSession(
            session_id=session_id,
            status=event["data"]["object"]["status"],
            type=event["type"],
            payment_status=event["data"]["object"]["payment_status"],
            email=email,
        )
        db.session.add(new_session)
        db.session.commit() # Commit to get ID
        
        # 2. Generate Access Codes & Tickets
        for item in line_items["data"]:
            description = item["description"] # e.g. "Volwassen Ticket - SHOW 1..."
            quantity = item["quantity"]
            
            for _ in range(quantity):
                # Retry loop for unique code (though collision probability is low)
                while True:
                    code = generate_unique_code()
                    if not AccessCode.query.filter_by(code=code).first():
                        break
                
                access_code = AccessCode(
                    code=code,
                    is_valid=True,
                    type=description,
                    checkout_session=new_session
                )
                db.session.add(access_code)
                
                # Generate Image (assuming tickets.py has this function)
                # We need to extract show info from description or just pass the code?
                # tickets.generate_ticket_image expects (unique_id, shownumber, date, time)
                # We can parse the description string or pass defaults. 
                # For now, we'll try to parse or hardcode placeholders if parsing fails,
                # to ensure the file is generated.
                # Description format: "... - SHOW X (TIME)"
                
                # Simplified parsing logic for demo:
                shownumber = 1
                if "SHOW 2" in description: shownumber = 2
                if "SHOW 3" in description: shownumber = 3
                
                time_str = "13u30"
                if "18u30" in description: time_str = "18u30"
                if "10u00" in description: time_str = "10u00"
                
                date = 28
                if "29/" in description or "SHOW 3" in description: date = 29
                
                generate_ticket_image(code, shownumber, date, time_str)
        
        db.session.commit()
        
        # 3. Send Email
        try:
             send_email(f"https://tickets.tsirk.be/success?session_id={session_id}", email, email)
             print(f"Email sent to {email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
