import logging
import os

from datetime import datetime
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from flask_apscheduler import APScheduler
from flask_mail import Mail
# from flask_login import LoginManager

from warden.config import Config

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create the empty instances
mail = Mail()
# login_manager = LoginManager()

# Check size of debug.log file if it exists, if larger than maxsize, archive
try:
    debugfile = os.stat("debug.log")
    maxsize = 5 * 1024 * 1024  # 5MB max size - increase if needed more history
    if debugfile.st_size > maxsize:
        print("Startup message: Debug File size is larger than maxsize")
        print("Moving into archive")
        # rename file to include archive time and date
        archive_file = "debug_" + datetime.now().strftime(
            "%I%M%p_on_%B_%d_%Y") + ".log"
        archive_file = os.path.join("./debug_archive/", archive_file)
        os.rename("debug.log", archive_file)
except FileNotFoundError:
    pass

format_str = "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
handler = RotatingFileHandler("debug.log",
                              maxBytes=1 * 1024 * 1024,
                              backupCount=2)
logging.basicConfig(filename="debug.log",
                    level=logging.DEBUG,
                    format=format_str)
handler.setFormatter(format_str)
logging.captureWarnings(True)

# If login required - go to login:
# login_manager.login_view = "users.login"
# To display messages - info class (Bootstrap)
# login_manager.login_message_category = "info"
logging.info("Starting main program...")

services = {}


# ------------------------------------
# Application Factory
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    mail.init_app(app)
    # login_manager.init_app(app)

    # Start Schedulers
    scheduler = APScheduler()
    scheduler.init_app(app)

    if not scheduler.running:
        scheduler.start()

    from warden.routes import warden
    from warden.errors.handlers import errors
    app.register_blueprint(warden)
    app.register_blueprint(errors)

    @app.context_processor
    def jinja_shared():
        from warden.warden import check_services
        from warden.warden_pricing_engine import test_tor
        values = {
            'services': check_services(load=True, expiry=90),
            'tor': test_tor()
        }
        return dict(values)

    return app
