from datetime import datetime
from bs4 import BeautifulSoup
import json

from coala_utils.decorators import generate_ordering

#modify to include the missing values
@generate_ordering('username', 'created_at', 'statuses_count', 'followers_count', 'friends_count', 'favourites_count', 'listed_count', 'default_profile', 'geo_enabled', 'profile_use_background_image', 'verified', 'protected')
class Profile:
    def __init__(self, username, created_at, statuses_count, followers_count, friends_count, favourites_count, listed_count, default_profile, geo_enabled, profile_use_background_image, verified, protected):
        try:
            self.username = username.replace("@", "")
        except:
            self.username = ""
        
        self.created_at = created_at
        self.statuses_count = statuses_count
        self.followers_count = followers_count
        self.friends_count = friends_count
        self.favourites_count = favourites_count
        self.listed_count = listed_count
        self.default_profile = default_profile
        self.geo_enabled = geo_enabled
        self.profile_use_background_image = profile_use_background_image
        self.verified = verified
        self.protected = protected


    @classmethod
    def from_soup(cls, soup):
        try:
            sideBar = soup.find('div', 'ProfileHeaderCard')
        except:
            sideBar = ""
        
        try:
            username = sideBar.find('span', 'username').get_text()
        except:
            username = ""
        
        created_at = ""
        statuses_count = ""
        followers_count = ""
        friends_count = ""
        favourites_count = ""
        listed_count = ""
        default_profile = ""
        geo_enabled = ""
        profile_use_background_image = ""
        verified = ""
        protected = ""

        try:
            json_details = json.loads(soup.find('input', {'class': 'json-data'})['value'])
            user_details = json_details['profile_user']
            created_at = user_details['created_at'] 
            statuses_count = user_details['statuses_count'] 
            followers_count = user_details['followers_count']
            friends_count = user_details['friends_count']
            favourites_count = user_details['favourites_count'] 
            listed_count = user_details['listed_count'] 
            default_profile = user_details['default_profile']
            geo_enabled = user_details['geo_enabled']
            profile_use_background_image = user_details['profile_use_background_image']
            verified = user_details['verified']
            protected = user_details['protected']
        except Exception as e:
            print("Got an error scraping: {}".format(str(e)))

        return cls(
            username=username,
            created_at=created_at,
            statuses_count=statuses_count,
            followers_count=followers_count,
            friends_count=friends_count,
            favourites_count=favourites_count,
            listed_count=listed_count,
            default_profile=default_profile,
            geo_enabled=geo_enabled,
            profile_use_background_image=profile_use_background_image,
            verified=verified,
            protected=protected
        )

    @classmethod
    def from_html(cls, html):
        soup = BeautifulSoup(html, "lxml")
        profile = Profile.from_soup(soup)
        return profile