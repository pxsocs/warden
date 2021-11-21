import logging
import configparser
import os
import json
import pickle


from config import Config

import mhp as mrh


# Returns the current application path
def current_path():
    application_path = os.path.dirname(os.path.abspath(__file__))
    return (application_path)


# Returns the home path
def home_path():
    from pathlib import Path
    home = str(Path.home())
    return (home)


def create_config(config_file):
    logging.warning(
        "Config File not found. Getting default values and saving.")
    # Get the default config and save into config.ini
    default_file = Config.default_config_file

    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)

    return(default_config)


def update_config(config_file=Config.config_file):
    logging.info("Updating Config file")
    from flask import current_app
    with open(config_file, 'w') as file:
        current_app.settings.write(file)


def load_config(config_file=Config.config_file):
    # Load Config
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    return (CONFIG)


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    filename = 'warden/' + filename
    filename = os.path.join(home_path(), filename)
    if action == 'delete':
        try:
            os.remove(filename)
            return('deleted')
        except Exception:
            return('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'rb') as handle:
                    ld = pickle.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")

        except Exception as e:
            return ("file not found")
    else:
        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            return ("saved")


# Function to load and save data into json
def json_it(action='load', filename=None, data=None):
    filename = 'warden/' + filename
    filename = os.path.join(home_path(), filename)
    if action == 'delete':
        try:
            os.remove(filename)
            return('deleted')
        except Exception:
            return('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'r') as handle:
                    ld = json.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")

        except Exception as e:
            return ("file not found")
    else:
        # Serializing json
        json_object = json.dumps(data, indent=4)

        # Writing to sample.json
        with open(filename, "w") as handle:
            handle.write(json_object)
            return ("saved")


def fxsymbol(fx, output='symbol'):
    # Gets an FX 3 letter symbol and returns the HTML symbol
    # Sample outputs are:
    # "EUR": {
    # "symbol": "",
    # "name": "Euro",
    # "symbol_native": "",
    # "decimal_digits": 2,
    # "rounding": 0,
    # "code": "EUR",
    # "name_plural": "euros"
    from warden_modules import current_path
    filename = os.path.join(current_path(), 'static/json_files/currency.json')
    with open(filename) as fx_json:
        fx_list = json.load(fx_json)
    try:
        out = fx_list[fx][output]
    except Exception:
        if output == 'all':
            return (fx_list[fx])
        out = fx
    return (out)


def heatmap_generator():
    # If no Transactions for this user, return empty.html
    from warden_modules import transactions_fx, generatenav
    transactions = transactions_fx()
    if transactions.empty:
        return None, None, None, None

    # Generate NAV Table first
    data = generatenav()
    data["navpchange"] = (data["NAV_fx"] / data["NAV_fx"].shift(1)) - 1
    returns = data["navpchange"]
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(returns, eoy=True)

    heatmap_stats = heatmap
    cols = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "eoy",
    ]
    cols_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    years = (heatmap.index.tolist())
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(
        axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(
        axis=1)
    heatmap_stats["POSITIVES"] = heatmap_stats[heatmap_stats[cols_months] > 0].count(
        axis=1
    )
    heatmap_stats["NEGATIVES"] = heatmap_stats[heatmap_stats[cols_months] < 0].count(
        axis=1
    )
    heatmap_stats["POS_MEAN"] = heatmap_stats[heatmap_stats[cols_months] > 0].mean(
        axis=1
    )
    heatmap_stats["NEG_MEAN"] = heatmap_stats[heatmap_stats[cols_months] < 0].mean(
        axis=1
    )
    heatmap_stats["MEAN"] = heatmap_stats[heatmap_stats[cols_months] != 0].mean(
        axis=1)

    return (heatmap, heatmap_stats, years, cols)


def determine_docker_host_ip_address():
    cmd = "ip route show"
    import subprocess
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return str(output).split(' ')[2]


def runningInDocker():
    try:
        with open('/proc/self/cgroup', 'r') as procfile:
            for line in procfile:
                fields = line.strip().split('/')
                if 'docker' in fields:
                    return True

        return False

    except Exception:
        return False


# Serialize only objects that are json compatible
# This will exclude classes and methods
def safe_serialize(obj):
    def default(o):
        return f"{type(o).__qualname__}"
    return json.dumps(obj, default=default)
