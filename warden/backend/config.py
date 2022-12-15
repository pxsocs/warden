import os
import configparser
import logging
import secrets
from pathlib import Path

home = Path.home()
# make directory to store all private data at /home/.warden
# /root/.warden/
home_dir = os.path.join(home, '.warden/')

import __main__

basedir = os.path.abspath(os.path.dirname(__main__.__file__))
# Check if the home directory exists, if not create it
try:
    os.mkdir(home_dir)
except Exception:
    pass


def create_config():

    default_config_file = os.path.join(basedir,
                                       'static/config/config_default.ini')
    config_file = os.path.join(home_dir, 'config.ini')

    # Get the default config and save into config.ini
    default_file = default_config_file
    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)

    return (default_config)


# Config class for Application Factory
class Config:
    import __main__
    basedir = os.path.abspath(os.path.dirname(__main__.__file__))

    # Check if secret key exists, if not create it
    from backend.utils import pickle_it
    # Try loading it from home directory
    sk = pickle_it('load', 'secret_key.pkl')
    # Not found, create it and save
    if sk == 'file not found':
        sk = secrets.token_urlsafe(16)
        pickle_it('save', 'secret_key.pkl', sk)
    SECRET_KEY = sk

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        home_dir, "warden.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    debug_file = os.path.join(home_dir, 'debug.log')

    version_file = os.path.join(basedir, 'static/config/version.txt')

    default_config_file = os.path.join(basedir,
                                       'static/config/config_default.ini')
    config_file = os.path.join(home_dir, 'config.ini')

    # Check if config file exists
    file_config_file = Path(config_file)
    if not file_config_file.is_file() or os.stat(
            file_config_file).st_size == 0:
        # File does not exist, create config file
        print("[i] Config.ini not found. Creating config file from default...")
        create_config()

    # Used for notifications --- FUTURE FEATURE
    MAIL_SERVER = os.environ.get("EMAIL_SERVER")
    MAIL_PORT = os.environ.get("EMAIL_PORT")
    MAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS")
    MAIL_USERNAME = os.environ.get("EMAIL_USER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Pretty print json
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Do not start new job until the last one is done
    SCHEDULER_JOB_DEFAULTS = {'coalesce': False, 'max_instances': 1}
    SCHEDULER_API_ENABLED = True


def update_config(app, config_file=Config.config_file):
    logging.info("Updating Config file")
    with open(config_file, 'w') as file:
        app.settings.write(file)


def load_config(config_file=Config.config_file):
    # Load Config
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    return (CONFIG)
