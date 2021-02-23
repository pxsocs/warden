import os
import configparser
from pathlib import Path

home_path = Path.home()
# make directory to store all private data at /home/warden
# /root/warden/
home_dir = os.path.join(home_path, 'warden')
try:
    os.mkdir(home_dir)
except Exception:
    pass


def create_config():
    basedir = os.path.abspath(os.path.dirname(__file__))
    home_dir = os.path.join(home_path, 'warden')

    default_config_file = os.path.join(basedir, 'static/config/config_default.ini')
    config_file = os.path.join(home_dir, 'config.ini')

    # Get the default config and save into config.ini
    default_file = default_config_file
    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)

    return(default_config)

# Config class for Application Factory


class Config:
    home_dir = os.path.join(home_path, 'warden')
    basedir = os.path.abspath(os.path.dirname(__file__))

    # You should change this secret key. But make sure it's done before any data
    # is included in the database
    SECRET_KEY = "24feff264xscdcjncdjdcjuu212i"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(home_dir, "warden.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    debug_file = os.path.join(home_dir, 'debug.log')

    version_file = os.path.join(basedir, 'static/config/version.txt')

    default_config_file = os.path.join(basedir, 'static/config/config_default.ini')
    config_file = os.path.join(home_dir, 'config2.ini')

    # Check if config file exists
    file_config_file = Path(config_file)
    if not file_config_file.is_file():
        create_config()

    # Used for notifications --- FUTURE FEATURE
    MAIL_SERVER = "smtp.googlemail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Pretty print json
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Do not start new job until the last one is done
    SCHEDULER_JOB_DEFAULTS = {'coalesce': False, 'max_instances': 1}
    SCHEDULER_API_ENABLED = True
