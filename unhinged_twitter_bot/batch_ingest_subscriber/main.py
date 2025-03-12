import argparse
import daft

from unhinged_twitter_bot.twitter import TwitterAPI

class CSVWriter:
    def __init__(self, dest_folder: str):
        self.dest_folder = dest_folder
        self.buffer = []
        self.buffer_size = 1000
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        
    def ingest(self, tweet_data: str):
        self.buffer.append(tweet_data)
        if len(self.buffer) >= self.buffer_size:
            self.flush()
            
    def flush(self):
        if not self.buffer:
            return
        
        df = daft.from_pydict({"json_data": self.buffer})
        df = df.with_column("author", df["json_data"].json.query(".author"))
        df = df.with_column("content", df["json_data"].json.query(".content"))
        df = df.exclude("json_data")
        df.write_csv(self.dest_folder)

        self.buffer = []


def main():
    parser = argparse.ArgumentParser("batch_ingest_subscriber")
    parser.add_argument("dest_folder", help="Destination folder to write tweet data")
    args = parser.parse_args()

    api = TwitterAPI.get_api()

    with CSVWriter(args.dest_folder) as writer:
        print(f"Ingesting data into: {args.dest_folder}")
        for tweet in api.get_tweets():
            writer.ingest(tweet)
