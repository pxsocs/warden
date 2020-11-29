from warden_modules import (check_services, specter_update, wallets_update)
from warden_pricing_engine import fxsymbol
from utils import (create_config, update_config,
                   load_specter, specter_checks,
                   load_wallets, diags, create_specter_session)
from backgroundjobs import (background_services_update,
                            background_settings_update,
                            background_specter_update,
                            background_wallets_update)
from config import Config
import logging
import configparser
import os
import sys
import atexit
import json
import warnings
import inspect

from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import (Flask, request, current_app,
                   has_request_context)

from flask_mail import Mail
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler


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
            print("[!] Config File needs to be rebuilt")
            create_config(config_file)
    # Debug Mode?
    #  To debug the application set an environment variable:
    #  EXPORT WARDEN_STATUS=developer
    flask_debug = False
    WARDEN_STATUS = os.environ.get("WARDEN_STATUS")
    if 'debug' in sys.argv or WARDEN_STATUS == "developer":
        print("  >> Debug is On")
        with app.app_context():
            app.settings['SERVER']['debug'] = 'True'
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("DEBUG MODE is on")

    from routes import warden
    from errors.handlers import errors
    app.register_blueprint(warden)
    app.register_blueprint(errors)

    specter_login_success = False

    while not specter_login_success:
        # Create Specter Session
        with app.app_context():
            app.specter_session = create_specter_session()
        if app.specter_session == 'unauthorized':
            print("\033[1;33;40m  [UNAUTHORIZED] Could not login to Specter - check username and password.")
            input_username = (input(f"  >> Specter Username [{app.settings['SPECTER']['specter_login']}] : "))
            input_password = (input(f"  >> Specter Password [{app.settings['SPECTER']['specter_password']}] : "))
            if input_username:
                app.settings['SPECTER']['specter_login'] = input_username
            if input_password:
                app.settings['SPECTER']['specter_password'] = input_password
            update_config()
        else:
            specter_login_success = True

    print("\033[1;32;40m✓ Logged in to Specter Server\033[1;37;40m")

    # Check Specter
    print("\033[1;37;40m  Checking Specter Server status ...")
    specter_checks()
    print("\033[1;37;40m  Loading Specter data ...")
    # For the first load, just get a saved file if available
    # The background jobs will update later
    with app.app_context():
        app.specter = specter_update(load=True)

    print("\033[1;37;40m  Loading Wallets data ...")
    with app.app_context():
        app.wallets = wallets_update(load=True)

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

    print("  Checking Services Availability ...")
    with app.app_context():
        app.services = check_services()

    # Start Schedulers
    print("  Starting Background Jobs ...")

    def bk_su():
        with app.app_context():
            background_specter_update()

    def bk_wu():
        with app.app_context():
            background_wallets_update()

    def bk_svu():
        with app.app_context():
            background_services_update

    def bk_stu():
        with app.app_context():
            background_settings_update()

    scheduler = BackgroundScheduler()
    scheduler.add_job(bk_su, 'interval', seconds=30)
    scheduler.add_job(bk_wu, 'interval', seconds=30)
    scheduler.add_job(bk_svu, 'interval', seconds=60)
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
    # CLS + Welcome

    print("  Launching Application ...")
    app = create_app()
    app.app_context().push()
    app = init_app(app)
    app.app_context().push()

    def close_running_threads():
        print(f"""
            \033[1;32;40m-----------------------------------------------------------------
            \033[1;37;40m              Shutting Down.... Please Wait.
            \033[1;32;40m-----------------------------------------------------------------
            """)

        print(f"""
            \033[1;32;40m-----------------------------------------------------------------
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
