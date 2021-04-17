from flask import flash
import pandas as pd
import numpy as np
from pricing_engine.engine import (fx_rate,
                                   price_ondate, fx_price_ondate, realtime_price,
                                   historical_prices)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def simulate_portfolio(
        assets=['BTC'],  # List of asset tickers
        weights=[1],  # List of weights, 1 = 100%
        rebalance='never',  # never, daily, weekly, monthly, quarterly, annually
        save=False,  # saves the variables above under a name
        name=None,  # string of name to save
        initial_investment=1000,  # in fx values
        load=False,
        start_date=datetime(2000, 1, 1),
        end_date=datetime.today(),
        fx='USD',
        short_term_tax_rate=0):

    # Create an empty df
    merged_df = pd.DataFrame(columns=['date'])
    # Fill the dates from first trade until today
    merged_df['date'] = pd.date_range(start=start_date, end=end_date)
    merged_df = merged_df.set_index('date')
    merged_df.index = merged_df.index.astype('datetime64[ns]')

    # Create empty columns for later
    merged_df['fiat_value'] = 0
    merged_df['rebalance_date'] = False

    for ticker in assets:
        prices = historical_prices(ticker, fx=fx)
        prices.index = prices.index.astype('datetime64[ns]')
        if prices.empty:
            merged_df[id + '_price'] = 0
            flash(f"Prices for ticker {id} could not be downloaded." +
                  " {id} was not included in analysis.", "warning")
            save = False

        start_date_ticker = prices.index.min()
        if start_date_ticker > start_date:
            try:
                flash(f"Requested start date was {start_date.strftime('%b-%d-%y')} " +
                      f"but the ticker {id} only has pricing data from " +
                      f"{start_date_ticker.strftime('%b-%d-%y')}. Adjusted start date.", "warning")
            except Exception:
                pass
            start_date = start_date_ticker

        prices = prices.rename(columns={'close_converted': ticker + '_price'})
        prices[ticker + '_price'] = prices[ticker + '_price'].astype(float)
        prices = prices[ticker + '_price']

        # Check if prices is a Series. If so, convert to dataframe
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()

        merged_df = pd.merge(merged_df, prices, on='date', how='left')
        # Replace NaN with prev value, if no prev value then zero
        merged_df[ticker + '_price'].fillna(method='backfill', inplace=True)
        merged_df[ticker + '_price'].fillna(method='ffill', inplace=True)
        merged_df[ticker + '_return'] = merged_df[ticker + '_price'].pct_change().fillna(0)

    # Trim the dataframe so it starts at the new start date
    # start date is adjusted to the first date when both datas are
    # available -- see code above
    mask = (merged_df.index >= start_date)
    merged_df = merged_df.loc[mask]

    # With the dataframe trimmed, calculate cum returns
    for ticker in assets:
        # Calculate cum_returns
        merged_df[ticker + '_cum_return'] = (1 + merged_df[ticker + '_return']).cumprod()

        # Calculate the unrebalanced positions
        merged_df[ticker + '_fiat_pos_unbalanced'] = (weights[assets.index(ticker)] *
                                                      initial_investment *
                                                      merged_df[ticker + '_cum_return'])
        merged_df[ticker + '_fiat_pos_balanced'] = np.nan

    # Portfolio Value unrebalanced
    merged_df['port_fiat_pos_unbalanced'] = (merged_df[
        [col for col in merged_df.columns if col.endswith('_fiat_pos_unbalanced')]].sum(
            axis=1))

    for ticker in assets:
        merged_df[ticker + '_weight'] = (
            merged_df[ticker + '_fiat_pos_unbalanced'] /
            merged_df['port_fiat_pos_unbalanced'])

    # Create a list of rebalancing dates
    rebalance_days = [('never', None),
                      ('daily', timedelta(days=1)),
                      ('weekly', timedelta(days=7)),
                      ('monthly', relativedelta(months=+1)),
                      ('quarterly', relativedelta(months=+3)),
                      ('annualy', relativedelta(months=+12))
                      ]

    rebalancing_delta = dict(rebalance_days)[rebalance]

    # Fill the df with these checks for rebalancing dates
    loop_date = start_date
    if rebalancing_delta is not None:
        while loop_date < end_date:
            merged_df.at[loop_date, 'rebalance_date'] = True
            loop_date += rebalancing_delta

    previous_date = start_date
    # Rebalance the portfolio on rebalancing dates
    for loop_date in merged_df.index.tolist():
        if loop_date == start_date:
            for ticker in assets:
                merged_df.at[loop_date, ticker + '_costbasis'] = (weights[assets.index(ticker)] *
                                                                  initial_investment)
            continue
        # NOT REBALANCE DATE:
        if not merged_df.at[loop_date, 'rebalance_date']:
            # Repeat the cost basis from before, nothing changed
            for ticker in assets:
                merged_df.at[loop_date, ticker + '_costbasis'] = (
                    merged_df.at[previous_date, ticker + '_costbasis'])
                merged_df.at[loop_date, ticker + '_fiat_pos_balanced'] = (
                    merged_df.at[previous_date, ticker + '_fiat_pos_balanced'] *
                    (1 + merged_df.at[loop_date, ticker + '_return'])
                )

        # REBALANCE DATE, make changes
        else:
            print(loop_date)

        previous_date = loop_date

    print(merged_df)
