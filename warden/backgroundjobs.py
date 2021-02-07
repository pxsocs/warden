import configparser
from flask import current_app as app
from warden_modules import regenerate_nav
from specter_importer import Specter
from config import Config
from warden_pricing_engine import fxsymbol


# Start background threads

def background_specter_update():
    app.specter = Specter()
    app.specter.refresh_txs(load=False)
    app.specter.home_parser(load=False)
    wallets = app.specter.wallet_alias_list(load=True)
    for wallet in wallets:
        app.specter.wallet_info(wallet_alias=wallet, load=False)
        app.specter.rescan_progress(wallet_alias=wallet, load=False)


def background_settings_update():
    # Reload config
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
    regenerate_nav()
