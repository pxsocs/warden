from config import Config
from backgroundjobs import (background_settings_update,
                            background_specter_update)
from utils import create_config, diags
from warden_pricing_engine import fxsymbol
from specter_importer import Specter
import logging
import configparser
import os
import sys
import atexit
import warnings

from logging.handlers import RotatingFileHandler
from flask import Flask

from flask_mail import Mail
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

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
        print("\033[1;36;40m  Config File could not be loaded, created a new one with default values...\033[1;37;40m")
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

    print(f"\033[1;37;40m  Running version: {version}\033[1;37;40m")

    with app.app_context():
        app.settings = config_settings
    with app.app_context():
        try:
            app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
        except KeyError:  # Problem with this config, reset
            print("\033[1;33;40m  [!] Config File needs to be rebuilt")
            create_config(config_file)
    # Debug Mode?
    #  To debug the application set an environment variable:
    #  EXPORT WARDEN_STATUS=developer
    WARDEN_STATUS = os.environ.get("WARDEN_STATUS")
    if ('-debug' in sys.argv or '-d' in sys.argv or WARDEN_STATUS == "developer"):
        print("  >> Debug is On")
        with app.app_context():
            app.settings['SERVER']['debug'] = 'True'
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("DEBUG MODE is on")

    from routes import warden
    from errors.handlers import errors
    app.register_blueprint(warden)
    app.register_blueprint(errors)

    # For the first load, just get a saved file if available
    # The background jobs will update later
    with app.app_context():
        app.specter = Specter()
        app.specter.refresh_txs(load=True)

    from warden_pricing_engine import test_tor
    print("\033[1;37;40m  Testing Tor ...")
    with app.app_context():
        app.tor = test_tor()
    if app.tor:
        print("\033[1;32;40m✓ Tor Running\033[1;37;40m")
    else:
        print("\033[1;33;40m  Tor disabled - check your connection or Tor browser")

    # Check if home folder exists, if not create
    home = str(Path.home())
    home_path = os.path.join(home, 'warden/')
    try:
        os.makedirs(os.path.dirname(home_path))
    except Exception:
        pass

    # Start Schedulers
    print("  Starting Background Jobs ...")

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

    print("\033[1;32;40m✓ Application startup is complete\033[1;37;40m")

    return app


def create_and_init():
    app = create_app()
    init_app(app)
    app.app_context().push()
    return app


def main():
    # Make sure current libraries are found in path
    current_path = os.path.abspath(os.path.dirname(__file__))
    # CLS + Welcome
    print("\033[1;32;40m")
    for _ in range(50):
        print("")

    print("\033[1;37;40m  Welcome to the WARden <> Launching Application ...")
    print(f"  [i] Running from: {current_path}")
    app = create_app()
    app.app_context().push()
    app = init_app(app)
    app.app_context().push()

    def close_running_threads():
        print(f"""
            \033[1;32;40m-----------------------------------------------------------------
            \033[1;37;40m                        Goodbye
            \033[1;37;40m             Keep Stacking. Keep Verifying.
            \033[1;32;40m-----------------------------------------------------------------
            """)

    # Register the def above to run at close
    atexit.register(close_running_threads)

    print("  Launching Server ...")
    print("\033[1;32;40m✓ WARden Server is Ready\033[1;37;40m")
    try:
        debug = app.settings['SERVER']['debug']
    except:
        debug = False

    print("\033[1;32;40m")
    for _ in range(50):
        print("")
    print(f"""
    \033[1;32;40m
    -----------------------------------------------------------------
         _   _           __        ___    ____     _
        | |_| |__   ___  \ \      / / \  |  _ \ __| | ___ _ __
        | __| '_ \ / _ \  \ \ /\ / / _ \ | |_) / _` |/ _ \ '_  |
        | |_| | | |  __/   \ V  V / ___ \|  _ < (_| |  __/ | | |
         \__|_| |_|\___|    \_/\_/_/   \_\_| \_\__,_|\___|_| |_|
                                          Specter Server Edition
    -----------------------------------------------------------------
    \033[1;37;40m       Privacy Focused Portfolio & Bitcoin Address Tracker
    \033[1;32;40m-----------------------------------------------------------------
    \033[1;37;40m                      Application Loaded
    \033[1;32;40m-----------------------------------------------------------------
    \033[1;37;40m                Open your browser and navigate to:
    \033[1;37;40m
    \033[1;37;40m                     http://localhost:5000/
    \033[1;37;40m                               or
    \033[1;37;40m                     http://127.0.0.1:5000/
    \033[1;32;40m-----------------------------------------------------------------
    \033[1;37;40m                     CTRL + C to quit server
    \033[1;32;40m-----------------------------------------------------------------
    \033[1;37;40m
    """)

    app.run(debug=debug,
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
