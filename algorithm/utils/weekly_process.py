import pandas as pd
import numpy as np
import csv

from glob import glob
import os
import swifter
import shutil

import tweepy

import time
import datetime
from calendar import timegm

from utils.casIn.user_influence import P,influence
from utils.common_utils import get_root_dir, merge_csvs
from utils.twitter_authentication import *
from utils.profilescraper import profileScraper
from process import create_cascades, processor, process_scraped_profile, get_sentiment

def get_influence(df):
    df = df.reset_index(drop=True)

    p_ij = P(df,r = -0.000068)
    inf, m_ij = influence(p_ij)
    df['inf'] = inf
    df = df[['ID', 'inf', 'cascade']]
    return df

def get_file_name():
    fname = get_root_dir() + '/algorithm/data/temp/rescraped.csv'

    if os.path.isfile(fname):
        pass
    else:
        # create output file and add header
        with open(fname, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            header = ['timestamp','id','text','likes','retweets','username','user_id','user_created_at','in_response_to', 
                      'in_response_to_user_id', 'response_type', 'has_geolocation', 'is_verified', 'total_tweets', 'total_followers', 
                      'total_following', 'total_likes', 'total_lists', 'has_background', 'is_protected', 'default_profile']
            
            writer.writerow(header)
    
    return fname

# function for adding data to csv file
def write_csv(row_data):
    filename = get_file_name()

    with open(filename, 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row_data)

def make_tweets(find_id):
    found = original[original['in_response_to_id'] == find_id]
    parsed = p.parse(found.iloc[0]['Tweet'])
    
    current_tweet = {}
    
    current_tweet['ID'] = found.iloc[0].in_response_to_id
    current_tweet['Tweet'] = found.iloc[0].Tweet
    current_tweet['Time'] = found.iloc[0].Time - (found.iloc[1].Time - found.iloc[0].Time)
    try:
        current_tweet['User'] = parsed.users[0]
    except:
        current_tweet['User'] = ''
    current_tweet['Likes'] = 0
    current_tweet['Retweets'] = 0
    current_tweet['in_response_to_id'] = 0
    current_tweet['response_type'] = 'tweet'
    
    return pd.Series(current_tweet)

def rescrape_and_add(original, to_scrape):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    print("Rescraping {} tweets".format(to_scrape))
    for i in range(100, len(to_scrape)+100, 100):
        print("{} {}".format(i-100, i))
        
        tweets = api.statuses_lookup(to_scrape['index'][i-100:i].values,tweet_mode='extended')
        
        for tweet in     tweets:
            response_type = 'tweet'
            in_response_to = None

            try:
                in_response_to = tweet.in_reply_to_status_id
                in_response_to_user_id = tweet.in_reply_to_user_id_str
            except:
                pass

            if in_response_to == None:
                if hasattr(tweet, 'retweeted_status'):
                    response_type = 'retweet'
                    in_response_to = tweet.retweeted_status.id
                    in_response_to_user_id = tweet.retweeted_status.user._json['id_str'] #probably not required
                else:
                    if hasattr(tweet, 'quoted_status'):
                        response_type = 'quoted_retweet'
                        in_response_to = tweet.quoted_status.id
                        in_response_to_user_id = tweet.quoted_status.user._json['id_str'] #probably not required
                    else:
                        in_response_to = '0'
            else:
                response_type = 'reply'


            tweetText = ''
            try:
                tweetText = tweetText + tweet.extended_tweet['full_text']
            except:
                try:
                    tweetText = tweetText + tweet.full_text
                except:
                    pass

            try:
                tweetText = tweetText + ' <retweeted_status> ' + tweet.retweeted_status.extended_tweet['full_text'] + ' </retweeted_status>'
            except:
                try:
                    tweetText = tweetText + ' <retweeted_status> ' + tweet.retweeted_status.text + ' </retweeted_status>'
                except:
                    pass

            try:
                tweetText = tweetText + ' <quoted_status> ' + tweet.quoted_status.extended_tweet['full_text'] + ' </quoted_status>'
            except:
                try:
                    tweetText = tweetText + ' <quoted_status> ' + tweet.quoted_status.text + ' </quoted_status>'
                except:
                    pass

            if 'urls' in tweet.entities:
                for url in tweet.entities['urls']:
                    try:
                        tweetText = tweetText.replace(url['url'], url['expanded_url'])
                    except:
                        pass

            write_csv([tweet.created_at, tweet.id, tweetText, tweet.favorite_count, tweet.retweet_count,            
            tweet.user.screen_name, tweet.user._json['id_str'], tweet.user._json['created_at'],in_response_to, 
            in_response_to_user_id ,response_type, tweet.user.geo_enabled, tweet.user.verified, tweet.user.statuses_count, 
            tweet.user.followers_count, tweet.user.friends_count, tweet.user.favourites_count, tweet.user.listed_count
            ,tweet.user.profile_use_background_image, tweet.user.protected, tweet.user.default_profile])

    
    rescraped = pd.read_csv(get_root_dir() + '/data/temp/rescraped.csv')
    profile = pd.read_csv(os.path.join(get_root_dir(), 'data/cleaned_profile.csv'))
    
    original['Time'] = pd.to_datetime(original['Time'])

    original['Time'] = original['Time'].astype(int) // 10**9
    rescraped_df, rescraped_profile = processor(rescraped)
    non_existing = to_scrape[~to_scrape['index'].isin(rescraped['id'])]

    p = ttp.Parser()
    virtual_tweets = non_existing['index'].apply(make_tweets)
    rescraped = pd.concat([virtual_tweets, rescraped_df]).reset_index(drop=True)
    virtual_tweets['User'] = virtual_tweets['User'].str.lower()
    rescrape = virtual_tweets[~virtual_tweets['User'].isin(profile['username'])]
    ps = profileScraper()
    scraped = ps.query_profile(rescrape['User'].values)
    scraped_profile = process_scraped_profile(scraped)

    new_profile = pd.concat([scraped_profile, rescraped_profile, profile]) #clean them seperately before concating
    new_profile = new_profile.drop_duplicates(subset=['username']).reset_index(drop=True)
    new_profile.to_csv(os.path.join(get_root_dir(), 'data/cleaned_profile.csv'), index=None)

    rescraped = get_sentiment(rescraped)
    new_df = pd.concat([original, rescraped])
    new_df = new_df.sort_values('Time')

    return new_df, new_profile

# Every week, after all clean, leave the cascade of the last 2 days and join 5 days (leaving the 2 days) to update influence and all. Our influence file will probably be renamed
# to include the date. This strategy has flaws of missed tweet too. But that is good enough for now

dir = get_root_dir()
storagefolder = os.path.join(dir, 'data/storage')

storagesfiles = glob(storagefolder + "/*")
combined = merge_csvs(storagesfiles)
df = pd.read_csv(combined)

df['Time'] = pd.to_datetime(df['Time'])
df = create_cascades(df) 

df = df.sort_values('Time')

counts = df['cascade'].value_counts().reset_index()
ids_count = counts[counts['cascade'] > 3][['index']]
non_existing = ids_count[~ids_count['index'].isin(df['ID'])]

df, profile = rescrape_and_add(df, non_existing)
df = df.merge(profile[['username', 'total_followers']], left_on='User', right_on='username', how='inner')
df = df.rename(columns={'Time': 'time', 'total_followers': 'magnitude', 'User': 'user_id'})
counts = df['cascade'].value_counts().reset_index()

df = df[df['cascade'].isin(counts[counts['cascade'] > 2]['index'])]
oldcascade_file = storagefolder + "/old_cascade.csv"
df = df[['ID', 'time', 'magnitude', 'user_id', 'cascade']]

#This mechanism still has repetition and needs to be fixed
if os.path.isfile(oldcascade_file):
    old_file = pd.read_csv(oldcascade_file)
    oldcascade_file = oldcascade_file[oldcascade_file['cascade'].isin(df['cascade'])]
    df.to_csv(oldcascade_file, index=None)

    df = pd.concat([df, oldcascade_file])
    df = df.reset_index()
else:
    df.to_csv(oldcascade_file, index=None)

d = df.groupby('cascade').apply(get_influence)
d = d.drop_duplicates()
df = df.merge(d, on='ID')
df = df.drop('cascade_y', axis=1).rename(columns={'cascade_x':'cascade'})

#update the influence file
curr_inf = pd.read_csv(os.path.join(dir, 'data/userwise_influence.csv')) #save code probably needs to moved down here
#work on the interface for now. Still lot to do here as seen in http://localhost:8888/notebooks/crypto-analysis/meta_analyse/data_analysis/2)%20Influence%20Calculation.ipynb