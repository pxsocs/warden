import configparser
import logging
import requests
import time
from flask import flash
from flask import current_app as app
from warden_modules import regenerate_nav
from specter_importer import Specter
from config import Config
from utils import fxsymbol, pickle_it
from datetime import datetime
from message_handler import Message

# Searches local network for an instance of Mempool Space to avoid using
# the open net version


def background_mempool_seeker():
    # Will return a value if a server was found in the last 3 minutes
    EXPIRY = 180
    from connections import is_service_running
    server_found = is_service_running('Mempool.space Explorer', EXPIRY)
    if server_found[0] is True:
        # Open Config and update
        config_file = Config.config_file
        config_settings = configparser.ConfigParser()
        config_settings.read(config_file)
        config_settings['MEMPOOL']['url'] = server_found[1]['url']
        with open(config_file, 'w') as file:
            config_settings.write(file)
        app.message_handler.clean_category('Mempool.space')
        message = Message(category='Mempool.space',
                          message_txt=f"<span class='text-success'>Using local server at {server_found[1]['url']}</span>")
        app.message_handler.add_message(message)

    # Wait 1 minute before running again
    time.sleep(60)


def background_specter_health():
    health = app.specter.is_healthy()
    if health is False:
        message = Message(category='Specter Server',
                          message_txt=f"<span class='text-danger'>Health Check Returned False at {app.specter.base_url}</span>")
        app.message_handler.add_message(message)
        health_text = pickle_it('load', 'specter_health.pkl')
        message = Message(category='Specter Server',
                          message_txt=f"<span class='text-danger'>Health Check Result: {health_text}</span>")
        app.message_handler.add_message(message)
        # Check for other URLs where Specter could be located
        seeker = app.specter.seek_specter()
        if seeker is not None:
            # Open Config and update
            config_file = Config.config_file
            config_settings = configparser.ConfigParser()
            config_settings.read(config_file)
            config_settings['SPECTER']['url'] = seeker['url']
            with open(config_file, 'w') as file:
                config_settings.write(file)

            message = Message(category='Specter Server',
                              message_txt=f"<span class='text-success'>Found an alternative server at {app.specter.base_url}.<br>Updated to use this server.</span>")
            app.message_handler.add_message(message)
            return
        else:
            message = Message(category='Specter Server',
                              message_txt=f"<span class='text-danger'>Could not find any alternative servers running</span>")
            app.message_handler.add_message(message)

    health_text = pickle_it('load', 'specter_health.pkl')
    message = Message(category='Specter Server',
                      message_txt=f"<span class='text-info'>Health Check Result: {health_text}</span>")
    app.message_handler.add_message(message)


