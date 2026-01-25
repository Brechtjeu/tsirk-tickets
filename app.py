import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Initialize the app with Bootstrap for grid system
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])
server = app.server

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
    app.run(debug=True, host='0.0.0.0')
