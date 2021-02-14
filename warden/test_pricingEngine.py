# Run unit tests from the warden directory:
# $ python3 test_pricingEngine.py


import unittest
import requests
from warden_pricing_engine import price_data_rt, tor_request, test_tor


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

    def test_prices(self):
        # Realtime prices
        ticker = 'BTC'
        result = price_data_rt(ticker)
        # Check if not note
        self.assertIsNotNone(result)
        import numbers
        self.assertIsInstance(result, numbers.Number)


if __name__ == '__main__':
    print("Running tests... Please wait...")
    unittest.main()
