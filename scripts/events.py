import argparse
import daft

from unhinged_twitter_bot.twitter import TwitterAPI


def make_tweet(author: str, content: str):
    api = TwitterAPI.get_api()
    api.make_tweet(content, author)


def view_tweet():
    api = TwitterAPI.get_api()

    for tweet in api.get_tweets():
        print(f"Received tweet: {tweet}")

def ingest_tweets(csv_filepath: str):
    df = daft.read_csv(csv_filepath)
    for row in df.iter_rows():
        author = row["Username"]
        text = row["Text"]
        make_tweet(author, text)


def main():
    parser = argparse.ArgumentParser("events_cli")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    make_tweet_parser = subparsers.add_parser("make-tweet", help="Manually make a new tweet")
    make_tweet_parser.add_argument("--author", required=True, help="Author name")
    make_tweet_parser.add_argument("content", help="Text content of the tweet")

    make_tweet_parser = subparsers.add_parser("view-tweets", help="View tweets on event stream") 

    ingest_tweets_parser = subparsers.add_parser("ingest-tweets", help="Ingest tweets from a properly formatted CSV")
    ingest_tweets_parser.add_argument("csv_filepath")

    args = parser.parse_args()
    if args.command == "make-tweet":
        print(f"Making tweet for @{args.author}: {args.content}")
        make_tweet(args.author, args.content)
    elif args.command == "view-tweets":
        view_tweet()
    elif args.command == "ingest-tweets":
        print(f"Ingesting CSV at {args.csv_filepath}")
        ingest_tweets(args.csv_filepath)
    else:
        raise ValueError(f"Unrecognized command: {args.command}")
