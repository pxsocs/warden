import logging
import configparser
import os
import sys
import atexit
import json
import requests
import pickle

from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import (Flask, request, current_app,
                   has_request_context, flash, abort)

from flask_apscheduler import APScheduler
from flask_mail import Mail
from pathlib import Path

from config import Config
from warden_pricing_engine import tor_request
from warden_decorators import MWT, timing
from ansi_management import (warning, success, error, info, clear_screen, bold,
                             muted, yellow, blue)

from yaspin import yaspin

import mhp as mrh

# Method to create a new config file if not found
# Copies data from warden.config_default.ini into a new config.ini


def create_config(config_file):
    logging.warn("Config File not found. Getting default values and saving.")
    # Get the default config and save into config.ini
    default_file = Config.default_config_file

    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)


def update_config(config_file=Config.config_file):
    logging.info("Updating Config file")
    with open(config_file, 'w') as file:
        current_app.settings.write(file)


def load_config():
    # Load Config
    basedir = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(basedir, 'config.ini')
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    return (CONFIG)


# Critical checks for specter
def specter_checks():
    with yaspin(text="Checking Specter Server Status", color="cyan") as spinner:
        try:
            specter_data = load_specter()
            if specter_data == "unauthorized":
                spinner.fail("💥 ")
                spinner.write(warning("    Specter Login UNAUTHORIZED -- Check username and password"))
            elif specter_data['is_running']:
                spinner.ok("✅ ")
                spinner.write(success("    Specter API is available [SUCCESS]"))
            elif not specter_data['is_running']:
                spinner.fail("💥 ")
                spinner.write(warning("    Specter is not running"))
                print(warning("    Login to Specter Server and check if it's running"))
        except Exception:
            spinner.fail("💥 ")
            spinner.write(warning("    Specter Server cannot be reached. Check if it's running."))


@MWT(timeout=10)
def load_specter():
    logging.info("Updating Specter...")
    # Try to reach API
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)
    onion = config['SPECTER']['specter_onion']
    url = config['SPECTER']['specter_url']
    username = config['SPECTER']['specter_login']
    password = config['SPECTER']['specter_password']

    if not onion or onion == '':
        try:
            r = requests.get(url + '/api/v1alpha/specter', auth=(username, password))
            specter = json.loads(r.json())
        except Exception as e:
            return(f"Error {str(e)}")

    else:
        url = url + '/api/v1alpha/specter/'
        specter = tor_request(url, tor_only=True)
    return(specter)


@MWT(timeout=30)
def load_wallet(wallet_alias, session=None):
    if not session:
        try:
            session = current_app.specter_session
        except Exception:
            session = create_specter_session()
    logging.info(f"Loading Wallet: {wallet_alias}")
    # Try to reach API
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)
    onion = config['SPECTER']['specter_onion']
    url = config['SPECTER']['specter_url']
    username = config['SPECTER']['specter_login']
    password = config['SPECTER']['specter_password']

    if not onion or onion == '':
        try:
            r = requests.get(url + '/api/v1alpha/wallet_info/' + str(wallet_alias) + '/', auth=(username, password))
            wallet = json.loads(r.json())
            logging.info(f"Done Loading Wallet: {wallet_alias}")
            return(wallet)
        except Exception as e:
            wallet = None
    else:
        url = url + '/api/v1alpha/wallet_info/' + wallet_alias + '/'
        wallet = tor_request(url, tor_only=True)

    return (wallet)


def load_wallets():
    logging.info(f"Loading all Wallets")
    specter_data = load_specter()
    wallets_data = {}
    errors = 0
    for alias in specter_data['wallets_alias']:
        wallet_json = load_wallet(alias)
        wallets_data[alias] = wallet_json
        if not wallet_json:
            errors += 1
            logging.error(f"Error loading wallet {alias}")
    logging.info(f"Finished Building Wallets Class")
    if errors > 0:
        return None

    return (wallets_data)


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    logging.info(f"Pickle {action} file: {filename}")
    from warden_modules import home_path
    filename = 'warden/' + filename
    filename = os.path.join(home_path(), filename)
    if action == 'load':
        try:
            with open(filename, 'rb') as handle:
                ld = pickle.load(handle)
                logging.info(f"Loaded: Pickle {action} file: {filename}")
                return (ld)
        except Exception as e:
            logging.warn(f"Error: Pickle {action} file: {filename} error:{e}")
            return ("file not found")
    else:
        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            logging.info(f"Saved: Pickle {action} file: {filename}")
            return ("saved")


def create_specter_session():
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)
    onion = config['SPECTER']['specter_onion']
    url = config['SPECTER']['specter_url']
    username = config['SPECTER']['specter_login']
    password = config['SPECTER']['specter_password']
    r = None
    # First post login info into session to authenticate

    if password:
        try:
            r = requests.get(url + '/api/v1alpha/specter/', auth=(username, password))
        except Exception:
            failed = True
            while failed:
                print("")
                print("\033   [!] WARNING")
                print(f"\033[1;33;40m  [!] Could not connect to Specter at url: {url}")
                print("      Format: http://127.0.0.1:25441")
                url_new = input(f"  >> Enter Specter Server URL [{url}]: ")
                if url_new:
                    url = url_new
                try:
                    # Remove redundant /
                    if url[-1] == '/':
                        url = url[:-1]
                    failed = False
                    r = requests.get(url + '/api/v1alpha/specter/', auth=(username, password))
                    config['SPECTER']['specter_url'] = url
                    with open(file, 'w') as f:
                        config.write(f)
                    print("  [OK] Config Updated")
                except Exception:
                    failed = True

    # Check if login was authorized
    if r:
        # If an html page is returned instead of json, there is an error
        if r.status_code == 404:
            logging.warn("Could not authenticate Specter login")
            return("API404")
        if "<!DOCTYPE html>" in str(r.content):
            logging.warn("Could not authenticate Specter login")
            return("unauthorized")
        if r.status_code == 401:
            logging.warn("Could not authenticate Specter login")
            return("unauthorized")

    return()


