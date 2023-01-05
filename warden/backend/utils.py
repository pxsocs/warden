import os
import io
import json
import pickle
import time
from datetime import datetime

import backend.mhp as mrh
import pandas as pd
import numpy as np


# Function to load and save data into pickles
def pickle_it(action='load', filename=None, data=None):
    from backend.config import home_dir
    if filename is not None:
        filename = os.path.join(home_dir, filename)
    else:
        filename = os.path.join(home_dir, filename)

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
    from backend.config import home_dir
    filename = os.path.join(home_dir, filename)
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
    from backend.config import basedir
    filename = os.path.join(basedir, 'static/json_files/currency.json')
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


def df_col_to_highcharts(df, cols):
    """
    receives columns in format ['col1'] or ['col1', 'col2',...]
    returns a dictionary that can later be used in highcharts
    names is a list of names for the columns
    colors is a list of colors for the columns
    """
    # copy only these columns
    data = df[cols].copy()
    # dates need to be in Epoch time for Highcharts
    data.index = (data.index - datetime(1970, 1, 1)).total_seconds()
    data.index = data.index * 1000
    data.index = data.index.astype(np.int64)
    # Make sure it is a dataframe
    if isinstance(data, pd.Series):
        data = data.to_frame()
    data = data.to_records(index=True).tolist()
    data = [list(elem) for elem in data]
    return data


def get_image(domain):
    """
    Returns the image for a given ticker
    """
    return "https://www.google.com/s2/favicons?domain=" + domain


def safe_filename(s):
    return ("".join([
        c for c in s if c.isalpha() or c.isdigit() or c == '_' or c == '-'
    ]).rstrip())


def join_all(threads, timeout):
    """
    Args:
        threads: a list of thread objects to join
        timeout: the maximum time to wait for the threads to finish
    Raises:
        RuntimeError: is not all the threads have finished by the timeout
    """
    start = cur_time = time.time()
    while cur_time <= (start + timeout):
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=0)
        if all(not t.is_alive() for t in threads):
            break
        time.sleep(0.1)
        cur_time = time.time()
    else:
        still_running = [t for t in threads if t.is_alive()]
        num = len(still_running)
        names = [t.name for t in still_running]
        raise RuntimeError('Timeout on {0} threads: {1}'.format(num, names))


# Downloads DF into Excel file - returns the file name
def download_pd_excel(df, sheet_name='WARden_export_data'):
    from backend.config import home_dir
    filename = safe_filename(sheet_name) + '.xlsx'
    filename = os.path.join(home_dir, filename)
    df.to_excel(filename, sheet_name=sheet_name)
    return (filename)