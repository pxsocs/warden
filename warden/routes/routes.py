import logging
from flask.helpers import get_flashed_messages
from warden_decorators import MWT
from flask import (Blueprint, redirect, render_template, abort, flash, session,
                   request, current_app, url_for)
from flask_login import login_user, logout_user, current_user, login_required
from backend.warden_modules import (warden_metadata, positions, generatenav,
                                    specter_df, regenerate_nav, home_path,
                                    clean_float, transactions_fx)
from pricing_engine.engine import fx_rate, historical_prices, realtime_price

from forms import RegistrationForm, LoginForm, TradeForm

from werkzeug.security import check_password_hash, generate_password_hash
from models import User, AccountInfo, Trades
from backend.utils import update_config, heatmap_generator, pickle_it
from operator import itemgetter
from packaging import version
from connections import tor_request, url_parser
from specter_importer import Specter

from datetime import datetime
import jinja2
import numpy as np
import json
import os
import urllib
import requests
import pandas as pd

warden = Blueprint("warden",
                   __name__,
                   template_folder='templates',
                   static_folder='static')


@warden.before_request
def before_request():
    # Remove duplicate messages from Flask Flash
    messages = get_flashed_messages(with_categories=True)
    messages = list(set(messages))
    for category, message in messages:
        flash(message, category)

    # if no users found, send to setup
    try:
        users = User.query.all()
    except Exception:
        users = []
    if users == []:
        return redirect(url_for("user_routes.initial_setup"))

    # Ignore check for some pages - these are mostly methods that need
    # to run even in setup mode
    exclude_list = [
        "warden.setup", "warden.specter_auth", "warden.login",
        "warden.register", "warden.logout", "warden.show_broadcast",
        "warden.show_log", "warden.config_ini", "warden.newtrade"
    ]
    if request.endpoint in exclude_list:
        return

    if not current_user.is_authenticated:
        return redirect(url_for("warden.login"))

    # Create empty status dictionary
    meta = {
        'tor': current_app.tor,
        'specter_reached': current_app.specter.specter_reached,
        'specter_auth': current_app.specter.specter_auth
    }
    # Save this in Flask session
    session['status'] = json.dumps(meta)

    # Check if still downloading data, if so load files
    if current_app.downloading:
        # No need to test if still downloading txs
        flash(
            "Downloading from Specter. In the mean time, some transactions may be outdated or missing. Leave the app running to finish download.",
            "info")

    # Check that Specter is > 1.1.0 version
    # (this is the version where tx API was implemented)
    try:
        specter_version = str(current_app.specter.home_parser()['version'])
        if version.parse(specter_version) < version.parse(
                "1.1.0") and specter_version != "unknown":
            flash(
                f"Sorry, you need Specter version 1.1.0 or higher to connect to WARden. You are running version {specter_version}. Please upgrade.",
                "danger")
    # An error below means no file was ever created - probably needs setup
    except Exception:
        pass


@warden.after_request
def after_request_func(response):
    # Clear messages in flash
    session.pop('_flashes', None)
    return (response)


@warden.route("/register", methods=["GET", "POST"])
def register():

    # if a password is already set, go to login page
    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hash = generate_password_hash(form.password.data)
        user = User(username=form.username.data, password=hash)
        current_app.db.session.add(user)
        current_app.db.session.commit()
        flash(f"Account created for {form.username.data}.", "success")
        login_user(user, remember=True)
        return redirect(url_for("warden.warden_page"))

    return render_template("warden/register.html", title="Register", form=form)


@warden.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and check_password_hash(user.password,
                                                    form.password.data):
            login_user(user, remember=True)
            flash(f"Login Successful. Welcome {user}.", "success")
            next_page = request.args.get("next")  # get the original page
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("warden.warden_page"))
        else:
            flash("Login failed. Please check Username and Password", "danger")

    return render_template("warden/login.html", title="Login", form=form)


@warden.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("warden.warden_page"))


