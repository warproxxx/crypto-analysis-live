import pandas as pd
from utils.common_utils import get_root_dir
import os

def merge_time(df):
    ret = {}
    ret['Open'] = df.iloc[0]['Open']
    ret['High'] = max(df['High'])
    ret['Low'] = min(df['Low'])
    ret['Close'] = df.iloc[-1]['Close']
    ret['Volume'] = sum(df['Volume'])
    return pd.Series(ret)

def get_price(symbol, duration='30Min'):
    dir = get_root_dir()

    fname = dir + "/data/price/{}.csv".format(symbol)
    if not(os.path.isfile(fname)):
        print('Price data has not been downloaded. Starting Download. This might take some time')
        from price_stream import price_stream
        price_stream()

    df = pd.read_csv(fname)
    df['Time'] = pd.to_datetime(df['Time'])

    price_df = df.groupby(pd.Grouper(key='Time', freq=duration)).apply(merge_time)
    return price_df