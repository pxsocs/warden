from flask import (Blueprint, flash, request, current_app, jsonify, Response,
                   redirect, url_for)
from backend.warden_modules import (warden_metadata, positions_dynamic,
                                    generatenav, specter_df, current_path,
                                    regenerate_nav, home_path, transactions_fx)
from connections import tor_request, url_parser
from pricing_engine.engine import price_ondate, historical_prices
from flask_login import login_required, current_user
from random import randrange
from pricing_engine.engine import fx_rate, realtime_price
from backend.utils import heatmap_generator, pickle_it, safe_serialize
from models import Trades, AccountInfo, TickerInfo
from datetime import datetime, timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta
import mhp as mrh
import simplejson
import logging
import pandas as pd
import numpy as np
import json
import os
import math
import csv
import requests
import socket

api = Blueprint('api', __name__)


@api.route("/gitreleases", methods=["GET"])
@login_required
def gitreleases():
    url = 'https://api.github.com/repos/pxsocs/warden/releases'
    request = tor_request(url)
    try:
        data = request.json()
    except Exception:
        try:  # Try again - some APIs return a json already
            data = json.loads(request)
        except Exception:
            data = json.dumps("Error getting request")

    return json.dumps(data)


@api.route("/txs_json", methods=['GET'])
@login_required
def txs_json():
    df_pkl = 'warden/txs_pf.pkl'
    tx_df = pickle_it(action='load', filename=df_pkl)
    return tx_df.to_json(orient='table')


@api.route("/satoshi_quotes_json", methods=['GET'])
@login_required
def satoshi_quotes_json():
    url = 'https://raw.githubusercontent.com/NakamotoInstitute/nakamotoinstitute.org/0bf08c48cd21655c76e8db06da39d16036a88594/data/quotes.json'
    try:
        quotes = tor_request(url).json()
    except Exception:
        return (json.dumps(' >> Error contacting server. Retrying... '))
    quote = quotes[randrange(len(quotes))]
    return (quote)


def alert_activity():
    alerts = False
    # Don't send any alerts as activity still being downloaded
    if current_app.downloading:
        return alerts
    ack_file = 'txs_diff.pkl'
    try:
        data = pickle_it(action='load', filename=ack_file)
        if data == 'file not found':
            raise FileNotFoundError
        if data['changes_detected_on'] is not None:
            return (True)
        else:
            return (False)
    except Exception:
        return (False)


# API End Point checks for wallet activity


# Gets a local pickle file and dumps - does not work with pandas df
# Do not include extension pkl on argument
@api.route("/get_pickle", methods=['GET'])
@login_required
def get_pickle():
    filename = request.args.get("filename")
    serialize = request.args.get("serialize")
    if not serialize:
        serialize = True
    if not filename:
        return None
    filename += ".pkl"
    data_loader = pickle_it(action='load', filename=filename)
    if serialize is True:
        return (json.dumps(data_loader,
                           default=lambda o: '<not serializable>'))
    else:
        return (json.dumps(data_loader, default=str))


@api.route("/check_activity", methods=['GET'])
@login_required
def check_activity():
    alerts = alert_activity()
    return (json.dumps(alerts))


# API End Point with all WARden metadata
@api.route("/warden_metadata", methods=['GET'])
@login_required
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


# Returns a JSON with Test Response on TOR
@api.route("/testtor", methods=["GET"])
@login_required
def testtor():
    from connections import test_tor
    return json.dumps(test_tor())


#  API End point
# Json for main page with realtime positions


@api.route("/positions_json", methods=["GET"])
@login_required
def positions_json():
    # Get all transactions and cost details
    # This serves the main page
    try:
        dfdyn, piedata = positions_dynamic()
        btc_price = realtime_price("BTC")['price'] * fx_rate()['fx_rate']
        dfdyn = dfdyn.to_dict(orient='index')
    except Exception:
        dfdyn = piedata = None
        btc_price = 0
    try:
        btc = realtime_price("BTC")['price']
    except TypeError:
        btc = 0
    if not btc:
        btc = 0

    json_dict = {
        'positions': dfdyn,
        'piechart': piedata,
        'user': current_app.fx,
        'btc': btc_price
    }
    return simplejson.dumps(json_dict, ignore_nan=True)