# Main page for WARden
@warden.route("/", methods=['GET'])
@warden.route("/warden", methods=['GET'])
@login_required
def warden_page():
    # For now pass only static positions, will update prices and other
    # data through javascript after loaded. This improves load time
    # and refresh speed.
    # Get positions and prepare df for delivery

    df = positions()
    try:
        df = positions()
    except Exception as e:
        flash(f"Error getting transactions: {e}", "danger")
        return redirect(url_for("warden.newtrade"))

    if not df.empty:
        if df.index.name != 'trade_asset_ticker':
            df.set_index('trade_asset_ticker', inplace=True)
        df = df[df['is_currency'] == 0].sort_index(ascending=True)
        df = df.to_dict(orient='index')
    else:
        form = TradeForm()
        form.trade_currency.data = current_app.fx['code']
        form.trade_date.data = datetime.utcnow()
        return (render_template('warden/empty_txs.html',
                                title='No Transactions Found',
                                form=form,
                                current_user=fx_rate(),
                                current_app=current_app))

    # Create a custody DF
    transactions = transactions_fx()
    custody_df = transactions.groupby(["trade_account", "trade_asset_ticker"
                                       ])[["trade_quantity"]].sum()

    # Open Counter, increment, send data
    try:
        counter = pickle_it('load', 'counter.pkl')
        if counter == 'file not found':
            raise
        counter += 1
        pickle_it('save', 'counter.pkl', counter)
        if counter == 25:
            flash(
                "Looks like you've been using the app frequently. " +
                "Consider donating to support it.", "info")
        if counter == 50:
            flash(
                "Open Source software is transparent and free. " +
                "Support it. Make a donation.", "info")
        if counter % 100:
            flash(
                "Looks like you are a frequent user of the WARden. " +
                "Consider a donation.", "info")

    except Exception:
        # File wasn't found. Create start at zero
        flash(
            "Welcome. Consider making a donation " +
            "to support this software.", "info")
        counter = 0
        pickle_it('save', 'counter.pkl', counter)

    meta = warden_metadata()

    # Sort the wallets by balance
    sorted_wallet_list = []
    try:
        for wallet in current_app.specter.wallet_alias_list():
            wallet_df = meta['full_df'].loc[meta['full_df']['wallet_alias'] ==
                                            wallet]
            if wallet_df.empty:
                balance = 0
            else:
                balance = wallet_df['amount'].sum()
            sorted_wallet_list.append((wallet, balance))

        sorted_wallet_list = sorted(sorted_wallet_list,
                                    reverse=True,
                                    key=itemgetter(1))
        sorted_wallet_list = [i[0] for i in sorted_wallet_list]
        wallets_exist = True
    except Exception as e:

        logging.error(e)
        wallets_exist = False

    from api.routes import alert_activity
    if not current_app.downloading:
        activity = alert_activity()
    else:
        activity = False

    templateData = {
        "title": "Portfolio Dashboard",
        "warden_metadata": meta,
        "portfolio_data": df,
        "FX": current_app.settings['PORTFOLIO']['base_fx'],
        "alerts": activity,
        "current_app": current_app,
        "sorted_wallet_list": sorted_wallet_list,
        "wallets_exist": wallets_exist,
        "custody_df": custody_df
    }
    return (render_template('warden/warden.html', **templateData))


@warden.route("/list_transactions", methods=['GET'])
@login_required
def list_transactions():
    transactions = specter_df()
    return render_template("warden/transactions.html",
                           title="Specter Transaction History",
                           transactions=transactions,
                           current_app=current_app)


@warden.route("/satoshi_quotes", methods=['GET'])
@login_required
def satoshi_quotes():
    return render_template("warden/satoshi_quotes.html",
                           title="Satoshi Wisdom",
                           current_app=current_app)


# Update user fx settings in config.ini
@warden.route('/update_fx', methods=['GET', 'POST'])
@login_required
def update_fx():
    fx = request.args.get("code")
    current_app.settings['PORTFOLIO']['base_fx'] = fx
    update_config()
    from backend.utils import fxsymbol as fxs
    current_app.fx = fxs(fx, 'all')
    regenerate_nav()
    redir = request.args.get("redirect")
    return redirect(redir)


