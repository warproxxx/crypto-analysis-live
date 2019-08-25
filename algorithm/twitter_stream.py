import tweepy
import csv
import sys
import datetime
import time
import logging
from utils.twitter_authentication import *
from utils.common_utils import get_root_dir
import pandas as pd
import os
from calendar import timegm

def get_file_name():
    fname = os.path.join(get_root_dir(), 'data/forwardtest/twitter_stream/' + str(datetime.datetime.now().date()) + '.csv')
    
    stream_dir = os.path.join(get_root_dir(), 'data/forwardtest/twitter_stream')

    if not os.path.isdir(stream_dir):
        os.makedirs(stream_dir)

    if os.path.isfile(fname):
        pass
    else:
        # create output file and add header
        with open(fname, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            header = ['timestamp','id','text','likes','retweets','username','user_id','user_created_at','in_response_to', 'in_response_to_user_id', 'response_type', 'has_geolocation', 'is_verified', 'total_tweets', 'total_followers', 'total_following', 'total_likes', 'total_lists', 'has_background', 'is_protected', 'default_profile']
            writer.writerow(header)
    
    return fname

# function for adding data to csv file
def write_csv(row_data):
    filename = get_file_name()

    with open(filename, 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row_data)

#override tweepy.StreamListener to add logic to on_status
#override tweepy.StreamListener to add logic to on_status
class MyStreamListener(tweepy.StreamListener):

    def on_status(self, tweet):
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
                tweetText = tweetText + tweet.text
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
        tweet.user.followers_count, tweet.user.friends_count, tweet.user.favourites_count, tweet.user.listed_count,
        tweet.user.profile_use_background_image, tweet.user.protected, tweet.user.default_profile])

        # all parameters possible here:
        # https://dev.twitter.com/overview/api/tweets

def twitter_stream():
    df = pd.read_csv(os.path.join(get_root_dir(), 'keywords.csv'))
    search_query = []

    for row in df['Keywords']:
        currKeywords = [x.strip() for x in row.split(',')]
        search_query = search_query + currKeywords

    logger = logging.getLogger(__name__)

    # auth & api handlers
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    print('Authenticated as %s' % api.me().screen_name)

    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener)

    while True:
        print("Starting stream tracking")
        try:
            myStream.filter(track=search_query, languages=['en'])
        except Exception as e:
            print('error')
            # Network error or stream failing behind
            # https://github.com/tweepy/tweepy/issues/448
            # prevent stream from crashing & attempt to recover
            logger.info(e)
            print(e)
            continue
