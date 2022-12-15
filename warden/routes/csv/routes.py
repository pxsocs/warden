import csv
import hashlib
import logging
import secrets
import os
import pandas as pd
from datetime import datetime

import dateutil.parser as parser

from flask import (Blueprint, flash, redirect, render_template, request,
                   send_file, url_for, current_app)
from flask_login import current_user, login_required

from models.models import Trades, AccountInfo
from forms.forms import ImportCSV, TradeForm
from backend.utils import clean_float
from backend.config import home_dir
from backend.warden_modules import transactions_fx
from pricing_engine.engine import fx_rate

csv_routes = Blueprint('csv_routes', __name__)


def cleancsvfile(file):
    df = pd.read_csv(file)
    count = df.count()[0] + 1
    df.to_csv(file, index=False)
    return (count)


@csv_routes.route("/exportcsv")
@login_required
# Download all transactions in CSV format
def exportcsv():
    transactions = Trades.query.filter_by(
        user_id=current_user.username).order_by(Trades.trade_date)

    if transactions.count() == 0:
        form = TradeForm()
        form.trade_currency.data = current_app.fx['code']
        form.trade_date.data = datetime.utcnow()
        return render_template("warden/empty_txs.html",
                               title="Empty Transaction List",
                               current_app=current_app,
                               current_user=fx_rate(),
                               form=form)

    filename = (current_user.username + "_" +
                datetime.now().strftime("%Y%m%d") + ".")
    filepath = os.path.join(home_dir, filename)
    df = transactions_fx()
    compression_opts = dict(method='zip', archive_name=filename + 'csv')
    df.to_csv(filepath + 'zip', index=True, compression=compression_opts)

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
                    filename = os.path.join(home_dir, filename)
                    form.csvfile.data.save(filename)
                    row_count = cleancsvfile(filename)
                    csv_reader = open(filename, "r", encoding="utf-8")
                    csv_reader = csv.DictReader(csv_reader)
                    csvfile = form.csvfile.data

                return render_template("warden/importcsv.html",
                                       title="Import CSV File",
                                       form=form,
                                       csv=csv_reader,
                                       csvfile=csvfile,
                                       filename=filename,
                                       current_app=current_app,
                                       row_count=row_count)

    if request.method == "GET":
        filename = request.args.get("f")
        if filename:
            df = pd.read_csv(filename)
            # Clean the dataframe
            df.columns = [
                'trade_date', 'trade_account', 'trade_operation',
                'trade_asset_ticker', 'trade_quantity', 'trade_price',
                'trade_fees', 'cash_value', 'trade_notes',
                'trade_blockchain_id'
            ]

            # Make sure these are float numbers
            floaters = [
                'trade_quantity', 'trade_price', 'trade_fees', 'cash_value'
            ]
            for element in floaters:
                df[element].apply(clean_float)

            # Parse trade date
            df['trade_date'] = df['trade_date'].astype('datetime64[ns]')

            # Accept only B / S on operation, sanitize
            df['trade_operation'] = df['trade_operation'].str.upper()
            df['trade_operation'] = df['trade_operation'].str.replace(' ', '')
            df.drop(df[(df.trade_operation != 'B')
                       & (df.trade_operation != 'S')].index,
                    inplace=True)

            # Make sure there is a cash value
            df.loc[df["cash_value"].isnull(), 'cash_value'] = (
                (df["trade_price"] * df["trade_quantity"]) - df["trade_fees"])

            df['trade_asset_ticker'] = df['trade_asset_ticker'].str.upper()
            # Remove spaces on tickers
            df['trade_asset_ticker'] = df['trade_asset_ticker'].str.replace(
                ' ', '')

            df['trade_currency'] = current_app.settings['PORTFOLIO']['base_fx']
            df['trade_inputon'] = datetime.utcnow()

            df['user_id'] = current_user.username

            trade_account_list = df['trade_account'].unique().tolist()

            # Import DF into database
            df.to_sql(name='trades',
                      con=current_app.db.engine,
                      if_exists='append',
                      index=False)

            #  Accounts
            accounts = AccountInfo.query.filter_by(
                user_id=current_user.username).order_by(
                    AccountInfo.account_longname)

            # Include the new accounts in account list
            for account in trade_account_list:
                # Check if current account is in list, if not, include
                curacc = accounts.filter_by(account_longname=account).first()

                if not curacc:
                    account = AccountInfo(user_id=current_user.username,
                                          account_longname=account)
                    current_app.db.session.add(account)
                    current_app.db.session.commit()

            flash(
                "Imported CSV Successfully. NAV and Portfolio will update soon.",
                "success")
            return redirect(url_for("warden.warden_page"))

    return render_template("warden/importcsv.html",
                           title="Import CSV File",
                           current_app=current_app,
                           form=form)


@csv_routes.route("/csvtemplate")
# template details for CSV import
def csvtemplate():
    return render_template("warden/csvtemplate.html",
                           title="CSV Template",
                           current_app=current_app)
