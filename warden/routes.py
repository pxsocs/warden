from warden_decorators import MWT
from flask import (Blueprint, redirect, render_template, abort,
                   flash, session, request, current_app, url_for, get_flashed_messages)
from flask_login import login_user, logout_user, current_user, login_required, UserMixin
from warden_modules import (warden_metadata, positions,
                            generatenav, specter_df,
                            regenerate_nav,
                            home_path)

from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, StringField,
                     SubmitField)
from wtforms.validators import DataRequired, Email, Length, EqualTo
from werkzeug.security import check_password_hash, generate_password_hash
from warden_pricing_engine import (fx_rate, PROVIDER_LIST,
                                   PriceData)
from utils import update_config, heatmap_generator, pickle_it
from operator import itemgetter
from packaging import version

from datetime import datetime
import jinja2
import numpy as np
import json
import os
import urllib
import logging

warden = Blueprint("warden",
                   __name__,
                   template_folder='templates',
                   static_folder='static')


# Check Specter health every 60 seconds
# A randomizer number below will make sure the cache is not used
@MWT(timeout=60)
def specter_test(force=False, randomizer=None):
    return_dict = {}
    messages = None
    # Load basic specter data
    try:
        specter = current_app.specter.init_session()
        if type(specter) == str:
            if 'Specter Error' in specter:
                return_dict['specter_status'] = 'Error'
                messages = specter
                return (return_dict, messages)

    except Exception as e:
        return_dict['specter_status'] = 'Error'
        messages = str(e)

    return (return_dict, messages)

# START WARDEN ROUTES ----------------------------------------
# Things to check before each request:
# 1. Is Tor running? It's a requirement.
# 2. Is Specter server running? Also a requirement.
# 2.5 If running, is there a balance?
# 3. Found MyNode? Not a requirement but enables added functions.
# 4. Found Bitcoin Node? Not a requirement but enables added functions.


@current_app.login_manager.user_loader
def load_user(user_id):
    return User


class User(UserMixin):
    def __init__(self):
        if current_app.settings.has_option('SETUP', 'hash'):
            self.password = current_app.settings['SETUP']['hash']
        else:
            self.password = None
        self.username = 'specter_warden'
        self.id = 1


@warden.before_request
def before_request():
    # Ignore check for some pages - these are mostly methods that need
    # to run even in setup mode
    exclude_list = [
        "warden.setup", "warden.testtor", "warden.gitreleases",
        "warden.realtime_btc", "warden.data_folder", "warden.testtor",
        "warden.checkservices", "warden.check_activity", "warden.warden_page_metadata",
        "warden.specter_json", "warden.specter_auth", "warden.login", "warden.register",
        "warden.logout"
    ]
    if request.endpoint in exclude_list:
        return

    # Check Tor
    tor = current_app.tor

    # Create empty status dictionary
    meta = {
        'tor': tor,
        'specter_reached': True,
        'specter_auth': True
    }
    # Save this in Flask session
    session['status'] = json.dumps(meta)

    if current_app.downloading:
        # No need to test if still downloading txs
        flash("Downloading transactions from Specter. Some transactions may be missing. This can take several minutes at first run.", "info")
    else:
        # Test Specter
        try:
            specter_dict, specter_messages = specter_test(force=False)
        except Exception as e:
            specter_messages = str(e)

    if current_app.specter.wallet_alias_list() is None:
        meta['specter_reached'] = False
        session['status'] = json.dumps(meta)
        specter_messages = 'Having trouble finding Specter transactions. Check Specter Server'
        # If local data is present, continue
        data = pickle_it(action='load', filename='specter_txs.pkl')
        if data != 'file not found':
            return

    # Check that Specter is > 1.1.0 version
    # (this is the version where tx API was implemented)
    try:
        specter_version = str(current_app.specter.home_parser()['version'])
    except KeyError:
        # if no password set - send to register
        if not current_app.settings.has_option('SETUP', 'hash'):
            return redirect(url_for("warden.register"))
        flash("Could not connect to Specter. Check credentials below.", "warning")
        return redirect(url_for('warden.specter_auth'))

    if version.parse(specter_version) < version.parse("1.1.0"):
        flash(f"Sorry, you need Specter version 1.1.0 or higher to connect to WARden. You are running version {specter_version}. Please upgrade.", "danger")
        return redirect(url_for('warden.specter_auth'))

    if specter_messages:
        if 'Read timed out' in str(specter_messages):
            flash("Having trouble connecting to Specter. Connection timed out. Data may be outdated.", "warning")
            return

        if 'Connection refused' in str(specter_messages):
            meta['specter_reached'] = False
            session['status'] = json.dumps(meta)
            try:
                flash('Having some difficulty reaching Specter Server. ' +
                      f'Please make sure it is running at {current_app.specter.base_url}. Using cached data. Last Update: ' +
                      current_app.specter.home_parser()['last_update'], 'warning')
                return redirect(url_for('warden.specter_auth'))
            except KeyError:
                flash('Looks like your first time running the WARden. Welcome.', 'info')
                return redirect(url_for('warden.specter_auth'))
        elif 'Unauthorized Login' in str(specter_messages):
            meta['specter_reached'] = False
            session['status'] = json.dumps(meta)
            return redirect(url_for('warden.specter_auth'))
        else:
            abort(500, specter_messages)

    # Update session status
    session['status'] = json.dumps(meta)


