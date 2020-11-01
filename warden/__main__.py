import logging
import configparser
import os
import sys
import atexit
import json
import warnings

from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import (Flask, request, current_app,
                   has_request_context)

from flask_apscheduler import APScheduler
from flask_mail import Mail
from pathlib import Path

from warden.config import Config
from warden.utils import (create_config, update_config, specter_checks,
                          load_specter, specter_checks, specter_datafolder_check,
                          specter_library_check)
from warden.warden_pricing_engine import fxsymbol
from warden.warden import check_services


def create_app():
    # Config of Logging
    formatter = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(
        handlers=[RotatingFileHandler(
            filename=Config.debug_file,
            mode='w', maxBytes=512000, backupCount=2)],
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
    # Read Global Variables from config(s)
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
        print("  Config File could not be loaded, created a new one with default values...")
        create_config(config_file)
    with app.app_context():
        app.settings = config_settings
    with app.app_context():
        app.fx = fxsymbol(config_settings['PORTFOLIO']['base_fx'], 'all')
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

    from warden.routes import warden
    from warden.errors.handlers import errors
    app.register_blueprint(warden)
    app.register_blueprint(errors)

    # After app was created, make some important checks for Specter
    # 1. Specter data folder found / setup?
    # 2. Specter python library found?

    # Check Specter
    print("  Checking Specter Server status ...")
    specter_checks()
    print("  Loading Specter data ...")
    app.specter = load_specter()

    from warden.warden_pricing_engine import test_tor
    print("  Testing Tor ...")
    app.tor = test_tor()
    if app.tor:
        print("✓ Tor Running")
    else:
        print("  Tor disabled - check your connection or Tor browser")

    print("  Checking Services Status ...")
    app.services = check_services()

    print("✓ Application startup is complete")

    return app


def create_and_init():
    app = create_app()
    app.app_context().push()
    init_app(app)
    return app


print("  Launching Application ...")
app = create_app()
app.app_context().push()
init_app(app)

# Start Schedulers
print("  Starting Background Jobs ...")
with app.app_context():
    scheduler = APScheduler()
    scheduler.init_app(app)
if not scheduler.running:
    logging.info(
        "Starting Background Jobs: Upgrade Specter & get Service Status")
    with app.app_context():
        scheduler.start()


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
print("✓ WARden Server is Ready")
app.run(debug=app.settings['SERVER']['debug'],
        threaded=True,
        host='0.0.0.0',
        port=25442,
        use_reloader=True)
