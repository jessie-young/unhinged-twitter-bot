#!/usr/bin/env python3
import os
import json
import time
import redis
import lancedb
import uuid
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
import logging

from unhinged_twitter_bot.config import LANCEDB_TABLE_NAME
from unhinged_twitter_bot.twitter import TwitterAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize embedding function
embedding_func = get_registry().get("sentence-transformers").create(
    name="BAAI/bge-small-en-v1.5", 
    device="cpu"
)

# Define LanceDB model with additional columns
class Tweet(LanceModel):
    text: str = embedding_func.SourceField()
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()
    tweet_id: str = None
    username: str = None
    author_id: str = None
    retweets: int = 0
    likes: int = 0
    created_at: float = None  # Renamed from timestamp
    reply_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    impression_count: int = 0
    lang: str = None


def process_tweet(tweet_data, table):
    """Process a tweet and add its embedding to LanceDB"""
    try:
        # Parse tweet data
        tweet = json.loads(tweet_data)
        
        # Check if this is the TwitterAPI format (with author/content) or the expected format (with text/id)
        if 'content' in tweet and 'author' in tweet:
            # This is from TwitterAPI
            tweet_text = tweet.get('content', '')
            username = tweet.get('author', '')
            tweet_id = str(uuid.uuid4())  # Generate a UUID since there's no ID
            author_id = tweet.get('author_id', username)
            retweets = 0
            likes = 0
            created_at = time.time()
            reply_count = 0
            quote_count = 0
            bookmark_count = 0
            impression_count = 0
            lang = tweet.get('lang', 'en')
            logger.info(f"Received tweet in TwitterAPI format from {username}")
        else:
            # This is the expected format
            tweet_text = tweet.get('text', '')
            username = tweet.get('username', '')
            tweet_id = tweet.get('id', str(uuid.uuid4()))
            author_id = tweet.get('author_id', username)
            
            # Extract metrics
            retweets = int(tweet.get('retweets', 0))
            likes = int(tweet.get('likes', 0))
            reply_count = int(tweet.get('reply_count', 0))
            quote_count = int(tweet.get('quote_count', 0))
            bookmark_count = int(tweet.get('bookmark_count', 0))
            impression_count = int(tweet.get('impression_count', 0))
            
            # Convert timestamp or use created_at directly
            if 'created_at' in tweet:
                created_at = tweet.get('created_at')
                # If created_at is a string, try to convert to timestamp
                if isinstance(created_at, str):
                    try:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    except (ValueError, TypeError):
                        created_at = time.time()
            else:
                created_at = tweet.get('timestamp', time.time())
                
            lang = tweet.get('lang', 'en')
        
        if not tweet_text:
            logger.warning(f"Received empty tweet text for tweet ID {tweet_id}")
            return
            
        # Create tweet record with embedding and all the additional fields
        tweet_record = {
            "text": tweet_text,
            "tweet_id": tweet_id,
            "username": username,
            "author_id": author_id,
            "retweets": retweets,
            "likes": likes,
            "created_at": created_at,
            "reply_count": reply_count,
            "quote_count": quote_count,
            "bookmark_count": bookmark_count,
            "impression_count": impression_count,
            "lang": lang
        }
        
        # Add to LanceDB
        table.add([tweet_record])
        logger.info(f"Added tweet {tweet_id} from {username} to LanceDB")
        
    except Exception as e:
        logger.error(f"Error processing tweet: {e}")

def main():
    logger.info("Tweet embedding service started")

    # LanceDB setup
    uri = "/app/data/lancedb"
    db = lancedb.connect(uri)

    # Get table name from environment variable if set, otherwise use default
    table_name = os.environ.get("LANCEDB_TABLE_NAME", LANCEDB_TABLE_NAME)
    logger.info(f"Using table name: {table_name}")

    # Create or open table
    if table_name in db.table_names():
        table = db.open_table(table_name)
        logger.info(f"Opened existing '{table_name}' table")
    else:
        table = db.create_table(table_name, schema=Tweet)
        logger.info(f"Created new '{table_name}' table")
        
    # Dump the contents of the table (limited to avoid memory issues)
    logger.info(f"Dumping contents of table '{table_name}':")
    
    # Count total records
    total_count = len(table)
    logger.info(f"Table contains {total_count} total records")
    
    # Show a limited number of records
    max_records_to_display = 5
    if total_count == 0:
        logger.info("Table is empty")
    else:
        # Use execute() to get the raw data and limit the number of records
        query_result = table.search().limit(max_records_to_display).to_list()
        
        logger.info(f"Displaying first {min(max_records_to_display, total_count)} records:")
        for i, record in enumerate(query_result):
            # Create a clean version without the vector to display
            display_record = {k: v for k, v in record.items() if k != 'vector'}
            logger.info(f"Record {i + 1}: {display_record}")

    api = TwitterAPI()
    for tweet in api.get_tweets():
        process_tweet(tweet, table)

if __name__ == "__main__":
    main()