@warden.route("/register", methods=["GET", "POST"])
def register():

    # if a password is already set, go to login page
    if current_app.settings.has_option('SETUP', 'hash'):
        if current_user.is_authenticated:
            return redirect(url_for("warden.warden_page"))
        else:
            return redirect(url_for("warden.login"))

    class RegistrationForm(FlaskForm):
        password = PasswordField("Password", validators=[DataRequired()],
                                 render_kw={"placeholder": "Password"})
        confirm_password = PasswordField(
            "Confirm Password", validators=[DataRequired(),
                                            EqualTo("password")],
            render_kw={"placeholder": "Confirm Password"})
        submit = SubmitField("Register")

    form = RegistrationForm()
    if form.validate_on_submit():
        hash = generate_password_hash(form.password.data)
        current_app.settings.set('SETUP', 'hash', hash)
        update_config()
        flash("Password set successfully", "success")
        return redirect(url_for("warden.warden_page"))
    return render_template("warden/register.html", title="Register", form=form)


@warden.route("/login", methods=["GET", "POST"])
def login():

    # if no password set - send to register
    if not current_app.settings.has_option('SETUP', 'hash'):
        return redirect(url_for("warden.register"))

    class LoginForm(FlaskForm):
        password = PasswordField("Password", validators=[DataRequired()])
        submit = SubmitField("Login")

    if current_user.is_authenticated:
        return redirect(url_for("warden.warden_page"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User()
        if check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            flash("Login Successful. Welcome.", "success")
            # The get method below is actually very helpful
            # it returns None if empty. Better than using [] for a dictionary.
            next_page = request.args.get("next")  # get the original page
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("warden.warden_page"))
        else:
            flash("Login failed. Please check password", "danger")

    return render_template("warden/login.html", title="Login", form=form)


@warden.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("warden.warden_page"))


# Support method to check if donation was acknowledged
def donate_check():
    counter_file = os.path.join(home_path(),
                                'warden/counter.json')
    donated = False
    try:
        with open(counter_file) as data_file:
            json_all = json.loads(data_file.read())
        if json_all == "donated":
            donated = True
    except Exception:
        donated = False
    return (donated)


# Main page for WARden
@ warden.route("/", methods=['GET'])
@ warden.route("/warden", methods=['GET'])
@login_required
def warden_page():
    # For now pass only static positions, will update prices and other
    # data through javascript after loaded. This improves load time
    # and refresh speed.
    # Get positions and prepare df for delivery
    df = positions()
    if df.empty:
        msg = "Specter has no transaction history or is down. Open Specter Server and check."
        flash(msg, "warning")
        abort(500, msg)
    if df.index.name != 'trade_asset_ticker':
        df.set_index('trade_asset_ticker', inplace=True)
    df = df[df['is_currency'] == 0].sort_index(ascending=True)
    df = df.to_dict(orient='index')
    # Open Counter, increment, send data
    counter_file = os.path.join(home_path(),
                                'warden/counter.json')
    donated = False
    try:
        with open(counter_file) as data_file:
            json_all = json.loads(data_file.read())
        if json_all == "donated":
            donated = True
        else:
            counter = int(json_all)
            counter += 1
            if counter == 25:
                flash(
                    "Looks like you've been using the app frequently. " +
                    "Awesome! Consider donating.", "info")
            if counter == 50:
                flash(
                    "Open Source software is transparent and free. " +
                    "Support it. Make a donation.", "info")
            if counter == 200:
                flash(
                    "Looks like you are a frequent user of the WARden. " +
                    "Have you donated?", "info")
            if counter >= 1000:
                flash(
                    "You've opened this page 1,000 times or more. " +
                    "Really! Time to make a donation?", "danger")
            with open(counter_file, 'w') as fp:
                json.dump(counter, fp)

    except Exception:
        # File wasn't found. Create start at zero
        if not donated:
            flash(
                "Welcome. Consider making a donation " +
                "to support this software.", "info")
            counter = 0
            with open(counter_file, 'w') as fp:
                json.dump(counter, fp)

    meta = warden_metadata()

    sorted_wallet_list = []
    for wallet in current_app.specter.wallet_alias_list():
        wallet_df = meta['full_df'].loc[meta['full_df']['wallet_alias'] == wallet]
        if wallet_df.empty:
            balance = 0
        else:
            balance = wallet_df['amount'].sum()
        sorted_wallet_list.append((wallet, balance))

    sorted_wallet_list = sorted(sorted_wallet_list, reverse=True, key=itemgetter(1))
    sorted_wallet_list = [i[0] for i in sorted_wallet_list]
    from api.routes import alert_activity

    templateData = {
        "title": "Portfolio Dashboard",
        "warden_metadata": meta,
        "portfolio_data": df,
        "FX": current_app.settings['PORTFOLIO']['base_fx'],
        "donated": donated,
        "alerts": alert_activity(),
        "current_app": current_app,
        "sorted_wallet_list": sorted_wallet_list
    }
    return (render_template('warden/warden.html', **templateData))


