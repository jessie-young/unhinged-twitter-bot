import argparse
import redis

from unhinged_twitter_bot.config import REDIS_EVENTS_PUBSUB_ADDR, REDIS_TWEET_TOPIC
from unhinged_twitter_bot.twitter import TwitterAPI


def make_tweet(author: str, content: str):
    print(f"Making tweet for @{author}: {content}")
    api = TwitterAPI.get_api()
    api.make_tweet(content, author)


def view_tweet():
    r = redis.Redis.from_url(f"redis://{REDIS_EVENTS_PUBSUB_ADDR}")
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_TWEET_TOPIC)
    
    print("Listening for tweets...")
    for message in pubsub.listen():
        if message["type"] == "message":
            print(f"Received tweet: {message['data'].decode('utf-8')}")
            break  # Exit after receiving one message
    
    pubsub.unsubscribe()


def main():
    parser = argparse.ArgumentParser("events_cli")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    make_tweet_parser = subparsers.add_parser("make-tweet", help="Manually make a new tweet")
    make_tweet_parser.add_argument("--author", required=True, help="Author name")
    make_tweet_parser.add_argument("content", help="Text content of the tweet")

    make_tweet_parser = subparsers.add_parser("view-tweet", help="View tweets on event stream") 

    args = parser.parse_args()
    if args.command == "make-tweet":
        make_tweet(args.author, args.content)
    elif args.command == "view-tweet":
        view_tweet()
    else:
        raise ValueError(f"Unrecognized command: {args.command}")
