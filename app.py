import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

import stripe
from flask import Flask, jsonify, request, render_template



# Initialize the app with Bootstrap for grid system
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP], external_scripts = ['https://js.stripe.com/v3/'])
server = app.server
app.title = "Tickets Show 2026"


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


# ------------------------------------------------------------------------------
#  ____ _____ ____  ___ ____  _____ 
# / ___|_   _|  _ \|_ _|  _ \| ____|
# \___ \ | | | |_) || || |_) |  _|  
#  ___) || | |  _ < | ||  __/| |___ 
# |____/ |_| |_| \_\___|_|   |_____|
# ------------------------------------------------------------------------------


stripe_keys = {
    'secret_key': os.environ['STRIPE_SECRET_KEY'],
    'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY'],
}
stripe.api_key = stripe_keys['secret_key']

@server.route('/config')
def config():
    stripe_config = {'publicKey': stripe_keys['publishable_key']}
    return jsonify(stripe_config)




if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
