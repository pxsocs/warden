import json
from datetime import datetime
from flask import current_app
from flask_login import UserMixin

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

    def __repr__(self):
        return (self.username)


class Trades(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150),
                        db.ForeignKey("user.id"),
                        nullable=False)
    trade_inputon = db.Column(db.DateTime, default=datetime.utcnow())
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

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))


class AccountInfo(db.Model):
    account_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    account_longname = db.Column(db.String(255))
    account_type = db.Column(db.String(255))
    notes = db.Column(db.Text)

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))


class TickerInfo(db.Model):
    ticker_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trade_asset_ticker = db.Column(db.String(20), nullable=False)
    provider = db.Column(db.String(), nullable=False)
    json_endpoint = db.Column(db.String(), nullable=False)
    json_price_field = db.Column(db.String(), nullable=False)
    json_date_field = db.Column(db.String(), nullable=False)

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))


class SpecterInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    url = db.Column(db.String(), nullable=False)
    login = db.Column(db.String(), nullable=True)
    password = db.Column(db.String(), nullable=True)

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))


class Allocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    allocation_inputon = db.Column(db.String(), default=str(datetime.utcnow()))
    allocation = db.Column(db.String(), nullable=False)
    visibility = db.Column(db.String(), default='private')
    rebalance = db.Column(db.String(), default='never')
    portfolio_name = db.Column(db.String(250))
    loaded_times = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    other_data = db.Column(db.PickleType())

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))


class RequestData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    portfolio = db.Column(db.String())
    tickers = db.Column(db.String())
    allocations = db.Column(db.String())
    rebalance = db.Column(db.String())
    start_date = db.Column(db.String())
    end_date = db.Column(db.String())
    data = db.Column(db.String())
    request_time = db.Column(db.String(), default=str(datetime.utcnow()))

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))