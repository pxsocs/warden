from datetime import datetime
import requests
from pricing_engine.engine import apikey
from connections import tor_request
import pandas as pd

# Docs
# https://financialmodelingprep.com/developer/docs/#Stock-Price

api = apikey('fmp', True)


def realtime(ticker, parsed=True):
    '''
    Gets realtime prices using FMP
    Only Stocks are accepted

    Result:
    [
        {
            "symbol": "AAPL",
            "price": 121.26000000,
            "volume": 164560045
        }
    ]

    Limit reached Message:
    {'Error Message':
    'Limit Reach . Please upgrade your plan or
    visit our documentation for more details at
    https://financialmodelingprep.com/developer/docs/pricing'}

    :param str ticker: Ticker or Symbol
    :return: Realtime price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''
    # Request data
    globalURL = 'https://financialmodelingprep.com/api/v3/quote-short/' + ticker
    globalURL += '?apikey=' + api

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()

    if parsed:
        try:
            result = {
                'symbol': data[0]['symbol'],
                'name': None,
                'price': data[0]['price'],
                'fx': 'USD',
                'time': datetime.utcnow(),
                'timezone': 'utc',
                'source': 'fmp'
            }
            return result
        except Exception:
            return None

    return data


def historical(ticker, parsed=True):
    '''
    Gets historical prices using FMP
    Only Stocks are accepted

    Result:
    {
        "symbol" : "AAPL",
        "historical" : [ {
            "date" : "2021-02-26",
            "open" : 122.589996,
            "high" : 124.849998,
            "low" : 121.199997,
            "close" : 121.260002,
            "adjClose" : 121.260002,
            "volume" : 1.6432E8,
            "unadjustedVolume" : 1.6432E8,
            "change" : -1.32999,
            "changePercent" : -1.085,
            "vwap" : 122.43667,
            "label" : "February 26, 21",
            "changeOverTime" : -0.01085
        }, {...}, ...],
    }

    API Limit result:
    {
        "Error Message":
        "Limit Reach . Please upgrade your plan or
        visit our documentation for more details at
        https://financialmodelingprep.com/developer/docs/pricing "
    }

    :param str ticker: Ticker or Symbol
    :return: Historical price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''
    globalURL = 'https://financialmodelingprep.com/api/v3/historical-price-full/' + ticker
    globalURL += '?apikey=' + api

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()

    if parsed:
        try:
            df = pd.DataFrame.from_records(data['historical'])
            df = df.rename(
                columns={
                    'close': 'close',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'volume': 'volume'
                })
            df.set_index('date', inplace=True)
            df_save = df[['close', 'open', 'high', 'low', 'volume']]
        except Exception:
            df_save = pd.DataFrame()
        return (df_save)

    return data


def asset_list(term=None):
    master_list = []
    try:
        url = f'https://financialmodelingprep.com/api/v3/search?query={term}&limit=10&apikey=d44fb36a0c62da8ff9b1b40b47802000'
        result = tor_request(url).json()
        for item in result:
            master_list.append(
                {
                    'symbol': item['symbol'],
                    'name': item['name'],
                    'provider': 'fp_stock',
                    'notes': item['exchangeShortName'],
                    'fx': item['currency']
                }
            )
    except Exception:
        pass

    return (master_list)