def background_specter_update():
    ts = time.time()
    message = Message(category='Specter Server',
                      message_txt="<span class='text-info'>Starting Background Update</span>",
                      notes=f'Trying to reach Specter at {app.specter.base_url}')
    app.message_handler.add_message(message)

    # Is Specter reachable?
    if app.specter.is_reachable() is True:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-success'>Specter Server Found</span>",
                          notes=f'Reachable at {app.specter.base_url}')
        app.message_handler.add_message(message)
    else:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-danger'>Specter Server Unreacheable</span>",
                          notes=f'Tried at {app.specter.base_url}')
        app.message_handler.add_message(message)
        return

    # Is Authenticated?
    if app.specter.is_auth() is True:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-success'>Successfully Authenticated</span>",
                          notes=f'Reachable at {app.specter.base_url}')
        app.message_handler.add_message(message)
    else:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-danger'>Could not Authenticate - CHECK LOGIN CREDENTIALS</span>",
                          notes=f'Tried at {app.specter.base_url}')
        app.message_handler.add_message(message)
        return

    # OK To start running background jobs

    # Check if node is up and running
    message = Message(category='Specter Server',
                      message_txt="<span class='text-info'>Checking for Synch Status...</span>")
    app.message_handler.add_message(message)
    try:
        metadata = app.specter.home_parser(load=False)
        sync = metadata['bitcoin_core_is_syncing']
        if sync is False:
            message = Message(category='Specter Server',
                              message_txt="<span class='text-success'>Specter is connected to a fully synched node</span>")
            app.message_handler.add_message(message)
        else:
            message = Message(category='Specter Server',
                              message_txt="<span class='text-warning'>Specter is connected to a node that is still synching...</span>",
                              notes="Txs info may be outdated.")
            app.message_handler.add_message(message)

    except Exception as e:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-warning'>Could not check node from Specter</span>",
                          notes=f'{e}')
        app.message_handler.add_message(message)

    # Refresh Transactions
    message = Message(category='Specter Server',
                      message_txt="<span class='text-info'>Getting Specter TXs...</span>")
    app.message_handler.add_message(message)
    try:
        ts_t = time.time()
        txs = app.specter.refresh_txs(load=False)
        te_t = time.time()
        message = Message(category='Specter Server',
                          message_txt="<span class='text-success'>Finished Transaction Refresh</span>",
                          notes=f"<span class='text-info'>Loaded {len(txs['txlist'])} Transactions in {round((te_t - ts_t), 2)} seconds.</span>"
                          )
        app.message_handler.add_message(message)
    except Exception as e:
        message = Message(category='Specter Server',
                          message_txt="<span class='text-warning'>Could not get Transactions</span>",
                          notes=f'{e}')
        app.message_handler.add_message(message)
        return

    # Check wallets
    wallets = app.specter.wallet_alias_list(load=True)
    if wallets is None:
        app.specter.specter_reached = False
        specter_message = 'Having trouble finding Specter transactions. Check Specter Server.'
        flash(specter_message, 'warning')

    else:
        for wallet in wallets:
            ts_a = time.time()
            app.specter.wallet_info(wallet_alias=wallet, load=False)
            rescan = app.specter.rescan_progress(wallet_alias=wallet, load=False)
            te_a = time.time()
            message = Message(category='Specter Server',
                              message_txt=f"<span class='text-success'>Loaded wallet {wallet} </span>",
                              notes=f"Time to load: {round((te_a - ts_a), 2)} seconds. Rescan Info: {rescan} "
                              )
            app.message_handler.add_message(message)

    # Success
    te = time.time()
    message = Message(category='Specter Server',
                      message_txt="<span class='text-success'>Background Job for Specter Server Done</span>",
                      notes=f"Previous job took {round((te - ts), 2)} seconds to complete. Found {len(txs['txlist'])} Transactions."
                      )
    app.message_handler.add_message(message)
    app.downloading = False


def background_settings_update():
    app.message_handler.clean_category('NAV Calculation')
    config_file = Config.config_file
    config_settings = configparser.ConfigParser()
    config_settings.read(config_file)
    app.settings = config_settings
    app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
    ts = time.time()
    regenerate_nav()
    te = time.time()
    message = Message(category='NAV Calculation',
                      message_txt="<span class='text-success'>NAV Recalculated</span>",
                      notes=f"Calculation took {round((te - ts) * 1000, 2)} ms"
                      )
    app.message_handler.add_message(message)
    # Wait 5 seconds before running again
    time.sleep(5)


# Check Specter health
def specter_test(force=False):
    return_dict = {}
    messages = None
    # Load basic specter data
    try:
        specter = app.specter.init_session()
        if type(specter) == str:
            if 'Specter Error' in specter:
                return_dict['specter_status'] = 'Error'
                messages = specter
                return (return_dict, messages)

    except Exception as e:
        return_dict['specter_status'] = 'Error'
        messages = str(e)

    return (return_dict, messages)


def test_RealTimeBTC():
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


def background_scan_network():
    from connections import scan_network
    try:
        message = Message(category='Scanning Network',
                          message_txt="<span class='text-info'>Started Scanning Network for running services...</span>",
                          notes=""
                          )
        app.message_handler.add_message(message)
        ts = time.time()
        app.scan_network = scan_network()
        te = time.time()
        logging.info("Finished Scanning Network in Background")
        message = Message(category='Scanning Network',
                          message_txt="<span class='text-success'>Network Scan Finished</span>",
                          notes=f"Scan took {round((te - ts) * 1000, 2)} ms"
                          )
        app.message_handler.add_message(message)
    except Exception as e:
        message = Message(category='Scanning Network',
                          message_txt="<span class='text-danger'>Started Scanning Network returned an error</span>",
                          notes=f"{e}"
                          )
        app.message_handler.add_message(message)
