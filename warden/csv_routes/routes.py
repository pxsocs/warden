import csv
import hashlib
import logging
import secrets
import os
from datetime import datetime

import dateutil.parser as parser

from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, url_for, current_app)
from flask_login import current_user, login_required

from models import Trades, AccountInfo
from forms import ImportCSV
from utils import home_path
from warden_modules import transactions_fx, clean_float

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
                    filename = form.csvfile.data.filename
                    filename = os.path.join(home_path(), filename)
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
            line_counter = 0  # skip first line where field names are

            accounts = AccountInfo.query.filter_by(
                user_id=current_user.username).order_by(
                    AccountInfo.account_longname)

            for line in csv_reader:
                if line_counter != 0:
                    items = line.split(",")
                    random_hex = secrets.token_hex(21)

                    # Check if there is any data on this line:
                    empty = True
                    # 10 columns expected
                    for x in range(0, 10):
                        try:
                            if items[x] != "":
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
                        errorlist.append(f"missing date on line: {line_counter}")

                    # Check the Operation Type
                    try:
                        if "B" in items[2]:
                            qop = 1
                            operation = "B"
                        elif "S" in items[2]:
                            qop = -1
                            operation = "S"
                        else:
                            qop = 0
                            operation = "X"
                            errors = errors + 1
                            errorlist.append(f"missing operation on line {line_counter}")
                    except IndexError:
                        qop = 0
                        operation = "X"
                        errors = errors + 1
                        errorlist.append(f"missing operation on line {line_counter}")

                    # Import Quantity
                    try:
                        if items[4].replace(" ", "") != "":
                            quant = abs(clean_float(items[4])) * qop
                        else:
                            quant = 0
                    except ValueError:
                        quant = 0
                        errors = errors + 1
                        errorlist.append(
                            f"Quantity error on line {line_counter} - quantity \
                            {items[4]} could not be converted")

                    # Import Price
                    try:
                        if items[5].replace(" ", "") != "":
                            price = clean_float(items[5])
                        else:
                            price = 0
                    except ValueError:
                        price = 0
                        errors = errors + 1
                        errorlist.append(f"Price error on line {line_counter} - price \
                            {items[5]} could not be converted")

                    # Import Fees
                    try:
                        if items[6].replace(" ", "").replace("\n", "") != "":
                            fees = abs(clean_float(items[6]))
                        else:
                            fees = 0
                    except ValueError:
                        fees = 0
                        errors = errors + 1
                        errorlist.append(
                            f"error #{errors}: Fee error on line {line_counter} - Fee --\
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
                        errorlist.append(f"Missing account on line {line_counter}")

                    # Import Asset Symbol
                    try:
                        ticker = items[3].replace(" ", "")
                    except ValueError:
                        ticker = ""
                        errors = errors + 1
                        errorlist.append(f"Missing ticker on line {line_counter}")

                    # Find Trade Reference, if none, assign one
                    try:
                        tradeid = items[9]
                    except (ValueError, IndexError):
                        random_hex = secrets.token_hex(21)
                        tradeid = random_hex

                    # Import Cash Value - if none, calculate
                    try:
                        if items[7].replace(" ", "").replace("\n", "") != "":
                            cashvalue = clean_float(items[7])
                        else:
                            cashvalue = ((price) * (quant)) - abs(fees)
                    except ValueError:
                        cashvalue = 0
                        errors = errors + 1
                        errorlist.append(
                            f"error #{errors}: Cash_Value error on line \
                             {line_counter} - Cash_Value --{items[7]}-- could not \
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
                    current_app.db.session.add(trade)
                    current_app.db.session.commit()

                    # Check if current account is in list, if not, include

                    curacc = accounts.filter_by(
                        account_longname=account).first()

                    if not curacc:
                        account = AccountInfo(user_id=current_user.username,
                                              account_longname=account)
                        current_app.db.session.add(account)
                        current_app.db.session.commit()

                line_counter += 1

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
