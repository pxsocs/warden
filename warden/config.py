import os
from datetime import datetime, timedelta
from pathlib import Path


# Config class for Application Factory
class Config:
    home_path = Path.home()
    # make directory to store all private data at /home/warden
    # /root/warden/
    try:
        home_dir = os.path.join(home_path, 'warden')
        os.mkdir(home_dir)
    except Exception:
        pass

    basedir = os.path.abspath(os.path.dirname(__file__))

    # You should change this secret key. But make sure it's done before any data
    # is included in the database
    SECRET_KEY = "24feff264xscdcjncdjdcjuu212i"

    debug_file = os.path.join(home_path, 'warden/debug.log')

    version_file = os.path.join(basedir, 'static/config/version.txt')

    default_config_file = os.path.join(basedir, 'static/config/config_default.ini')
    config_file = os.path.join(basedir, 'config.ini')

    # Used for password recovery. Not needed in most cases.
    MAIL_SERVER = "smtp.googlemail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # ApScheduler Jobs
    JOBS = [{
        'id': 'background_job',
        'func': 'warden_modules:background_jobs',
        'trigger': 'interval',
        'seconds': 30,
        'next_run_time': datetime.now() + timedelta(seconds=15)
    }]

    # Pretty print json
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Do not start new job until the last one is done
    SCHEDULER_JOB_DEFAULTS = {'coalesce': False, 'max_instances': 1}
    SCHEDULER_API_ENABLED = True
