from utils import load_config, pickle_it, fxsymbol
import pandas as pd
import os
import logging
from datetime import datetime


def apikey(source, required=True):
    # GET API_KEY
    if load_config().has_option('API', source):
        API_KEY = load_config()['API'][source]
    else:
        API_KEY = None
    if required and API_KEY is None:
        raise Exception(f'{source} requires an API KEY and none was found.')
    return API_KEY


def price_ondate(ticker, date_input):
    df = historical_prices(ticker)
    if df.empty:
        return None
    try:
        dt = pd.to_datetime(date_input)
        idx = df.iloc[df.index.get_loc(dt, method='nearest')]
        return (idx)
    except Exception as e:
        logging.warning("Error getting price on date " + date_input +
                        " for " + ticker + ". Error " + str(e))
        return (None)


def historical_prices(ticker, fx='USD', source=None):
    '''
    RETURNS a DF with
        columns={
                'close': 'close',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'volume': 'volume'
        }
    '''

    if source and type(source) != list:
        raise TypeError("source has to be a list of strings - can be one string inside a list")

    try:
        source_list = realtime_mapping[ticker]
    except KeyError:
        source_list = [
            'cryptocompare',
            'alphavantage_currency',
            'fmp',
            'alphavantage_global',
            'twelvedata'
        ]

    from pricing_engine.alphavantage import historical as aa_historical
    from pricing_engine.cryptocompare import historical as cc_historical
    from pricing_engine.fmp import historical as fmp_historical
    from pricing_engine.twelvedata import historical as td_historical

    results = pd.DataFrame()
    # Gets from each source
    for src in source_list:
        # Try to load file if exists
        filename = (ticker + "_" + fx + ".price")
        # Check if file was updated today
        from warden_modules import home_path
        file_check = os.path.join(home_path(), 'warden/' + filename)
        # Try to read from file and check how recent it is
        try:
            today = datetime.now().date()
            filetime = datetime.fromtimestamp(os.path.getctime(file_check))
            if filetime.date() == today:
                df = pd.read_pickle(file_check)
                return (df)
        except Exception:
            pass

        if src == 'alphavantage_currency':
            results = aa_historical(ticker, function='DIGITAL_CURRENCY_DAILY')
        if src == 'alphavantage_global':
            results = aa_historical(ticker, function='TIME_SERIES_DAILY_ADJUSTED')
        if src == 'alphavantage_fx':
            results = aa_historical(ticker, function='FX_DAILY')
        if src == 'cryptocompare':
            results = cc_historical(ticker)
        if src == 'fmp':
            results = fmp_historical(ticker)
        if src == 'twelvedata':
            results = td_historical(ticker)
        # Check if data is valid
        if not results.empty:
            # Include fx column and convert to currency if needed
            if fx != 'USD':
                # Get a currency df
                print(fx)
                df_fx = aa_historical(fx, function='FX_DAILY')
                df_fx.index = pd.to_datetime(df_fx.index)
                df_fx = df_fx.rename(columns={'close': 'fx_close'})
                df_fx = df_fx[['fx_close']]
                df_fx['fx_close'] = pd.to_numeric(df_fx.fx_close,
                                                  errors='coerce')
                df_fx['fx_close'] = 1 / df_fx['fx_close']

                # Merge the two dfs:
                merge_df = pd.merge(results, df_fx, on='date', how='inner')
                merge_df['close'] = merge_df['close'].astype(float)
                merge_df['close_converted'] = merge_df['close'] * merge_df[
                    'fx_close']
                results = merge_df

            else:
                results['fx_close'] = 1
                results['close_converted'] = results['close'].astype(float)
            # Save this file to be used during the same day instead of calling API
            pickle_it(action='save', filename=filename, data=results)
            return (results)

    return (results)


# The below is a priority list for some usually accessed tickers
realtime_mapping = {
    'BTC': ['cryptocompare', 'alphavantage_currency'],
    'GBTC': ['fmp', 'twelvedata', 'alphavantage_global'],
    'ETH': ['cryptocompare', 'alphavantage_currency'],
    'MSTR': ['fmp', 'twelvedata', 'alphavantage_global']
}


def realtime_price(ticker, fx='USD', source=None):
    '''
    Gets realtime price from first provider available and returns
    result = {
            'symbol': ,
            'name': ,
            'price': ,
            'fx': ,
            'time': ,
            'timezone':
            'source':
        }
    '''
    if source and type(source) != list:
        raise TypeError("source has to be a list of strings - can be one string inside a list")

    try:
        source_list = realtime_mapping[ticker]
    except KeyError:
        source_list = [
            'cryptocompare',
            'alphavantage_currency',
            'fmp',
            'alphavantage_global',
            'twelvedata'
        ]

    from pricing_engine.alphavantage import realtime as aa_realtime
    from pricing_engine.cryptocompare import realtime as cc_realtime
    from pricing_engine.fmp import realtime as fmp_realtime
    from pricing_engine.twelvedata import realtime as td_realtime

    results = None
    # Gets from each source
    for src in source_list:
        if src == 'alphavantage_currency':
            results = aa_realtime(ticker, fx, 'CURRENCY_EXCHANGE_RATE')
        if src == 'alphavantage_global':
            results = aa_realtime(ticker, fx, 'GLOBAL_QUOTE')
        if src == 'cryptocompare':
            results = cc_realtime(ticker, fx)
        if src == 'fmp':
            results = fmp_realtime(ticker)
        if src == 'twelvedata':
            results = td_realtime(ticker)
        # Check if data is valid
        if results is not None:
            if 'price' in results:
                if results['price'] is not None:
                    return (results)

    return (results)


def GBTC_premium(price):
    # Calculates the current GBTC premium in percentage points
    # to BTC (see https://grayscale.co/bitcoin-trust/)
    SHARES = 0.00095812  # as of 8/1/2020
    fairvalue = price_data_rt("BTC") * SHARES
    premium = (price / fairvalue) - 1
    return fairvalue, premium


def fx_rate():
    config = load_config()
    fx = config['PORTFOLIO']['base_fx']

    # This grabs the realtime current currency conversion against USD
    try:
        if fx == 'USD':
            raise Exception('USD does not need conversion to USD')
        # get fx rate
        rate = {}
        rate['base'] = fx
        rate['symbol'] = fxsymbol(fx)
        rate['name'] = fxsymbol(fx, 'name')
        rate['name_plural'] = fxsymbol(fx, 'name_plural')
        rate['cross'] = "USD" + " / " + fx
        try:
            fxrate = realtime_price(fx, fx='USD', source='alphavantage_currency')
            rate['fx_rate'] = 1 / (float()))
        except Exception:
            rate['fx_rate']=1
    except Exception as e:
        rate={}
        rate['error']=("Error: " + str(e))
        rate['fx_rate']=1
    return (rate)