@warden.route('/specter_auth', methods=['GET', 'POST'])
@login_required
def specter_auth():
    if request.method == 'GET':

        templateData = {
            "title": "Login to Specter",
            "current_app": current_app,
            "current_user": current_user
        }
        return (render_template('warden/specter_auth.html', **templateData))

    if request.method == 'POST':
        from message_handler import Message
        current_app.message_handler.clean_category('Specter Connection')
        url = request.form.get('url')
        url = url_parser(url)

        # Try to ping this url
        if 'onion' not in url:
            try:
                status_code = requests.head(url).status_code
            except Exception as e:
                flash(f'Please check Specter URL. Error: {e}', 'danger')
        else:
            try:
                status_code = tor_request(url).status_code
            except Exception as e:
                flash(f'Please check Specter URL. Error: {e}', 'danger')

        try:
            if int(status_code) < 400:
                message = Message(
                    category='Specter Connection',
                    message_txt='Pinging URL',
                    notes=
                    f"{url}<br> ping <span class='text-success'>✅ Success</span>"
                )
                current_app.message_handler.add_message(message)
            else:
                flash('Please check Specter URL (unreacheable)', 'danger')
                return redirect(url_for('warden.specter_auth'))
        except Exception as e:
            flash(f'Error Connecting. Error: {e}', 'danger')
            return redirect(url_for('warden.specter_auth'))

        # Try to authenticate
        try:
            current_app.specter.base_url = url
            current_app.specter.login_url = url + 'auth/login'
            current_app.specter.tx_url = url + 'wallets/wallets_overview/txlist'
            current_app.specter.core_url = url + 'settings/bitcoin_core?'
            current_app.specter.login_payload = {
                'username': request.form.get('username'),
                'password': request.form.get('password')
            }
            session = current_app.specter.init_session()
            session.close()
        except Exception as e:
            flash(f'Error logging in to Specter: {e}', 'danger')
            return redirect(url_for('warden.specter_auth'))

        current_app.downloading = True
        current_app.settings['SPECTER']['specter_url'] = url
        current_app.settings['SPECTER']['specter_login'] = request.form.get(
            'username')
        current_app.settings['SPECTER']['specter_password'] = request.form.get(
            'password')
        update_config()

        current_app.specter = Specter()
        current_app.specter.refresh_txs(load=False)

        flash("Success. Connected to Specter Server.", "success")
        # Now allow download of all txs in background on next run
        return redirect(url_for('warden.warden_page'))


# Donation Thank you Page
@warden.route("/donate", methods=['GET'])
@login_required
def donate():
    counter_file = os.path.join(home_path(), 'warden/counter.json')
    templateData = {
        "title": "Support this Software",
        "current_app": current_app
    }
    return (render_template('warden/warden_thanks.html', **templateData))


# Page with a single historical chart of NAV
# Include portfolio value as well as CF_sumcum()
@warden.route("/navchart")
@login_required
def navchart():
    data = generatenav()
    navchart = data[["NAV_fx"]].copy()
    # dates need to be in Epoch time for Highcharts
    navchart.index = (navchart.index - datetime(1970, 1, 1)).total_seconds()
    navchart.index = navchart.index * 1000
    navchart.index = navchart.index.astype(np.int64)
    navchart = navchart.to_dict()
    navchart = navchart["NAV_fx"]

    port_value_chart = data[[
        "PORT_cash_value_fx", "PORT_fx_pos", "PORT_ac_CFs_fx"
    ]].copy()
    port_value_chart["ac_pnl_fx"] = (port_value_chart["PORT_fx_pos"] -
                                     port_value_chart["PORT_ac_CFs_fx"])
    # dates need to be in Epoch time for Highcharts
    port_value_chart.index = (port_value_chart.index -
                              datetime(1970, 1, 1)).total_seconds()
    port_value_chart.index = port_value_chart.index * 1000
    port_value_chart.index = port_value_chart.index.astype(np.int64)
    port_value_chart = port_value_chart.to_dict()

    return render_template("warden/warden_navchart.html",
                           title="NAV Historical Chart",
                           navchart=navchart,
                           port_value_chart=port_value_chart,
                           fx=current_app.settings['PORTFOLIO']['base_fx'],
                           current_user=fx_rate(),
                           data=data,
                           current_app=current_app)


