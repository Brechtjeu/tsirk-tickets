import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import os
import logging
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the app with Bootstrap for grid system
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP], external_scripts = ['https://js.stripe.com/v3/', 'https://unpkg.com/html5-qrcode'])
server = app.server
app.title = "Tickets Show 2026"

# Import DB and Stripe Integration
from db import init_db
from stripe_integration import register_stripe_routes


# Initialize Database and Stripe Routes
init_db(server)
register_stripe_routes(server)

app.layout = html.Div([
    dcc.Store(id="cart-store", storage_type="session", data={}),
    # Background Image Container
    html.Div(className="poster-bg"),
    
    # Overlay for readability
    html.Div(className="content-overlay", children=[
        # Navigation / Header area
        html.Div([
            html.H1("SHOW 'T SIRK VINDT UIT!", className="main-title text-center mb-0"),
            html.H3("EEN LEUKE VOORSTELLING", className="sub-title text-center text-gold"),
        ], className="header-section py-4"),

        # Page Container
        dash.page_container,
        
        # Footer
        html.Footer([
            html.P("WWW.TSIRK.BE", className="text-center text-muted small mt-5")
        ])
    ])
])

if __name__ == "__main__":
    logger.info(f"Starting app in {'DEBUG' if DEBUG_MODE else 'PRODUCTION'} mode")
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5000)
