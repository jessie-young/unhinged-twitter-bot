import argparse



def make_tweet(author: str, content: str):
    print(f"Making tweet for @{author}: {content}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser("events_cli")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    make_tweet_parser = subparsers.add_parser("make-tweet", help="Manually make a new tweet")
    make_tweet_parser.add_argument("--author", required=True, help="Author name")
    make_tweet_parser.add_argument("content", help="Text content of the tweet")

    args = parser.parse_args()
    if args.command == "make-tweet":
        make_tweet(args.author, args.content)
