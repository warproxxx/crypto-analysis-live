'''
Created with help from:
https://pawelmhm.github.io/asyncio/python/aiohttp/2016/04/22/asyncio-aiohttp.html
'''

import asyncio
import pandas as pd
from aiohttp import ClientSession
from urllib.parse import urlparse

all_urls = pd.read_csv('urls.csv')['url'].values
all_urls_with_port = []

for url in all_urls:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        replaced = parsed._replace(netloc=parsed.netloc + ":443")
    else:
        replaced = parsed._replace(netloc=parsed.netloc + ":80")
        
    all_urls_with_port.append(replaced.geturl())

async def fetch(url, session):
    try:
        async with session.head(url, allow_redirects=True) as response:
            open('resolved.csv', 'a').write('{},{}\n'.format(url, response.url))
            return response.url
    except Exception as e:
        print(str(e))
        return ""

async def bound_fetch(sem, url, session):
    async with sem:
        await fetch(url, session)

async def run(r):
    global all_urls
    tasks = []
    sem = asyncio.Semaphore(1000)

    async with ClientSession() as session:
        for i in range(r):
            task = asyncio.ensure_future(bound_fetch(sem, all_urls_with_port[i], session))
            tasks.append(task)

        responses = asyncio.gather(*tasks)
        await responses

number = len(all_urls)
loop = asyncio.get_event_loop()

future = asyncio.ensure_future(run(number))
loop.run_until_complete(future)
