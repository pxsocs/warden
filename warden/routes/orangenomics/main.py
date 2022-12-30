import ast
import json
import dateutil.parser as parser
from datetime import datetime
from flask import (Blueprint, render_template, current_app, redirect, flash,
                   url_for, request)
from flask_login import (login_required, login_user, current_user, logout_user)
from forms.forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash, check_password_hash
from models.models import User, RequestData, Allocation
from sqlalchemy import desc
from backend.bitcoin_analytics import bitcoin_correlation

orangenomics = Blueprint('main', __name__)

# Minimum TemplateData used for render_template in all routes
# This ensures FX and current_app are sent to the render page
# at all times

templateData = {
    "title": "OrangeNomics",
    "current_app": current_app,
    "current_user": current_user
}


# Portfolio editing and including
@orangenomics.route("/orangenomics/portfolio", methods=['GET', 'POST'])
def portfolio():
    templateData['title'] = "Portfolio"
    # portfolio should be passed as a list of tuples
    # (ticker, weight) i.e [("BTC", 0.5), ("AAPL", 0.5)]
    # An empty list will create an empty portfolio with one line
    templateData['portfolio'] = []
    return (render_template('orangenomics/main/portfolio.html',
                            **templateData))


@orangenomics.route("/orangenomics/portfolio_table", methods=['GET', 'POST'])
def portfolio_table():
    return (render_template('orangenomics/main/portfolio_table.html'))


@orangenomics.route("/orangenomics/analyze", methods=['GET', 'POST'])
def analyze(btc_only=False):
    # btc_only returns only the data for BTC
    if btc_only is True:
        output_format = 'DATA'
        tickers = [("BTC", "Bitcoin")]
        portfolio = [('BTC', 1)]
        start_date = None
        end_date = None
        allocations = [0]
        rebalance = 'never'
        window = 180
        fx = 'USD'
        ad_data = 'BTC Only Request'
    else:
        # output_format=json returns a json with data
        output_format = request.args.get("output_format")

        # Get portfolio data
        portfolio = request.args.get("portfolio")
        portfolio = ast.literal_eval(portfolio)

        # Get start and end dates
        start_date = request.args.get("start_date")
        if start_date is not None:
            try:
                start_date = parser.parse(start_date.strip('"'))
            except Exception:
                start_date = None
        end_date = request.args.get("end_date")
        if end_date is not None:
            try:
                end_date = parser.parse(end_date.strip('"'))
            except Exception:
                end_date = None
        # get ticker and name data
        tickers = request.args.get("tickers")
        if tickers is not None:
            tickers = tickers.replace('null', '""')
            tickers = ast.literal_eval(tickers)
        else:
            # Need to get ticker names
            tickers = []
            for asset in portfolio:
                ticker = asset[0]
                from pricing_engine.engine import historical_prices, get_ticker_info
                import pandas as pd
                df = historical_prices(ticker)
                if isinstance(df, pd.DataFrame):
                    if not df.empty:
                        source = df['source'][0]
                        data = get_ticker_info(ticker, source)
                        ticker_name = data[0]['name']
                else:
                    ticker_name = ticker
                tickers.append([ticker, ticker_name])

        # Get simulation scenarios
        # These should be input as a list
        allocations = request.args.get("allocations")
        if allocations is None:
            allocations = [0.05, 0.10, 0.25]

        # Gets rebalance period
        rebalance = request.args.get("rebalance")
        rebalance = 'never' if rebalance is None else rebalance

        # Gets rolling correlation period
        window = request.args.get("window")
        try:
            window = int(window)
        except Exception:
            window = None
        if window is None:
            window = 180

        # Gets fx
        fx = request.args.get("fx")
        if fx is None:
            fx = 'USD'

        # Gets additional data if any from the request
        # This has no impact on analysis but will be saved
        # in the database for future use
        ad_data = request.args.get("data")
        if ad_data is None:
            ad_data = ''

    # Start analysis
    from backend.portfolio_analytics import portfolio_analysis
    data = portfolio_analysis(portfolio, tickers, allocations, rebalance,
                              start_date, end_date, window, fx)

    # Store the inputs for later analysis
    # This can be used to see which tickers are most accessed for example
    try:
        user_id = current_user.id
    except AttributeError:
        user_id = 0

    db_data = RequestData(portfolio=str(portfolio),
                          tickers=str(tickers),
                          allocations=str(allocations),
                          rebalance=str(rebalance),
                          start_date=str(start_date),
                          end_date=str(end_date),
                          request_time=str(datetime.utcnow()),
                          user_id=user_id,
                          data=ad_data)
    current_app.db.session.add(db_data)
    current_app.db.session.commit()

    # Store for template usage
    templateData['data_json'] = json.dumps(data, default=str)
    templateData['data'] = data

    # Return data in json format
    if output_format is not None:
        if output_format.upper() == 'JSON':
            return json.dumps(data, default=str)
        if output_format.upper() == 'DATA':
            return (data)

    return (render_template('orangenomics/main/analyze.html', **templateData))


