from datetime import datetime
from pathlib import Path
import requests
import os
from pricing_engine.engine import apikey
from connections import tor_request
import pandas as pd

# docs
# https://www.alphavantage.co/documentation/

api = apikey('alphavantage', True)


def realtime(ticker, fx='USD', function='CURRENCY_EXCHANGE_RATE', parsed=True):
    if function == 'CURRENCY_EXCHANGE_RATE':
        # Request data
        globalURL = 'https://www.alphavantage.co/query?function=' + function
        globalURL += '&from_currency=' + ticker
        globalURL += '&to_currency=' + fx
        globalURL += '&apikey=' + api

        # No need for any API calls to return 1 :)
        if ticker == fx:
            return (
                {'Realtime Currency Exchange Rate':
                 {'1. From_Currency Code': ticker,
                  '2. From_Currency Name': ticker,
                  '3. To_Currency Code': fx,
                  '4. To_Currency Name': fx,
                  '5. Exchange Rate': '1',
                  '6. Last Refreshed': datetime.utcnow(),
                  '7. Time Zone': 'UTC',
                  '8. Bid Price': '1',
                  '9. Ask Price': '1'}}
            )

        # SAMPLE RETURN DATA
        # {'Realtime Currency Exchange Rate':
        #   {'1. From_Currency Code': 'BTC',
        #   '2. From_Currency Name': 'Bitcoin',
        #   '3. To_Currency Code': 'USD',
        #   '4. To_Currency Name': 'United States Dollar',
        #   '5. Exchange Rate': '44541.42000000',
        #   '6. Last Refreshed': '2021-02-28 13:07:01',
        #   '7. Time Zone': 'UTC',
        #   '8. Bid Price': '44541.42000000',
        #   '9. Ask Price': '44541.43000000'}}

    if function == 'GLOBAL_QUOTE':
        globalURL = 'https://www.alphavantage.co/query?function=' + function
        globalURL += '&symbol=' + ticker
        globalURL += '&apikey=' + api

        # SAMPLE RETURN DATA
        # {'Global Quote':
        #   {'01. symbol': 'GBTC',
        #   '02. open': '43.7000',
        #   '03. high': '45.6000',
        #   '04. low': '40.8000',
        #   '05. price': '43.2000',
        #   '06. volume': '21947497',
        #   '07. latest trading day': '2021-02-26',
        #   '08. previous close': '48.4000',
        #   '09. change': '-5.2000',
        #   '10. change percent': '-10.7438%'
        #   }
        # }

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()

    # Parse the data so it's in the standard format for realtime data
    # {
    #   'symbol':
    #   'price':
    #   'fx' :
    #   'time':
    #   'timezone':
    # }
    if parsed:
        try:
            if function == 'CURRENCY_EXCHANGE_RATE':
                result = {
                    'symbol': ticker,
                    'name': data['2. From_Currency Name'],
                    'price': data['5. Exchange Rate'],
                    'fx': fx,
                    'time': data['6. Last Refreshed'],
                    'timezone': data['7. Time Zone'],
                    'source': 'alphavantage'
                }
                return result
            if function == 'GLOBAL_QUOTE':
                result = {
                    'symbol': ticker,
                    'name': None,
                    'price': data['Global Quote']['05. price'],
                    'high': data['Global Quote']['03. high'],
                    'open': data['Global Quote']['02. open'],
                    'chg': data['Global Quote']['10. change percent'],
                    'volume': data['Global Quote']['06. volume'],
                    'fx': 'USD',
                    'time': data['Global Quote']['07. latest trading day'],
                    'timezone': 'US/Eastern',
                    'source': 'Alphavantage Stocks'
                }
                return result
        except Exception:
            return None

    return data


