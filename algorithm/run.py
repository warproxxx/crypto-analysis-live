import os
import shutil
from threading import Thread
from glob import glob

import pandas as pd
import numpy as np

import datetime
import time

from features import get_features, perform_backtest

from twitter_stream import twitter_stream
from price_stream import price_stream
from utils.common_utils import get_root_dir, merge_csvs
from process import processor, get_sentiment, clean_further, add_keyword, clean_profile

# t = Thread(target=twitter_stream)
# t.start()

print('Started Live Tweet Collection')

t = Thread(target=price_stream)
t.start()

print('Started Live Price Collection')

dir = get_root_dir()
temp_dir = os.path.join(dir, 'data/temp')

if not os.path.isdir(temp_dir):
    os.makedirs(temp_dir)

def save_to_file(df):
    global dir
    keyword = df.iloc[0]['keyword']
    print(keyword)
    
    df = df.drop('keyword', axis=1)

    coinwise_folder = os.path.join(dir, "data/coinwise")

    if not os.path.isdir(coinwise_folder):
        os.makedirs(coinwise_folder)

    savefile = "{}/{}.csv".format(coinwise_folder, keyword)

    if os.path.isfile(savefile):
        df.to_csv(savefile, index=None, mode='a')
    else:
        df.to_csv(savefile, index=None)

while True:
    # currentTime = datetime.datetime.now(datetime.timezone.utc)

    # if currentTime.minute % 10 != 0: #change logic to better run it every 10 mins
    #     time.sleep(5)
# else:
    time.sleep(10)
    keywords = pd.read_csv(get_root_dir() + '/keywords.csv')

    files = glob('data/twitter_stream/*')
    
    #copy these files into a folder so they can be processed independently
    for idx, file in enumerate(files):
        old_name = os.path.join(dir, files[idx])
        files[idx] = os.path.join(dir, files[idx].replace('twitter_stream/', 'temp/'))
        shutil.move(old_name, files[idx])

    combined = merge_csvs(files)
    df = pd.read_csv(combined)
    df, user_info = processor(df)

    savefile = os.path.join(dir, 'data/all_cleaned.csv')
    profilefile = os.path.join(dir, 'data/cleaned_profile.csv')

    for file in files:
        os.remove(file)

    df = get_sentiment(df)
    df = clean_further(df)
    df = add_keyword(df)

    df['ID'] = df['ID'].astype(int)
    df['Time'] = pd.to_datetime(df['Time'], unit='s')

    if not os.path.isfile(savefile):
        df.to_csv(savefile, index=None)
    else:
        df.to_csv(savefile, index=None, mode='a')

    if os.path.isfile(profilefile):
        user_info = pd.concat([user_info, pd.read_csv(profilefile)])
        user_info = clean_profile(user_info)

    user_info.to_csv(profilefile, index=None)

    df = df[df['keyword'] != 'invalid']
    df.groupby('keyword').apply(save_to_file)

    storage_dir = os.path.join(dir, 'data/storage')

    if not os.path.isdir(storage_dir):
        os.makedirs(storage_dir)

    storagename = os.path.join(storage_dir, 'all_cleaned_{}.csv'.format(int(time.time())))
    shutil.move(savefile, storagename)
    
    for idx, row in keywords.iterrows():
        features = get_features(row['Symbol'])
        
        # if currentTime.minute % 30 != 0:
        perform_backtest(features, row['Symbol'], n_fast_par=24, n_slow_par=52, long_macd_threshold_par=2, long_per_threshold_par=1, 
                        long_close_threshold_par=1, short_macd_threshold_par=-1, short_per_threshold_par=0, short_close_threshold_par=0.5,
                        initial_cash=10000, comission=0.1)