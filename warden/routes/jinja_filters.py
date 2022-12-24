import jinja2
import os
import json
from flask import Blueprint, current_app
from datetime import datetime

jinja_filters = Blueprint('jinja_filters', __name__)


# Contect Processor makes variables available across all templates
# and pages so it's easily accessable later
@current_app.context_processor
def cache_busters():
    return {
        'now': datetime.utcnow(),
    }


@jinja2.pass_context
def inject_now(context):
    return {'now': datetime.utcnow()}


@jinja2.pass_context
@jinja_filters.app_template_filter()
def jformat(context, n, places, divisor=1):
    if n is None:
        return "-"
    else:
        try:
            n = float(n)
            n = n / divisor
            if n == 0:
                return "-"
        except ValueError:
            return "-"
        except TypeError:
            return (n)
        try:
            form_string = "{0:,.{prec}f}".format(n, prec=places)
            return form_string
        except (ValueError, KeyError):
            return "-"


# Jinja filter - epoch to time string
@jinja2.pass_context
@jinja_filters.app_template_filter()
def epoch(context, epoch):
    time_r = datetime.fromtimestamp(epoch).strftime("%m-%d-%Y (%H:%M)")
    return time_r


# Jinja filter - fx details
@jinja2.pass_context
@jinja_filters.app_template_filter()
def fxsymbol(context, fx, output='symbol'):
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
    try:
        from application_factory import current_path
        filename = os.path.join(current_path,
                                'static/json_files/currency.json')
        with open(filename) as fx_json:
            fx_list = json.load(fx_json, encoding='utf-8')
        out = fx_list[fx][output]
    except Exception:
        out = fx
    return (out)


# Jinja filter - time to time_ago
@jinja2.pass_context
@jinja_filters.app_template_filter()
def time_ago(context, time=False):
    if type(time) is str:
        try:
            time = int(time)
        except TypeError:
            return time
        except ValueError:
            try:
                # Try different parser
                time = datetime.strptime(time, '%m-%d-%Y (%H:%M)')
            except Exception:
                return time
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        return ("")
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 10:
            return "Just Now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(int(day_diff)) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"


@jinja2.pass_context
@jinja_filters.app_template_filter()
def shorten(context,
            text,
            max_lenght,
            suffix='...',
            break_words=True,
            tail=False):
    if len(text) <= max_lenght:
        return text
    if not break_words:
        return text[:max_lenght] + suffix
    if tail:
        return text[-max_lenght:] + suffix
    return text[:max_lenght] + suffix
