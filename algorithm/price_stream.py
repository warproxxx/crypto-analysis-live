'''
Get data since the backtest duration and update regularly
'''

import pandas as pd
import datetime
import time

import requests
import json

import os

from binance.client import Client as BinanceClient
from utils.common_utils import get_root_dir

def get_binance_data(pairname, start_timestamp):
    binance_client = BinanceClient('api_key', 'api_secret')
    klines = binance_client.get_historical_klines(pairname, BinanceClient.KLINE_INTERVAL_1MINUTE, start_timestamp)
    df = pd.DataFrame(klines, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_Time', 'quote_asset_volume', 'no_of_trades', 'taker_buy_base_asset_vol', 'taker_buy_quote_asset_volume', 'ignore'])
    df = df[['Time', 'Open', 'High', 'Low', 'Close', 'quote_asset_volume']]
    df = df.rename(columns={'quote_asset_volume': 'Volume'})
    df['Time'] = pd.to_datetime(df['Time'], unit='ms') #see cleaning
    return df

def get_bitfinex_data(pairname, start_timestamp):
    end_time = 99999999999999999999
    all_df = pd.DataFrame()

    while end_time > start_timestamp:
        print(end_time)
        
        if end_time == 99999999999999999999:
            res = requests.get('https://api.bitfinex.com/v2/candles/trade:1m:t{}/hist?limit=5000'.format(pairname))
        else:
            res = requests.get('https://api.bitfinex.com/v2/candles/trade:1m:t{}/hist?end={}&limit=5000'.format(pairname, end_time))
        
        df = pd.DataFrame(json.loads(res.text))
        df.columns = ['Time', 'Open', 'Close', 'High', 'Low', 'Volume']
        end_time = df['Time'].iloc[-1]
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        
        all_df = pd.concat([all_df, df])
        time.sleep(1)

    all_df['Volume'] = all_df['Volume'] * all_df['Open']
    return all_df

def convert_to_timestamped(df):
    df['Time'] = df['Time'].astype(int) // 10 ** 9
    df = df.sort_values('Time')
    new_df = pd.DataFrame()
    new_df['Time'] = [x for x in range(df['Time'].iloc[0], df['Time'].iloc[-1], 60)]
    df = pd.merge_asof(new_df, df, on='Time', direction='nearest')
    df['Time'] = pd.to_datetime(df['Time'], unit='s')
    return df    


def clean_price(df):
    df = convert_to_timestamped(df)
    a = df[['Open', 'High', 'Low', 'Close']]
    a = a.astype(float)
    a = a - a.shift(1)
    a['temp'] = a['Open'] + a['High'] + a['Low'] + a['Close']
    a = a.dropna()
    a = a[a['temp'] == 0]
    df.loc[a['temp'].index, 'Volume'] = 0
    df = df.drop_duplicates('Time').reset_index(drop=True)
    return df

def price_stream():
    keywords = pd.read_csv(get_root_dir() + '/keywords.csv')

    coin_dir = get_root_dir() + "/data/price"

    if not os.path.isdir(coin_dir):
        os.makedirs(coin_dir)
    
    for idx, row in keywords.iterrows():
        start_timestamp = 1561939200000

        exchange_name = row['exchange_name']
        pairname = row['pair_name'].replace('/', '')

        current_file = coin_dir + "/{}.csv".format(row['Symbol'])
        print(current_file)
        
        all_df = pd.DataFrame()

        if os.path.isfile(current_file):
            all_df = pd.read_csv(current_file)

            if len(all_df) > 0:
                all_df['Time'] = pd.to_datetime(all_df['Time'])
                start_timestamp = all_df['Time'].astype(int).iloc[-1] // 10**6

        if row['exchange_name'] == 'Binance':
            curr_df = get_binance_data(pairname, start_timestamp)
        elif row['exchange_name'] == 'Bitfinex':
            curr_df = get_bitfinex_data(pairname, start_timestamp)

        full_df = pd.concat([all_df, curr_df])
        full_df = clean_price(full_df)

        full_df.to_csv(current_file, index=None)

price_stream()