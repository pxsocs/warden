from config import Config
from utils import (create_config, diags, runningInDocker)
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
from logging.handlers import RotatingFileHandler
from ansi.colour import fg
from flask import Flask
from flask_login import LoginManager, current_user
from flask_mail import Mail
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from ansi_management import (warning, success, error, info, clear_screen, bold,
                             muted, yellow, blue)


# Make sure current libraries are found in path
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(current_path)


def create_app():
    # Config of Logging
    formatter = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(
        handlers=[RotatingFileHandler(
            filename=str(Config.debug_file),
            mode='w', maxBytes=120000, backupCount=0)],
        level=logging.INFO,
        format=formatter,
        datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.info("Starting main program...")

    # Launch app
    app = Flask(__name__)
    app.config.from_object(Config)

    return app


def create_tor():
    # ----------------------------------------------
    #                 Test Tor
    # ----------------------------------------------
    with yaspin(text="Testing Tor", color="cyan") as spinner:
        from warden_pricing_engine import test_tor
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
                    "    Could not connect to Tor. WARden requires Tor to run. Quitting..."
                ))
            print(
                info(
                    "    Download Tor at: https://www.torproject.org/download/"
                ))
            print("    [i] Tor Diagnostic:")
            print(tor)
            print("")
            exit()


# ------------------------------------
# Application Factory
def init_app(app):
    warnings.filterwarnings('ignore')
    # Create the empty Mail instance
    # mail = Mail()
    # mail.init_app(app)

    # Load config.ini into app
    # --------------------------------------------
    # Read Global Variables from warden.config(s)
    # Can be accessed like a dictionary like:
    # app.settings['PORTFOLIO']['RENEW_NAV']
    # --------------------------------------------
    config_file = Config.config_file
    os.path.isfile(config_file)

    # Config
    config_settings = configparser.ConfigParser()
    if os.path.isfile(config_file):
        config_settings.read(config_file)
        print(success("✅ Config Loaded from config.ini - edit it for customization"))
    else:
        print(error("  Config File could not be loaded, created a new one with default values..."))
        create_config(config_file)
        config_settings.read(config_file)

    # Check if password has been set
    # if no password set - send to register
    if not config_settings.has_option('SETUP', 'hash'):
        print(yellow("  [i] This is a new setup. Welcome to WARden."))
        print(yellow("  [i] No login password found. Will ask you to create a new one."))

    # create empty instance
    app.login_manager = LoginManager()
    # If login required - go to login:
    app.login_manager.login_view = "warden.login"
    # To display messages - info class (Bootstrap)
    app.login_manager.login_message_category = "secondary"
    app.login_manager.init_app(app)

    # Get Version
    print("")
    try:
        version_file = Config.version_file
        with open(version_file, 'r') as file:
            version = file.read().replace('\n', '')
    except Exception:
        version = 'unknown'
    with app.app_context():
        app.version = version

    print(f"  [i] Running version: {version}")
    print("")

    # Check if config.ini exists
    with app.app_context():
        app.settings = config_settings
    with app.app_context():
        try:
            from warden_pricing_engine import fxsymbol
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
    app.register_blueprint(warden)
    app.register_blueprint(errors)
    app.register_blueprint(api)

    # For the first load, just get a saved file if available
    # The background jobs will update later
    print("  [i] Checking if Specter Server was configured...")
    print("")
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
                                background_specter_update)

    def bk_su():
        with app.app_context():
            background_specter_update()
            app.downloading = False

    def bk_stu():
        with app.app_context():
            background_settings_update()

    app.scheduler = BackgroundScheduler()
    app.scheduler.add_job(bk_su, 'interval', seconds=30)
    app.scheduler.add_job(bk_stu, 'interval', seconds=60)

    app.scheduler.start()
    print(success("✅ Background jobs running"))
    print("")
    app.app_context().push()

    print(success("✅ Application startup is complete"))

    return app


def create_and_init():
    app = create_app()
    init_app(app)
    app.app_context().push()
    return app


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    local_ip_address = s.getsockname()[0]
    return (local_ip_address)


def main(debug=False):

    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))

    # CLS + Welcome
    print("")
    print("")
    print(yellow("  Welcome to the WARden <> Launching Application ..."))
    print("")
    print(f"  [i] Running from directory: {current_path}")
    print("")

    if runningInDocker():
        print(success(f"✅ Running inside docker container {emoji.emojize(':whale:')}"))
        # Try to start Tor if in docker container
        print("")

    app = create_app()
    app.app_context().push()
    app = init_app(app)
    app.app_context().push()

    def close_running_threads(app):
        print("")
        print("")
        print(yellow("  [i] Please Wait... Shutting down."))
        app.scheduler.shutdown(wait=False)
        print("""
                           Goodbye &
                         Keep Stacking
            """)
        print("")

    # Register the def above to run at close
    atexit.register(close_running_threads, app)

    print("")
    print(success("✅ WARden Server is Ready... Launch cool ASCII logo!"))
    print("")

    def onion_string():
        if app.settings['SERVER'].getboolean('onion_server'):
            return (f"""
      {emoji.emojize(':onion:')} Tor Onion server running at:
      {yellow(app.tor_service_id + '.onion')}
                """)
        else:
            return ('')

    def local_network_string():
        host = app.settings['SERVER'].get('host')
        if app.runningInDocker:
            return ('')
        else:
            if host == '0.0.0.0':
                return (f"""
      Or through your network at address:
      {yellow('http://')}{yellow(get_local_ip())}{yellow(':5000/')}
                """)

    print(
        fg.brightgreen("""
        _   _           __        ___    ____     _
       | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
       | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
       | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
        \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|"""))

    print(f"""
                                    {yellow("Specter Server Edition")} {emoji.emojize(':key: :ghost:')}
                                    {yellow("Powered by NgU technology")} {emoji.emojize(':rocket:')}


           Privacy Focused Portfolio & Bitcoin Address Tracker
    -----------------------------------------------------------------
                          Application Loaded

      Open your browser and navigate to one of these addresses:
      {yellow('http://localhost:5000/')}
      {yellow('http://127.0.0.1:5000/')}
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
            use_reloader=False)

    if app.settings['SERVER'].getboolean('onion_server'):
        from tor import stop_hidden_services
        stop_hidden_services(app)


if __name__ == '__main__':
    # Run Diagnostic Function
    debug = False
    if "debug" in sys.argv:
        print("")
        print(yellow("  [i] DEBUG MODE: ON"))
        debug = True
    main(debug=debug)
