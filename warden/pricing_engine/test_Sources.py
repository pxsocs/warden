# Run by executing from warden directory:
# python3 -m pricing_engine.test_Sources

import unittest
from backend.utils import load_config
from pricing_engine.engine import (apikey, realtime_price, historical_prices,
                                   price_ondate, fx_price_ondate)
from pricing_engine.alphavantage import realtime, historical
from pricing_engine.cryptocompare import realtime as cc_realtime
from pricing_engine.cryptocompare import historical as cc_historical
from pricing_engine.fmp import realtime as fmp_realtime
from pricing_engine.fmp import historical as fmp_historical

from pricing_engine.twelvedata import realtime as td_realtime
from pricing_engine.twelvedata import historical as td_historical

import pandas as pd


class TestPricing(unittest.TestCase):

    # Test REALTIME PRICES
    def test_realtime_parsed(self):
        ticker_list = ['BTC', 'GBTC', 'ETH', 'IBM', 'MSTR', 'TSLA']
        for ticker in ticker_list:
            results = realtime_price(ticker)['price']
            self.assertIsNotNone(results,
                                 f'Could not get realtime price for {ticker}')

    # Test price_ondate
    def test_price_ondate(self):
        dates = ['1/1/19']
        tickers = ['BTC', 'GBTC']
        for date in dates:
            for ticker in tickers:
                price_ondate(ticker, date)

    def test_fx_price_ondate(self):
        date = '1/1/20'
        fx_price_ondate('USD', 'BRL', date)
        fx_price_ondate('EUR', 'BRL', date)
        fx_price_ondate('BRL', 'USD', date)

    def test_historical_parsed(self):
        # Sources directly

        # BTC from Alphavantage Digital
        result = historical('BTC', function='DIGITAL_CURRENCY_DAILY')
        self.assertIsInstance(result, pd.DataFrame,
                              'BTC DIGITAL_CURRENCY_DAILY')
        self.assertFalse(result.empty, 'BTC DIGITAL_CURRENCY_DAILY')

        # BTC converted to BRL
        result = historical_prices('BTC', fx='EUR')
        self.assertIsInstance(result, pd.DataFrame, 'BTC BRL')
        self.assertFalse(result.empty, 'BTC BRL')

        # EUR from Alphavantage FX
        result = historical('EUR', function='FX_DAILY')
        self.assertIsInstance(result, pd.DataFrame, 'EUR FX_DAILY')
        self.assertFalse(result.empty, 'EUR FX_DAILY')

        # AAPL from Alphavantage TIME_SERIES_DAILY_ADJUSTED
        result = historical('AAPL', function='TIME_SERIES_DAILY_ADJUSTED')
        self.assertIsInstance(result, pd.DataFrame,
                              'AAPL TIME_SERIES_DAILY_ADJUSTED')
        self.assertFalse(result.empty, 'AAPL TIME_SERIES_DAILY_ADJUSTED')

        # BTC from Cryptocompare
        result = cc_historical('BTC')
        self.assertIsInstance(result, pd.DataFrame, 'BTC CC')
        self.assertFalse(result.empty, 'BTC CC')

        # GBTC from fmp
        result = td_historical('GBTC')
        # if FP API calls reached limit it will raise an error
        self.assertIsInstance(result, pd.DataFrame, 'GBTC 12D')
        self.assertFalse(result.empty, 'GBTC 12d')

        # Test Auto grabber using engine.py historical_prices
        ticker_list = ['BTC', 'GBTC', 'IBM']
        for ticker in ticker_list:
            results = historical_prices(ticker)
            self.assertIsInstance(results, pd.DataFrame,
                                  f'{ticker} - Auto historical')
            self.assertFalse(results.empty, f'{ticker} - Auto historical')

    # =====================================
    # 12 Data Tests
    # =====================================

    def test_td_found_api(self):
        config = load_config()
        self.assertEqual(config.has_option('API', 'twelvedata'), True)
        api_key = apikey('twelvedata', True)
        self.assertNotEqual(api_key, None)

    def test_td_realtime(self):
        ticker_list = ['AAPL', 'GBTC']
        for ticker in ticker_list:
            td_realtime(ticker=ticker)

    def test_td_historical(self):
        ticker_list = ['AAPL', 'GBTC']
        for ticker in ticker_list:
            td_historical(ticker)

    # =====================================
    # ALPHAVANTAGE TESTS
    # =====================================

    def test_aa_found_api(self):
        config = load_config()
        self.assertEqual(config.has_option('API', 'alphavantage'), True)
        api_key = apikey('alphavantage', True)
        self.assertNotEqual(api_key, None)

    def test_aa_realtime(self):
        ticker_list = [('BTC', 'CURRENCY_EXCHANGE_RATE'),
                       ('GBTC', 'GLOBAL_QUOTE'), ('AAPL', 'GLOBAL_QUOTE'),
                       ('ETH', 'CURRENCY_EXCHANGE_RATE'),
                       ('EUR', 'CURRENCY_EXCHANGE_RATE'),
                       ('USD', 'CURRENCY_EXCHANGE_RATE')]
        for ticker in ticker_list:
            realtime(ticker=ticker[0], function=ticker[1])

    def test_aa_historical(self):
        ticker_list = [('BTC', 'DIGITAL_CURRENCY_DAILY'),
                       ('GBTC', 'TIME_SERIES_DAILY_ADJUSTED'),
                       ('AAPL', 'TIME_SERIES_DAILY_ADJUSTED'),
                       ('ETH', 'DIGITAL_CURRENCY_DAILY'), ('EUR', 'FX_DAILY'),
                       ('USD', 'FX_DAILY')]
        for ticker in ticker_list:
            historical(ticker=ticker[0], function=ticker[1])

    # =====================================
    # CRYPTOCOMPARE TESTS
    # =====================================

    def test_cc_found_api(self):
        api_key = apikey('cryptocompare', True)
        self.assertNotEqual(api_key, None)

    def test_cc_realtime(self):
        ticker_list = [('BTC', 'USD'), ('BTC', 'EUR'), ('ETH', 'BTC,USD,GBP'),
                       ('ETH', 'BRL')]
        for ticker in ticker_list:
            cc_realtime(ticker=ticker[0], fxs=ticker[1])

    def test_cc_historical(self):
        ticker_list = [('BTC', 'USD'), ('BTC', 'EUR'), ('ETH', 'BRL')]
        for ticker in ticker_list:
            cc_historical(ticker=ticker[0], fx=ticker[1])

    # =====================================
    # FMP TESTS
    # =====================================

    def test_fmp_found_api(self):
        config = load_config()
        self.assertEqual(config.has_option('API', 'fmp'), True)
        api_key = apikey('fmp', True)
        self.assertNotEqual(api_key, None)

    def test_fmp_realtime(self):
        ticker_list = ['BTC', 'AAPL', 'GBTC', 'IBM']
        for ticker in ticker_list:
            fmp_realtime(ticker=ticker)

    def test_fmp_historical(self):
        ticker_list = ['BTC', 'AAPL', 'GBTC', 'IBM']
        for ticker in ticker_list:
            fmp_historical(ticker=ticker)


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
