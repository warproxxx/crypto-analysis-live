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
from utils.get_price_data import get_price
from utils.backtest_parameter import *
from process import processor, get_sentiment, clean_further, add_keyword, clean_profile
from weekly_process import weekly_process

def save_to_file(df):
    global dir
    keyword = df.iloc[0]['keyword']
    print(keyword)
    
    df = df.drop('keyword', axis=1)

    coinwise_folder = os.path.join(dir, "data/coinwise")

    if not os.path.isdir(coinwise_folder):
        os.makedirs(coinwise_folder)

    savefile = "{}/{}.csv".format(coinwise_folder, keyword)
    df.to_csv(savefile, index=None)

def get_keywords():
    keywords = pd.read_csv(get_root_dir() + '/keywords.csv')
    return keywords

def one_minute_cleaning():
    global dir
    keywords = get_keywords()
    #Get list of files
    files = glob(os.path.join(dir, 'data/twitter_stream/*'))
    
    #copy these files into a folder so they can be processed independently
    for idx, file in enumerate(files):
        old_name = os.path.join(dir, files[idx])
        files[idx] = os.path.join(dir, files[idx].replace('twitter_stream/', 'temp/'))
        shutil.move(old_name, files[idx])
        print('moving {}'.format(file))

    print(files)
    combined = merge_csvs(files)
    print('merged')
    df = pd.read_csv(combined)
    df, user_info = processor(df)
    print('first processed')
    savefile = os.path.join(dir, 'data/all_cleaned.csv')
    

    for file in files:
        os.remove(file)

    print("getting sentiment and all")

    df['ID'] = df['ID'].astype(int)

    df = add_keyword(df)
    df = df[df['keyword'] != 'invalid']
    df = df.reset_index(drop=True)
    df = get_sentiment(df)

    #because of some bug in pandas, saving and rereading is needed to prevent wrong data
    df.to_csv(savefile, index=None)

    df = pd.read_csv(savefile)
    df = clean_further(df)

    df.to_csv(savefile, index=None)

    os.makedirs(dir + "/data/temp/profiles")
    
    user_info = clean_profile(user_info)
    user_info.to_csv(dir + "/data/temp/profiles/{}.csv".format(int(time.time())), index=None)
    #five minute profile processes. It sent there because profile cleaning takes time.

    df = df.sort_values('Time')
    df.groupby('keyword').apply(save_to_file) #should be appended to this file. Features have to be added

    curr_start = df.iloc[0]['Time']
    curr_end = df.iloc[-1]['Time']

    storage_dir = os.path.join(dir, 'data/storage/all_cleaned/')

    if not os.path.isdir(storage_dir):
        os.makedirs(storage_dir)

    storagename = os.path.join(storage_dir, 'all_cleaned_{}.csv'.format(int(time.time())))
    shutil.move(savefile, storagename)

    for idx, row in keywords.iterrows():
        print(row['Symbol'])
        tweet_df = pd.read_csv(dir + '/data/coinwise/{}.csv'.format(row['Symbol']))
        tweet_df['Time'] = pd.to_datetime(tweet_df['Time'])

        price_df = get_price(row['Symbol'])


        tweet_df = tweet_df.sort_values('Time')
        tweet_df = tweet_df.set_index('Time')
        tweet_df.index = tweet_df.index.ceil(freq='30Min')  
        tweet_df = tweet_df.reset_index()

        features = get_features(tweet_df, price_df, row['Symbol'], curr_start, curr_end)

def ten_minute():
    files = dir + "/data/temp/profiles/*"
    temp_profiles = merge_csvs(files)
    user_info = pd.read_csv(temp_profiles)
    profilefile = os.path.join(dir, 'data/cleaned_profile.csv')
    
    if os.path.isfile(profilefile):
        user_info = pd.concat([user_info, pd.read_csv(profilefile)])
        user_info = clean_profile(user_info)

    user_info.to_csv(profilefile, index=None)

    for file in files:
        os.remove(file)

def thirty_minutes_backtest():
    keywords = get_keywords()

    for idx, row in keywords.iterrows():
        perform_backtest(row['Symbol'], n_fast_par=n_fast_par, n_slow_par=n_slow_par, long_macd_threshold_par=long_macd_threshold_par, 
                    long_per_threshold_par=long_per_threshold_par, long_close_threshold_par=long_close_threshold_par, 
                    short_macd_threshold_par=short_macd_threshold_par, short_per_threshold_par=short_per_threshold_par, 
                    short_close_threshold_par=short_close_threshold_par, initial_cash=initial_cash, comission=comission)

def three_day():
    weekly_process()

if __name__ == "__main__":
    t = Thread(target=twitter_stream)
    t.start()

    print('Started Live Tweet Collection')

    t = Thread(target=price_stream)
    t.start()

    print('Started Live Price Collection')

    dir = get_root_dir()
    temp_dir = os.path.join(dir, 'data/temp')

    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)