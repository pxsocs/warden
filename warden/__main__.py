from flask.globals import current_app
from yaspin import yaspin
import logging
import subprocess
import configparser
import os
import sys
import atexit
import warnings
import socket
import emoji
import time
import sqlite3
import requests
from logging.handlers import RotatingFileHandler
from packaging import version
from ansi.colour import fg
from flask import Flask
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from ansi_management import (warning, success, error, info, clear_screen,
                             muted, yellow, blue)


# Make sure current libraries are found in path
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)


def create_app():
    # Config of Logging
    from config import Config
    formatter = "[%(asctime)s] {%(module)s:%(funcName)s:%(lineno)d} %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(
        handlers=[RotatingFileHandler(
            filename=str(Config.debug_file),
            mode='w', maxBytes=120000, backupCount=0)],
        level=logging.INFO,
        format=formatter,
        datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.getLogger('apscheduler').setLevel(logging.CRITICAL)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.info("Starting main program...")

    # Launch app
    app = Flask(__name__)
    app.config.from_object(Config)

    return app


def create_tor():
    from ansi_management import (warning, success, error, info, clear_screen, bold,
                                 muted, yellow, blue)
    from config import Config
    # ----------------------------------------------
    #                 Test Tor
    # ----------------------------------------------
    with yaspin(text="Testing Tor", color="cyan") as spinner:
        from connections import test_tor
        tor = test_tor()
        if tor['status']:
            logging.info(success("Tor Connected"))
            spinner.ok("✅ ")
            spinner.text = success("    Tor Connected [Success]")
            print("")
            return (tor)
        else:
            logging.error(error("Could not connect to Tor"))
            spinner.fail("💥 ")
            spinner.text = warning("    Tor NOT connected [ERROR]")
            print(
                error(
                    "    Could not connect to Tor."
                ))

            print(
                info(
                    "    [i] If you have a Tor Browser installed try opening (leave it running) and try again."
                ))

            print(
                info(
                    "    [i] If you are running Linux try the command: "
                ) + yellow('service tor start'))
            print(
                info(
                    "    or download Tor at: https://www.torproject.org/download/"
                ))
            print("")


