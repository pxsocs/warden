import logging
import configparser
import os
import json
import pickle

from flask import current_app

from config import Config

import mhp as mrh

# Method to create a new config file if not found
# Copies data from warden.config_default.ini into a new config.ini


def create_config(config_file):
    logging.warn("Config File not found. Getting default values and saving.")
    # Get the default config and save into config.ini
    default_file = Config.default_config_file

    default_config = configparser.ConfigParser()
    default_config.read(default_file)

    with open(config_file, 'w') as file:
        default_config.write(file)


def update_config(config_file=Config.config_file):
    logging.info("Updating Config file")
    with open(config_file, 'w') as file:
        current_app.settings.write(file)


def load_config():
    # Load Config
    basedir = os.path.abspath(os.path.dirname(__file__))
    config_file = os.path.join(basedir, 'config.ini')
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_file)
    return (CONFIG)


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    logging.info(f"Pickle {action} file: {filename}")
    from warden_modules import home_path
    filename = 'warden/' + filename
    filename = os.path.join(home_path(), filename)
    if action == 'load':
        try:
            with open(filename, 'rb') as handle:
                ld = pickle.load(handle)
                logging.info(f"Loaded: Pickle {action} file: {filename}")
                return (ld)
        except Exception as e:
            logging.warn(f"Error: Pickle {action} file: {filename} error:{e}")
            return ("file not found")
    else:
        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            logging.info(f"Saved: Pickle {action} file: {filename}")
            return ("saved")


#  Tests

def diags(e=None):
    if e:
        print("---------------------------------")
        print("  An error occured ")
        print("  Running a quick diagnostic")
        print("---------------------------------")
        print("  Error Message")
        print("  " + str(e))
        print("---------------------------------")
    return_dict = {}
    print("  Starting Tests...")
    print("---------------------------------")

    # Loading Config
    print("  Loading config file...")
    file = Config.config_file
    config = configparser.ConfigParser()
    config.read(file)

    # Test Pricing Engine
    print("---------------------------------")
    print(" Starting Price Engine")
    print("---------------------------------")
    ticker = 'BTC'
    print(f"Ticker: {ticker}")
    print("Testing Realtime Pricing")
    from warden_pricing_engine import price_data_rt, REALTIME_PROVIDER_PRIORITY
    price = price_data_rt(ticker, priority_list=REALTIME_PROVIDER_PRIORITY, diags=True)
    print(price)

    print(json.dumps(return_dict, indent=4, sort_keys=True))

    return(return_dict)


def heatmap_generator():
    # If no Transactions for this user, return empty.html
    from warden_modules import specter_df, generatenav
    transactions = specter_df()
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
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(axis=1)
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
    heatmap_stats["MEAN"] = heatmap_stats[heatmap_stats[cols_months] != 0].mean(axis=1)

    return (heatmap, heatmap_stats, years, cols)
