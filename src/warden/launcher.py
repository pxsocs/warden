import os
import requests
from yaspin import yaspin
import logging
import pandas as pd
from ansi_management import (warning, success, error, info, clear_screen, bold,
                             muted, yellow, blue)
from welcome import logo
import configparser
from warden_pricing_engine import (test_tor,
                                   tor_request, REALTIME_PROVIDER_PRIORITY,
                                   FX_RT_PROVIDER_PRIORITY, HISTORICAL_PROVIDER_PRIORITY,
                                   FX_PROVIDER_PRIORITY)
from utils import specter_checks

# Make sure services are running and app can be launched

# Main Variables
basedir = os.path.abspath(os.path.dirname(__file__))
debug_file = os.path.join(basedir, 'debug.log')


def create_tor():
    # ----------------------------------------------
    #                 Test Tor
    # ----------------------------------------------
    with yaspin(text="Testing Tor", color="cyan") as spinner:
        tor = test_tor()
        if tor['status']:
            logging.info(success("Tor Connected"))
            spinner.ok("✅ ")
            spinner.write(success("    Tor Connected [SUCCESS]"))
            print("")
            return (tor)
        else:
            logging.error(error("Could not connect to Tor"))
            spinner.fail("💥 ")
            spinner.write(warning("    Tor NOT connected [ERROR]"))
            print(
                error(
                    "    Could not connect to Tor. WARden requires Tor to run. Quitting..."
                ))
            print(
                info(
                    "    Download Tor at: https://www.torproject.org/download/"
                ))
            print("")
            exit()


def load_config(quiet=False):
    # Load Config
    config_file = os.path.join(basedir, 'config.ini')
    CONFIG = configparser.ConfigParser()
    if quiet:
        CONFIG.read(config_file)
        return (CONFIG)

    with yaspin(text="Loading config.ini", color="cyan") as spinner:

        # Check that config file exists
        if os.path.isfile(config_file):
            CONFIG.read(config_file)
            spinner.ok("✅ ")
            spinner.write(success("    Config Loaded [SUCCESS]"))
            print("")
            return (CONFIG)
        else:
            spinner.fail("💥 ")
            spinner.write(
                warning("    Config file could not be loaded [ERROR]"))
            print(error("    WARden requires config.ini to run. Quitting..."))
            exit()


def check_stockprices(ticker='AAPL'):
    with yaspin(text=f"Testing Historical Price for Stocks with ticker: {ticker}",
                color="green") as spinner:
        from warden_pricing_engine import price_data_fx
        price = price_data_fx(ticker)
        fail = True
        message = ""
        # Is it a dataframe?
        if isinstance(price, pd.DataFrame):
            if not price.empty:
                try:
                    current_price = price['close'].values[0]
                    message = f"    Latest price for {ticker} is {current_price}. "
                    message += f"Prices available from {price.index.min().strftime('%h-%d-%Y')} to {price.index.max().strftime('%h-%d-%Y')} [SUCCESS]"
                    fail = False
                except Exception as e:
                    fail = True
                    message = f"    Could not get prices. Error: {e}"
            else:
                fail = True
                message = "    Could not get prices. Empty Historical Dataframe was returned."
        else:
            fail = True
            message = "    Could not get prices. Price request returned None."

        if fail:
            spinner.fail("💥 ")
            spinner.write(
                warning(message))
        else:
            spinner.ok("✅ ")
            spinner.write(success(message))

        return (message)


def check_cryptocompare():
    with yaspin(text=f"Testing price grab from Cryptocompare",
                color="green") as spinner:
        config = load_config()
        api_key = config['API'].get('cryptocompare')
        # tickers should be in comma sep string format like "BTC,ETH,LTC" and "USD,EUR"
        baseURL = (
            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC" +
            "&tsyms=USD&api_key=" + api_key)
        try:
            request = tor_request(baseURL)
        except requests.exceptions.ConnectionError:
            spinner.fail("💥 ")
            spinner.write(
                warning("    Connection Error - check internet connection"))
            exit()

        data = request.json()

        try:
            if data['Response'] == 'Error':
                config_file = os.path.join(basedir, 'config.ini')
                spinner.fail("💥 ")
                spinner.write(warning("    CryptoCompare Returned an error"))
                print("    " + data['Message'])
                if data['Message'] == 'You are over your rate limit please upgrade your account!':
                    # First try to get a random API KEY
                    if config['API'].getboolean('random') is not True:
                        print(
                            "    Looks like you are over the API Limit. Will try to generate a random API."
                        )
                        size = 16
                        import binascii
                        random_key = binascii.b2a_hex(os.urandom(size))
                        config['API']['random'] = 'True'
                        config['API']['cryptocompare'] = str(
                            random_key.decode("utf-8"))
                        with open(config_file, 'w') as configfile:
                            config.write(configfile)
                        check_cryptocompare()
                        return

                    print(
                        '    -----------------------------------------------------------------'
                    )
                    print(
                        yellow("    Looks like you need to get an API Key. "))
                    print(
                        yellow("    The WARden comes with a shared key that"))
                    print(yellow("    eventually gets to the call limit."))
                    print(
                        '    -----------------------------------------------------------------'
                    )
                    print(
                        blue(
                            '    Go to: https://www.cryptocompare.com/cryptopian/api-keys'
                        ))
                    print(muted("    Current API:"))
                    print(f"    {api_key}")
                    new_key = input('    Enter new API key (Q to quit): ')
                    if new_key == 'Q' or new_key == 'q':
                        exit()
                    config['API']['cryptocompare'] = new_key
                    with open(config_file, 'w') as configfile:
                        config.write(configfile)
                    check_cryptocompare()
        except KeyError:
            try:
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.ok("✅ ")
                spinner.write(success(f"    BTC price is: {btc_price}  [SUCCESS]"))
                return
            except Exception:
                spinner.fail("💥 ")
                spinner.write(
                    warning("    CryptoCompare Returned an UNKNOWN error"))
                print(data)

        return (data)


clear_screen()
logo()
print("")
print(success("Launching Application..."))
print("")
create_tor()
specter_checks()
print("")
check_cryptocompare()
print("")
check_stockprices()
print("")