@ warden.route("/list_transactions", methods=['GET'])
@login_required
def list_transactions():
    transactions = specter_df()
    return render_template("warden/transactions.html",
                           title="Full Transaction History",
                           transactions=transactions,
                           current_app=current_app)


@ warden.route("/satoshi_quotes", methods=['GET'])
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
    from warden_pricing_engine import fxsymbol as fxs
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
            "donated": donate_check(),
            "status": json.loads(session['status']),
            "current_app": current_app,
        }
        return (render_template('warden/specter_auth.html', **templateData))

    if request.method == 'POST':
        from yaspin import yaspin
        from ansi_management import (warning, success, error, info, clear_screen, bold,
                                     muted, yellow, blue)

        print("")
        print(yellow("  Specter Authentication Log"))
        url = request.form.get('url')
        if url[-1] != '/':
            url += '/'
        if (not url.startswith('http://')) or (not url.startswith('http://')):
            url = 'http://' + url
        current_app.settings['SPECTER']['specter_url'] = url
        print(f"  [i] Trying to reach specter at {url}")
        current_app.settings['SPECTER']['specter_login'] = request.form.get('username')
        current_app.settings['SPECTER']['specter_password'] = request.form.get('password')
        update_config()
        # Recreate the specter class
        from specter_importer import Specter
        current_app.specter = Specter()

        dt = datetime.now()
        seq = int(dt.strftime("%Y%m%d%H%M%S"))
        specter_dict, specter_messages = specter_test(force=True, randomizer=seq)
        if specter_messages is not None:
            if 'Connection refused' in specter_messages:
                flash('Having some difficulty reaching Specter Server. ' +
                      f'Please make sure it is running at {current_app.specter.base_url}', 'warning')
                print(error("💥 Connection Refused. Check URL."))
                return redirect(url_for('warden.specter_auth'))
            if 'Unauthorized Login' in specter_messages:
                print(error("💥 Invalid Credentials. Check Username and Password. Leave blank if none."))
                flash('Invalid Credentials or URL. Try again. ', 'danger')
                return redirect(url_for('warden.specter_auth'))

        # Update Config
        # Limit the Number of txs to avoid delays in checking
        # when user has many txs
        current_app.specter.tx_payload['limit'] = 50
        txs = current_app.specter.refresh_txs(load=False)
        try:
            print(f"  Was able to download {len(txs['txlist'])} transactions")
        except Exception:
            print(error("  Something went wrong... Here's what Specter returned:"))
            print(txs)
            flash('Something went wrong. Check your console for a message. Or try again.', 'danger')
            return redirect(url_for('warden.specter_auth'))

        print(success("  ✅ Connected to Specter Server"))
        print("  Please note that only the first 50 transactions will show")
        print("  at your dashboard as other transactions are downloaded in background.")
        print("")
        current_app.downloading = True

        specter_version = str(current_app.specter.home_parser()['version'])
        flash(f"Success. Connected to Specter Server. Running Specter version {specter_version}.", "success")
        flash("Notice: Only first 50 transactions were downloaded. If you have many transactions, the refresh will run on the background but may take many minutes. Leave the app running.", "warning")
        # Now allow download of all txs in background on next run
        current_app.specter.tx_payload['limit'] = 0
        return redirect(url_for('warden.warden_page'))


# Donation Thank you Page
@ warden.route("/donated", methods=['GET'])
@login_required
def donated():
    counter_file = os.path.join(home_path(),
                                'warden/counter.json')
    templateData = {"title": "Thank You!", "donated": donate_check(), "current_app": current_app}
    with open(counter_file, 'w') as fp:
        json.dump("donated", fp)
    return (render_template('warden/warden_thanks.html', **templateData))


