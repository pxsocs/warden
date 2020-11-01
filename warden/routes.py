from flask import (Blueprint, redirect, render_template,
                   flash, session, request, current_app, url_for)
from warden.warden import (list_specter_wallets, warden_metadata, positions,
                           positions_dynamic, get_price_ondate,
                           generatenav, specter_df, check_services,
                           current_path, specter_update, regenerate_nav)

from warden.warden_pricing_engine import (test_tor, tor_request, price_data_rt,
                                          fx_rate)
from warden.utils import update_config

from datetime import datetime
from dateutil.relativedelta import relativedelta
import jinja2
import simplejson
import pandas as pd
import numpy as np
import json
import os
import urllib
import csv

warden = Blueprint("warden",
                   __name__,
                   template_folder='templates',
                   static_folder='static')


# START WARDEN ROUTES ----------------------------------------
# Things to check before each request:
# 1. Is Tor running? It's a requirement.
# 2. Is Specter server running? Also a requirement.
# 2.5 If running, is there a balance?
# 3. Found MyNode? Not a requirement but enables added functions.
# 4. Found Bitcoin Node? Not a requirement but enables added functions.
@warden.before_request
def before_request():
    # Ignore check for some pages - these are mostly methods that need
    # to run even in setup mode
    exclude_list = [
        "warden.setup", "warden.testtor", "warden.gitreleases",
        "warden.realtime_btc", "warden.data_folder", "warden.testtor",
        "warden.checkservices", "warden.check_activity", "warden.warden_metadata",
        "warden.node_info", "warden.specter_json"
    ]
    if request.endpoint in exclude_list:
        return
    need_setup = False
    # Check Tor
    tor = current_app.tor
    need_setup = not tor['status']
    # Get Services
    services = current_app.services
    need_setup = not services['specter']['running']
    # Are Wallets Found?
    specter_wallets = have_specter_wallets(load=False)
    need_setup = not specter_wallets
    # Transactions found?
    df = positions()
    need_setup = df.empty
    if need_setup:
        meta = {
            'tor': tor,
            'services': services,
            'specter_wallets': specter_wallets,
            'txs': df.empty
        }
        messages = json.dumps(meta)
        session['messages'] = messages
        return redirect(url_for("warden.setup"))


# Support method to check if donation was acknowledged
def donate_check():
    counter_file = os.path.join(current_path(),
                                'static/json_files/counter.json')
    donated = False
    try:
        with open(counter_file) as data_file:
            json_all = json.loads(data_file.read())
        if json_all == "donated":
            donated = True
    except Exception:
        donated = False
    return (donated)


# Support method to check for specter wallets
def have_specter_wallets(load=True):
    wallets = list_specter_wallets(load)
    if (wallets == []) or (wallets == None):
        return False
    return True


# Main page for WARden
@ warden.route("/", methods=['GET'])
@ warden.route("/warden", methods=['GET'])
def warden_page():
    # For now pass only static positions, will update prices and other
    # data through javascript after loaded. This improves load time
    # and refresh speed.
    # Get positions and prepare df for delivery
    df = positions()
    if df.index.name != 'trade_asset_ticker':
        df.set_index('trade_asset_ticker', inplace=True)
    df = df[df['is_currency'] == 0].sort_index(ascending=True)
    df = df.to_dict(orient='index')

    # Open Counter, increment, send data
    counter_file = os.path.join(current_path(),
                                'static/json_files/counter.json')
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

    alerts = False
    meta = warden_metadata()
    if not meta['warden_enabled']:
        abort(500, 'WARden is not Enabled. Check your Connections.')
    if isinstance(meta['old_new_df_old'], pd.DataFrame):
        if not meta['old_new_df_old'].empty:
            alerts = True
    if isinstance(meta['old_new_df_new'], pd.DataFrame):
        if not meta['old_new_df_new'].empty:
            alerts = True

    templateData = {
        "title": "Portfolio Dashboard",
        "warden_metadata": meta,
        "warden_enabled": warden_metadata()['warden_enabled'],
        "portfolio_data": df,
        "FX": current_app.settings['PORTFOLIO']['base_fx'],
        "donated": donated,
        "alerts": alerts,
        "specter": specter_update(),
        "current_app": current_app
    }
    return (render_template('warden/warden.html', **templateData))


