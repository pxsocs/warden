import configparser
from flask import current_app as app
from warden_modules import regenerate_nav
from specter_importer import Specter
from config import Config
from warden_pricing_engine import fxsymbol
from message_handler import Message

# Start background threads


def background_specter_update():
    # clean old messages
    app.message_handler.clean_category('background')
    message = Message(category='background',
                      message_txt="<span class='text-info'>Starting Background Update</span>")
    app.message_handler.add_message(message)

    metadata = app.specter.home_parser(load=False)

    # Log Home data
    message = Message(category='background',
                      message_txt='Home Data Crawler',
                      notes=f"Loaded the following wallets:<br><span class='text-success'>{metadata['alias_list']}</span>"
                      )
    app.message_handler.add_message(message)
    message = Message(category='background',
                      message_txt='Home Data Crawler',
                      notes=f"<span class='text-success'>Bitcoin Core is at block {metadata['bitcoin_core_data']['Blocks count']}</span>"
                      )
    app.message_handler.add_message(message)
    #  End log

    txs = app.specter.refresh_txs(load=False)

    # Log Home data
    message = Message(category='background',
                      message_txt="<span class='text-success'>Finished Transaction Refresh ✅</span>",
                      notes=f"<span class='text-info'>Loaded {len(txs['txlist'])} Transactions</span>"
                      )
    app.message_handler.add_message(message)
    #  End log

    wallets = app.specter.wallet_alias_list(load=True)
    for wallet in wallets:
        app.specter.wallet_info(wallet_alias=wallet, load=False)
        app.specter.rescan_progress(wallet_alias=wallet, load=False)

    app.downloading = False


def background_settings_update():
    # Reload config
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
    regenerate_nav()
