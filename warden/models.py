from datetime import datetime
from flask import current_app

db = current_app.db


class Trades(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150),
                        db.ForeignKey("user.id"),
                        nullable=False)
    trade_inputon = db.Column(db.DateTime,
                              nullable=False,
                              default=datetime.utcnow)
    trade_date = db.Column(db.DateTime,
                           nullable=False,
                           default=datetime.utcnow)
    trade_currency = db.Column(db.String(3), nullable=False, default="USD")
    trade_asset_ticker = db.Column(db.String(20), nullable=False)
    trade_account = db.Column(db.String(20), nullable=False)
    trade_quantity = db.Column(db.Float)
    trade_operation = db.Column(db.String(2), nullable=False)
    trade_price = db.Column(db.Float)
    trade_fees = db.Column(db.Float, default=0)
    trade_notes = db.Column(db.Text)
    trade_reference_id = db.Column(db.String(50))
    trade_blockchain_id = db.Column(db.String(150))
    cash_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"Trades('{self.trade_date}', '{self.trade_asset_ticker}', \
                        '{self.trade_quantity}', '{self.trade_price}', \
                        '{self.trade_fees}')"
