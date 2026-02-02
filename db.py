from flask_sqlalchemy import SQLAlchemy
import random
import string
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

db = SQLAlchemy()

# Define the CheckoutSession model
class CheckoutSession(db.Model):
    __tablename__ = 'checkout_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, unique=True, nullable=False)
    status = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    payment_status = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    amount_total = db.Column(db.Integer, nullable=True) # In cents
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    access_codes = db.relationship('AccessCode', backref='checkout_session', lazy=True)

def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase, k=6))

# Define the AccessCode model
class AccessCode(db.Model):
    __tablename__ = 'access_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False, default=generate_unique_code)
    is_valid = db.Column(db.Boolean, default=True)
    type = db.Column(db.String, nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('checkout_sessions.id'), nullable=False)
    uitpas_number = db.Column(db.String, nullable=True)

def init_db(app):
    """
    Initialize the database with the given Flask app.
    """
    logger.info("Initializing Database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tsirk_tickets.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()