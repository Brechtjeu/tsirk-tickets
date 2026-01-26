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
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP], external_scripts = ['https://js.stripe.com/v3/'])
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
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Home", href="/")),
            dbc.NavItem(dbc.NavLink("Winkelmandje", href="/cart")),
        ],
        brand="Tickets 't Sirk 2026",
        brand_href="/",
        color="primary",
        dark=True,
    ),
    dash.page_container
])

if __name__ == "__main__":
    logger.info(f"Starting app in {'DEBUG' if DEBUG_MODE else 'PRODUCTION'} mode")
    app.run(debug=DEBUG_MODE, host='0.0.0.0')