@warden.route("/heatmap")
@login_required
# Returns a monthly heatmap of returns and statistics
def heatmap():
    heatmap_gen, heatmap_stats, years, cols = heatmap_generator()

    return render_template("warden/heatmap.html",
                           title="Monthly Returns HeatMap",
                           heatmap=heatmap_gen,
                           heatmap_stats=heatmap_stats,
                           years=years,
                           cols=cols,
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/volchart", methods=["GET", "POST"])
@login_required
# Only returns the html - request for data is done through jQuery AJAX
def volchart():
    return render_template("warden/volchart.html",
                           title="Historical Volatility Chart",
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/portfolio_compare", methods=["GET"])
@login_required
def portfolio_compare():
    return render_template("warden/portfolio_compare.html",
                           title="Portfolio Comparison",
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/price_and_position", methods=["GET"])
@login_required
def price_and_position():
    # Gets price and position data for a specific ticker
    ticker = request.args.get("ticker")
    fx = request.args.get("fx")
    if fx is None:
        fx = fx_rate()['base']

    # Gets Price and market data first
    realtime_data = realtime_price(ticker=ticker, fx=fx)
    historical_data = historical_prices(ticker=ticker, fx=fx)
    historical_data.index = historical_data.index.astype('datetime64[ns]')

    filemeta = (ticker + "_" + fx + ".meta")
    historical_meta = pickle_it(action='load', filename=filemeta)

    price_chart = historical_data[["close_converted", "close"]].copy()
    # dates need to be in Epoch time for Highcharts
    price_chart.index = price_chart.index.astype('datetime64[ns]')
    price_chart.index = (price_chart.index -
                         datetime(1970, 1, 1)).total_seconds()
    price_chart.index = price_chart.index * 1000
    price_chart.index = price_chart.index.astype(np.int64)
    price_chart = price_chart.to_dict()
    price_chart_usd = price_chart["close"]
    price_chart = price_chart["close_converted"]

    # Now gets position data
    df = positions()
    if isinstance(df, pd.DataFrame):
        if not df.empty:
            df = df[df['trade_asset_ticker'] == ticker]

    df_trades = transactions_fx()
    position_chart = None
    if isinstance(df_trades, pd.DataFrame):
        df_trades = df_trades[df_trades['trade_asset_ticker'] == ticker]
        if not df_trades.empty:
            df_trades = df_trades.sort_index(ascending=True)
            df_trades['trade_quantity_cum'] = df_trades[
                'trade_quantity'].cumsum()
            position_chart = df_trades[["trade_quantity_cum"]].copy()
            # dates need to be in Epoch time for Highcharts
            position_chart.index = position_chart.index.astype(
                'datetime64[ns]')
            position_chart.index = (position_chart.index -
                                    datetime(1970, 1, 1)).total_seconds()
            position_chart.index = position_chart.index * 1000
            position_chart.index = position_chart.index.astype(np.int64)
            position_chart = position_chart.to_dict()
            position_chart = position_chart["trade_quantity_cum"]

    if ticker == 'GBTC':
        from pricing_engine.engine import GBTC_premium
        from parseNumbers import parseNumber
        GBTC_price = parseNumber(realtime_data['price'])
        GBTC_fairvalue, GBTC_premium = GBTC_premium(GBTC_price)
    else:
        GBTC_premium = GBTC_fairvalue = None

    return render_template("warden/price_and_position.html",
                           title="Ticker Price and Positions",
                           current_app=current_app,
                           current_user=fx_rate(),
                           realtime_data=realtime_data,
                           historical_data=historical_data,
                           historical_meta=historical_meta,
                           positions=df,
                           ticker=ticker,
                           fx=fx,
                           price_chart=price_chart,
                           price_chart_usd=price_chart_usd,
                           position_chart=position_chart,
                           GBTC_premium=GBTC_premium,
                           GBTC_fairvalue=GBTC_fairvalue)


# Allocation History


@warden.route("/allocation_history", methods=["GET"])
@login_required
def allocation_history():
    return render_template("warden/allocation_history.html",
                           title="Portfolio Historical Allocation",
                           current_app=current_app,
                           current_user=fx_rate())


# Show debug info
@warden.route('/show_log')
@login_required
def show_log():
    return render_template('warden/show_log.html',
                           title="Debug Viewer",
                           current_app=current_app,
                           current_user=fx_rate())


# Show debug info
@warden.route('/show_broadcast')
@login_required
def show_broadcast():
    category = request.args.get("category")
    return render_template(
        'warden/show_broadcast.html',
        title="Message Broadcaster",
        current_app=current_app,
        current_user=fx_rate(),
        category=category,
    )


# Show debug info
@warden.route('/config_ini', methods=['GET', 'POST'])
@login_required
def config_ini():
    from config import Config
    config_file = Config.config_file
    if not os.path.isfile(config_file):
        flash('Config File not Found. Restart the app.', 'danger')
        config_contents = None
    else:
        f = open(config_file, 'r')
        config_contents = f.read()

    if request.method == 'POST':
        config_txt = request.form.get('config_txt')
        f = open(config_file, "w")
        f.write(config_txt)
        f.close()
        flash("Config File Saved", "success")
        config_contents = config_txt

    return render_template('warden/config_ini.html',
                           title="Custom Configurations",
                           current_app=current_app,
                           current_user=fx_rate(),
                           config_file=config_file,
                           config_contents=config_contents)


#   TRADES -----------------------------------------------


@warden.route("/newtrade", methods=["GET", "POST"])
@login_required
def newtrade():
    form = TradeForm()
    acclist = AccountInfo.query.filter_by(user_id=current_user.username)
    accounts = []
    for item in acclist:
        accounts.append((item.account_longname, item.account_longname))
    form.trade_account.choices = accounts

    if request.method == "POST":

        if form.validate_on_submit():
            # Need to include two sides of trade:
            if form.trade_operation.data in ("B"):
                qop = 1
            elif form.trade_operation.data in ("S"):
                qop = -1
            else:
                qop = 0
                flash(
                    "Trade Operation Error. Should be B for buy or S for sell.",
                    "warning")

            # Calculate Trade's cash value
            cvfail = False

            try:
                p = float(clean_float(form.trade_price.data))
                q = float(clean_float(form.trade_quantity.data))
                f = float(clean_float(form.trade_fees.data))
                cv = qop * (q * p) + f

            except ValueError:
                flash(
                    "Error on calculating fiat amount \
                for transaction - TRADE NOT included",
                    "danger",
                )
                cvfail = True
                cv = 0

            # Check what type of trade this is
            # Cash and/or Asset

            try:
                tquantity = float(form.trade_quantity.data) * qop
            except ValueError:
                tquantity = 0

            try:
                tprice = float(form.trade_price.data)
            except ValueError:
                tprice = 0

            trade = Trades(
                user_id=current_user.username,
                trade_date=form.trade_date.data,
                trade_account=form.trade_account.data,
                trade_currency=form.trade_currency.data,
                trade_asset_ticker=form.trade_asset_ticker.data,
                trade_quantity=tquantity,
                trade_operation=form.trade_operation.data,
                trade_price=tprice,
                trade_fees=form.trade_fees.data,
                trade_notes=form.trade_notes.data,
                cash_value=cv,
            )
            if not cvfail:
                current_app.db.session.add(trade)
                current_app.db.session.commit()
                regenerate_nav()
                flash("Trade included", "success")

            return redirect(url_for("warden.warden_page"))
        else:
            flash("Trade Input failed. Something went wrong. Try Again.",
                  "danger")

    form.trade_currency.data = current_app.fx['code']
    form.trade_date.data = datetime.utcnow()
    return render_template("warden/newtrade.html",
                           form=form,
                           title="New Trade",
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/trade_transactions")
@login_required
# List of all transactions
def trade_transactions():
    transactions = Trades.query.filter_by(user_id=current_user.username)

    if transactions.count() == 0:
        form = TradeForm()
        form.trade_currency.data = current_app.fx['code']
        form.trade_date.data = datetime.utcnow()
        return render_template("warden/empty_txs.html",
                               title="Empty Transaction List",
                               current_app=current_app,
                               current_user=fx_rate(),
                               form=form)

    return render_template("warden/trade_transactions.html",
                           title="Transaction History",
                           transactions=transactions,
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/edittransaction", methods=["GET", "POST"])
@login_required
# Edit transaction takes arguments {id} or {reference_id}
def edittransaction():
    form = TradeForm()
    reference_id = request.args.get("reference_id")
    id = request.args.get("id")
    if reference_id:
        trade = Trades.query.filter_by(
            user_id=current_user.username).filter_by(
                trade_reference_id=reference_id).first()
        if trade.count() == 0:
            abort(404, "Transaction not found")
        id = trade.id

    trade = Trades.query.filter_by(user_id=current_user.username).filter_by(
        id=id).first()

    if trade is None:
        abort(404)

    if trade.user_id != current_user.username:
        abort(403)

    acclist = AccountInfo.query.filter_by(user_id=current_user.username)
    accounts = []
    for item in acclist:
        accounts.append((item.account_longname, item.account_longname))
    form.trade_account.choices = accounts
    form.submit.label.text = 'Edit Trade'

    if request.method == "POST":

        if form.validate_on_submit():
            # Write changes to database
            if form.trade_operation.data in ("B", "D"):
                qop = 1
            elif form.trade_operation.data in ("S", "W"):
                qop = -1
            else:
                qop = 0

            # Calculate Trade's cash value
            cvfail = False

            try:
                p = float(clean_float(form.trade_price.data))
                q = float(clean_float(form.trade_quantity.data))
                f = float(clean_float(form.trade_fees.data))
                cv = qop * (q * p) + f

            except ValueError:
                flash(
                    "Error on calculating cash amount \
                for transaction - TRADE NOT edited. Try Again.",
                    "danger",
                )
                cvfail = True
                cv = 0

            trade.trade_date = form.trade_date.data
            trade.trade_asset_ticker = form.trade_asset_ticker.data
            trade.trade_currency = form.trade_currency.data
            trade.trade_operation = form.trade_operation.data
            trade.trade_quantity = float(form.trade_quantity.data) * qop
            trade.trade_price = float(clean_float(form.trade_price.data))
            trade.trade_fees = float(clean_float(form.trade_fees.data))
            trade.trade_account = form.trade_account.data
            trade.trade_notes = form.trade_notes.data
            trade.cash_value = cv

            if not cvfail:
                current_app.db.session.commit()
                regenerate_nav()
                flash("Trade edit successful", "success")

            return redirect(url_for("warden.warden_page"))

        flash("Trade edit failed. Something went wrong. Try Again.", "danger")

    # Pre-populate the form
    form.trade_date.data = trade.trade_date
    form.trade_currency.data = trade.trade_currency
    form.trade_asset_ticker.data = trade.trade_asset_ticker
    form.trade_operation.data = trade.trade_operation
    form.trade_quantity.data = abs(float(trade.trade_quantity))
    form.trade_price.data = trade.trade_price
    form.trade_fees.data = trade.trade_fees
    form.trade_account.data = trade.trade_account
    form.trade_notes.data = trade.trade_notes

    return render_template("warden/edittransaction.html",
                           title="Edit Transaction",
                           form=form,
                           trade=trade,
                           id=id,
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/deltrade", methods=["GET"])
@login_required
# Deletes a trade - takes one argument: {id}
def deltrade():
    if request.method == "GET":
        id = request.args.get("id")
        trade = Trades.query.filter_by(id=id).first()

        if trade is None:
            flash(f"Trade id: {id} not found. Nothing done.", "warning")
            return redirect(url_for("warden.warden_page"))

        if trade.user_id != current_user.username:
            abort(403)

        Trades.query.filter_by(id=trade.id).delete()
        current_app.db.session.commit()
        regenerate_nav()
        flash("Trade deleted", "danger")
        return redirect(url_for("warden.warden_page"))

    else:
        return redirect(url_for("warden.warden_page"))


@warden.route("/delalltrades", methods=["GET"])
@login_required
# This deletes all trades from database - use with caution. Should not
# be called directly as it will delete all trades without confirmation!
def delalltrades():

    transactions = Trades.query.filter_by(
        user_id=current_user.username).order_by(Trades.trade_date)

    if transactions.count() == 0:
        form = TradeForm()
        form.trade_currency.data = current_app.fx['code']
        form.trade_date.data = datetime.utcnow()
        return render_template("warden/empty_txs.html",
                               title="Empty Transaction List",
                               current_app=current_app,
                               current_user=fx_rate(),
                               form=form)

    if request.method == "GET":
        Trades.query.filter_by(user_id=current_user.username).delete()
        current_app.db.session.commit()
        regenerate_nav()
        flash("ALL TRANSACTIONS WERE DELETED", "danger")
        return redirect(url_for("warden.warden_page"))

    else:
        return redirect(url_for("warden.warden_page"))


# Shows Current Running Services


@warden.route("/running_services", methods=["GET"])
def running_services():
    return render_template("warden/running_services.html",
                           title="Running Services and Status",
                           current_app=current_app,
                           current_user=fx_rate())


@warden.route("/drawdown", methods=["GET"])
@login_required
def drawdown():
    return render_template("warden/drawdown.html",
                           title="Drawdown Analysis",
                           current_app=current_app,
                           current_user=fx_rate())


# -------------------------------------------------
#  START JINJA 2 Filters
# -------------------------------------------------
# Jinja2 filter to format time to a nice string
# Formating function, takes self +
# number of decimal places + a divisor


@jinja2.contextfilter
@warden.app_template_filter()
def jformat(context, n, places, divisor=1):
    if n is None:
        return "-"
    else:
        try:
            n = float(n)
            n = n / divisor
            if n == 0:
                return "-"
        except ValueError:
            return "-"
        except TypeError:
            return (n)
        except Exception:
            return "#error"
        try:
            form_string = "{0:,.{prec}f}".format(n, prec=places)
            return form_string
        except (ValueError, KeyError):
            return "-"


# Jinja filter - epoch to time string
@jinja2.contextfilter
@warden.app_template_filter()
def epoch(context, epoch):
    time_r = datetime.fromtimestamp(epoch).strftime("%m-%d-%Y (%H:%M)")
    return time_r


# Jinja filter - fx details
@jinja2.contextfilter
@warden.app_template_filter()
def fxsymbol(context, fx, output='symbol'):
    # Gets an FX 3 letter symbol and returns the HTML symbol
    # Sample outputs are:
    # "EUR": {
    # "symbol": "",
    # "name": "Euro",
    # "symbol_native": "",
    # "decimal_digits": 2,
    # "rounding": 0,
    # "code": "EUR",
    # "name_plural": "euros"
    try:
        from thewarden.users.utils import current_path
        filename = os.path.join(current_path(),
                                'static/json_files/currency.json')
        with open(filename) as fx_json:
            fx_list = json.load(fx_json, encoding='utf-8')
        out = fx_list[fx][output]
    except Exception:
        out = fx
    return (out)


@jinja2.contextfilter
@warden.app_template_filter()
def jencode(context, url):
    return urllib.parse.quote_plus(url)


# Jinja filter - time to time_ago
@jinja2.contextfilter
@warden.app_template_filter()
def time_ago(context, time=False):
    if type(time) is str:
        try:
            time = int(time)
        except TypeError:
            return ""
        except ValueError:
            # Try different parser
            time = datetime.strptime(time, '%m-%d-%Y (%H:%M)')
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        return ("")
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 10:
            return "Just Now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(int(day_diff)) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"


# END WARDEN ROUTES ----------------------------------------
