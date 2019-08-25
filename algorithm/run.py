import os
import shutil
from threading import Thread
from glob import glob

import pandas as pd
import numpy as np

import datetime
import time

from twitter_stream import twitter_stream
from utils.common_utils import get_root_dir, merge_csvs
from process import processor, get_sentiment, clean_further, create_cascades, add_keyword

t = Thread(target=twitter_stream)
t.start()

print('Started Live Collection')

dir = get_root_dir()
temp_dir = os.path.join(dir, 'data/temp')

if not os.path.isdir(temp_dir):
    os.makedirs(temp_dir)

def save_to_file(df):
    global dir
    keyword = df.iloc[0]['keyword']
    print(keyword)
    
    df = df.drop('keyword', axis=1)

    coinwise_folder = os.path.join(dir, "data/forwardtest/coinwise")

    if not os.path.isdir(coinwise_folder):
        os.makedirs(coinwise_folder)

    savefile = "{}/{}.csv".format(coinwise_folder, keyword)

    if os.path.isfile(savefile):
        df.to_csv(savefile, index=None, mode='a')
    else:
        df.to_csv(savefile, index=None)

while True:
    #Use this logic later but for testing not
    # currentTime = datetime.datetime.now(datetime.timezone.utc)

    # if currentTime.minute % 30 != 0: #change logic to better run it every 30 mins
    #     time.sleep(5)
    # else:
    time.sleep(10)

    files = glob('data/forwardtest/twitter_stream/*')
    
    #copy these files into a folder so they can be processed independently
    for idx, file in enumerate(files):
        old_name = os.path.join(dir, files[idx])
        files[idx] = os.path.join(dir, files[idx].replace('forwardtest/twitter_stream/', 'temp/'))
        shutil.move(old_name, files[idx])

    combined = merge_csvs(files)
    df = pd.read_csv(combined)
    df, user_info = processor(df)

    savefile = os.path.join(dir, 'data/forwardtest/all_cleaned.csv')

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

    df = df[df['keyword'] != 'invalid']
    df.groupby('keyword').apply(save_to_file)
    
    #For feature calculation only use those which were not blacklisted. Price too

        #CASCADING IS NOT REQUIRED TO CALCULATE DAILY FEATURES. DO THOSE AT THE END OF THE DATA
    # if 24hour:
    #     df = create_cascades(df) #do this only for tweets which are no longer being retweeted. Finding that out is tricky
    #     counts = df['cascade'].value_counts().reset_index()
    #     ids_count = counts[counts['cascade'] > 3][['index']]
    #     non_existing = ids_count[~ids_count['index'].isin(df['ID'])]

    #     rescrape_file = os.path.join(dir, 'data/to_scrape.csv')

    #     non_existing.to_csv(rescrape_file, index=None)
    #Now File 3. Do these later. First the live management. Later do these