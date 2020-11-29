import configparser
from flask import current_app as app
from warden_modules import (specter_update, wallets_update, check_services, regenerate_nav)
from config import Config
from warden_pricing_engine import fxsymbol


# Start background threads
# Get Specter tx data and updates every 30 seconds (see config.py)


def background_specter_update():
    app.specter = specter_update(load=False)


def background_wallets_update():
    app.wallets = wallets_update(load=False)


def background_services_update():
    app.services = check_services(load=False)


def background_settings_update():
    # Reload config
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
    regenerate_nav()
