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
                   has_request_context)

from flask_apscheduler import APScheduler
from flask_mail import Mail
from pathlib import Path

from config import Config
from warden_pricing_engine import tor_request
from warden_decorators import MWT, timing

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


# Method to create a new config file if not found
# Copies data from warden.config_default.ini into a new config.ini
def update_config(config_file=Config.config_file):
    logging.info("Updating Config file")
    with open(config_file, 'w') as file:
        current_app.settings.write(file)


# Critical checks for specter
def specter_checks():
    specter_data = load_specter()
    if specter_data == "unauthorized":
        print("  Specter Login UNAUTHORIZED -- Check username and password")
    elif specter_data['is_running']:
        print("  Specter API is available [SUCCESS]")
    elif not specter_data['is_running']:
        print("  Specter API is available but Specter is not running [WARNING]")


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
    login_data = {
        'username': username,
        'password': password
    }
    session = requests.session()
    if not onion or onion == '':
        try:
            # First post login info into session to authenticate
            login = session.post(url + '/login', login_data)
            # Check if login was authorized
            if login.status_code == 401:
                print("  Specter Login UNAUTHORIZED -- Check username and password")
                logging.warn("Could not authenticate Specter login")
                return ("unauthorized")
            r = session.get(url + '/api/specter/')
            specter = json.loads(r.content.decode('utf-8'))

        except Exception as e:
            specter = f"Error: {e}"
    else:
        url = url + '/api/specter/'
        specter = tor_request(url, tor_only=True)
    return(specter)


@MWT(timeout=30)
def load_wallet(wallet_alias):
    logging.info(f"Loading Wallet: {wallet_alias}")
    # Try to reach API
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)
    onion = config['SPECTER']['specter_onion']
    url = config['SPECTER']['specter_url']
    username = config['SPECTER']['specter_login']
    password = config['SPECTER']['specter_password']
    login_data = {
        'username': username,
        'password': password
    }
    session = requests.session()
    if not onion or onion == '':
        try:
            # First post login info into session to authenticate
            login = session.post(url + '/login', login_data)
            # Check if login was authorized
            if login.status_code == 401:
                print("  Specter Login UNAUTHORIZED -- Check username and password")
                logging.warn("Could not authenticate Specter login")
                return ("unauthorized")
            r = session.get(url + '/api/wallet_info/' + wallet_alias + '/')
            specter = json.loads(r.content.decode('utf-8'))
        except Exception as e:
            specter = f"Error: {e}"
    else:
        url = url + '/api/wallet_info/' + wallet_alias + '/'
        specter = tor_request(url, tor_only=True)
    logging.info(f"Done Loading Wallet: {wallet_alias}")
    return(specter)


def load_wallets():
    logging.info(f"Loading all Wallets")
    specter_data = load_specter()
    wallets_data = {}
    for alias in specter_data['wallets_alias']:
        wallet_json = load_wallet(alias)
        wallets_data[alias] = wallet_json
    logging.info(f"Finished Building Wallets Class")
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
