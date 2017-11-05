# Wurm twitter feed Discord integration

import configparser
import html
import tweepy
import json
import requests
import urllib.request
from pprint import pprint
import sqlite3
from time import sleep
import sys

config = configparser.ConfigParser()
config.read('config.ini')

WEBHOOK = config["webhook"]["feed"]
WEBHOOK_ALERTS = config["webhook"]["alerts"]

FOLLOW = config["twitter"]["follow"].split()

auth = tweepy.OAuthHandler(config["twitter"]["consumer_key"], config["twitter"]["consumer_secret"])
auth.set_access_token(config["twitter"]["access_token_key"], config["twitter"]["access_token_secret"])

api = tweepy.API(auth)

conn = sqlite3.connect('tweets.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tweets(name VARCHAR, tweet_id  INT, text VARCHAR)''')
conn.commit()

AGES = ["young", "adolescent", "mature", "aged", "old", "venerable"]
ANIMALS = [
        "anaconda",
        "black bear",
        "black wolf",
        "brown bear",
        "cave bug",
        "crab",
        "crocodile",
        "fog spider",
        "goblin",
        "hell hound",
        "hell scorpious",
        "huge spider",
        "large rat",
        "lava fiend",
        "lava spider",
        "mountain lion",
        "scorpion",
        "sea serpent",
        "shark",
        "troll",
        "wild boar",
        "wild cat",
        "deathcrawler minion",
        "drakespirit"
        "eaglespirit",
        "sol demon",
        "son of nogump",
        "spawn of uttacha"
        ]

def forward_tweet(tweet, webhook):
    data = {
            'username': tweet.user.name,
            'content': html.unescape(tweet.text)
        }

    try:
        while True:
            result = requests.post(webhook, data=json.dumps(data), headers={"content-type":"application/json"}, timeout=10)
            resp = None
            try:
                resp = json.loads(result.text)
            except json.decoder.JSONDecodeError as e:
                pass

            if resp and "retry_after" in resp:
                print ("Hit rate limit. Sleeping", resp["retry_after"], "ms")
                sleep(resp["retry_after"]/1000)
                continue
            return True

    except Exception as e:
        print (e, file=sys.stderr)
        return False

def save_tweet(tweet):
    c.execute("""INSERT INTO tweets (tweet_id, name, text) VALUES(?,?,?)""",
            (tweet.id, tweet.user.screen_name, html.unescape(tweet.text)))
    conn.commit()

def process_tweet(tweet):
    print ("Got", html.unescape(tweet.text))

    if "raises the settlement alarm!" in tweet.text:
        #if not any(a in tweet.text for a in AGES) or not any(a in tweet.text for a in ANIMALS):
        foo = [a in tweet.text for a in AGES]
        bar = [a in tweet.text for a in ANIMALS]
        if not any(foo) or not any(bar):
            forward_tweet(tweet, WEBHOOK_ALERTS)

    if forward_tweet(tweet, WEBHOOK):
        save_tweet(tweet)

def poll_user(username):
    c.execute("SELECT MAX(tweet_id) FROM tweets WHERE name='%s'" % (username));
    since_id = c.fetchone()[0]

    tweets = {}
    for tweet in tweepy.Cursor(api.user_timeline,
            screen_name=username,
            since_id = since_id,
            wait_on_rate_limit = True,
            wait_on_rate_limit_notify = True,
            ).items(10000):
        tweets[tweet.id] = tweet

    for tweet_id, tweet in tweets.items():
        process_tweet(tweet)

def loop():
    rate_limits = api.rate_limit_status()
    while True:
        for username in FOLLOW:
            try:
                poll_user(username)
            except Exception as e:
                print (e, file=sys.stderr)
        seconds = rate_limits["resources"]["statuses"]["/statuses/user_timeline"]["limit"]/900*len(FOLLOW)
        sleep(seconds)

if __name__ == '__main__':
    loop()
