import argparse
import os
import redis

from dotenv import load_dotenv


load_dotenv(dotenv_path=".env.dev")


REDIS_ADDR = os.environ["REDIS_EVENTS_PUBSUB_ADDR"]
REDIS_TOPIC_NAME = "tweets"


def make_tweet(author: str, content: str):
    print(f"Making tweet for @{author}: {content}")
    r = redis.Redis.from_url(f"redis://{REDIS_ADDR}")
    tweet_data = {
        "author": author,
        "content": content
    }
    result = r.publish(REDIS_TOPIC_NAME, str(tweet_data))
    print(f"Published to Redis topic `{REDIS_TOPIC_NAME}` with result: {result}")


def view_tweet():
    r = redis.Redis.from_url(f"redis://{REDIS_ADDR}")
    pubsub = r.pubsub()
    pubsub.subscribe(REDIS_TOPIC_NAME)
    
    print("Listening for tweets...")
    for message in pubsub.listen():
        if message["type"] == "message":
            print(f"Received tweet: {message['data'].decode('utf-8')}")
            break  # Exit after receiving one message
    
    pubsub.unsubscribe()


if __name__ == "__main__":
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
