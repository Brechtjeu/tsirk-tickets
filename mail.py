from __future__ import print_function
import time
import brevo_python
from brevo_python.rest import ApiException
from pprint import pprint
from dotenv import load_dotenv
import os

import logging

logger = logging.getLogger(__name__)

# Configure API key authorization: api-key
configuration = brevo_python.Configuration()

key = os.getenv('BREVO_API_KEY')
if key == None:
    logger.warning("BREVO_API_KEY not found in environment variables")
    load_dotenv()
    key = os.getenv('BREVO_API_KEY')
    logger.debug(f"Loaded key: {key[:5]}...") # Log partial key for debug
configuration.api_key['api-key'] = key

def send_email(download_link, to_email, to_name):
    # create an instance of the API class
    api_instance = brevo_python.TransactionalEmailsApi(brevo_python.ApiClient(configuration))
    subject = "Welkom bij de nieuwste uitvinding van 't Sirk!"
    sender = {"name":"'t Sirk'","email":"show@tsirk.be"}
    reply_to = {"name":"'t Sirk'","email":"show@tsirk.be"}
    # HTML bericht
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Roboto', sans-serif;
                text-align: center;
                margin: 0;
                padding: 0;
                background-color: #05152a; /* Primary Blue */
                color: #ffffff;
            }}
            .container {{
                max-width: 600px;
                margin: 50px auto;
                background: rgba(5, 21, 42, 1);
                border: 1px solid #d4af37; /* Gold Border */
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 0 20px rgba(5, 21, 42, 0.8);
            }}
            h1 {{
                color: #d4af37; /* Gold */
                text-transform: uppercase;
                letter-spacing: 0.1em;
                font-weight: 900;
                margin-bottom: 10px;
            }}
            h2 {{
                color: #d4af37; /* Gold */
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 700;
                border-bottom: 1px solid #d4af37;
                display: inline-block;
                padding-bottom: 5px;
                margin-top: 30px;
            }}
            h3 {{
                color: #d4af37; /* Gold */
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 700;
                border-bottom: 1px solid #d4af37;
                display: inline-block;
                padding-bottom: 5px;
                margin-top: 30px;
            }}
            p {{
                font-size: 1.1em;
                color: #e0e0e0;
                line-height: 1.6;
            }}
            a {{
                color: #d4af37;
                text-decoration: none;
                font-weight: bold;
            }}
            a:hover {{
                text-decoration: underline;
                color: #f0c445;
            }}
            .table-container {{
                display: flex;
                justify-content: center;
                align-items: center;
                margin-top: 20px;
            }}
            .custom-table {{
                width: 100%;
                border-collapse: collapse;
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #d4af37;
            }}
            .custom-table th, .custom-table td {{
                border: 1px solid #444;
                padding: 12px;
                text-align: left;
                font-size: 0.95rem;
                vertical-align: top;
            }}
            .custom-table th {{
                background-color: rgba(212, 175, 55, 0.2);
                color: #d4af37;
                text-transform: uppercase;
                border-bottom: 2px solid #d4af37;
                text-align: center;
            }}
            .custom-table td {{
                color: #fff;
                border-color: #333;
            }}
            .custom-table tr:nth-child(even) {{
                background-color: rgba(255, 255, 255, 0.02);
            }}
            .highlight {{
                color: #d4af37;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                font-size: 0.9em;
                color: #888;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Bedankt voor je aankoop!</h1>
            <p>Hallo,</p>
            <p>Fijn dat je naar onze show komt kijken! Klik <a href="{download_link}" target="_blank">hier</a> om je tickets te downloaden. Je hoeft ze niet af te drukken, laat ze gewoon op je smartphone scannen aan de inkom.</p>
            <p>Let goed op! Dit jaar lopen onze shows verspreid over 2 dagen. Op je ticket(s) vind je terug welke show(s) je gaat kijken.</p>
            
            <h2>Showindeling</h2>
            <p class="highlight">Opgelet: Artiesten worden 30min voor aanvang van hun show bij hun lesgever verwacht</p>
            
            <h3>Show 1 op ZA 28 maart<br>13u30 - 16u00</h3>
            <div class="table-container">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th width="100%">Groepen</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Opening<br>
                                Luchtacro beginners Retie<br>
                                Kleuters<br>
                                Eenwieler training<br>
                                Gastoptreden</td>
                        </tr>
                        <tr>
                            <td>PAUZE</td>
                        </tr>
                        <tr>
                            <td>Multi 1<br>
                                Acro 1<br>
                                Evenwicht<br>
                                Luchtacro experts Mol</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3>Show 2 op ZA 28 maart<br>18u30 - 21u00</h3>
            <div class="table-container">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th width="100%">Groepen</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                Opening<br>
                                Luchtacro gevorderden Mol<br>
                                Multi Retie<br>
                                Eenwieler basket<br>
                                Gastoptreden
                            </td>
                        </tr>
                        <tr>
                            <td>PAUZE</td>
                        </tr>
                        <tr>
                            <td>
                                Multi 3<br>
                                Acro 2<br>
                                Jongleren<br>
                                Luchtacro experts Retie
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3>Show 3 op ZO 29 maart<br>10u00 - 12u30</h3>
            <div class="table-container">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th width="100%">Groepen</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                Opening<br>
                                Luchtacro beginners Mol<br>
                                Kleuter-ouder<br>
                                Multi+<br>
                                Gastoptreden: Amuze
                            </td>
                        </tr>
                        <tr>
                            <td>PAUZE</td>
                        </tr>
                        <tr> 
                            <td>
                                Luchtacro volwassenen<br>
                                Multi 1<br>
                                Eenwieler beginners<br>
                                Luchtacro gevorderden Retie
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <p>Tot snel!</p>
            <div class="footer">
                <p>PS: Wil je komen helpen op de show maar weet je niet goed hoe? Stuur een mailtje naar <a href="mailto:info@tsirk.be">info@tsirk.be</a>.</p>
            </div>
        </div>
    </body>
    </html>
    '''

    to = [{"email": to_email, "name": to_name}]
    send_smtp_email = brevo_python.SendSmtpEmail(to=to, reply_to=reply_to,
                                                 html_content=html_content, sender=sender, subject=subject) # SendSmtpEmail | Values to send a transactional email

    try:
        # Send a transactional email
        logger.info(f"Sending email to {to_email}")
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully. MessageId: {api_response.message_id}")
        # pprint(api_response)
    except ApiException as e:
        logger.error(f"Exception when calling TransactionalEmailsApi->send_transac_email: {e}")

if __name__ == "__main__":
    send_email(
        download_link="https://example.com/download-tickets",
        to_email="vanroybrecht@gmail.com",
        to_name="Brecht Van Roy"
    )

def send_admin_notification(session_id, customer_email, uitpas_items):
    api_instance = brevo_python.TransactionalEmailsApi(brevo_python.ApiClient(configuration))
    subject = f"ACTION REQUIRED: UitPas Tickets Verification ({session_id[:8]})"
    sender = {"name":"'t Sirk Sales","email":"noreply@tsirk.be"}
    to = [{"email":"show@tsirk.be", "name":"Ticket Admin"}]
    
    items_html = ""
    for item in uitpas_items:
        items_html += f"<li><strong>{item['number']}</strong>: {item['desc']} (Code: {item['code']})</li>"

    html_content = f'''
    <html>
    <body>
        <h2>Nieuwe UitPas Bestelling die verificatie vereist</h2>
        <p><strong>Klant Email:</strong> {customer_email}</p>
        <p><strong>Sessie ID:</strong> {session_id}</p>
        <h3>UitPas Nummers te controleren:</h3>
        <ul>
            {items_html}
        </ul>
        <p>Controleer deze nummers in de UitPas database. Indien geldig, activeer de tickets via het dashboard.</p>
    </body>
    </html>
    '''

    send_smtp_email = brevo_python.SendSmtpEmail(to=to, html_content=html_content, sender=sender, subject=subject)

    try:
        logger.info(f"Sending admin notification for session {session_id}")
        api_instance.send_transac_email(send_smtp_email)
    except ApiException as e:
        logger.error(f"Exception when calling send_admin_notification: {e}")