# ------------------------------------
# Application Factory
def init_app(app):
    from ansi_management import (warning, success, error)
    from utils import (create_config, runningInDocker)
    from config import Config
    from connections import tor_request
    warnings.filterwarnings('ignore')

    # Load config.ini into app
    # --------------------------------------------
    # Read Global Variables from warden.config(s)
    # Can be accessed like a dictionary like:
    # app.settings['PORTFOLIO']['RENEW_NAV']
    # --------------------------------------------
    config_file = Config.config_file
    app.warden_status = {}
    # Config
    config_settings = configparser.ConfigParser()
    if os.path.isfile(config_file):
        config_settings.read(config_file)
        app.warden_status['initial_setup'] = False
        print(success("✅ Config Loaded from config.ini - edit it for customization"))
    else:
        print(error("  Config File could not be loaded, created a new one with default values..."))
        create_config(config_file)
        config_settings.read(config_file)
        app.warden_status['initial_setup'] = True

    table_error = False
    try:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()
    except sqlite3.OperationalError:
        table_error = True

    # Create empty instance of SQLAlchemy
    app.db = SQLAlchemy()
    app.db.init_app(app)
    # Import models so tables are created
    from models import Trades, User, AccountInfo, TickerInfo, SpecterInfo
    app.db.create_all()

    #  There was an initial error on getting users
    #  probably because tables were not created yet.
    # The above create_all should have solved it so try again.
    if table_error:
        # create empty instance of LoginManager
        app.login_manager = LoginManager()

    # If login required - go to login:
    app.login_manager.login_view = "warden.login"
    # To display messages - info class (Bootstrap)
    app.login_manager.login_message_category = "secondary"
    app.login_manager.init_app(app)

    # Create empty instance of messagehandler
    from message_handler import MessageHandler
    app.message_handler = MessageHandler()
    app.message_handler.clean_all()

    # Get Version
    print("")
    try:
        version_file = Config.version_file
        with open(version_file, 'r') as file:
            current_version = file.read().replace('\n', '')
    except Exception:
        current_version = 'unknown'
    with app.app_context():
        app.version = current_version

    # Check if there are any users on database, if not, needs initial setup
    users = User.query.all()
    if users == []:
        app.warden_status['initial_setup'] = True

    # Check for Cryptocompare API Keys
    print("")
    check_cryptocompare()
    print("")

    print(f"[i] Running WARden version: {current_version}")
    app.warden_status['running_version'] = current_version

    # CHECK FOR UPGRADE
    repo_url = 'https://api.github.com/repos/pxsocs/warden/releases'
    try:
        github_version = tor_request(repo_url).json()[0]['tag_name']
    except Exception:
        github_version = None

    app.warden_status['github_version'] = github_version

    if github_version:
        print(f"[i] Newest WARden version available: {github_version}")
        parsed_github = version.parse(github_version)
        parsed_version = version.parse(current_version)

        app.warden_status['needs_upgrade'] = False
        if parsed_github > parsed_version:
            print(warning("  [i] Upgrade Available"))
            app.warden_status['needs_upgrade'] = True
        if parsed_github == parsed_version:
            print(success("✅ You are running the latest version"))
    else:
        print(warning("[!] Could not check GitHub for updates"))

    print("")
    # Check if config.ini exists
    with app.app_context():
        app.settings = config_settings
    with app.app_context():
        try:
            from utils import fxsymbol
            app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
        except KeyError:  # Problem with this config, reset
            print(error("  [!] Config File needs to be rebuilt"))
            print("")
            create_config(config_file)

    # TOR Server through Onion Address --
    # USE WITH CAUTION - ONION ADDRESSES CAN BE EXPOSED!
    # WARden needs to implement authentication (coming soon)
    if app.settings['SERVER'].getboolean('onion_server'):
        from stem.control import Controller
        from urllib.parse import urlparse
        app.tor_port = app.settings['SERVER'].getint('onion_port')
        app.port = app.settings['SERVER'].getint('port')
        from warden_modules import home_path
        toraddr_file = os.path.join(home_path(), "onion.txt")
        app.save_tor_address_to = toraddr_file
        proxy_url = "socks5h://localhost:9050"
        tor_control_port = ""
        try:
            tor_control_address = urlparse(proxy_url).netloc.split(":")[0]
            if tor_control_address == "localhost":
                tor_control_address = "127.0.0.1"
            app.controller = Controller.from_port(
                address=tor_control_address,
                port=int(tor_control_port)
                if tor_control_port
                else "default",
            )
        except Exception:
            app.controller = None
        from tor import start_hidden_service
        start_hidden_service(app)

    from routes import warden
    from errors.handlers import errors
    from api.routes import api
    from csv_routes.routes import csv_routes
    from user_routes.routes import user_routes
    from simulator.routes import simulator
    app.register_blueprint(warden)
    app.register_blueprint(errors)
    app.register_blueprint(api)
    app.register_blueprint(csv_routes)
    app.register_blueprint(user_routes)
    app.register_blueprint(simulator)

    # Prepare app to receive Specter Server info
    # For the first load, just get a saved file if available
    # The background jobs will update later
    with app.app_context():
        from specter_importer import Specter
        app.specter = Specter()
        app.specter.refresh_txs(load=True)
        app.downloading = False

    with app.app_context():
        app.runningInDocker = runningInDocker()

    with app.app_context():
        app.tor = create_tor()

    # Check if home folder exists, if not create
    home = str(Path.home())
    home_path = os.path.join(home, 'warden/')
    try:
        os.makedirs(os.path.dirname(home_path))
    except Exception:
        pass

    # Start Schedulers
    from backgroundjobs import (background_settings_update,
                                background_specter_update,
                                background_scan_network,
                                background_specter_health,
                                background_mempool_seeker)

    def bk_su():
        with app.app_context():
            background_specter_update()

    def bk_stu():
        with app.app_context():
            background_settings_update()

    def bk_scan():
        with app.app_context():
            background_scan_network()

    def bk_specter_health():
        with app.app_context():
            background_specter_health()

    def bk_mempool_health():
        with app.app_context():
            background_mempool_seeker()

    app.scheduler = BackgroundScheduler()
    app.scheduler.add_job(bk_su, 'interval', seconds=1)
    app.scheduler.add_job(bk_stu, 'interval', seconds=1)
    app.scheduler.add_job(bk_scan, 'interval', seconds=1)
    app.scheduler.add_job(bk_specter_health, 'interval', seconds=1)
    app.scheduler.add_job(bk_mempool_health, 'interval', seconds=1)
    app.scheduler.start()
    print(success("✅ Background jobs running"))
    print("")
    app.app_context().push()

    print(success("✅ Application startup is complete"))

    return app


