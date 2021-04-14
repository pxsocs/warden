from datetime import datetime
import requests
from pricing_engine.engine import apikey
from connections import tor_request
import pandas as pd
from warden_decorators import MWT

# Docs
# https://min-api.cryptocompare.com/documentation

api = apikey('cryptocompare', False)


@MWT(timeout=10)
def realtime(ticker, fxs='USD', parsed=True):
    '''
    Gets realtime prices using CryptoCompare
    Only Cryptocurrencies are accepted

    Result:
    {'BTC': 0.03041, 'USD': 1354.75, 'GBP': 975.18}

    :param str ticker: Ticker or Symbol
    :param str fxs: a string of a single currency or comma separated currencies. ex: 'USD' or 'USD,EUR'
    :return: Realtime price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''
    # Request data
    globalURL = 'https://min-api.cryptocompare.com/data/price?fsym=' + ticker
    globalURL += '&tsyms=' + fxs

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()

    # PARSED DATA only returns the first FX
    if parsed:
        try:
            fx = fxs.split(',')[0]
            result = {
                'symbol': ticker,
                'name': None,
                'price': data[fx],
                'fx': fx,
                'time': datetime.utcnow(),
                'timezone': 'utc',
                'source': 'cryptocompare'
            }
            return result
        except Exception:
            return None

    return data


def historical(ticker, fx='USD', parsed=True):
    '''
    Gets historical prices using CryptoCompare
    Only Cryptocurrencies are accepted

    Result:
    {
        "Response": "Success",
        "Message": "",
        "HasWarning": false,
        "Type": 100,
        "RateLimit": {

        },
        "Data": {
            "Aggregated": false,
            "TimeFrom": 1613606400,
            "TimeTo": 1614470400,
            "Data": [
            {
                "time": 1613606400,
                "high": 52550.6,
                "low": 50874.81,
                "open": 52154.91,
                "volumefrom": 42530.26,
                "volumeto": 2205232619.94,
                "close": 51591.61,
                "conversionType": "direct",
                "conversionSymbol": ""
            },...

    :param str ticker: Ticker or Symbol
    :param str fx: a string of a single currency
    :return: Historical price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''
    globalURL = 'https://min-api.cryptocompare.com/data/v2/histoday?fsym=' + ticker
    globalURL += '&tsym=' + fx
    globalURL += '&limit=2000'

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()['Data']

    if parsed:
        try:
            df = pd.DataFrame.from_dict(data['Data'])
            df = df.rename(columns={'time': 'date'})
            df['date'] = pd.to_datetime(df['date'], unit='s')
            df.set_index('date', inplace=True)
            df_save = df[['close', 'open', 'high', 'low']]
            # If the dataframe only has zeros as close, return an empty df
            if df['close'].sum() == 0:
                raise Exception
        except Exception:
            df_save = pd.DataFrame()
        return (df_save)

    return data


def asset_list(term=None):
    master_list = []
    try:
        url = 'https://min-api.cryptocompare.com/data/all/coinlist'
        result = tor_request(url).json()
        result = result['Data']
        for key, value in result.items():
            if term.upper() in value['Symbol'].upper() or term.upper() in value['FullName'].upper().upper():
                master_list.append(
                    {
                        'symbol': value['Symbol'],
                        'name': value['FullName'],
                        'provider': 'cc_digital'
                    }
                )
    except Exception:
        pass

    return (master_list)


# For Tables that need multiple prices at the same time, it's quicker to get
# a single price request
# This will attempt to get all prices from cryptocompare api and return a single df
# If a price for a security is not found, other rt providers will be used.
def multiple_price_grab(tickers, fx):
    # tickers should be in comma sep string format like "BTC,ETH,LTC"
    baseURL = \
        "https://min-api.cryptocompare.com/data/pricemultifull?fsyms="\
        + tickers + "&tsyms=" + fx + "&&api_key=" + api
    try:
        request = tor_request(baseURL)
    except requests.exceptions.ConnectionError:
        return ("ConnectionError")
    try:
        data = request.json()
    except AttributeError:
        data = "ConnectionError"
    return (data)