# Returns current BTC price and FX rate for current user
# This is the function used at the layout navbar to update BTC price
# Please note that the default is to update every 20s (MWT(20) above)
@api.route("/realtime_btc", methods=["GET"])
@login_required
def realtime_btc():
    try:
        fx_details = fx_rate()
        fx_r = {
            'cross': fx_details['symbol'],
            'fx_rate': fx_details['fx_rate']
        }
        fx_r['btc_usd'] = realtime_price("BTC", fx='USD')['price']
        fx_r['btc_fx'] = fx_r['btc_usd'] * fx_r['fx_rate']
    except Exception as e:
        logging.warn(
            f"There was an error while getting realtime prices. Error: {e}")
        fx_r = 0
    return json.dumps(fx_r)


# API end point - cleans notifications and creates a new checkpoint
@api.route("/dismiss_notification", methods=["POST"])
@login_required
def dismiss_notification():
    # Run the df and clean the files (True)
    specter_df(delete_files=True)
    flash("Notification dismissed. New CheckPoint created.", "success")
    return json.dumps("Done")


# API end point to return Specter data
# args: ?load=True (True = loads saved json, False = refresh data)
@api.route("/specter", methods=["GET"])
@login_required
def specter_json():
    data = current_app.specter.home_parser()
    return simplejson.dumps(data, ignore_nan=True)


# API end point to return Current App Specter data
# args: ?load=True (True = loads saved json, False = refresh data)
@api.route("/currentappspecter", methods=["GET"])
@login_required
def currentspecter_json():

    data = current_app.specter.wallet_info
    return simplejson.dumps(data, ignore_nan=True)


# Latest Traceback message
@api.route("/traceback_error", methods=["GET"])
@login_required
def traceback_error():
    import traceback
    trace = traceback.format_exc()
    return simplejson.dumps(trace, ignore_nan=True)


# API end point
# Function returns summary statistics for portfolio NAV and values
# Main function for portfolio page
@api.route("/portstats", methods=["GET", "POST"])
@login_required
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
    meta["end_nav"] = float(data["NAV_fx"][-1])
    meta["max_nav"] = float(data["NAV_fx"].max())
    meta["max_nav_date"] = data[
        data["NAV_fx"] == data["NAV_fx"].max()].index.strftime("%B %d, %Y")[0]
    meta["min_nav"] = float(data["NAV_fx"].min())
    meta["min_nav_date"] = data[
        data["NAV_fx"] == data["NAV_fx"].min()].index.strftime("%B %d, %Y")[0]
    meta["end_portvalue"] = data["PORT_fx_pos"][-1].astype(float)
    meta["end_portvalue_usd"] = meta["end_portvalue"] / fx_rate()['fx_rate']
    meta["max_portvalue"] = data["PORT_fx_pos"].astype(float).max()
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


# API end point - returns a json with NAV Chartdata
@api.route("/navchartdatajson", methods=["GET", "POST"])
@login_required
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
@api.route("/stackchartdatajson", methods=["GET", "POST"])
@login_required
#  Creates a table with dates and NAV values
def stackchartdatajson():
    data = generatenav()
    # Generate data for Stack chart
    # Filter to Only BTC Positions
    try:
        data['BTC_cum'] = data['PORT_VALUE_BTC']
        stackchart = data[["BTC_cum"]]
        # dates need to be in Epoch time for Highcharts
        stackchart.index = (stackchart.index -
                            datetime(1970, 1, 1)).total_seconds()
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


# API end point - returns a json with Portfolio Fiat Value
@api.route("/fiatchartdatajson", methods=["GET", "POST"])
@login_required
#  Creates a table with dates and Fiat values
def fiatchartdatajson():
    data = generatenav()
    # Generate data for Stack chart
    # Filter to Only BTC Positions
    fx = current_app.settings['PORTFOLIO']['base_fx']
    if fx is None:
        fx = 'USD'

    try:
        data['fiat'] = data['PORT_fx_pos']
        fiatchart = data[["fiat"]]
        # dates need to be in Epoch time for Highcharts
        fiatchart.index = (fiatchart.index -
                           datetime(1970, 1, 1)).total_seconds()
        fiatchart.index = fiatchart.index * 1000
        fiatchart.index = fiatchart.index.astype(np.int64)
        fiatchart = fiatchart.to_dict()
        fiatchart = fiatchart["fiat"]
        # Sort for HighCharts
        import collections
        fiatchart = collections.OrderedDict(sorted(fiatchart.items()))
        fiatchart = json.dumps(fiatchart)
    except Exception as e:
        return (json.dumps({"Error": str(e)}))
    return fiatchart