def check_cryptocompare():
    from utils import pickle_it

    with yaspin(text="Testing price grab from Cryptocompare",
                color="green") as spinner:
        data = {'Response': 'Error', 'Message': None}
        try:
            api_key = pickle_it('load', 'cryptocompare_api.pkl')
            if api_key != 'file not found':
                baseURL = (
                    "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                    + "&tsyms=USD&api_key=" + api_key)
                req = requests.get(baseURL)
                data = req.json()
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.text = (success(f"BTC price is: {btc_price}"))
                spinner.ok("✅ ")
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            else:
                data = {'Response': 'Error', 'Message': 'No API Key is set'}
        except Exception as e:
            data = {'Response': 'Error', 'Message': str(e)}
            logging.error(data)

        try:
            if data['Response'] == 'Error':
                spinner.color = 'yellow'
                spinner.text = "CryptoCompare Returned an error " + data[
                    'Message']
                # ++++++++++++++++++++++++++
                #  Load Legacy
                # ++++++++++++++++++++++++++
                try:
                    # Let's try to use one of the
                    # legacy api keys stored under cryptocompare_api.keys file
                    # You can add as many as you'd like there
                    filename = 'warden/static/cryptocompare_api.keys'
                    file = open(filename, 'r')
                    for line in file:
                        legacy_key = str(line)

                        spinner.text = (
                            warning(f"Trying different API Keys..."))

                        baseURL = (
                            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC"
                            + "&tsyms=USD&api_key=" + legacy_key)

                        try:
                            data = None
                            logging.debug(f"Trying API Key {legacy_key}")
                            request = requests.get(baseURL)
                            data = request.json()
                            btc_price = (
                                data['DISPLAY']['BTC']['USD']['PRICE'])
                            spinner.text = (
                                success(f"BTC price is: {btc_price}"))
                            spinner.ok("✅ ")
                            logging.debug(f"API Key {legacy_key} Success")
                            pickle_it('save', 'cryptocompare_api.pkl',
                                      legacy_key)
                            return
                        except Exception as e:
                            logging.debug(f"API Key {legacy_key} ERROR: {e}")
                            logging.debug(
                                f"API Key {legacy_key} Returned: {data}")
                            spinner.text = "Didn't work... Trying another."
                except Exception:
                    pass
                spinner.text = (error("Failed to get API Key - read below."))
                spinner.fail("[!]")
                print(
                    '    -----------------------------------------------------------------'
                )
                print(yellow("    Looks like you need to get an API Key. "))
                print(yellow("    The WARden comes with a shared key that"))
                print(yellow("    eventually gets to the call limit."))
                print(
                    '    -----------------------------------------------------------------'
                )
                print(
                    yellow(
                        '    Go to: https://www.cryptocompare.com/cryptopian/api-keys'
                    ))
                print(
                    yellow(
                        '    To get an API Key. Keys from cryptocompare are free.'
                    ))
                print(
                    yellow(
                        '    [Tip] Get a disposable email to signup and protect privacy.'
                    ))
                print(
                    yellow(
                        '    Services like https://temp-mail.org/en/ work well.'
                    ))

                print(muted("    Current API:"))
                print(f"    {api_key}")
                new_key = input('    Enter new API key (Q to quit): ')
                if new_key == 'Q' or new_key == 'q':
                    exit()
                pickle_it('save', 'cryptocompare_api.pkl', new_key)
                check_cryptocompare()
        except KeyError:
            try:
                btc_price = (data['DISPLAY']['BTC']['USD']['PRICE'])
                spinner.ok("✅ ")
                spinner.write(success(f"BTC price is: {btc_price}"))
                pickle_it('save', 'cryptocompare_api.pkl', api_key)
                return
            except Exception:
                spinner.text = (
                    warning("CryptoCompare Returned an UNKNOWN error"))
                spinner.fail("💥 ")
        return (data)


def get_local_ip():
    from utils import pickle_it
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    local_ip_address = s.getsockname()[0]
    pickle_it('save', 'local_ip_address.pkl', local_ip_address)
    return (local_ip_address)


def goodbye():
    for n in range(0, 100):
        print("")
    print(
        fg.brightgreen(f"""
   \ \ / (_)_ _ ___ ___
    \ V /| | '_/ -_|_-<
     \_/ |_|_| \___/__/
           (_)_ _
    _  _   | | '  |         _
   | \| |_ |_|_||_| ___ _ _(_)___
   | .` | || | '  \/ -_) '_| (_-<
   |_|\_|\_,_|_|_|_\___|_| |_/__/
"""))

    print(fg.boldyellow("    If you enjoyed the app..."))
    print("")
    print(
        fg.brightgreen(
            "    tipping.me (Lightning): https://tippin.me/@alphaazeta"))
    print("")
    print(
        fg.brightgreen(
            "    onchain: bc1q4fmyksw40vktte9n6822e0aua04uhmlez34vw5gv72zlcmrkz46qlu7aem"
        ))
    print("")
    print(fg.brightgreen("    payNym: +luckyhaze615"))
    print(fg.brightgreen("    https://paynym.is/+luckyhaze615"))
    print("")


def main(debug=False, reloader=False):
    from utils import (create_config, runningInDocker)
    from ansi_management import (warning, success, error, info, clear_screen, bold,
                                 muted, yellow, blue)

    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))

    # CLS + Welcome
    print("")
    print("")
    print(yellow("Welcome to the WARden <> Launching Application ..."))
    print("")
    print(f"[i] Running from directory: {current_path}")
    print("")

    if runningInDocker():
        print(success(f"✅ Running inside docker container {emoji.emojize(':whale:')} Getting some James Bartley vibes..."))
        print("")

    app = create_app()
    app.app_context().push()
    app = init_app(app)
    app.app_context().push()

    def close_running_threads(app):
        print("")
        print("")
        print(yellow("[i] Please Wait... Shutting down."))
        # Delete Debug File
        try:
            from config import Config
            os.remove(Config.debug_file)
        except FileNotFoundError:
            pass
        # Clean all messages
        app.message_handler.clean_all()
        # Breaks background jobs
        app.scheduler.shutdown(wait=False)
        goodbye()
        os._exit(1)

    # Register the def above to run at close
    atexit.register(close_running_threads, app)

    print("")
    print(success("✅ WARden Server is Ready... Launch cool ASCII logo!"))
    print("")

    def onion_string():
        from utils import pickle_it
        if app.settings['SERVER'].getboolean('onion_server'):
            try:
                pickle_it('save', 'onion_address.pkl', app.tor_service_id + '.onion')
                return (f"""
        {emoji.emojize(':onion:')} Tor Onion server running at:
        {yellow(app.tor_service_id + '.onion')}
                    """)
            except Exception:
                return (yellow("[!] Tor Onion Server Not Running"))
        else:
            return ('')

    def local_network_string():
        host = app.settings['SERVER'].get('host')
        port = str(app.settings['SERVER'].getint('port'))
        if app.runningInDocker:
            return ('')
        else:
            if host == '0.0.0.0':
                return (f"""
      Or through your network at address:
      {yellow('http://')}{yellow(get_local_ip())}{yellow(f':{port}/')}
                """)

    port = str(app.settings['SERVER'].getint('port'))

    print(
        fg.brightgreen("""
        _   _           __        ___    ____     _
       | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
       | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
       | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
        \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))

    print(f"""
                                    {yellow("Powered by NgU technology")} {emoji.emojize(':rocket:')}


           Privacy Focused Portfolio & Bitcoin Address Tracker
    -----------------------------------------------------------------
                          Application Loaded

      Open your browser and navigate to one of these addresses:
      {yellow('http://localhost:' + str(port) + '/')}
      {yellow('http://127.0.0.1:' + str(port) + '/')}
      {local_network_string()}
      {onion_string()}
    ----------------------------------------------------------------
                         CTRL + C to quit server
    ----------------------------------------------------------------

    """)

    app.run(debug=debug,
            threaded=True,
            host=app.settings['SERVER'].get('host'),
            port=app.settings['SERVER'].getint('port'),
            use_reloader=reloader)

    if app.settings['SERVER'].getboolean('onion_server'):
        from tor import stop_hidden_services
        stop_hidden_services(app)


if __name__ == '__main__':
    # Run Diagnostic Function
    from ansi_management import yellow
    debug = False
    reloader = False
    if "debug" in sys.argv:
        print("")
        print(yellow("  [i] DEBUG MODE: ON"))
        debug = True
    if "reloader" in sys.argv:
        print("")
        print(yellow("  [i] RELOAD MODE: ON"))
        reloader = True
    main(debug=debug, reloader=reloader)
