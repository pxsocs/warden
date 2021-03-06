import csv
import hashlib
import logging
import os
from datetime import datetime

import dateutil.parser as parser

from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, url_for, current_app)
from flask_login import current_user, login_required

from models import Trades
from forms import ImportCSV
from utils import home_path
from warden_modules import transactions_fx

csv_routes = Blueprint('csv_routes', __name__)


@csv_routes.route("/exportcsv")
@login_required
# Download all transactions in CSV format
def exportcsv():
    transactions = Trades.query.filter_by(
        user_id=current_user.username).order_by(Trades.trade_date)

    if transactions.count() == 0:
        return render_template("empty.html")

    filename = (current_user.username + "_" +
                datetime.now().strftime("%Y%m%d") + ".")
    filepath = os.path.join(home_path(), filename)
    df = transactions_fx()
    compression_opts = dict(method='zip',
                            archive_name=filename + 'csv')
    df.to_csv(filepath + 'zip', index=True,
              compression=compression_opts)

    return send_file(filepath + 'zip', as_attachment=True)


@csv_routes.route("/importcsv", methods=["GET", "POST"])
@login_required
# imports a csv file into database
def importcsv():

    form = ImportCSV()

    if request.method == "POST":

        if form.validate_on_submit():
            if form.submit.data:
                if form.csvfile.data:
                    test_file = "thewarden/dailydata/test.csv"
                    filename = os.path.join(current_path(), test_file)
                    os.makedirs(os.path.dirname(filename), exist_ok=True)

                    filename = "thewarden/dailydata/" + form.csvfile.data.filename
                    filename = os.path.join(current_path(), filename)
                    form.csvfile.data.save(filename)

                    csv_reader = open(filename, "r", encoding="utf-8")
                    csv_reader = csv.DictReader(csv_reader)
                    csvfile = form.csvfile.data

                return render_template(
                    "importcsv.html",
                    title="Import CSV File",
                    form=form,
                    csv=csv_reader,
                    csvfile=csvfile,
                    filename=filename,
                )
    if request.method == "GET":
        filename = request.args.get("f")
        if filename:
            csv_reader = open(filename, "r", encoding="utf-8")
            # csv_reader = csv.DictReader(csv_reader)

            errors = 0
            errorlist = []
            a = 0  # skip first line where field names are

            accounts = AccountInfo.query.filter_by(
                user_id=current_user.username).order_by(
                    AccountInfo.account_longname)

            for line in csv_reader:
                if a != 0:
                    items = line.split(",")
                    random_hex = secrets.token_hex(21)

                    # Check if there is any data on this line:
                    empty = True
                    for l in range(0, 10):
                        try:
                            if items[l] != "":
                                empty = False
                        except IndexError:
                            pass
                    if empty:
                        continue

                    # import TimeStamp Field
                    try:
                        tradedate = parser.parse(items[0])
                    except ValueError:
                        tradedate = datetime.now()
                        errors = errors + 1
                        errorlist.append(f"missing date on line: {a}")

                    # Check the Operation Type
                    try:
                        if "B" in items[2]:
                            qop = 1
                            operation = "B"
                        elif "S" in items[2]:
                            qop = -1
                            operation = "S"
                        elif "D" in items[2]:
                            qop = 1
                            operation = "D"
                        elif "W" in items[2]:
                            qop = -1
                            operation = "W"
                        else:
                            qop = 0
                            operation = "X"
                            errors = errors + 1
                            errorlist.append(f"missing operation on line {a}")
                    except IndexError:
                        qop = 0
                        operation = "X"
                        errors = errors + 1
                        errorlist.append(f"missing operation on line {a}")

                    # Import Quantity
                    try:
                        if items[4].replace(" ", "") != "":
                            quant = abs(cleancsv(items[4])) * qop
                        else:
                            quant = 0
                    except ValueError:
                        quant = 0
                        errors = errors + 1
                        errorlist.append(
                            f"Quantity error on line {a} - quantity \
                            {items[4]} could not be converted")

                    # Import Price
                    try:
                        if items[5].replace(" ", "") != "":
                            price = cleancsv(items[5])
                        else:
                            price = 0
                    except ValueError:
                        price = 0
                        errors = errors + 1
                        errorlist.append(f"Price error on line {a} - price \
                            {items[5]} could not be converted")

                    # Import Fees
                    try:
                        if items[6].replace(" ", "").replace("\n", "") != "":
                            fees = cleancsv(items[6])
                        else:
                            fees = 0
                    except ValueError:
                        fees = 0
                        errors = errors + 1
                        errorlist.append(
                            f"error #{errors}: Fee error on line {a} - Fee --\
                            {items[6]}-- could not be converted")

                    # Import Notes
                    try:
                        notes = items[8]
                    except IndexError:
                        notes = ""

                    # Import Account
                    try:
                        account = items[1]
                    except ValueError:
                        account = ""
                        errors = errors + 1
                        errorlist.append(f"Missing account on line {a}")

                    # Import Asset Symbol
                    try:
                        ticker = items[3].replace(" ", "")
                        if ticker != "USD":
                            listcrypto = listofcrypto.query.filter_by(
                                symbol=ticker)
                            if listcrypto is None:
                                errors = errors + 1
                                errorlist.append(
                                    f"ticker {ticker} in line {a} \
                                    imported but not found in pricing list")

                    except ValueError:
                        ticker = ""
                        errors = errors + 1
                        errorlist.append(f"Missing ticker on line {a}")

                    # Find Trade Reference, if none, assign one
                    try:
                        tradeid = items[9]
                    except (ValueError, IndexError):
                        random_hex = secrets.token_hex(21)
                        tradeid = random_hex

                    # Import Cash Value - if none, calculate
                    try:
                        if items[7].replace(" ", "").replace("\n", "") != "":
                            cashvalue = cleancsv(items[7])
                        else:
                            cashvalue = ((price) * (quant)) + fees
                    except ValueError:
                        cashvalue = 0
                        errors = errors + 1
                        errorlist.append(
                            f"error #{errors}: Cash_Value error on line \
                             {a} - Cash_Value --{items[7]}-- could not \
                             be converted")

                    trade = Trades(
                        user_id=current_user.username,
                        trade_date=tradedate,
                        trade_account=account,
                        trade_asset_ticker=ticker,
                        trade_quantity=quant,
                        trade_operation=operation,
                        trade_price=price,
                        trade_fees=fees,
                        trade_notes=notes,
                        cash_value=qop * cashvalue,
                        trade_reference_id=tradeid,
                    )
                    db.session.add(trade)
                    db.session.commit()
                    regenerate_nav()

                    # Check if current account is in list, if not, include

                    curacc = accounts.filter_by(
                        account_longname=account).first()

                    if not curacc:
                        account = AccountInfo(user_id=current_user.username,
                                              account_longname=account)
                        db.session.add(account)
                        db.session.commit()

                a = a + 1

            # re-generates the NAV on the background
            # re-generates the NAV on the background - delete First
            # the local NAV file so it's not used.
            usernamehash = hashlib.sha256(
                current_user.username.encode("utf-8")).hexdigest()
            filename = "thewarden/nav_data/" + usernamehash + ".nav"
            filename = os.path.join(current_path(), filename)
            logging.info(f"[newtrade] {filename} marked for deletion.")
            # Since this function can be run as a thread,
            # it's safer to delete the current NAV file if it exists.
            # This avoids other tasks reading the local file which
            # is outdated
            try:
                os.remove(filename)
                logging.info("[importcsv] Local NAV file deleted")
            except OSError:
                logging.info("[importcsv] Local NAV file not found" +
                             " for removal - continuing")
            generatenav_thread = threading.Thread(target=generatenav,
                                                  args=(current_user.username,
                                                        True))
            logging.info("[importcsv] Change to database - generate NAV")
            generatenav_thread.start()

            if errors == 0:
                flash("CSV Import successful", "success")
            if errors > 0:
                logging.error("Errors found. Total of ", errors)

                flash(
                    "CSV Import done but with errors\
                 - CHECK TRANSACTION LIST",
                    "danger",
                )
                for error in errorlist:
                    flash(error, "warning")

            return redirect(url_for("main.home"))

    return render_template("importcsv.html",
                           title="Import CSV File",
                           form=form)


@csv_routes.route("/csvtemplate")
# template details for CSV import
def csvtemplate():
    return render_template("warden/csvtemplate.html",
                           title="CSV Template",
                           current_app=current_app)