# API end point - returns a json with BTC Fiat Price


@api.route("/btcchartdatajson", methods=["GET", "POST"])
@login_required
#  Creates a table with dates and Fiat values
def btcchartdatajson():
    data = generatenav()
    try:
        data['fiat'] = data['BTC_price']
        fiatchart = data[["fiat"]]
        # dates need to be in Epoch time for Highcharts
        fiatchart.index = (fiatchart.index -
                           datetime(1970, 1, 1)).total_seconds()
        fiatchart.index = fiatchart.index * 1000
        fiatchart.index = fiatchart.index.astype(np.int64)
        fiatchart = fiatchart.to_dict()
        fiatchart = fiatchart["fiat"]
        # Sort for HighCharts
        import collections
        fiatchart = collections.OrderedDict(sorted(fiatchart.items()))
        fiatchart = json.dumps(fiatchart)
    except Exception as e:
        return (json.dumps({"Error": str(e)}))
    return fiatchart


# Return the price of a ticker on a given date
# Takes arguments:
# ticker:       Single ticker for filter (default = NAV)
# date:         date to get price
@api.route("/getprice_ondate", methods=["GET"])
@login_required
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
            price = str(price_ondate(ticker, get_date).close)
        except Exception as e:
            price = "Not Found. Error: " + str(e)
        return price


@api.route("/fx_lst", methods=["GET"])
@login_required
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