@ warden.route("/list_transactions", methods=['GET'])
def list_transactions():
    transactions = specter_df()
    return render_template("warden/transactions.html",
                           title="Full Transaction History",
                           transactions=transactions,
                           current_app=current_app)


# Returns notification if no wallets were found at Specter
@ warden.route("/setup", methods=['GET'])
def setup():
    need_setup = False
    # Check Tor
    tor = test_tor()
    need_setup = not tor['status']
    # Get Services
    services = check_services()
    need_setup = not services['specter']['running']
    # Are Wallets Found?
    specter_wallets = have_specter_wallets()
    need_setup = not specter_wallets
    # Transactions found?
    df = positions()
    need_setup = not df.empty
    meta = {
        'tor': tor,
        'services': services,
        'specter_wallets': specter_wallets,
        'txs': not df.empty,
        'need_setup': need_setup,
    }
    messages = json.dumps(meta)
    session['messages'] = messages
    templateData = {
        "title": "System Status",
        "donated": donate_check(),
        "messages": json.loads(session['messages']),
        "specter": specter_update(),
        "current_app": current_app,
    }
    return (render_template('warden/warden_empty.html', **templateData))

# Update user fx settings in config.ini


@warden.route('/update_fx', methods=['GET', 'POST'])
def update_fx():
    fx = request.args.get("code")
    current_app.settings['PORTFOLIO']['base_fx'] = fx
    update_config()
    from warden.warden_pricing_engine import fxsymbol as fxs
    current_app.fx = fxs(fx, 'all')
    regenerate_nav()
    redir = request.args.get("redirect")
    return redirect(redir)


# Save current folder to json
@warden.route('/data_folder', methods=['GET', 'POST'])
def data_folder():
    data_file = os.path.join(current_path(),
                             'static/json_files/specter_data_folder.json')

    if request.method == 'GET':
        try:
            with open(data_file) as data_file:
                return_data = json.loads(data_file.read())
        except Exception as e:
            return_data = str(e)
        return(json.dumps(return_data))

    if request.method == 'POST':
        results = request.form
        # Test this data folder
        try:
            data_folder = results['data_folder']
            # Test if can get specter data
            specter = specter_update(load=False, data_folder=data_folder)
            # Check Status
            is_configured = specter['is_configured']
            is_running = specter['is_running']
            wallets = specter['wallets']['wallets']

        except Exception as e:
            return json.dumps({"message": "Error: " + str(e)})

        message = ""
        ok_save = True
        if not is_configured:
            ok_save = False
            message += "Specter does not seem to be configured in this folder. "

        if not is_running:
            ok_save = False
            message += "Specter does not seem to be running in this folder. "

        if wallets == {}:
            ok_save = False
            message += "No wallets found - check folder."

        if ok_save:
            with open(data_file, 'w') as fp:
                json.dump(results, fp)
            message += "Specter Data folder found. Saved Successfully."

        return json.dumps({"message": message})


# API End Point checks for wallet activity
@ warden.route("/check_activity", methods=['GET'])
def check_activity():
    alerts = False
    meta = warden_metadata()
    if meta['warden_enabled']:
        if isinstance(meta['old_new_df_old'], pd.DataFrame):
            if not meta['old_new_df_old'].empty:
                alerts = True
                regenerate_nav()
        if isinstance(meta['old_new_df_new'], pd.DataFrame):
            if not meta['old_new_df_new'].empty:
                alerts = True
                regenerate_nav()
    return (json.dumps(alerts))