#  Tests

def diags(e=None):
    if e:
        print("---------------------------------")
        print("  An error occured ")
        print("  Running a quick diagnostic")
        print("---------------------------------")
        print("  Error Message")
        print("  " + str(e))
        print("---------------------------------")
    return_dict = {}
    messages = []
    print("  Starting Tests...")
    print("---------------------------------")
    # run specter tests

    # Loading Config
    print("  Loading config file...")
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)
    username = config['SPECTER']['specter_login']
    password = config['SPECTER']['specter_password']

    print("  Trying Specter Server Authorization...")
    # Fist check if authentication works
    specter_session = create_specter_session()
    if specter_session == 'unauthorized':
        print("[ERROR] Unauthorized error. Check Specter username and password.")
        exit()
    if specter_session == 'ConnectionError':
        print("[ERROR] Could not connect to Specter. Is it running?")
        exit()
    else:
        url = config['SPECTER']['specter_url']
        print("  Trying to get Specter Data...")
        r = requests.get(url + '/api/v1alpha/specter/', auth=(username, password))
        print("  Returned Response Code: " + str(r))

    # Load basic specter data
    # try:
    print("  Load Specter Data...")
    specter = load_specter()

    if specter == 'unauthorized':
        return_dict['specter_status'] = 'Unauthorized'
        msg = 'Could not login to Specter: Unauthorized'
        print(msg)
        messages.append(msg)
    else:
        return_dict['specter_isrunning'] = specter['is_running']
        return_dict['specter_lastupdate'] = specter['last_update']
        return_dict['specter_wallets'] = specter['wallets_names']
        print("Specter Results:")
        print("Running: " + str(return_dict['specter_isrunning']))
        print("Last Update: " + str(return_dict['specter_lastupdate']))
        print("Wallets Found: " + str(return_dict['specter_wallets']))

    # except Exception as e:
    #     print("Specter Results:")
    #     print("Error message")
    #     print(str(e))
    #     return_dict['specter_status'] = 'Error'
    #     messages.append(str(e))
    #     exit()

    # run wallet tests
    wallets_data = {}
    test_df = None
    print("---------------------------------")
    print(" Starting Wallets Test")
    print("---------------------------------")
    for alias in specter['wallets_alias']:
        print(f"Checking Wallet: {alias}")
        wallets_data[alias] = {}
        wallet = load_wallet(alias, session=specter_session)
        if not wallet:
            print("Warning: Wallet data was returned empty. Check connections.")
            wallets_data[alias]['status'] = 'Empty'
        else:
            wallets_data[alias]['name'] = wallet[alias]['name']
            wallets_data[alias]['balance'] = wallet[alias]['balance']['trusted']
            wallets_data[alias]['txcount'] = wallet[alias]['info']['txcount']
            wallets_data[alias]['scanning'] = wallet[alias]['info']['scanning']
            # If we find a wallet and it has txcount, let's test importing it into a df
            if wallets_data[alias]['txcount'] > 0:
                from warden_modules import get_specter_tx
                df = get_specter_tx(alias, load=False, session=specter_session)
                if df.empty:
                    print('Failed to import. Empty.')
                    return_dict['df_import'] = '[ERROR] Failed to import. Empty.'
                else:
                    balance = df['amount'].sum()
                    return_dict['df_import'] = 'Imported - balance = ' + str(balance)
                    print(return_dict['df_import'])
                    print("Results : ")
                    for key, value in wallets_data[alias].items():
                        print(str(key) + ' : ' + str(value))
        print("- - - - - - - - - - ")

    return_dict['wallets'] = wallets_data
    return_dict['messages'] = messages

    # Test Pricing Engine
    print("---------------------------------")
    print(" Starting Price Engine")
    print("---------------------------------")
    ticker = 'BTC'
    print(f"Ticker: {ticker}")
    print("Testing Realtime Pricing")
    from warden_pricing_engine import price_data_rt, REALTIME_PROVIDER_PRIORITY
    price = price_data_rt(ticker, priority_list=REALTIME_PROVIDER_PRIORITY, diags=True)
    print(price)

    print(json.dumps(return_dict, indent=4, sort_keys=True))

    return(return_dict)


def heatmap_generator():
    # If no Transactions for this user, return empty.html
    from warden_modules import specter_df, generatenav
    transactions = specter_df()
    if transactions.empty:
        return None, None, None, None

    # Generate NAV Table first
    data = generatenav()
    data["navpchange"] = (data["NAV_fx"] / data["NAV_fx"].shift(1)) - 1
    returns = data["navpchange"]
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(returns, eoy=True)

    heatmap_stats = heatmap
    cols = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "eoy",
    ]
    cols_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    years = (heatmap.index.tolist())
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(axis=1)
    heatmap_stats["POSITIVES"] = heatmap_stats[heatmap_stats[cols_months] > 0].count(
        axis=1
    )
    heatmap_stats["NEGATIVES"] = heatmap_stats[heatmap_stats[cols_months] < 0].count(
        axis=1
    )
    heatmap_stats["POS_MEAN"] = heatmap_stats[heatmap_stats[cols_months] > 0].mean(
        axis=1
    )
    heatmap_stats["NEG_MEAN"] = heatmap_stats[heatmap_stats[cols_months] < 0].mean(
        axis=1
    )
    heatmap_stats["MEAN"] = heatmap_stats[heatmap_stats[cols_months] != 0].mean(axis=1)

    return (heatmap, heatmap_stats, years, cols)
