# Run unit tests from the warden directory:
# $ python3 test_pricingEngine.py


from datetime import datetime
import unittest
import requests
import pandas as pd
from warden_pricing_engine import (price_data_rt, tor_request,
                                   test_tor, get_price_ondate)


class TestPricing(unittest.TestCase):

    # This tests if a Onion URL is reachable using tor_request method
    def test_tor_request(self):
        # Test standard request using Tor
        url = 'http://www.google.com/'
        result = tor_request(url)
        # got response back?
        self.assertIsInstance(result, requests.models.Response)
        # Got code ok back?
        self.assertEqual(result.ok, True)

        # For testing we are using the MemPool.Space onion address
        # this is a good URL to test since it can also be used as a feed to
        # mempool data later
        url = 'http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/'
        result = tor_request(url)
        # got response back?
        self.assertIsInstance(result, requests.models.Response)
        # Got code ok back?
        self.assertEqual(result.ok, True)

    # Make tests to check Tor is getting hidden IPs and connecting
    def test_tor_tester(self):
        result = test_tor()
        # Check if string contains error message
        con_err = 'Connection Error' in result['pre_proxy']
        self.assertFalse(con_err)
        post_err = 'Failed' in result['post_proxy_ping']
        self.assertFalse(post_err)
        # Make sure Tor IP address is not the same as original
        tor_ip_err = (result['pre_proxy'] == result['post_proxy'])
        self.assertFalse(tor_ip_err)

    # Check if pricing APIs are running and returning a valid price

    def test_rt_prices(self):
        # Realtime prices
        ticker_list = ['BTC', 'MSTR']
        for ticker in ticker_list:
            result = price_data_rt(ticker)
            # Check if not none
            self.assertIsNotNone(result)
            import numbers
            self.assertIsInstance(result, numbers.Number)

    def test_price_ondate(self):
        ticker_list = ['BTC', 'MSTR']
        dates = [datetime(2018, 1, 1, 0, 0)]
        for ticker in ticker_list:
            for date in dates:
                result = get_price_ondate(ticker, date)
                # Check if not zero => this equals fail
                self.assertIsNot(result, 0)
                # Expected result is a dataframe with:
                # close    13444.88
                # open     13850.49
                # high     13921.53
                # low      12877.67
                self.assertIsInstance(result, pd.Series)


if __name__ == '__main__':
    print("Running tests... Please wait...")
    unittest.main()
