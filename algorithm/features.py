'''
Contains the modules required for features creation
'''

import pandas as pd
from glob import glob
import swifter
import numpy as np
import matplotlib.pyplot as plt
import os
import ta

def merge_time(df):
    ret = {}
    ret['Open'] = df.iloc[0]['Open']
    ret['High'] = max(df['High'])
    ret['Low'] = min(df['Low'])
    ret['Close'] = df.iloc[-1]['Close']
    ret['Volume'] = sum(df['Volume'])
    return pd.Series(ret)

#maybe create a percentage of influential users
def tweets_to_features(group):
    features = {}
    
    bots = group[group['predicted'] == 1]
    humans = group[group['predicted'] == 0]
    
    features['number_of_tweets'] = len(group)
    try:
        features['percentage_bots'] = (len(bots)/len(group)) * 100
    except:
        features['percentage_bots'] = 0
        
    features['total_influence'] = group['avg_influence'].sum()
    
    try:
        features['sentistrength_total'] = sum(group['pos_neg'] * group['avg_influence'])
    except:
        features['sentistrength_total'] = 0
        
    try:
        features['vader_total'] = sum(group['vader_emotion'] * group['avg_influence'])
    except:
        features['vader_total'] = 0
    
    try:
        features['sentistrength_total_mean'] = sum(group['pos_neg'] * group['avg_influence'])/sum(group['avg_influence'])
    except:
        features['sentistrength_total_mean'] = 0
        
    try:
        features['vader_total_mean'] = sum(group['vader_emotion'] * group['avg_influence'])/sum(group['avg_influence'])
    except:
        features['vader_total_mean'] = 0
    
    return pd.Series(features)

def get_features(coin_name, minutes, test='forwardtest'):
    '''
    Create features for the given coin
    '''
    userwise_inf_file = os.path.join(dir, 'data/userwise_influence.csv')
    userwise_inf = pd.read_csv(userwise_inf_file)
    
    price_df = pd.read_csv('data/{}/processed_price/{}.csv'.format(test, coin_name))
    tweet_df = pd.read_csv('data/{}/coinwise/{}.csv'.format(test, coin_name))
    
    price_df['Time'] = pd.to_datetime(price_df['Time'], unit='s')
    tweet_df['Time'] = pd.to_datetime(tweet_df['Time'])
    
    tweet_df = tweet_df.merge(userwise_inf[['username', 'avg_influence', 'total_influence']], left_on='User', right_on='username')
    price_df = price_df.groupby(pd.Grouper(key='Time', freq='{}Min'.format(str(minutes)))).apply(merge_time)

    new_df = pd.DataFrame()
    new_df['time'] = price_df.index

    tweet_df = tweet_df.rename(columns={'Time': 'time'})
    tweet_df = tweet_df.sort_values('time')
    new_df['time_group'] = new_df['time']
    tweet_df = pd.merge_asof(tweet_df, new_df, on='time', direction='nearest')
    
    tweet_df = tweet_df[((tweet_df['time_group'] - tweet_df['time']).astype(int) // 10 ** 9).abs() < (minutes*60)]

    features = tweet_df.groupby('time_group').apply(tweets_to_features)
    features = features.reset_index().rename(columns={'time_group': 'Time'}).set_index('Time')
    features = features.join(price_df, how='outer')
    features = features.reset_index()
    features = features.fillna(0)
    return features