import logging
import configparser
import os
import json
import pickle
from datetime import datetime
from config import Config, home_path

import mhp as mrh


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    if filename is not None:
        filename = os.path.join(home_path(), filename)
    else:
        filename = os.path.join(home_path(), filename)

    # list all pkl files at directory
    if action == 'list':
        files = os.listdir(filename)
        ret_list = [x for x in files if x.endswith('.pkl')]
        return (ret_list)

    if action == 'delete':
        try:
            os.remove(filename)
            return ('deleted')
        except Exception:
            return ('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'rb') as handle:
                    ld = pickle.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")

        except Exception:
            return ("file not found")
    else:
        # Make directory if doesn't exist
        try:
            directory = os.path.dirname(filename)
            os.stat(directory)
        except Exception:
            os.mkdir(directory)

        with open(filename, 'wb') as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            return ("saved")


# Function to load and save data into json
def json_it(action='load', filename=None, data=None):
    filename = os.path.join(home_path(), filename)
    if action == 'delete':
        try:
            os.remove(filename)
            return ('deleted')
        except Exception:
            return ('failed')

    if action == 'load':
        try:
            if os.path.getsize(filename) > 0:
                with open(filename, 'r') as handle:
                    ld = json.load(handle)
                    return (ld)
            else:
                os.remove(filename)
                return ("file not found")
        except Exception:
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
    from backend.warden_modules import current_path
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
    from backend.warden_modules import transactions_fx, generatenav
    transactions = transactions_fx()
    if transactions.empty:
        return None, None, None, None

    # Generate NAV Table first
    data = generatenav()
    data["navpchange"] = (data["NAV_fx"] / data["NAV_fx"].shift(1)) - 1
    returns = data["navpchange"]
    # Run the mrh function to generate heatmap table
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
    heatmap_stats["POSITIVES"] = heatmap_stats[
        heatmap_stats[cols_months] > 0].count(axis=1)
    heatmap_stats["NEGATIVES"] = heatmap_stats[
        heatmap_stats[cols_months] < 0].count(axis=1)
    heatmap_stats["POS_MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] > 0].mean(axis=1)
    heatmap_stats["NEG_MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] < 0].mean(axis=1)
    heatmap_stats["MEAN"] = heatmap_stats[
        heatmap_stats[cols_months] != 0].mean(axis=1)

    return (heatmap, heatmap_stats, years, cols)


# Serialize only objects that are json compatible
# This will exclude classes and methods
def safe_serialize(obj):

    def default(o):
        return f"{type(o).__qualname__}"

    return json.dumps(obj, default=default)


# Better to use parseNumber most of the times...
# Function to clean CSV fields - leave only digits and .
def clean_float(text):
    if not isinstance(text, str):
        return text
    if text is None:
        return (0)
    acceptable = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."]
    string = ""
    for char in (text):
        if char in acceptable:
            string = string + char
    try:
        string = float(string)
    except Exception:
        string = 0
    return (string)


def cleandate(text):  # Function to clean Date fields
    if text is None:
        return (None)
    text = str(text)
    acceptable = [
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "/", "-", ":",
        " "
    ]
    str_parse = ""
    for char in text:
        if char in acceptable:
            char = '-' if (char == '.' or char == '/') else char
            str_parse = str_parse + char
    from dateutil import parser

    str_parse = parser.parse(str_parse, dayfirst=True)
    return (str_parse)


def file_created_today(filename):
    try:
        today = datetime.now().date()
        filetime = datetime.fromtimestamp(os.path.getctime(filename))
        if filetime.date() == today:
            return True
        else:
            return False
    except Exception:
        return False