@api.route("/heatmapbenchmark_json", methods=["GET"])
@login_required
# Return Monthly returns for Benchmark and Benchmark difference from NAV
# Takes arguments:
# ticker   - single ticker for filter
def heatmapbenchmark_json():

    # Get portfolio data first
    heatmap_gen, heatmap_stats, years, cols = heatmap_generator()

    # Now get the ticker information and run comparison
    if request.method == "GET":
        ticker = request.args.get("ticker")
        # Defaults to king BTC
        if not ticker:
            ticker = "BTC"

    # Gather the first trade date in portfolio and store
    # used to match the matrixes later
    # Panda dataframe with transactions
    df = transactions_fx()
    # Filter the df acccoring to filter passed as arguments
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    start_date = df["trade_date"].min()
    start_date -= timedelta(days=1)  # start on t-1 of first trade

    # Generate price Table now for the ticker and trim to match portfolio
    fx = current_app.settings['PORTFOLIO']['base_fx']
    data = historical_prices(ticker, fx)
    mask = data.index >= start_date
    data = data.loc[mask]

    # If notification is an error, skip this ticker
    if data is None:
        messages = data.errors
        return jsonify(messages)

    data = data.rename(columns={'close_converted': ticker + '_price'})
    data = data[[ticker + '_price']]
    data.sort_index(ascending=True, inplace=True)
    data["pchange"] = (data / data.shift(1)) - 1
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(data["pchange"], eoy=True)
    heatmap_stats = heatmap
    cols = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "eoy",
    ]
    cols_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    years = heatmap.index.tolist()
    # Create summary stats for the Ticker
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(
        axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(
        axis=1)
    heatmap_stats["POSITIVES"] = heatmap_stats[
        heatmap_stats[cols_months] > 0].count(axis=1)
    heatmap_stats["NEGATIVES"] = heatmap_stats[
        heatmap_stats[cols_months] < 0].count(axis=1)
    heatmap_stats["POS_MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] > 0].mean(axis=1)
    heatmap_stats["NEG_MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] < 0].mean(axis=1)
    heatmap_stats["MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] != 0].mean(axis=1)

    # Create the difference between the 2 df - Pandas is cool!
    heatmap_difference = heatmap_gen - heatmap

    # return (heatmap, heatmap_stats, years, cols, ticker, heatmap_diff)
    return simplejson.dumps(
        {
            "heatmap": heatmap.to_dict(),
            "heatmap_stats": heatmap_stats.to_dict(),
            "cols": cols,
            "years": years,
            "ticker": ticker,
            "heatmap_diff": heatmap_difference.to_dict(),
        },
        ignore_nan=True,
        default=datetime.isoformat,
    )


@api.route("/histvol", methods=["GET", "POST"])
@login_required
# Returns a json with data to create the vol chart
# takes inputs from get:
# ticker, meta (true returns only metadata), rolling (in days)
# metadata (max, mean, etc)
def histvol():
    # if there's rolling variable, get it, otherwise default to 30
    if request.method == "GET":
        try:
            q = int(request.args.get("rolling"))
        except ValueError:
            q = 30
    else:
        q = 30

    ticker = request.args.get("ticker")
    metadata = request.args.get("meta")

    # When ticker is not sent, will calculate for portfolio
    if not ticker:
        data = generatenav()
        data["vol"] = (data["NAV_fx"].pct_change().rolling(q).std() *
                       (365**0.5) * 100)
        # data.set_index('date', inplace=True)
        vollist = data[["vol"]]
        vollist.index = vollist.index.strftime("%Y-%m-%d")
        datajson = vollist.to_json()

    if ticker:
        filename = "thewarden/historical_data/" + ticker + ".json"
        filename = os.path.join(current_path(), filename)

        try:
            with open(filename) as data_file:
                local_json = json.loads(data_file.read())
                data_file.close()
                prices = pd.DataFrame(
                    local_json["Time Series (Digital Currency Daily)"]).T
                prices["4b. close (USD)"] = prices["4b. close (USD)"].astype(
                    np.float)
                prices["vol"] = (
                    prices["4b. close (USD)"].pct_change().rolling(q).std() *
                    (365**0.5) * 100)
                pricelist = prices[["vol"]]
                datajson = pricelist.to_json()

        except (FileNotFoundError, KeyError):
            datajson = "Ticker Not Found"

    if metadata is not None:
        metatable = {}
        metatable["mean"] = vollist.vol.mean()
        metatable["max"] = vollist.vol.max()
        metatable["min"] = vollist.vol.min()
        metatable["last"] = vollist.vol[-1]
        metatable["lastvsmean"] = (
            (vollist.vol[-1] / vollist.vol.mean()) - 1) * 100
        metatable = json.dumps(metatable)
        return metatable

    return datajson


@api.route("/mempool_json", methods=["GET", "POST"])
@login_required
def mempool_json():
    url = None
    try:
        mp_config = current_app.settings['MEMPOOL']
        url = mp_config.get('url')
        url = url_parser(url)

        # Get recommended fees
        try:
            mp_fee = tor_request(url + 'api/v1/fees/recommended').json()
        except Exception:
            mp_fee = tor_request(url + 'api/v1/fees/recommended').text

        if 'Service Unavailable' in mp_fee:
            return json.dumps({
                'mp_fee':
                '-',
                'mp_blocks':
                '-',
                'mp_url':
                url,
                'error':
                'Mempool.space seems to be unavailable. Maybe node is still synching.'
            })
        mp_blocks = tor_request(url + 'api/blocks').json()

        return json.dumps({
            'mp_fee': mp_fee,
            'mp_blocks': mp_blocks,
            'mp_url': url,
            'error': None
        })

    except Exception as e:
        if url is None:
            url = 'Could not find url'
        return json.dumps({
            'mp_fee': '-',
            'mp_blocks': '-',
            'mp_url': url,
            'error': f'Error: {e}'
        })


@api.route("/portfolio_compare_json", methods=["GET"])
@login_required
# Compare portfolio performance to a list of assets
# Takes arguments:
# tickers  - (comma separated. ex: BTC,ETH,AAPL)
# start    - start date in the format YYMMDD
# end      - end date in the format YYMMDD
# method   - "chart": returns NAV only data for charts
#          - "all": returns all data (prices and NAV)
#          - "meta": returns metadata information
def portfolio_compare_json():
    if request.method == "GET":
        tickers = request.args.get("tickers").upper()
        tickers = tickers.split(",")
        start_date = request.args.get("start")
        method = request.args.get("method")

        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"[portfolio_compare_json] Error: {e}, " +
                         "setting start_date to zero")
            start_date = datetime.strptime('2011-01-01', "%Y-%m-%d")

        end_date = request.args.get("end")

        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"[portfolio_compare_json] Error: {e}, " +
                         "setting end_date to now")
            end_date = datetime.now()
    data = {}

    logging.info("[portfolio_compare_json] NAV requested in list of " +
                 "tickers, requesting generatenav.")
    nav = generatenav()
    nav_only = nav["NAV_fx"]

    # Now go over tickers and merge into nav_only df
    messages = {}
    meta_data = {}
    fx = current_app.settings['PORTFOLIO']['base_fx']
    if fx is None:
        fx = 'USD'
    for ticker in tickers:
        if ticker == "NAV":
            # Ticker was NAV, skipped
            continue
        # Generate price Table now for the ticker and trim to match portfolio
        data = historical_prices(ticker, fx=fx)
        data.index = data.index.astype('datetime64[ns]')
        # If notification is an error, skip this ticker
        if data is None:
            messages = data.errors
            return jsonify(messages)
        data = data.rename(columns={'close_converted': ticker + '_price'})
        data = data[ticker + '_price']
        nav_only = pd.merge(nav_only, data, on="date", how="left")
        nav_only[ticker + "_price"].fillna(method="bfill", inplace=True)
        messages[ticker] = "ok"
        logging.info(f"[portfolio_compare_json] {ticker}: Success - Merged OK")

    nav_only.fillna(method="ffill", inplace=True)
    # Trim this list only to start_date to end_date:
    mask = (nav_only.index >= start_date) & (nav_only.index <= end_date)
    nav_only = nav_only.loc[mask]

    # Now create the list of normalized Returns for the available period
    # Plus create a table with individual analysis for each ticker and NAV
    nav_only["NAV_norm"] = (nav_only["NAV_fx"] / nav_only["NAV_fx"][0]) * 100
    nav_only["NAV_ret"] = nav_only["NAV_norm"].pct_change()

    table = {}
    table["meta"] = {}
    table["meta"]["start_date"] = nav_only.index[0].strftime("%m-%d-%Y")
    table["meta"]["end_date"] = nav_only.index[-1].strftime("%m-%d-%Y")
    table["meta"]["number_of_days"] = ((nav_only.index[-1] -
                                        nav_only.index[0])).days
    table["meta"]["count_of_points"] = nav_only["NAV_fx"].count().astype(float)
    table["NAV"] = {}
    table["NAV"]["start"] = nav_only["NAV_fx"][0]
    table["NAV"]["end"] = nav_only["NAV_fx"][-1]
    table["NAV"]["return"] = (nav_only["NAV_fx"][-1] /
                              nav_only["NAV_fx"][0]) - 1
    table["NAV"]["avg_return"] = nav_only["NAV_ret"].mean()
    table["NAV"]["ann_std_dev"] = nav_only["NAV_ret"].std() * math.sqrt(365)
    for ticker in tickers:
        if messages[ticker] == "ok":
            # Include new columns for return and normalized data
            nav_only[ticker + "_norm"] = (nav_only[ticker + "_price"] /
                                          nav_only[ticker + "_price"][0]) * 100
            nav_only[ticker + "_ret"] = nav_only[ticker + "_norm"].pct_change()
            # Create Metadata
            table[ticker] = {}
            table[ticker]["start"] = nav_only[ticker + "_price"][0]
            table[ticker]["end"] = nav_only[ticker + "_price"][-1]
            table[ticker]["return"] = (nav_only[ticker + "_price"][-1] /
                                       nav_only[ticker + "_price"][0]) - 1
            table[ticker]["comp2nav"] = table[ticker]["return"] - \
                table["NAV"]["return"]
            table[ticker]["avg_return"] = nav_only[ticker + "_ret"].mean()
            table[ticker]["ann_std_dev"] = nav_only[
                ticker + "_ret"].std() * math.sqrt(365)

    logging.info("[portfolio_compare_json] Success")

    # Create Correlation Matrix
    filter_col = [col for col in nav_only if col.endswith("_ret")]
    nav_matrix = nav_only[filter_col]
    corr_matrix = nav_matrix.corr(method="pearson").round(2)
    corr_html = corr_matrix.to_html(classes="table small text-center",
                                    border=0,
                                    justify="center")

    # Now, let's return the data in the correct format as requested
    if method == "chart":
        return_data = {
            "data": nav_only.to_json(),
            "messages": messages,
            "meta_data": meta_data,
            "table": table,
            "corr_html": corr_html,
        }
        return jsonify(return_data)

    return nav_only.to_json()


@api.route('/log')
@login_required
def progress_log():
    lines = request.args.get("lines")
    if lines is not None:
        try:
            lines = int(lines)
        except Exception:
            lines = 200
    else:
        lines = 200
    from config import Config
    from backend.warden_modules import tail
    debug = Config.debug_file
    data = tail(debug, lines)
    # Filter if needed
    level = request.args.get("level")
    tmp = ""
    if level is not None:
        for item in str(data).split("\n"):
            if level in item:
                tmp += item + "\n"
        data = tmp

    return json.dumps(str(data))


@api.route('/broadcaster')
@login_required
def broadcaster():
    category = request.args.get("category")
    if category == 'None':
        category = None
    return current_app.message_handler.to_json(category=category)


@api.route("/assetlist", methods=["GET", "POST"])
# List of available tickers. Also takes argument {term} so this can be used
# in autocomplete forms
def assetlist():
    q = request.args.get("term")
    jsonlist = []
    if len(q) < 2:
        return jsonify(jsonlist)
    # Get list of available tickers from pricing APIs
    from pricing_engine.alphavantage import asset_list
    jsonlist.extend(asset_list(q))
    # jsonlist.extend(asset_list_cc(q))
    # jsonlist.extend(asset_list_fp(q))

    return jsonify(jsonlist)


@api.route("/aclst", methods=["GET", "POST"])
@login_required
# Returns JSON for autocomplete on account names.
# Gathers account names from trades and account_info tables
# Takes on input ?term - which is the string to be found
def aclst():
    list = []
    if request.method == "GET":

        tradeaccounts = Trades.query.filter_by(
            user_id=current_user.username).group_by(Trades.trade_account)

        accounts = AccountInfo.query.filter_by(
            user_id=current_user.username).group_by(
                AccountInfo.account_longname)

        q = request.args.get("term")
        for item in tradeaccounts:
            if q.upper() in item.trade_account.upper():
                list.append(item.trade_account)
        for item in accounts:
            if q.upper() in item.account_longname.upper():
                list.append(item.account_longname)

        list = json.dumps(list)

        return list


@api.route("/portfolio_tickers_json", methods=["GET", "POST"])
@login_required
# Returns a list of all tickers ever traded in this portfolio
def portfolio_tickers_json():
    if request.method == "GET":
        df = pd.read_sql_table("trades", current_app.db.engine)
        df = df[(df.user_id == current_user.username)]
        list_of_tickers = df.trade_asset_ticker.unique().tolist()
        if ('BTC' not in list_of_tickers):
            list_of_tickers.append('BTC')
        return jsonify(list_of_tickers)


@api.route("/generatenav_json", methods=["GET", "POST"])
@login_required
# Creates a table with dates and NAV values
# Takes 2 arguments:
# force=False (default) : Forces the NAV generation without reading saved file
# filter=None (default): Filter to be applied to Pandas df (df.query(filter))
def generatenav_json():
    if request.method == "GET":
        filter = request.args.get("filter")
        force = request.args.get("force")
        if not filter:
            filter = ""
        if not force:
            force = False
        nav = generatenav(current_user.username, force, filter)
        return nav.to_json()


# Return the list of hosts found + the ones at standard list
# Also used to include new hosts or delete old ones


@api.route("/host_list", methods=["GET", "POST"])
@login_required
def host_list():
    services = pickle_it('load', 'services_found.pkl')
    hosts = pickle_it('load', 'hosts_found.pkl')
    if request.method == "GET":
        delete = request.args.get("delete")
        if delete is not None:
            try:
                del services[delete]
            except Exception:
                pass
            try:
                host = delete.strip("http://")
                host = host.strip("https://")
                host = host.strip("/")
                if ':' in host:
                    host = host.split(":")[0]
                for key, item in hosts.items():
                    if item['host'] == host:
                        del hosts[key]
                        break

            except Exception:
                pass

            pickle_it('save', 'services_found.pkl', services)
            pickle_it('save', 'hosts_found.pkl', hosts)
            return redirect(url_for("warden.running_services"))

        return (json.dumps(hosts))
    if request.method == "POST":
        url = request.form.get("new_url")
        url = url_parser(url)
        hosts[url] = {'ip': url, 'host': url, 'last_time': None}

        pickle_it('save', 'hosts_found.pkl', hosts)

        try:
            if not '.onion' in url:
                host_ip = socket.gethostbyname(url)
            else:
                host_ip = url
            services[host_ip] = {
                'url': url,
                'status': 'Loading...',
                'port': None,
                'service': 'Checking Status'
            }
            pickle_it('save', 'services_found.pkl', services)

        except Exception:
            pass

        return redirect(url_for("warden.running_services"))


@api.route("/drawdown_json", methods=["GET"])
@login_required
# Return the largest drawdowns in a time period
# Takes arguments:
# ticker:       Single ticker for filter (default = NAV)
# start_date:   If none, defaults to all available
# end_date:     If none, defaults to today
# n_dd:         Top n drawdowns to be calculated
# chart:        Boolean - return data for chart
def drawdown_json():
    # Get the arguments and store
    if request.method == "GET":
        start_date = request.args.get("start")
        ticker = request.args.get("ticker")
        n_dd = request.args.get("n_dd")
        chart = request.args.get("chart")
        if not ticker:
            ticker = "NAV"
        ticker = ticker.upper()
        if n_dd:
            try:
                n_dd = int(n_dd)
            except TypeError:
                n_dd = 2
        if not n_dd:
            n_dd = 2
        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"Warning: {e}, " + "setting start_date to zero")
            start_date = datetime(2000, 1, 1)

        end_date = request.args.get("end")
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"Warning: {e}, " + "setting end_date to now")
            end_date = datetime.now()

    # Create a df with either NAV or ticker prices
    if ticker == "NAV":
        data = generatenav(current_user.username)
        data = data[["NAV_fx"]]
        data = data.rename(columns={'NAV_fx': 'close'})
    else:
        # Get price of ticker passed as argument
        data = price_data_fx(ticker)
        # If notification is an error, skip this ticker
        if data is None:
            messages = data.errors
            return jsonify(messages)
        data = data.rename(columns={'close_converted': ticker + '_price'})
        data = data[[ticker + '_price']]
        data = data.astype(float)
        data.sort_index(ascending=True, inplace=True)
        data = data.rename(columns={ticker + '_price': 'close'})
    # Trim the df only to start_date to end_date:
    mask = (data.index >= start_date) & (data.index <= end_date)
    data = data.loc[mask]
    # # Calculate drawdowns
    # df = 100 * (1 + data / 100).cumprod()

    df = pd.DataFrame()
    df["close"] = data['close']
    df["ret"] = df.close / df.close[0]
    df["modMax"] = df.ret.cummax()
    df["modDD"] = (df.ret / df["modMax"]) - 1
    # Starting date of the currency modMax
    df["end_date"] = df.index
    # is this the first occurence of this modMax?
    df["dup"] = df.duplicated(["modMax"])

    # Now, exclude the drawdowns that have overlapping data, keep only highest
    df_group = df.groupby(["modMax"]).min().sort_values(by="modDD",
                                                        ascending=True)
    # Trim to fit n_dd
    df_group = df_group.head(n_dd)
    # Format a dict for return
    return_list = []
    for index, row in df_group.iterrows():
        # access data using column names
        tmp_dict = {}
        tmp_dict["dd"] = row["modDD"]
        tmp_dict["start_date"] = row["end_date"].strftime("%Y-%m-%d")
        tmp_dict["end_value"] = row["close"]
        tmp_dict["recovery_date"] = (
            df[df.modMax == index].tail(1).end_date[0].strftime("%Y-%m-%d"))
        tmp_dict["end_date"] = (df[df.close == row["close"]].tail(
            1).end_date[0].strftime("%Y-%m-%d"))
        tmp_dict["start_value"] = df[df.index == row["end_date"]].tail(
            1).close[0]
        tmp_dict["days_to_recovery"] = (
            df[df.modMax == index].tail(1).end_date[0] - row["end_date"]).days
        tmp_dict["days_to_bottom"] = (
            df[df.close == row["close"]].tail(1).end_date[0] -
            row["end_date"]).days
        tmp_dict["days_bottom_to_recovery"] = (
            df[df.modMax == index].tail(1).end_date[0] -
            df[df.close == row["close"]].tail(1).end_date[0]).days
        return_list.append(tmp_dict)

    if chart:
        start_date = data.index.min()
        total_days = (end_date - start_date).days
        # dates need to be in Epoch time for Highcharts
        data.index = (data.index - datetime(1970, 1, 1)).total_seconds()
        data.index = data.index * 1000
        data.index = data.index.astype(np.int64)
        data = data.to_dict()
        # Generate the flags for the chart
        # {
        #         x: 1500076800000,
        #         title: 'TEST',
        #         text: 'TEST text'
        # }
        flags = []
        plot_bands = []
        # Create a dict for flags and plotBands on chart
        total_recovery_days = 0
        total_drawdown_days = 0
        for item in return_list:
            # First the start date for all dd
            tmp_dict = {}
            start_date = datetime.strptime(item["start_date"], "%Y-%m-%d")
            start_date = (start_date -
                          datetime(1970, 1, 1)).total_seconds() * 1000
            tmp_dict["x"] = start_date
            tmp_dict["title"] = "TOP"
            tmp_dict["text"] = "Start of drawdown"
            flags.append(tmp_dict)
            # Now the bottom for all dd
            tmp_dict = {}
            end_date = datetime.strptime(item["end_date"], "%Y-%m-%d")
            end_date = (end_date - datetime(1970, 1, 1)).total_seconds() * 1000
            tmp_dict["x"] = end_date
            tmp_dict["title"] = "BOTTOM"
            tmp_dict["text"] = "Bottom of drawdown"
            flags.append(tmp_dict)
            # Now the bottom for all dd
            tmp_dict = {}
            recovery_date = datetime.strptime(item["recovery_date"],
                                              "%Y-%m-%d")
            recovery_date = (recovery_date -
                             datetime(1970, 1, 1)).total_seconds() * 1000
            tmp_dict["x"] = recovery_date
            tmp_dict["title"] = "RECOVERED"
            tmp_dict["text"] = "End of drawdown Cycle"
            flags.append(tmp_dict)
            # Now create the plot bands
            drop_days = (end_date - start_date) / 1000 / 60 / 60 / 24
            recovery_days = (recovery_date - end_date) / 1000 / 60 / 60 / 24
            total_drawdown_days += round(drop_days, 0)
            total_recovery_days += round(recovery_days, 0)
            tmp_dict = {}
            tmp_dict["label"] = {}
            tmp_dict["label"]["align"] = "center"
            tmp_dict["label"]["textAlign"] = "left"
            tmp_dict["label"]["rotation"] = 90
            tmp_dict["label"]["text"] = "Lasted " + \
                str(round(drop_days, 0)) + " days"
            tmp_dict["label"]["style"] = {}
            tmp_dict["label"]["style"]["color"] = "white"
            tmp_dict["label"]["style"]["fontWeight"] = "bold"
            tmp_dict["color"] = "#E6A68E"
            tmp_dict["from"] = start_date
            tmp_dict["to"] = end_date
            plot_bands.append(tmp_dict)
            tmp_dict = {}
            tmp_dict["label"] = {}
            tmp_dict["label"]["rotation"] = 90
            tmp_dict["label"]["align"] = "center"
            tmp_dict["label"]["textAlign"] = "left"
            tmp_dict["label"]["text"] = ("Lasted " +
                                         str(round(recovery_days, 0)) +
                                         " days")
            tmp_dict["label"]["style"] = {}
            tmp_dict["label"]["style"]["color"] = "white"
            tmp_dict["label"]["style"]["fontWeight"] = "bold"
            tmp_dict["color"] = "#8CADE1"
            tmp_dict["from"] = end_date
            tmp_dict["to"] = recovery_date
            plot_bands.append(tmp_dict)

        return jsonify({
            "chart_data": data['close'],
            "messages": "OK",
            "chart_flags": flags,
            "plot_bands": plot_bands,
            "days": {
                "recovery": total_recovery_days,
                "drawdown": total_drawdown_days,
                "trending":
                total_days - total_drawdown_days - total_recovery_days,
                "non_trending": total_drawdown_days + total_recovery_days,
                "total": total_days,
            },
        })

    return simplejson.dumps(return_list)
