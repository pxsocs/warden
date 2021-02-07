#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Monthly Returns Heatmap
# https://github.com/ranaroussi/monthly-returns-heatmap
#
# Copyright 2017 Ran Aroussi
#
# Licensed under the GNU Lesser General Public License, v3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.gnu.org/licenses/lgpl-3.0.en.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__version__ = "0.0.11"
__author__ = "Ran Aroussi"
# __all__ = ['get', 'plot']

import pandas as pd
from pandas.core.base import PandasObject


def sum_returns(returns, groupby, compounded=True):
    def returns_prod(data):
        return (data + 1).prod() - 1

    if compounded:
        return returns.groupby(groupby).apply(returns_prod)
    return returns.groupby(groupby).sum()


def get(returns, eoy=False, is_prices=False, compounded=True):
    # get close / first column if given DataFrame
    if isinstance(returns, pd.DataFrame):
        returns.columns = map(str.lower, returns.columns)
        if len(returns.columns) > 1 and 'close' in returns.columns:
            returns = returns['close']
        else:
            returns = returns[returns.columns[0]]

    # convert price data to returns
    if is_prices:
        returns = returns.pct_change()

    original_returns = returns

    returns = pd.DataFrame(
        sum_returns(returns, returns.index.strftime('%Y-%m-01'), compounded))
    returns.columns = ['Returns']
    returns.index = pd.to_datetime(returns.index)

    # get returnsframe
    returns['Year'] = returns.index.strftime('%Y')
    returns['Month'] = returns.index.strftime('%b')

    # make pivot table
    returns = returns.pivot('Year', 'Month', 'Returns').fillna(0)

    # handle missing months
    for month in [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
            'Oct', 'Nov', 'Dec'
    ]:
        if month not in returns.columns:
            returns.loc[:, month] = 0

    # order columns by month
    returns = returns[[
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct',
        'Nov', 'Dec'
    ]]

    if eoy:
        returns['eoy'] = sum_returns(original_returns,
                                     original_returns.index.year).values

    return returns


PandasObject.get_returns_heatmap = get
PandasObject.sum_returns = sum_returns
