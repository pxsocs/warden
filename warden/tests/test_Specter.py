# Run unit tests from the warden directory:
# $ python3 test_Specter.py
import unittest
from unittest.mock import patch
import requests
from backend.config import Config
import configparser
from specter.specter_importer import Specter


class TestSpecter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config_file = Config.config_file
        cls.config = configparser.ConfigParser()
        cls.config.read(config_file)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_ping_url(self):
        print("Pinging URL:")
        # Test if this url can be reached
        url = self.config['SPECTER'].get('specter_url')
        print(url)
        result = requests.get(url)
        print("Resulted in: " + str(result))
        # got response back?
        self.assertIsInstance(result, requests.models.Response)
        # Got code ok back?
        self.assertEqual(result.ok, True)

    def test_auth(self):
        print("Checking authentication to Specter with credentials:")
        print(f"url: {self.config['SPECTER'].get('specter_url')}")
        print(f"username: {self.config['SPECTER'].get('specter_login')}")
        print(f"password: {self.config['SPECTER'].get('specter_password')}")
        specter = Specter()
        session = specter.init_session()
        print(session)

    def test_home(self):
        print("Reaching Specter and getting main page data")
        print("Checks the integrity of parser data")
        specter = Specter()
        data = specter.home_parser()
        self.assertNotIn('error', data)
        # check data does not return an error
        checker_list = ['bitcoin_core_data', 'version']
        for element in checker_list:
            self.assertNotIn('error', data[element])


if __name__ == '__main__':
    print("Running tests... Please wait...")

    unittest.main()
