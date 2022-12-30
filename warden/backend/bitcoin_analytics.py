from backend.portfolio_analytics import create_nav
from flask import flash
from pricing_engine.engine import historical_prices
import pandas as pd


def bitcoin_correlation(start_date=None,
                        end_date=None,
                        benchmarks=['SPY'],
                        windows=[30, 60, 90],
                        rank_keep=10,
                        threshold=0.80,
                        fx='USD'):
    """
    The Bitcoin correlation data is defined as:
    1.  Create a list of benchmark indices:
        ideally multi-asset class;
        an example is provided below using ETFs. The advantage of using
        ETFs is that they are liquid and have wide data availability for
        downloading. The disadvantage is that it may have limited historical
        dataset and it doesn't trade on weekends.
        benchmarks = ['SPY', 'QQQ', 'US Money supply?', 'Deflation ETF?']
        start_date = None, end_date = None

    2.  Define a list of rolling correlation windows for calculations.
        Consider geometric means maybe?
        windows = [30, 60, 90, 180]

    3.  This will result in a daily correlation between BTC and each asset.
        With this we can identify which asset (or indicator) is driving BTC's
        price. Maybe create a ranking of the top [10] correlations. Only keep
        the ones that have correlation above a threshold [80%].
        rank_keep = 10
        threshold = 0.80

    4.  Visualization TOOLS:
        a. Create an animated bar chart along time showing how the rank above
        moved along time. Which assets had the highest correlation.
        b. COUPLE / DECOUPLE INDEX: Important here is to track when BTC
        decouples. This will show by the rolling correlation falling below or
        above historical levels. For example, the 30 day rolling being above
        the 90 days will show that the correlation is picking up.
        Create a matrix of when these cross. Above or below.
        c. Create an index showing how many correlations are above the
        threshold. Ideal is to see this closest to zero as possible. A drop
        in this index will highlight a trend towards a correlation break.
        d. Consider creating an index based on a multiple regression. I.e.
        Bitcoin price is explained by x, y or z.
    """

    # Get the datasets
    if 'BTC' not in benchmarks:
        benchmarks.insert(0, 'BTC')

    df = pd.DataFrame(columns=['date'])
    for ticker in benchmarks:
        prices = historical_prices(ticker, fx)
        if prices.empty is True:
            flash(
                f"prices for ticker {ticker} could not be downloaded -- excluded from calculations",
                "warning")

        # check if prices is a Series. If so, convert to dataframe
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()

        # rename the column names so they are unique to this ticker
        prices = prices.rename(columns={'close_converted': ticker + '_price'})
        prices = prices[ticker + '_price']
        prices = prices.reset_index()
        prices = prices.set_index(['date'])

        # Trim prices so it only includes from start to end date
        # Trim the dates from start to end if not None
        # greater than the start date and smaller than the end date
        if start_date is not None:
            prices = prices.loc[start_date:]
        if end_date is not None:
            prices = prices.loc[:end_date]

        # Merge
        if df.empty:
            df = prices
        else:
            prices = prices.asfreq('D')
            df = pd.merge(df, prices, on='date', how='outer')

        # Process and clean daily NAV
        df = df.sort_index()

    for ticker in benchmarks:
        # Replace NaN with prev value, if no prev value then zero
        df[ticker + '_price'].fillna(method='backfill', inplace=True)
        df[ticker + '_price'].fillna(method='ffill', inplace=True)
        # include percentage change
        df[ticker + '_day_return'] = df[ticker + '_price'].pct_change()
        df[ticker + '_day_return'].fillna(0, inplace=True)
        # include factor of return
        df[ticker + '_perc_factor'] = (df[ticker + '_day_return']) + 1
        df[ticker + '_perc_factor'].fillna(1, inplace=True)
        # Cumulative compounded returns
        df[ticker + '_cum_return'] = df[ticker + '_perc_factor'].cumprod()
        # NAV
        df[ticker + '_NAV'] = df[ticker + '_cum_return'] * 100

    # Calculate rolling correlations
    for ticker in benchmarks:
        for window in windows:
            if ticker != 'BTC':
                df[ticker + '_corr_window_' +
                   str(window)] = df[ticker + '_day_return'].rolling(
                       window=window, min_periods=1).corr(df['BTC_day_return'])

    return df
