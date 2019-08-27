from multiprocessing.pool import Pool
import requests
import json
import random
import time
import csv

from functools import partial

from utils.profilescraper.profile import Profile

import os

class profileScraper:
    def __init__(self, proxy=None):
        self.HEADERS_LIST = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0', 'Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0']        
        self.proxy = proxy

    def query_single_profile(self, url, retry=10):
        print("Querying {}".format(url))
        
        headers = {'User-Agent': random.choice(self.HEADERS_LIST)}

        try:
            if (self.proxy == None):
                response = requests.get(url, headers=headers)
            else:
                response = requests.get(url, headers=headers, proxies=self.proxy)

            html = response.text or ''

            profile = Profile.from_html(html)

            if not profile:
                return 0

            return profile
        except requests.exceptions.HTTPError as e:
            print('HTTPError {} while requesting "{}"'.format(
                e, url))
        except requests.exceptions.ConnectionError as e:
            print('ConnectionError {} while requesting "{}"'.format(
                e, url))
        except requests.exceptions.Timeout as e:
            print('TimeOut {} while requesting "{}"'.format(
                e, url))
        except json.decoder.JSONDecodeError as e:
            print('Failed to parse JSON "{}" while requesting "{}".'.format(
                e, url))
        except ValueError as e:
            print('Failed to parse JSON "{}" while requesting "{}"'.format(e, url))

        if retry > 0:
            print("Retrying... (Attempts left: {})".format(retry))
            return self.query_single_profile(url, retry-1)
        
        print("Giving up.")
        return 0


    def query_profile(self, profiles, poolsize=20):
        '''
        profiles: List
        Unique profies to scrape from

        poolsize: int
        Size of pool. Bigger - the more instance of browser is opened
        '''

        url = "https://twitter.com/{}"
        no_profiles = len(profiles)

        if (poolsize > no_profiles):
            poolsize = no_profiles

        urls = [url.format(x) for x in profiles]
        all_profiles = []

        pool = Pool(poolsize)
        profile_received = 0

        try:
            for profile in pool.imap_unordered(partial(self.query_single_profile), urls):
                profile_received = profile_received+1
                all_profiles.append(profile)
                print("Got {} profiles (1 new).".format(profile_received))            
        finally:
            pool.close()
            pool.join()

        return all_profiles
