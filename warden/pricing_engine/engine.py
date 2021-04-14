import requests
from utils import load_config, pickle_it, fxsymbol
import pandas as pd
import os
import logging
from datetime import datetime
from dateutil import parser
from warden_decorators import MWT
from parseNumbers import parseNumber


@ MWT(timeout=10)
def apikey(source, required=True):
    # GET API_KEY
    if load_config().has_option('API', source):
        API_KEY = load_config()['API'][source]
    else:
        API_KEY = None
    if required and API_KEY is None:
        raise Exception(f'{source} requires an API KEY and none was found.')
    return API_KEY


@ MWT(timeout=200)
def price_ondate(ticker, date_input):
    df = historical_prices(ticker)
    if df.empty:
        return None
    try:
        dt = pd.to_datetime(date_input)
        df.index = df.index.astype('datetime64[ns]')
        df = df[~df.index.duplicated(keep='first')]
        idx = df.iloc[df.index.get_loc(dt, method='nearest')]
        return (idx)
    except Exception as e:
        logging.warning("Error getting price on date " + date_input +
                        " for " + ticker + ". Error " + str(e))
        return (None)


# The below is a priority list for some usually accessed tickers
mapping = {
    'BTC': ['cryptocompare', 'alphavantage_currency'],
    'GBTC': ['twelvedata', 'fmp', 'alphavantage_global'],
    'ETH': ['cryptocompare', 'alphavantage_currency'],
    'MSTR': ['alphavantage_global', 'twelvedata', 'fmp'],
}


@ MWT(timeout=200)
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

    ticker = ticker.replace(' ', '')

    if source and type(source) != list:
        raise TypeError("source has to be a list of strings - can be one string inside a list")

    try:
        source_list = mapping[ticker]
    except KeyError:
        source_list = [
            'cryptocompare',
            'twelvedata',
            'alphavantage_currency',
            'alphavantage_global',
            'fmp'
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
                df_fx = aa_historical(fx, function='FX_DAILY')
                df_fx.index = pd.to_datetime(df_fx.index)
                df_fx = df_fx.loc[~df_fx.index.duplicated(keep='first')]
                df_fx = df_fx.rename(columns={'close': 'fx_close'})
                df_fx = df_fx[['fx_close']]
                df_fx['fx_close'] = pd.to_numeric(df_fx.fx_close,
                                                  errors='coerce')
                df_fx['fx_close'] = 1 / df_fx['fx_close']

                # Merge the two dfs:
                results.index = pd.to_datetime(results.index)
                results = results.loc[~results.index.duplicated(keep='first')]
                merge_df = pd.merge(results, df_fx, on='date', how='inner')
                merge_df['close'] = merge_df['close'].astype(float)
                merge_df['close_converted'] = merge_df['close'] * merge_df[
                    'fx_close']

                results = merge_df

            else:
                results['fx_close'] = 1
                results['close_converted'] = pd.to_numeric(results.close,
                                                           errors='coerce')

            results.index = results.index.astype('datetime64[ns]')
            # Save this file to be used during the same day instead of calling API
            pickle_it(action='save', filename=filename, data=results)
            # save metadata as well
            metadata = {
                'source': src,
                'last_update': datetime.utcnow()
            }
            filemeta = (ticker + "_" + fx + ".meta")
            pickle_it(action='save', filename=filemeta, data=metadata)

            return (results)
        else:
            logging.info(f"Source {src} does not return any data for {ticker}. Trying other sources.")
    if results.empty:
        logging.warning(f"Could not retrieve a df for {ticker} from any source")

    return (results)


@ MWT(timeout=5)
def realtime_price(ticker, fx=None, source=None, parsed=True):
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
    if fx is None:
        config = load_config()
        fx = config['PORTFOLIO']['base_fx']

    if fx == 'USD':
        fxrate = 1
    else:
        from pricing_engine.alphavantage import realtime as aa_realtime
        fxrate = aa_realtime(fx)
        fxrate = parseNumber(fxrate['price'])

    ticker = ticker.replace(' ', '')
    if source and type(source) != list:
        raise TypeError("source has to be a list of strings - can be one string inside a list")

    try:
        source_list = mapping[ticker]
    except KeyError:
        source_list = [
            'cryptocompare',
            'alphavantage_currency',
            'alphavantage_global',
            'twelvedata',
            'fmp'
        ]

    from pricing_engine.alphavantage import realtime as aa_realtime
    from pricing_engine.cryptocompare import realtime as cc_realtime
    from pricing_engine.fmp import realtime as fmp_realtime
    from pricing_engine.twelvedata import realtime as td_realtime

    results = None
    # Gets from each source
    for src in source_list:
        if src == 'alphavantage_currency':
            results = aa_realtime(ticker, 'USD', 'CURRENCY_EXCHANGE_RATE', parsed=parsed)
        if src == 'alphavantage_global':
            results = aa_realtime(ticker, 'USD', 'GLOBAL_QUOTE', parsed=parsed)
        if src == 'cryptocompare':
            results = cc_realtime(ticker, 'USD', parsed=parsed)
        if src == 'fmp':
            results = fmp_realtime(ticker, parsed=parsed)
        if src == 'twelvedata':
            results = td_realtime(ticker, parsed=parsed)
        # Check if data is valid
        if results is not None:
            if parsed and 'price' in results:
                if results['price'] is not None:
                    if isinstance(results['time'], str):
                        results['time'] = parser.parse(results['time'])
                    results['price'] = parseNumber(results['price'])
                    results['price'] = (
                        results['price'] / fxrate)
                    return (results)
    return (results)


@ MWT(timeout=200)
def GBTC_premium(price):
    # Calculates the current GBTC premium in percentage points
    # to BTC (see https://grayscale.co/bitcoin-trust/)
    SHARES = 0.00094643  # as of 3/15/2021
    fairvalue = realtime_price("BTC")['price'] * SHARES
    premium = (price / fairvalue) - 1
    return fairvalue, premium


@ MWT(timeout=200)
def fx_rate():
    config = load_config()
    fx = config['PORTFOLIO']['base_fx']

    # This grabs the realtime current currency conversion against USD
    try:
        rate = {}
        rate['base'] = fx
        rate['symbol'] = fxsymbol(fx)
        rate['name'] = fxsymbol(fx, 'name')
        rate['name_plural'] = fxsymbol(fx, 'name_plural')
        rate['cross'] = "USD" + " / " + fx
        if fx.upper() == 'USD':
            rate['fx_rate'] = 1
        else:
            try:
                from pricing_engine.alphavantage import realtime as aa_realtime
                fxrate = aa_realtime(fx)
                fxrate = parseNumber(fxrate['price'])
                rate['fx_rate'] = 1 / fxrate
            except Exception as e:
                rate['error'] = ("Error: " + str(e))
                rate['fx_rate'] = 1
    except Exception as e:
        rate = {}
        rate['error'] = ("Error: " + str(e))
        rate['fx_rate'] = 1
    return (rate)


@ MWT(timeout=200)
def fx_price_ondate(base, cross, date):
    # Gets price conversion on date between 2 currencies
    # on a specific date
    try:
        if base == 'USD':
            price_base = 1
        else:
            base_class = price_ondate(base, date)
            price_base = base_class['close']
        if cross == 'USD':
            price_cross = 1
        else:
            cross_class = price_ondate(cross, date)
            price_cross = cross_class['close']
        conversion = float(price_base) / float(price_cross)
        return (conversion)
    except Exception:
        return (1)