# API End Point with all WARden metadata
@ warden.route("/warden_metadata", methods=['GET'])
def metadata_json():
    meta = warden_metadata()
    # jsonify transactions
    for wallet in meta['txs']:
        try:
            meta['txs'][wallet] = meta['txs'][wallet].to_dict()
        except Exception:
            pass
    try:
        meta['df_old'] = meta['df_old'].to_dict()
    except Exception:
        pass

    try:
        meta['full_df'] = meta['full_df'].to_dict()
    except Exception:
        pass

    try:
        meta['old_new_df_old'] = meta['old_new_df_old'].to_dict()
    except Exception:
        pass

    return (json.dumps(meta, default=lambda o: '<not serializable>'))


# Donation Thank you Page
@ warden.route("/donated", methods=['GET'])
def donated():
    counter_file = os.path.join(current_path(),
                                'static/json_files/counter.json')
    templateData = {"title": "Thank You!", "donated": donate_check(), "current_app": current_app}
    with open(counter_file, 'w') as fp:
        json.dump("donated", fp)
    return (render_template('warden/warden_thanks.html', **templateData))


# Returns a JSON with Test Response on TOR
@ warden.route("/testtor", methods=["GET"])
def testtor():
    return json.dumps(test_tor())


# Returns a JSON with Test Response on TOR
@ warden.route("/gitreleases", methods=["GET"])
def gitreleases():
    url = 'https://api.github.com/repos/pxsocs/specter_warden/releases'
    request = tor_request(url)
    try:
        data = request.json()
    except Exception:
        try:  # Try again - some APIs return a json already
            data = json.loads(request)
        except Exception:
            data = json.dumps("Error getting request")

    return json.dumps(data)


# API End point
# Json for main page with realtime positions
@ warden.route("/positions_json", methods=["GET"])
def positions_json():
    # Get all transactions and cost details
    # This serves the main page
    dfdyn, piedata = positions_dynamic()
    dfdyn = dfdyn.to_dict(orient='index')

    json_dict = {
        'positions': dfdyn,
        'piechart': piedata,
        'user': current_app.fx,
        'btc': price_data_rt("BTC") * fx_rate()['fx_rate']
    }
    return simplejson.dumps(json_dict, ignore_nan=True)


# Returns current BTC price and FX rate for current user
# This is the function used at the layout navbar to update BTC price
# Please note that the default is to update every 20s (MWT(20) above)
@ warden.route("/realtime_btc", methods=["GET"])
def realtime_btc():
    fx_details = fx_rate()
    fx_r = {'cross': fx_details['symbol'], 'fx_rate': fx_details['fx_rate']}
    fx_r['btc_usd'] = price_data_rt("BTC")
    fx_r['btc_fx'] = fx_r['btc_usd'] * fx_r['fx_rate']
    return json.dumps(fx_r)


# API end point - cleans notifications and creates a new checkpoint
@ warden.route("/dismiss_notification", methods=["POST"])
def dismiss_notification():
    # Run the df and clean the files (True)
    specter_df(True)
    flash("Notification dismissed. New CheckPoint created.", "success")
    return json.dumps("Done")


