from datetime import datetime
import requests
from pricing_engine.engine import apikey
from connections.connections import tor_request
import pandas as pd
from backend.decorators import MWT

# Docs
# https://twelvedata.com/docs

api = apikey('twelvedata', True)

# TWELVEDATA API is super limited so all requests here are cached for 60 seconds
# to avoid blowing up the API


@MWT(timeout=60)
def realtime(ticker, parsed=True):
    '''
    Gets realtime prices using TwelveData
    Only Stocks are accepted

    Result:
    {
        "symbol": "GBTC",
        "name": "Grayscale Bitcoin Trust (BTC)",
        "exchange": "OTC",
        "currency": "USD",
        "datetime": "2021-03-01",
        "open": "46.18000",
        "high": "47.07000",
        "low": "45.70000",
        "close": "46.20000",
        "volume": "7298247",
        "previous_close": "43.20000",
        "change": "3.00000",
        "percent_change": "6.94444",
        "average_volume": "16354631",
        "fifty_two_week": {
            "low": "5.01000",
            "high": "58.22000",
            "low_change": "41.19000",
            "high_change": "-12.02000",
            "low_change_percent": "822.15566",
            "high_change_percent": "-20.64583",
            "range": "5.010000 - 58.220001"
            }
    }

    :param str ticker: Ticker or Symbol
    :return: Realtime price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''
    # Request data
    globalURL = 'https://api.twelvedata.com/quote?symbol=' + ticker
    globalURL += '&apikey=' + api

    response = requests.get(globalURL)

    data = response.json()

    if parsed:
        try:
            result = {
                'symbol': data['symbol'],
                'name': data['name'],
                'price': data['close'],
                'fx': data['currency'],
                'time': data['datetime'],
                'chg': data['percent_change'],
                'timezone': None,
                'source': 'TwelveData'
            }
            return result
        except Exception:
            return None

    return data


@MWT(timeout=60)
def historical(ticker, parsed=True):
    '''
    Gets historical prices using 12D
    Only Stocks are accepted

    Result:
    {
   "meta":{
      "symbol": "AAPL",
      "interval": "1min",
      "currency": "USD",
      "exchange_timezone": "America/New_York",
      "exchange": "NASDAQ",
      "type": "Common Stock"
   },
   "values":[
      {
         "datetime":"2019-08-09 15:59:00",
         "open":"200.93999",
         "high":"201.25599",
         "low":"200.85199",
         "close":"201.05000",
         "volume":"472287"},...
         ]

    :param str ticker: Ticker or Symbol
    :return: Historical price data
    :raises Exception: if Tor request returns a 403 (not authorized)
    '''

    globalURL = 'https://api.twelvedata.com/time_series?symbol=' + ticker
    globalURL += '&interval=1day&outputsize=5000&apikey=' + api

    response = requests.get(globalURL)

    data = response.json()

    if parsed:
        try:
            df = pd.DataFrame.from_records(data['values'])
            df = df.rename(columns={'datetime': 'date'})
            df.set_index('date', inplace=True)
            df_save = df[['close', 'open', 'high', 'low', 'volume']]
        except Exception:
            df_save = pd.DataFrame()
        return (df_save)

    return data


@MWT(timeout=60)
def asset_list(term=None):
    master_list = []
    try:
        url = f'https://api.twelvedata.com/symbol_search?symbol={term}'
        result = requests.get(url).json()
        for item in result['data']:
            master_list.append({
                'symbol': item['symbol'],
                'name': item['instrument_name'],
                'provider': '12Data',
                'notes': item['exchange'],
                'fx': item['currency']
            })
    except Exception:
        pass

    return (master_list)
