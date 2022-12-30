import configparser
import logging
import requests
import time
from flask import flash
from backend.warden_modules import regenerate_nav
from specter.specter_importer import Specter
from backend.config import Config
from backend.utils import fxsymbol, pickle_it
from datetime import datetime
from connections.message_handler import Message


def background_settings_update(app):
    app.message_handler.clean_category('NAV Calculation')
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
    ts = time.time()
    regenerate_nav()
    te = time.time()
    message = Message(
        category='NAV Calculation',
        message_txt="<span class='text-success'>NAV Recalculated</span>",
        notes=f"Calculation took {round((te - ts) * 1000, 2)} ms")
    app.message_handler.add_message(message)
    # Wait 5 seconds before running again
    time.sleep(5)


def test_RealTimeBTC(app):
    from pricing_engine.engine import realtime_price
    ticker = 'BTC'
    results = realtime_price(ticker)
    run_time = datetime.now()

    if results is None:
        health = False
        price = None
        error_message = 'Realtime Price returned None'
    try:
        price = results['price']
        health = True
        error_message = None
    except Exception as e:
        health = False
        price = None
        error_message = f"Realtime Price returned an error: {e}"

    data = {
        'health': health,
        'price': price,
        'error_message': error_message,
        'run_time': run_time
    }

    filename = 'status_realtime_btc.pkl'
    pickle_it(action='save', filename=filename, data=data)

    return (data)


def background_scan_network(app):
    from connections.connections import scan_network
    try:
        app.scan_network = scan_network()
    except Exception as e:
        logging.error(f"Error Scanning Network: {e}")
