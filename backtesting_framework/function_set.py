import pandas as pd
import numpy as np


def pct_change(series):
        return series[-1]/series[0] - 1

def momentum(data_center,formation_period):
    # data
    ticker_dict = data_center.ticker_dict
    dateList = data_center.dateList
    # calculate
    momentum_dict = dict()
    for ticker in ticker_dict:
        px_series = ticker_dict[ticker].loc[dateList,'CLOSE']
        # momentum_dict[ticker] = px_series.rolling(window=formation_period, min_periods=1).apply(pct_change)
        momentum_dict[ticker] = px_series.rolling(window=formation_period).apply(pct_change)
    # table
    momentum_df = pd.DataFrame(
        data=momentum_dict,
        index=dateList
    )
    return momentum_df

def moving_average(data_center,col_name , period):
    # data
    ticker_dict = data_center.ticker_dict
    dateList = data_center.dateList
    # calculate
    moving_average_dict = dict()
    for ticker in ticker_dict:
        px_series = ticker_dict[ticker].loc[dateList,col_name]
        moving_average_dict[ticker] = px_series.rolling(window=period, min_periods=1).mean()

    moving_average_df = pd.DataFrame(
        data=moving_average_dict,
        index=dateList
    )
    return moving_average_df

def moving_std(data_center,col_name , period):
    # data
    ticker_dict = data_center.ticker_dict
    dateList = data_center.dateList
    # calculate
    moving_std_dict = dict()
    for ticker in ticker_dict:
        px_series = ticker_dict[ticker].loc[dateList,col_name]
        moving_std_dict[ticker] = px_series.rolling(window=period, min_periods=1).std()

    moving_std_df = pd.DataFrame(
        data=moving_std_dict,
        index=dateList
    )
    return moving_std_df