# Page with a single historical chart of NAV
# Include portfolio value as well as CF_sumcum()
@ warden.route("/navchart")
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
                           donated=donate_check(),
                           data=data,
                           current_app=current_app)


@ warden.route("/heatmap")
@login_required
# Returns a monthly heatmap of returns and statistics
def heatmap():
    heatmap_gen, heatmap_stats, years, cols = heatmap_generator()

    return render_template(
        "warden/heatmap.html",
        title="Monthly Returns HeatMap",
        heatmap=heatmap_gen,
        heatmap_stats=heatmap_stats,
        years=years,
        cols=cols,
        current_app=current_app,
        current_user=fx_rate()
    )


@ warden.route("/volchart", methods=["GET", "POST"])
@login_required
# Only returns the html - request for data is done through jQuery AJAX
def volchart():
    return render_template("warden/volchart.html",
                           title="Historical Volatility Chart",
                           current_app=current_app,
                           current_user=fx_rate())


@ warden.route("/portfolio_compare", methods=["GET"])
@login_required
def portfolio_compare():
    return render_template("warden/portfolio_compare.html",
                           title="Portfolio Comparison",
                           current_app=current_app,
                           current_user=fx_rate())


@ warden.route("/price_feed", methods=["GET"])
@login_required
def price_feed():
    return_dict = {}
    ticker = request.args.get("ticker")
    ticker = "BTC" if not ticker else ticker
    ticker = ticker.upper()
    for pr in PROVIDER_LIST:
        provider = PROVIDER_LIST[pr]
        price_data = PriceData(ticker, provider)
        data = {}
        data['provider_info'] = {
            'name': provider.name,
            'errors': provider.errors,
            'base_url': provider.base_url,
            'doc_link': provider.doc_link,
            'field_dict': provider.field_dict,
            'globalURL': None
        }
        if provider.base_url is not None:
            globalURL = (provider.base_url + "?" + provider.ticker_field + "=" +
                         ticker + provider.url_args)
            # Some APIs use the ticker without a ticker field i.e. xx.xx./AAPL&...
            # in these cases, we pass the ticker field as empty
            if provider.ticker_field == '':
                if provider.url_args[0] == '&':
                    provider.url_args = provider.url_args.replace('&', '?', 1)
                globalURL = (provider.base_url + "/" + ticker + provider.url_args)
            # Some URLs are in the form http://www.www.www/ticker_field/extra_fields?
            if provider.replace_ticker is not None:
                globalURL = provider.base_url.replace('ticker_field', ticker)
            data['provider_info']['globalURL'] = globalURL

        try:

            data['price_data'] = {
                'ticker': ticker,
                'last_update': price_data.last_update.strftime('%m/%d/%Y'),
                'first_update': price_data.first_update.strftime('%m/%d/%Y'),
                'last_close': float(price_data.last_close),
                'errors': price_data.errors
            }
        except Exception as e:
            data['price_data'] = {
                'price_data_errors': price_data.errors,
                'error': str(e)
            }

        # Try to get realtime prices
        data['realtime'] = {
            'price': (price_data.realtime(PROVIDER_LIST[pr])),
            'error': price_data.errors
        }

        return_dict[provider.name] = data

    return render_template("warden/price_feed.html",
                           title="Price Feed Check",
                           current_app=current_app,
                           current_user=fx_rate(),
                           return_dict=return_dict)


# Show debug info
@ warden.route('/show_log')
@login_required
def show_log():
    log = logging.getLogger('__name__')
    log.info("route =>'/env' - hit!")
    return render_template('warden/show_log.html',
                           title="Debug Viewer",
                           current_app=current_app,
                           current_user=fx_rate()
                           )


# -------------------------------------------------
#  START JINJA 2 Filters
# -------------------------------------------------
# Jinja2 filter to format time to a nice string
# Formating function, takes self +
# number of decimal places + a divisor


@ jinja2.contextfilter
@ warden.app_template_filter()
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
        try:
            form_string = "{0:,.{prec}f}".format(n, prec=places)
            return form_string
        except (ValueError, KeyError):
            return "-"


# Jinja filter - epoch to time string
@ jinja2.contextfilter
@ warden.app_template_filter()
def epoch(context, epoch):
    time_r = datetime.fromtimestamp(epoch).strftime("%m-%d-%Y (%H:%M)")
    return time_r


# Jinja filter - fx details
@ jinja2.contextfilter
@ warden.app_template_filter()
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


@ jinja2.contextfilter
@ warden.app_template_filter()
def jencode(context, url):
    return urllib.parse.quote_plus(url)


# Jinja filter - time to time_ago
@ jinja2.contextfilter
@ warden.app_template_filter()
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
