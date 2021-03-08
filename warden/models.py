from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

db = current_app.db


@current_app.login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    trades = db.relationship("Trades", backref="trade_inputby", lazy=True)
    account = db.relationship("AccountInfo",
                              backref="account_owner",
                              lazy=True)

    def get_reset_token(self, expires_sec=300):
        s = Serializer(current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": self.id}).decode("utf-8")

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token)["user_id"]
        except (KeyError, TypeError):
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return (self.username)


class Trades(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150),
                        db.ForeignKey("user.id"),
                        nullable=False)
    trade_inputon = db.Column(db.DateTime,
                              default=datetime.utcnow())
    trade_date = db.Column(db.DateTime,
                           nullable=False,
                           default=datetime.utcnow())
    trade_currency = db.Column(db.String(3), nullable=False, default="USD")
    trade_asset_ticker = db.Column(db.String(20), nullable=False)
    trade_account = db.Column(db.String(20), nullable=False)
    trade_quantity = db.Column(db.Float)
    trade_operation = db.Column(db.String(2), nullable=False)
    trade_price = db.Column(db.Float)
    trade_fees = db.Column(db.Float, default=0)
    trade_notes = db.Column(db.Text)
    trade_blockchain_id = db.Column(db.String(150))
    cash_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"Trades('{self.trade_date}', '{self.trade_asset_ticker}', \
                        '{self.trade_quantity}', '{self.trade_price}', \
                        '{self.trade_fees}')"

    def to_dict(self):
        return (vars(self))


class AccountInfo(db.Model):
    account_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    account_longname = db.Column(db.String(255))
    account_type = db.Column(db.String(255))
    notes = db.Column(db.Text)


class TickerInfo(db.Model):
    ticker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trade_asset_ticker = db.Column(db.String(20), nullable=False)
    provider = db.Column(db.String(), nullable=False)
    json_endpoint = db.Column(db.String(), nullable=False)
    json_price_field = db.Column(db.String(), nullable=False)
    json_date_field = db.Column(db.String(), nullable=False)


class SpecterInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    url = db.Column(db.String())
    login = db.Column(db.String())
    passowrd = db.Column(db.String())
