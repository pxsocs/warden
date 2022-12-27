import json
from datetime import datetime, date, timedelta
from flask import current_app
from flask_login import UserMixin, current_user, login_required
from sqlalchemy import func
from backend.utils import pickle_it

db = current_app.db

# Loaders -------------


@current_app.login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    # Update the application status object
    current_app.warden_status['username'] = user.username
    return user


def load_Node(name=None, url=None):
    if name is None and url is None:
        query = Nodes.query.all()
        node_list = []
        for element in query:
            node_list.append(element)
        return node_list
    if name is not None:
        query = Nodes.query.filter_by(name=name).first()
        return query
    if url is not None:
        query = Nodes.query.filter_by(url=url).first()
        return query


# ---------------- End loaders ----------------


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


#  Node Models -------------


class Nodes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    # Make sure to parse url before including / editing
    url = db.Column(db.String(250), nullable=False, unique=True)
    is_reachable = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=None)
    last_check = db.Column(db.DateTime, default=date.min)
    is_localhost = db.Column(db.Boolean, default=None)
    node_tip_height = db.Column(db.Integer, default=0)
    mps_api_reachable = db.Column(db.Boolean, default=False)
    ping_time = db.Column(db.PickleType(), default=0)
    last_online = db.Column(db.DateTime, default=date.min)
    blockchain_tip_height = pickle_it('load', 'max_blockchain_tip_height.pkl')

    def is_onion(self):
        return (True if 'onion' in self.url else False)

    def is_at_tip(self):
        # Reload the blockchain tip height from file
        self.blockchain_tip_height = pickle_it(
            'load', 'max_blockchain_tip_height.pkl')
        is_at_tip = False if self.node_tip_height != self.blockchain_tip_height else True
        return is_at_tip

    def as_dict(self):
        dict_return = {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }
        # Add methods to return dict
        dict_return['is_onion'] = self.is_onion()
        dict_return['is_at_tip'] = self.is_at_tip()
        return (dict_return)

    def __repr__(self):
        return (json.dumps(self.as_dict(), default=str))

        # return f'{self.id}, {self.name}, {self.url}'