# API end point to return node info
# MyNode Bitcoin Data for front page
@ warden.route("/node_info", methods=["GET"])
def node_info():
    data = specter_update(load=True)
    status = {
        'info': data.info,
        'bitcoin': data.network_info,
        'services': check_services(load=True),
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return simplejson.dumps(status, ignore_nan=True)


# API end point to return service status
@ warden.route("/services", methods=["GET"])
def checkservices():
    services = check_services()
    return simplejson.dumps(services, ignore_nan=True)


# API end point to return Specter data
# args: ?load=True (True = loads saved json, False = refresh data)
@ warden.route("/specter", methods=["GET"])
def specter_json():
    load = request.args.get("load")
    load = True if not load else load
    specter = specter_update(load=load)
    return simplejson.dumps(specter, ignore_nan=True)


# Latest Traceback message
@ warden.route("/traceback_error", methods=["GET"])
def traceback_error():
    import traceback
    trace = traceback.format_exc()
    return simplejson.dumps(trace, ignore_nan=True)


# API end point
# Function returns summary statistics for portfolio NAV and values
# Main function for portfolio page
@ warden.route("/portstats", methods=["GET", "POST"])
def portstats():
    meta = {}
    # Looking to generate the following data here and return as JSON
    # for AJAX query on front page:
    # Start date, End Date, Start NAV, End NAV, Returns (1d, 1wk, 1mo, 1yr,
    # YTD), average daily return. Best day, worse day. Std dev of daily ret,
    # Higher NAV, Lower NAV + dates. Higher Port Value (date).
    data = generatenav()
    meta["start_date"] = (data.index.min()).date().strftime("%B %d, %Y")
    meta["end_date"] = data.index.max().date().strftime("%B %d, %Y")
    meta["start_nav"] = data["NAV_fx"][0]
    meta["end_nav"] = data["NAV_fx"][-1].astype(float)
    meta["max_nav"] = data["NAV_fx"].max().astype(float)
    meta["max_nav_date"] = data[
        data["NAV_fx"] == data["NAV_fx"].max()].index.strftime("%B %d, %Y")[0]
    meta["min_nav"] = data["NAV_fx"].min().astype(float)
    meta["min_nav_date"] = data[
        data["NAV_fx"] == data["NAV_fx"].min()].index.strftime("%B %d, %Y")[0]
    meta["end_portvalue"] = data["PORT_fx_pos"][-1].astype(float)
    meta["end_portvalue_usd"] = meta["end_portvalue"] / fx_rate()['fx_rate']
    meta["max_portvalue"] = data["PORT_fx_pos"].max().astype(float)
    meta["max_port_date"] = data[data["PORT_fx_pos"] == data["PORT_fx_pos"].
                                 max()].index.strftime("%B %d, %Y")[0]
    meta["min_portvalue"] = round(data["PORT_fx_pos"].min(), 0)
    meta["min_port_date"] = data[data["PORT_fx_pos"] == data["PORT_fx_pos"].
                                 min()].index.strftime("%B %d, %Y")[0]
    meta["return_SI"] = (meta["end_nav"] / meta["start_nav"]) - 1
    # Temporary fix for an issue with portfolios that are just too new
    # Create a function to handle this
    try:
        meta["return_1d"] = (meta["end_nav"] / data["NAV_fx"][-2]) - 1
    except IndexError:
        meta["return_1d"] = "-"

    try:
        meta["return_1wk"] = (meta["end_nav"] / data["NAV_fx"][-7]) - 1
    except IndexError:
        meta["return_1wk"] = "-"

    try:
        meta["return_30d"] = (meta["end_nav"] / data["NAV_fx"][-30]) - 1
    except IndexError:
        meta["return_30d"] = "-"

    try:
        meta["return_90d"] = (meta["end_nav"] / data["NAV_fx"][-90]) - 1
    except IndexError:
        meta["return_90d"] = "-"

    try:
        meta["return_ATH"] = (meta["end_nav"] / meta["max_nav"]) - 1
    except IndexError:
        meta["return_ATH"] = "-"

    try:
        yr_ago = pd.to_datetime(datetime.today() - relativedelta(years=1))
        yr_ago_NAV = data.NAV_fx[data.index.get_loc(yr_ago, method="nearest")]
        meta["return_1yr"] = meta["end_nav"] / yr_ago_NAV - 1
    except IndexError:
        meta["return_1yr"] = "-"

    # Create data for summa"age
    meta["fx"] = current_app.settings['PORTFOLIO']['base_fx']
    meta["daily"] = {}
    for days in range(1, 8):
        meta["daily"][days] = {}
        meta["daily"][days]["date"] = data.index[days * -1].date().strftime(
            "%A <br> %m/%d")
        meta["daily"][days]["nav"] = data["NAV_fx"][days * -1]
        meta["daily"][days]["nav_prev"] = data["NAV_fx"][(days + 1) * -1]
        meta["daily"][days]["perc_chg"] = (meta["daily"][days]["nav"] /
                                           meta["daily"][days]["nav_prev"]) - 1
        meta["daily"][days]["port"] = data["PORT_fx_pos"][days * -1]
        meta["daily"][days]["port_prev"] = data["PORT_fx_pos"][(days + 1) * -1]
        meta["daily"][days]["port_chg"] = (meta["daily"][days]["port"] -
                                           meta["daily"][days]["port_prev"])

    # Removes Numpy type from json - returns int instead
    def convert(o):
        if isinstance(o, np.int64):
            return int(o)
        else:
            return (o)

    # create chart data for a small NAV chart
    return simplejson.dumps(meta, ignore_nan=True, default=convert)


# Page with a single historical chart of NAV
# Include portfolio value as well as CF_sumcum()
@ warden.route("/navchart")
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
                           current_app=current_app)