@orangenomics.route("/orangenomics/port_actions", methods=['GET', 'POST'])
def port_actions():
    try:
        user_id = current_user.id
    except AttributeError:
        user_id = 0

    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            # Check if this portfolio name already exists for this user
            port = Allocation.query.filter_by(user_id=user_id).filter_by(
                portfolio_name=data['port_name'].upper()).first()
            if port:
                raise Exception(
                    "Portfolio name already exists. Choose another name.")
            # Check if exists on public list
            if data['port_visibility'] == 'public':
                public_ports = Allocation.query.filter_by(
                    visibility='public').filter_by(
                        portfolio_name=data['port_name']).first()
                if public_ports:
                    raise Exception(
                        "Portfolio name already exists for a public portfolio. Choose another name."
                    )
            db_data = Allocation(allocation_inputon=str(datetime.utcnow()),
                                 user_id=user_id,
                                 portfolio_name=data['port_name'].upper(),
                                 allocation=str(data['port_data']),
                                 rebalance=str(data['rebalance']),
                                 visibility=str(data['port_visibility']))
            current_app.db.session.add(db_data)
            current_app.db.session.commit()
            return json.dumps("success")
        except Exception as e:
            return json.dumps("Error: " + str(e))

    if request.method == 'GET':
        action = request.args.get("action")
        filter = request.args.get("filter")
        if filter is None:
            filter = ''
        # Get list of private portfolios for this user
        # plus top N public portfolios sorted by load times
        if action == 'get_portfolios':
            # Get user portfolios
            private_port_list = Allocation.query.filter_by(
                user_id=user_id).filter(
                    Allocation.portfolio_name.contains(filter)).all()

            # Get public portfolios
            public_port_list = Allocation.query.filter_by(
                visibility='public').filter(
                    Allocation.portfolio_name.contains(filter)).order_by(
                        desc(Allocation.loaded_times)).all()

            return json.dumps({
                'private': [x.as_dict() for x in private_port_list],
                'public': [x.as_dict() for x in public_port_list]
            })
        # Load a specific portfolio
        if action == 'get_portfolio':
            port_id = request.args.get("port_id")
            if port_id is None:
                return json.dumps("")
            portfolio = Allocation.query.filter_by(user_id=user_id).filter_by(
                id=port_id).first()
            if portfolio is None:
                # Search on public portfolios
                portfolio = Allocation.query.filter_by(
                    visibility='public').filter_by(id=port_id).first()
            if portfolio:
                loader = request.args.get("loader")
                # If an argument of loader is passed, increase the loader count
                if loader is not None:
                    loaded_times = int(portfolio.loaded_times) + 1
                    portfolio.loaded_times = loaded_times
                    current_app.db.session.commit()
                port = portfolio.as_dict()
                port['allocation'] = ast.literal_eval(port['allocation'])
                return json.dumps(port)
            else:
                return json.dumps("")
            # Update load times


@orangenomics.route("/orangenomics/btc_analytics", methods=['GET', 'POST'])
def btc_analytics():
    data = analyze(btc_only=True)
    return json.dumps(data, default=str)


@orangenomics.route("/orangenomics/btc_correl", methods=['GET'])
def btc_correl():
    benchmarks = [
        'SPY', 'QQQ', 'GLD', 'IEUR', 'GSG', 'UUP', 'SLV', 'TLT', 'HYG'
    ]
    df = bitcoin_correlation(benchmarks=benchmarks)
    templateData['title'] = "Correlation Analysis"
    templateData['html_table'] = df.tail(10).to_html(classes=['table'])
    return (render_template('orangenomics/main/correlation_analysis.html',
                            **templateData))
