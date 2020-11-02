import os
from datetime import datetime, timedelta


# Config class for Application Factory
class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))

    # You should change this secret key. But make sure it's done before any data
    # is included in the database
    SECRET_KEY = "24feff264xscdcjncdjdcjuu212i"

    debug_file = os.path.join(basedir, 'debug.log')

    config_file = os.path.join(basedir, 'config.ini')
    default_config_file = os.path.join(basedir, 'config_default.ini')

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