# API end point - returns a json with NAV Chartdata
@ warden.route("/navchartdatajson", methods=["GET", "POST"])
#  Creates a table with dates and NAV values
def navchartdatajson():
    data = generatenav()
    # Generate data for NAV chart
    navchart = data[["NAV_fx"]]
    # dates need to be in Epoch time for Highcharts
    navchart.index = (navchart.index - datetime(1970, 1, 1)).total_seconds()
    navchart.index = navchart.index * 1000
    navchart.index = navchart.index.astype(np.int64)
    navchart = navchart.to_dict()
    navchart = navchart["NAV_fx"]
    # Sort for HighCharts
    import collections
    navchart = collections.OrderedDict(sorted(navchart.items()))
    navchart = json.dumps(navchart)
    return navchart


# API end point - returns a json with NAV Chartdata
@ warden.route("/stackchartdatajson", methods=["GET", "POST"])
#  Creates a table with dates and NAV values
def stackchartdatajson():
    data = generatenav()
    # Generate data for Stack chart
    # Filter to Only BTC Positions
    try:
        data['BTC_cum'] = data['BTC_quant'].cumsum()
        stackchart = data[["BTC_cum"]]
        # dates need to be in Epoch time for Highcharts
        stackchart.index = (stackchart.index - datetime(1970, 1, 1)).total_seconds()
        stackchart.index = stackchart.index * 1000
        stackchart.index = stackchart.index.astype(np.int64)
        stackchart = stackchart.to_dict()
        stackchart = stackchart["BTC_cum"]
        # Sort for HighCharts
        import collections
        stackchart = collections.OrderedDict(sorted(stackchart.items()))
        stackchart = json.dumps(stackchart)
    except Exception as e:
        return (json.dumps({"Error": str(e)}))
    return stackchart


# Return the price of a ticker on a given date
# Takes arguments:
# ticker:       Single ticker for filter (default = NAV)
# date:         date to get price
@ warden.route("/getprice_ondate", methods=["GET"])
def getprice_ondate():
    # Get the arguments and store
    if request.method == "GET":
        date_input = request.args.get("date")
        ticker = request.args.get("ticker")
        if (not ticker) or (not date_input):
            return 0
        ticker = ticker.upper()
        get_date = datetime.strptime(date_input, "%Y-%m-%d")
        # Create price object
        try:
            price = str(get_price_ondate(ticker, get_date).close)
        except Exception as e:
            price = "Not Found. Error: " + str(e)
        return price


@warden.route("/fx_lst", methods=["GET"])
# Receiver argument ?term to return a list of fx (fiat and digital)
# Searches the list both inside the key as well as value of dict
def fx_list():
    fx_dict = {}
    filename = os.path.join(current_path(),
                            'static/csv_files/physical_currency_list.csv')
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        fx_dict = {rows[0]: rows[1] for rows in reader}
    q = request.args.get("term")
    if q is None:
        q = ""
    list_key = {
        key: value
        for key, value in fx_dict.items() if q.upper() in key.upper()
    }
    list_value = {
        key: value
        for key, value in fx_dict.items() if q.upper() in value.upper()
    }
    list = {**list_key, **list_value}
    list = json.dumps(list)
    return list


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