def historical(ticker, function='TIME_SERIES_DAILY_ADJUSTED', fx='USD', parsed=True):
    if function == 'TIME_SERIES_DAILY_ADJUSTED':
        globalURL = 'https://www.alphavantage.co/query?function=' + function
        globalURL += '&symbol=' + ticker
        globalURL += '&outputsize=full&apikey=' + api

        # Sample Result
        #   "Meta Data": {
        #     "1. Information": "Daily Prices (open, high, low, close) and Volumes",
        #     "2. Symbol": "IBM",
        #     "3. Last Refreshed": "2021-02-26",
        #     "4. Output Size": "Compact",
        #     "5. Time Zone": "US/Eastern"
        #   },
        #   "Time Series (Daily)": {
        #     "2021-02-26": {
        #       "1. open": "122.2500",
        #       "2. high": "122.2500",
        #       "3. low": "118.8800",
        #       "4. close": "118.9300",
        #       "5. volume": "8868848"
        #     },

    if function == 'DIGITAL_CURRENCY_DAILY':
        globalURL = 'https://www.alphavantage.co/query?function=' + function
        globalURL += '&symbol=' + ticker
        globalURL += '&market=' + fx
        globalURL += '&apikey=' + api

        # Sample Result
        #  {
        # "Meta Data": {
        #     "1. Information": "Daily Prices and Volumes for Digital Currency",
        #     "2. Digital Currency Code": "BTC",
        #     "3. Digital Currency Name": "Bitcoin",
        #     "4. Market Code": "CNY",
        #     "5. Market Name": "Chinese Yuan",
        #     "6. Last Refreshed": "2021-02-28 00:00:00",
        #     "7. Time Zone": "UTC"
        # },
        # "Time Series (Digital Currency Daily)": {
        #     "2021-02-28": {
        #         "1a. open (CNY)": "298429.05591000",
        #         "1b. open (USD)": "46103.67000000",
        #         "2a. high (CNY)": "301526.96898000",
        #         "2b. high (USD)": "46582.26000000",
        #         "3a. low (CNY)": "295091.83603000",
        #         "3b. low (USD)": "45588.11000000",
        #         "4a. close (CNY)": "298880.48293000",
        #         "4b. close (USD)": "46173.41000000",
        #         "5. volume": "2680.54607000",
        #         "6. market cap (USD)": "2680.54607000"

    if function == 'FX_DAILY':
        globalURL = 'https://www.alphavantage.co/query?function=' + function
        globalURL += '&from_symbol=' + ticker
        globalURL += '&to_symbol=' + fx
        globalURL += '&market=' + fx
        globalURL += '&outputsize=full&apikey=' + api

        # Sample Result
        # {
        # "Meta Data": {
        #     "1. Information": "Forex Daily Prices (open, high, low, close)",
        #     "2. From Symbol": "EUR",
        #     "3. To Symbol": "USD",
        #     "4. Output Size": "Full size",
        #     "5. Last Refreshed": "2021-02-26 21:55:00",
        #     "6. Time Zone": "UTC"
        # },
        # "Time Series FX (Daily)": {
        #     "2021-02-26": {
        #         "1. open": "1.2159",
        #         "2. high": "1.2183",
        #         "3. low": "1.2060",
        #         "4. close": "1.2072"
        #     },

    response = tor_request(url=globalURL)
    if response.status_code == 403:
        response = requests.get(globalURL)

    data = response.json()

    if parsed:
        if function == 'DIGITAL_CURRENCY_DAILY':
            try:
                if 'Time Series (Digital Currency Daily)' in data:
                    df = pd.DataFrame.from_dict(
                        data['Time Series (Digital Currency Daily)'],
                        orient="index")
                if 'Time Series FX (Daily)' in data:
                    df = pd.DataFrame.from_dict(
                        data['Time Series FX (Daily)'],
                        orient="index")

                # Clean columns
                for i in range(0, 7):
                    for string in ['a', 'b', 'c', 'd', 'e', 'f']:
                        df.columns = df.columns.str.replace(f'{i}{string}. ', '')

                df = df.rename(
                    columns={
                        'close (USD)': 'close',
                        'open (USD)': 'open',
                        'high (USD)': 'high',
                        'low (USD)': 'low'
                    })
                df_save = df[['close', 'open', 'high', 'low']]
                df_save.index.names = ['date']
            except Exception:
                df_save = pd.DataFrame()
            return (df_save)

        if function == 'TIME_SERIES_DAILY_ADJUSTED' or function == 'FX_DAILY':
            try:
                if 'Time Series FX (Daily)' in data:
                    df = pd.DataFrame.from_dict(data['Time Series FX (Daily)'],
                                                orient="index")
                if 'Time Series (Daily)' in data:
                    df = pd.DataFrame.from_dict(data['Time Series (Daily)'],
                                                orient="index")

                df = df.rename(
                    columns={
                        '4. close': 'close',
                        '1. open': 'open',
                        '2. high': 'high',
                        '3. low': 'low'
                    })
                df_save = df[['close', 'open', 'high', 'low']]
                df_save.index.names = ['date']
            except Exception:
                df_save = pd.DataFrame()
            return (df_save)

    return data


def asset_list(term=None):
    import csv
    basedir = os.path.abspath(os.path.dirname(__file__))
    master_list = []
    if term is None:
        term = ""
    # Alphavantage Currency List - CSV
    filename = os.path.join(basedir, 'static/csv_files/physical_currency_list.csv')
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if term.upper() in row[0].upper() or term in row[1].upper():
                master_list.append(
                    {
                        'symbol': row[0],
                        'name': row[1],
                        'provider': 'aa_fx'
                    }
                )
    # Alphavantage Digital Currency list
    filename = os.path.join(basedir, 'static/csv_files/digital_currency_list.csv')
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if term.upper() in row[0].upper() or term.upper() in row[1].upper():
                master_list.append(
                    {
                        'symbol': row[0],
                        'name': row[1],
                        'provider': 'aa_digital'
                    }
                )
    # Alphavantage Stock Search EndPoint
    try:
        url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH'
        url += '&keywords=' + term
        url += '&apikey=' + api
        result = requests.get(url).json()
        result = result['bestMatches']
        for element in result:
            master_list.append(
                {
                    'symbol': element['1. symbol'],
                    'name': element['2. name'],
                    'provider': 'aa_stock',
                    'notes': element['3. type'] + ' ' + element['4. region'],
                    'fx': element['8. currency']
                }
            )
    except Exception:
        pass
    return (master_list)
