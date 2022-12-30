from datetime import datetime
import requests
import os
from connections.connections import tor_request
from backend.decorators import timeout
import pandas as pd
from backend.decorators import MWT
import yfinance as yf
# docs
# https://pypi.org/project/yfinance/


@MWT(timeout=10)
def realtime(ticker, fx='USD', function=None, parsed=True):
    data = yf.Ticker(ticker)
    # Get latest price
    df = data.history(period='day')
    # SAMPLE RETURN DATA (Pandas DF)
    # Date Open        High         Low       Close   Volume  Dividends  Stock Splits
    # 2022-08-24  275.410004  277.209991  275.179993  275.640015  9802911          0             0

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
            result = {
                'symbol': ticker,
                'name': data.info['shortName'],
                'price': df['Close'][0],
                'fx': 'USD',
                'time': datetime.utcnow(),
                'timezone': 'utc',
                'source': 'Yahoo Finance'
            }
            return result
        except Exception:
            return None

    return df


def historical(ticker,
               function='TIME_SERIES_DAILY_ADJUSTED',
               fx='USD',
               parsed=True):

    data = yf.Ticker(ticker)
    # Get latest price
    df = data.history(period='max')
    # SAMPLE RETURN DATA (Pandas DF)
    # Date Open        High         Low       Close   Volume  Dividends  Stock Splits
    # 2022-08-24  275.410004  277.209991  275.179993  275.640015  9802911          0             0

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
            df = df.rename(columns={
                'Close': 'close',
                'Open': 'open',
                'High': 'high',
                'Low': 'low'
            })
            df_save = df[['close', 'open', 'high', 'low']]
            df_save.index.names = ['date']
            df_save['source'] = 'Yahoo Finance'
            df_save['url'] = 'https://www.yahoo.com'
        except Exception:
            # Return empty DF
            df_save = pd.DataFrame()
        return (df_save)
    return df


# @timeout(40)
def get_company_info(ticker):
    data = yf.Ticker(ticker)
    info = data.info
    return (info)


def asset_list(term=None):
    master_list = []
    try:
        info = get_company_info(term)
        master_list.append({
            'symbol': term,
            'name': info['shortName'],
            'provider': 'yahoo',
            'notes': info['exchange'],
            'fx': info['financialCurrency']
        })
    except Exception as e:
        print(e)

    return (master_list)
