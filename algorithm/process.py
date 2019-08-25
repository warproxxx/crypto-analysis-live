import pandas as pd
import numpy as np
from utils.common_utils import get_root_dir
import swifter
import os
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from subprocess import Popen

def clean_further(df):
    '''
    Final Cleaning step to drop non numeric
    '''
    df = df[pd.to_numeric(df['ID'], errors='coerce').notnull()]
    df = df[pd.to_numeric(df['in_response_to_id'], errors='coerce').notnull()]
    df['ID'] = df['ID'].astype(int)
    df['in_response_to_id'] = df['in_response_to_id'].astype(int)
    df = df.drop_duplicates(subset=['ID'])
    return df

def create_cascades(df):
    df['cascade'] = df['in_response_to_id']
    df.loc[df[df['cascade'] == 0].index, 'cascade'] = df[df['cascade'] == 0].ID
    return df

def clean_profile(user_info):
    user_info = user_info.fillna(0)

    user_info = user_info[user_info['username'] != ""]
    user_info = user_info[user_info['username'] != 0]


    user_info['username'] = user_info['username'].str.lower()

    user_info['has_background'] = user_info['has_background'].astype(bool)
    user_info['is_protected'] = user_info['is_protected'].astype(bool)
    user_info['default_profile'] = user_info['default_profile'].astype(bool)
    user_info['has_geolocation'] = user_info['has_geolocation'].astype(bool)
    user_info['is_verified'] = user_info['is_verified'].astype(bool)

    user_info['has_background'] = user_info['has_background'].astype(int)
    user_info['is_protected'] = user_info['is_protected'].astype(int)
    user_info['default_profile'] = user_info['default_profile'].astype(int)
    user_info['has_background'] = user_info['has_background'].astype(int)
    user_info['has_geolocation'] = user_info['has_geolocation'].astype(int)
    user_info['is_verified'] = user_info['is_verified'].astype(int)

    user_info = user_info.reset_index(drop=True)

    user_info['user_created_at'] = pd.to_datetime(user_info['user_created_at'])
    user_info['user_created_at'] = user_info['user_created_at'].astype(np.int64) // 10**9

    user_info = user_info.drop_duplicates(subset='username')

    return user_info[['username', 'user_created_at', 'total_tweets', 'total_followers', 'total_following', 'total_likes', 'total_lists', 'default_profile', 'has_geolocation', 'has_background', 'is_verified', 'is_protected']]

def process_scraped_profile(all_profiles):
    dict = {}

    i = 0 

    for profile in all_profiles:
        dict[i] = {'username': profile.username, 'user_created_at': profile.created_at, 'total_tweets': profile.statuses_count, 
        'total_followers': profile.followers_count, 'total_following':profile.friends_count , 'total_likes': profile.favourites_count, 
        'total_lists': profile.listed_count, 'default_profile': profile.default_profile, 'has_geolocation': profile.geo_enabled, 
        'has_background': profile.profile_use_background_image, 'is_verified': profile.verified, 'is_protected': profile.protected}

        i = i + 1
    
    df = pd.DataFrame.from_dict(dict).T
    
    df = clean_profile(df)

    return df

def processor(df):
    '''
    Parameters:
    ___________

    df (Dataframe): The long collected dataframe

    Returns:
    ________
    df, userInfo (dataframe): cleaned and converted into profile and user data
    '''
    user_info = df[['username', 'user_created_at', 'has_geolocation', 'is_verified', 'total_tweets', 'total_followers', 'total_following', 'total_likes', 'total_lists', 'has_background', 'is_protected', 'default_profile']].drop_duplicates(subset='username', keep='last')
    user_info = clean_profile(user_info)
    
    df = df[['timestamp', 'id', 'text', 'likes', 'retweets', 'username', 'in_response_to', 'response_type']]

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].astype(np.int64) // 10**9

    df = df.fillna(0)

    df['in_response_to'] = df['in_response_to'].fillna(0)
    df['in_response_to'] = df['in_response_to'].astype(int)

    df = df.drop_duplicates()
    df = df.rename(columns={'id': 'ID', 'timestamp': 'Time', 'username': 'User', 'text': 'Tweet', 'in_response_to': 'in_response_to_id', 'likes': 'Likes', 'retweets': 'Retweets'})


    
    
    df = df.reset_index(drop=True)
    df = df[['ID', 'Tweet', 'Time', 'User', 'Likes', 'Retweets', 'in_response_to_id', 'response_type']]

    return df, user_info

def add_keyword(df, drop_non_existing=False):
    '''
    Adds keyword to the df

    Parameters:
    ___________

    df (Dataframe): The dataframe

    drop_non_existing (Boolean): To drop non existing or not
    '''
    #do cascading here too and include the entire cascade if more than 5% of values contain a keyword. The cascade contains that keyword. This means convert to like this

    current = get_root_dir()
    path = os.path.join(current, "keywords.csv")

    keywords = pd.read_csv(path)
    keywords = keywords.set_index('Symbol')

    symbol_keyword = {}

    for idx, row in keywords.iterrows():
        currKeywords = [x.strip().lower() for x in row['Keywords'].split(',')]
        symbol_keyword[idx] = currKeywords
    

    #maybe a crypto keyword? Bitcoin should be last
    def find_which(x):
        x = x.lower()

        nonlocal symbol_keyword

        matches = []
        
        for idx,row in symbol_keyword.items():
            for keyword in row:
                if keyword in x:
                    matches.append(idx)
        
        matches = list(set(matches))

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 2:
            if 'BTC' in matches:
                req_index = 1 - matches.index('BTC')
                return matches[req_index]
        
        return "invalid"

    df['keyword'] = df['Tweet'].swifter.apply(find_which)
    return df

def get_sentiment(df):
    '''
    Adds sentiment to the df
    '''
    root_dir = get_root_dir()

    s = SentimentIntensityAnalyzer()
    df['vader_emotion'] = df['Tweet'].swifter.apply(lambda x: s.polarity_scores(x)['compound'])

    cop = df['Tweet'].copy()
    
    cop = cop.fillna("NA")

    cop = cop.replace(r'\\n',' ', regex=True) 
    cop = cop.replace(r'\n',' ', regex=True) 

    cop = cop.replace(r'\\r',' ', regex=True) 
    cop = cop.replace(r'\r',' ', regex=True) 

    cop = cop.replace(r'\\t',' ', regex=True) 
    cop = cop.replace(r'\t',' ', regex=True) 

    tempFolder = os.path.join(root_dir, "data/temp")
    tempFile = os.path.join(tempFolder, "tweets")
    cop.to_csv(tempFile, index=None, header=None)


    sentiFolder = os.path.join(root_dir, "utils")
    

    command = "java -jar {} sentidata {} input {}".format(os.path.join(sentiFolder, "SentiStrength.jar"), os.path.join(sentiFolder, "SentiStrength_Data/"), tempFile)
    print(command)

    process= Popen(command.split())
    process.wait()

    os.remove(tempFile)


    outputFile = os.path.join(tempFolder, "tweets0_out.txt")
    aa = pd.read_csv(outputFile, sep="\t")
    df = df.join(aa[['Positive', 'Negative']])
    os.remove(outputFile)

    df['pos_neg'] = df['Positive'] + df['Negative']

    df = df.drop(['Positive', 'Negative'], axis=1)

    return df