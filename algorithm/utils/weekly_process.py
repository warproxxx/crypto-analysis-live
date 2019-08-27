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
from process import create_cascades

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

def rescrape_and_add(original, to_scrape):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

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

    
    rescraped = pd.read_csv(get_root_dir() + '/algorithm/data/temp/rescraped.csv')



# Every week, after all clean, leave the cascade of the last 2 days and join 5 days (leaving the 2 days) to update influence and all. Our influence file will probably be renamed
# to include the date. This strategy has flaws of missed tweet too. But that is good enough for now

dir = get_root_dir()
savefile = os.path.join(dir, 'data/all_cleaned.csv')
storagefile = os.path.join(dir, 'data/storage/all_cleaned_{}.csv'.format(int(time.time())))
allcleaned_old = os.path.join(dir, 'data/all_cleaned_old.csv')

shutil.move(savefile, storagefile)

df = pd.read_csv(storagefile)

df['Time'] = pd.to_datetime(df['Time'])
df = create_cascades(df) 

df = df.sort_values('Time')

counts = df['cascade'].value_counts().reset_index()
ids_count = counts[counts['cascade'] > 3][['index']]
non_existing = ids_count[~ids_count['index'].isin(df['ID'])]

df = rescrape_and_add(df, non_existing)

#leave info on cascade to merge it later

#do this only for tweets which are no longer being retweeted. Finding that out is tricky
#     counts = df['cascade'].value_counts().reset_index()
#     ids_count = counts[counts['cascade'] > 3][['index']]
#     non_existing = ids_count[~ids_count['index'].isin(df['ID'])]

#     rescrape_file = os.path.join(dir, 'data/to_scrape.csv')

#     non_existing.to_csv(rescrape_file, index=None)
#Now File 3. Do these later. First the live management. Later do these