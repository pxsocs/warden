from config import Config
from utils import create_config, diags
from specter_importer import Specter
from yaspin import yaspin
import logging
import configparser
import os
import sys
import atexit
import warnings
import socket
import emoji
from logging.handlers import RotatingFileHandler
from flask import Flask
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
            filename=Config.debug_file,
            mode='w', maxBytes=120000, backupCount=0)],
        level=logging.INFO,
        format=formatter,
        datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger('WARden')
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
            spinner.write(success("    Tor Connected [Success]"))
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


# ------------------------------------
# Application Factory
def init_app(app):
    warnings.filterwarnings('ignore')
    # Create the empty Mail instance
    mail = Mail()
    mail.init_app(app)

    # Load config.ini into app
    # --------------------------------------------
    # Read Global Variables from warden.config(s)
    # Can be accessed like a dictionary like:
    # app.settings['PORTFOLIO']['RENEW_NAV']
    # --------------------------------------------
    print("  Getting Config ...")
    config_file = Config.config_file
    os.path.isfile(config_file)
    # create empty instance
    config_settings = configparser.ConfigParser()
    if os.path.isfile(config_file):
        config_settings.read(config_file)
    else:
        print(error("  Config File could not be loaded, created a new one with default values..."))
        create_config(config_file)
        config_settings.read(config_file)

    # Get Version
    try:
        version_file = Config.version_file
        with open(version_file, 'r') as file:
            version = file.read().replace('\n', '')
    except Exception:
        version = 'unknown'
    with app.app_context():
        app.version = version

    print(f"  Running version: {version}")

    with app.app_context():
        app.settings = config_settings
    with app.app_context():
        try:
            from warden_pricing_engine import fxsymbol
            app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
        except KeyError:  # Problem with this config, reset
            print(error("  [!] Config File needs to be rebuilt"))
            create_config(config_file)

    from routes import warden
    from errors.handlers import errors
    app.register_blueprint(warden)
    app.register_blueprint(errors)

    # For the first load, just get a saved file if available
    # The background jobs will update later
    with app.app_context():
        app.specter = Specter()
        app.specter.refresh_txs(load=True)

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
    print("  Starting Background Jobs ...")

    from backgroundjobs import (background_settings_update,
                                background_specter_update)

    def bk_su():
        with app.app_context():
            background_specter_update()

    def bk_stu():
        with app.app_context():
            background_settings_update()

    scheduler = BackgroundScheduler()
    scheduler.add_job(bk_su, 'interval', seconds=30)
    scheduler.add_job(bk_stu, 'interval', seconds=60)

    scheduler.start()

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


def main():
    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))
    # CLS + Welcome
    print("  Welcome to the WARden <> Launching Application ...")
    print(f"  [i] Running from: {current_path}")
    app = create_app()
    app.app_context().push()
    app = init_app(app)
    app.app_context().push()

    def close_running_threads():
        print(f"""
            -----------------------------------------------------------------
                                    Goodbye
                         Keep Stacking. Keep Verifying.
            -----------------------------------------------------------------
            """)

    # Register the def above to run at close
    atexit.register(close_running_threads)

    print("  Launching Server ...")
    print(success("✅ WARden Server is Ready"))

    print(f"""

         _   _           __        ___    ____     _
        | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
        | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
        | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
         \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|
                                    Specter Server Edition {emoji.emojize(':key: :ghost:')}

           Privacy Focused Portfolio & Bitcoin Address Tracker
    -----------------------------------------------------------------
                          Application Loaded

      Open your browser and navigate to one of these addresses:
      {yellow('http://localhost:5000/')}
      {yellow('http://127.0.0.1:5000/')}
      Or through your network at address:
      {yellow('http://')}{yellow(get_local_ip())}{yellow(':5000/')}
    -----------------------------------------------------------------
                         CTRL + C to quit server
    -----------------------------------------------------------------

    """)

    app.run(debug=False,
            threaded=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=False)


if __name__ == '__main__':
    # Run Diagnostic Function
    if "--diag" in sys.argv:
        diags()
        exit()
    main()
